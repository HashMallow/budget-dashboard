# End-State Cleanup Plan

This project currently keeps discovery artifacts, sample inputs, generated local files, and implementation notes because they are useful while building. Before deployment or final repository cleanup, keep only files that are required for the app, tests, documentation, and reproducible setup.

## Keep In The Main Project

These files should remain in the final project:

```text
README.md
Makefile
manage.py
pyproject.toml
uv.lock
uv.toml
.python-version
.env.example
.gitignore

config/
marketing/
templates/

docs/CURRENT_STATE_AND_RUN_GUIDE.md
docs/PROJECT_BLUEPRINT.md
docs/PROJECT_FILE_REFERENCE.md
docs/END_STATE_CLEANUP_PLAN.md
docs/DATA_MODEL.md
docs/RBAC_SPEC.md
docs/EXCEL_IMPORT_SPEC.md
docs/DASHBOARD_SPEC.md
docs/PRODUCT_REQUIREMENTS.md
docs/ACCEPTANCE_TESTS.md
docs/IMPLEMENTATION_PLAN.md

docs/discovery/column_mapping.yml
```

`docs/discovery/column_mapping.yml` should remain unless the importer default is moved to a dedicated app config path. The importer currently uses this mapping.

## Ignore Or Remove Before Final Commit/Deployment

These are local/generated or peripheral files:

```text
.venv/
.uv-cache/
db.sqlite3
media/
staticfiles/
__pycache__/
.pytest_cache/
.ruff_cache/
.artifacts/

*.xlsx
*.ogg
*.oga
*.mp3
*.m4a
*.wav

docs/discovery/audio_*.md
docs/discovery/*.wav
docs/discovery/workbook_*.md
docs/discovery/import_risks.md

marketing_dashboard_codex_instructions_updated.zip
```

These are now covered by `.gitignore` where appropriate.

Use this ignored folder for raw voice notes, WAV conversions, and generated transcript markdown:

```text
.artifacts/voice-feedback/
```

Keep durable decisions in normal docs, not in raw transcript files.

## Recreate Discovery Artifacts Later

Audio transcription can be recreated with the local Codex skill:

```text
.agents/skills/audio-transcription/
```

Recommended command:

```bash
make transcribe-audio AUDIO=.artifacts/voice-feedback/audio/my-note.ogg TRANSCRIPT_OUT=.artifacts/voice-feedback/transcripts
```

Workbook discovery can be recreated with:

```bash
uv run python tools/inspect_xlsx_structure.py path/to/workbook.xlsx --out-dir docs/discovery
```

Import mapping can be recreated or updated by rerunning discovery and editing:

```text
docs/discovery/column_mapping.yml
```

## Cleanup Commands

Remove safe generated local artifacts:

```bash
make clean-artifacts
```

Remove the local SQLite database:

```bash
make clean-local-db
```

Only run `make clean-local-db` if you are okay losing the local imported data. You can recreate the database with:

```bash
make setup
make import
```

## Suggested Final Repository Shape

```text
Alireza/
├── README.md
├── Makefile
├── manage.py
├── pyproject.toml
├── uv.lock
├── uv.toml
├── .python-version
├── .env.example
├── .gitignore
├── config/
├── marketing/
├── templates/
├── docs/
│   ├── CURRENT_STATE_AND_RUN_GUIDE.md
│   ├── PROJECT_BLUEPRINT.md
│   ├── PROJECT_FILE_REFERENCE.md
│   ├── END_STATE_CLEANUP_PLAN.md
│   ├── DATA_MODEL.md
│   ├── RBAC_SPEC.md
│   ├── EXCEL_IMPORT_SPEC.md
│   ├── DASHBOARD_SPEC.md
│   ├── PRODUCT_REQUIREMENTS.md
│   └── discovery/
│       └── column_mapping.yml
├── data/
└── imports/
```

## Later Improvement

Move the finalized import mapping from:

```text
docs/discovery/column_mapping.yml
```

to a runtime config path such as:

```text
marketing/import_mappings/marketing_spend_mapping.yml
```

After that, the entire `docs/discovery/` folder can be treated as generated discovery output and ignored or removed.
