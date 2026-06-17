# Phase 2 — Current Status and Next Steps

Phase 2 has moved from “planned” to “mostly implemented for day-to-day use.” This document
separates what exists in the code from what still needs product work before a polished
production rollout.

For the authoritative run guide, see
[`CURRENT_STATE_AND_RUN_GUIDE.md`](CURRENT_STATE_AND_RUN_GUIDE.md). For deployment, see
[`DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md). For the codebase tour, see
[`PROJECT_EXPLAINED.md`](PROJECT_EXPLAINED.md).

---

## What landed

The current app now includes:

```text
[x] Server-side analytics helpers in marketing/analytics.py
[x] Main dashboard Chart.js: spend pie (all teams), monthly trend, per-team bar, budget vs actual
[x] Dedicated team list and team dashboard pages with budget variance
[x] Data-sheet reference seeding (`make seed-reference`) + panel CRUD at `/reference/`
[x] Vendor / campaign / contract Excel + PDF exports (permission-scoped)
[x] Invoice table Excel export and workbook-style Excel export
[x] Server-rendered PDF reports (dashboard, vendors, campaigns, contracts) with Persian/RTL support
[x] Browser-printable invoice report
[x] Contract tracking UI (list, create, edit, stages, attachments)
[x] Permission-scoped export gates through can_export()
[x] Consolidated Settings menu (language, amount format, currency unit, theme)
[x] Sectioned sidebar + in-app Help (`/help/`)
[x] Invoice business line (`business_section`) from Excel Business Section
[x] Finance overview dashboard layout (team-filter UX, paired charts)
[x] Campaign CRUD at `/reference/campaigns/`
[x] Persian PDF glyph shaping fix (arabic-reshaper without python-bidi reversal)
[x] Compact/full amount display; Rial/Toman; همت for trillion-tier Toman amounts
[x] Light/dark theme toggle (session-persisted)
[x] Jalali month/year filters and Shamsi date parsing in import + forms
[x] Tests for permissions, imports, analytics, exports, PDF, reference CRUD, money display
[x] Invoice amount breakdown: action cost, 10% VAT, insurance withholding, paid amount (voice _2, _12)
[x] Manual budget CRUD, budget variance on invoice form, PDF export wizard, vendor/campaign merge
[x] Editor Excel import permission (can_import_excel), inline payment-stage edit in lists
[x] Dashboard UI polish: planned budget vs actual spend terminology, full-width charts, Finance nav
```

**Test suite (2026-06-16):** 123 passed, 1 skipped (`uv run pytest -q`).

The important architectural choice is still intact: dashboards and exports are built from
permission-filtered querysets on the server. Chart.js only draws prepared aggregate JSON; it does
not receive raw spreadsheet data.

---

## Still thin or missing

```text
[ ] Exact Excel round-trip export — 4-sheet mirror identical to source workbook (Google Sheets sync)
[ ] Year-end financial breakdown export — marketing spend vs VAT vs insurance deposits (fields exist per invoice)
[ ] Budget variance by category (Budget sheet line titles)
[ ] Richer campaign-over-year visualization (monthly bars + budget overlay)
[ ] Lookup validation/dropdowns wired into every invoice data-entry form
[ ] Campaign CRUD in the custom panel — **done** at `/reference/campaigns/`; keep improving campaign report UX
[ ] Invoice action-month vs invoice-date reporting toggle
[ ] Upload hardening: file size limits, content-type checks, S3 production storage
[ ] CI/CD pipeline running make check
[ ] Live AWS or PaaS deployment (runbook exists in docs/operations/DEPLOYMENT_AWS.md)
[ ] JSON API endpoints for a future React front-end
[ ] Caching for dashboard aggregates if data volume grows
```

Money and date display got a solid pass (compact/full, Toman toggle, Jalali grouping, Persian
digits in FA mode). Keep regression tests when touching exports or table layouts.

## Current caveats

These are intentional boundaries of the current implementation:

```text
Reference data can be seeded (`make seed-reference`) and managed in the panel (`/reference/`).
  SpendCategory, SubTeam, Requester, BusinessLine, InsuranceRateOption exist in the database.
  Invoice form uses dropdowns for category, business line, and insurance rate.
  `business_section` is still a CharField (not FK) — form-enforced only.

Invoice amount breakdown (action cost, VAT, insurance, paid) is implemented in
  marketing/invoice_amounts.py and on invoice/vendor detail pages.
  No dedicated year-end export separating marketing vs tax vs insurance totals yet.

Charts are richer, but still rendered inside Django templates.
  This is fine for the current server-rendered panel.
  When React is introduced, expose marketing/analytics.py through JSON endpoints.
  Do not rebuild dashboard math on the client.

PDF export includes a filter wizard at `/exports/pdf/` plus direct report endpoints.
  Summary PDFs are not a full year-end tax/insurance breakdown suite.
  /reports/invoices/print/ still exists for browser print-to-PDF.
  /exports/workbook.xlsx recreates familiar sheet names and monthly budget/actual views.
  It is scoped to the user's permitted data and sanitized for Excel and Google Sheets compatibility.
  Next step: optional “include empty budget rows” and variance columns for budget managers.

Reference seeding is manual.
  make import imports invoice and budget facts.
  make seed-reference seeds lookup rows from the Data sheet.
  make load-data runs both, which is safer after a fresh database/import.

Team dashboard budget is a headline number.
  The current budget card sums planned budget for the selected team across all years/months.
  It is not planned-vs-actual variance analysis yet.

Dates are now Shamsi-aware, but date-heavy imports need regression checks.
  The importer and forms parse Shamsi/Jalali text before Gregorian fallback.
  Keep tests around Persian/Arabic digits and `1405/01/10`-style dates.

Display preferences are session-scoped, not per-user profile fields.
  Language, amount format, currency unit, and theme persist in the session.
  Next step (optional): store preferences on the User model for cross-device consistency.
```

---

## Priorities

| Priority | Theme | Why |
|---|---|---|
| **P0** | Exact Excel round-trip (4-sheet mirror) | Product owner needs Google Sheets sync with the source workbook layout |
| **P0** | Deploy a small production instance | The app is useful only when non-technical users can reach it in a browser |
| **P1** | Year-end tax/insurance breakdown report | Aggregate marketing spend vs VAT vs insurance deposits for finance close |
| ~~P1~~ ✅ | SMS / Referral reporting polish | **Done (2026-06-17):** Referral rolls into Growth and SMS into Retention in charts; never a standalone team/pie slice; dedicated cards remain |
| **P1** | Upload hardening and S3 | Invoice/payment images are user-supplied and should survive server replacement |
| **P1** | CI/CD running `make check` | Locks tests, lint, and Django checks before deployment |
| **P2** | Budget alerts and aging dashboards | High value; surfaces invoices stuck in finance review |
| **P2** | JSON API + optional React front-end | Useful later, but Django templates are enough for the internal admin panel now |

---

## Recommended next build order

```text
1. Build exact 4-sheet Excel round-trip export mirroring the source workbook (Google Sheets sync).
2. Add year-end financial breakdown export: marketing spend vs VAT vs insurance deposits.
3. ✅ Done — SMS/Referral never mix into team pie slices (roll into Growth/Retention; dedicated cards kept).
4. Extend workbook export with variance columns and optional empty budget rows for budget managers.
5. Harden uploads, then move production media to S3.
6. Add CI/CD that runs `make check` and deploys after successful checks.
7. Deploy on a small always-on service: PaaS first for speed, or EC2/RDS/S3 for AWS learning.
8. Add JSON endpoints only when the React front-end becomes the next real milestone.
```

---

## Feature ideas for budget managers

These are practical additions beyond the original spec. They are ordered by typical ROI for
someone who owns marketing spend and monthly budget reviews.

### Variance and forecast (highest ROI)

| Idea | What it gives the budget manager |
|---|---|
| **Planned vs actual by month/team/campaign** | The main “budget review” screen: green/yellow/red variance per row |
| **% budget consumed (YTD and MTD)** | “Team A has used 78% of Q1 budget with 40% of the quarter left” |
| **Burn-rate forecast** | Simple run-rate projection to year-end based on trailing 3 months |
| **Budget line drill-down** | Click a category (e.g. media, events) and see invoices that drove overage |
| **Reforecast / notes** | Let managers attach a short note when actuals diverge (“campaign shifted to April”) |

### Workflow and cash control

| Idea | What it gives the budget manager |
|---|---|
| **Aging by payment stage** | Sort invoices by days in FINANCE_REVIEW or SUBMITTED; already partially on dashboard — extend to team views |
| **Overdue / attention queue** | Single list: “needs approval,” “missing receipt,” “amount over budget line” |
| **Vendor payment calendar** | Expected cash out by week/month from due dates and unpaid stages |
| **Duplicate invoice warnings** | Flag same invoice number + vendor or suspicious near-duplicates on save/import |
| **Bulk stage updates** | Finance approves a filtered batch after month-end close |

### Reporting and exports

| Idea | What it gives the budget manager |
|---|---|
| **Variance workbook export** | Current workbook export + Planned / Actual / Variance / % columns per month |
| **Scheduled email digest** | Weekly PDF or Excel to managers: top variances + stuck invoices |
| **Executive one-pager** | One-page PDF: total spend, top 5 vendors, top 3 over-budget teams |
| **Year-over-year compare** | When multi-year data exists: same month last year vs this year |
| **Campaign ROI placeholder** | Optional planned budget vs actual per campaign for annual planning |

### Data quality and governance

| Idea | What it gives the budget manager |
|---|---|
| **Lookup dropdowns from Data sheet** | Category, sub-team, requester as validated choices — fewer typos than free text |
| **Reference-data admin UI** | Add/deactivate vendors and categories without Django Admin |
| **Import diff report** | After re-import: “12 updated, 3 new, 1 skipped — here’s why” |
| **Audit trail on amount/stage changes** | Who changed invoice amount or payment stage and when (history exists for stage; extend if needed) |
| **Soft budget locks** | Warn (or block) editors when posting spend over remaining monthly budget |

### Access and collaboration

| Idea | What it gives the budget manager |
|---|---|
| **Per-user display preferences** | Save language/Toman/theme on the user profile, not only session |
| **Team-scoped “budget owner” role** | Manager sees variance only for owned teams; admin sees all |
| **Read-only share links or exports** | Observer gets a fixed monthly pack without edit access |
| **Comments on invoices** | Finance ↔ marketing thread on a specific invoice |

### Nice-to-have later

```text
- Mobile-friendly invoice photo capture from phone camera
- Slack/Teams webhook when invoice enters FINANCE_REVIEW
- Multi-currency support if vendors invoice in USD/EUR (store IRR + FX rate)
- Integration hook: export to accounting ERP format
- Dashboard caching when invoice count exceeds ~10k rows
```

Start with **planned-vs-actual** and **variance export** — they directly replace the manual
Budget / Market Live Spending sheet review that budget managers already do in Excel.

---

## Notes on implemented patterns

### Data-sheet reference seeding

`make seed-reference` calls `marketing.reference_data.seed_reference_data_from_workbook()`.
It reads the real workbook `Data` sheet through `docs/discovery/column_mapping.yml` and upserts:

```text
Vendor
SpendCategory
SubTeam
Requester
```

This keeps the `Data` sheet as reference data, not as a runtime fact table.

### Dashboard charts

`marketing/analytics.py` centralizes the aggregation logic:

```text
visible invoice queryset
        |
        v
monthly_spend_rows / team_spend_rows / overall_spend_pie
        |
        v
json_script in Django template
        |
        v
Chart.js draws the chart
```

This pattern is the right base for future JSON endpoints because the permission-filtered math is
already reusable.

### Exports

The Excel exports are built with `openpyxl`:

```text
/exports/invoices.xlsx      Flat invoice table
/exports/vendors.xlsx       Vendor spend summary
/exports/campaigns.xlsx     Campaign spend summary
/exports/workbook.xlsx      Multi-sheet layout (invoices, budget, Market Live Spending, Data)
```

Workbook export lives in `marketing/exports/workbook.py`. Every cell is normalized to
Excel-safe scalars, illegal control characters are stripped, auto-filter ranges are explicit
(`A1:…` not open-ended `dimensions`), and regression tests validate structure and round-trip loading.

The server-rendered PDF is built in `marketing/reports/pdf.py` and served from:

```text
/reports/dashboard.pdf
```

All export routes check `can_export(request.user)` and use permission-scoped querysets so a
limited user cannot export data outside their permitted scope.

### Display preferences

Session-backed preferences (language, compact/full amounts, Rial/Toman, light/dark theme) flow
through:

```text
MoneyDisplayMiddleware → activate_money_display()
display_preferences context processor → templates + Chart.js globals
{% money %} template filter → marketing/money_format.py
```

Stored invoice amounts always remain in Rial; toggles affect UI and chart labels only.

