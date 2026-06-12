# Current State and Run Guide

This document explains what exists right now, how the pieces fit together, and how to test the app locally before moving on to a basic UI, visual dashboards, analysis features, and AWS deployment.

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
Django Admin panel
/admin/
```

The app currently uses Django Admin as the first working panel. This is useful for validating the database, imported workbook data, users, roles, and core models before building a custom dashboard UI.

## Current Project Structure

```text
Alireza/
├── AGENTS.md
├── README.md
├── Makefile
├── manage.py
├── requirements.txt
├── pyproject.toml
├── db.sqlite3
├── your_workbook.xlsx
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── marketing/
│   ├── models.py
│   ├── admin.py
│   ├── permissions.py
│   ├── importers/
│   │   └── excel.py
│   ├── management/commands/
│   │   ├── bootstrap_dev_admin.py
│   │   ├── import_marketing_excel.py
│   │   └── seed_auth_groups.py
│   ├── migrations/
│   └── tests/
│
├── docs/
│   ├── discovery/
│   │   ├── audio_transcript.fa.md
│   │   ├── audio_summary.en.md
│   │   ├── audio_requirements.en.md
│   │   ├── workbook_structure.md
│   │   ├── workbook_sample_rows.md
│   │   ├── column_mapping.yml
│   │   └── import_risks.md
│   └── CURRENT_STATE_AND_RUN_GUIDE.md
│
├── data/
├── imports/
└── templates/
```

## Current Capabilities

### Working Now

```text
[x] Audio transcription/discovery documentation
[x] Workbook structure discovery
[x] Column mapping based on the real workbook
[x] Django project setup
[x] Local SQLite database
[x] Core data models
[x] Django Admin panel
[x] Auth groups: Admin, Manager, Editor, Observer
[x] Local admin bootstrap command
[x] Excel import command
[x] Dry-run import mode
[x] Idempotent re-import behavior
[x] Server-side permission helper functions
[x] Tests for permissions, status history, and importer behavior
[x] Makefile command pipeline
```

### Partially Working

```text
[~] Basic dashboard route exists, but it is only a placeholder page.
[~] Roles and permissions exist in code, but custom user-facing screens do not use them yet.
[~] Data is imported and viewable in Django Admin, not yet in a polished dashboard UI.
```

### Not Built Yet

```text
[ ] Friendly custom dashboard UI
[ ] Excel upload/import page in the browser
[ ] Invoice create/edit screens outside Django Admin
[ ] Team-scoped user dashboards
[ ] Charts and visual analysis
[ ] Vendor report page
[ ] Campaign report page
[ ] Excel/PDF export pages
[ ] Production deployment configuration
[ ] AWS deployment
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
```

### Main Models

```text
Team
  Marketing team or department.

Vendor
  Supplier/vendor used by invoices.

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

The importer reads this mapping file:

```text
docs/discovery/column_mapping.yml
```

The importer currently imports:

```text
Invoices from: Marketing Spend Input
Budget lines from: Budget
Reference behavior from: Data
Summary sheet ignored for import: Market Live Spending
```

The real workbook import produced:

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

## How To Run Locally

Run these commands from the project root:

```bash
cd /home/workplace/Documents/Projects/Alireza
```

### First-Time Setup

```bash
make setup
```

This does:

```text
1. Creates .venv if needed
2. Installs Python dependencies
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

### Start The Local Panel

```bash
make run
```

Open:

```text
http://127.0.0.1:8000/admin/
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
http://127.0.0.1:8001/admin/
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
setup -> dev-admin -> import -> run
```

## How To Test The App Manually

### 1. Check Admin Login

Open:

```text
http://127.0.0.1:8000/admin/
```

Login with:

```text
admin / admin12345
```

Expected result:

```text
Django Admin opens successfully.
Marketing app sections are visible.
```

### 2. Check Imported Data

In Django Admin, open:

```text
Marketing
├── Teams
├── Vendors
├── Campaigns
├── Budget lines
├── Invoices
├── Invoice attachments
├── Invoice status history
└── User team access
```

Expected counts:

```text
Teams: 8
Vendors: 25
Campaigns: 5
Invoices: 51
Budget lines: 1639
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
team = Growth
team = Brand
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
8 tests passed
```

## Current Make Commands

```text
make help
  Show available commands.

make setup
  Create virtualenv, install dependencies, migrate database, seed auth groups.

make dev-admin
  Create/update local admin user: admin / admin12345.

make import-dry-run
  Preview Excel import without database writes.

make import
  Import/update Excel data into the database.

make run
  Start local Django server.

make panel
  Create/update local admin and start server.

make first-run
  Setup, create local admin, import workbook, start server.

make check
  Run Django checks, tests, and lint.

make shell
  Open Django shell.
```

## Development Roadmap

### Phase 1: Basic Custom UI

Goal: move beyond Django Admin for everyday usage.

```text
1. Add login/logout pages.
2. Add base layout and navigation.
3. Add invoice list page.
4. Add invoice detail page.
5. Add team/vendor/campaign list pages.
6. Apply server-side permission filters to every page.
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
  |-- Import status page
```

### Phase 2: Browser-Based Excel Upload

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

### Phase 3: Visualization and Analysis

Goal: build the real dashboard.

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

### Phase 4: Data Entry and Workflow

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

### Phase 5: Exports

Goal: let permitted users export reports.

```text
1. Filtered invoice Excel export
2. Vendor report Excel export
3. Campaign report Excel export
4. Dashboard PDF summary
5. Permission-scoped exports
```

### Phase 6: AWS Deployment

Goal: deploy for non-technical users.

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
docs/PROJECT_FILE_REFERENCE.md
```

### Current Panel Is Django Admin

Right now, `/admin/` is the working panel. It is functional but not the final user experience.

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
Drop workbook in project root/data/imports
Run make import-dry-run
Run make import
```

Future workflow:

```text
Upload workbook in browser
Review dry-run preview
Confirm import
```

### Discovery Mapping Matters

The importer depends on:

```text
docs/discovery/column_mapping.yml
```

If the Excel workbook structure changes, update discovery/mapping before importing.

## Recommended Next Step

Build the basic custom UI next:

```text
1. App login/logout
2. Base dashboard layout
3. Invoice list and detail pages
4. Vendor list page
5. Campaign list page
6. Budget list page
7. Server-side permission filtering on all pages
```

After that, add:

```text
1. Chart.js dashboard visualizations
2. Browser-based Excel upload/import
3. Analysis/report pages
4. Export capabilities
5. AWS deployment
```
