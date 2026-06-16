# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "python-telegram-bot",
# ]
# ///

"""Telegram ingestion pipeline — Phase 1 only.

Downloads messages and audio to disk. Does NOT transcribe.
Run continuously with --poll (default) or periodically with --once (cron-friendly).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_env import load_env

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path.cwd()
DRAFTS_DIR = PROJECT_ROOT / "docs/discovery/requests/drafts"
VOICE_DIR = PROJECT_ROOT / ".artifacts/telegram-bot/voice"
WAV_DIR = PROJECT_ROOT / ".artifacts/telegram-bot/wav"
AUDIO_DIR = PROJECT_ROOT / ".artifacts/telegram-bot/audio"
STATE_DIR = PROJECT_ROOT / ".artifacts/telegram-bot"
OFFSET_FILE = STATE_DIR / "offset.json"

AUDIO_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/ogg",
    "audio/opus",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "application/ogg",
}
AUDIO_EXTENSIONS = {".ogg", ".oga", ".mp3", ".m4a", ".wav", ".webm", ".opus"}


def ensure_dirs() -> None:
    for path in (DRAFTS_DIR, VOICE_DIR, WAV_DIR, AUDIO_DIR, STATE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def convert_to_wav(source_path: Path) -> Path | None:
    """Convert an audio file to .wav using ffmpeg."""
    if source_path.suffix.lower() == ".wav":
        return source_path

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.warning("ffmpeg not found — skipping WAV conversion")
        return None

    wav_path = WAV_DIR / f"{source_path.stem}.wav"
    try:
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", str(source_path), str(wav_path)],
            check=True,
        )
        logger.info("Converted %s → %s", source_path, wav_path)
        return wav_path
    except subprocess.CalledProcessError as exc:
        logger.error("ffmpeg conversion failed: %s", exc)
        return None


def save_draft(
    *,
    message_id: int,
    chat_id: int,
    sender: str,
    content: str,
    draft_type: str,
    audio_file: Path | None = None,
    forward_from: str | None = None,
) -> Path:
    """Save a draft markdown file with structured YAML frontmatter."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = DRAFTS_DIR / f"{draft_type}_{timestamp}_{chat_id}_{message_id}.md"

    lines = [
        "---",
        "source: telegram",
        f"sender: {sender}",
        f"date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"type: {draft_type}",
        "status: pending",
        f"message_id: {message_id}",
        f"chat_id: {chat_id}",
    ]
    if forward_from:
        lines.append(f"forward_from: {forward_from}")
    if audio_file:
        lines.append(f"audio_file: {audio_file.resolve()}")
    lines.append("---")

    file_path.write_text("\n".join(lines) + "\n\n" + content + "\n", encoding="utf-8")
    logger.info("Saved draft: %s", file_path)
    return file_path


def _get_message(update: Update):
    return update.message or update.channel_post


def _get_sender(update: Update) -> str:
    if update.channel_post:
        return update.channel_post.chat.title or "unknown-channel"
    msg = update.message
    if msg and msg.from_user:
        return msg.from_user.username or msg.from_user.first_name or "unknown"
    return "unknown"


def _get_forward_from(message) -> str | None:
    if getattr(message, "forward_origin", None):
        origin = message.forward_origin
        if hasattr(origin, "sender_user") and origin.sender_user:
            user = origin.sender_user
            return user.username or user.first_name
        if hasattr(origin, "chat") and origin.chat:
            return origin.chat.title or origin.chat.username
    if getattr(message, "forward_from", None):
        user = message.forward_from
        return user.username or user.first_name
    if getattr(message, "forward_from_chat", None):
        return message.forward_from_chat.title or message.forward_from_chat.username
    return None


def _audio_extension(file_name: str | None, mime_type: str | None) -> str:
    if file_name:
        suffix = Path(file_name).suffix.lower()
        if suffix in AUDIO_EXTENSIONS:
            return suffix
    mime_map = {
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/m4a": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/ogg": ".ogg",
        "audio/opus": ".ogg",
        "application/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/webm": ".webm",
    }
    if mime_type and mime_type in mime_map:
        return mime_map[mime_type]
    return ".bin"


async def _download_audio(
    context: ContextTypes.DEFAULT_TYPE,
    file_id: str,
    dest_path: Path,
) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tg_file = await context.bot.get_file(file_id)
    await tg_file.download_to_drive(str(dest_path))
    logger.info("Downloaded audio to %s", dest_path)
    return dest_path


