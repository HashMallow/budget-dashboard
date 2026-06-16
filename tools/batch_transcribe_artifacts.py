#!/usr/bin/env python3
"""Batch-transcribe audio under .artifacts/ per audio-transcription SKILL.md.

After a successful batch, update docs/voice-feedback/PROCESSING_LOG.en.md (git-tracked).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Prefer conda ml-env (torch + CUDA + faster-whisper); override with TRANSCRIBE_PYTHON.
PY = Path(
    os.environ.get(
        "TRANSCRIBE_PYTHON",
        "/home/workplace/miniconda3/envs/ml-env/bin/python",
    )
)
SCRIPT = ROOT / ".agents/skills/audio-transcription/scripts/transcribe_audio.py"
OUT_DIR = ROOT / ".artifacts/voice-feedback/transcripts"
WAV_DIR = ROOT / ".artifacts/voice-feedback/converted"

# Skill search paths (ogg sources only)
AUDIO_GLOBS = (
    ".artifacts/audio/*.ogg",
    ".artifacts/voice-feedback/audio/*.ogg",
)


def collect_sources() -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for pattern in AUDIO_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)
    return files


def needs_transcription(path: Path, out: Path) -> bool:
    if not out.exists():
        return True
    text = out.read_text(encoding="utf-8")
    if "Model: `large-v3`" in text or "openai whisper-1" in text:
        return False
    if "mlx-whisper large-v3" in text:
        return False
    # Re-run medium/small/unknown local whisper outputs.
    return True


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WAV_DIR.mkdir(parents=True, exist_ok=True)

    pending: list[Path] = []
    for f in collect_sources():
        out = OUT_DIR / f"{f.stem}_transcript.fa.md"
        if not needs_transcription(f, out):
            print(f"skip {f.name}")
            continue
        pending.append(f)

    if not pending:
        print("No pending audio under .artifacts/")
        return 0

    print(f"Transcribing {len(pending)} file(s) — OpenAI → CUDA large-v3 → CPU (skill order)...")
    ok = fail = 0
    for i, f in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] {f}", flush=True)
        cmd = [
            str(PY),
            str(SCRIPT),
            str(f),
            "--out-dir",
            str(OUT_DIR),
            "--wav-dir",
            str(WAV_DIR),
            "--language",
            "fa",
            "--model",
            "auto",
            "--device",
            "cuda",
            "--compute-type",
            "float16",
            "--output-name",
            f"{f.stem}_transcript.fa.md",
        ]
        if subprocess.run(cmd).returncode == 0:
            ok += 1
        else:
            fail += 1
            print(f"FAIL {f.name}", flush=True)

    print(f"\nBATCH_DONE ok={ok} fail={fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
