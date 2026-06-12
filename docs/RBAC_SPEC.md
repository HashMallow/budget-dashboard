# RBAC and Permission Specification

## Goal
Ensure every user sees and modifies only the data they are allowed to access.

## Roles

### Admin
Implemented through Django superuser or Admin group.

Permissions:

- view all data
- edit all data
- upload all files
- export all reports
- manage users and team access

### Manager
Permissions:

- view dashboards and reports for permitted scope
- view invoices, vendors, campaigns, and budgets for permitted scope
- export if `can_export` is true
- no user management unless later granted

### Editor
Permissions:

- view permitted team data
- create invoice records for permitted teams
- edit invoice records for permitted teams
- update payment stage if permitted by view/form policy
- upload invoice files only if `can_upload_invoice_files` is true
- upload payment proof only if `can_upload_payment_proofs` is true
- export only if `can_export` is true

### Observer
Permissions:

- view permitted data
- no create/edit/delete
- no upload
- no user management

## Scope Rules

Each non-admin user gets one or more `UserTeamAccess` rows.

A row can be:

- team-specific: user can access one team
- global: user can access all marketing data according to their role

Referral and SMS data are not normal team data. Non-admin users can see Referral/SMS only when:

- they have global access, or
- `can_view_referral_sms` is true

## Server-Side Enforcement

Implement helper functions such as:

```python
get_user_scope(user)
filter_invoices_for_user(queryset, user)
filter_budget_lines_for_user(queryset, user)
filter_campaigns_for_user(queryset, user)
can_edit_invoice(user, invoice)
can_upload_invoice_file(user, invoice)
can_upload_payment_proof(user, invoice)
can_export(user, scope)
```

Use these helpers in every view, form, API endpoint, chart endpoint, and export endpoint.

Do not rely on template-level hiding alone.

## Permission Tests

Add tests for at least these cases:

1. Admin can see all invoices.
2. Team A editor cannot see Team B invoices.
3. Team A editor cannot create invoices for Team B.
4. Observer cannot edit invoices.
5. Editor without upload permission cannot upload invoice files.
6. Editor with upload permission can upload invoice files for own team.
7. Manager without `can_view_referral_sms` cannot see Referral/SMS rows.
8. Global manager can see all teams.
9. Export endpoint respects user scope.
10. Chart endpoint respects user scope.
