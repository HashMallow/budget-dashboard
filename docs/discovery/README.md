# Discovery mapping

`column_mapping.yml` in this directory is an **example template** with generic sheet names,
team labels, and sample values. It documents the importer shape without customer-specific
names or PII.

For a real deployment:

1. Copy your workbook locally (gitignored `*.xlsx`).
2. Run discovery / `tools/inspect_xlsx_structure.py` against that file.
3. Maintain a **private** `column_mapping.yml` (or set `--mapping` on import commands) with
   your actual sheet names, team labels, and column headers.

Never commit production workbook files, database dumps, or mappings that contain real vendor
names, employee names, or client branding.
