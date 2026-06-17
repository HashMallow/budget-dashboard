# Requirements vs Implementation Audit

> Cross-referencing **26 voice transcripts** and [USER_REQUESTS.en.md](voice-feedback/USER_REQUESTS.en.md) against the current codebase.  
> Fix backlog via [cursor_prompts.md](cursor_prompts.md).  
> Session log: [PROCESSING_LOG.en.md](voice-feedback/PROCESSING_LOG.en.md)

**Last verified:** 2026-06-16 · Tests: **123 passed, 1 skipped** ✅

---

## Summary Scorecard

| Area | Transcript source | Status | Notes |
|------|-------------------|--------|-------|
| Invoice amounts (action cost, VAT, insurance, paid) | `_2`, `_12` | ✅ **Done** | Fields on model + form auto-calc + `invoice_amounts.py` |
| Business line dropdown (admin-managed) | `_4`, `_19`, `_21` | ✅ **Done** | `BusinessLine` model + reference CRUD + invoice form select |
| Insurance rate dropdown | `_2`, `_12` | ✅ **Done** | `InsuranceRateOption` model + reference CRUD |
| Category dropdown (not free text) | `_5` | ✅ **Done** | `SpendCategory` model, dropdown on form |
| Dashboard: year/team/business-line/month filters | `_3`, `_17`, `_20`, `_22` | ✅ **Done** | All 4 filters in dashboard toolbar |
| Marketing queue (submitted, days waiting) | `_17` | ✅ **Done** | Separate table with days in stage |
| Finance queue (in finance review, days waiting) | `_17` | ✅ **Done** | Separate table with days in stage |
| Recently paid (last 7 days) | `_20`, `_22` | ✅ **Done** | Table with links to invoice detail |
| Clickable vendor names → vendor detail | `_8` | ✅ **Done** | All vendor names are `<a>` links to `/vendors/<id>/` |
| Vendor detail: all invoices, contracts, totals | `_8` | ✅ **Done** | Shows action/tax/paid totals + invoice list + contracts |
| Color-coded invoice rows (paid vs pending) | `_8`, `_15` | ✅ **Done** | CSS classes `invoice-row--paid` / `invoice-row--pending` |
| Invoice list: sort by entry date (newest first) | `_15`, `_16` | ✅ **Done** | Default sort is `created_at desc` |
| Days "—" when paid | `_15` | ✅ **Done** | `show_days_in_current_stage` returns `False` when PAID |
| Budget vs actual chart + table | `_6` | ✅ **Done** | Monthly bar chart + table with planned/actual/deviation |
| Budget variance by team table | `_6` | ✅ **Done** | Collapsible section on dashboard |
| Referral/SMS shown separately | `22-13-57` | ✅ **Done** | Stat chips on dashboard + separate CostBucket |
| Spend pie chart (team + referral + SMS) | AGENTS.md | ✅ **Done** | Doughnut chart with referral/SMS segments |
| Team spend chart | AGENTS.md | ✅ **Done** | Bar chart by team |
| Vendor spend table (highest to lowest) | AGENTS.md | ✅ **Done** | Sorted by `total desc` |
| Campaign spend table on dashboard | AGENTS.md | ✅ **Done** | Table with campaign, year, invoices, amount |
| Invoice status summary (count per stage) | AGENTS.md | ✅ **Done** | Payment status table |
| Contracts module (CRUD, stages, attachments) | `_9` | ✅ **Done** | Full lifecycle + legal stages + attachments |
| Invoice attachments + payment proofs | AGENTS.md | ✅ **Done** | Upload with permission checks |
| Invoice status history | AGENTS.md | ✅ **Done** | Auto-created on stage change |
| Contract status history | related | ✅ **Done** | Auto-created on stage change |
| Excel import (workbook) | AGENTS.md | ✅ **Done** | Management command + web UI |
| Excel export (invoices, vendors, campaigns, workbook) | `22-09-58` | ✅ **Done** | 4 export endpoints |
| PDF export (dashboard, vendors, campaigns, contracts) | `_10` | ✅ **Done** | Direct endpoints + `/exports/pdf/` wizard |
| User/role management | AGENTS.md | ✅ **Done** | Admin user access page |
| Team-level access control | AGENTS.md | ✅ **Done** | `UserTeamAccess` + server-side filtering |
| Reference data CRUD (vendors, categories, business lines, insurance rates, sub-teams, requesters, campaigns) | `_4`, `_21` | ✅ **Done** | Full CRUD for 7 reference types |
| Jalali date support | `_7`, `_11` | ✅ **Done** | `jalali.py` + `FlexibleDateField` |
| Help/sitemap page | — | ✅ **Done** | `/help/` endpoint |
| **Manual budget CRUD** | `_18` | ✅ | `/budgets/new/`, edit, delete (admin) |
| **Budget-line variance at invoice entry** | `_6` | ✅ | Live panel + `/api/budget-variance/` |
| **Remaining budget % consumed** | `_6` | ✅ | `% Consumed` column on variance tables |
| **PDF export wizard** (pick BL, vendor, team, month) | `_10` | ✅ | `/exports/pdf/` wizard |
| **Vendor/campaign merge UI** | `21-52-39`, `_21` | ✅ | Reference merge pages |
| **Editor Excel import permission** | `21-52-39` | ✅ | `can_import_excel` on `UserTeamAccess` |
| **Inline payment-stage edit in lists** | `_14` | ✅ | Dropdown in invoice list + dashboard queues |
| **Team → budget-line filtering on invoice form** | `_5`, `_19` | ✅ | `/api/categories-for-team/` + form JS |
| Dashboard UI: terminology, wider charts, consolidated nav, dark mode | `_7`, `_11`, `22-05-26` | ✅ **Done** | Planned budget vs actual spend labels; full-width charts; Finance nav section |
| **Year-end tax/insurance breakdown report** | `_2`, `_12` | ⚠️ **Partial** | Per-invoice and per-vendor totals exist; no dedicated year-end export/report |
| **Exact Excel round-trip (4-sheet mirror)** | `22-09-58` | ❌ **Backlog** | Workbook export exists but does not identically mirror source template |

