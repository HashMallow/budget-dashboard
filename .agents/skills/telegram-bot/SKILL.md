---
name: telegram-bot-pipeline
description: Sync recent Telegram messages into drafts and .artifacts/. Use when the user mentions new Telegram requests, new messages, voice notes, forwarded audio, or asks to check/load/fetch messages from Telegram. Always run fetch_requests.py FIRST before transcribing or processing drafts.
---

# Telegram Bot Pipeline

Use this skill when you need to ingest requests from a Telegram group, chat, or channel — especially when the user says things like "there are new requests", "check telegram", "load new messages", or "process what I sent on Telegram".

It handles text, native voice notes, audio files, and forwarded audio attachments.

## Agent-driven workflow (primary — no cron or always-on bot needed)

When the user mentions new Telegram requests, **run these steps in order** from the project root:

### Step 1 — Fetch messages + transcribe audio (one command)

```bash
python skills/telegram-bot/scripts/fetch_requests.py
```

(Use `.agents/skills/` or `.cursor/skills/` instead of `skills/` if copied into a host project.)

This runs Phase 1 (sync recent Telegram messages to drafts + `.artifacts/`) and Phase 2a (transcribe pending voice/audio). Reads `TELEGRAM_BOT_TOKEN` from `.env` in the project root (or from the environment).

Or run the steps separately:

```bash
# Phase 1 only
uv run skills/telegram-bot/scripts/telegram_pipeline.py --once

# Phase 2a only (uses audio-transcription skill)
python skills/audio-transcription/scripts/process_audio_queue.py
```

### Step 2 — Process drafts (AI agent)

After fetch completes, read `docs/discovery/requests/drafts/` and for each unprocessed draft:
- Text drafts (`type: text`) → translate if needed, create instruction files, apply changes
- Audio drafts (`status: transcribed`) → read the transcript, create instruction files, apply changes
- Move finished drafts to `drafts/processed/`

**Do not skip Step 1.** Drafts on disk may be stale until the sync script runs.

## Architecture (three phases)

```text
Phase 1 — telegram_pipeline.py     Ingest messages + download audio → drafts + .artifacts/
Phase 2a — process_audio_queue.py  Transcribe pending audio drafts (standalone, no bot needed)
Phase 2b — AI Agent                Translate, create instruction files, apply code changes
```

The Telegram bot and transcription pipeline are **fully decoupled**. They communicate only through files on disk.

## Workflow

**Phase 1: Ingestion (`telegram_pipeline.py`)**

Saves every incoming message as a draft file. Does **not** transcribe.

1. Connects to Telegram using `TELEGRAM_BOT_TOKEN`.
2. Handles:
   - **Text messages** → `docs/discovery/requests/drafts/text_<timestamp>_<chat_id>_<id>.md`
   - **Voice notes** (`message.voice`) → downloads `.ogg`, converts to `.wav`
   - **Audio files** (`message.audio`) → MP3, M4A, etc.
   - **Forwarded audio documents** (`message.document` with audio mime type) — the most common failure mode for forwards
3. Each draft has structured YAML frontmatter:

```yaml
---
source: telegram
sender: username
date: 2025-06-16 12:00:00
type: voice          # text | voice | audio
status: pending      # pending → transcribed → processed (or → failed)
message_id: 42
chat_id: -100123456
message_dir: /abs/.artifacts/telegram-bot/messages/voice_..._42   # voice/audio only
audio_file: /abs/.../messages/voice_..._42/audio.wav              # voice/audio only
forward_from: original_sender            # when forwarded
---
```

The audio queue worker adds `transcript_file`, `confidence`, and `processed_at` on success,
or `error` + `processed_at` on failure. See the full contract in
[`docs/architecture/draft-schema.md`](../../docs/architecture/draft-schema.md).

**Phase 2a: Transcription (`process_audio_queue.py` — standalone)**

Runs independently of the Telegram bot:

```bash
# Process all pending audio drafts once
python skills/audio-transcription/scripts/process_audio_queue.py

# Watch for new drafts (runs until Ctrl+C)
python skills/audio-transcription/scripts/process_audio_queue.py --watch 60

# Preview what would be transcribed
python skills/audio-transcription/scripts/process_audio_queue.py --dry-run
```

For each pending draft with `type: voice` or `type: audio`:
1. Reads `audio_file` from frontmatter
2. Runs `transcribe_audio.py`
3. Writes transcript to `.artifacts/telegram-bot/transcripts/`
4. Updates draft: `status: transcribed`, adds transcript body

**Phase 2b: Processing (AI Agent)**

When asked to "process the telegram queue" or "check drafts":

1. Scan `docs/discovery/requests/drafts/` (skip `processed/`).
2. For drafts with `status: transcribed` (or `type: text`):
   - Translate non-English content if needed
   - Create structured instruction files in `docs/discovery/requests/`
   - Apply code changes
3. Move processed drafts to `docs/discovery/requests/drafts/processed/` and set `status: processed`.

## Directory Layout

Each audio message gets its **own folder** named with the same stem as its draft, so a
draft and its audio + transcript are trivially correlated. A generated `INDEX.md` links
everything together.

