# Discovery mapping

`column_mapping.yml` in this directory is an **example template** with generic sheet names,
team labels, and sample values. It documents the importer shape without customer-specific
names or PII.

For a real deployment:

1. Copy your workbook locally (gitignored `*.xlsx`).
2. Copy `column_mapping.local.yml.example` → `column_mapping.local.yml` (also gitignored).
3. Set `sheets.invoices.actual_sheet_name` to the invoice tab name in **your** workbook.
4. Run import / dry-run — the importer also tries **header auto-detection** when the tab
   name differs but required columns (e.g. `Invoice Number`) are present.

Alternatively run discovery / `tools/inspect_xlsx_structure.py` and maintain a fully private
mapping via `--mapping /path/to/private/column_mapping.yml`.

Never commit production workbook files, database dumps, or mappings that contain real vendor
names, employee names, or client branding.
