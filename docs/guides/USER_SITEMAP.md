# Site map — what each part of the panel does

A plain-language guide for marketing, finance, and operations staff who use the **Marketing Finance Hub** day to day. No technical background required.

**Inside the app:** open **Help** (راهنما) in the left menu — or go to `/help/` before sign-in. Content appears in your chosen language (English or فارسی).

---

## What this application is for

The panel replaces scattered Excel tracking with one place to:

- See how much marketing money was spent, by team, vendor, and campaign
- Track each invoice from submission through payment
- Compare **planned budget** vs **actual spend**
- Track vendor **contracts** and upcoming renewals
- Export reports to Excel or PDF for meetings and finance

The database is the source of truth after the first Excel import. Day-to-day work happens in the panel; Excel is mainly for bulk import and export.

---

## How to open the panel

1. Go to the web address your IT team gave you (for local testing, usually `http://127.0.0.1:8000/`).
2. Sign in with the **username** and **password** your admin created.
3. You land on the **Dashboard** — the home overview.

To sign out, use **Logout** at the bottom of the left menu.

---

## The left menu (main site map)

| Menu item | What it is for | Who usually sees it |
|-----------|----------------|---------------------|
| **Dashboard** | Big-picture spend, charts, budget vs actual, payment status | Everyone (within their access) |
| **Invoices** | List, search, create, and edit marketing invoices | Everyone; only Editors/Admins can change data |
| **Teams** | Pick a team and open its focused dashboard | Everyone (only teams you are allowed to see) |
| **Vendors** | Which suppliers you paid, how much, and payment stages | Everyone (within scope) |
| **Contracts** | Vendor agreements, dates, stages, attachments | Everyone (within scope) |
| **Campaigns** | Spend grouped by marketing campaign for the year | Everyone (within scope) |
| **Budget** | Planned monthly budgets from the workbook | Everyone (within scope) |
| **Excel Import** | Upload the master workbook to refresh data | **Admins only** |
| **Users** | Create logins and set who can see which teams | **Admins only** |
| **Reference data** | Maintain vendor names, categories, sub-teams, requesters | **Admins only** |
| **Help** | This guide, inside the app | Everyone |

---

## Top bar: Settings and Exports

### Settings (gear icon)

Personal display options — they do **not** change the underlying data:

- **Language** — English or فارسی for labels and menus
- **Amount format** — compact (K/M/B) or full numbers with commas
- **Currency unit** — Rial or Toman
- **Theme** — light or dark

### Exports (download icon)

On many pages you will see **Exports** or a single download button. These download Excel (`.xlsx`) or PDF files using **the same filters** you have on screen (year, team, search, etc.). You only get data you are allowed to see.

Typical exports:

- Invoices spreadsheet
- Vendor spend report
- Campaign spend report
- Dashboard summary PDF
- Contracts report

If you do not see export buttons, your admin may not have enabled **Can export** for your account.

---

## Page-by-page guide

### Dashboard

**Purpose:** The management overview.

**What you see:**

- Total marketing spend and how much is already paid
- Separate totals for **Referral** and **SMS** (these sit outside normal team breakdowns but count in overall spend)
- Filters for **year** and **team**
- Charts: monthly trend, spend breakdown (pie chart hides when you filter to one team — use the team dashboard instead)
- **Budget vs actual** table — planned amount, spent amount, and variance by month
- Invoices that need attention (stuck in review, overdue stages)
- Contract alerts (expiring soon or expired)

**Typical use:** Monday stand-up, monthly review, “how are we doing against budget?”

---

### Invoices

**Purpose:** The working list of every marketing spend line / invoice.

**What you can do:**

- **Search** by invoice number, vendor, campaign, category, or description
- **Filter** by team, payment stage, year, etc.
- Open an invoice to see full detail, payment history, and uploaded files
- **Editors** and **Admins** can add invoices and change payment stage
- Attach **invoice images** and **payment receipts** if your admin allowed uploads

**Payment stages** (workflow): Draft → Submitted → Finance review → Approved → Paid (or Rejected / Cancelled). The detail page shows how many days an invoice has been in the current stage.

---

### Teams

**Purpose:** Focus on one marketing team at a time.

**Flow:**

1. Open **Teams** — you see only teams you may access.
2. Click a team name → **team dashboard** with that team’s spend, vendors, campaigns, and attention items.

**Typical use:** Brand manager checking Brand spend only; growth lead reviewing Growth vendors.

---

### Vendors

**Purpose:** Answer “who did we pay, and how much?”

