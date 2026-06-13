# Project Blueprint

This blueprint captures the intended product direction, current implementation decisions, voice-note feedback, and the near-term roadmap.

## Product Goal

Build an internal Django dashboard for marketing spend monitoring, invoice/payment workflow tracking, Excel import/export, vendor/campaign reporting, and budget-vs-actual analysis.

The final users should not need terminal commands. They should log in through a browser and use a normal admin/dashboard UI.

## Current Architecture Decision

```text
Local development
  uv + Makefile
  SQLite
  Custom Django panel
  Browser XLSX import
  Django Admin fallback

Near-term app
  Django templates
  Server-rendered browser UI
  SQLite locally
  Chart.js visualizations

Production target
  Docker
  Gunicorn
  PostgreSQL
  S3 media storage
  AWS EC2 first
```

Serverless is not the recommended first production target. This app has normal admin sessions, file uploads, reports, and background-style import work, so an always-on small Django service is simpler and easier to operate for version 1.

## Current Data Flow

```text
Excel workbook
      |
      v
docs/discovery/column_mapping.yml
      |
      v
marketing/importers/excel.py
      |
      v
Database
      |
      +--> Custom panel now
      |
      `--> Django Admin fallback
```

## Feedback Incorporated

### Voice Feedback: Excel Data Sheet

The Excel `Data` sheet is a lookup/reference sheet, not an invoice or budget fact table.

Use it later to seed or validate:

```text
vendors
categories/titles
sub-teams
requesters
month names
```

It should not become a runtime table that users edit directly. In the final app, add/remove vendor and reference data through database-backed UI screens.

### Voice Feedback: Duplicate Team Names

The workbook contains names that appear to refer to the same business team:

```text
Ops & Analytics
Operation & Analysis

Brand
Brand (PR & Social & CSR)
```

Database-backed alias rules are now implemented:

```text
TeamAlias
  raw_name
  team
  is_active
  notes
```

Current seeded aliases:

```text
Operation & Analysis -> Ops & Analytics
Brand (PR & Social & CSR) -> Brand
```

The importer resolves aliases before creating new teams. Existing imported rows were moved to the canonical teams and the old duplicate teams were marked inactive.

### Voice Feedback: BudgetLine Shape

Keep the normalized database structure:

```text
BudgetLine
  year
  month
  team
  category
  planned_amount
```

Then build a human-friendly budget view that pivots months horizontally:

```text
Team | Category | Farvardin | Ordibehesht | Khordad | ... | Esfand
```

The browser view should support horizontal scrolling for the Excel-like budget table.

### User Feedback: Keep The Final Project Clean

Keep source code, config, tests, selected product docs, and the import mapping. Ignore generated/local artifacts such as the SQLite database, caches, source audio files, source workbook files, WAV conversions, and generated discovery transcripts.

Discovery can be recreated later through the local Codex skills and helper scripts.

### User Feedback: Move To uv

Use `pyproject.toml` and `uv.lock` as the standard dependency workflow.

The Makefile now runs Django and test commands through:

```text
uv run
```

`pyproject.toml` and `uv.lock` are the only dependency sources. The Makefile does not expose a pip/venv setup path.

uv may still create an internal project environment while syncing dependencies, but developers and deployment commands should call `uv run ...` or `make ...`, not `.venv/bin/python`.

### User Feedback: Deployment Later On AWS

Recommended first production shape:

```text
Docker + EC2 + RDS PostgreSQL + S3
```

Avoid serverless for version 1 unless requirements change substantially.

## Current Capabilities

```text
[x] Discovery completed from real audio and workbook
[x] Follow-up voice feedback captured
[x] Django project scaffolded
[x] Core models created
[x] Django Admin registered
[x] Custom panel dashboard/list/detail/form pages
[x] Persian/English shell toggle and Persian digit toggle
[x] Browser Excel dry-run/confirm import
[x] Admin user/access creation screen
[x] TeamAlias model and obvious duplicate-team merge
[x] Excel importer implemented
[x] Dry-run import implemented
[x] Idempotent re-import implemented
[x] Baseline roles and permission helpers implemented
[x] Local admin bootstrap implemented
[x] uv-based command pipeline implemented
[x] Frontend smoke/permission tests passing
[x] Tests and lint checks passing
```

## Current Panel

```text
/login/           Login
/                 Dashboard
/invoices/        Invoice list/create/detail/edit
/vendors/         Vendor spend report
/campaigns/       Campaign spend report
/budgets/         Budget table and pivot
/imports/         Admin-only Excel upload/import
/users/           Admin-only user/access management
/admin/           Django Admin fallback
```

Users are database records. Do not manage ordinary users in `.env`; use the `/users/` panel as admin. `.env` is for secrets and deployment configuration.

## Next Build Phase: Analysis UI

Build the analysis layer on top of the current server-rendered pages:

```text
1. Chart.js dashboard visualizations
2. JSON endpoints for chart data
3. Budget planned-vs-actual analysis
4. Dedicated team dashboards
5. Full page-by-page English copy for every form/table label
6. Reference-data management seeded from the Data sheet
```

## Analysis And Visualization Phase

Add dashboards backed by server-side aggregation:

```text
total spend
monthly spend
spend by team
spend by category
referral spend
SMS spend
vendor spend descending
invoice count by vendor
payment stage summary
finance-review aging
campaign spend
budget planned vs actual
```

## Deployment Phase

Target shape:

```text
Users
  |
  v
HTTPS
  |
  v
Nginx/Caddy or AWS load balancer
  |
  v
Docker: Django + Gunicorn
  |
  +--> RDS PostgreSQL
  |
  `--> S3 media uploads
```

Minimum deployment work:

```text
1. Dockerfile and docker-compose for local production-like runs
2. PostgreSQL settings
3. S3 media storage
4. Gunicorn entrypoint
5. DEBUG=False production config
6. Real secrets through environment variables
7. collectstatic/static serving
8. Database backup plan
```

## Current Run Commands

```bash
make setup
make dev-admin
make import-dry-run
make import
make run
```

Local panel:

```text
http://127.0.0.1:8000/login/
http://127.0.0.1:8000/admin/
admin / admin12345
```

Verification:

```bash
make check
```
