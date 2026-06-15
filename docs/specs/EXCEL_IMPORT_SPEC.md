# Excel Import Specification

## Goal
Import the initial marketing spend data and budget data from an Excel workbook into the database.

## Dependency on Discovery Phase

Before implementing the importer, run the workflow in `docs/specs/AUDIO_TRANSCRIPTION_AND_XLSX_DISCOVERY.md`.

The importer uses `docs/discovery/column_mapping.yml` as its source of truth for column headers,
row ranges, and import rules. That file in the public repo is an **anonymized template** (generic
tab names such as `Marketing Spend Input`).

Sheet resolution order at import time:

1. `actual_sheet_name` from the mapping (after merging optional gitignored
   `docs/discovery/column_mapping.local.yml`)
2. Optional `sheet_aliases` listed in the mapping
3. **Header auto-detection** — if exactly one workbook tab contains the required column headers
   (e.g. `Invoice Number`, `Vendor Name`, `Invoice Amount (IRR)`), use that tab

Live team names, vendors, and business lines always come from **imported workbook data**, not from
example labels in the YAML template.

If `column_mapping.yml` is missing, the import command should stop with a clear error.

The workbook will be placed in the project/Codex directory. The exact filename is not guaranteed.

## Workbook Discovery

Search for Excel files in this order:

1. `./*.xlsx`
2. `./data/*.xlsx`
3. `./imports/*.xlsx`

If multiple files exist, print the list and require a CLI argument such as:

```bash
python manage.py import_marketing_excel --file path/to/file.xlsx
```

## Expected Sheets

At minimum, expect:

- one input/data-entry sheet
- one budget sheet

The sheet names may be Persian or English. Use fuzzy matching and configurable aliases.

Suggested aliases:

### Input Sheet Aliases

- `input`
- `inputs`
- `data`
- `invoice`
- `invoices`
- `spend`
- `expenses`
- `ورودی`
- `هزینه`
- `هزینه کرد`
- `فاکتور`

### Budget Sheet Aliases

- `budget`
- `budgets`
- `plan`
- `planning`
- `بودجه`

## Column Mapping Strategy

Do not hard-code only one column name. Implement alias-based mapping.

Required invoice concepts:

- invoice number
- vendor name
- amount
- invoice date or month/year
- team or cost bucket/category
- payment stage if available

Optional invoice concepts:

- business line (Excel **Business Section** — segments such as Consumer, Youth, Enterprise, …)
- campaign name
- category
- description
- due date
- paid date
- currency
- referral/SMS marker

Required budget concepts:

- planned amount
- year or date/month
- team/category/campaign if available

## Suggested Column Aliases

### Invoice Number

- `invoice number`
- `invoice no`
- `invoice`
- `factor number`
- `شماره فاکتور`
- `فاکتور`

### Vendor

- `vendor`
- `vendor name`
- `supplier`
- `نام وندور`
- `وندور`
- `تامین کننده`

### Team

- `team`
- `department`
- `unit`
- `تیم`
- `واحد`

### Amount

- `amount`
- `cost`
- `spend`
- `expense`
- `total`
- `مبلغ`
- `هزینه`
- `هزینه کرد`
- `جمع`

### Date

- `date`
- `invoice date`
- `month`
- `year`
- `تاریخ`
- `ماه`
- `سال`

### Payment Stage

- `payment stage`
- `status`
- `payment status`
- `مرحله پرداخت`
- `وضعیت`
- `وضعیت پرداخت`

### Campaign

- `campaign`
- `campaign name`
- `کمپین`
- `نام کمپین`

### Category

- `category`
- `type`
- `channel`
- `دسته`
- `دسته بندی`
- `کانال`

### Budget

- `budget`
- `planned amount`
- `allocated`
- `بودجه`
- `مبلغ بودجه`

## Normalization Rules

1. Trim whitespace from strings.
2. Normalize Persian/Arabic variants where practical, for example `ي` to `ی` and `ك` to `ک`.
3. Normalize vendor names using lowercase, stripped punctuation, and collapsed spaces.
4. Parse amounts safely. Remove commas and currency symbols before Decimal conversion.
5. Do not use float for money.
6. Parse dates from both Excel serial dates and text dates when possible.
7. If date parsing fails but month/year exists, create a date using the first day of that month.
8. Map payment stage text into the internal enum.
9. Detect Referral/SMS rows using category, team, or description keywords.

## Referral and SMS Detection

If a row contains Referral-related keywords in category/team/description, set:

```text
cost_bucket = REFERRAL
```

If a row contains SMS-related keywords in category/team/description, set:

```text
cost_bucket = SMS
```

Otherwise, if a valid team exists:

```text
cost_bucket = TEAM
```

If no team exists and it is not Referral/SMS:

```text
cost_bucket = GENERAL
```

## Import Command Requirements

Create a command:

```bash
python manage.py import_marketing_excel --file path/to/workbook.xlsx --dry-run
python manage.py import_marketing_excel --file path/to/workbook.xlsx
```

The command must:

- print detected sheets
- print detected columns
- print selected mappings
- import/update teams
- import/update vendors
- import/update campaigns if campaign data exists
- import/update invoices
- import/update budget lines
- report created/updated/skipped rows
- write skipped-row reasons
- support `--dry-run`

## Idempotency

Re-running the importer should not create duplicate invoices.

Preferred matching:

1. invoice number + normalized vendor
2. if invoice number missing: deterministic fingerprint from vendor + date + amount + team + description

## Raw Data Preservation

Store the original row as JSON in `raw_data_json` for invoices and budget lines. This helps debug imports later.

## Error Handling

If required columns cannot be mapped, stop with a clear message explaining:

- which sheet was detected
- which columns were found
- which required fields were missing
- how to add aliases to the mapping dictionary


## Discovery-Aware Import Behavior

The import command should support the real workbook mapping produced during discovery:

```bash
python manage.py import_marketing_excel --file path/to/workbook.xlsx --mapping docs/discovery/column_mapping.yml --dry-run
python manage.py import_marketing_excel --file path/to/workbook.xlsx --mapping docs/discovery/column_mapping.yml
```

Behavior:

1. Load `docs/discovery/column_mapping.yml`.
2. Merge `docs/discovery/column_mapping.local.yml` when present (gitignored; see
   `column_mapping.local.yml.example`).
3. Resolve each sheet: mapped `actual_sheet_name` → `sheet_aliases` → header auto-detection.
4. Use mapped `header_row` and `columns` for row parsing.
5. If a required concept is not mapped, attempt column alias detection where implemented.
6. If still missing, stop with a clear error instead of importing partial data silently.
7. Print created/updated/skipped counts and skipped-row reasons.

The importer must be able to work with Persian headers, but internal model fields must remain English.
