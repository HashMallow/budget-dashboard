#!/usr/bin/env python3
"""Standalone transcription worker — Phase 2a.

Scans telegram drafts for pending audio/voice messages, transcribes them using
transcribe_audio.py, and updates the draft files. Completely independent of the
Telegram bot; run on demand, via cron, or as a systemd timer.

Safe to run twice per day: a lock file prevents concurrent workers, and already
transcribed drafts are skipped (idempotent).

Usage:
    python process_audio_queue.py                          # process all pending drafts
    python process_audio_queue.py --backend local          # never call cloud APIs
    python process_audio_queue.py --max-items 20           # cap how many drafts to process
    python process_audio_queue.py --max-runtime-seconds 600
    python process_audio_queue.py --dry-run                # list pending without spending
    python process_audio_queue.py --watch 60               # poll every 60 seconds
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRANSCRIBE_SCRIPT = SCRIPT_DIR / "transcribe_audio.py"

PROJECT_ROOT = Path.cwd()
DRAFTS_DIR = PROJECT_ROOT / "docs/discovery/requests/drafts"
REQUESTS_DIR = DRAFTS_DIR.parent
INDEX_FILE = REQUESTS_DIR / "INDEX.md"
TRANSCRIPTS_DIR = PROJECT_ROOT / ".artifacts/telegram-bot/transcripts"
STATE_DIR = PROJECT_ROOT / ".artifacts/telegram-bot"
LOCK_FILE = STATE_DIR / "queue.lock"

# A lock older than this (and/or owned by a dead PID) is considered stale and
# may be stolen automatically by a new worker.
STALE_LOCK_SECONDS = 3600

AUDIO_DRAFT_TYPES = {"voice", "audio"}
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FIELD_RE = re.compile(r"^(\w+):\s*(.*)$", re.MULTILINE)
AUDIO_FILE_BODY_RE = re.compile(r"^audio_file:\s*(.+)$", re.MULTILINE)
CONFIDENCE_RE = re.compile(r"Confidence:\s*`?([\w-]+)`?", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    frontmatter: dict[str, str] = {}
    for key, value in FIELD_RE.findall(match.group(1)):
        frontmatter[key.strip()] = value.strip()

    body = text[match.end() :]
    return frontmatter, body


def render_frontmatter(fields: dict[str, str]) -> str:
    lines = ["---"]
    for key, value in fields.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def _one_line(text: str) -> str:
    """Collapse whitespace so a value is safe inside a single frontmatter line."""
    return " ".join(str(text).split())[:500]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def resolve_audio_path(meta: dict[str, str], body: str) -> Path | None:
    """Read audio_file from frontmatter or legacy body line; resolve relative paths."""
    raw = meta.get("audio_file")
    if not raw:
        match = AUDIO_FILE_BODY_RE.search(body)
        raw = match.group(1).strip() if match else None
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def is_pending_audio_draft(meta: dict[str, str], body: str) -> bool:
    draft_type = meta.get("type")
    if draft_type not in AUDIO_DRAFT_TYPES:
        return False
    status = meta.get("status")
    # Never reprocess terminal states (idempotency).
    if status in {"transcribed", "processed", "failed", "comprehended"}:
        return False
    if status == "pending":
        return True
    # Legacy drafts: voice/audio type without status and without embedded transcript
    return "## Transcript" not in body and "awaiting transcription" in body.lower()


def find_pending_drafts() -> list[Path]:
    if not DRAFTS_DIR.exists():
        return []

    pending: list[Path] = []
    for path in sorted(DRAFTS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        if not is_pending_audio_draft(meta, body):
            continue
        if resolve_audio_path(meta, body) is None:
            continue
        pending.append(path)
    return pending


# ---------------------------------------------------------------------------
# Lock file (idempotency / concurrency protection)
# ---------------------------------------------------------------------------

def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by another user
    except Exception:
        return False
    return True


def _read_lock() -> dict:
    try:
        return json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return {}


def _lock_is_stale(info: dict) -> bool:
    if not info:
        return True  # empty/unreadable lock is treated as stale
    pid = info.get("pid")
    if isinstance(pid, int) and not _pid_alive(pid):
        return True
    epoch = info.get("epoch")
    if isinstance(epoch, (int, float)) and (time.time() - epoch) > STALE_LOCK_SECONDS:
        return True
    return False


def acquire_lock(force: bool = False) -> bool:
    """Create the lock atomically. Returns True if acquired, False if another live worker holds it."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    for _ in range(3):
        try:
            fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            info = _read_lock()
            if force or _lock_is_stale(info):
                holder = info.get("pid", "unknown")
                print(f"Stealing stale/forced lock (previous holder pid={holder}).", file=sys.stderr)
                try:
                    LOCK_FILE.unlink()
                except FileNotFoundError:
                    pass
                continue
            print(
                f"Another queue worker is already running (pid={info.get('pid')}, "
                f"since {info.get('created_at')}). Aborting. "
                f"Use --force if you are sure it is dead.",
                file=sys.stderr,
            )
            return False
        else:
            with os.fdopen(fd, "w") as handle:
                json.dump({"pid": os.getpid(), "epoch": time.time(), "created_at": _now()}, handle)
            return True
    print("Could not acquire lock after retries.", file=sys.stderr)
    return False


