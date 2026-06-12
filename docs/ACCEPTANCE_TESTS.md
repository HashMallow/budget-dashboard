# Acceptance Tests

Use these as the practical definition of done for the first local version.

## Discovery Phase

- [ ] Audio file is found or missing audio is explicitly documented.
- [ ] Persian transcript is saved to `docs/discovery/audio_transcript.fa.md`, or transcription limitation is documented.
- [ ] English summary is saved to `docs/discovery/audio_summary.en.md`.
- [ ] Structured English requirements are saved to `docs/discovery/audio_requirements.en.md`.
- [ ] Excel workbook is found or missing workbook is explicitly documented.
- [ ] Workbook sheets, dimensions, header rows, and columns are saved to `docs/discovery/workbook_structure.md`.
- [ ] Sample rows are saved to `docs/discovery/workbook_sample_rows.md`.
- [ ] `docs/discovery/column_mapping.yml` maps workbook columns to invoice and budget concepts.
- [ ] `docs/discovery/import_risks.md` lists missing/ambiguous mappings and import risks.


## Authentication

- [ ] Admin can log in.
- [ ] Non-admin user can log in.
- [ ] Logged-out users cannot access dashboard pages.

## User and Role Management

- [ ] Admin can create users.
- [ ] Admin can assign a user to one or more teams.
- [ ] Admin can assign Manager, Editor, or Observer role.
- [ ] Admin can grant/revoke upload permissions.
- [ ] Admin can grant/revoke export permissions.

## Excel Import

- [ ] Import command finds an Excel workbook or accepts a `--file` argument.
- [ ] Dry-run mode prints sheets, columns, and mapping results.
- [ ] Input sheet imports invoice/spend rows.
- [ ] Budget sheet imports budget lines.
- [ ] Vendors are created/updated.
- [ ] Teams are created/updated.
- [ ] Campaigns are created/updated when campaign data exists.
- [ ] Re-running import does not duplicate invoices.
- [ ] Skipped rows are reported with reasons.

## Dashboards

- [ ] Admin sees total marketing spend.
- [ ] Admin sees pie chart for overall spend.
- [ ] Admin sees monthly spend chart.
- [ ] Admin sees team spend breakdown.
- [ ] Referral spend is shown separately.
- [ ] SMS spend is shown separately.
- [ ] Team dashboard shows vendor names.
- [ ] Team dashboard shows invoice counts per vendor.
- [ ] Team dashboard shows invoice numbers per vendor.
- [ ] Team dashboard shows payment stages.

## Vendor Reporting

- [ ] Vendor table defaults to spend descending.
- [ ] Vendor table shows invoice count.
- [ ] Vendor table shows invoice numbers.
- [ ] Vendor table respects user permissions.

## Campaign Reporting

- [ ] Campaign report shows annual campaign costs.
- [ ] Campaign report has a chart.
- [ ] Campaign report has a table.
- [ ] Campaign report respects user permissions.

## Invoice Entry and Tracking

- [ ] Admin can create invoice for any team.
- [ ] Editor can create invoice only for assigned team.
- [ ] Observer cannot create invoice.
- [ ] Payment stage can be updated by authorized users.
- [ ] Stage changes create history records.
- [ ] Days in current payment stage is displayed.

## Uploads

- [ ] Authorized user can upload invoice image/document.
- [ ] Unauthorized user cannot upload invoice image/document.
- [ ] Authorized user can upload payment proof.
- [ ] Unauthorized user cannot upload payment proof.
- [ ] Users only see attachments for invoices they can access.

## Exports

- [ ] Admin can export invoices to Excel.
- [ ] Admin can export vendor report to Excel/PDF.
- [ ] Admin can export campaign report to Excel/PDF.
- [ ] Non-admin export respects `can_export`.
- [ ] Exported data respects team scope.

## Security

- [ ] Team A user cannot access Team B invoice detail by guessing URL.
- [ ] Team A user cannot export Team B data by changing query parameters.
- [ ] Observer cannot submit POST requests to edit data.
- [ ] Upload endpoint validates permission server-side.
