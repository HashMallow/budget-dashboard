# AGENTS.md — Marketing Spend Monitoring Dashboard

## Purpose
Build a web-based admin panel for monitoring, entering, analyzing, and exporting marketing spend data. The app must start from an Excel workbook that will be placed in the Codex/project directory. The workbook includes at least two sheets: an input/data-entry sheet and a budget sheet.

The instructions in this repository are in English. The end-user interface may later support Persian labels, but the implementation, code comments, model names, migrations, and developer docs should stay in English.


## Mandatory Pre-Implementation Discovery

Before building the Django app, importer, database models, or dashboards, run a discovery phase using the real files in the project directory:

1. Transcribe the provided audio file (`.ogg` or similar) into Persian.
2. Summarize the transcript and extract English requirements.
3. Inspect the provided `.xlsx` workbook structure without modifying it.
4. Identify the input/data-entry sheet and budget sheet.
5. Map real workbook columns to the app concepts and models.
6. Save the discovery outputs under `docs/discovery/`.

Use `docs/specs/AUDIO_TRANSCRIPTION_AND_XLSX_DISCOVERY.md` as the detailed specification. If using Codex skills, use `.agents/skills/audio-xlsx-discovery/SKILL.md`.

Do not guess sheet names or column names. Do not implement the final importer until `docs/discovery/column_mapping.yml` exists or the missing mappings are clearly documented.

## Recommended Stack
Use a pragmatic, batteries-included stack:

- Backend/web app: **Django 5+**
- UI: Django templates + Bootstrap or Tailwind + Chart.js
- Database for local development: SQLite
- Database for production-ready deployment later: PostgreSQL-compatible schema
- Excel import/export: `pandas` + `openpyxl`
- PDF export: `WeasyPrint` if available; otherwise `ReportLab`
- Auth/RBAC: Django auth + groups/permissions + custom team-level access model
- File uploads: Django `FileField`/`ImageField`, local media storage first
- Tests: pytest + pytest-django
- Formatting/linting: ruff

Avoid building a separate React frontend unless explicitly requested later. This product is an internal dashboard; speed, correctness, access control, and maintainability matter more than frontend complexity.

## Non-Negotiable Product Requirements

1. The app must have user authentication with username/password.
2. The admin user must have full access to all data, users, teams, invoices, budgets, campaigns, exports, and uploads.
3. The admin must be able to create at least 10+ users and assign each user a role and team-level access.
4. Users must only see data they are authorized to see.
5. Roles must include at minimum:
   - `Admin`: full access.
   - `Manager`: can view dashboards/reports for assigned teams or all teams if granted.
   - `Editor`: can enter and update invoice/spend data for assigned teams.
   - `Observer`: read-only access for assigned teams.
6. Admin can decide whether a user may upload invoice images and payment proof images.
7. Editors can enter invoice/spend information only for their assigned teams.
8. Managers and observers can see invoice progress/status for their permitted scope.
9. The app must import initial data from an Excel workbook in the project directory.
10. The database must become the source of truth after import; Excel is an import/export format, not the runtime database.
11. Admin can export filtered/current data to Excel and PDF.
12. Referral and SMS costs must be shown separately, outside regular team breakdowns, while still included in overall marketing spend.
13. The app must support invoice payment tracking, including payment stage, days in current stage, invoice image upload, and payment receipt/proof image upload.
14. The dashboard must show marketing spend pie charts overall, monthly, and per team.
15. The dashboard must show vendor-level information: vendor name, invoice count, payment stage, invoice numbers, and total spend from highest to lowest.
16. The dashboard must show campaign spend throughout the year using both a table and a chart.

## Important Excel Handling Rules

The workbook will be available in the project/Codex directory. Do not assume exact file name. Search for `*.xlsx` in the repository root and common data directories.

Expected sheets:

- Input/data-entry sheet: likely contains invoice/spend rows.
- Budget sheet: likely contains budget rows by month/team/campaign/category.

Because the exact column names may be Persian, inconsistent, or changed over time, implement an importer that:

1. Lists detected sheet names.
2. Lists detected columns for each relevant sheet.
3. Normalizes column names using aliases.
4. Produces a clear error report when required fields cannot be mapped.
5. Supports a mapping dictionary that can be extended without rewriting the importer.
6. Stores original raw row data in a JSON field for traceability.

Never silently drop rows during import. Every skipped row must be reported with a reason.


The Excel importer must consume or mirror the mapping from `docs/discovery/column_mapping.yml` after the discovery phase. If the workbook contains Persian headers, merged headers, hidden sheets, or multiple tables per sheet, document those issues in `docs/discovery/import_risks.md` and handle them explicitly.

## Suggested Domain Model

Implement these models or close equivalents. Keep names in English.

### Team
Represents a marketing team or department.

Fields:
- `name`
- `slug`
- `is_active`

### Vendor
Represents suppliers/vendors.

Fields:
- `name`
- `normalized_name`
- `tax_id` optional
- `notes`

### Campaign
Represents annual or monthly marketing campaigns.

Fields:
- `name`
- `year`
- `team` optional
- `planned_start_date` optional
- `planned_end_date` optional
- `status`
- `notes`

### BudgetLine
Represents budget by month/year/team/category/campaign.

Fields:
- `year`
- `month`
- `team` optional
- `campaign` optional
- `category`
- `planned_amount`
- `currency`
- `source_sheet`
- `source_row_number`
- `raw_data_json`

### Invoice
Represents actual marketing spend/invoice records.

