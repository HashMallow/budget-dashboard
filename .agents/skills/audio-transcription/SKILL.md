---
name: audio-transcription
description: Transcribe spoken audio notes and extract concise summaries or requirements. Use when Codex is asked to work with audio files such as .ogg, .oga, .mp3, .m4a, or .wav; when Telegram voice/audio drafts need transcription; or as step 2 after the telegram-bot-pipeline skill syncs new messages. Prefer process_audio_queue.py for Telegram drafts; use transcribe_audio.py for individual files.
---

# Audio Transcription

Use this skill when an audio file is an input artifact and the user needs a transcript, summary, requirements, or a written record.

## Workflow

1. Locate audio files if the user did not provide an explicit path:
   - Search the current directory, `data/`, `imports/`, `docs/`, `.artifacts/telegram-bot/`, and `.artifacts/voice-feedback/audio/`.
   - If multiple likely files exist and the intended one is unclear, ask for the path.
2. Create the requested output directory. Use `docs/discovery/` when this is part of project discovery.
   For follow-up voice notes in this repo, prefer:

```text
.artifacts/voice-feedback/audio/       source .ogg files
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
4. Choose a **backend** explicitly (`--backend local|openai|auto`, or the
   `TRANSCRIPTION_BACKEND` env var). Do not print or commit API keys.
   - `local` — never calls cloud APIs. **Use this for scheduled/cron runs.**
   - `openai` — only the OpenAI API; fails clearly (exit 2) if the key/SDK is missing
     instead of silently falling back.
   - `auto` (default) — uses OpenAI when `OPENAI_API_KEY` is set, otherwise local.
5. For the local chain, the script auto-detects hardware and picks the best path
   (fallback order: **CUDA GPU → Apple Silicon (mlx) → whisper CLI → CPU**):
   - **CUDA GPU (prioritized):** Uses `faster-whisper` with batched inference for massive speedup.
     With 16 GB VRAM, it defaults to `large-v3` in `float16` with batch size 16.
   - **macOS (Apple Silicon):** Uses `mlx-whisper` with `large-v3` via Apple GPU acceleration.
   - **CPU fallback:** Uses `faster-whisper` with `small` model in `int8`.
6. The `--model auto` flag (now the default) auto-selects the best model for your hardware:
   - `large-v3` for ≥10 GB VRAM or Apple Silicon
   - `medium` for ≥5 GB VRAM
   - `small` for CPU
7. If no speech-to-text tool is available, write a transcript file documenting the limitation, then continue with any written requirements available.
8. Preserve the source language in the transcript. Mark unclear audio as `[unclear]`; do not invent missing words.
9. When requested, add an English summary and structured requirements file.

## Telegram Queue Worker (Phase 2a)

When the user mentions new Telegram requests, the **telegram-bot-pipeline** skill runs first (`fetch_requests.py`), which calls this worker automatically. You can also run it directly:

When audio arrives via the Telegram bot pipeline, use the standalone queue worker instead of transcribing files one-by-one:

```bash
# Process all pending audio drafts once
python skills/audio-transcription/scripts/process_audio_queue.py

# Scheduled-safe: local only, capped work
python skills/audio-transcription/scripts/process_audio_queue.py --backend local --max-items 20

# Preview pending drafts (no work, no API calls)
python skills/audio-transcription/scripts/process_audio_queue.py --dry-run

# Specify language (e.g. Persian)
python skills/audio-transcription/scripts/process_audio_queue.py --language fa