def release_lock() -> None:
    """Remove the lock only if we own it (robust against double-release)."""
    info = _read_lock()
    if info.get("pid") == os.getpid():
        try:
            LOCK_FILE.unlink()
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Audio duration (best-effort, for --max-audio-minutes)
# ---------------------------------------------------------------------------

def _audio_duration_seconds(path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=True,
        )
        return float(out.stdout.strip())
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Draft transcription
# ---------------------------------------------------------------------------

def extract_transcript_text(transcript_path: Path) -> str:
    text = transcript_path.read_text(encoding="utf-8")
    marker = "## Transcript"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return text.strip()


def extract_confidence(transcript_path: Path) -> str | None:
    try:
        text = transcript_path.read_text(encoding="utf-8")
    except OSError:
        return None
    head = text.split("## Transcript", 1)[0]
    match = CONFIDENCE_RE.search(head)
    return match.group(1).lower() if match else None


def _message_dir_for(meta: dict[str, str], audio_file: Path) -> Path | None:
    """Return the per-message folder for this draft, if it uses the folder layout."""
    raw = meta.get("message_dir")
    if raw:
        path = Path(raw)
        return path if path.is_absolute() else (PROJECT_ROOT / path)
    # Derive from audio path: .../messages/<stem>/audio.wav
    parent = audio_file.parent
    if parent.parent.name == "messages":
        return parent
    return None


def _rel(target: Path, start: Path) -> str:
    """Relative POSIX path from `start` dir to `target`, for portable markdown links."""
    try:
        return os.path.relpath(target, start).replace(os.sep, "/")
    except ValueError:
        return str(target)


def write_navigable_transcript(
    transcript_path: Path,
    *,
    meta: dict[str, str],
    draft_path: Path,
    audio_file: Path,
    source_audio: Path | None,
    transcript_text: str,
    confidence: str | None,
) -> None:
    """Rewrite the transcript file with a metadata header and backlinks so it is
    self-describing and easy to cross-check against the source audio and draft."""
    here = transcript_path.parent
    sender = meta.get("sender", "unknown")
    date = meta.get("date", "")
    dtype = meta.get("type", "audio")

    rel_draft = _rel(draft_path.resolve(), here)
    rel_wav = _rel(audio_file.resolve(), here)
    rel_source = _rel(source_audio.resolve(), here) if source_audio else rel_wav

    front = ["---", f"title: Transcript — {dtype} from {sender}"]
    if date:
        front.append(f"date: {date}")
    for key in ("type", "sender", "message_id", "chat_id"):
        if meta.get(key):
            front.append(f"{key}: {meta[key]}")
    if confidence:
        front.append(f"confidence: {confidence}")
    front.append(f"draft: {rel_draft}")
    front.append(f"audio_wav: {rel_wav}")
    if source_audio:
        front.append(f"audio_source: {rel_source}")
    front.append("---")

    header_title = f"# Transcript — {dtype} from {sender}"
    if date:
        header_title += f" · {date}"

    nav = [
        header_title,
        "",
        f"- Listen: [{Path(rel_wav).name}]({rel_wav})"
        + (f" (original: [{Path(rel_source).name}]({rel_source}))" if source_audio else ""),
        f"- Draft: [{draft_path.name}]({rel_draft})",
        "",
        "## Transcript",
        "",
        transcript_text.strip(),
        "",
    ]
    transcript_path.write_text("\n".join(front) + "\n\n" + "\n".join(nav), encoding="utf-8")


