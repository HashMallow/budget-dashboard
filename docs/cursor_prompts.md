# Cursor Prompts — Fix Missing Features

Copy-paste each prompt into Cursor. They are self-contained with enough context about the existing codebase.

**Patch status (2026-06-16):** All 9 prompts are **implemented** ✅. See `marketing/tests/test_cursor_prompts.py` and [PROCESSING_LOG.en.md](voice-feedback/PROCESSING_LOG.en.md).

| # | Prompt | Priority | Patched |
|---|--------|----------|---------|
| 1 | Manual Budget CRUD | 🔴 High | ✅ |
| 2 | Budget-line variance on invoice form | 🔴 High | ✅ |
| 3 | Remaining budget % on variance tables | 🟡 Medium | ✅ |
| 4 | PDF export wizard | 🟡 Medium | ✅ |
| 5 | Inline payment-stage edit in lists | 🟡 Medium | ✅ |
| 6 | Vendor/campaign merge UI | 🟡 Medium | ✅ |
| 7 | Team → budget-line cascade | 🟡 Medium | ✅ |
| 8 | Editor Excel import permission | 🟢 Low | ✅ |
| 9 | Contract ceiling on vendor detail | 🟢 Low | ✅ |

After implementing a prompt, update this table, [requirements_audit.md](requirements_audit.md), and [PROCESSING_LOG.en.md](voice-feedback/PROCESSING_LOG.en.md).

---

## 🔴 1. Manual Budget CRUD (High Priority) — ✅ **Patched**

```
Add create, edit, and delete views for BudgetLine records in the marketing app.

Context:
- The BudgetLine model already exists in marketing/models.py (line ~294). Fields: year, month, team (FK), campaign (FK, optional), category, planned_amount (Decimal), currency, source_sheet, source_row_number, raw_data_json.
- Budget lines are currently read-only, displayed in marketing/views/budgets.py → budget_list() and the template templates/marketing/budgets/list.html. They are imported from Excel only.
- The user (product owner) explicitly asked: "I need a section to enter budgets manually. Teams, sub-teams, budget lines should be addable/editable. Budget is month by month (Farvardin to Esfand = months 1–12)."
- Follow the existing CRUD pattern used by reference_views.py (e.g. vendor_reference_create, vendor_reference_edit) and invoices.py (invoice_create, invoice_edit).
- Permission: only admin/superuser can create/edit/delete budget lines. Use the existing permission helper user_has_admin_access() from marketing/permissions.py.

What to implement:
1. Create a BudgetLineForm in marketing/forms.py. Fields: year, month (1-12 dropdown using Jalali month names from marketing/jalali.py JALALI_MONTHS), team (ModelChoiceField), campaign (optional ModelChoiceField), category (use SpendCategory queryset or free text matching existing pattern), planned_amount. Apply apply_ui_language() like other forms.
2. Add budget_create and budget_edit views in marketing/views/budgets.py. Follow the pattern from marketing/views/invoices.py (invoice_create/invoice_edit). Check user_has_admin_access(). On save, leave source_sheet blank and source_row_number null (manual entry).
3. Add a budget_delete view (POST only, admin-only) that deletes a budget line and redirects back to budget_list.
4. Add URL patterns in marketing/urls.py: path("budgets/new/", ...), path("budgets/<int:pk>/edit/", ...), path("budgets/<int:pk>/delete/", ...).
5. Create template templates/marketing/budgets/form.html following the pattern of templates/marketing/invoices/form.html.
6. Add a "New budget line" button on the budget list page (templates/marketing/budgets/list.html) visible only to admins, and add edit/delete links in each pivot row or in the raw budget line table.
7. Add a test in marketing/tests/ that verifies: admin can create a budget line, non-admin gets 403, created budget line appears in budget_list.

Acceptance criteria:
- Admin can navigate to /budgets/new/, fill in year + month + team + category + amount, and save.
- The new budget line appears in the budget list and in the dashboard budget vs actual calculations.
- Non-admin users cannot access the create/edit/delete views.
```

---

## 🔴 2. Budget-Line Variance on Invoice Form (High Priority) — ✅ **Patched**

