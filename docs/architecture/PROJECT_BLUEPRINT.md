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
  Data-sheet lookup seeding

Production target
  Gunicorn
  PostgreSQL
  S3 media storage
  AWS EC2 + Caddy first, then RDS, then S3
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

It is now used to seed or validate:

```text
vendors
categories/titles
sub-teams
requesters
month names
```

It should not become a runtime table that users edit directly. The implemented seed command creates
database lookup rows; the next step is a friendly browser UI to manage those rows without editing
Excel.

### Voice Feedback: Duplicate Team Names

The workbook contains names that appear to refer to the same business team:

```text
Ops & Analytics
Operations & Analysis

Team Beta
Team Beta (PR & Social)
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
Operations & Analysis -> Ops & Analytics
Team Beta (PR & Social) -> Team Beta
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

### Voice Feedback: Roles

Manager should be treated as a reporting/view role, not as a broad edit role.

```text
Admin
  Full ownership of users, imports, edits, uploads, and exports.

Manager
  View dashboards/reports for its allowed scope; export only if explicitly granted.

Observer
  Read-only access for its allowed scope.

Editor
  Data-entry/update role for assigned teams or granted global scope.
```

The app should keep enforcing this server-side. Hiding buttons in the UI is not enough.

### Voice Feedback: Dates And Amounts

Dates from the workbook and forms may be Shamsi/Jalali. They must not be misread as Gregorian
years. The importer and invoice forms now accept values such as:

```text
1405/01/10
۱۴۰۵/۰۱/۱۰
2026-03-30
```

The database stores normalized Gregorian dates; Persian mode displays Jalali dates back to users.

Recent voice feedback also called out possible number/amount display problems. Treat money display
as a QA-sensitive area: Persian digit display must not change stored numeric values, and amount
columns in team/vendor tables must stay aligned on narrow screens.

### User Feedback: Keep The Final Project Clean

Keep source code, config, tests, selected product docs, and the import mapping. Ignore generated/local artifacts such as the SQLite database, caches, source audio files, source workbook files, WAV conversions, and generated discovery transcripts.

Raw voice notes, WAV conversions, and raw transcript markdown should live in:

```text
.artifacts/voice-feedback/
```

That directory is ignored by Git. Copy only durable product decisions back into docs.

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
EC2 + Caddy + Gunicorn
then RDS PostgreSQL
then S3 media uploads
```

Docker is useful when you want reproducible deploys, but it is not required for the first working
server. Avoid serverless for version 1 unless requirements change substantially.

Decision: use the AWS learning path, not the PaaS shortcut, unless the priority changes from
learning/control to fastest possible public URL.

## Current Capabilities

```text
[x] Discovery completed from real audio and workbook
[x] Follow-up voice feedback captured
[x] Django project scaffolded
[x] Core models created
[x] Django Admin registered
[x] Custom panel dashboard/list/detail/form pages
[x] Persian/English shell toggle and Persian digit toggle
[x] Shamsi/Jalali date parsing for imports and invoice forms
[x] Browser Excel dry-run/confirm import
[x] Admin user/access creation screen
[x] TeamAlias model and obvious duplicate-team merge
[x] Excel importer implemented
[x] Dry-run import implemented
[x] Idempotent re-import implemented
[x] Baseline roles and permission helpers implemented
[x] Local admin bootstrap implemented
[x] uv-based command pipeline implemented
[x] Data-sheet reference seeding implemented
[x] Dedicated team dashboards implemented
[x] Dashboard Chart.js pie/monthly/team charts implemented (pie hidden when main dashboard is team-filtered)
[x] Sectioned sidebar navigation and in-app Help at `/help/`
[x] Invoice business line field and filters
[x] Finance overview dashboard layout
[x] Campaign reference CRUD in panel
[x] Persian PDF shaping (Vazirmatn + arabic-reshaper)
[x] Vendor and campaign Excel exports implemented
[x] Server-rendered dashboard PDF implemented with ReportLab
[x] Frontend smoke/permission tests passing
[x] Tests and lint checks passing
```

## Current Panel

```text
/login/           Login
/help/            In-app guide
/                 Finance overview dashboard
/teams/           Team list and per-team dashboards
/invoices/        Invoice list/create/detail/edit (business line)
/vendors/         Vendor spend report
/campaigns/       Campaign spend report
/budgets/         Budget table and pivot
/contracts/       Contract tracking
/reference/       Admin lookup CRUD (vendors, categories, sub-teams, campaigns, requesters)
/imports/         Admin-only Excel upload/import
/users/           Admin-only user/access management
/exports/*.xlsx   Permission-scoped Excel exports
/reports/*.pdf    Permission-scoped PDF reports
/admin/           Django Admin fallback
```

Sidebar: Overview · Spend & teams · Reports · Administration · Help (bottom).

Users are database records. Do not manage ordinary users in `.env`; use the `/users/` panel as admin. `.env` is for secrets and deployment configuration.

## Next Build Phase: BI Depth and Operational Hardening

The first analysis layer is now present. Next, deepen it and prepare the app for real users:

```text
1. Budget planned-vs-actual analysis
2. Richer campaign-over-year visuals
3. Reference-data management screens for vendors/categories/sub-teams/requesters
4. Lookup-backed invoice form dropdowns or autocomplete
5. Upload hardening and S3 media storage
6. CI/CD that runs `make check`
7. Production deployment on AWS or a PaaS
8. JSON endpoints only when a React front-end becomes necessary
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
Nginx/Caddy, PaaS router, or AWS load balancer
  |
  v
Django + Gunicorn
  |
  +--> RDS PostgreSQL
  |
  `--> S3 media uploads
```

Minimum deployment work:

```text
1. Launch EC2 + Caddy + Gunicorn
2. Add RDS PostgreSQL after the EC2 app is stable
3. Add S3 media storage after RDS is stable
4. Gunicorn entrypoint
5. DEBUG=False production config
6. Real secrets through environment variables
7. collectstatic/static serving
8. Database backup plan
9. Optional Dockerfile and docker-compose for reproducible production-like runs
```

## Current Run Commands

```bash
make setup
make dev-admin
make load-data-dry-run
make load-data
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
