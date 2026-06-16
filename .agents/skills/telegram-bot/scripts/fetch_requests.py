#!/usr/bin/env python3
"""Fetch recent Telegram messages and transcribe pending audio — agent entry point.

Run this when the user says there are new requests, new messages, or asks to
check Telegram. It performs Phase 1 (sync) and Phase 2a (transcribe) in one shot.

Usage:
    python fetch_requests.py
    python fetch_requests.py --skip-transcribe
    python fetch_requests.py --language fa

Requires TELEGRAM_BOT_TOKEN in .env or the environment.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from load_env import load_env

SKILLS_ROOT = SCRIPT_DIR.parent.parent
TELEGRAM_SCRIPT = SCRIPT_DIR / "telegram_pipeline.py"
TRANSCRIBE_QUEUE = SKILLS_ROOT / "audio-transcription" / "scripts" / "process_audio_queue.py"
DRAFTS_DIR = Path.cwd() / "docs/discovery/requests/drafts"


def telegram_sync_cmd() -> list[str]:
    """Use uv for telegram_pipeline (PEP 723 deps) when available."""
    if shutil.which("uv"):
        return ["uv", "run", str(TELEGRAM_SCRIPT), "--once"]
    return [sys.executable, str(TELEGRAM_SCRIPT), "--once"]


def run(cmd: list[str], *, label: str) -> int:
    print(f"\n── {label} ──", file=sys.stderr)
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"✗ {label} failed (exit {result.returncode})", file=sys.stderr)
    else:
        print(f"✓ {label} done", file=sys.stderr)
    return result.returncode


def list_new_drafts() -> list[Path]:
    if not DRAFTS_DIR.exists():
        return []
    return sorted(DRAFTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Telegram requests and transcribe audio.")
    parser.add_argument("--skip-transcribe", action="store_true", help="Only sync Telegram; skip transcription.")
    parser.add_argument("--language", default=None, help="Language code for transcription (e.g. fa).")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing.")
    args = parser.parse_args()

    env_file = load_env()
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        print("TELEGRAM_BOT_TOKEN is not set.", file=sys.stderr)
        if env_file:
            print(f"Add TELEGRAM_BOT_TOKEN=your_token to {env_file}", file=sys.stderr)
        else:
            print("Create a .env file in the project root with TELEGRAM_BOT_TOKEN=your_token", file=sys.stderr)
        return 1
    if env_file:
        print(f"Loaded env from {env_file}", file=sys.stderr)

    sync_cmd = telegram_sync_cmd()
    transcribe_cmd = [sys.executable, str(TRANSCRIBE_QUEUE)]
    if args.language:
        transcribe_cmd.extend(["--language", args.language])

    if args.dry_run:
        print("Would run:", file=sys.stderr)
        print(f"  1. {' '.join(sync_cmd)}", file=sys.stderr)
        if not args.skip_transcribe:
            print(f"  2. {' '.join(transcribe_cmd)}", file=sys.stderr)
        return 0

    before = {p.name for p in list_new_drafts()}
    exit_code = run(sync_cmd, label="Sync Telegram messages")

    if exit_code != 0:
        return exit_code

    after = list_new_drafts()
    new_files = [p for p in after if p.name not in before]
    if new_files:
        print(f"\nNew drafts ({len(new_files)}):", file=sys.stderr)
        for p in new_files:
            print(f"  • {p.name}", file=sys.stderr)
    else:
        print("\nNo new drafts since last sync.", file=sys.stderr)

    if args.skip_transcribe:
        return 0

    if not TRANSCRIBE_QUEUE.exists():
        print(f"Transcription queue script not found: {TRANSCRIBE_QUEUE}", file=sys.stderr)
        return 1

    return run(transcribe_cmd, label="Transcribe pending audio")


if __name__ == "__main__":
    raise SystemExit(main())
