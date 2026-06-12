---
name: audio-transcription
description: Transcribe spoken audio notes and extract concise summaries or requirements. Use when Codex is asked to work with audio files such as .ogg, .oga, .mp3, .m4a, or .wav; convert audio formats; prefer OpenAI speech-to-text when OPENAI_API_KEY is available; fall back to local Whisper/faster-whisper; save transcripts and derived notes as markdown.
---

# Audio Transcription

Use this skill when an audio file is an input artifact and the user needs a transcript, summary, requirements, or a written record.

## Workflow

1. Locate audio files if the user did not provide an explicit path:
   - Search the current directory, `data/`, `imports/`, and `docs/` for `*.ogg`, `*.oga`, `*.mp3`, `*.m4a`, and `*.wav`.
   - If multiple likely files exist and the intended one is unclear, ask for the path.
2. Create the requested output directory. Use `docs/discovery/` when this is part of project discovery.
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

The script:

- Converts `.ogg`/`.oga` to WAV with `ffmpeg`.
- Uses OpenAI speech-to-text when `OPENAI_API_KEY` is available.
- Falls back to `whisper` CLI, then `faster_whisper`.
- Writes a markdown transcript.

Review the transcript after generation. Local Whisper output can contain phonetic mistakes, especially for Persian names, mixed English/Persian business terms, and noisy mobile voice notes.

## Requirements Extraction

When deriving requirements from a transcript:

- Separate exact transcript from interpretation.
- Keep the source-language transcript in its own file.
- Write summaries and requirements in English unless the user asks otherwise.
- Include open questions for ambiguous phrases, missing context, or low-confidence sections.
- Cross-check audio-derived requirements against any written product docs before implementation.
