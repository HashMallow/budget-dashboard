# Dashboard and Reporting Specification

> **Implemented UI (2026):** The live panel uses the **Marketing Finance Hub** branding, a **sectioned sidebar** (Overview / **Finance** / Administration / Help), and a **Finance overview** dashboard with KPI cards labeled **Planned budget (projection)** vs **Total actual spend**, full-width charts, budget variance with `% Consumed`, and team-filtered layouts. Invoice forms auto-calculate VAT, insurance, and paid amount from action cost. See [`guides/USER_SITEMAP.md`](../guides/USER_SITEMAP.md) for the end-user map. This spec remains the requirements reference.

## Dashboard Navigation

Provide a simple internal dashboard with these main sections:

1. Overview (Dashboard)
2. Finance (Invoices, Teams, Budget, Vendors, Campaigns, Contracts)
3. Administration (Excel Import, Users, Reference data) — admin only
4. Help — bottom of sidebar; also `/help/`
5. Exports — top bar on relevant pages

## Overview Dashboard

Visible to Admin and authorized Managers.

Cards:

- Total actual spend (and planned budget projection where shown)
- Total team spend
- Referral spend
- SMS spend
- Number of invoices
- Number of unpaid invoices
- Number of invoices in finance review

Invoice financial breakdown (per invoice and on vendor detail):

- Action cost (base marketing spend)
- Tax (10% VAT on action cost by default)
- Insurance withholding (16.67% or 7.78% typical)
- Paid amount — net paid by finance: `(action − insurance) + tax`
- Invoice face total (`amount` = action + tax)

Year-end aggregate report separating marketing spend vs tax vs insurance deposits — **not built yet** (see [`requirements_audit.md`](../requirements_audit.md)).

Charts:

- Pie chart: overall spend by team/cost bucket
- Bar/line chart: monthly total spend
- Pie or stacked chart: monthly spend by team
- Separate chart/card for Referral spend
- Separate chart/card for SMS spend
- Invoice count by payment stage

Tables:

- Top vendors by spend, descending
- Invoices currently in finance review, sorted by days in stage descending
- Campaign spend summary for selected year

## Team Dashboard

When a team is selected, show:

- Team total spend
- Monthly team spend
- Team campaign spend
- Vendor table for the team
- Invoice table for the team

Vendor table columns:

- vendor name
- invoice count
- invoice numbers
- current payment stages
- total amount

Invoice table columns:

- invoice number
- vendor
- campaign
- category
- amount
- payment stage
- days in current stage
- invoice date
- paid date
- attachment count

## Vendor Report

Default sorting: total spend descending.

Columns:

- vendor name
- total spend
- invoice count
- invoice numbers
- teams involved
- campaigns involved
- unpaid amount
- paid amount

Filters:

- year
- month
- team
- campaign
- category
- payment stage
- cost bucket

## Campaign Report

Show campaign costs throughout the year.

Columns:

- campaign name
- year
- team
- planned amount if available
- actual spend
- variance actual minus planned
- invoice count
- vendors

Charts:

- campaign spend by month
- campaign spend by team
- planned vs actual if budget data exists

## Invoice Tracking

Invoice list should support filters:

- team
- vendor
- campaign
- category
- payment stage
- date range
- cost bucket

Invoice detail must show:

- all invoice fields
- uploaded invoice images/documents
- uploaded payment proof images
- status history
- days in current status

## Chart Implementation

Use Chart.js. Server should provide aggregated JSON endpoints or embed JSON in templates.

Important: do not aggregate unauthorized data in the frontend. All aggregation must be permission-filtered on the server.

## Export UI

Provide export buttons on report pages:

- Export current filtered table to Excel
- Export current filtered report to PDF

Exports must use the same filters and permission scope as the visible page.
