# Consolidated User Requirements (Sorted by User Needs & Personas)

This document gathers all actionable feedback from the voice transcripts dated June 16, 2026 (files `_2` through `_22`). The requirements have been reorganized based on the core needs of the different users interacting with the system, along with their source file references and current implementation status.

## 1. Data Entry & Accuracy (The "Editor" Need)
*Users entering data need a frictionless, error-proof way to log marketing spend.*
* **Strict Dropdowns:** Business Line, Budget Category, Vendor, and Campaign fields must be dropdowns to prevent typos. `[Source: _4, _19, _21]` `[Status: Implemented]`
* **Auto-Calculated Financials:** The system must automatically calculate VAT, subtract Insurance Withholding, and output the final Paid Amount. Editors only input the base Action Cost. `[Source: _2, _12]` `[Status: Implemented]`
* **Live Budget Variance:** The form must show a live variance check (planned vs. actual and % consumed) so Editors immediately know how much budget is left. `[Source: _6]` `[Status: Implemented]`
* **Flexible Creation & Inline Edits:** Editors must be able to add new Vendors/Campaigns on the fly, and update payment stages inline directly from list views. `[Source: _14, _21]` `[Status: Implemented]`

## 2. Financial Tracking & Workflow (The "Finance/Ops" Need)
*Reviewers need exact financial breakdowns, audit trails, and bottleneck tracking.*
* **Exact Financial Splits:** Invoices must strictly track Action Cost, VAT, Insurance, and the Net Paid Amount. `[Source: _2, _12]` `[Status: Implemented]`
* **Bottleneck Queues:** The dashboard requires a *Marketing Queue* and a *Finance Queue*, both showing the number of days an invoice has been waiting. `[Source: _17, _20, _22]` `[Status: Implemented]`
* **Recently Paid Hub:** A dedicated section showing recently paid invoices with quick links to download payment receipts. `[Source: _22]` `[Status: Implemented]`
* **Contracts Tracking:** The system must track contracts and mandate the upload of final signed versions. `[Source: _9]` `[Status: Implemented]`

## 3. High-Level Reporting & Analysis (The "Manager" Need)
*Managers need clear, accurate, and filterable overviews of team spending.*
* **Dashboard Filtering:** Support for filtering by Year, Team, Business Line, and Jalali Month. `[Source: _3, _17, _20]` `[Status: Implemented]`
* **Anomaly Separation:** Huge costs like SMS and Referral programs must be structurally isolated (SMS under Retention, Referral under Growth) so they don't skew standard team charts. `[Source: _13]` `[Status: Implemented]`
* **Vendor Hub:** Every vendor mention must be clickable, routing to a Vendor Detail page showing historical spend and contracts. `[Source: _8]` `[Status: Implemented]`
* **Exporting Wizards:** A custom PDF export wizard to slice data by Business Line, Vendor, Team, and Month. `[Source: _10]` `[Status: Implemented]`
* **Exact Excel Round-trip Export:** Extracting data back into an Excel file that identically mirrors the original 4-sheet starting template for Google Sheets syncing. `[Source: 22-09-58]` `[Status: Backlog - To Be Implemented]`

## 4. System Administration & Control (The "Admin" Need)
*Admins need tools to maintain data hygiene and set global parameters.*
* **Reference Data Locks:** Only Admins can add or manage core Business Lines and Budget Lines. `[Source: _21]` `[Status: Implemented]`
* **Duplicate Merging:** An Admin UI to merge duplicate or misspelled Vendor/Campaign entries created by Editors. `[Source: _21]` `[Status: Implemented]`
* **Manual Budgeting:** A panel to manually enter and edit budget lines by team, category, and month. `[Source: _5, _18, _19]` `[Status: Implemented]`

## 5. Usability & Experience (Universal User Need)
*All users expect a modern, culturally localized, and highly readable interface.*
* **Jalali Everywhere:** Consistent use of the Jalali (Shamsi) calendar. `[Source: _11, 22-29-43]` `[Status: Implemented]`
* **Visual Status Cues:** Color-coded rows (paid vs. unpaid) and a dash (`—`) for days waiting when an invoice is fully paid. `[Source: _8, _15, _16]` `[Status: Implemented]`
* **Smart Sorting:** Lists should default to sorting by Entry Date. `[Source: _15, _16]` `[Status: Implemented]`
* **UI Polish & Correct Terminology:** Wider charts, Dark Mode, consolidated navigation, and fixing the confusing terminology mix-up between "Actual Spend" and "Budget" on the dashboard. `[Source: _7, _11, 22-05-26]` `[Status: Implemented — 2026-06-16]`
