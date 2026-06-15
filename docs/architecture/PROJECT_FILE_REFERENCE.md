# Project File Reference

This document explains the project structure and what each important file does.

It focuses on source files, project configuration, discovery outputs, and workflow files. It does not list every generated file inside `.venv/`, `.uv-cache/`, `__pycache__/`, `.pytest_cache/`, or `.ruff_cache/`.

## Visual Map

```text
Alireza/
|
|-- Makefile                         Local command pipeline
|-- README.md                        Quick start guide
|-- AGENTS.md                        Canonical agent/product instructions
|-- CLAUDE.md                        Pointer to AGENTS.md
|-- manage.py                        Django command entrypoint
|-- pyproject.toml                   Project metadata, dependencies, test/lint config
|-- uv.lock                          Locked dependency graph
|-- uv.toml                          Project-local uv config
|-- .python-version                  Python version for uv and local tools
|-- .env.example                     Example environment variables
|-- .gitignore                       Files Git should ignore
|
|-- config/                          Django project settings
|   |-- settings.py
|   |-- urls.py
|   |-- asgi.py
|   |-- wsgi.py
|   `-- __init__.py
|
|-- marketing/                       Main Django app
|   |-- models.py                    Database schema
|   |-- admin.py                     Django Admin panel setup
|   |-- permissions.py               Server-side RBAC helpers
|   |-- context_processors.py        Display language/digit preferences
|   |-- analytics.py                 Dashboard/report aggregation helpers
|   |-- reference_data.py            Data-sheet lookup seeding service
|   |-- forms.py                     Custom panel forms
|   |-- views.py                     Web views
|   |-- urls.py                      App routes
|   |-- apps.py                      App config
|   |-- importers/
|   |   |-- excel.py                 Excel import service
|   |   `-- __init__.py
|   |-- reports/
|   |   |-- pdf.py                   ReportLab PDF builder
|   |   `-- __init__.py
|   |-- management/commands/
|   |   |-- bootstrap_dev_admin.py   Local admin shortcut
|   |   |-- import_marketing_excel.py Excel import command
|   |   |-- seed_reference_data.py   Seed Data-sheet lookup rows
|   |   |-- seed_auth_groups.py      Create auth groups
|   |   `-- __init__.py
|   |-- migrations/
|   |   |-- 0001_initial.py          Initial database schema migration
|   |   |-- 0002_add_team_aliases.py Team alias model + canonical aliases
|   |   |-- 0003_canonical_campaign_names.py Campaign-name cleanup
|   |   |-- 0004_reference_lookup_models.py SpendCategory/SubTeam/Requester
|   |   `-- __init__.py
|   `-- tests/
|       |-- test_permissions.py
|       |-- test_excel_importer.py
|       |-- test_frontend_views.py
|       |-- test_phase2_features.py
|       `-- __init__.py
|
|-- templates/
|   |-- registration/login.html      Panel login
|   `-- marketing/                   Custom panel templates
|
|-- docs/
|   |-- PROJECT_BLUEPRINT.md
|   |-- CURRENT_STATE_AND_RUN_GUIDE.md
|   |-- PROJECT_FILE_REFERENCE.md
|   |-- discovery/
|   |   `-- column_mapping.yml       Importer mapping (tracked; other discovery outputs are local/gitignored)
|   `-- product/spec docs...
|
|-- .artifacts/                      Ignored local/generated artifacts
|   `-- voice-feedback/              Raw voice notes, WAV conversions, transcripts
|
|-- .agents/
|   `-- skills/audio-transcription/  Reusable Codex transcription skill
|
|-- data/                            Optional workbook drop folder
|-- imports/                         Optional workbook drop folder
`-- tools/                           Discovery helper scripts
```

## Root Files

### `Makefile`

Local command pipeline so you do not need to remember long Django commands.

It runs the project through `uv`, so commands use the locked dependency set from `pyproject.toml` and `uv.lock`.

Important commands:

```bash
make setup
make dev-admin
make import-dry-run
make import
make load-data-dry-run
make load-data
make run
make panel
make first-run
make check
```

This is the easiest way to run the project locally.

### `README.md`

Short quick-start guide. It links to the more detailed guide files.

Use this when you only need the basic commands.

### `AGENTS.md`

Standing instructions for coding agents working in this repo.

This is the highest-level project contract. It explains the product goal, mandatory discovery phase,
recommended stack, non-negotiable requirements, data model direction, access-control rules, dashboard
requirements, import rules, and definition of done.

Use this when:

```text
You want to know what the app is supposed to become.
You are asking an AI coding agent to continue the project.
You need to check whether a feature is required or optional.
```

### `CLAUDE.md`

Claude-specific project context generated during the Claude update.

Treat this as helper context, not the canonical product spec. If it conflicts with `AGENTS.md`,
`PROJECT_BLUEPRINT.md`, or the current code, prefer the latter.

### `manage.py`

Django command entrypoint.

Examples:

```bash
uv run python manage.py migrate
uv run python manage.py import_marketing_excel
uv run python manage.py runserver
```

Most of the time, use `make ...` instead.

### `pyproject.toml`

Main Python project configuration.

Defines:

```text
project name/version
supported Python version
runtime dependencies
dev dependency group
ruff lint configuration
pytest configuration
```

This is the standard dependency source for `uv`.

### `uv.lock`

Locked dependency graph generated by `uv lock` or `uv sync`.

Commit this file so local development and future deployment builds install the same dependency versions.

### `uv.toml`

Project-local uv config.

The Makefile points uv at this file so project commands do not depend on user-level uv configuration.

### `.python-version`

Declares the local Python version:

```text
3.13
```

uv and other local tools can use this when choosing an interpreter.

### `.env.example`

Example environment variables.

Current examples:

```text
DJANGO_DEBUG=true
DJANGO_SECRET_KEY=
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_DEFAULT_CURRENCY=IRR
```

This is a template only. Real secrets should go in `.env` or server environment variables later.

### `.gitignore`

Prevents generated/local files from being committed.

Examples:

```text
.venv/
.uv-cache/
db.sqlite3
media/
staticfiles/
__pycache__/
*.wav
```

## Django Project: `config/`

### `config/settings.py`

Main Django configuration.

Controls:

```text
Installed apps
Middleware
Templates
SQLite database
Static files
Media files
Timezone
Login URLs
Default currency
```

Right now the project uses SQLite for local development.

### `config/urls.py`

Top-level URL routing.

Current routes:

```text
/admin/  -> Django Admin
/        -> marketing app URLs
```

### `config/asgi.py`

ASGI entrypoint for async-capable servers.

You usually do not touch this during normal development.

### `config/wsgi.py`

WSGI entrypoint for production servers like Gunicorn.

This will matter later during deployment.

### `config/__init__.py`

Marks `config/` as a Python package.

Usually empty.

## Django App: `marketing/`

### `marketing/models.py`

Core database models.

Models currently defined:

```text
Team
TeamAlias
Vendor
SpendCategory
SubTeam
Requester
Campaign
BudgetLine
Invoice
InvoiceAttachment
UserTeamAccess
InvoiceStatusHistory
```

Important behavior:

```text
Invoice payment stage changes create InvoiceStatusHistory rows.
Paid invoices set paid_at automatically.
Vendors use normalized names to avoid duplicates.
SpendCategory, SubTeam, and Requester are lookup tables seeded from the Data sheet.
Invoices preserve source sheet/source row/raw row JSON.
```

### `marketing/admin.py`

Django Admin panel configuration.

Controls how models appear in `/admin/`:

```text
List columns
Filters
Search fields
Inline invoice attachments
Inline invoice status history
Autocomplete fields
```

This is why imported invoices, budget lines, vendors, teams, and access rules are visible in the panel.

### `marketing/permissions.py`

Central server-side access-control helpers.

Important functions:

```text
get_user_scope(user)
filter_invoices_for_user(queryset, user)
filter_budget_lines_for_user(queryset, user)
filter_campaigns_for_user(queryset, user)
can_edit_invoice(user, invoice)
can_upload_invoice_file(user, invoice)
can_upload_payment_proof(user, invoice)
can_export(user)
```

These will be used by the custom UI so users only see permitted data.

### `marketing/context_processors.py`

Adds display preferences to templates:

```text
ui_lang
number_locale
html_lang
html_dir
```

These power the `FA/EN` and `123/۰۱۲` top-bar buttons.

### `marketing/analytics.py`

Reusable server-side aggregation helpers for dashboard and report numbers.

Includes:

```text
monthly_spend_rows()
monthly_chart_data()
team_spend_rows()
team_chart_data()
overall_spend_pie()
vendor_grouped_rows()
attention_invoices()
```

These functions keep the chart/report math out of templates and make it reusable later for JSON API
endpoints.

### `marketing/reference_data.py`

Reads the workbook `Data` sheet and seeds lookup/reference rows:

```text
Vendor
SpendCategory
SubTeam
Requester
```

It uses `docs/discovery/column_mapping.yml`, normalizes names, supports dry-run mode, and upserts by
normalized name.

### `marketing/forms.py`

Forms for the custom panel.

Includes:

```text
Invoice create/edit form
Payment stage update form
Invoice attachment upload form
Excel workbook upload form
Admin user/access creation form
```

Important behavior:

```text
Users are created in the database, not .env.
Team/editor permissions are validated server-side.
Upload permissions are checked before accepting files.
```

Current caveat:

```text
SpendCategory, SubTeam, and Requester are seeded lookup models, but invoice forms are not fully
lookup-backed yet. Category is still free text; wiring seeded categories into dropdown/autocomplete
fields and validation is a future step.
```

### `marketing/views.py`

Current web views.

Current panel views:

```text
/login/
/
/teams/
/teams/<id>/
/invoices/
/vendors/
/campaigns/
/budgets/
/imports/
/users/
/exports/invoices.xlsx
/exports/vendors.xlsx
/exports/campaigns.xlsx
/reports/dashboard.pdf
/reports/invoices/print/
```

These views call `marketing/permissions.py` before showing, editing, uploading, importing, or exporting data.

### `marketing/urls.py`

Routes for the `marketing` app.

Currently:

```text
"" -> dashboard
"teams/" -> team list
"teams/<id>/" -> dedicated team dashboard
"invoices/" -> invoice list
"vendors/" -> vendor report
"campaigns/" -> campaign report
"budgets/" -> budget table/pivot
"imports/" -> Excel upload/import
"users/" -> user/access management
"exports/vendors.xlsx" -> vendor Excel export
"exports/campaigns.xlsx" -> campaign Excel export
"reports/dashboard.pdf" -> dashboard PDF export
```

Later this will include routes like:

```text
/invoices/
/vendors/
/campaigns/
/reports/
/imports/
```

### `marketing/apps.py`

Django app configuration.

Defines:

```text
MarketingConfig
```

Usually this file stays simple.

### `marketing/__init__.py`

Marks `marketing/` as a Python package.

Usually empty.

## Importer: `marketing/importers/`

### `marketing/importers/excel.py`

Reusable Excel import service.

This is the core import logic called by the management command.

It does:

```text
1. Finds workbook when --file is not supplied.
2. Reads docs/discovery/column_mapping.yml.
3. Opens XLSX with openpyxl.
4. Imports invoice rows.
5. Imports budget rows.
6. Creates teams/vendors/campaigns as needed.
7. Preserves raw row JSON.
8. Supports dry-run mode.
9. Reports skipped rows with reasons.
10. Re-runs idempotently: updates existing rows instead of duplicating.
```

Important discovery-specific behavior:

```text
Marketing Spend Input -> Invoice
Budget -> BudgetLine
Duplicate invoice number/vendor rows fall back to source sheet + row number
Referral rows map to cost_bucket=REFERRAL
Paid maps to PAID
Finance maps to FINANCE_REVIEW
```

### `marketing/importers/__init__.py`

Marks `importers/` as a Python package.

Usually empty.

## Management Commands

### `marketing/management/commands/bootstrap_dev_admin.py`

Creates or updates a local development admin user.

Used by:

```bash
make dev-admin
make panel
make first-run
```

Default local login:

```text
admin / admin12345
```

Safety behavior:

```text
Refuses to run when DEBUG=False.
```

This prevents the easy local password command from being used in production.

### `marketing/management/commands/import_marketing_excel.py`

Command wrapper around the Excel importer service.

Used by:

```bash
make import-dry-run
make import
```

Raw examples:

```bash
uv run python manage.py import_marketing_excel --dry-run
uv run python manage.py import_marketing_excel
uv run python manage.py import_marketing_excel --file ./imports/my-file.xlsx
```

It prints:

```text
Detected sheets
Selected invoice mapping
Selected budget mapping
Created/updated/skipped counts
Skipped-row reasons
```

### `marketing/management/commands/seed_auth_groups.py`

Creates baseline Django auth groups:

```text
Admin
Manager
Editor
Observer
```

Used by:

```bash
make setup
```

### `marketing/management/commands/seed_reference_data.py`

Command wrapper around the Data-sheet lookup seeding service.

Used by:

```bash
make seed-reference-dry-run
make seed-reference
```

Raw examples:

```bash
uv run python manage.py seed_reference_data --dry-run
uv run python manage.py seed_reference_data
uv run python manage.py seed_reference_data --file ./imports/my-file.xlsx
```

It prints created/updated/skipped counts for vendors, categories, sub-teams, and requesters.

### `marketing/management/__init__.py`

Marks `management/` as a Python package.

Required for Django to discover custom commands.

### `marketing/management/commands/__init__.py`

Marks `commands/` as a Python package.

Required for Django to discover custom commands.

## Migrations

### `marketing/migrations/0001_initial.py`

Initial database schema generated by Django.

Creates tables for:

```text
Team
Vendor
Campaign
BudgetLine
Invoice
InvoiceAttachment
UserTeamAccess
InvoiceStatusHistory
```

Do not edit this manually unless there is a very specific migration reason.

### `marketing/migrations/0002_add_team_aliases.py`

Adds `TeamAlias` and seeds the obvious workbook duplicate-team mappings.

### `marketing/migrations/0003_canonical_campaign_names.py`

Canonicalizes campaign labels such as `on going` into consistent campaign names.

### `marketing/migrations/0004_reference_lookup_models.py`

Adds lookup tables seeded from the workbook `Data` sheet:

```text
SpendCategory
SubTeam
Requester
```

### `marketing/migrations/__init__.py`

Marks `migrations/` as a Python package.

Usually empty.

## Tests

### `marketing/tests/test_permissions.py`

Tests role/scope behavior and invoice payment-stage history.

Examples:

```text
Admin can see all invoices.
Team editor only sees own team invoices.
Observer cannot edit invoices.
Referral/SMS requires explicit access or global access.
Payment stage changes create history rows.
Team aliases resolve imported duplicate team names.
```

### `marketing/tests/test_excel_importer.py`

Tests the Excel importer with a generated mini workbook.

Covers:

```text
Invoice import
Budget line import
Dry-run behavior
Duplicate invoice number/vendor handling
Re-import updates instead of duplicating
Referral bucket detection
Payment stage mapping
```

### `marketing/tests/test_frontend_views.py`

Tests the custom panel routing and high-risk permissions.

Covers:

```text
Admin dashboard rendering.
Team editor invoice scope.
Observer blocked from invoice creation.
Editor can create invoice only for their own team.
```

### `marketing/tests/test_phase2_features.py`

Tests the newer Phase 2 capabilities:

```text
Data-sheet reference seeding creates lookup rows.
Team dashboard access is scoped for an editor.
Admin can export vendor Excel, campaign Excel, and dashboard PDF.
```

### `marketing/tests/__init__.py`

Marks `tests/` as a Python package.

Usually empty.

## Templates

### `templates/marketing/base.html`

Shared RTL layout for the panel.

Contains:

```text
Sidebar navigation (grouped sections: Overview, Spend & teams, Reports, Administration, Help)
Responsive layout CSS
Table/form/card styling
Print styles
```

### `templates/marketing/help_sitemap.html`

In-app Help page (`/help/`). Mirrors `docs/guides/USER_SITEMAP.md` with RTL-friendly `nav_path` / `ui_flow` tags for FA.

### `templates/registration/login.html`

Standalone login page (split layout; links to Help).

### `templates/marketing/dashboard.html`

Main dashboard (**Finance overview**).

Current purpose:

```text
Compact filter toolbar + scope banner when one team is selected
Primary KPI cards (spend, budget, deviation, invoice count)
Secondary stat strip (paid, referral, SMS, contracts)
Paired budget-vs-actual and monthly-trend charts
Spend pie + spend-by-team row (all teams only)
Collapsible budget-by-team table
Vendor/campaign previews; payment stages; finance-review attention list
```

### `templates/marketing/teams/list.html`

Team index page with links to dedicated team dashboards.

### `templates/marketing/teams/dashboard.html`

Dedicated team dashboard with team totals, budget total, monthly chart, vendors, campaigns, and
attention invoices.

### `templates/marketing/invoices/`

Invoice list, create/edit form, and detail pages.

### `templates/marketing/vendors/report.html`

Vendor report sorted by total spend, with invoice counts, stages, and invoice numbers.

### `templates/marketing/campaigns/report.html`

Campaign spend report with table, simple bars, and monthly grid.

### `templates/marketing/budgets/list.html`

BudgetLine table plus Excel-like month pivot.

### `templates/marketing/imports/upload.html`

Admin-only browser upload, dry-run preview, and confirm import page.

### `templates/marketing/users/access.html`

Admin-only database-backed user and team access management page.

### `templates/marketing/print/invoice_report.html`

Browser-printable invoice report that can be saved as PDF.

## Reports

### `marketing/reports/pdf.py`

Builds server-rendered PDF bytes with ReportLab.

Current pattern:

```text
Django view gathers permission-scoped rows
        |
        v
