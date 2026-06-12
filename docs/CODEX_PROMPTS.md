# Codex Prompts

Use these prompts sequentially. Do not ask Codex to build everything in one huge step unless you want a messy result.

## Prompt 0 — Audio and XLSX Discovery

Read `AGENTS.md`, `docs/AUDIO_TRANSCRIPTION_AND_XLSX_DISCOVERY.md`, and the `audio-xlsx-discovery` skill if available. Before writing the Django app, find the audio file and Excel workbook in the repository root, `data/`, or `imports/`. Transcribe the audio into Persian, summarize it in English, extract structured English requirements, inspect the `.xlsx` workbook structure, identify input and budget sheets, detect header rows and columns, sample a few rows, and create all required files under `docs/discovery/`, especially `column_mapping.yml` and `import_risks.md`. Do not modify the workbook. Stop after discovery and report the proposed column-to-model mapping and open questions.

## Prompt 1 — Project Setup

Read `AGENTS.md` and all files in `docs/`. Create the initial Django project for the marketing spend monitoring dashboard. Use Django templates, SQLite for local development, media uploads, pytest, and ruff. Do not implement deployment. Add a README with local run commands. Stop after the app boots and tests run.

## Prompt 2 — Models

Implement the data models described in `docs/DATA_MODEL.md`. Create migrations, register models in Django admin, add useful list displays/filters, and add model tests for invoice status history and days in current payment stage. Keep all model names and field names in English.

## Prompt 3 — Excel Importer

Implement the Excel importer described in `docs/EXCEL_IMPORT_SPEC.md`. The importer must discover `.xlsx` files, support `--file`, support `--dry-run`, detect sheets, map columns through aliases, import invoices and budget lines, preserve raw row JSON, and avoid duplicate invoices on repeated import. Add tests using a small generated workbook fixture.

## Prompt 4 — Authentication and RBAC

Implement authentication and access control based on `docs/RBAC_SPEC.md`. Add central permission/queryset helpers and tests proving that team-limited users cannot see or modify other teams' data. Do not rely only on hiding buttons in templates.

## Prompt 5 — Invoice CRUD and Uploads

Build invoice list/detail/create/edit pages. Enforce team-level permissions server-side. Add invoice attachment and payment proof upload handling. Add tests for editor and observer behavior.

## Prompt 6 — Dashboards

Build the overview and team dashboards from `docs/DASHBOARD_SPEC.md`. Use Chart.js. All chart data must come from server-side permission-filtered aggregation functions. Show Referral and SMS spend separately from team spend.

## Prompt 7 — Vendor and Campaign Reports

Build vendor and campaign report pages. Vendor report must default to total spend descending. Campaign report must include both table and chart views for yearly campaign costs. Add filters and tests.

## Prompt 8 — Exports

Add Excel and PDF exports for invoices, vendor report, campaign report, and dashboard/report summaries. Exports must respect user permissions and current filters. Add tests for export permissions.

## Prompt 9 — Polish and Final QA

Review the app against `docs/ACCEPTANCE_TESTS.md`. Fix gaps. Improve empty states, error messages, import reporting, form validation, and README instructions. Do not add production deployment unless explicitly requested.
