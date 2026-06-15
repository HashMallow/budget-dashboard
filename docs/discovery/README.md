# Discovery mapping

`column_mapping.yml` in this directory is an **anonymized template** shipped with the public repo.
It documents importer shape (column headers, row ranges, rules) using generic sheet names and
example labels — not customer-specific branding or PII.

## Running locally (no extra files required)

1. Place your workbook in the project root (any filename; `*.xlsx` is gitignored).
2. Run `make load-data-dry-run` then `make load-data`.

The importer merges this template with an optional local override (below), then resolves sheets:

| Step | What happens |
|------|----------------|
| 1 | Use `actual_sheet_name` from mapping |
| 2 | Try `sheet_aliases` if listed |
| 3 | **Auto-detect** by required column headers when the tab name differs |

After import, the **dashboard and lists show names from your workbook** (teams, vendors, business
lines). Help text in the repo may use generic examples (Consumer, Team Alpha); that does not
change imported data.

## Optional: `column_mapping.local.yml` (gitignored)

Use when you want explicit control — for example matching Excel **export** tab names to your
source workbook:

```bash
cp docs/discovery/column_mapping.local.yml.example docs/discovery/column_mapping.local.yml
```

Edit `sheets.invoices.actual_sheet_name` (and other overrides) as needed. This file is never
committed.

## Private deployments

- Maintain a fully private mapping: `python manage.py import_marketing_excel --mapping /path/to/private/column_mapping.yml`
- Re-run discovery with `tools/inspect_xlsx_structure.py` when the workbook layout changes.

Never commit production workbooks, database dumps, or mappings that contain real vendor names,
employee names, or client branding.
