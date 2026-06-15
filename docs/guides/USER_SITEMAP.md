# Site map — what each part of the panel does

A plain-language guide for marketing, finance, and operations staff who use the **Marketing Finance Hub** day to day. No technical background required.

**Inside the app:** open **Help** (راهنما) at the **bottom of the left menu** — or go to `/help/` before sign-in. Content appears in your chosen language (English or فارسی).

---

## What this application is for

The panel replaces scattered Excel tracking with one place to:

- See how much marketing money was spent, by team, vendor, and campaign
- Track each invoice from submission through payment
- Compare **planned budget** vs **actual spend**
- Track vendor **contracts** and upcoming renewals
- Filter and report by **business line** (business segments: Consumer, Youth, Enterprise, etc. from Excel)
- Export reports to Excel or PDF for meetings and finance

The database is the source of truth after the first Excel import. Day-to-day work happens in the panel; Excel is mainly for bulk import and export.

---

## How to open the panel

1. Go to the web address your IT team gave you (for local testing, usually `http://127.0.0.1:8000/`).
2. Sign in with the **username** and **password** your admin created.
3. You land on the **Finance overview** dashboard — the home screen.

To sign out, use **Logout** at the bottom of the left menu (below your username).

---

## The left menu (grouped sections)

The sidebar is organized in sections (not one long flat list). **Help** is always at the bottom, above your user name.

### Overview

| Item | What it is for |
|------|----------------|
| **Dashboard** | Big-picture spend, charts, budget vs actual, payment status |

### Spend & teams

| Item | What it is for |
|------|----------------|
| **Invoices** | List, search, create, and edit marketing invoices |
| **Teams** | Pick a team and open its focused dashboard |

### Reports

| Item | What it is for |
|------|----------------|
| **Budget** | Planned monthly budgets from the workbook |
| **Vendors** | Which suppliers you paid, how much, and payment stages |
| **Campaigns** | Spend grouped by marketing campaign for the year |
| **Contracts** | Vendor agreements, dates, stages, attachments |

### Administration *(admins only)*

| Item | What it is for |
|------|----------------|
| **Excel Import** | Upload the master workbook to refresh data |
| **Users** | Create logins and set who can see which teams |
| **Reference data** | Maintain vendors, categories, sub-teams, campaigns, requesters |

### Help *(bottom of menu)*

| Item | What it is for |
|------|----------------|
| **Help** | This guide, inside the app |

**Who sees what:** Everyone sees Overview, Spend & teams, and Reports (within their team access). Only admins see Administration. Help is available to everyone, including before sign-in at `/help/`.

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

PDF exports use correct Persian text direction when your language is فارسی.

If you do not see export buttons, your admin may not have enabled **Can export** for your account.

---

## Page-by-page guide

### Dashboard (Finance overview)

**Purpose:** The management overview — calmer layout with grouped sections.

**What you see:**

- **Primary cards:** total spend, planned budget, budget deviation, invoice count
- **Secondary strip:** paid amount, Referral, SMS, contract alerts
- **Budget vs actual** and **monthly trend** side by side
- When viewing **all teams:** spend pie and spend-by-team charts in a separate row
- When **one team is filtered:** a banner shows which team; pie and team breakdown hide; budget and monthly trend stay paired (like the team dashboard)
- Tables: top vendors, campaigns, payment stages, invoices in finance review
- **Budget by team** (all teams only) in a collapsible section

**Filters:** year and team at the top.

**Typical use:** Monday stand-up, monthly review, “how are we doing against budget?”

---

### Invoices

**Purpose:** The working list of every marketing spend line / invoice.

**What you can do:**

- **Search** by invoice number, vendor, campaign, category, **business line**, or description
- **Filter** by team, payment stage, year, **business line**, etc.
- Open an invoice to see full detail, payment history, and uploaded files
- **Editors** and **Admins** can add invoices and change payment stage
- Attach **invoice images** and **payment receipts** if your admin allowed uploads

**Business line** is the business segment from Excel (**Business Section**): Consumer, Youth, Enterprise, etc. It is separate from **team** (Growth, Brand, …).

**Payment stages** (workflow): Draft → Submitted → Finance review → Approved → Paid (or Rejected / Cancelled). The detail page shows how many days an invoice has been in the current stage.

---

### Teams

**Purpose:** Focus on one marketing team at a time.

**Flow:**

1. Open **Teams** — you see only teams you may access.
2. Click a team name → **team dashboard** with that team’s spend, vendors, campaigns, and attention items.

You can also filter the main dashboard to one team, or open **Open team dashboard** from the team filter banner.

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

**Admins** can add campaigns under **Reference data → Campaigns** or from the Campaigns page.

---

### Budget

**Purpose:** View **planned** monthly budgets (imported from the budget sheet in Excel).

**What you see:** Budget lines by month, team, and category. When you filter to one team, the planned-by-team chart hides; monthly plan and tables still show that team. Compare with actuals on the Dashboard’s budget variance section.

---

### Excel Import (admins)

**Purpose:** Load or refresh data from the official marketing workbook.

**What happens:** The system reads invoice and budget sheets, maps columns (including **Business Section** → business line), and updates the database. Skipped rows are reported with reasons — nothing is silently dropped.

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
- **Campaigns** — named initiatives linked on invoices
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
| Find invoices for a business segment (e.g. Junior) | **Invoices** → **Business line** filter or search |
| Find an invoice by number | **Invoices** → search box |
| Record a new invoice | **Invoices** → **New invoice** (if you are Editor/Admin) |
| See who we paid the most | **Vendors** |
| Check budget vs actual | **Dashboard** → budget vs actual section |
| Download a spreadsheet for finance | Current page → **Exports** (if enabled) |
| Renew a vendor contract | **Contracts** → open contract → update dates/stage |
| Fix a vendor spelling | **Reference data** → Vendors (Admin) |
| Add a campaign | **Reference data** → Campaigns, or **Campaigns** → New campaign (Admin) |
| Onboard a colleague | **Users** → New user (Admin) |

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
| **Team** | Marketing unit (e.g. Growth, Brand) |
| **Business line** | business segment from Excel **Business Section** (Consumer, Youth, Enterprise, …) — filterable on invoices; separate from team |
| **Referral / SMS** | Special cost buckets shown separately from team spend |
| **Payment stage** | Where the invoice sits in the approval/payment workflow |
| **Budget line** | Planned spend for a month/team/category |
| **Vendor** | Supplier or agency you pay |
| **Campaign** | A named marketing initiative tied to spend |