```text
docs/discovery/requests/
├── INDEX.md                             ← navigation hub: one row per draft (Phase 2a)
├── drafts/                              ← raw incoming messages (Phase 1)
│   ├── text_20260616_120000_-1001293270975_42.md
│   ├── voice_20260616_120100_250394750_43.md
│   └── processed/                       ← archived after Phase 2b
└── instruction_20260616_42.md           ← structured instruction (Phase 2b)

.artifacts/telegram-bot/
├── messages/                            ← one folder per audio message (stem = draft name)
│   └── voice_20260616_120100_250394750_43/
│       ├── source.oga                   ← original download
│       ├── audio.wav                    ← ffmpeg-converted (ready to transcribe)
│       └── transcript.md                ← transcript + backlinks (Phase 2a)
└── offset.json                          ← last processed update_id (--once mode)
```

The `transcript.md` in each folder carries YAML frontmatter and relative links back to
its `audio.wav`, `source.*`, and draft — so you can open a transcript and confirm it
matches the audio. Legacy flat layouts (`voice/`, `wav/`, `transcripts/`) from older runs
still work; the queue and `INDEX.md` handle both.

## Setup

1. Create a bot using [BotFather](https://t.me/BotFather) and get the token.
2. For **channels**: add the bot as Administrator with "Read" permission.
3. For **groups**: make it Admin, or disable Group Privacy via BotFather → Bot Settings.
4. Add the token to a `.env` file in the project root:

```bash
cp .env.example .env
# Edit .env and set TELEGRAM_BOT_TOKEN=your_token_here
```

Scripts load `.env` automatically. Shell exports still work and take precedence.

## Periodic cleanup

Runtime files (drafts, audio, transcripts, INDEX) accumulate over time. From the project root:

```bash
# Typical “once in a while” cleanup — removes artifacts + active drafts, keeps processed/
make clean-runtime

# Lighter: caches, lock file, logs only
make clean

# Full wipe including processed drafts and Whisper model cache
make clean-all
```

See `make help` for all targets. `.env` is never deleted.

## Running

Run from the **project root** (where `docs/` and `.artifacts/` should live).

### Option A: Twice-daily finite sync (recommended — no always-on bot)

For normal use, run a **finite, idempotent** job a couple of times per day. Each run fetches
pending updates, transcribes locally, and exits. It is safe to run twice per day: the offset
file avoids re-ingesting messages, and the queue lock + terminal statuses avoid double work.

```bash
# Manual, on-demand (fetch + transcribe locally, capped)
python skills/telegram-bot/scripts/fetch_requests.py --backend local --max-items 20

# Cron — 09:00 and 17:00 daily, local-only (no cloud spend)
0 9,17 * * * cd /path/to/project && python skills/telegram-bot/scripts/fetch_requests.py --backend local --max-items 20 >> .artifacts/telegram-bot/fetch.log 2>&1
```

**Avoiding cloud API usage in scheduled mode:** always pass `--backend local` (or set
`TRANSCRIPTION_BACKEND=local` in `.env`). With `local`, no OpenAI calls are made even if
`OPENAI_API_KEY` is present. Use `--max-items` / `--max-runtime-seconds` to bound each run.

**Preview before running** (no work, no API calls):

```bash
python skills/telegram-bot/scripts/fetch_requests.py --dry-run
python skills/audio-transcription/scripts/process_audio_queue.py --dry-run
```

You can also split sync and transcription onto separate schedules:

```bash
# Sync only (no transcription)
python skills/telegram-bot/scripts/fetch_requests.py --skip-transcribe
# Transcribe only, local + capped
python skills/audio-transcription/scripts/process_audio_queue.py --backend local --max-items 20
```

### Option B: `--watch` (interactive only)

`--watch` re-scans on an interval and **holds the queue lock for the whole session**. Use it
only for interactive/foreground sessions where you want near-real-time transcription. Do not
combine it with the cron job above (the cron run would exit with code 3 while watch holds the
lock). For unattended operation, prefer Option A.

### Option C: Always-on polling

```bash
uv run skills/telegram-bot/scripts/telegram_pipeline.py --poll
```

Stop with Ctrl+C. For background: `nohup ... &`. Only needed if you want messages ingested
the instant they arrive; otherwise Option A is simpler and cheaper.

## Processing Drafts (AI Agent Instructions)

Trigger phrases: "new requests", "check telegram", "process telegram queue", "load messages", "I sent something on Telegram".

**Always run fetch first:**

```bash
python skills/telegram-bot/scripts/fetch_requests.py
```

(Use `.agents/skills/` or `.cursor/skills/` instead of `skills/` if copied into a host project.)

Then process each draft in `docs/discovery/requests/drafts/` (skip `processed/`):

1. Read frontmatter (`type`, `status`, `sender`, `audio_file`, `transcript_file`).
2. For `type: text` or `status: transcribed`:
   a. Read content / transcript.
   b. Translate non-English content if needed.
   c. Create a structured instruction file in `docs/discovery/requests/`.
   d. Apply code changes or answer questions.
3. Move processed drafts to `drafts/processed/`.

If `fetch_requests.py` reports no new drafts but the user insists they sent something, verify `.env` contains `TELEGRAM_BOT_TOKEN` and the bot has access to the chat.
