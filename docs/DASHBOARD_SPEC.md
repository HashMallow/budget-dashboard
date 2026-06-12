# Dashboard and Reporting Specification

## Dashboard Navigation

Provide a simple internal dashboard with these main sections:

1. Overview
2. Teams
3. Vendors
4. Campaigns
5. Invoices
6. Budget
7. Exports
8. User Access Management, admin only

## Overview Dashboard

Visible to Admin and authorized Managers.

Cards:

- Total marketing spend
- Total team spend
- Referral spend
- SMS spend
- Number of invoices
- Number of unpaid invoices
- Number of invoices in finance review

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
