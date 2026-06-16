---
name: audio-xlsx-discovery
description: Use when a project includes an audio business request and an Excel workbook that must become the source for database/import structure. Transcribe the audio, inspect workbook sheets/columns, and create mapping docs before coding the importer.
---

# Audio + XLSX Discovery Skill

Use this skill before implementing database models, Excel importers, dashboards, or RBAC when the project has both an audio note and an `.xlsx` file.

## Required Steps

1. Search for audio: `.artifacts/audio/`, `.artifacts/voice-feedback/audio/`, then repo root, `data/`, `imports/`.
2. Search for Excel files: `*.xlsx` in the repository root, `data/`, and `imports/`.
3. Create `docs/discovery/` if it does not exist; create `.artifacts/voice-feedback/transcripts/` if needed.
4. Transcribe the audio (see `.agents/skills/audio-transcription/SKILL.md` backend priority):
   - **1.** OpenAI `whisper-1` if `OPENAI_API_KEY` exists.
   - **2.** mlx-whisper `large-v3` on macOS.
   - **3.** faster-whisper `large-v3` on CUDA (this project: conda **`ml-env`**).
   - **4.** faster-whisper on CPU (`small`) only if nothing else works.
   - Convert `.ogg` to `.wav` with `ffmpeg` first when needed.
   - Mark unclear sections as `[unclear]`.
   - Batch: `python tools/batch_transcribe_artifacts.py`
5. Save **English product-owner topics** (git-tracked under `docs/voice-feedback/`):
   - `docs/voice-feedback/USER_REQUESTS.en.md` — **main topics** for agents
   - `docs/voice-feedback/PROCESSING_LOG.en.md` — verification, fixes, backlog (**update each batch**)
   - Per-file Persian (local): `.artifacts/voice-feedback/transcripts/{stem}_transcript.fa.md`
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
- Preserve the original Persian transcript in `.artifacts/`; English summary in **`docs/voice-feedback/`** (git-tracked).
- Read **`docs/voice-feedback/USER_REQUESTS.en.md`** before implementing invoice, dashboard, or reference-data changes.
- Append **`docs/voice-feedback/PROCESSING_LOG.en.md`** after each transcription batch or fix pass.
- Treat Excel as initial import/export format, not the runtime database.
- The database becomes the source of truth after import.
- If transcription is unavailable, document the limitation and proceed using written requirements.
