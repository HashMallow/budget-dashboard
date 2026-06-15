# Current State and Run Guide

This document explains what exists right now, how the pieces fit together, and how to test the app locally.

## Doc map (start here)

| If you need… | Read |
|---|---|
| Run the app locally | This file — **Setup** and **Make commands** below |
| What to build next | [`PHASE_2.md`](PHASE_2.md) |
| Deploy to AWS / production | [`DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md) |
| Codebase tour | [`PROJECT_EXPLAINED.md`](PROJECT_EXPLAINED.md) |
| Roles and permissions | [`ACCESS_BY_ROLE.md`](ACCESS_BY_ROLE.md) / [`PERMISSIONS_MATRIX.md`](PERMISSIONS_MATRIX.md) |
| Excel import rules | [`EXCEL_IMPORT_SPEC.md`](EXCEL_IMPORT_SPEC.md) + `docs/discovery/column_mapping.yml` |
| Agent/build instructions | [`../AGENTS.md`](../AGENTS.md) |

## Big Picture

```text
Audio note + Excel workbook
          |
          v
Discovery documents
docs/discovery/
          |
          v
Column mapping
docs/discovery/column_mapping.yml
          |
          v
Excel importer
marketing/importers/excel.py
          |
          v
SQLite database
db.sqlite3
          |
          v
Custom Django panel
/
          |
          v
Django Admin fallback
/admin/
```

The app now has a minimal custom panel for non-technical users. Django Admin remains available as a fallback for low-level maintenance.

Local commands now run through `uv`, using `pyproject.toml` and `uv.lock` as the standard dependency setup.

The workbook `Data` sheet has its own reference-data path: `make seed-reference` seeds lookup rows,
while the main importer continues to handle invoice and budget facts.

Important distinction:

```text
make import
  Imports invoice and budget facts only.

make seed-reference
  Seeds lookup/reference rows from the Data sheet.

make load-data
  Runs both steps and is the safest fresh-database workflow.
```

## Current Project Structure

```text
Alireza/
├── AGENTS.md / CLAUDE.md          Agent instructions
├── README.md
├── Makefile                        uv-based dev/prod commands
├── manage.py
├── pyproject.toml                  deps (+ optional 'prod' extra) and tool config
├── uv.lock / uv.toml / .python-version
├── db.sqlite3                      local dev database (gitignored)
├── your_workbook.xlsx   source workbook for import (gitignored)
│
├── config/
│   ├── settings.py                 env-driven; flips to prod mode when DJANGO_DEBUG=false
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py                      gunicorn entrypoint: config.wsgi:application
│
├── marketing/
│   ├── models.py                   Team, Vendor, Campaign, BudgetLine, Invoice, ...
│   ├── admin.py
│   ├── analytics.py                server-side dashboard/report aggregation helpers
│   ├── reference_data.py           Data-sheet lookup seeding service
│   ├── views.py                    panel views (dashboard, CRUD, reports, exports)
│   ├── reference_views.py          admin reference-data CRUD (/reference/)
│   ├── urls.py
│   ├── forms.py                    invoice + user-access forms (with FA/EN labels)
│   ├── permissions.py              server-side RBAC scope/queryset filtering
│   ├── translations.py             EN→FA UI string catalog
│   ├── context_processors.py       injects UI language / number locale into templates
│   ├── jalali.py                   Gregorian↔Jalali helpers for month/year grouping
│   ├── templatetags/marketing_format.py   {% t %}, form_errors, stage/bucket labels
│   ├── importers/excel.py          workbook → DB importer (aliases, canonicalization)
│   ├── reports/pdf.py              ReportLab PDF builder (FA/EN, RTL)
│   ├── reports/pdf_fonts.py        Vazirmatn registration + Persian shaping
│   ├── management/commands/
│   │   ├── bootstrap_dev_admin.py
│   │   ├── import_marketing_excel.py
│   │   ├── seed_reference_data.py
│   │   └── seed_auth_groups.py
│   ├── migrations/                 0001_initial through 0004_reference_lookup_models
│   └── tests/                      importer, permissions, frontend, and phase-2 feature tests
│
├── templates/
│   ├── registration/login.html
│   └── marketing/                  base.html + dashboard, invoices/, vendors/, campaigns/,
│                                   teams/, budgets/, contracts/, reference/, imports/, users/
│
├── docs/
│   ├── PROJECT_EXPLAINED.md         guided tour of the codebase
│   ├── PROJECT_BLUEPRINT.md
│   ├── PROJECT_FILE_REFERENCE.md
│   ├── ACCESS_BY_ROLE.md            who can see/do what per role
│   ├── DEPLOYMENT_AWS.md            deploy-this-app runbook + alternatives
│   ├── CURRENT_STATE_AND_RUN_GUIDE.md   (this file)
│   ├── DATA_MODEL.md / RBAC_SPEC.md / EXCEL_IMPORT_SPEC.md / ... (specs)
│   └── discovery/                  audio transcripts, workbook structure, column_mapping.yml
│
├── data/  imports/                 drop-zones for workbooks (each has a .gitkeep)
├── media/                          uploaded invoice/payment images (gitignored)
└── tools/                          one-off discovery scripts (transcribe, inspect xlsx)
```

## Current Capabilities

### Working Now

```text
[x] Audio transcription/discovery documentation
[x] Follow-up voice feedback documentation
[x] Workbook structure discovery
[x] Column mapping based on the real workbook
[x] Django project setup
[x] uv dependency workflow
[x] Local SQLite database
[x] Core data models
[x] Django Admin panel
[x] Custom panel login/dashboard shell
[x] Persian/English shell toggle and Persian digit display toggle
[x] Invoice list/detail/create/edit pages
[x] Payment stage update page action
[x] Invoice/payment proof upload controls
[x] Vendor report page
[x] Campaign report page
[x] Budget table and pivot page
[x] Browser Excel upload dry-run/confirm page
[x] Admin user/access creation page
[x] Team alias model, seeded aliases, and importer alias resolution
[x] Auth groups: Admin, Manager, Editor, Observer
[x] Local admin bootstrap command
[x] Excel import command
[x] Dry-run import mode
[x] Idempotent re-import behavior
[x] Server-side permission helper functions
[x] Tests for permissions, status history, and importer behavior
[x] Makefile command pipeline
[x] Full bilingual (FA/EN) UI: static text, form labels/choices, and validation messages
[x] Persian-digit display in FA mode (display-only; form inputs stay Latin)
[x] Jalali (Persian-calendar) month/year grouping and year filters in reports
[x] Shamsi/Jalali date parsing in Excel import and invoice forms (`1405/01/10`, `۱۴۰۵/۰۱/۱۰`, and Gregorian ISO)
[x] Overall-spend pie chart (Chart.js doughnut; hidden when a single team is filtered on the main dashboard)
[x] Sectioned sidebar navigation (Overview / Spend & teams / Reports / Administration / Help at bottom)
[x] In-app Help page at `/help/` (mirrors USER_SITEMAP; RTL-friendly navigation paths in FA)
[x] Invoice `business_section` field (business segments from Excel Business Section) — filter, search, import, export
[x] Finance overview dashboard layout (primary KPI cards, stat strip, paired budget/trend charts, collapsible team budget table)
[x] Campaign reference CRUD in panel (`/reference/campaigns/`)
[x] Persian PDF reports: arabic-reshaper only (no python-bidi reversal) for correct RTL words in ReportLab
[x] Excel export of the (permission-filtered) invoice table
[x] Printable invoice report page (browser print-to-PDF)
[x] Campaign-name canonicalization (e.g. "on going" -> "Ongoing") in importer + data migration
[x] Production settings wiring: DATABASE_URL switch, WhiteNoise, HTTPS/security headers, logging
[x] Optional 'prod' dependency extra (gunicorn, psycopg, whitenoise, dj-database-url)
[x] Make targets for dev auto-reload and production (dev, prod-install, collectstatic, prod-run)
[x] Data sheet reference seeding (`make seed-reference`) into SpendCategory, SubTeam, Requester (+ vendors)
[x] Dedicated team dashboards at `/teams/` and `/teams/<id>/`
[x] Monthly trend (line) and per-team (bar) Chart.js charts on the main dashboard
[x] Vendor and campaign Excel exports (permission-scoped)
[x] Server-rendered PDF reports via ReportLab (`/reports/*.pdf`) with Persian/RTL + Vazirmatn when UI is FA
[x] Contract tracking UI (`/contracts/`) with stages, expiry, and attachments
[x] Reference-data management UI (`/reference/`) for vendors, categories, sub-teams, requesters (admin)
[x] Budget planned-vs-actual variance table and chart on main and team dashboards
[x] Budget planned-by-month and planned-by-team charts on `/budgets/`
[x] Workbook-style Excel export that recreates the source workbook's sheets (`/exports/workbook.xlsx`)
[x] Consolidated Settings menu in the top bar (language, amount format, currency unit, theme)
[x] Compact/full amount display toggle (e.g. 84.3B vs 84,276,543,010) with exact value on hover
[x] Rial/Toman currency display toggle (display-only; stored values stay in Rial)
[x] Light/Dark theme toggle (persisted per session)
[x] همت (hezar milliard) compact label for trillion-tier amounts in Toman mode
```

### Partially Working

```text
[~] Invoice category field is still free text; seeded SpendCategory rows are not yet enforced dropdowns.
[~] Budget variance is by month and team; category-level variance from Budget sheet titles is not built yet.
[~] Campaign CRUD exists in the panel at `/reference/campaigns/` (and links from the campaign report); Django Admin remains a fallback.
[~] Lookup rows can be managed at `/reference/` or via `make seed-reference`; not every form validates against them yet.
[~] PDF exports support Persian shaping (Vazirmatn + arabic-reshaper); layout polish can still improve.
[~] Media uploads use local `media/`; S3 production storage is documented but not provisioned.
```

### Not Built Yet

```text
[ ] Separate React front-end (planned later, consumes the same data)
[ ] Live AWS deployment (settings are ready; infra not provisioned yet — see docs/operations/DEPLOYMENT_AWS.md)
[ ] JSON API endpoints for a future React front-end
```

## Data Model Overview

```text
Team
  |
  |----< Invoice >---- Vendor
  |         |
  |         |---- Campaign
  |         |
  |         |----< InvoiceAttachment
  |         |
  |         |----< InvoiceStatusHistory
  |
  |----< BudgetLine
  |
  |----< UserTeamAccess >---- User

Data sheet lookup rows
  |
  |---- Vendor
  |---- SpendCategory
  |---- SubTeam
  `---- Requester
```

### Main Models

```text
Team
  Marketing team or department.

Vendor
  Supplier/vendor used by invoices.

SpendCategory
  Lookup/category title seeded from the workbook Data sheet.

SubTeam
  Lookup sub-team label seeded from the workbook Data sheet.

Requester
  Lookup requester/person label seeded from the workbook Data sheet.

Campaign
  Marketing campaign, usually tied to year and optionally team.

BudgetLine
  Planned monthly budget imported from the Budget sheet.

Invoice
  Actual spend/invoice record imported from Marketing Spend Input.

InvoiceAttachment
  Future invoice image/payment proof file support.

InvoiceStatusHistory
  Records payment stage changes.

UserTeamAccess
  Team-level access control for Manager, Editor, Observer users.
```

## Import Flow

```text
Workbook in root/data/imports
          |
          v
make import-dry-run
          |
          |  Shows what will be created/updated/skipped
          v
Review output
          |
          v
make import
          |
          v
Database updated
```

The importer reads:

```text
docs/discovery/column_mapping.yml          (tracked anonymized template)
docs/discovery/column_mapping.local.yml    (optional gitignored overrides)
```

Resolution order for invoice/budget tabs: mapped name → aliases → header auto-detection when the
workbook tab name differs from the template.

The importer currently targets:

```text
Invoices from: invoice sheet (template name: Marketing Spend Input; auto-detects real tab)
Budget lines from: Budget
Reference behavior from: Data
Summary sheet ignored for import: Market Live Spending
```

After import, the database holds your workbook's real team/vendor/business-line names. Generic
wording in help text or the YAML template does not replace that data.

Example counts from a sample import:

```text
Teams: 8
Vendors: 25
Campaigns: 5
Invoices: 51
Budget lines: 1639
```

Payment stages imported:

```text
PAID: 39
FINANCE_REVIEW: 12
```

Cost buckets imported:

```text
TEAM: 49
REFERRAL: 2
SMS: 0 actual invoice rows found so far
```

## Follow-Up Voice Feedback Captured

Raw voice notes, WAV conversions, and raw transcripts are kept outside the main docs tree:

```text
.artifacts/voice-feedback/
```

That directory is ignored by Git. Durable product decisions from those notes are summarized below
and in `docs/architecture/PROJECT_BLUEPRINT.md`.

Decisions to carry into the next implementation phase:

```text
Data sheet
  Treat as lookup/reference data, not as a main invoice or budget table.
  Seed vendors, categories, sub-teams, and requesters with `make seed-reference`.

Vendor management
  Add/remove vendors in the app UI, not by editing the Excel Data sheet.

Team aliases
  Implemented as database-backed TeamAlias rows.
  Example aliases: Operations & Analysis -> Ops & Analytics; Team Beta (PR) -> Team Beta.

BudgetLine UI
  Keep normalized rows in the database.
  Build an Excel-like pivot table with horizontal month scrolling for humans.

Roles
  Manager should be closer to Observer than Admin/Editor: strong view/report access, little or no edit access.
  Observer should remain read-only.
  Editor should be the role that can enter/import/update data within its assigned scope.

Dates and amounts
  Shamsi/Jalali dates must be parsed correctly instead of being misread as Gregorian years.
  Amount columns and money display need QA whenever Persian digits or narrow tables are changed.
```

## How To Run Locally

Run these commands from the project root:

```bash
cd /path/to/Alireza
```

### Prerequisites

The repo uses a `Makefile` for common tasks (`make setup`, `make run`, `make check`, etc.). Install `make` before running those commands.

**macOS** — if `make` is missing (`command not found: make`), install developer tools first:

```bash
xcode-select --install
```

Or with Homebrew:

```bash
brew install make
```

Check:

```bash
make --version
```

Also install [uv](https://docs.astral.sh/uv/) if you do not have it yet:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Without `make`, use the raw `uv run python manage.py …` commands documented under each section below and in [`../README.md`](../README.md).

### First-Time Setup

```bash
make setup
```

This does:

```text
1. Uses uv to sync the locked Python environment
2. Installs runtime and dev dependencies from pyproject.toml/uv.lock
3. Runs database migrations
4. Creates baseline auth groups
```

### Create Local Admin Login

```bash
make dev-admin
```

Default local login:

```text
username: admin
password: admin12345
```

This is for local development only. The command refuses to run when `DEBUG=False`.

### Import Workbook

Preview first:

```bash
make import-dry-run
```

Then import:

```bash
make import
```

If there is more than one workbook:

```bash
make import-dry-run FILE=./imports/my-workbook.xlsx
make import FILE=./imports/my-workbook.xlsx
```

### Seed Data-Sheet References

Preview first:

```bash
make seed-reference-dry-run
```

Then seed:

```bash
make seed-reference
```

This reads the workbook `Data` sheet through `docs/discovery/column_mapping.yml` and creates or
updates:

```text
Vendor
SpendCategory
SubTeam
Requester
```

The current local database has been seeded with:

```text
Vendors: 123 total
Spend categories: 38
Sub-teams: 15
Requesters: 27
```

Dry-run counts are useful as a preview, but they count repeated workbook cells before database
writes happen, so the final created/updated/skipped numbers can be lower.

### Start The Local Panel

```bash
make run
```

Open:

```text
http://127.0.0.1:8000/login/
```

Login:

```text
username: admin
password: admin12345
```

If port 8000 is busy:

```bash
make run PORT=8001
```

Then open:

```text
http://127.0.0.1:8001/login/
```

### One-Command Local Panel Shortcut

After setup:

```bash
make panel
```

This creates/updates the local admin and starts the server.

### Full First-Run Shortcut

```bash
make first-run
```

This runs:

```text
setup -> dev-admin -> load-data -> run
```

## How To Test The App Manually

### 1. Check Admin Login

Open:

```text
http://127.0.0.1:8000/login/
```

Login with:

```text
admin / admin12345
```

Expected result:

```text
Custom panel opens successfully.
Sectioned sidebar: Overview, Spend & teams, Reports, Administration (admin), Help at bottom.
Dashboard, invoices, vendors, campaigns, budgets, imports, and users are visible as permitted.
```

### 2. Check Imported Data

In the custom panel, open:

```text
Dashboard (Finance overview)
├── Invoices (incl. business line filter)
├── Teams
├── Reports: Budget · Vendors · Campaigns · Contracts
├── Administration: Imports · Users · Reference data
└── Help (bottom of menu)
```

Expected counts:

```text
Core imported invoice/budget facts:
Teams: 8
Vendors: 25
Campaigns: 5
Invoices: 51
Budget lines: 1639

After `make seed-reference`:
Vendors: 123 total
Spend categories: 38
Sub-teams: 15
Requesters: 27
```

### 3. Check Invoice Filters

Open:

```text
Marketing -> Invoices
```

Try filters:

```text
payment_stage = PAID
payment_stage = FINANCE_REVIEW
cost_bucket = TEAM
cost_bucket = REFERRAL
team = Team Alpha
team = Team Beta
```

Expected result:

```text
Filters should return matching invoice rows.
```

### 4. Check Re-Import Safety

Run:

```bash
make import
```

Expected result:

```text
Invoices: created=0, updated=51
Budget lines: created=0, updated=1639
```

This means the importer updates existing records instead of duplicating them.

### 5. Check Automated Tests

Run:

```bash
make check
```

Expected result:

```text
Django check passes
Tests pass
Ruff lint passes
```

Current result:

```text
94+ tests passed (pytest -q), 1 skipped when LibreOffice conversion is unavailable locally
```

## Current Make Commands

```text
make help
  Show available commands.

make setup
  Sync uv dependencies, migrate database, seed auth groups.

make dev-admin
  Create/update local admin user: admin / admin12345.

make import-dry-run
  Preview Excel import without database writes.

make import
  Import/update Excel data into the database.

make load-data-dry-run
  Preview both the main invoice/budget import and the Data-sheet reference seed.

make load-data
  Run the main invoice/budget import, then seed Data-sheet lookup rows.

make seed-reference-dry-run
  Preview Data-sheet lookup seeding without database writes.

make seed-reference
  Seed vendors, categories, sub-teams, and requesters from the workbook Data sheet.

make transcribe-audio AUDIO=voice.ogg
  Local voice-note transcription. Auto-uses the GPU when available, else CPU.

make transcribe-voice AUDIO=.artifacts/voice-feedback/audio/note.ogg
  Transcribe into the `.artifacts/voice-feedback/` layout (audio / converted / transcripts).

make transcribe-audio-gpu AUDIO=voice.ogg [TRANSCRIPT_MODEL=large-v3]
  Force GPU (CUDA, float16) transcription.

make transcribe-audio-high AUDIO=voice.ogg
  Highest accuracy: large-v3 on the GPU (~3 GB VRAM in float16).

make run
  Start local Django server (no auto-reload).

make dev
  Start local Django server WITH auto-reload (picks up code changes automatically).

make panel
  Create/update local admin and start server.

make first-run
  Setup, create local admin, import workbook, start server.

make check
  Run Django checks, tests, and lint.

make shell
  Open Django shell.

make prod-install
  uv sync with the 'prod' extra (gunicorn, psycopg, whitenoise, dj-database-url).

make collectstatic
  Collect static files into STATIC_ROOT (for production static serving).

make clean-artifacts
  Remove __pycache__, pytest/ruff caches, staticfiles, discovery WAV artifacts.

make clean-local-db
  Delete db.sqlite3 (destructive). Re-run make setup and make dev-admin afterward.

Variables:
  FILE=workbook.xlsx     Pass when multiple .xlsx files exist
  HOST=127.0.0.1         Server bind host (make dev / make run / make prod-run)
  PORT=8000              Server port (e.g. make dev PORT=8001)
  ADMIN_USER / ADMIN_PASSWORD / ADMIN_EMAIL   For make dev-admin
```

Raw command equivalent when you do not want to use `make`:

```bash
uv run python manage.py migrate
uv run python manage.py seed_auth_groups
uv run python manage.py import_marketing_excel --dry-run
uv run python manage.py seed_reference_data --dry-run
uv run python manage.py runserver 127.0.0.1:8000 --noreload
```

## Current Panel Routes

```text
/login/                        Login
/help/                         In-app guide (public; mirrors USER_SITEMAP.md)
/                              Finance overview dashboard (sectioned layout; pie hidden when team filtered)
/teams/                        Team list with links to per-team dashboards
/teams/<id>/                   Team dashboard (budget variance, vendors, campaigns, monthly chart)
/invoices/                     Invoice list/create/detail/edit (business line filter + search)
/vendors/                      Vendor spend report (descending)
/campaigns/                    Campaign spend report
/budgets/                      Budget table, pivot, and planned-budget charts
/contracts/                    Contract list/create/detail/edit/stage/attachments
/reference/                    Admin-only lookup CRUD hub
/reference/vendors/            Manage vendor reference rows
/reference/categories/         Manage spend categories
/reference/sub-teams/          Manage sub-teams
/reference/campaigns/          Manage campaigns (admin)
/reference/requesters/         Manage requesters
/imports/                      Admin-only Excel upload/import
/users/                        Admin-only user/access management
/exports/invoices.xlsx         Excel export of filtered invoices (needs can_export)
/exports/vendors.xlsx          Excel export of vendor report
/exports/campaigns.xlsx        Excel export of campaign report
/exports/contracts.xlsx        Excel export of contract list
/exports/workbook.xlsx         Workbook-style Excel (source-workbook sheet layout)
/reports/dashboard.pdf         Dashboard PDF summary (ReportLab; FA shaping via Vazirmatn)
/reports/vendors.pdf           Vendor spend PDF
/reports/campaigns.pdf         Campaign spend PDF
/reports/contracts.pdf         Contract report PDF
/reports/invoices/print/       Printable invoice report (browser print)
/admin/                        Django Admin fallback
/preferences/                  Set display preferences (language, amount format, currency unit, theme)
```

**Sidebar sections:** Overview · Spend & teams · Reports · Administration (admin) · Help (bottom).

**Workbook export (`.xlsx`):** Generated by `marketing/exports/workbook.py` with Excel-safe cells,
explicit auto-filter bounds, and regression tests in `marketing/tests/test_workbook_export.py`.
Exports are meant to open cleanly in Microsoft Excel and Google Sheets.

Users are database records, not environment variables. Use `/users/` as an admin to create users, assign Admin/Manager/Editor/Observer roles, grant team/global access, and deactivate users. `.env` is for deployment settings and secrets such as `DJANGO_SECRET_KEY`, database URLs, and allowed hosts.

Use the **Settings** menu (⚙) in the top bar to change display preferences: UI language (FA/EN), amount format (compact vs full), currency unit (Rial vs Toman), and theme (light/dark). The whole UI is translated — navigation, page headers, table columns, card labels, form field labels and choices, and validation messages. In Persian mode, displayed numbers are rendered as Persian digits (display only; form inputs keep Latin digits so submitted data is unaffected). Currency and amount-format choices are display-only and never change the stored Rial values, so exports remain exact.

## Development Roadmap

> Status is tracked against reality below. The "Current Capabilities" section above is the
> authoritative list of what runs today; the phases here show the original plan and how far each got.

### Phase 1: Basic Custom UI — DONE

Goal: move beyond Django Admin for everyday usage.

```text
1. Add login/logout pages.
2. Add base layout and navigation.
3. Add invoice list page.
4. Add invoice detail page.
5. Add team/vendor/campaign list pages.
6. Add team alias management.
7. Add admin fallback and lookup seeding for vendors/categories/sub-teams; richer management screens later.
8. Apply server-side permission filters to every page.
```

Recommended first screens:

```text
Dashboard shell
  |
  |-- Invoice list
  |-- Invoice detail
  |-- Vendor list
  |-- Campaign list
  |-- Budget list
  |-- Team aliases
  |-- Import status page
```

### Phase 2: Browser-Based Excel Upload — DONE

Goal: let an admin upload Excel through the UI instead of using terminal commands.

```text
1. Add admin-only upload page.
2. Upload workbook to media/imports/.
3. Run dry-run import.
4. Show preview: created/updated/skipped counts.
5. Show skipped-row reasons.
6. Add confirm button.
7. Run actual import after confirmation.
```

Flow:

```text
Admin uploads workbook
        |
        v
Dry-run result page
        |
        v
Admin confirms
        |
        v
Database import
        |
        v
Import summary page
```

### Phase 3: Visualization and Analysis — MOSTLY DONE

Goal: build the real dashboard. Done: summary cards, budget vs actual variance (month + team),
vendor/campaign tables, monthly trend chart, per-team chart, dedicated team dashboards, overall-spend
pie chart (hidden when a single team is filtered), and budget planned charts on `/budgets/`.
Pending: category-level budget variance and richer campaign/budget analysis.

Charts and tables:

```text
1. Total marketing spend
2. Monthly spend
3. Spend by team
4. Spend by category
5. Referral spend separately
6. SMS spend separately
7. Vendor spend descending
8. Invoice count by vendor
9. Payment stage summary
10. Aging in finance review
11. Campaign spend by month/year
12. Budget planned vs actual
```

Recommended backend pattern:

```text
Queryset permission filter
        |
        v
Aggregation service
        |
        v
Template table + Chart.js JSON
```

### Phase 4: Data Entry and Workflow — DONE

Goal: allow teams/editors to enter and update invoices.

```text
1. Invoice create form
2. Invoice edit form
3. Payment stage update
4. Status history display
5. Invoice file upload
6. Payment proof upload
7. Team-scoped form choices
8. Permission tests for every action
```

### Phase 5: Exports — DONE FOR CURRENT SCOPE

Goal: let permitted users export reports. Done: invoice-table Excel export, vendor/campaign/contract
Excel exports, workbook-style Excel, printable invoice report, and server-rendered PDF reports
(dashboard, vendors, campaigns, contracts) via ReportLab with Persian/RTL when the UI is FA.
Future work: further PDF layout polish, S3 media storage, and scheduled exports if needed.

```text
1. Filtered invoice Excel export
2. Vendor report Excel export
3. Campaign report Excel export
4. Dashboard PDF summary
5. Permission-scoped exports
```

### Phase 6: AWS Deployment — SETTINGS READY, INFRA PENDING

Goal: deploy for non-technical users. The app is production-ready in code (DATABASE_URL/Postgres
switch, WhiteNoise, HTTPS/security headers, logging, `prod` extra, gunicorn). What remains is
provisioning the infrastructure. See `docs/operations/DEPLOYMENT_AWS.md` for a concrete, copy-pasteable runbook
(single EC2 + Caddy, then RDS, then S3).

Chosen path:

```text
1. EC2 + Caddy + Gunicorn
2. RDS PostgreSQL
3. S3 for uploaded invoice/payment files
4. CloudWatch + CI/CD
5. ALB/Terraform only if the app needs more reliability or repeatability
```

Recommended production shape:

```text
User browser
    |
    v
AWS Load Balancer or Nginx
    |
    v
Gunicorn + Django app
    |
    +---- PostgreSQL / Amazon RDS
    |
    +---- S3 for media uploads
    |
    +---- Static files via S3/CloudFront or Nginx
```

For version 1, prefer this small always-on Django deployment over serverless. It is easier to operate
with login sessions, admin workflows, uploads, imports, PDF/Excel exports, and later scheduled jobs.

Deployment checklist:

```text
1. Move from SQLite to PostgreSQL.
2. Set DEBUG=False.
3. Use real SECRET_KEY from environment.
4. Configure ALLOWED_HOSTS.
5. Configure static files.
6. Configure media storage, preferably S3.
7. Add production logging.
8. Add database backups.
9. Add HTTPS.
10. Add deployment scripts or CI/CD.
```

Likely AWS services:

```text
EC2 or ECS/Fargate     Run Django app
RDS PostgreSQL         Production database
S3                     Uploaded invoices/payment proofs
CloudFront             Optional static/media CDN
Route 53               Domain/DNS
ACM                    HTTPS certificate
CloudWatch             Logs/metrics
```

## Important Notes

### Project File Reference

For a file-by-file explanation of the project, see:

```text
docs/architecture/PROJECT_FILE_REFERENCE.md
```

### Current Panel

The working panel starts at `/login/`. Django Admin remains available at `/admin/` for fallback maintenance.

### Local Admin Password

The local dev admin is:

```text
admin / admin12345
```

Do not use this password in production.

### Import Is Explicit

The app does not yet auto-watch folders or auto-import dropped files.

Current workflow:

```text
Upload workbook at /imports/
Review dry-run preview
Confirm import
```

Terminal workflow remains available:

```text
Drop workbook in project root/data/imports
Run make load-data-dry-run
Run make load-data
```

### Discovery Mapping Matters

The importer depends on:

```text
docs/discovery/column_mapping.yml
```

If the Excel workbook structure changes, update discovery/mapping before importing.

## Recommended Next Step

Deepen the analysis layer where the current charts stop:

```text
1. Budget variance by category (Budget sheet line titles)
2. Richer campaign-over-year visualization
3. Wire SpendCategory / SubTeam / Requester into invoice form dropdowns
4. Campaign CRUD in the custom panel
5. Optional JSON endpoints for a later React front-end
```

After that, harden and ship it:

```text
1. Upload size/type validation and S3 media storage
2. CI/CD running make check
3. AWS deployment per docs/operations/DEPLOYMENT_AWS.md (or a PaaS)
```

The React front-end stays a separate, later project that consumes the same server-aggregated data.

For a fuller, prioritized plan of improvements and next steps, see `docs/project/PHASE_2.md`.
