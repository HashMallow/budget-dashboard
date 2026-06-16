---
name: audio-transcription
description: Transcribe spoken audio notes and extract concise summaries or requirements. Use when Codex is asked to work with audio files such as .ogg, .oga, .mp3, .m4a, or .wav; when Telegram voice/audio drafts need transcription; or as step 2 after the telegram-bot-pipeline skill syncs new messages. Prefer process_audio_queue.py for Telegram drafts; use transcribe_audio.py for individual files.
---

# Audio Transcription

Use this skill when an audio file is an input artifact and the user needs a transcript, summary, requirements, or a written record.

## Workflow

1. Locate audio files if the user did not provide an explicit path:
   - Search `.artifacts/audio/`, `.artifacts/voice-feedback/audio/`, `.artifacts/telegram-bot/voice/`, `.artifacts/telegram-bot/audio/`, then `data/`, `imports/`, and `docs/`.
   - If multiple likely files exist and the intended one is unclear, ask for the path.
2. Create the requested output directory. Use `docs/discovery/` when this is part of project discovery.
   For follow-up voice notes in this repo, prefer:

```text
.artifacts/audio/                      Telegram / bulk voice drops (also searched)
.artifacts/voice-feedback/audio/       older source .ogg files
.artifacts/voice-feedback/converted/   ffmpeg WAV output
.artifacts/voice-feedback/transcripts/ markdown transcripts
```

For Telegram-ingested audio, prefer:

```text
.artifacts/telegram-bot/voice/         native voice notes (.ogg)
.artifacts/telegram-bot/audio/         forwarded/sent audio files
.artifacts/telegram-bot/wav/           ffmpeg-converted WAV
.artifacts/telegram-bot/transcripts/   transcription output
```

3. Convert `.ogg` or `.oga` to `.wav` with `ffmpeg` before transcription.
4. **Backend priority** (implemented in `transcribe_audio.py`; do not skip steps):

| Order | Backend | When | Default model (`--model auto`) |
|------:|---------|------|----------------------------------|
| 1 | **OpenAI** `whisper-1` | `OPENAI_API_KEY` is set | n/a (API) |
| 2 | **mlx-whisper** | macOS (`darwin`) + `mlx-whisper` installed | `large-v3` |
| 3 | **faster-whisper + CUDA** | CUDA available | `large-v3` (`float16`, batched) |
| 4 | **whisper CLI** | `whisper` on `PATH` (legacy optional) | CLI default |
| 5 | **faster-whisper + CPU** | nothing above succeeded | `small` (`int8`) |

   On **Mac**, mlx runs before CUDA (most Macs have no CUDA). On **Linux + GPU**, OpenAI is tried first, then CUDA `large-v3`, then CPU.

   Do not print or commit API keys. Override with `--model large-v3` (or `medium` / `small`) when you need a fixed size on every backend.

5. If a `large-v3` load fails (OOM, missing libs), the script downgrades: `large-v3 → medium → small → base`, then may fall through to the next backend in the table above.
6. If no backend succeeds, write a limitation markdown file and continue with any written requirements available.
7. Preserve the source language in the transcript. Mark unclear audio as `[unclear]`; do not invent missing words.
8. When requested, add an English summary and structured requirements file.

## Telegram Queue Worker (Phase 2a)

When the user mentions new Telegram requests, the **telegram-bot-pipeline** skill runs first (`fetch_requests.py`), which calls this worker automatically. You can also run it directly:

When audio arrives via the Telegram bot pipeline, use the standalone queue worker instead of transcribing files one-by-one:

```bash
# Process all pending audio drafts once
python skills/audio-transcription/scripts/process_audio_queue.py

# Watch for new drafts every 60 seconds
python skills/audio-transcription/scripts/process_audio_queue.py --watch 60

# Preview pending drafts
python skills/audio-transcription/scripts/process_audio_queue.py --dry-run

# Specify language (e.g. Persian)
python skills/audio-transcription/scripts/process_audio_queue.py --language fa
```

The worker:
1. Scans `docs/discovery/requests/drafts/` for drafts with `status: pending` and `type: voice|audio`
2. Reads `audio_file` from YAML frontmatter (not freeform body text)
3. Runs `transcribe_audio.py` on each file
4. Writes transcripts to `.artifacts/telegram-bot/transcripts/`
5. Updates drafts to `status: transcribed` with the transcript embedded

This runs **completely independently** of the Telegram bot. Schedule it via cron, run on demand, or use `--watch`.

## Output Files

