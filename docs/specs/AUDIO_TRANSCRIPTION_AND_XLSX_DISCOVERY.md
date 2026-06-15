# Audio Transcription and XLSX Structure Discovery

## Purpose
Before implementing the dashboard or finalizing database/import mappings, Codex must inspect the real project inputs:

1. The `.ogg` audio file containing extra business requirements.
2. The `.xlsx` workbook that will act as the initial data source.

The goal is to produce a small set of discovery documents that explain what the audio says, what the workbook contains, and how workbook columns map to the database models.

Do **not** skip this step. Do **not** guess the workbook structure.

## Expected Input Files

Search the repository root and common data directories:

```text
./*.ogg
./*.oga
./*.mp3
./*.m4a
./*.wav
./data/*
./imports/*
./*.xlsx
./data/*.xlsx
./imports/*.xlsx
```

If multiple audio or workbook files exist, list them and continue with the most likely one only when the name is clear. Otherwise ask the developer to pass explicit paths to the discovery command.

## Required Discovery Outputs

Create these files under `docs/discovery/`:

```text
docs/discovery/audio_transcript.fa.md
docs/discovery/audio_summary.en.md
docs/discovery/audio_requirements.en.md
docs/discovery/workbook_structure.md
docs/discovery/workbook_sample_rows.md
docs/discovery/column_mapping.yml
docs/discovery/import_risks.md
```

### `audio_transcript.fa.md`

A Persian/Farsi transcript of the audio.

Rules:
- Preserve the original Persian as much as possible.
- Mark unclear audio as `[unclear]`.
- Do not invent missing words.
- Include timestamps if the transcription tool provides them.

### `audio_summary.en.md`

A concise English summary of the audio.

### `audio_requirements.en.md`

A structured English requirements list extracted from the audio. Group requirements into:

- Users and access control
- Dashboards and charts
- Vendor/invoice reporting
- Campaign reporting
- Invoice data entry
- Payment workflow tracking
- File/image upload requirements
- Excel import/export requirements
- PDF export requirements
- Open questions or unclear items

### `workbook_structure.md`

A workbook inventory:

- file path
- workbook sheet names
- visible/hidden status if available
- approximate row/column counts per sheet
- likely sheet purpose: input data, budget data, lookup/reference, dashboard/pivot, unknown
- detected header row per sheet
- detected columns per sheet
- merged cell ranges, if any

### `workbook_sample_rows.md`

For each relevant sheet, include:

- normalized column names
- first 5 non-empty data rows as Markdown tables
- any columns that look like dates, money, status, team, vendor, campaign, invoice number, referral, SMS

Do not include private/sensitive data beyond the minimum sample rows needed for mapping.

### `column_mapping.yml`

Create a machine-readable mapping from workbook sheets and columns to app/domain concepts.

Example:

```yaml
workbook: data/marketing.xlsx
sheets:
  input:
    actual_sheet_name: "ورودی"
    header_row: 1
    model: Invoice
    columns:
      invoice_number: "شماره فاکتور"
      vendor_name: "نام وندور"
      amount: "مبلغ"
      invoice_date: "تاریخ"
      team: "تیم"
      payment_stage: "مرحله پرداخت"
      campaign_name: "کمپین"
      category: "دسته بندی"
  budget:
    actual_sheet_name: "بودجه"
    header_row: 1
    model: BudgetLine
    columns:
      planned_amount: "بودجه"
      year: "سال"
      month: "ماه"
      team: "تیم"
      campaign_name: "کمپین"
```

### `import_risks.md`

List all issues that could affect import correctness:

- missing required fields
- ambiguous column names
- duplicated invoice numbers
- Persian date format issues
- numbers stored as text
- merged headers
- multiple tables on one sheet
- formulas instead of raw values
- hidden sheets
- rows that look like totals/subtotals
- category values that need mapping to `REFERRAL`, `SMS`, `TEAM`, or `GENERAL`

## Audio Transcription Options

### Preferred: OpenAI Speech-to-Text API

Use this when `OPENAI_API_KEY` is available.

Recommended behavior:

1. Convert `.ogg` to `.wav` first if needed:

```bash
ffmpeg -y -i input.ogg docs/discovery/audio.wav
```

2. Transcribe with a strong speech-to-text model.
3. Save the original Persian transcript and an English summary.

Implementation can use the OpenAI Python SDK or a small script created by Codex. Do not commit API keys.

### Fallback: Local Whisper

Use this when API access is unavailable but `whisper` is installed.

```bash
ffmpeg -y -i input.ogg docs/discovery/audio.wav
whisper docs/discovery/audio.wav --model medium --language Persian --output_format txt --output_dir docs/discovery
```

If the machine is weak, start with `small` and clearly mark that the transcript may be lower quality.

### If No Transcription Tool Is Available

Create `docs/discovery/audio_transcript.fa.md` with:

```text
Audio transcription could not be completed locally because no speech-to-text tool was available.
```

Then continue using the Persian requirements already provided in `AGENTS.md` and `docs/specs/PRODUCT_REQUIREMENTS.md`, but mark this limitation in `docs/discovery/import_risks.md`.

## XLSX Structure Discovery Script Requirements

Codex should create or use a script similar to `tools/inspect_xlsx_structure.py` that:

1. Opens the workbook in read-only/data-only mode.
2. Lists sheets and dimensions.
3. Detects likely header rows by finding rows with many non-empty text cells.
4. Prints raw and normalized column names.
5. Prints a small number of sample rows.
6. Detects likely input and budget sheets using aliases.
7. Detects likely money/date/status/team/vendor/campaign/invoice columns.
8. Writes the discovery Markdown and YAML files.

Do not mutate or save the workbook during discovery.

## Required Order of Work

1. Run audio transcription/discovery.
2. Run workbook structure discovery.
3. Compare audio-derived requirements with workbook columns.
4. Create `column_mapping.yml`.
5. Update importer aliases/mappings based on the discovered workbook.
6. Only then implement database import and dashboard logic.

## Completion Criteria for Discovery Phase

Discovery is complete only when:

- the audio transcript or transcription limitation is documented;
- the audio requirements are summarized in English;
- all workbook sheets and columns are listed;
- the input sheet and budget sheet are identified, or ambiguity is documented;
- required invoice and budget concepts are mapped or listed as missing;
- import risks are documented;
- `column_mapping.yml` exists and is used by the importer.