```
When creating or editing an invoice, show a live budget-line variance panel that displays planned budget, actual spend, remaining budget, and % consumed for the selected budget line / team / month combination.

Context:
- The invoice form is in marketing/forms.py (InvoiceForm class). The create/edit views are in marketing/views/invoices.py.
- The template is templates/marketing/invoices/form.html.
- Budget variance calculation already exists in marketing/analytics.py: budget_actual_variance_window_rows(), jalali_budget_month_totals(), jalali_month_totals().
- The user said (transcript _6): "When I submit an invoice, I pick a budget line. I should see: for this team + budget line, how much was planned, how much spent, deviation, and percentage."
- BudgetLine model has year, month, team, category, planned_amount.

What to implement:
1. Add a JSON API endpoint at marketing/urls.py, e.g. path("api/budget-variance/", views.budget_variance_api, name="budget_variance_api"). This endpoint accepts GET params: team_id, category (budget line name), year, month. It returns JSON: { planned, actual, remaining, percent_consumed }.
2. The view should:
   - Query BudgetLine.objects.filter(team_id=team_id, category=category, year=year, month=month) to get planned amount.
   - Query Invoice.objects.filter(team_id=team_id, category=category) filtered to the same Jalali year/month to get actual spend.
   - Calculate remaining = planned - actual, percent = (actual/planned)*100.
   - Use the existing filter_budget_lines_for_user() permission check.
3. In the invoice form template (templates/marketing/invoices/form.html), add a <div id="budget-variance-panel"> below the category/team/date fields. Style it as a card with 4 values: Planned, Actual, Remaining, % Consumed. Use the existing .card CSS classes.
4. Add JavaScript that listens to changes on the team, category, and invoice_date fields. When all three have values, fetch the API endpoint and update the panel. Convert the invoice_date to Jalali year/month using a simple JS helper or pass it to the server.
5. Show a colored indicator: green if under budget, yellow if 80-100%, red if over budget.

Acceptance criteria:
- When an admin/editor selects a team + category + date on the invoice form, the budget variance panel appears showing planned/actual/remaining/%.
- If no budget line matches, show "No budget data for this combination."
- The panel updates live without page reload.
```

---

## 🟡 3. Remaining Budget % on Variance Tables (Medium Priority) — ✅ **Patched**

```
Add a "% Consumed" column to the budget variance tables on the dashboard and team dashboard.

Context:
- Dashboard template: templates/marketing/dashboard.html, lines ~141-171 show the "Budget vs actual" table with columns: Month, Planned, Actual, Deviation.
- Team dashboard: templates/marketing/teams/dashboard.html has a similar table.
- The data comes from marketing/analytics.py → budget_actual_variance_window_rows() which already returns rows with planned, actual, deviation.
- The "Budget variance by team" collapsible table (dashboard.html ~248-273) also has Planned, Actual, Deviation columns.
- The user said (transcript _6): "Show me the percentage. Next to every number, show the percentage too."

What to implement:
1. In marketing/analytics.py, modify budget_actual_variance_window_rows() to add a "percent_consumed" key to each row: percent_consumed = (actual / planned * 100) if planned > 0 else None.
2. Do the same in team_budget_variance_rows().
3. In budget_variance_row_totals(), add percent_consumed for the totals row.
4. In templates/marketing/dashboard.html, add a "% Consumed" column (<th> and <td>) to the budget variance table. Display as "XX%" with color: green (<80%), yellow (80-100%), red (>100%). Use a template filter or inline logic.
5. Do the same in the "Budget variance by team" table.
6. Do the same in templates/marketing/teams/dashboard.html.
7. In templates/marketing/budgets/list.html, add % consumed to the pivot table if applicable.

Acceptance criteria:
- Every budget variance row (monthly and per-team) shows "% Consumed" colored by severity.
- If planned is 0, show "—" instead of a percentage.
- The totals row also shows overall % consumed.
```

---

## 🟡 4. PDF Export Wizard (Medium Priority) — ✅ **Patched**

```
Add a PDF export wizard page where the user can pick filters (business line, vendor, team, month, year) before generating a PDF report.

Context:
- Current PDF exports are direct links: /reports/dashboard.pdf, /reports/vendors.pdf, /reports/campaigns.pdf, /reports/contracts.pdf (in marketing/urls.py).
- PDF generation is in marketing/reports/pdf.py with functions: build_dashboard_summary_pdf(), build_vendor_report_pdf(), build_campaign_report_pdf(), build_contract_report_pdf().
- Export views are in marketing/views/exports.py. They currently accept query params for filtering but there's no intermediate picker page.
- The user said (transcript _10): "When I click PDF export, open a page where I can select what to export. Maybe just Retail spend, or a specific vendor, or Growth team for one month. Need filters for: month, year, team, vendor, and business line."

What to implement:
1. Create a new view pdf_export_wizard(request) in marketing/views/exports.py (or a new file).
2. Add URL: path("exports/pdf/", views.pdf_export_wizard, name="pdf_export_wizard").
3. Create template templates/marketing/exports/pdf_wizard.html. It should have:
   - Report type selector: Dashboard Summary, Vendor Report, Campaign Report, Invoice List
   - Filter dropdowns: Year, Month (Jalali), Team, Business Line, Vendor (searchable select)
   - Preview text showing what will be exported based on current selections
   - "Generate PDF" button that submits the form
4. On form submit (POST), redirect to the appropriate existing PDF endpoint with the selected filters as query params (e.g. /reports/vendors.pdf?team=3&year=1405&business_section=Retail).
5. The existing PDF views already support query param filtering via filter_invoice_queryset(). Verify they handle business_section, vendor, and month params.
6. Update navigation: replace direct PDF links on dashboards/export sections with a link to the wizard page.
7. Permission: require can_export(request.user) from marketing/permissions.py.

Acceptance criteria:
- User clicks "Export PDF" → lands on wizard page with filter dropdowns.
- User selects filters → clicks Generate → gets a filtered PDF.
- All filter combinations work without errors.
```

