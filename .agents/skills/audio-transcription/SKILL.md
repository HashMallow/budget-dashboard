---
name: audio-transcription
description: Transcribe spoken audio notes and extract concise summaries or requirements. Use when Codex is asked to work with audio files such as .ogg, .oga, .mp3, .m4a, or .wav; convert audio formats; prefer OpenAI speech-to-text when OPENAI_API_KEY is available; fall back to local Whisper/faster-whisper; save transcripts and derived notes as markdown.
---

# Audio Transcription

Use this skill when an audio file is an input artifact and the user needs a transcript, summary, requirements, or a written record.

## Workflow

1. Locate audio files if the user did not provide an explicit path:
   - Search the current directory, `data/`, `imports/`, `docs/`, and `.artifacts/voice-feedback/audio/`.
   - If multiple likely files exist and the intended one is unclear, ask for the path.
2. Create the requested output directory. Use `docs/discovery/` when this is part of project discovery.
   For follow-up voice notes in this repo, prefer:

```text
.artifacts/voice-feedback/audio/       source .ogg files
.artifacts/voice-feedback/converted/   ffmpeg WAV output
.artifacts/voice-feedback/transcripts/ markdown transcripts
```

Use `make transcribe-voice` for that layout.
3. Convert `.ogg` or `.oga` to `.wav` with `ffmpeg` before transcription.
4. Prefer OpenAI speech-to-text if `OPENAI_API_KEY` is available. Do not print or commit API keys.
5. If OpenAI is unavailable, use local `whisper` CLI if installed.
6. If `whisper` CLI is unavailable, use Python `faster_whisper` if installed. Downloading a model may require user approval.
7. If no speech-to-text tool is available, write a transcript file documenting the limitation, then continue with any written requirements available.
8. Preserve the source language in the transcript. Mark unclear audio as `[unclear]`; do not invent missing words.
9. When requested, add an English summary and structured requirements file.

## Output Files

For discovery work, use these names unless the user asks otherwise:

```text
docs/discovery/audio_transcript.fa.md
docs/discovery/audio_summary.en.md
docs/discovery/audio_requirements.en.md
```

For non-Persian audio, adjust the language suffix, for example `audio_transcript.en.md`.

## Script

Prefer the bundled helper when a direct command is useful:

```bash
python .agents/skills/audio-transcription/scripts/transcribe_audio.py path/to/audio.ogg --out-dir docs/discovery --language fa
```

In this repository, prefer the Make/uv wrapper so transcription packages remain optional tooling
instead of app dependencies:

```bash
# Discovery output (docs/discovery/):
make transcribe-audio AUDIO=path/to/audio.ogg

# Voice-feedback layout (.artifacts/voice-feedback/):
make transcribe-voice AUDIO=.artifacts/voice-feedback/audio/note.ogg
```

Equivalent direct command:

```bash
UV_CONFIG_FILE=uv.toml UV_CACHE_DIR=.uv-cache uv run --with faster-whisper python .agents/skills/audio-transcription/scripts/transcribe_audio.py path/to/audio.ogg --out-dir docs/discovery --language fa --model small
```

### GPU and high-accuracy transcription

The script auto-detects CUDA: with `--device auto` (the default) it uses the GPU when a CUDA
device is present and falls back to CPU otherwise. `--compute-type auto` picks `float16` on GPU
and `int8` on CPU. If GPU init fails (missing cuDNN/cuBLAS runtime), it logs and falls back to CPU.

On this machine, system CUDA libraries (`/usr/local/cuda`) are usually enough — the Makefile does
**not** download the heavy `nvidia-cublas-cu12` / `nvidia-cudnn-cu12` wheels by default. If GPU
init fails, set:

```bash
TRANSCRIPT_GPU_PACKAGES="--with faster-whisper --with nvidia-cublas-cu12 --with nvidia-cudnn-cu12"
```

```bash
# Auto (GPU when available):
make transcribe-audio AUDIO=path/to/audio.ogg

# Force GPU, optionally with a bigger model:
make transcribe-audio-gpu AUDIO=path/to/audio.ogg TRANSCRIPT_MODEL=medium

# Highest accuracy: large-v3 on the GPU (~3 GB VRAM in float16):
make transcribe-audio-high AUDIO=path/to/audio.ogg
```

Model accuracy order: `tiny` < `base` < `small` < `medium` < `large-v3`. For Persian voice notes,
use at least **`medium`**; `small`/`tiny` are often phonetically garbled. Models download once
into `docs/discovery/faster-whisper-models/` (gitignored). Override with `WHISPER_DOWNLOAD_ROOT`.

**Download stalls:** Hugging Face model downloads can be very slow without `HF_TOKEN`. If a run
appears stuck at 0 bytes, check network speed to `huggingface.co` / `cas-bridge.xethub.hf.co`.
Use `medium` first (smaller download), or set `HF_TOKEN` for higher rate limits.

If `OPENAI_API_KEY` is set and you want OpenAI speech-to-text through the helper, include the
OpenAI package for that run:

```bash
make transcribe-audio AUDIO=path/to/audio.ogg TRANSCRIPT_PACKAGES="--with openai --with faster-whisper"
```

If you intentionally want a persistent local-only install inside `.venv`, install it with `uv pip`
and do not add it to `pyproject.toml` unless transcription becomes part of the app runtime.

The script:

- Converts `.ogg`/`.oga` to WAV with `ffmpeg` (quiet; use `--wav-dir` to separate WAV from transcript output).
- Uses OpenAI speech-to-text when `OPENAI_API_KEY` is available.
- Falls back to `whisper` CLI, then `faster_whisper`.
- Writes a markdown transcript with timestamps.
- Caches models under `docs/discovery/faster-whisper-models/` (or `WHISPER_DOWNLOAD_ROOT`).

Review the transcript after generation. Local Whisper output can contain phonetic mistakes, especially for Persian names, mixed English/Persian business terms, and noisy mobile voice notes.

## Requirements Extraction

When deriving requirements from a transcript:

- Separate exact transcript from interpretation.
- Keep the source-language transcript in its own file.
- Write summaries and requirements in English unless the user asks otherwise.
- Include open questions for ambiguous phrases, missing context, or low-confidence sections.
- Cross-check audio-derived requirements against any written product docs before implementation.
