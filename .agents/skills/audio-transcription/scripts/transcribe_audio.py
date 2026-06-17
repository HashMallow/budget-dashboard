#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


AUDIO_EXTENSIONS = {".ogg", ".oga", ".mp3", ".m4a", ".wav", ".webm", ".opus", ".flac"}

# Model downgrade chain: try the best model first, fall back on OOM or failure
MODEL_FALLBACK_CHAIN = ["large-v3", "medium", "small", "base"]

# Backend selection: which transcription path is allowed to run.
#   local  → never call cloud APIs (recommended for scheduled/cron runs)
#   openai → only the OpenAI API; fail clearly if SDK/key is missing
#   auto   → use OpenAI when OPENAI_API_KEY is set, otherwise fall back to local
VALID_BACKENDS = {"local", "openai", "auto"}


def _resolve_backend(cli_backend: str | None) -> str:
    """Resolve the effective backend. CLI flag wins, then TRANSCRIPTION_BACKEND, then 'auto'."""
    if cli_backend:
        return cli_backend.strip().lower()
    env_backend = os.environ.get("TRANSCRIPTION_BACKEND")
    if env_backend:
        return env_backend.strip().lower()
    return "auto"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def markdown_header(
    source: Path,
    wav_path: Path | None,
    tool: str,
    language: str | None,
    confidence: str | None = None,
) -> list[str]:
    lines = [
        "# Audio Transcript",
        "",
        f"Source audio: `{source}`",
    ]
    if wav_path is not None:
        lines.append(f"Converted WAV: `{wav_path}`")
    lines.append(f"Transcription tool: `{tool}`")
    if confidence:
        lines.append(f"Confidence: `{confidence}`")
    lines.extend(
        [
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


# ---------------------------------------------------------------------------
# Environment detection — conda, venv, system python, CUDA (version-agnostic)
# ---------------------------------------------------------------------------

def _detect_conda_env() -> str | None:
    """Return the name of the active conda environment, or None."""
    return os.environ.get("CONDA_DEFAULT_ENV")


def _detect_python_env() -> dict:
    """Detect the current Python runtime environment without hardcoding any CUDA version."""
    info: dict = {
        "python": sys.executable,
        "platform": sys.platform,
        "conda_env": _detect_conda_env(),
        "venv": os.environ.get("VIRTUAL_ENV"),
        "cuda_available": False,
        "cuda_version": None,
        "gpu_name": None,
        "vram_gb": 0.0,
    }
    # Probe torch — works regardless of how it was installed (conda, pip, system)
    try:
        import torch
        info["cuda_available"] = torch.cuda.is_available()
        if info["cuda_available"]:
            info["cuda_version"] = torch.version.cuda  # e.g. "12.8", never hardcoded
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["vram_gb"] = torch.cuda.get_device_properties(0).total_mem / (1024 ** 3)
    except Exception:
        pass
    # Fallback: ctranslate2 can also detect CUDA without torch
    if not info["cuda_available"]:
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                info["cuda_available"] = True
        except Exception:
            pass
    return info


def _print_env_info(info: dict) -> None:
    """Print a human-readable diagnostic of the detected environment."""
    print("─── Environment ───", file=sys.stderr)
    if info["conda_env"]:
        print(f"  Conda env:    {info['conda_env']}", file=sys.stderr)
    elif info["venv"]:
        print(f"  Virtualenv:   {info['venv']}", file=sys.stderr)
    else:
        print(f"  Python:       {info['python']}", file=sys.stderr)
    if info["cuda_available"]:
        print(f"  CUDA:         {info['cuda_version'] or 'detected (version unknown)'}", file=sys.stderr)
        print(f"  GPU:          {info['gpu_name'] or 'unknown'}", file=sys.stderr)
        print(f"  VRAM:         {info['vram_gb']:.1f} GB", file=sys.stderr)
    elif info["platform"] == "darwin":
        print("  Accelerator:  Apple Silicon (mlx-whisper)", file=sys.stderr)
    else:
        print("  Accelerator:  CPU only", file=sys.stderr)
    print("───────────────────", file=sys.stderr)


def _setup_dependencies() -> int:
    """One-time setup: install faster-whisper into the current environment.
    Detects conda vs pip and uses the right installer. Never hardcodes CUDA versions —
    assumes the environment already has the correct torch+CUDA stack."""
    info = _detect_python_env()
    _print_env_info(info)

    packages = ["faster-whisper"]
    if info["platform"] == "darwin":
        packages.append("mlx-whisper")

    if info["conda_env"]:
        print(f"Installing into conda env '{info['conda_env']}'...", file=sys.stderr)
        # Use pip inside the conda env (faster-whisper is pip-only)
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + packages
    elif info["venv"]:
        print(f"Installing into virtualenv '{info['venv']}'...", file=sys.stderr)
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + packages
    else:
        print("No conda/venv detected. Installing via pip for current Python...", file=sys.stderr)
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + packages

    print(f"  Running: {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("✓ Dependencies installed successfully.", file=sys.stderr)
    else:
        print("✗ Installation failed. Check the output above.", file=sys.stderr)
    return result.returncode


# ---------------------------------------------------------------------------
# CUDA / device helpers (version-agnostic)
# ---------------------------------------------------------------------------

def _cuda_available() -> bool:
    """Detect CUDA without hardcoding any version."""
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        pass
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def _gpu_vram_gb() -> float:
    """Return total VRAM in GB for the first CUDA device, or 0 if unavailable."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_mem / (1024 ** 3)
    except Exception:
        pass
    return 0.0


def _resolve_device(device: str) -> str:
    if device == "auto":
        return "cuda" if _cuda_available() else "cpu"
    return device


def _resolve_compute_type(compute_type: str, device: str) -> str:
    if compute_type != "auto":
        return compute_type
    return "float16" if device == "cuda" else "int8"


def _auto_model(model: str, device: str) -> str:
    """When model is 'auto', pick the best model based on available VRAM."""
    if model != "auto":
        return model
    if device == "cuda":
        vram = _gpu_vram_gb()
        if vram >= 10 or vram == 0.0:
            return "large-v3"     # ~3 GB in float16, easily fits 10+ GB VRAM. 0.0 handles cases where torch is unavailable but CUDA works via ctranslate2.
        elif vram >= 5:
            return "medium"
        else:
            return "small"
    elif sys.platform == "darwin":
        return "large-v3"         # Apple Silicon unified memory handles this well
    else:
        return "small"            # CPU fallback, keep it light


def _model_fallback_chain(starting_model: str) -> list[str]:
    """Return a list of models to try, starting from the given model and going smaller."""
    if starting_model in MODEL_FALLBACK_CHAIN:
        idx = MODEL_FALLBACK_CHAIN.index(starting_model)
        return MODEL_FALLBACK_CHAIN[idx:]
    return [starting_model]  # unknown model, no fallback


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
    batch_size: int = 0,
) -> tuple[list[str], str]:
    resolved_device = _resolve_device(device)
    resolved_compute = _resolve_compute_type(compute_type, resolved_device)
    starting_model = _auto_model(model, resolved_device)

    # Use batched inference on GPU for massive speedup (requires faster-whisper >= 1.0)
    use_batched = batch_size > 0 or (resolved_device == "cuda" and batch_size == 0)
    effective_batch = batch_size if batch_size > 0 else 16  # default batch on GPU

    if use_batched:
        try:
            from faster_whisper import BatchedInferencePipeline, WhisperModel
        except ImportError:
            from faster_whisper import WhisperModel
            use_batched = False
    else:
        from faster_whisper import WhisperModel

    def _load(model_name: str, dev: str, compute: str) -> tuple:
        download_root = _model_download_root()
        Path(download_root).mkdir(parents=True, exist_ok=True)
        whisper_model = WhisperModel(
            model_name, device=dev, compute_type=compute, download_root=download_root
        )
        if use_batched:
            pipeline = BatchedInferencePipeline(model=whisper_model)
            return pipeline, model_name, dev, compute, True
        return whisper_model, model_name, dev, compute, False

    # Try loading with automatic model downgrade on failure (OOM, missing libs, etc.)
    engine = None
    resolved_model = starting_model
    is_batched = False
    for try_model in _model_fallback_chain(starting_model):
        try:
            engine, resolved_model, resolved_device, resolved_compute, is_batched = _load(
                try_model, resolved_device, resolved_compute
            )
            break
        except Exception as exc:
            err_str = str(exc).lower()
            is_oom = "out of memory" in err_str or "oom" in err_str or "cuda" in err_str
            if is_oom and try_model != MODEL_FALLBACK_CHAIN[-1]:
                print(f"Model '{try_model}' failed ({exc}); downgrading...", file=sys.stderr)
                continue
            elif resolved_device == "cuda":
                print(f"CUDA init failed ({exc}); falling back to CPU.", file=sys.stderr)
                try:
                    engine, resolved_model, resolved_device, resolved_compute, is_batched = _load(
                        try_model, "cpu", "int8"
                    )
                    break
                except Exception:
                    continue
            else:
                raise

    if engine is None:
        raise RuntimeError("All models in the fallback chain failed.")

    if resolved_model != starting_model:
        print(f"Using downgraded model: {resolved_model} (requested: {starting_model})", file=sys.stderr)

    # GPU: higher beam_size for accuracy; batched mode for throughput
    beam = 5 if resolved_device != "cuda" else 7
    transcribe_kwargs = dict(language=language, vad_filter=True, beam_size=beam)
    if is_batched:
        transcribe_kwargs["batch_size"] = effective_batch

    segments, info = engine.transcribe(str(audio_path), **transcribe_kwargs)
    runtime_label = f"{resolved_device}/{resolved_compute}"
    if is_batched:
        runtime_label += f" batch={effective_batch}"

    lines = [
        f"Detected language: `{info.language}` probability `{info.language_probability:.2f}`",
        f"Model: `{resolved_model}` Runtime: `{runtime_label}`",
        "",
    ]

    try:
        from tqdm import tqdm
        total_dur = info.duration
        pbar = tqdm(total=total_dur, unit="s", desc=f"Transcribing {audio_path.name}", bar_format="{l_bar}{bar}| {n:.1f}/{total:.1f}s [{elapsed}<{remaining}]")
    except ImportError:
        pbar = None

    for segment in segments:
        text = segment.text.strip()
        if text:
            lines.append(f"[{segment.start:06.2f}-{segment.end:06.2f}] {text}")
        if pbar:
            pbar.update(segment.end - pbar.n)
            
    if pbar:
        pbar.close()

    return lines, runtime_label


def transcribe_mlx_whisper(
    audio_path: Path,
    language: str | None,
    model: str,
) -> tuple[list[str], str]:
    import mlx_whisper

    if not model.startswith("mlx-community/"):
        model_repo = f"mlx-community/whisper-{model}-mlx"
    else:
        model_repo = model

    kwargs = {}
    if language:
        kwargs["language"] = language

    result = mlx_whisper.transcribe(str(audio_path), path_or_hf_repo=model_repo, **kwargs)

    detected_lang = result.get("language", language or "auto")
    lines = [f"Detected language: `{detected_lang}`", ""]
    for segment in result.get("segments", []):
        text = segment.get("text", "").strip()
        if text:
            start = segment.get("start", 0.0)
            end = segment.get("end", 0.0)
            lines.append(f"[{start:06.2f}-{end:06.2f}] {text}")

    return lines, "mlx-whisper (Apple GPU)"


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
    parser.add_argument("audio", nargs="?", type=Path, default=None,
                        help="Audio file to transcribe. Not required when using --setup or --env-info.")
    parser.add_argument("--out-dir", type=Path, default=Path("docs/discovery"))
    parser.add_argument(
        "--backend",
        default=None,
        choices=["local", "openai", "auto"],
        help="Which transcription path to allow. 'local' never calls cloud APIs "
             "(recommended for scheduled runs); 'openai' requires OPENAI_API_KEY and the "
             "openai SDK; 'auto' uses OpenAI when a key is present, else local. "
             "Falls back to the TRANSCRIPTION_BACKEND env var, then 'auto'.",
    )
    parser.add_argument("--language", default=None, help="Language code such as fa or en. Omit for auto-detect.")
    parser.add_argument("--model", default="auto",
                        help="Whisper model name. 'auto' picks the best model for your hardware. "
                             "Options: large-v3, medium, small, base, tiny, or auto.")
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
    parser.add_argument(
        "--batch-size",
        type=int,
        default=0,
        help="Batch size for GPU batched inference (0 = auto: 16 on GPU, disabled on CPU).",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="One-time setup: detect the environment (conda/venv) and install faster-whisper "
             "into it. Does not hardcode any CUDA version — uses whatever torch+CUDA is already present.",
    )
    parser.add_argument(
        "--env-info",
        action="store_true",
        help="Print detected environment info (conda env, CUDA version, GPU, VRAM) and exit.",
    )
    args = parser.parse_args()

    # Handle --env-info: just print diagnostics and exit
    if args.env_info:
        info = _detect_python_env()
        _print_env_info(info)
        return 0

    # Handle --setup: install dependencies into the detected environment
    if args.setup:
        return _setup_dependencies()

    if args.audio is None:
        parser.error("the following arguments are required: audio (or use --setup / --env-info)")
    # Always print environment info at the start of a transcription run
    info = _detect_python_env()
    _print_env_info(info)

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
    backend = _resolve_backend(args.backend)
    if backend not in VALID_BACKENDS:
        print(f"Invalid backend '{backend}'. Choose one of: {', '.join(sorted(VALID_BACKENDS))}", file=sys.stderr)
        return 2
    print(f"Transcription backend: {backend}", file=sys.stderr)

    # --- OpenAI-only backend: must succeed via OpenAI or fail clearly (no local fallback) ---
    if backend == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            reason = "backend=openai but OPENAI_API_KEY is not set."
            print(reason, file=sys.stderr)
            write_limitation(out_path, audio_path, reason)
            return 2
        try:
            text = transcribe_openai(wav_path, args.language)
        except ImportError as exc:
            reason = f"backend=openai but the openai SDK is not installed: {exc}"
            print(reason, file=sys.stderr)
            write_limitation(out_path, audio_path, reason)
            return 2
        except Exception as exc:
            reason = f"backend=openai transcription failed: {exc}"
            print(reason, file=sys.stderr)
            write_limitation(out_path, audio_path, reason)
            return 1
        transcript_lines = markdown_header(audio_path, converted, "openai whisper-1", args.language, "high")
        transcript_lines.append(text)
        out_path.write_text("\n".join(transcript_lines).strip() + "\n", encoding="utf-8")
        print(out_path)
        return 0

    # --- auto backend: try OpenAI first when a key exists, then fall back locally ---
    if backend == "auto" and os.environ.get("OPENAI_API_KEY"):
        try:
            text = transcribe_openai(wav_path, args.language)
            transcript_lines = markdown_header(audio_path, converted, "openai whisper-1", args.language, "high")
            transcript_lines.append(text)
            out_path.write_text("\n".join(transcript_lines).strip() + "\n", encoding="utf-8")
            print(out_path)
            return 0
        except Exception as exc:
            print(f"OpenAI transcription failed, falling back locally: {exc}", file=sys.stderr)

    # --- Local chain (backend == 'local' or 'auto' without/after OpenAI) ---
    # Prioritize CUDA GPU over mlx-whisper — a 16 GB VRAM GPU with large-v3 in float16
    # is significantly faster than Apple Silicon unified memory.
    if _cuda_available():
        try:
            resolved_model = _auto_model(args.model, "cuda")
            print(f"CUDA detected ({_gpu_vram_gb():.1f} GB VRAM). Using model: {resolved_model}", file=sys.stderr)
            body, runtime = transcribe_faster_whisper(
                wav_path, args.language, args.model, args.device, args.compute_type, args.batch_size
            )
            confidence = "medium" if runtime.startswith("cuda") else "low-medium"
            transcript_lines = markdown_header(
                audio_path, converted, f"faster-whisper ({runtime})", args.language, confidence
            )
            transcript_lines.extend(body)
            out_path.write_text("\n".join(transcript_lines).strip() + "\n", encoding="utf-8")
            print(out_path)
            return 0
        except Exception as exc:
            print(f"CUDA transcription failed, trying fallbacks: {exc}", file=sys.stderr)

    if sys.platform == "darwin":
        try:
            import mlx_whisper  # Test if available
            resolved_model = _auto_model(args.model, "mlx")
            body, runtime = transcribe_mlx_whisper(wav_path, args.language, resolved_model)
            transcript_lines = markdown_header(
                audio_path, converted, f"mlx-whisper {resolved_model} ({runtime})", args.language, "medium"
            )
            transcript_lines.extend(body)
            out_path.write_text("\n".join(transcript_lines).strip() + "\n", encoding="utf-8")
            print(out_path)
            return 0
        except ImportError:
            print("mlx-whisper not installed; falling back to faster_whisper.", file=sys.stderr)
        except Exception as exc:
            print(f"mlx-whisper transcription failed, trying faster_whisper: {exc}", file=sys.stderr)

    if shutil.which("whisper"):
        try:
            text = transcribe_whisper_cli(wav_path, args.out_dir, args.language)
            transcript_lines = markdown_header(audio_path, converted, "whisper CLI", args.language, "medium")
            transcript_lines.append(text)
            out_path.write_text("\n".join(transcript_lines).strip() + "\n", encoding="utf-8")
            print(out_path)
            return 0
        except Exception as exc:
            print(f"whisper CLI transcription failed, trying faster_whisper: {exc}", file=sys.stderr)

    try:
        body, runtime = transcribe_faster_whisper(
            wav_path, args.language, args.model, args.device, args.compute_type, args.batch_size
        )
        confidence = "medium" if runtime.startswith("cuda") else "low-medium"
        transcript_lines = markdown_header(
            audio_path, converted, f"faster-whisper ({runtime})", args.language, confidence
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
