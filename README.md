# Marketing Spend Monitoring Dashboard

Local Django app for importing, monitoring, entering, reporting, and exporting marketing spend data.

For a more visual explanation of the current structure, capabilities, run workflow, and roadmap, see:

```text
docs/PROJECT_BLUEPRINT.md
docs/CURRENT_STATE_AND_RUN_GUIDE.md
docs/PROJECT_FILE_REFERENCE.md
```

## Current Status

- Discovery is complete under `docs/discovery/`.
- Django project and `marketing` app are scaffolded.
- Core models, admin registration, baseline auth groups, permission helpers, and initial tests are in place.
- The Excel importer works from `docs/discovery/column_mapping.yml`.
- The project now uses `uv` as the standard dependency and command runner.
- A minimal custom UI is available for dashboard, invoices, vendors, campaigns, budgets, imports, and users.
- Chart.js-style visualization endpoints and deeper analysis are the next implementation phases.

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
/invoices/        Invoice list/create/detail/edit
/vendors/         Vendor spend report
/campaigns/       Campaign spend report
/budgets/         Budget table and pivot
/imports/         Admin-only Excel upload/import
/users/           Admin-only user/access management
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

## Verification

```bash
make check
```

This currently runs Django checks, 12 pytest tests, and ruff through uv.