async def _save_audio_draft(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    file_id: str,
    file_name: str | None,
    mime_type: str | None,
    draft_type: str,
    prefix: str,
) -> None:
    message = _get_message(update)
    if not message:
        return

    sender = _get_sender(update)
    forward_from = _get_forward_from(message)
    ext = _audio_extension(file_name, mime_type)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    source_path = (VOICE_DIR if draft_type == "voice" else AUDIO_DIR) / f"{prefix}_{timestamp}_{message.chat_id}_{message.message_id}{ext}"

    try:
        await _download_audio(context, file_id, source_path)
    except Exception as exc:
        logger.error("Failed to download audio (message %s): %s", message.message_id, exc)
        return

    wav_path = convert_to_wav(source_path)
    audio_path = wav_path or source_path

    forward_note = f" (forwarded from {forward_from})" if forward_from else ""
    content = f"[{draft_type.title()} message{forward_note} — awaiting transcription]\n"
    save_draft(
        message_id=message.message_id,
        chat_id=message.chat_id,
        sender=sender,
        content=content,
        draft_type=draft_type,
        audio_file=audio_path,
        forward_from=forward_from,
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = _get_message(update)
    if not message or not message.text:
        return

    sender = _get_sender(update)
    forward_from = _get_forward_from(message)
    logger.info("Received text from %s: %s...", sender, message.text[:80])

    content = message.text
    if forward_from:
        content = f"[Forwarded from {forward_from}]\n\n{content}"

    save_draft(
        message_id=message.message_id,
        chat_id=message.chat_id,
        sender=sender,
        content=content,
        draft_type="text",
        forward_from=forward_from,
    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = _get_message(update)
    if not message or not message.voice:
        return

    logger.info("Received voice message from %s", _get_sender(update))
    await _save_audio_draft(
        update,
        context,
        file_id=message.voice.file_id,
        file_name=None,
        mime_type="audio/ogg",
        draft_type="voice",
        prefix="voice",
    )


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle audio attachments (MP3, M4A, etc.) including forwarded files."""
    message = _get_message(update)
    if not message or not message.audio:
        return

    logger.info("Received audio file from %s", _get_sender(update))
    await _save_audio_draft(
        update,
        context,
        file_id=message.audio.file_id,
        file_name=message.audio.file_name,
        mime_type=message.audio.mime_type,
        draft_type="audio",
        prefix="audio",
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document attachments that are audio files (common for forwards)."""
    message = _get_message(update)
    if not message or not message.document:
        return

    doc = message.document
    file_name = doc.file_name or ""
    mime_type = doc.mime_type or ""

    is_audio = mime_type in AUDIO_MIME_TYPES or Path(file_name).suffix.lower() in AUDIO_EXTENSIONS
    if not is_audio:
        return

    logger.info("Received audio document from %s: %s", _get_sender(update), file_name or mime_type)
    await _save_audio_draft(
        update,
        context,
        file_id=doc.file_id,
        file_name=file_name,
        mime_type=mime_type,
        draft_type="audio",
        prefix="doc",
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = _get_message(update)
    if not message:
        return
    await message.reply_text(
        "Bot started. Send text, voice notes, or audio files — they will be saved as draft requests."
    )


def build_application(token: str) -> Application:
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST & filters.TEXT, handle_text))
    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST & filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST & filters.AUDIO, handle_audio))
    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST & filters.Document.ALL, handle_document))
    return application


def load_offset() -> int | None:
    if not OFFSET_FILE.exists():
        return None
    try:
        data = json.loads(OFFSET_FILE.read_text(encoding="utf-8"))
        return int(data.get("offset", 0)) + 1
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def save_offset(update_id: int) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(json.dumps({"offset": update_id, "updated": datetime.now().isoformat()}), encoding="utf-8")


async def run_once(application: Application) -> int:
    """Fetch pending Telegram updates once, process them, and exit."""
    offset = load_offset()
    processed = 0

    async with application:
        await application.initialize()
        await application.start()
        updates = await application.bot.get_updates(
            offset=offset,
            timeout=10,
            allowed_updates=Update.ALL_TYPES,
        )
        for update in updates:
            await application.process_update(update)
            save_offset(update.update_id)
            processed += 1
        await application.stop()

    logger.info("Sync complete — processed %d update(s)", processed)
    return processed


def run_polling(application: Application) -> None:
    logger.info("Starting Telegram Bot Pipeline (polling)...")
    logger.info("Project root: %s", PROJECT_ROOT)
    logger.info("Drafts → %s", DRAFTS_DIR)
    logger.info("Voice  → %s", VOICE_DIR)
    logger.info("Audio  → %s", AUDIO_DIR)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


def main() -> None:
    parser = argparse.ArgumentParser(description="Telegram ingestion pipeline (Phase 1).")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Fetch pending updates once and exit (use with cron instead of a always-on bot).",
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Run continuous polling (default when neither --once nor --poll is given).",
    )
    args = parser.parse_args()

    env_file = load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set.")
        if env_file:
            logger.error("Checked %s — add TELEGRAM_BOT_TOKEN=your_token there.", env_file)
        else:
            logger.error("Create a .env file in the project root with TELEGRAM_BOT_TOKEN=your_token")
        logger.error("Or export it: export TELEGRAM_BOT_TOKEN=your_token")
        sys.exit(1)
    if env_file:
        logger.info("Loaded env from %s", env_file)

    ensure_dirs()
    application = build_application(token)

    if args.once:
        import asyncio

        asyncio.run(run_once(application))
    else:
        run_polling(application)


if __name__ == "__main__":
    main()
