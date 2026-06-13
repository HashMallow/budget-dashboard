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
[x] Main dashboard Chart.js pie chart, monthly trend line, and per-team bar chart
[x] Dedicated team list and team dashboard pages
[x] Data-sheet reference seeding for vendors, categories, sub-teams, and requesters
[x] Vendor report Excel export
[x] Campaign report Excel export
[x] Invoice table Excel export
[x] Workbook-style Excel export (/exports/workbook.xlsx) — familiar sheet layout from DB data
[x] Server-rendered dashboard summary PDF using ReportLab
[x] Browser-printable invoice report
[x] Permission-scoped export gates through can_export()
[x] Consolidated Settings menu (language, amount format, currency unit, theme)
[x] Compact/full amount display toggle with hover for exact values
[x] Rial/Toman display toggle (display-only; stored values stay in Rial)
[x] Light/dark theme toggle (session-persisted)
[x] Jalali month/year filters and Shamsi date parsing in import + forms
[x] Tests for reference seeding, team dashboard scope, Excel exports, PDF, money display, and workbook export
```

The important architectural choice is still intact: dashboards and exports are built from
permission-filtered querysets on the server. Chart.js only draws prepared aggregate JSON; it does
not receive raw spreadsheet data.

---

## Still thin or missing

```text
[ ] Budget planned-vs-actual analysis (variance table/chart — highest-value gap)
[ ] Richer campaign-over-year visualization (monthly bars + budget overlay)
[ ] Reference-data management screens beyond Django Admin fallback
[ ] Lookup validation/dropdowns wired into every data-entry form
[ ] SMS / Referral as first-class dashboard sections (separate from team spend, per product rules)
[ ] Persian/RTL PDF rendering with an embedded Persian-capable font
[ ] Upload hardening: file size, content type, extension, and S3 production storage
[ ] CI/CD pipeline
[ ] Live AWS or PaaS deployment
[ ] JSON API endpoints for a future React front-end
[ ] Caching for dashboard aggregates if data volume grows
[ ] High-accuracy GPU transcription workflow (blocked on slow Hugging Face model downloads in some environments)
```

ReportLab currently proves the server-PDF pattern with English text and simple tables. If PDFs need
Persian text, the next step is to register a Persian font and handle RTL/shaping deliberately.

Money and date display got a solid pass (compact/full, Toman toggle, Jalali grouping, Persian
digits in FA mode). Keep regression tests when touching exports or table layouts.

## Current caveats

These are intentional boundaries of the current implementation:

```text
Reference data is seeded, but not yet used throughout the UI.
  SpendCategory, SubTeam, and Requester exist in the database and Django Admin.
  Invoice forms still use a free-text category field.
  Next step: dropdown/autocomplete choices and validation backed by seeded lookups.

Charts are richer, but still rendered inside Django templates.
  This is fine for the current server-rendered panel.
  When React is introduced, expose marketing/analytics.py through JSON endpoints.
  Do not rebuild dashboard math on the client.

PDF export is a summary, not a polished full report suite.
  /reports/dashboard.pdf covers totals, top vendors, and payment stages.
  /reports/invoices/print/ still exists for browser print-to-PDF.
  Next step: report-specific PDFs for vendors/campaigns with better layout and Persian/RTL support.

Workbook export is a clean DB round-trip, not a byte-for-byte clone.
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
| **P0** | Budget planned-vs-actual | Core BI question for every budget manager: “Are we over or under, and where?” |
| **P0** | Deploy a small production instance | The app is useful only when non-technical users can reach it in a browser |
| **P1** | SMS / Referral reporting polish | Product rule: show separately from team breakdowns while still in total spend |
| **P1** | Reference management UI + form dropdowns | Reduces bad categories/vendors and matches how the Excel Data sheet was meant to work |
| **P1** | Upload hardening and S3 | Invoice/payment images are user-supplied and should survive server replacement |
| **P1** | CI/CD running `make check` | Locks tests, lint, and Django checks before deployment |
| **P2** | Budget alerts and aging dashboards | High value once variance exists; surfaces invoices stuck in finance review |
| **P2** | JSON API + optional React front-end | Useful later, but Django templates are enough for the internal admin panel now |

---

## Recommended next build order

```text
1. Add budget planned-vs-actual dashboard cards, variance table, and monthly chart (team + campaign drill-down).
2. Polish SMS / Referral cards and filters so they never mix into team pie slices unless explicitly requested.
3. Add reference-data management screens for vendors, categories, sub-teams, and requesters.
4. Wire seeded lookup rows into invoice forms where it improves data quality.
5. Extend workbook export with variance columns (planned, actual, delta, % used) for budget managers.
6. Harden uploads, then move production media to S3.
7. Add CI/CD that runs `make check` and deploys after successful checks.
8. Deploy on a small always-on service: PaaS first for speed, or EC2/RDS/S3 for AWS learning.
9. Add Persian/RTL PDF support if PDFs need Persian-facing output.
10. Add JSON endpoints only when the React front-end becomes the next real milestone.
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

