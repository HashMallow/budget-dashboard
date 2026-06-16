#!/usr/bin/env python3
"""Standalone transcription worker — Phase 2a.

Scans telegram drafts for pending audio/voice messages, transcribes them using
transcribe_audio.py, and updates the draft files. Completely independent of the
Telegram bot; run on demand, via cron, or as a systemd timer.

Usage:
    python process_audio_queue.py                  # process all pending drafts
    python process_audio_queue.py --watch 60       # poll every 60 seconds
    python process_audio_queue.py --dry-run        # list pending without transcribing
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TRANSCRIBE_SCRIPT = SCRIPT_DIR / "transcribe_audio.py"

PROJECT_ROOT = Path.cwd()
DRAFTS_DIR = PROJECT_ROOT / "docs/discovery/requests/drafts"
TRANSCRIPTS_DIR = PROJECT_ROOT / ".artifacts/telegram-bot/transcripts"

AUDIO_DRAFT_TYPES = {"voice", "audio"}
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FIELD_RE = re.compile(r"^(\w+):\s*(.+)$", re.MULTILINE)
AUDIO_FILE_BODY_RE = re.compile(r"^audio_file:\s*(.+)$", re.MULTILINE)


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
    if status in {"transcribed", "processed"}:
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


def extract_transcript_text(transcript_path: Path) -> str:
    text = transcript_path.read_text(encoding="utf-8")
    marker = "## Transcript"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return text.strip()


def transcribe_draft(draft_path: Path, *, language: str | None, model: str) -> bool:
    content = draft_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(content)

    audio_file = resolve_audio_path(meta, body)
    if audio_file is None or not audio_file.exists():
        print(f"Audio file missing for {draft_path.name}: {audio_file}", file=sys.stderr)
        return False

    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    transcript_name = f"{draft_path.stem}.transcript.md"
    transcript_path = TRANSCRIPTS_DIR / transcript_name

    cmd = [
        sys.executable,
        str(TRANSCRIBE_SCRIPT),
        str(audio_file),
        "--out-dir",
        str(TRANSCRIPTS_DIR),
        "--output-name",
        transcript_name,
        "--model",
        model,
    ]
    if language:
        cmd.extend(["--language", language])

    print(f"Transcribing {audio_file.name} → {transcript_path.name}", file=sys.stderr)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        return False

    if not transcript_path.exists():
        print(f"Transcription finished but output not found: {transcript_path}", file=sys.stderr)
        return False

    transcript_text = extract_transcript_text(transcript_path)
    meta["status"] = "transcribed"
    meta["audio_file"] = str(audio_file.resolve())
    meta["transcript_file"] = str(transcript_path.resolve())

    updated_body = (
        f"## Transcript\n\n{transcript_text}\n\n"
        f"---\n\n"
        f"Original placeholder:\n\n{body.strip()}\n"
    )
    draft_path.write_text(render_frontmatter(meta) + "\n\n" + updated_body, encoding="utf-8")
    print(f"Updated draft: {draft_path.name}", file=sys.stderr)
    return True


def process_queue(*, language: str | None, model: str, dry_run: bool) -> int:
    pending = find_pending_drafts()
    if not pending:
        print("No pending audio drafts.", file=sys.stderr)
        return 0

    print(f"Found {len(pending)} pending audio draft(s).", file=sys.stderr)
    if dry_run:
        for path in pending:
            text = path.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(text)
            audio = resolve_audio_path(meta, body)
            print(f"  {path.name}  audio={audio}", file=sys.stderr)
        return 0

    ok = 0
    for draft_path in pending:
        if transcribe_draft(draft_path, language=language, model=model):
            ok += 1
    print(f"Transcribed {ok}/{len(pending)} draft(s).", file=sys.stderr)
    return 0 if ok == len(pending) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Process pending audio drafts (Phase 2a).")
    parser.add_argument("--language", default=None, help="Language code such as fa or en.")
    parser.add_argument("--model", default="auto", help="Whisper model (default: auto).")
    parser.add_argument("--dry-run", action="store_true", help="List pending drafts without transcribing.")
    parser.add_argument(
        "--watch",
        type=int,
        default=0,
        metavar="SECONDS",
        help="Poll for new drafts every N seconds (0 = run once and exit).",
    )
    args = parser.parse_args()

    if args.watch > 0:
        print(f"Watching {DRAFTS_DIR} every {args.watch}s (Ctrl+C to stop)...", file=sys.stderr)
        try:
            while True:
                process_queue(language=args.language, model=args.model, dry_run=args.dry_run)
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\nStopped.", file=sys.stderr)
            return 0

    return process_queue(language=args.language, model=args.model, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
