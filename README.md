# Marketing Finance Hub

Local Django panel for importing, monitoring, entering, reporting, and exporting marketing spend data (also referred to in older docs as *Marketing Spend Monitoring Dashboard*).

For a more visual explanation of the current structure, capabilities, run workflow, and roadmap, see:

```text
docs/guides/PROJECT_EXPLAINED.md
docs/guides/USER_SITEMAP.md
docs/architecture/PROJECT_BLUEPRINT.md
docs/guides/CURRENT_STATE_AND_RUN_GUIDE.md
docs/architecture/PROJECT_FILE_REFERENCE.md
docs/operations/ACCESS_BY_ROLE.md
docs/operations/DEPLOYMENT_AWS.md
docs/project/PHASE_2.md
```

## Current Status

- Discovery is complete under `docs/discovery/` (audio transcript/summary/requirements, workbook
  structure/sample rows, `column_mapping.yml`, and import risks).
- Django project and `marketing` app are scaffolded with models, RBAC, importer, and **94+ tests**.
- The Excel importer works from `docs/discovery/column_mapping.yml` (idempotent re-import).
  Tab names in that file are **generic** for the public repo; import still works via **header
  auto-detection** when your workbook uses different sheet names. Optional gitignored
  `docs/discovery/column_mapping.local.yml` pins exact tab names (see **Import The Excel Workbook**).
- The project uses **`uv`** + **`Makefile`** as the standard local command runner.
- Custom panel: **sectioned sidebar** (Overview · Spend & teams · Reports · Administration · Help),
  finance overview dashboard (budget vs actual, charts; team-filtered layout), invoices with **business line**
  filter, teams, vendors, campaigns, budgets, **contracts**, **reference-data CRUD** (`/reference/`),
  in-app **Help** (`/help/`), imports, and user access.
- Bilingual FA/EN UI, Jalali reporting, Rial/Toman display, compact/full money formatting.
- Excel exports (invoices, vendors, campaigns, workbook layout) and **Persian/RTL PDF reports**
  (dashboard, vendors, campaigns, contracts) via ReportLab + Vazirmatn.
- Production settings wired (`prod` extra: gunicorn, Postgres, WhiteNoise) — see `docs/operations/DEPLOYMENT_AWS.md`.

## Prerequisites

Most local workflows use the project `Makefile`. You need `make` available in your shell.

**macOS** — a fresh Mac often does not include `make` until developer tools are installed. Pick one:

```bash
# Recommended: Apple Command Line Tools (includes make, git, clang)
xcode-select --install
```

Or, if you use Homebrew:

```bash
brew install make
```

Verify:

```bash
make --version
```