---

## Detailed Transcript Cross-Check

### Transcript `_2` (Invoice amounts & description)

**User said** (Persian, paraphrased):
> We have an action cost X. VAT is 10% of X. Invoice total = X + 10%. Then insurance is deducted (16.67% or 7.78%). Paid amount = (X − insurance) + 10% VAT. I want to see action, tax, insurance deposit, and paid amount separately — per invoice and per vendor. Also want a description field on invoices.

**Implementation check:**
- ✅ `Invoice` model has `action_cost_amount`, `tax_amount`, `insurance_rate_percent`, `insurance_amount`, `paid_amount`
- ✅ [invoice_amounts.py](../marketing/invoice_amounts.py) calculates these values
- ✅ Form auto-calculates from action cost
- ✅ `description` field exists on Invoice model
- ✅ Vendor detail page shows: invoice total, action cost, tax, paid amount (4 KPI cards)
- ✅ Test: [test_invoice_amounts.py](../marketing/tests/test_invoice_amounts.py)
- ⚠️ **Year-end report** separating marketing spend vs tax vs insurance deposits — not a dedicated export yet (aggregate via vendor detail / filtered exports only)

### Transcript `_4` (Business line dropdown)

**User said:**
> Business lines should be a dropdown, not free text. Currently options: Retail, Junior, Business. Admin should be able to add business lines in admin panel.

**Implementation check:**
- ✅ `BusinessLine` model with admin-managed CRUD at `/reference/business-lines/`
- ✅ Invoice form has dropdown select, not free text
- ⚠️ The `business_section` field on Invoice is a `CharField`, not a FK to `BusinessLine` — this means the dropdown values may not be fully enforced by DB constraint (only form-level)

### Transcript `_6` (Budget-line variance at invoice entry)

**User said:**
> When I submit an invoice with a budget line, I want to see a panel showing: for this team → this budget line → how much budget was planned, how much spent, deviation, percentage.

**Implementation check:**
- ✅ Live variance panel on invoice create/edit (`/api/budget-variance/` + form JS)
- ✅ Dashboard and team dashboard variance tables include `% Consumed`

### Transcript `_8` (Clickable vendors + vendor detail)

