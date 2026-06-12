#!/usr/bin/env python3
"""Transcribe a project audio note and write discovery docs.

Requires OPENAI_API_KEY for hosted transcription. Codex may extend this script.
Do not commit API keys.

Example:
    python tools/transcribe_audio.py --file audio_2026-06-12_10-33-51.ogg
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def convert_to_wav(input_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(input_path), str(output_path)], check=True)
    return output_path


def transcribe_with_openai(audio_path: Path) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Install the OpenAI SDK first: pip install openai") from exc

    client = OpenAI()
    with audio_path.open("rb") as f:
        result = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=f,
            language="fa",
        )
    return getattr(result, "text", str(result))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to audio file")
    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.exists():
        raise SystemExit(f"Audio file not found: {input_path}")

    discovery_dir = Path("docs/discovery")
    discovery_dir.mkdir(parents=True, exist_ok=True)

    wav_path = discovery_dir / "audio.wav"
    if input_path.suffix.lower() in {".ogg", ".oga", ".opus"}:
        audio_for_transcription = convert_to_wav(input_path, wav_path)
    else:
        audio_for_transcription = input_path

    if not os.getenv("OPENAI_API_KEY"):
        note = (
            "Audio transcription could not be completed because OPENAI_API_KEY is not set.\n\n"
            "Fallback option: install Whisper and run:\n\n"
            f"```bash\nwhisper {audio_for_transcription} --model medium --language Persian --output_format txt --output_dir docs/discovery\n```\n"
        )
        (discovery_dir / "audio_transcript.fa.md").write_text(note, encoding="utf-8")
        print(note)
        return

    transcript = transcribe_with_openai(audio_for_transcription)
    (discovery_dir / "audio_transcript.fa.md").write_text("# Audio Transcript — Persian\n\n" + transcript + "\n", encoding="utf-8")
    (discovery_dir / "audio_summary.en.md").write_text(
        "# Audio Summary — English\n\nTODO: Summarize the Persian transcript in English.\n",
        encoding="utf-8",
    )
    (discovery_dir / "audio_requirements.en.md").write_text(
        "# Audio Requirements — English\n\nTODO: Extract structured requirements from the Persian transcript.\n",
        encoding="utf-8",
    )
    print(f"Wrote transcript to {discovery_dir / 'audio_transcript.fa.md'}")


if __name__ == "__main__":
    main()
