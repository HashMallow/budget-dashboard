# Implementation Plan

## Phase -1 — Audio and Workbook Discovery

This phase must happen before Django implementation.

1. Locate the audio file and workbook.
2. Transcribe the audio into Persian.
3. Summarize and extract requirements in English.
4. Inspect the workbook sheet structure without modifying it.
5. Identify input/data-entry and budget sheets.
6. Detect header rows, columns, and sample rows.
7. Create `docs/discovery/column_mapping.yml`.
8. Create `docs/discovery/import_risks.md`.
9. Use the mapping in the importer implementation.

Suggested commands:

```bash
python tools/transcribe_audio.py --file ./audio_2026-06-12_10-33-51.ogg
python tools/inspect_xlsx_structure.py --file ./data/marketing.xlsx
```


## Phase 0 — Project Setup

1. Create Django project.
2. Create main app, for example `marketing`.
3. Add dependencies:
   - django
   - pandas
   - openpyxl
   - pillow
   - pytest
   - pytest-django
   - ruff
   - python-decouple or django-environ
   - reportlab or weasyprint
4. Configure local SQLite.
5. Configure media uploads.
6. Add `.env.example`.
7. Add basic README run commands.

## Phase 1 — Models and Admin

1. Implement models from `DATA_MODEL.md`.
2. Create migrations.
3. Register models in Django admin.
4. Add readable list displays and filters in admin.
5. Add `days_in_current_stage` property to Invoice.
6. Add status-history creation when payment stage changes.

## Phase 2 — Excel Import

1. Implement workbook discovery.
2. Implement sheet detection.
3. Implement column alias mapping.
4. Implement dry-run mode.
5. Import teams, vendors, campaigns, invoices, and budget lines.
6. Preserve raw row JSON.
7. Add idempotent upsert behavior.
8. Add import tests using a small generated workbook fixture.

## Phase 3 — Authentication and RBAC

1. Use Django login/logout.
2. Create groups or role choices.
3. Implement `UserTeamAccess` management.
4. Implement permission helper functions.
5. Add tests for server-side filtering.

## Phase 4 — Invoice CRUD and Uploads

1. Invoice list with filters.
2. Invoice create/edit forms.
3. Team-limited form choices.
4. Payment stage update with history.
5. Invoice attachment upload.
6. Payment proof upload.
7. Permission tests for create/edit/upload.

## Phase 5 — Dashboards

1. Overview dashboard.
2. Chart data aggregation services.
3. Team dashboard.
4. Referral and SMS separate cards/charts.
5. Invoice aging summary.
6. Permission tests for chart endpoints.

## Phase 6 — Reports

1. Vendor spend report sorted descending.
2. Campaign spend report.
3. Budget planned vs actual report.
4. Filters for year/month/team/campaign/category/stage.

## Phase 7 — Exports

1. Excel export for invoice table.
2. Excel export for vendor report.
3. Excel export for campaign report.
4. PDF export for dashboard/report summaries.
5. Permission tests for exports.

## Phase 8 — Polish

1. Improve layout and responsive tables.
2. Add empty-state messages.
3. Add import error download/report.
4. Add useful sample data generation command.
5. Add final README.

## Suggested Local Commands

```bash
make setup
make dev-admin
make import-dry-run
make import FILE=./data/marketing.xlsx
make run
make check
```

The Makefile is uv-only. Direct equivalents use `uv run python manage.py ...`.
