# Data Model Specification

Use Django models. Keep model, field, and migration names in English.

## Enumerations

### Role Values
Use these in `UserTeamAccess.role`:

- `MANAGER`
- `EDITOR`
- `OBSERVER`

Admin is represented by Django `is_superuser` or membership in an Admin group.

### Cost Bucket Values
Use these in `Invoice.cost_bucket`:

- `TEAM`: normal team spend
- `REFERRAL`: referral costs — shown on a dedicated card and rolled up into the **Growth** team for charts/totals (never a standalone team slice)
- `SMS`: SMS costs — shown on a dedicated card and rolled up into the **Retention** team for charts/totals (never a standalone team slice)
- `GENERAL`: general marketing costs not assigned to a team

### Payment Stage Values
Use these in `Invoice.payment_stage`:

- `DRAFT`
- `SUBMITTED`
- `FINANCE_REVIEW`
- `APPROVED`
- `PAID`
- `REJECTED`
- `CANCELLED`

### Attachment Type Values
Use these in `InvoiceAttachment.attachment_type`:

- `INVOICE_IMAGE`
- `PAYMENT_PROOF`
- `OTHER`

## Models

### Team
Fields:

- `name`: CharField, unique
- `slug`: SlugField, unique
- `is_active`: BooleanField, default true
- `created_at`: DateTimeField
- `updated_at`: DateTimeField

### Vendor
Fields:

- `name`: CharField
- `normalized_name`: CharField, indexed
- `tax_id`: CharField, blank allowed
- `notes`: TextField, blank allowed
- `created_at`: DateTimeField
- `updated_at`: DateTimeField

Indexes/constraints:

- index on `normalized_name`
- avoid duplicate vendors by normalized name when possible

### Campaign
Fields:

- `name`: CharField
- `year`: PositiveIntegerField
- `team`: ForeignKey Team, nullable/blank
- `planned_start_date`: DateField, nullable/blank
- `planned_end_date`: DateField, nullable/blank
- `status`: CharField, default `PLANNED`
- `notes`: TextField, blank allowed
- `created_at`: DateTimeField
- `updated_at`: DateTimeField

### BudgetLine
Fields:

- `year`: PositiveIntegerField
- `month`: PositiveSmallIntegerField, nullable/blank if annual-only
- `team`: ForeignKey Team, nullable/blank
- `campaign`: ForeignKey Campaign, nullable/blank
- `category`: CharField
- `planned_amount`: DecimalField
- `currency`: CharField, default from settings
- `source_sheet`: CharField, blank allowed
- `source_row_number`: PositiveIntegerField, nullable/blank
- `raw_data_json`: JSONField, default dict
- `created_at`: DateTimeField
- `updated_at`: DateTimeField

### Invoice
Fields:

- `invoice_number`: CharField, indexed
- `vendor`: ForeignKey Vendor
- `team`: ForeignKey Team, nullable/blank
- `campaign`: ForeignKey Campaign, nullable/blank
- `category`: CharField
- `cost_bucket`: CharField choices `TEAM`, `REFERRAL`, `SMS`, `GENERAL`
- `description`: TextField, blank allowed
- `invoice_date`: DateField
- `due_date`: DateField, nullable/blank
- `amount`: DecimalField — invoice total (action cost + VAT)
- `action_cost_amount`: DecimalField, nullable — base marketing spend before VAT
- `tax_amount`: DecimalField, nullable — VAT (default 10% of action cost; overridable)
- `insurance_rate_percent`: DecimalField, nullable — withholding rate (e.g. 16.67%, 7.78%)
- `insurance_amount`: DecimalField, nullable — withheld from vendor share of action cost
- `paid_amount`: DecimalField, nullable — net paid by finance: `(action − insurance) + tax`
- `currency`: CharField, default from settings
- `payment_stage`: CharField choices from Payment Stage Values
- `stage_changed_at`: DateTimeField
- `paid_at`: DateTimeField, nullable/blank
- `created_by`: ForeignKey User, nullable/blank, related name `created_invoices`
- `updated_by`: ForeignKey User, nullable/blank, related name `updated_invoices`
- `source_sheet`: CharField, blank allowed
- `source_row_number`: PositiveIntegerField, nullable/blank
- `business_section`: CharField, indexed, blank allowed — business segment from Excel **Business Section** (Consumer, Youth, Enterprise, …). Imported via `column_mapping.yml`; filterable on invoices.
- `raw_data_json`: JSONField, default dict
- `created_at`: DateTimeField
- `updated_at`: DateTimeField

Rules:

- Use Decimal for amount fields.
- Amount breakdown logic lives in `marketing/invoice_amounts.py` (10% VAT default, insurance withholding, paid amount).
- `amount` is the invoice face total; use `action_cost_amount`, `tax_amount`, `insurance_amount`, and `paid_amount` for finance breakdowns.
- `REFERRAL`/`SMS` are cost buckets, not teams: they appear on their own dashboard cards but never as a standalone team/pie slice. In team and overall charts they roll up into their parent team (Referral→Growth, SMS→Retention) per `marketing/cost_buckets.py`, so totals remain correct.
- When `payment_stage` changes, update `stage_changed_at` and create `InvoiceStatusHistory`.
- If stage becomes `PAID`, set `paid_at` if empty.
- Provide a method/property for `days_in_current_stage`.

Suggested uniqueness:

- `invoice_number` + `vendor` should be unique when invoice number exists.
- If the Excel data has missing invoice numbers, create a deterministic import fingerprint to avoid duplicates.

### InvoiceAttachment
Fields:

- `invoice`: ForeignKey Invoice
- `attachment_type`: CharField choices `INVOICE_IMAGE`, `PAYMENT_PROOF`, `OTHER`
- `file`: FileField/ImageField
- `uploaded_by`: ForeignKey User
- `uploaded_at`: DateTimeField
- `notes`: TextField, blank allowed

Rules:

- Do not allow upload unless the current user has permission for that invoice's team/cost bucket.
- Restrict file types to images and PDFs in the first version.

### UserTeamAccess
Fields:

- `user`: ForeignKey User
- `team`: ForeignKey Team, nullable/blank if global marketing access is supported
- `role`: CharField choices `MANAGER`, `EDITOR`, `OBSERVER`
- `can_upload_invoice_files`: BooleanField, default false
- `can_upload_payment_proofs`: BooleanField, default false
- `can_export`: BooleanField, default false
- `can_import_excel`: BooleanField, default false — allows non-admin editors to use `/imports/`
- `can_view_referral_sms`: BooleanField, default false
- `is_global`: BooleanField, default false
- `is_active`: BooleanField, default true
- `created_at`: DateTimeField
- `updated_at`: DateTimeField

Rules:

- If `is_global` is true, the user can access all teams according to their role.
- If `is_global` is false, access is limited to `team`.

### InvoiceStatusHistory
Fields:

- `invoice`: ForeignKey Invoice
- `old_stage`: CharField
- `new_stage`: CharField
- `changed_by`: ForeignKey User, nullable/blank
- `changed_at`: DateTimeField
- `note`: TextField, blank allowed

Rules:

- Create a history row every time payment stage changes.

## Aggregation Requirements

Implement service functions/query helpers for:

- total spend by month
- total spend by team
- total spend by category
- total spend by cost bucket
- referral spend by month
- SMS spend by month
- vendor spend descending
- invoice count by vendor
- invoice numbers by vendor
- campaign spend by year/month/team
- invoice status counts
- invoice aging by current stage

All aggregation functions must accept a user or explicit permission scope and only return authorized data.