**What you see:** Vendors sorted from **highest spend to lowest**, with invoice count, invoice numbers, payment stages, and totals.

**Typical use:** Negotiations, vendor reviews, finance reconciliation.

---

### Contracts

**Purpose:** Track agreements with vendors separately from individual invoices.

**What you can do:**

- List contracts with stage, dates, and team
- Open a contract for detail, history, and file attachments
- Admins and permitted Editors can create and update contracts

**Typical use:** Renewal planning, legal/finance handoff, “which contracts expire this month?” (also surfaced on the main dashboard).

---

### Campaigns

**Purpose:** See marketing **campaign** spend across the year.

**What you see:** Table and chart of campaign totals — useful for annual planning and post-campaign review.

---

### Budget

**Purpose:** View **planned** monthly budgets (imported from the budget sheet in Excel).

**What you see:** Budget lines by month, team, and category. Compare with actuals on the Dashboard’s budget variance section.

---

### Excel Import (admins)

**Purpose:** Load or refresh data from the official marketing workbook.

**What happens:** The system reads invoice and budget sheets, maps columns, and updates the database. Skipped rows are reported with reasons — nothing is silently dropped.

**Who:** Admins only. Most users never need this page.

---

### Users (admins)

**Purpose:** Control **who can log in** and **what they can see**.

**What admins set per person:**

- **Role:** Manager (read reports), Editor (enter invoices), or Observer (read only)
- **Team access:** one team, several teams, or all teams
- Flags: view Referral/SMS, upload files, export reports

See also [`operations/ACCESS_BY_ROLE.md`](../operations/ACCESS_BY_ROLE.md) for the full permission picture.

---

### Reference data (admins)

**Purpose:** Keep lookup lists tidy without using the technical Django admin site.

**Sections:**

- **Vendors** — supplier names used on invoices
- **Spend categories** — classification labels
- **Sub-teams** — finer grouping under main teams
- **Requesters** — who requested a spend line

Changes here affect dropdowns and reports going forward.

---

## Roles in one sentence

| Role | In practice |
|------|-------------|
| **Admin** | Sees and changes everything; manages users and imports |
| **Manager** | Sees dashboards and reports for assigned teams; does not edit invoices |
| **Editor** | Enters and updates invoices (and maybe contracts/uploads) for assigned teams |
| **Observer** | Read-only — good for stakeholders who need visibility without changing data |

If you see empty lists everywhere, your admin has not assigned team access yet.

---

## Common tasks

| I want to… | Go to… |
|------------|--------|
| Check overall spend this year | **Dashboard** → pick year |
| See one team only | **Dashboard** → team filter, or **Teams** → pick team |
| Find an invoice by number | **Invoices** → search box |
| Record a new invoice | **Invoices** → **New invoice** (if you are Editor/Admin) |
| See who we paid the most | **Vendors** |
| Check budget vs actual | **Dashboard** → budget variance table |
| Download a spreadsheet for finance | Current page → **Exports** (if enabled) |
| Renew a vendor contract | **Contracts** → open contract → update dates/stage |
| Fix a vendor spelling | **Reference data** → Vendors (Admin) |

---

## Creating users (admins)

On **Users**, admins create accounts with username, **initial password**, role, and team access.

See **[`operations/PASSWORDS_AND_USERS.md`](../operations/PASSWORDS_AND_USERS.md)** for:

- How to change the **admin** password (local vs production)
- Whether admins should pick passwords for colleagues (yes, with caveats)
- Better options to implement next (reset on Users page, self-service change, email reset)

---

## What this guide does not cover

- Installing or deploying the software → [`README.md`](../../README.md), [`SIMPLE_LOCAL_SETUP.md`](SIMPLE_LOCAL_SETUP.md)
- Technical file layout → [`PROJECT_FILE_REFERENCE.md`](../architecture/PROJECT_FILE_REFERENCE.md)
- AWS hosting → [`DEPLOYMENT_AWS.md`](../operations/DEPLOYMENT_AWS.md)

---

## Glossary

| Term | Meaning |
|------|---------|
| **Invoice** | A spend record — vendor, amount, date, payment stage |
| **Team** | Marketing unit (e.g. Growth, Brand) — not the same as “Business Section” in old Excel columns |
| **Referral / SMS** | Special cost buckets shown separately from team spend |
| **Payment stage** | Where the invoice sits in the approval/payment workflow |
| **Budget line** | Planned spend for a month/team/category |
| **Vendor** | Supplier or agency you pay |
| **Campaign** | A named marketing initiative tied to spend |
