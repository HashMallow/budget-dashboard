# README_FOR_CODEX.md

This folder contains English implementation instructions for building an internal marketing spend monitoring dashboard.

The original business request is in Persian, but all project instructions are intentionally written in English so Codex can use them reliably.

## Mandatory First Step

Before building the app, Codex must run the discovery workflow:

1. Locate the audio file and transcribe it.
2. Save Persian transcript + English summary + extracted English requirements.
3. Locate the Excel workbook.
4. Inspect sheet names, columns, header rows, sample rows, and likely input/budget sheets.
5. Create `docs/discovery/column_mapping.yml` and `docs/discovery/import_risks.md`.

Detailed instructions are in:

```text
docs/AUDIO_TRANSCRIPTION_AND_XLSX_DISCOVERY.md
.agents/skills/audio-xlsx-discovery/SKILL.md
```

Useful commands after files are placed in the repo:

```bash
python tools/transcribe_audio.py --file ./audio_2026-06-12_10-33-51.ogg
python tools/inspect_xlsx_structure.py --file ./data/marketing.xlsx
```

## What Codex Should Build

A Django-based web panel where:

- Admin manages all users, teams, invoices, budgets, vendors, campaigns, file uploads, and exports.
- Managers see dashboards/reports for their permitted teams.
- Editors enter invoice/spend data for their teams.
- Observers only view permitted data.
- Initial data is imported from an Excel workbook placed in the project directory.
- The database becomes the source of truth after import.
- Excel and PDF exports are available according to permissions.

## Suggested File Placement

When starting the actual app, keep these docs in the repository root:

```text
AGENTS.md
README_FOR_CODEX.md
docs/
  PRODUCT_REQUIREMENTS.md
  DATA_MODEL.md
  EXCEL_IMPORT_SPEC.md
  RBAC_SPEC.md
  DASHBOARD_SPEC.md
  IMPLEMENTATION_PLAN.md
  ACCEPTANCE_TESTS.md
  CODEX_PROMPTS.md
  AUDIO_TRANSCRIPTION_AND_XLSX_DISCOVERY.md
.env.example
.agents/skills/audio-xlsx-discovery/SKILL.md
tools/transcribe_audio.py
tools/inspect_xlsx_structure.py
```

The Excel file should be placed in one of these locations:

```text
./
./data/
./imports/
```

The importer should discover `*.xlsx` automatically.

## Recommended First Codex Prompt

Use the prompt in `docs/CODEX_PROMPTS.md`, starting with **Prompt 0 — Audio and XLSX Discovery**.