def _mark_failed(draft_path: Path, meta: dict[str, str], body: str, error: str) -> None:
    """Set status: failed and record the error without losing the original body."""
    meta["status"] = "failed"
    meta["error"] = _one_line(error)
    meta["processed_at"] = _now()
    draft_path.write_text(render_frontmatter(meta) + "\n\n" + body.strip() + "\n", encoding="utf-8")


def transcribe_draft(
    draft_path: Path,
    *,
    language: str | None,
    model: str,
    backend: str | None,
    max_audio_minutes: float,
) -> str:
    """Returns 'ok', 'failed', or 'skipped'."""
    content = draft_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(content)

    audio_file = resolve_audio_path(meta, body)
    if audio_file is None or not audio_file.exists():
        msg = f"audio_file not found: {audio_file}"
        print(f"  {draft_path.name}: {msg}", file=sys.stderr)
        _mark_failed(draft_path, meta, body, msg)
        return "failed"

    if max_audio_minutes > 0:
        duration = _audio_duration_seconds(audio_file)
        if duration is not None and (duration / 60.0) > max_audio_minutes:
            print(
                f"  Skipping {draft_path.name}: {duration / 60.0:.1f} min exceeds "
                f"--max-audio-minutes {max_audio_minutes}.",
                file=sys.stderr,
            )
            return "skipped"

    # Co-locate the transcript with its audio in the per-message folder when available;
    # otherwise fall back to the legacy flat transcripts directory.
    message_dir = _message_dir_for(meta, audio_file)
    if message_dir is not None:
        transcript_dir = message_dir
        transcript_name = "transcript.md"
    else:
        transcript_dir = TRANSCRIPTS_DIR
        transcript_name = f"{draft_path.stem}.transcript.md"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = transcript_dir / transcript_name

    cmd = [
        sys.executable,
        str(TRANSCRIBE_SCRIPT),
        str(audio_file),
        "--out-dir",
        str(transcript_dir),
        "--output-name",
        transcript_name,
        "--model",
        model,
    ]
    if backend:
        cmd.extend(["--backend", backend])
    if language:
        cmd.extend(["--language", language])

    print(f"Transcribing {audio_file.name} → {transcript_path.name}", file=sys.stderr)
    # Capture stdout (the transcript path) but let stderr stream live so the
    # transcription progress bar and diagnostics remain visible.
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    if result.returncode != 0:
        msg = f"transcribe_audio.py exited with code {result.returncode} (see log above)"
        print(f"  {draft_path.name}: {msg}", file=sys.stderr)
        _mark_failed(draft_path, meta, body, msg)
        return "failed"

    if not transcript_path.exists():
        msg = f"transcription finished but output not found: {transcript_path}"
        print(f"  {draft_path.name}: {msg}", file=sys.stderr)
        _mark_failed(draft_path, meta, body, msg)
        return "failed"

    transcript_text = extract_transcript_text(transcript_path)
    confidence = extract_confidence(transcript_path)

    # Find the original downloaded source (source.* inside the message folder) for backlinks.
    source_audio = None
    if message_dir is not None:
        for cand in sorted(message_dir.glob("source.*")):
            source_audio = cand
            break

    meta["status"] = "transcribed"
    meta["audio_file"] = str(audio_file.resolve())
    meta["transcript_file"] = str(transcript_path.resolve())
    meta["processed_at"] = _now()
    if confidence:
        meta["confidence"] = confidence
    meta.pop("error", None)

    # Rewrite the standalone transcript with metadata + backlinks so it is self-describing.
    write_navigable_transcript(
        transcript_path,
        meta=meta,
        draft_path=draft_path,
        audio_file=audio_file,
        source_audio=source_audio,
        transcript_text=transcript_text,
        confidence=confidence,
    )

    rel_transcript = _rel(transcript_path.resolve(), draft_path.parent)
    updated_body = (
        f"## Transcript\n\n"
        f"Full transcript + audio links: [{transcript_path.name}]({rel_transcript})\n\n"
        f"{transcript_text}\n\n"
        f"---\n\n"
        f"Original placeholder:\n\n{body.strip()}\n"
    )
    draft_path.write_text(render_frontmatter(meta) + "\n\n" + updated_body, encoding="utf-8")
    print(f"Updated draft: {draft_path.name}", file=sys.stderr)
    return "ok"