For this project, save voice-derived English instructions under **`docs/voice-feedback/`** (git-tracked):

```text
docs/voice-feedback/PROCESSING_LOG.en.md         verification + fixes + backlog
docs/voice-feedback/USER_REQUESTS.en.md          main topics (agents read first)
docs/voice-feedback/README.md
.artifacts/voice-feedback/transcripts/{stem}_transcript.fa.md   Persian (local)
.artifacts/voice-feedback/converted/            ffmpeg WAV (local)
```

After batch transcription, update **`PROCESSING_LOG.en.md`** with results.

## Script

### First-time setup

The script auto-detects your environment (conda, virtualenv, or system Python) and installs
`faster-whisper` into it. It never hardcodes a CUDA version — it piggybacks on whatever
`torch + CUDA` stack you already have configured.

```bash
# Check what environment is detected (conda env, CUDA version, GPU, VRAM):
python skills/audio-transcription/scripts/transcribe_audio.py --env-info

# One-time install of faster-whisper into your current env:
python skills/audio-transcription/scripts/transcribe_audio.py --setup
```

On your **conda system** with torch already installed, activate the env first (this project uses **`ml-env`**):

```bash
conda activate ml-env
python .agents/skills/audio-transcription/scripts/transcribe_audio.py --setup

# Batch all .artifacts audio (26 files):
PYTHONUNBUFFERED=1 python tools/batch_transcribe_artifacts.py
```

This runs `pip install faster-whisper` inside your conda env, reusing the existing
torch + CUDA 12.8 (or whatever version is present). No CUDA wheels are downloaded.

### Transcription

After setup, transcribe directly from the activated environment (`--model auto` is the default):

```bash
python .agents/skills/audio-transcription/scripts/transcribe_audio.py path/to/audio.ogg --out-dir docs/discovery --language fa
```

**Recommended shortcuts (this repo):**

```bash
# Best quality on NVIDIA GPU (large-v3, CUDA) — works without torch if ctranslate2 + nvidia-smi see the GPU:
make transcribe-audio-high AUDIO=.artifacts/audio/voice_....ogg \
  TRANSCRIPT_OUT=.artifacts/voice-feedback/transcripts \
  TRANSCRIPT_WAV_DIR=.artifacts/voice-feedback/converted \
  TRANSCRIPT_OUTPUT_NAME=voice_...._transcript.fa.md

# Shorthand when audio is under voice-feedback/audio/:
make transcribe-voice AUDIO=.artifacts/voice-feedback/audio/note.ogg

# Apple Silicon (mlx-whisper large-v3):
make transcribe-audio-mac AUDIO=path/to/audio.ogg TRANSCRIPT_MODEL=large-v3

# OpenAI (set OPENAI_API_KEY first):
make transcribe-audio AUDIO=path/to/audio.ogg TRANSCRIPT_PACKAGES="--with openai"
```

On Mac without conda, you can still use the `uv` wrapper:

```bash
uv run --with mlx-whisper .agents/skills/audio-transcription/scripts/transcribe_audio.py path/to/audio.ogg
```

### Backend priority and `--model auto`

See the table in **Workflow** above. Summary:

- **OpenAI first** when `OPENAI_API_KEY` is set.
- **mlx `large-v3`** on macOS before any local CUDA attempt.
- **CUDA `large-v3`** on Linux/Windows when a GPU is available (`float16`, batch 16).
- **CPU `small`** only as the last local fallback.

### Model fallback chain (OOM only)

If `large-v3` cannot load on mlx or CUDA, the script downgrades within that backend:

```
large-v3 → medium → small → base
```

Then it tries the next backend in the priority table (e.g. CUDA → CPU).

You can force a smaller model to save VRAM or time:

```bash
# Force medium (less VRAM, still decent for Persian):
python .agents/skills/audio-transcription/scripts/transcribe_audio.py audio.wav --model medium

# Force small (CPU-friendly):
python .agents/skills/audio-transcription/scripts/transcribe_audio.py audio.wav --model small --device cpu
```

Model accuracy order: `tiny` < `base` < `small` < `medium` < `large-v3`. For Persian voice notes,
prefer **`large-v3`** via OpenAI, mlx, or CUDA; avoid `small`/`tiny` unless CPU is the only option.
Models download once into `docs/discovery/faster-whisper-models/` (gitignored). Override with `WHISPER_DOWNLOAD_ROOT`.

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
- Tries backends in order: **OpenAI → mlx (macOS) → CUDA large-v3 → whisper CLI → CPU**.
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