**User said:**
> Everywhere a vendor name appears, clicking it should open a panel showing all their invoices (with numbers), paid/unpaid colors, contracts (start/end dates, ceiling).

**Implementation check:**
- ✅ Vendor names are clickable links throughout (dashboard, invoice list, queues)
- ✅ Vendor detail shows invoice list with paid/pending color coding
- ✅ Vendor detail shows contracts with stage and end date
- ✅ Vendor detail shows contracts with title, stage, start date, end date, and amount (ceiling)

### Transcript `_14` (Inline payment-stage change)

**User said:**
> Let me change the payment stage directly in the invoice list without opening each invoice. A dropdown or checkmark to mark as paid right in the list.

**Implementation check:**
- ✅ Invoice list: inline stage dropdown (AJAX) for authorized editors
- ✅ Dashboard marketing/finance queues: inline stage dropdown

### Transcript `_17` (Marketing/Finance queues + stage change)

**User said:**
> Show invoices waiting in marketing (submitted), with days waiting. Allow stage change right there. When changed from marketing to finance, it moves to the finance table. Finance table also shows days waiting.

**Implementation check:**
- ✅ Marketing queue table with days waiting
- ✅ Finance queue table with days waiting
- ✅ Inline stage change in queue tables (same dropdown as invoice list)

### Transcript `_18` (Manual budget entry)

**User said:**
> I need a section to enter budget data manually. Even if no Excel was imported, I should be able to register budgets. Teams, sub-teams, budget lines should be addable/editable. Budget is month by month (Farvardin to Esfand).

**Implementation check:**
- ✅ `/budgets/new/`, edit, delete (admin); `BudgetLineForm`

### Transcript `_10` (PDF export wizard)

**User said:**
> When I click PDF export, open a page where I can pick what to export: maybe just Retail spend, or a specific vendor, or Growth team for a specific month. Need filters for month, year, team, vendor, and business line.

**Implementation check:**
- ✅ `/exports/pdf/` wizard with report type + filters; topbar PDF links route through wizard

---

## What Matches the Transcripts Well ✅

1. **Invoice financial breakdown** — action cost / VAT / insurance / paid amount fully modeled and calculated
2. **Reference data management** — 7 reference types with admin CRUD (business lines, categories, insurance rates, vendors, campaigns, sub-teams, requesters)
3. **Dashboard filtering** — year, team, business line, Jalali month — all 4 filters present
4. **Operational queues** — marketing queue + finance queue with days waiting
5. **Vendor clickability** — every vendor name throughout the app links to vendor detail
6. **Invoice list UX** — entry-date default sort, paid/pending row colors, days hidden when paid
7. **Budget vs actual** — monthly variance chart + table with deviation
8. **Referral/SMS separation** — separate stat chips and included in overall pie chart
9. **Contracts** — full lifecycle with legal stages, attachments, and vendor linkage

## Cursor prompts patch status

All 9 prompts in [cursor_prompts.md](cursor_prompts.md) are **implemented** ✅ (verified 2026-06-16). See [test_cursor_prompts.py](../marketing/tests/test_cursor_prompts.py).

---

## What's Missing (Backlog) ❌

| # | Feature | Transcript | Priority |
|---|---------|------------|----------|
| 1 | **Exact Excel round-trip export** — 4-sheet mirror for Google Sheets sync | `22-09-58` | 🔴 High |
| 2 | **Year-end financial breakdown report** — separate totals for marketing spend, VAT, insurance deposits | `_2`, `_12` | 🟡 Medium |
| 3 | **Campaign spend chart** on dashboard (table exists; chart optional) | AGENTS.md | 🟢 Low |

## Minor Observations

- `business_section` on `Invoice` is a `CharField` rather than a FK to `BusinessLine` — works via form choices but isn't DB-enforced
- Campaign table on dashboard is table-only (no chart) — user mentioned "table and chart" for campaign spend

---

## Test Suite Status

```
123 passed, 1 skipped
```

Test coverage includes: analytics, contracts, cost buckets, cursor prompts, Excel importer, frontend views, import view, invoice amounts, invoice constraints, money formatting, permissions, phase 2 features, reference data + PDF, table sorting, workbook export.

---

*Audit date: 2026-06-16*
