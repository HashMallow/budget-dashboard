# Product Requirements — Marketing Finance Hub

> Historical title: *Marketing Spend Monitoring Dashboard*. Requirements below are unchanged.

## Source Material and Discovery

The original request came from Persian text plus an `.ogg` audio note. Before implementation, Codex must transcribe the audio and compare it with these written requirements. Any additional requirements found in audio must be added to `docs/discovery/audio_requirements.en.md` and reflected in implementation tasks.

The `.xlsx` workbook structure must also be inspected before finalizing imports or database mappings. The actual workbook mapping belongs in `docs/discovery/column_mapping.yml`.


## Goal
Create an internal panel for monitoring and analyzing marketing spend. The system should help the admin and authorized users understand where marketing money is being spent, by month, team, vendor, campaign, payment status, Referral, and SMS.

## Users and Roles

### Admin
The admin has full access to everything:

- all dashboards
- all teams
- all vendors
- all invoices
- all budgets
- all campaigns
- all exports
- all uploads
- user and permission management

### Manager
Managers can view dashboards and reports for their permitted team scope. Some managers may have global/all-marketing access.

### Editor
Editors can enter invoice/spend data for their assigned teams. They can track invoice status if permitted. Upload permissions are controlled separately.

### Observer
Observers can only view permitted data and cannot edit or upload.

## Core Features

### 1. Authentication
Users log in using username/password. Admin can create and manage users.

### 2. Access Control
Admin assigns users to roles and teams. A user may have access to one or more teams. Users only see records they are allowed to see.

### 3. Excel-Based Initial Import
The system imports data from an Excel file. The workbook has at least:

- an input/data-entry sheet
- a budget sheet

After import, the database is the main source of truth. Excel remains an import/export format.

### 4. Dashboards
The dashboard must show:

- overall marketing spend
- spend by month
- spend by team
- spend by category
- separate Referral spend
- separate SMS spend
- vendor spend from highest to lowest
- invoice payment stage summary
- campaign spend over the year

### 5. Team Drilldown
When a team is selected, the panel must show:

- vendor names
- number of invoices per vendor
- invoice numbers per vendor
- payment stage of invoices
- total spend per vendor
- team campaign costs

### 6. Vendor Reporting
There must be a table showing vendors sorted by total spend, highest to lowest.

### 7. Campaign Reporting
There must be a table and chart showing campaign costs during the year. Campaigns can be linked to teams, categories, vendors, and invoices.

### 8. Data Entry
Admin can enter all invoice/spend data. Editors can enter data only for permitted teams.

### 9. Invoice Tracking
Invoices must have payment stages. Users should be able to see how long an invoice has been in a stage such as finance review.

### 10. File Uploads
Authorized users can upload:

- invoice images/documents
- payment proof/receipt images

Access to uploads follows the same data-scope permissions.

### 11. Export
Authorized users can export reports to:

- Excel
- PDF

Exports must respect access control.

## Key Business Rules

1. Referral and SMS costs are part of total marketing spend but must be displayed separately from normal team spend.
2. Team-limited users must not see other teams' invoices, vendors, or campaign details unless explicitly granted.
3. Payment status updates must be visible to users with access to the invoice.
4. Status changes must create a history record.
5. The number of days in the current payment stage must be visible.
6. Vendor spend must be sortable and default to descending total spend.
7. Campaign spend must support year-level reporting.

## Out of Scope for First Version

- Production deployment
- SSO
- Multi-company tenancy
- Real-time notifications
- Complex approval workflows beyond payment stage tracking
- External accounting-system integration