Fields:
- `invoice_number`
- `vendor`
- `team` optional
- `campaign` optional
- `category`
- `cost_bucket`: one of `TEAM`, `REFERRAL`, `SMS`, `GENERAL`
- `description`
- `invoice_date`
- `due_date` optional
- `amount`
- `currency`
- `payment_stage`: one of `DRAFT`, `SUBMITTED`, `FINANCE_REVIEW`, `APPROVED`, `PAID`, `REJECTED`, `CANCELLED`
- `stage_changed_at`
- `paid_at` optional
- `created_by`
- `updated_by`
- `source_sheet`
- `source_row_number`
- `raw_data_json`

Computed/display fields:
- days in current payment stage
- month/year extracted from invoice date

### InvoiceAttachment
Supports invoice images/documents and payment receipts.

Fields:
- `invoice`
- `attachment_type`: `INVOICE_IMAGE`, `PAYMENT_PROOF`, `OTHER`
- `file`
- `uploaded_by`
- `uploaded_at`
- `notes`

### UserTeamAccess
Controls team-level permissions.

Fields:
- `user`
- `team`
- `role`: `MANAGER`, `EDITOR`, `OBSERVER`
- `can_upload_invoice_files`
- `can_upload_payment_proofs`
- `can_export`
- `is_active`

Admin/superuser bypasses this table and sees everything.

### InvoiceStatusHistory
Tracks invoice workflow changes.

Fields:
- `invoice`
- `old_stage`
- `new_stage`
- `changed_by`
- `changed_at`
- `note`

## Access Control Rules

Implement access checks centrally. Do not rely only on hiding UI buttons.

- Admin/superuser: full access.
- Manager: can view dashboards, reports, vendors, invoices, campaigns, and budgets for assigned teams. If explicitly granted all-team access, can view all teams.
- Editor: can create/edit invoice records for assigned teams. Editor cannot manage users. Editor can upload files only if the `UserTeamAccess` flags allow it.
- Observer: can view permitted team data only. No edits, no uploads, no user management.
- Referral and SMS data should be visible to Admin and any Manager with all-marketing/global access. Team-limited users see referral/SMS only if explicitly granted.

All querysets must be filtered server-side by the current user's permitted scope.

## Dashboard Requirements

### Admin/Manager Dashboard
Show:
- Total marketing spend.
- Overall spend pie chart by team/category/cost bucket.
- Monthly spend chart for all marketing spend.
- Monthly pie or stacked chart by team.
- Separate Referral spend card/chart.
- Separate SMS spend card/chart.
- Vendor spend table sorted descending by total amount.
- Campaign spend chart and table for the year.
- Invoice status summary by payment stage.
- Aging summary: invoices in finance review and number of days in that stage.

### Team Dashboard
When a team is selected, show:
- Team total spend.
- Team monthly spend.
- Team vendor list.
- For each vendor:
  - vendor name
  - invoice count
  - invoice numbers
  - current payment stages
  - total amount
- Team campaign spend.
- Invoices requiring attention.

### Invoice Detail Page
Show:
- Invoice metadata.
- Vendor.
- Team/campaign/category.
- Payment stage.
- Days in current stage.
- Status history.
- Invoice image/document attachments.
- Payment proof images.
- Actions allowed by current role.

## Data Entry Requirements

Admin can enter all invoice/spend data.
Editors can enter invoice/spend data only for their own teams.

Required invoice form fields:
- invoice number
- vendor
- team or cost bucket
- campaign optional
- category
- invoice date
- amount
- payment stage
- description optional
- invoice image/document upload optional depending on permission
- payment proof upload optional depending on permission

The form must validate that team-limited editors cannot assign invoices to unauthorized teams.

## Export Requirements

Admin can export:
- all invoice data to Excel
- filtered invoice data to Excel
- dashboard/report summary to PDF
- vendor spend report to Excel/PDF
- campaign spend report to Excel/PDF

Managers or other users can export only if `can_export` is true and only for their permitted data scope.

## Implementation Order

Follow this order. Do not jump to deployment.

0. Run audio transcription and XLSX structure discovery; create `docs/discovery/*`.
1. Create Django project and app structure.
2. Add settings for local SQLite, media uploads, static files, and environment variables.
3. Create models and migrations.
4. Create seed/import command to inspect Excel workbook and import data.
5. Create auth groups and baseline permissions.
6. Build central permission/queryset filtering helpers.
7. Build admin-only user/team access management screens.
8. Build invoice CRUD with permission checks.
9. Build upload handling for invoice images and payment proofs.
10. Build dashboards and chart JSON endpoints.
11. Build vendor report.
12. Build campaign report.
13. Build Excel/PDF exports.
14. Add tests for permissions, imports, dashboards, exports, and invoice stage history.
15. Add README run instructions.

## Quality Bar

- No hard-coded absolute paths.
- No hard-coded user passwords except documented local dev bootstrap command.
- No secret keys committed.
- All money values should use `Decimal`, not float.
- All dates should be timezone-aware where applicable.
- Use server-side permission checks for every view and export.
- Add tests for the highest-risk permission cases.
- Importer must be repeatable/idempotent where possible.
- Importer should update existing invoices by invoice number + vendor when re-run, not blindly duplicate rows.
- All charts must be backed by server-side aggregated data, not fragile client-side spreadsheet parsing.

## Definition of Done

The first complete local version is done when:

1. A superuser can log in.
2. The Excel file can be imported into the database.
3. Admin can create users, teams, and access rules.
4. Admin can see global dashboards and all reports.
5. A team-limited editor can only see and edit their team's invoices.
6. A read-only observer cannot modify anything.
7. Referral and SMS costs are visible separately from team spend.
8. Vendor spend is shown from highest to lowest.
9. Campaign spend is shown in table and chart form.
10. Invoice status changes create history records and show days in current stage.
11. Invoice and payment proof uploads work according to permissions.
12. Excel and PDF exports work for permitted scopes.
13. Tests pass.