---

## 🟡 5. Inline Payment-Stage Edit in Lists (Medium Priority) — ✅ **Patched**

```
Add inline payment-stage change functionality to the invoice list and dashboard queue tables, so users can change stage without opening each invoice's detail page.

Context:
- Invoice list: marketing/views/invoices.py → invoice_list(), template templates/marketing/invoices/list.html.
- Dashboard queues: templates/marketing/dashboard.html lines ~352-413 (marketing queue + finance queue tables).
- Stage update currently works only via invoice_stage_update() view at /invoices/<pk>/stage/ (POST with payment_stage field).
- The user said (transcript _14): "Let me change the payment stage in the invoice list. A dropdown for each invoice to select the status, without going into each invoice page."
- Permission check: can_edit_invoice(request.user, invoice) from marketing/permissions.py.

What to implement:
1. In the invoice list template (templates/marketing/invoices/list.html), add a small <form> or <select> element in each invoice row for users who have edit permission. The select should show PaymentStage choices. On change, submit via JavaScript (POST to /invoices/<pk>/stage/).
2. Implementation approach: For each invoice row, if the user can edit it, render a <select> with the current stage selected. Add a JS event listener on change that sends a fetch() POST to the invoice_stage_update URL with the new stage value + CSRF token. On success, update the row styling (paid/pending CSS class) and show a brief toast/flash message.
3. In the dashboard queue tables (marketing_queue and finance_queue), add a similar quick-action. At minimum, add a "Mark paid" button or a stage dropdown. When the stage changes, the invoice should visually move/disappear from the queue.
4. The existing invoice_stage_update view returns a redirect. Modify it to return JSON { "ok": true, "new_stage": "PAID" } when the request has Accept: application/json or X-Requested-With: XMLHttpRequest header. Otherwise keep the redirect for non-JS fallback.
5. Add appropriate CSRF handling in the JS fetch calls using the Django csrf token from the cookie or a hidden input.

Acceptance criteria:
- Invoice list shows a stage dropdown per row (for authorized users).
- Changing the dropdown updates the stage without full page reload.
- Dashboard queue tables have quick-action buttons.
- Permission checks still apply (non-editors don't see dropdowns).
- Page works without JS (graceful degradation — falls back to normal link to detail page).
```

---

## 🟡 6. Vendor/Campaign Merge UI (Medium Priority) — ✅ **Patched**

```
Add an admin-only UI to merge duplicate vendors and campaigns (fix typos, spacing variations).

Context:
- Vendor model in marketing/models.py has name and normalized_name. Campaign model has name, year, team.
- Reference data CRUD is in marketing/reference_views.py with existing list/create/edit views for vendors, categories, etc.
- The user said: "Admin should be able to merge duplicate vendor/campaign names (typos/spacing)."
- The normalize_name() function in marketing/models.py already handles Unicode normalization.

What to implement:
1. Add a vendor merge view (admin-only): marketing/reference_views.py or a new file. URL: path("reference/vendors/merge/", ..., name="vendor_merge").
2. The merge page should:
   - List all vendors with their normalized names, invoice counts, and a checkbox.
   - Admin selects 2+ vendors → clicks "Merge" → picks the canonical vendor to keep.
   - On merge: update all Invoice.vendor FK, Contract.vendor FK, and any other FKs pointing to the merged vendors. Then delete the duplicate Vendor records.
   - Show a confirmation page listing what will change: "X invoices and Y contracts will be reassigned from [duplicates] to [canonical vendor]."
3. Add a similar campaign merge view at path("reference/campaigns/merge/", ..., name="campaign_merge").
   - Campaign merge updates Invoice.campaign FK and BudgetLine.campaign FK.
4. Add links to the merge pages from the vendor and campaign reference list pages.
5. Wrap everything in a transaction.atomic() block.
6. Log the merge action (which records were merged into which target).
7. Add a test that creates two vendors with similar names, merges them, and verifies all invoices now point to the surviving vendor.

Acceptance criteria:
- Admin can select duplicate vendors → merge them → all invoices/contracts are reassigned.
- Admin can select duplicate campaigns → merge them → all invoices/budget lines are reassigned.
- Non-admin users cannot access merge pages.
- The merge is atomic (all-or-nothing).
```

