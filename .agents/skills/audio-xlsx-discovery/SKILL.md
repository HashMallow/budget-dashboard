---
name: audio-xlsx-discovery
description: Use when a project includes an audio business request and an Excel workbook that must become the source for database/import structure. Transcribe the audio, inspect workbook sheets/columns, and create mapping docs before coding the importer.
---

# Audio + XLSX Discovery Skill

Use this skill before implementing database models, Excel importers, dashboards, or RBAC when the project has both an audio note and an `.xlsx` file.

## Required Steps

1. Search for audio files: `*.ogg`, `*.oga`, `*.mp3`, `*.m4a`, `*.wav` in the repository root, `data/`, and `imports/`.
2. Search for Excel files: `*.xlsx` in the repository root, `data/`, and `imports/`.
3. Create `docs/discovery/` if it does not exist.
4. Transcribe the audio:
   - Prefer OpenAI speech-to-text if `OPENAI_API_KEY` exists.
   - Convert `.ogg` to `.wav` with `ffmpeg` first when needed.
   - Fallback to local Whisper if installed.
   - Mark unclear sections as `[unclear]`.
5. Save:
   - `docs/discovery/audio_transcript.fa.md`
   - `docs/discovery/audio_summary.en.md`
   - `docs/discovery/audio_requirements.en.md`
6. Inspect the workbook without modifying it:
   - sheet names
   - dimensions
   - visible/hidden sheets
   - likely header rows
   - columns
   - sample rows
   - likely input sheet
   - likely budget sheet
   - likely invoice/vendor/team/payment/campaign/amount/date columns
7. Save:
   - `docs/discovery/workbook_structure.md`
   - `docs/discovery/workbook_sample_rows.md`
   - `docs/discovery/column_mapping.yml`
   - `docs/discovery/import_risks.md`
8. Use the discovered mapping to implement the importer.

## Important Rules

- Do not guess exact Excel columns before inspecting the workbook.
- Do not silently drop rows.
- Do not commit API keys.
- Preserve the original Persian transcript; provide English summary and requirements separately.
- Treat Excel as initial import/export format, not the runtime database.
- The database becomes the source of truth after import.
- If transcription is unavailable, document the limitation and proceed using written requirements.
