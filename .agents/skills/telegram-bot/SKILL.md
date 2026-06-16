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
status: pending      # pending → transcribed → processed
message_id: 42
chat_id: -100123456
audio_file: /absolute/path/to/file.wav   # voice/audio only
forward_from: original_sender            # when forwarded
---
```

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

```text
docs/discovery/requests/
├── drafts/                              ← raw incoming messages (Phase 1)
│   ├── text_20250616_120000_-100_42.md
│   ├── voice_20250616_120100_-100_43.md
│   └── processed/                       ← archived after Phase 2b
└── instruction_20250616_42.md           ← structured instruction (Phase 2b)

.artifacts/telegram-bot/
├── voice/                               ← native voice note .ogg files
├── audio/                               ← forwarded/sent audio files (mp3, m4a, etc.)
├── wav/                                 ← ffmpeg-converted .wav files
├── transcripts/                         ← transcription output (Phase 2a)
└── offset.json                          ← last processed update_id (--once mode)
```

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

## Running

Run from the **project root** (where `docs/` and `.artifacts/` should live):

### Option A: Cron-friendly sync (recommended — no always-on bot)

Fetch pending messages every few minutes via cron:

```bash
# Manual sync
uv run skills/telegram-bot/scripts/telegram_pipeline.py --once

# Cron example — sync every 2 minutes
*/2 * * * * cd /path/to/project && uv run skills/telegram-bot/scripts/telegram_pipeline.py --once >> .artifacts/telegram-bot/sync.log 2>&1
```

Then transcribe on a separate schedule:

```bash
# Cron example — transcribe every 5 minutes
*/5 * * * * cd /path/to/project && python skills/audio-transcription/scripts/process_audio_queue.py >> .artifacts/telegram-bot/transcribe.log 2>&1
```

### Option B: Always-on polling

```bash
uv run skills/telegram-bot/scripts/telegram_pipeline.py --poll
```

Stop with Ctrl+C. For background: `nohup ... &`

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