build_dashboard_summary_pdf(...)
        |
        v
ReportLab SimpleDocTemplate + Paragraph/Table
        |
        v
HttpResponse(content_type="application/pdf")
```

Current limitation: the PDF uses simple English text and built-in fonts. Persian/RTL output needs a
Persian-capable font and deliberate RTL/shaping support.

## Documentation

The markdown files are split into five groups:

```text
Current operating docs        What to read today
Product/spec docs            What the product should satisfy
Discovery docs               What the real audio/workbook showed
Agent/helper docs            Prompts and AI workflow context
Deployment/AWS docs          How this becomes a real server
```

### Which docs to read first

```text
1. README.md
   Fast local start and command summary.

2. docs/guides/CURRENT_STATE_AND_RUN_GUIDE.md
   What works right now, how to run it, how to test it manually.

3. docs/guides/PROJECT_EXPLAINED.md
   Plain-language walkthrough of Django concepts and this project's flow.

4. docs/architecture/PROJECT_FILE_REFERENCE.md
   This map of every important file.

5. docs/architecture/PROJECT_BLUEPRINT.md
   Current product direction and chosen AWS path.

6. docs/operations/DEPLOYMENT_AWS.md
   EC2 + Caddy first, then RDS, then S3.
```

### `docs/architecture/PROJECT_BLUEPRINT.md`

Current product direction and decision log.

This is the best file for answering:

```text
What is the app trying to become?
What feedback has been incorporated?
What stack decisions have been made?
What are the next build phases?
What deployment path did we choose?
```

Current deployment decision captured there:

```text
EC2 + Caddy + Gunicorn first
then RDS PostgreSQL
then S3 media uploads
serverless later only if the requirements change
```

### `docs/guides/CURRENT_STATE_AND_RUN_GUIDE.md`

Practical status and runbook for local use.

Use this when you want to:

```text
Understand what exists today.
Run the project locally.
Import or seed the workbook data.
Check current URLs.
Manually test admin/editor/viewer behavior.
See which roadmap phases are done vs pending.
```

### `docs/guides/PROJECT_EXPLAINED.md`

Guided tour written for your learning style.

It maps this Django app to concepts you already know from Python, SQLAlchemy, FastAPI, Docker, and
your notebooks. It also explains request flow, QuerySets, permissions, importer behavior, bilingual
UI, CSRF, and the main commands.

Use this when the codebase feels abstract and you want the mental model.

### `docs/architecture/PROJECT_FILE_REFERENCE.md`

This file.

It is the table of contents for the repository. It explains the role of root files, Django files,
templates, markdown docs, discovery outputs, generated files, and safe modification workflows.

### `docs/project/PHASE_2.md`

Current Phase 2 status and next-step plan.

Use this when deciding what to build next. It lists what Claude/this phase already added:

```text
Data-sheet reference seeding
Team dashboards
Monthly/team Chart.js charts
Vendor/campaign Excel exports
ReportLab dashboard PDF
```

It also lists remaining work:

```text
Budget planned-vs-actual
Reference management UI
Lookup-backed forms
Upload hardening
Persian/RTL PDFs
CI/CD
AWS deployment
```

### `docs/operations/DEPLOYMENT_AWS.md`

App-specific AWS deployment runbook (preferred path: **EC2 + Caddy + gunicorn**).

Companion PDF for a gentler Console + CLI walkthrough:
`docs/reference/AWS_EC2_Deployment_Path_Field_Guide.pdf`

Upgrade order after the single box works:

```text
1. EC2 + Caddy + gunicorn
2. RDS PostgreSQL
3. S3 for uploads
4. CloudWatch + CI/CD
5. ALB / Terraform only if needed
```

PaaS, Lightsail, and VPS alternatives are in the appendix at the end of the runbook.

### `docs/operations/ACCESS_BY_ROLE.md`

Human-readable RBAC guide.

Use this when asking:

```text
What can Admin, Manager, Editor, or Observer do?
Which users can export?
Who can upload invoice files or payment proofs?
What should team-limited users see?
```

### `docs/specs/PRODUCT_REQUIREMENTS.md`

Original product-level requirements.

Use this as the broad product reference when checking whether the app still reflects the business
request: dashboards, users, access control, Excel import, invoice tracking, exports, referral/SMS
separation, and campaign/vendor reporting.

### `docs/architecture/DATA_MODEL.md`

Original data-model design.

The current Django models were built from this. Use it when checking why tables such as `Invoice`,
`BudgetLine`, `UserTeamAccess`, `InvoiceAttachment`, and `InvoiceStatusHistory` exist.

### `docs/specs/RBAC_SPEC.md`

Original role/access-control specification.

The permission helper functions in `marketing/permissions.py` were built from this. Use it when
changing role behavior or adding a new permission.

### `docs/specs/EXCEL_IMPORT_SPEC.md`

Original Excel import requirements.

Use this when changing importer behavior. It explains mapping, aliases, skipped-row reporting,
idempotency, raw-row traceability, and why the database becomes the source of truth after import.

### `docs/specs/DASHBOARD_SPEC.md`

Dashboard and analysis requirements.

Use this when adding BI features. It describes expected cards, charts, vendor reports, campaign
reports, payment-stage summaries, and budget analysis.

### `docs/guides/DEVELOPER_NOTES.md`

General developer notes.

Use this for implementation reminders that do not belong in product specs or the run guide.

### `docs/specs/AUDIO_TRANSCRIPTION_AND_XLSX_DISCOVERY.md`

Discovery workflow specification.

This guided the first mandatory phase: transcribe audio, inspect the workbook, create
`docs/discovery/column_mapping.yml`, and document import risks before implementing importer logic.

## Discovery Files

### `.artifacts/voice-feedback/`

Ignored local folder for raw voice feedback files:

```text
.artifacts/voice-feedback/audio/        source .ogg/.mp3/.m4a files
.artifacts/voice-feedback/converted/    generated .wav conversions
.artifacts/voice-feedback/transcripts/  generated transcript markdown
```

Durable decisions from voice notes should be copied into `docs/architecture/PROJECT_BLUEPRINT.md` and
`docs/guides/CURRENT_STATE_AND_RUN_GUIDE.md`, including:

```text
Data sheet is lookup/reference data.
Vendors should be managed in the app UI.
Duplicate team names need alias rules.
BudgetLine should stay normalized in the DB.
The budget UI should offer an Excel-like horizontal pivot table.
Managers are view/report users; Editors are scoped data-entry users.
Shamsi/Jalali dates must parse correctly.
Money/amount display needs QA when Persian digits or table layouts change.
```

### `docs/discovery/workbook_structure.md`

Inventory of workbook sheets, columns, headers, hidden columns, formulas, merged headers, and likely sheet purpose.

### `docs/discovery/workbook_sample_rows.md`

Sample rows and normalized columns from relevant workbook sheets.

### `docs/discovery/column_mapping.yml`

Anonymized **import template** (column headers, row ranges, rules). Consumed by the importer and
merged with optional gitignored `column_mapping.local.yml`.

Sheet resolution: mapped tab name → aliases → header auto-detection. **UI data** (team/vendor
names) comes from imported workbook rows, not from example labels in this file.

```text
If workbook structure changes, update the mapping (or your local override) before importing.
```

See also: `docs/discovery/README.md` and `column_mapping.local.yml.example`.

### `docs/discovery/import_risks.md`

Known import risks and open questions.

Examples:

```text
Formula risks
Date parsing risks
Duplicate invoice numbers
SMS actual spend not present in invoice sheet
Budget merged headers
```

### `docs/discovery/*.wav`

Generated WAV conversions used for transcription.

Generated artifact. It is ignored by Git.

## Codex Skill Files

### `.agents/skills/audio-transcription/SKILL.md`

Reusable Codex skill instructions for audio transcription.

Use when future work includes an audio file and needs:

```text
Transcript
Summary
Requirements extraction
```

### `.agents/skills/audio-transcription/scripts/transcribe_audio.py`

Helper script bundled with the transcription skill.

It can:

```text
Convert .ogg/.oga to .wav
Use OpenAI speech-to-text if OPENAI_API_KEY exists
Fallback to local Whisper/faster-whisper
Write markdown transcript output
```

### `.agents/skills/audio-transcription/agents/openai.yaml`

UI metadata for the Codex skill.

Usually not edited manually unless skill display text changes.

## Data Folders

### `data/.gitkeep`

Keeps the `data/` folder in the project.

You can place workbooks here:

```text
data/my-workbook.xlsx
```

### `imports/.gitkeep`

Keeps the `imports/` folder in the project.

You can place workbooks here:

```text
imports/my-workbook.xlsx
```

## Tool Scripts

### `tools/inspect_xlsx_structure.py`

Discovery helper script that inspects XLSX files without modifying them. Writes local markdown under
`docs/discovery/` (gitignored except `column_mapping.yml`).

Transcription uses `make transcribe-audio` / `.agents/skills/audio-transcription/scripts/transcribe_audio.py`.

## Local Generated Files

These are useful locally but should not be treated as source files.

### `.venv/`

Python virtual environment.

Created by:

```bash
make setup
```

Do not edit manually.

### `.uv-cache/`

Project-local uv package cache.

The Makefile sets `UV_CACHE_DIR=.uv-cache` so dependency cache files stay inside the project workspace and are ignored by Git.

### `db.sqlite3`

Local SQLite database.

Contains imported local data.

For production, this should become PostgreSQL.

### `__pycache__/`

Python bytecode cache directories.

Generated automatically.

### `.pytest_cache/`

Pytest cache.

Generated automatically.

### `.ruff_cache/`

Ruff lint cache.

Generated automatically.

### `media/`

Future upload folder for invoice images/payment proofs.

Ignored by Git.

### `staticfiles/`

Future collected static files folder.

Ignored by Git.

## Source Workbook and Audio

### `marketing_spend_workbook.xlsx`

Current real workbook used for discovery and import.

Imported with:

```bash
make load-data
```

### Raw Audio Notes

```text
.artifacts/voice-feedback/audio/
.artifacts/voice-feedback/transcripts/
```

Raw audio notes and generated transcripts are local ignored artifacts. They are useful for
traceability, but they are not part of the runtime project.

## How To Read This Project

Recommended order:

```text
1. README.md
2. docs/guides/CURRENT_STATE_AND_RUN_GUIDE.md
3. docs/architecture/PROJECT_FILE_REFERENCE.md
4. docs/discovery/column_mapping.yml
5. marketing/models.py
6. marketing/importers/excel.py
7. marketing/permissions.py
8. marketing/admin.py
```

## How To Modify This Project Safely

### Adding Database Fields

```text
1. Edit marketing/models.py
2. Run makemigrations
3. Run migrate
4. Update admin/tests/importer if needed
```

Commands:

```bash
uv run python manage.py makemigrations
uv run python manage.py migrate
make check
```

### Changing Excel Import Mapping

```text
1. Update docs/discovery/column_mapping.yml
2. Run make load-data-dry-run
3. Review skipped-row reasons
4. Run make load-data
5. Run make check
```

### Adding UI Pages

```text
1. Add view in marketing/views.py or a new views module
2. Add route in marketing/urls.py
3. Add template under templates/marketing/
4. Use marketing/permissions.py to filter querysets
5. Add tests
```

### Adding Dashboard Analysis

Recommended future structure:

```text
marketing/services/
  analytics.py

marketing/views/
  dashboards.py

templates/marketing/dashboard/
  overview.html
  team.html
```

Keep chart data server-side aggregated and permission-filtered.
