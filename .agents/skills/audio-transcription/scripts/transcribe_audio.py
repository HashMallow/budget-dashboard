#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


AUDIO_EXTENSIONS = {".ogg", ".oga", ".mp3", ".m4a", ".wav"}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def markdown_header(source: Path, wav_path: Path | None, tool: str, language: str | None) -> list[str]:
    lines = [
        "# Audio Transcript",
        "",
        f"Source audio: `{source}`",
    ]
    if wav_path is not None:
        lines.append(f"Converted WAV: `{wav_path}`")
    lines.extend(
        [
            f"Transcription tool: `{tool}`",
            f"Requested language: `{language or 'auto'}`",
            "",
            "## Transcript",
            "",
        ]
    )
    return lines


def convert_to_wav(audio_path: Path, out_dir: Path) -> Path:
    if audio_path.suffix.lower() not in {".ogg", ".oga"}:
        return audio_path
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to convert OGG/OGA audio to WAV.")
    wav_path = out_dir / f"{audio_path.stem}.wav"
    run([ffmpeg, "-y", "-loglevel", "error", "-i", str(audio_path), str(wav_path)])
    return wav_path


def transcribe_openai(audio_path: Path, language: str | None) -> str:
    from openai import OpenAI

    client = OpenAI()
    with audio_path.open("rb") as audio_file:
        kwargs = {
            "model": "whisper-1",
            "file": audio_file,
            "response_format": "text",
        }
        if language:
            kwargs["language"] = language
        result = client.audio.transcriptions.create(**kwargs)
    return str(result).strip()


def transcribe_whisper_cli(audio_path: Path, out_dir: Path, language: str | None) -> str:
    whisper = shutil.which("whisper")
    if not whisper:
        raise RuntimeError("whisper CLI is not installed.")
    command = [
        whisper,
        str(audio_path),
        "--output_format",
        "txt",
        "--output_dir",
        str(out_dir),
    ]
    if language:
        command.extend(["--language", language])
    run(command)
    transcript_path = out_dir / f"{audio_path.stem}.txt"
    return transcript_path.read_text(encoding="utf-8").strip()


def _cuda_available() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def _resolve_device(device: str) -> str:
    if device == "auto":
        return "cuda" if _cuda_available() else "cpu"
    return device


def _resolve_compute_type(compute_type: str, device: str) -> str:
    if compute_type != "auto":
        return compute_type
    return "float16" if device == "cuda" else "int8"


def _model_download_root() -> str:
    """Persistent cache directory (gitignored under docs/discovery/)."""
    override = os.environ.get("WHISPER_DOWNLOAD_ROOT")
    if override:
        return override
    return str(Path("docs/discovery/faster-whisper-models"))


def transcribe_faster_whisper(
    audio_path: Path,
    language: str | None,
    model: str,
    device: str = "auto",
    compute_type: str = "auto",
) -> tuple[list[str], str]:
    from faster_whisper import WhisperModel

    resolved_device = _resolve_device(device)
    resolved_compute = _resolve_compute_type(compute_type, resolved_device)

    def _load(dev: str, compute: str) -> tuple[WhisperModel, str, str]:
        download_root = _model_download_root()
        Path(download_root).mkdir(parents=True, exist_ok=True)
        return (
            WhisperModel(model, device=dev, compute_type=compute, download_root=download_root),
            dev,
            compute,
        )

    try:
        whisper_model, resolved_device, resolved_compute = _load(resolved_device, resolved_compute)
    except Exception as exc:
        if resolved_device == "cuda":
            # GPU init can fail when cuDNN/cuBLAS runtime libs are missing; fall back to CPU.
            print(f"CUDA init failed ({exc}); falling back to CPU.", file=sys.stderr)
            whisper_model, resolved_device, resolved_compute = _load("cpu", "int8")
        else:
            raise

    segments, info = whisper_model.transcribe(str(audio_path), language=language, vad_filter=True, beam_size=5)
    lines = [f"Detected language: `{info.language}` probability `{info.language_probability:.2f}`", ""]
    for segment in segments:
        text = segment.text.strip()
        if text:
            lines.append(f"[{segment.start:06.2f}-{segment.end:06.2f}] {text}")
    return lines, f"{resolved_device}/{resolved_compute}"


def write_limitation(out_path: Path, source: Path, reason: str) -> None:
    out_path.write_text(
        "\n".join(
            [
                "# Audio Transcript",
                "",
                f"Source audio: `{source}`",
                "",
                "Audio transcription could not be completed locally.",
                "",
                f"Reason: {reason}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe an audio file to markdown.")
    parser.add_argument("audio", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("docs/discovery"))
    parser.add_argument("--language", default=None, help="Language code such as fa or en. Omit for auto-detect.")
    parser.add_argument("--model", default="small", help="faster-whisper fallback model name (e.g. medium, large-v3).")
    parser.add_argument(
        "--wav-dir",
        type=Path,
        default=None,
        help="Directory for converted WAV files. Defaults to --out-dir.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Compute device for faster-whisper. 'auto' uses CUDA when available, else CPU.",
    )
    parser.add_argument(
        "--compute-type",
        default="auto",
        help="CTranslate2 compute type. 'auto' picks float16 on GPU and int8 on CPU.",
    )
    parser.add_argument("--output-name", default=None, help="Transcript markdown filename.")
    args = parser.parse_args()

    audio_path = args.audio
    if not audio_path.exists():
        print(f"Audio file not found: {audio_path}", file=sys.stderr)
        return 2
    if audio_path.suffix.lower() not in AUDIO_EXTENSIONS:
        print(f"Unsupported audio extension: {audio_path.suffix}", file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    wav_dir = args.wav_dir or args.out_dir
    wav_dir.mkdir(parents=True, exist_ok=True)
    suffix = args.language or "auto"
    output_name = args.output_name or f"audio_transcript.{suffix}.md"
    out_path = args.out_dir / output_name

    try:
        wav_path = convert_to_wav(audio_path, wav_dir)
    except Exception as exc:
        write_limitation(out_path, audio_path, str(exc))
        return 1

    transcript_lines: list[str]
    converted = wav_path if wav_path != audio_path else None

    if os.environ.get("OPENAI_API_KEY"):
        try:
            text = transcribe_openai(wav_path, args.language)
            transcript_lines = markdown_header(audio_path, converted, "openai whisper-1", args.language)
            transcript_lines.append(text)
            out_path.write_text("\n".join(transcript_lines).strip() + "\n", encoding="utf-8")
            print(out_path)
            return 0
        except Exception as exc:
            print(f"OpenAI transcription failed, falling back locally: {exc}", file=sys.stderr)

    if shutil.which("whisper"):
        try:
            text = transcribe_whisper_cli(wav_path, args.out_dir, args.language)
            transcript_lines = markdown_header(audio_path, converted, "whisper CLI", args.language)
            transcript_lines.append(text)
            out_path.write_text("\n".join(transcript_lines).strip() + "\n", encoding="utf-8")
            print(out_path)
            return 0
        except Exception as exc:
            print(f"whisper CLI transcription failed, trying faster_whisper: {exc}", file=sys.stderr)

    try:
        body, runtime = transcribe_faster_whisper(
            wav_path, args.language, args.model, args.device, args.compute_type
        )
        transcript_lines = markdown_header(
            audio_path, converted, f"faster-whisper {args.model} ({runtime})", args.language
        )
        transcript_lines.extend(body)
        out_path.write_text("\n".join(transcript_lines).strip() + "\n", encoding="utf-8")
        print(out_path)
        return 0
    except Exception as exc:
        write_limitation(out_path, audio_path, str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