# Watch for new drafts every 60 seconds (interactive use only — see note below)
python skills/audio-transcription/scripts/process_audio_queue.py --watch 60
```

The worker:
1. Scans `docs/discovery/requests/drafts/` for drafts with `status: pending` and `type: voice|audio`
2. Reads `audio_file` from YAML frontmatter (falls back to a legacy body line)
3. Runs `transcribe_audio.py` on each file, forwarding `--backend`/`--model`/`--language`
4. Writes the transcript **into the message's own folder** as `transcript.md`
   (`.artifacts/telegram-bot/messages/<stem>/transcript.md`), next to its `audio.wav`.
   Legacy drafts without a `message_dir` fall back to `.artifacts/telegram-bot/transcripts/`.
5. The transcript gets frontmatter + relative backlinks to its audio and draft, so you can
   open it and verify it matches the recording.
6. On success → `status: transcribed` (+ `transcript_file`, `confidence`, `processed_at`)
7. On failure → `status: failed` (+ `error`, `processed_at`); the original body is preserved
8. Rebuilds `docs/discovery/requests/INDEX.md` — a single table linking every draft to its
   transcript and audio (skip with `--no-index`; build only with `--index`).

This runs **completely independently** of the Telegram bot. Schedule it, run on demand, or use `--watch`.

### Navigating transcripts

- **Start at `docs/discovery/requests/INDEX.md`** — one row per message with links to the
  draft, transcript, and audio, plus status and confidence.
- Each message folder (`.artifacts/telegram-bot/messages/<stem>/`) holds the `source.*`,
  `audio.wav`, and `transcript.md` together.
- Rebuild the index any time without transcribing:
  `python skills/audio-transcription/scripts/process_audio_queue.py --index`

### Periodic cleanup

```bash
make clean-runtime   # remove artifacts + active drafts (keeps drafts/processed/)
make clean-all       # full wipe including model cache — see Makefile `make help`
```

### Safety controls (budget + idempotency)

| Flag | Purpose |
|---|---|
| `--backend local\|openai\|auto` | Control/avoid cloud spend. Defaults to `TRANSCRIPTION_BACKEND` then `auto`. |
| `--max-items N` | Process at most N drafts this run. |
| `--max-runtime-seconds S` | Stop starting new drafts after S seconds. |
| `--max-audio-minutes M` | Skip audio longer than M minutes (needs `ffprobe`). |
| `--dry-run` | List what would be processed; never spends or mutates. |
| `--force` | Steal an existing lock you are sure is dead. |

**Locking / idempotency:** the worker takes a lock at `.artifacts/telegram-bot/queue.lock`
so two runs never process the same drafts concurrently (a second run exits with code 3).
The lock is removed on normal exit. A lock is considered **stale** — and stolen
automatically — if its PID is dead or it is older than 1 hour. Terminal statuses
(`transcribed`, `failed`, `processed`) are never reprocessed, so the worker is safe to run
twice a day. To retry a `failed` draft, reset its `status` to `pending`.

See [`docs/architecture/draft-schema.md`](../../docs/architecture/draft-schema.md) for the full draft schema.

## Output Files

For discovery work, use these names unless the user asks otherwise:

```text
docs/discovery/audio_transcript.fa.md
docs/discovery/audio_summary.en.md
docs/discovery/audio_requirements.en.md
```

For non-Persian audio, adjust the language suffix, for example `audio_transcript.en.md`.

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

On your **conda system** with torch already installed, activate the env first:

```bash
conda activate <your-torch-env>
python skills/audio-transcription/scripts/transcribe_audio.py --setup
```

This runs `pip install faster-whisper` inside your conda env, reusing the existing
torch + CUDA 12.8 (or whatever version is present). No CUDA wheels are downloaded.

### Transcription

After setup, transcribe directly from the activated environment:

```bash
python skills/audio-transcription/scripts/transcribe_audio.py path/to/audio.ogg --out-dir docs/discovery --language fa
```

On Mac without conda, you can still use the `uv` wrapper:

```bash
uv run --with mlx-whisper skills/audio-transcription/scripts/transcribe_audio.py path/to/audio.ogg
```

### Hardware auto-detection and model selection

The script auto-detects your hardware and picks the best model. Use `--model auto` (the default):

| Hardware | Model | Compute | Inference |
|---|---|---|---|
| CUDA GPU ≥ 10 GB VRAM | `large-v3` | `float16` | Batched (batch=16) |
| CUDA GPU ≥ 5 GB VRAM | `medium` | `float16` | Batched |
| Apple Silicon (mlx) | `large-v3` | Apple GPU | Sequential |
| CPU only | `small` | `int8` | Sequential |

### Model fallback chain

If a model fails to load (OOM, missing libraries), the script automatically downgrades:

```
large-v3 → medium → small → base
```

You can also explicitly request a smaller model to reduce GPU/CPU load:

```bash
# Force medium model (less VRAM, still good accuracy for most languages):
python skills/audio-transcription/scripts/transcribe_audio.py audio.wav --model medium

# Force small model (minimal resources):
python skills/audio-transcription/scripts/transcribe_audio.py audio.wav --model small
```

Model accuracy order: `tiny` < `base` < `small` < `medium` < `large-v3`. For Persian voice notes,
use at least **`medium`**; `small`/`tiny` are often phonetically garbled. Models download once
into `docs/discovery/faster-whisper-models/` (gitignored). Override with `WHISPER_DOWNLOAD_ROOT`.

**Download stalls:** Hugging Face model downloads can be very slow without `HF_TOKEN`. If a run
appears stuck at 0 bytes, check network speed to `huggingface.co` / `cas-bridge.xethub.hf.co`.
Use `medium` first (smaller download), or set `HF_TOKEN` for higher rate limits.

To force OpenAI speech-to-text for a single run (requires `OPENAI_API_KEY` and the `openai`
package):

```bash
python skills/audio-transcription/scripts/transcribe_audio.py path/to/audio.ogg --backend openai
```

The script:

- Converts `.ogg`/`.oga` to WAV with `ffmpeg` (quiet; use `--wav-dir` to separate WAV from transcript output).
- Selects the backend via `--backend` / `TRANSCRIPTION_BACKEND` (`local` | `openai` | `auto`).
- Local fallback order: **CUDA `faster-whisper` → Apple Silicon `mlx-whisper` → `whisper` CLI → CPU `faster-whisper`**.
- Writes a markdown transcript with timestamps and a `Confidence:` line in the header.
- Caches models under `docs/discovery/faster-whisper-models/` (or `WHISPER_DOWNLOAD_ROOT`).

Review the transcript after generation. Local Whisper output can contain phonetic mistakes, especially for Persian names, mixed English/Persian business terms, and noisy mobile voice notes.

## Requirements Extraction

When deriving requirements from a transcript:

- Separate exact transcript from interpretation.
- Keep the source-language transcript in its own file.
- Write summaries and requirements in English unless the user asks otherwise.
- Include open questions for ambiguous phrases, missing context, or low-confidence sections.
- Cross-check audio-derived requirements against any written product docs before implementation.
