# Marketing Spend Monitoring Dashboard

Local Django app for importing, monitoring, entering, reporting, and exporting marketing spend data.

For a more visual explanation of the current structure, capabilities, run workflow, and roadmap, see:

```text
docs/PROJECT_EXPLAINED.md
docs/PROJECT_BLUEPRINT.md
docs/CURRENT_STATE_AND_RUN_GUIDE.md
docs/PROJECT_FILE_REFERENCE.md
docs/ACCESS_BY_ROLE.md
docs/DEPLOYMENT_AWS.md
docs/PHASE_2.md
```

## Current Status

- Discovery is complete under `docs/discovery/`.
- Django project and `marketing` app are scaffolded.
- Core models, admin registration, baseline auth groups, permission helpers, and initial tests are in place.
- The Excel importer works from `docs/discovery/column_mapping.yml`.
- The project now uses `uv` as the standard dependency and command runner.
- A custom UI is available for dashboard, invoices, vendors, campaigns, budgets, imports, and users.
- The UI is fully bilingual (FA/EN) with Persian-digit display and Jalali-calendar reporting in Persian mode.
- The dashboard includes Chart.js visuals for overall spend, monthly trend, and per-team spend.
- Dedicated team dashboards show team spend, vendors, campaigns, monthly trend, and attention invoices.
- The workbook `Data` sheet can seed lookup rows for vendors, categories, sub-teams, and requesters.
- Invoices, vendor reports, and campaign reports can be exported to Excel; the dashboard summary can be exported to a server-rendered PDF.
- Production settings are wired (DATABASE_URL/Postgres switch, WhiteNoise, HTTPS headers, logging) behind a `prod` dependency extra — see `docs/DEPLOYMENT_AWS.md`.

## Local Setup

Recommended:

```bash
make setup
make dev-admin
make run
```

This creates a local-only admin login:

```text
username: admin
password: admin12345
```

Open the panel at:

```text
http://127.0.0.1:8000/login/
```

Shortcut after setup:

```bash
make panel
```

Full first-run shortcut:

```bash
make first-run
```

Fallback without `make`:

```bash
uv sync --all-groups
uv run python manage.py migrate
uv run python manage.py seed_auth_groups
uv run python manage.py bootstrap_dev_admin --username admin --password admin12345
uv run python manage.py runserver 127.0.0.1:8000 --noreload
```

Then open:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/login/
```

Current panel sections:

```text
/                 Dashboard
/teams/           Team list and team dashboards
/invoices/        Invoice list/create/detail/edit
/vendors/         Vendor spend report
/campaigns/       Campaign spend report
/budgets/         Budget table and pivot
/imports/         Admin-only Excel upload/import
/users/           Admin-only user/access management
/exports/*.xlsx   Permission-scoped Excel exports
/reports/*.pdf    Permission-scoped PDF reports
/admin/           Django Admin fallback
```

Users are stored in the database, not `.env`. Use `/users/` as admin to create or deactivate users and assign team-level roles.

## Import The Excel Workbook

The importer uses `docs/discovery/column_mapping.yml`, so discovery must exist first.

Put a workbook in one of these locations:

```text
./*.xlsx
./data/*.xlsx
./imports/*.xlsx
```

If exactly one workbook is found, this is enough:

```bash
make import-dry-run
make import
```

For the full data-loading pipeline, including the workbook `Data` sheet lookups:

```bash
make load-data-dry-run
make load-data
```

If more than one workbook exists, pass the file explicitly:

```bash
make import-dry-run FILE=./marketing_spend_workbook.xlsx
make import FILE=./marketing_spend_workbook.xlsx
```

The command prints selected sheets, created/updated/skipped counts, and skipped-row reasons.
Re-running the import updates existing rows instead of duplicating them.

Raw Django command equivalent:

```bash
uv run python manage.py import_marketing_excel --dry-run
uv run python manage.py import_marketing_excel
```

## Seed Reference Data From The Data Sheet

The workbook `Data` sheet is treated as lookup/reference data, not invoice spend. After the main import, you can seed the database lookup rows:

```bash
make seed-reference-dry-run
make seed-reference
```

This creates or updates vendors, spend categories, sub-teams, and requesters from the real workbook mapping.

## Documentation

Full, categorized index with status labels: **[`docs/README.md`](docs/README.md)**.

Most-used docs:

| Doc | Purpose |
|---|---|
| [`docs/README.md`](docs/README.md) | Documentation map — start here to find anything |
| [`docs/PROJECT_EXPLAINED.md`](docs/PROJECT_EXPLAINED.md) | Plain-language guided tour |
| [`docs/CURRENT_STATE_AND_RUN_GUIDE.md`](docs/CURRENT_STATE_AND_RUN_GUIDE.md) | What works now + local run commands |
| [`docs/PHASE_2.md`](docs/PHASE_2.md) | Status and next features |
| [`docs/DEPLOYMENT_AWS.md`](docs/DEPLOYMENT_AWS.md) | Production deployment runbook |
| [`AGENTS.md`](AGENTS.md) | Product requirements for agents |

## Transcribe Future Voice Notes

Voice transcription is optional project tooling. It is not required by the deployed dashboard.

```bash
make transcribe-audio AUDIO=audio_2026-06-12_21-52-39.ogg
```

This uses `uv run --with faster-whisper`, so transcription tooling stays out of the main app
dependency list. If `OPENAI_API_KEY` is set and you want OpenAI speech-to-text, run:

```bash
make transcribe-audio AUDIO=voice.ogg TRANSCRIPT_PACKAGES="--with openai --with faster-whisper"
```

Keep raw voice notes, WAV conversions, and raw transcripts under:

```text
.artifacts/voice-feedback/
```

That directory is ignored by Git. Durable product decisions should be copied into
`docs/PROJECT_BLUEPRINT.md`, `docs/CURRENT_STATE_AND_RUN_GUIDE.md`, or the relevant spec doc.

## Verification

```bash
make check
```

This currently runs Django checks, pytest, and ruff through uv.

## Production / Deployment

Production dependencies live in an optional extra so local dev stays lean:

```bash
make prod-install      # uv sync --extra prod (gunicorn, psycopg, whitenoise, dj-database-url)
make collectstatic
make prod-run          # gunicorn, expects a production .env (DEBUG=false, DATABASE_URL, ...)
```

See `docs/DEPLOYMENT_AWS.md` for the full CLI-first AWS roadmap and cheaper alternatives.