# ---------------------------------------------------------------------------
# Queue processing
# ---------------------------------------------------------------------------

def _md_link(target_raw: str | None, base: Path, label: str | None = None) -> str:
    """Build a relative markdown link from `base` dir to an absolute/relative path string."""
    if not target_raw:
        return "—"
    target = Path(target_raw)
    if not target.is_absolute():
        target = PROJECT_ROOT / target
    if not target.exists():
        return "—"
    rel = _rel(target, base)
    return f"[{label or target.name}]({rel})"


def generate_index() -> Path | None:
    """Write docs/discovery/requests/INDEX.md — one navigable table of every draft,
    linking each entry to its draft, transcript, and audio."""
    if not DRAFTS_DIR.exists():
        return None

    rows = []
    for path in DRAFTS_DIR.glob("*.md"):
        meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        rows.append((path, meta))
    # Newest first (filenames are timestamped, so name sort works well).
    rows.sort(key=lambda r: r[0].name, reverse=True)

    lines = [
        "# Request Index",
        "",
        f"_Generated {_now()} · {len(rows)} item(s)._",
        "",
        "| Date | Sender | Type | Status | Conf. | Draft | Transcript | Audio |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for path, meta in rows:
        date = meta.get("date", "—")
        sender = meta.get("sender", "—")
        dtype = meta.get("type", "—")
        status = meta.get("status", "—")
        conf = meta.get("confidence", "—")
        draft_link = _md_link(str(path), REQUESTS_DIR, label=path.name)
        transcript_link = _md_link(meta.get("transcript_file"), REQUESTS_DIR, label="transcript")
        audio_link = _md_link(meta.get("audio_file"), REQUESTS_DIR, label="audio")
        lines.append(
            f"| {date} | {sender} | {dtype} | {status} | {conf} | "
            f"{draft_link} | {transcript_link} | {audio_link} |"
        )

    REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return INDEX_FILE


def process_queue(
    *,
    language: str | None,
    model: str,
    backend: str | None,
    dry_run: bool,
    max_items: int,
    max_runtime_seconds: int,
    max_audio_minutes: float,
    start_time: float,
) -> int:
    pending = find_pending_drafts()
    if not pending:
        print("No pending audio drafts.", file=sys.stderr)
        return 0

    print(f"Found {len(pending)} pending audio draft(s).", file=sys.stderr)
    print(f"Backend: {backend or 'env/auto'} | model: {model}", file=sys.stderr)

    if dry_run:
        limits = []
        if max_items:
            limits.append(f"max-items={max_items}")
        if max_runtime_seconds:
            limits.append(f"max-runtime={max_runtime_seconds}s")
        if max_audio_minutes:
            limits.append(f"max-audio={max_audio_minutes}min")
        if limits:
            print(f"Limits: {', '.join(limits)}", file=sys.stderr)
        print("Dry run — nothing will be transcribed and no API calls will be made.", file=sys.stderr)
        for path in pending:
            meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            audio = resolve_audio_path(meta, body)
            print(f"  {path.name}  audio={audio}", file=sys.stderr)
        return 0

    ok = failed = skipped = processed = 0
    for draft_path in pending:
        if max_items and processed >= max_items:
            print(f"Reached --max-items {max_items}; stopping.", file=sys.stderr)
            break
        if max_runtime_seconds and (time.time() - start_time) >= max_runtime_seconds:
            print(f"Reached --max-runtime-seconds {max_runtime_seconds}; stopping.", file=sys.stderr)
            break

        result = transcribe_draft(
            draft_path,
            language=language,
            model=model,
            backend=backend,
            max_audio_minutes=max_audio_minutes,
        )
        if result == "ok":
            ok += 1
            processed += 1
        elif result == "failed":
            failed += 1
            processed += 1
        else:  # skipped (e.g. too long) — left pending, not counted toward max-items
            skipped += 1

    summary = f"Transcribed {ok} ok, {failed} failed"
    if skipped:
        summary += f", {skipped} skipped"
    summary += f" (of {len(pending)} pending)."
    print(summary, file=sys.stderr)
    return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Process pending audio drafts (Phase 2a).")
    parser.add_argument("--language", default=None, help="Language code such as fa or en.")
    parser.add_argument("--model", default="auto", help="Whisper model (default: auto).")
    parser.add_argument(
        "--backend",
        default=None,
        choices=["local", "openai", "auto"],
        help="Transcription backend passed to transcribe_audio.py. 'local' avoids all cloud "
             "API calls (recommended for scheduled runs). Defaults to the TRANSCRIPTION_BACKEND "
             "env var, then 'auto'.",
    )
    parser.add_argument("--dry-run", action="store_true", help="List pending drafts without transcribing or spending.")
    parser.add_argument("--max-items", type=int, default=0, help="Max drafts to process this run (0 = no limit).")
    parser.add_argument(
        "--max-runtime-seconds",
        type=int,
        default=0,
        help="Stop starting new drafts after this many seconds (0 = no limit).",
    )
    parser.add_argument(
        "--max-audio-minutes",
        type=float,
        default=0,
        help="Skip individual audio files longer than this (needs ffprobe; 0 = no limit).",
    )
    parser.add_argument("--force", action="store_true", help="Steal an existing lock even if it looks active.")
    parser.add_argument("--index", action="store_true", help="Only (re)build docs/discovery/requests/INDEX.md and exit.")
    parser.add_argument("--no-index", action="store_true", help="Do not rebuild INDEX.md after processing.")
    parser.add_argument(
        "--watch",
        type=int,
        default=0,
        metavar="SECONDS",
        help="Poll for new drafts every N seconds (0 = run once and exit). Holds the lock for "
             "the whole session.",
    )
    args = parser.parse_args()

    start_time = time.time()

    # --index: just rebuild the navigation index (no lock, no transcription).
    if args.index:
        path = generate_index()
        print(f"Wrote {path}" if path else "No drafts directory; nothing to index.", file=sys.stderr)
        return 0

    # Dry-run never mutates state or spends, so it does not need the lock.
    if args.dry_run:
        return process_queue(
            language=args.language, model=args.model, backend=args.backend, dry_run=True,
            max_items=args.max_items, max_runtime_seconds=args.max_runtime_seconds,
            max_audio_minutes=args.max_audio_minutes, start_time=start_time,
        )

    if not acquire_lock(force=args.force):
        return 3

    def _maybe_index() -> None:
        if not args.no_index:
            path = generate_index()
            if path:
                print(f"Index updated: {path}", file=sys.stderr)

    try:
        if args.watch > 0:
            print(f"Watching {DRAFTS_DIR} every {args.watch}s (Ctrl+C to stop)...", file=sys.stderr)
            try:
                while True:
                    process_queue(
                        language=args.language, model=args.model, backend=args.backend, dry_run=False,
                        max_items=args.max_items, max_runtime_seconds=args.max_runtime_seconds,
                        max_audio_minutes=args.max_audio_minutes, start_time=start_time,
                    )
                    _maybe_index()
                    if args.max_runtime_seconds and (time.time() - start_time) >= args.max_runtime_seconds:
                        print("Reached --max-runtime-seconds; exiting watch loop.", file=sys.stderr)
                        return 0
                    time.sleep(args.watch)
            except KeyboardInterrupt:
                print("\nStopped.", file=sys.stderr)
                return 0

        rc = process_queue(
            language=args.language, model=args.model, backend=args.backend, dry_run=False,
            max_items=args.max_items, max_runtime_seconds=args.max_runtime_seconds,
            max_audio_minutes=args.max_audio_minutes, start_time=start_time,
        )
        _maybe_index()
        return rc
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