You also need [uv](https://docs.astral.sh/uv/) (Python dependency runner). If `make setup`
prints `/bin/sh: uv: command not found`, install it first.

On macOS with Homebrew:

```bash
brew install uv
```

Or with the official installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installing with the official installer, restart the terminal. If `uv --version` still does
not work, run:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Verify:

```bash
uv --version
```

If you prefer not to install `make`, every `make` target has a `uv run python manage.py …` equivalent — see **Fallback without `make`** below.

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

Copy-paste-safe first run, without shell comments. Paste only these command lines:

```bash
make setup
make dev-admin
make load-data-dry-run
make load-data
make check
make dev
```

If there is more than one `.xlsx` file in the project, pass the workbook explicitly:

```bash
make load-data-dry-run FILE=./path/to/your_workbook.xlsx
make load-data FILE=./path/to/your_workbook.xlsx
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
/                 Finance overview dashboard (sectioned layout; pie hidden when a team is filtered)
/help/            In-app guide (public; admin sections gated)
/teams/           Team list and team dashboards
/invoices/        Invoice list / create / detail / edit / uploads (business line filter)
/vendors/         Vendor spend report
/campaigns/       Campaign spend report (+ admin campaign CRUD links)
/budgets/         Budget table, pivot, and planned-budget charts
/contracts/       Contract tracking (stages, expiry, attachments)
/reference/       Admin-only lookup CRUD (vendors, categories, sub-teams, campaigns, requesters)
/imports/         Admin-only Excel upload / import
/users/           Admin-only user and team-access management
/exports/*.xlsx   Permission-scoped Excel exports
/reports/*.pdf    Permission-scoped PDF reports (Persian glyph shaping + Vazirmatn when UI is FA)
/admin/           Django Admin fallback
```

**Sidebar groups:** Overview (Dashboard) · Spend & teams (Invoices, Teams) · Reports (Budget, Vendors, Campaigns, Contracts) · Administration (Excel Import, Users, Reference data) · **Help** at the bottom.

After `make load-data`, manage lookup rows in the panel at **`/reference/`** (admin) or re-run
`make seed-reference` from the workbook Data sheet.

## Import The Excel Workbook

The importer reads `docs/discovery/column_mapping.yml` (tracked **template** with generic sheet
names and example labels). It merges an optional **gitignored**
`docs/discovery/column_mapping.local.yml` when present.

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
make import-dry-run FILE=./path/to/your_workbook.xlsx
make import FILE=./path/to/your_workbook.xlsx
```

### Sheet names vs what you see in the app

| Source | What it controls |
|--------|------------------|
| **Workbook cells** (after import) | Team names, vendors, business lines, amounts — what the dashboard and lists show |
| **`column_mapping.yml`** | Column headers, row ranges, import rules; generic tab **labels** in docs/export |
| **`column_mapping.local.yml`** (optional) | Your real invoice tab name, export sheet title, etc. |

**You do not need a local mapping file** if your invoice tab has the expected columns (`Invoice Number`,
`Vendor Name`, `Invoice Amount (IRR)`, …). The importer auto-detects the tab when the name differs
from the template (e.g. `Marketing Spend Input` vs `Marketing Spend Input`).

Optional — match export tab names to your source workbook:

```bash
cp docs/discovery/column_mapping.local.yml.example docs/discovery/column_mapping.local.yml
# edit sheets.invoices.actual_sheet_name if needed
```

See `docs/discovery/README.md` for details.

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

You can also add or edit these rows in the panel at **`/reference/`** (admin login required).

Users are stored in the database, not `.env`. Use `/users/` as admin to create or deactivate users and assign team-level roles.

## Documentation

Full, categorized index with status labels: **[`docs/README.md`](docs/README.md)**.

Most-used docs:

| Doc | Purpose |
|---|---|
| [`docs/README.md`](docs/README.md) | Documentation map — start here to find anything |
| [`docs/guides/USER_SITEMAP.md`](docs/guides/USER_SITEMAP.md) | End-user site map (also in-app: **Help**) |
| [`docs/guides/PROJECT_EXPLAINED.md`](docs/guides/PROJECT_EXPLAINED.md) | Plain-language guided tour |
| [`docs/guides/CURRENT_STATE_AND_RUN_GUIDE.md`](docs/guides/CURRENT_STATE_AND_RUN_GUIDE.md) | What works now + local run commands |
| [`docs/project/PHASE_2.md`](docs/project/PHASE_2.md) | Status and next features |
| [`docs/operations/DEPLOYMENT_AWS.md`](docs/operations/DEPLOYMENT_AWS.md) | Production deployment runbook |
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
`docs/architecture/PROJECT_BLUEPRINT.md`, `docs/guides/CURRENT_STATE_AND_RUN_GUIDE.md`, or the relevant spec doc.

## Verification

```bash
make check
```

This currently runs Django checks, pytest, and ruff through uv.

## Local cleanup

Generated caches, discovery transcripts, whisper model downloads, and verification DB copies are not
part of the source tree. Remove them safely with:

```bash
make clean-artifacts
```

Voice notes, workbooks, and `db.sqlite3` stay on disk unless you delete them yourself. To reset the
local database entirely: `make clean-local-db` then `make setup` and `make load-data`.

## Production / Deployment

**Preferred path:** single **EC2** + **Caddy** + **gunicorn** — full steps in [`docs/operations/DEPLOYMENT_AWS.md`](docs/operations/DEPLOYMENT_AWS.md).

**Companion PDF** (gentle Console + CLI walkthrough): [`docs/reference/AWS_EC2_Deployment_Path_Field_Guide.pdf`](docs/reference/AWS_EC2_Deployment_Path_Field_Guide.pdf)

```bash
make prod-install      # uv sync --extra prod
make collectstatic
make prod-run          # gunicorn; expects production .env (DEBUG=false, DATABASE_URL, ...)
```

PaaS, Lightsail, and VPS alternatives are summarized at the **end** of `docs/operations/DEPLOYMENT_AWS.md`.