---

## 🟡 7. Team → Budget-Line Cascade on Invoice Form (Medium Priority) — ✅ **Patched**

```
On the invoice form, when a team is selected, filter the category (budget line) dropdown to show only categories that have budget lines for that team.

Context:
- Invoice form: marketing/forms.py → InvoiceForm. The category field currently shows all SpendCategory records.
- BudgetLine model has team (FK) and category (CharField). SpendCategory model has name.
- The user said (transcript _5, _19): "Budget lines should be based on the database. When I select a team, show only the budget lines for that team."

What to implement:
1. Add a JSON API endpoint: path("api/categories-for-team/", views.categories_for_team_api, name="categories_for_team_api"). It accepts GET param team_id and returns JSON list of category names that have BudgetLine records for that team.
2. In the invoice form template (templates/marketing/invoices/form.html), add JavaScript that:
   - Listens to the team <select> change event.
   - Fetches /api/categories-for-team/?team_id=<selected> 
   - Filters the category dropdown to show only matching categories.
   - If no team is selected, show all categories.
3. Keep the full category list in the HTML (for no-JS fallback) but filter via JS.
4. Also consider filtering campaigns by team using the same pattern.

Acceptance criteria:
- Selecting a team on the invoice form filters the category dropdown to relevant budget lines.
- Clearing the team shows all categories.
- Works without JS (all categories remain available).
```

---

## 🟢 8. Editor Excel Import Permission (Low Priority) — ✅ **Patched**

```
Allow editors (not just admins) to import Excel workbooks, controlled by a permission flag.

Context:
- Import view: marketing/views/imports.py → import_workbook(). Currently checks user_has_admin_access().
- UserTeamAccess model has boolean flags: can_upload_invoice_files, can_upload_payment_proofs, can_export.
- The user said: "Editors should be able to import Excel."

What to implement:
1. Add a new boolean field can_import_excel to UserTeamAccess model in marketing/models.py. Default False. Run makemigrations + migrate.
2. Add a helper function can_import(user) in marketing/permissions.py. Returns True if superuser or if any active UserTeamAccess for the user has can_import_excel=True.
3. Update import_workbook() view to use can_import(request.user) instead of user_has_admin_access(request.user).
4. Update the user access management form (marketing/forms.py → UserTeamAccessForm or wherever the admin manages user permissions) to include the new can_import_excel field.
5. Update the navigation/UI to show the "Import" link for users who have can_import permission, not just admins.
6. Add a test verifying: editor with can_import_excel=True can access import page; editor without it gets 403.

Acceptance criteria:
- Admin can grant import permission to specific editors.
- Editors with the flag can access /imports/ and upload workbooks.
- Editors without the flag still get 403.
```

---

## 🟢 9. Contract Ceiling on Vendor Detail (Low Priority) — ✅ **Patched**

```
Show the contract amount (ceiling) column in the contracts table on the vendor detail page.

Context:
- Vendor detail template: templates/marketing/vendors/detail.html, lines 63-88 show a contracts table with columns: Title, Stage, End date.
- Contract model has an `amount` field (DecimalField, nullable).
- The user said (transcript _8): "I need to know the cooperation ceiling of their contract."
- The vendor detail view is in marketing/views/reports.py → vendor_detail().

What to implement:
1. In templates/marketing/vendors/detail.html, add a <th>Amount</th> column header and a <td>{{ contract.amount|money }}</td> cell in the contracts table. Also add start_date.
2. Update the table headers to: Title, Stage, Start date, End date, Amount (ceiling).
3. If contract.amount is null, display "—".

Acceptance criteria:
- Vendor detail page shows contract ceiling amount and start date alongside existing columns.
```

---

## Recommended Order

1. **Manual Budget CRUD** (🔴) — most impactful, unblocks budget workflow
2. **Budget-Line Variance on Invoice Form** (🔴) — depends on having budget data
3. **Remaining Budget %** (🟡) — quick win, complements #1 and #2
4. **Inline Payment-Stage Edit** (🟡) — big UX improvement
5. **PDF Export Wizard** (🟡) — extends existing functionality
6. **Team → Budget-Line Cascade** (🟡) — improves data entry quality
7. **Vendor/Campaign Merge** (🟡) — admin quality-of-life
8. **Editor Excel Import** (🟢) — small permission change
9. **Contract Ceiling on Vendor Detail** (🟢) — 5-minute template fix
