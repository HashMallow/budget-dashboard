# Permissions Matrix

Quick reference for what each user group can do in the **Marketing Finance Hub**.

For the detailed explanation, see `docs/operations/ACCESS_BY_ROLE.md`. For implementation, see
`marketing/permissions.py` and `marketing/forms.py`.

## Roles

```text
Admin
  Full access. Implemented as Django superuser or membership in the Admin group.

Manager
  View/report access for assigned teams or all teams if global access is enabled.

Editor
  Can view and enter/update invoice data for assigned teams.

Observer
  Read-only access for assigned teams.
```

## Scope Rules

| Scope / flag | Meaning |
|---|---|
| Team-specific access | User can see data for one assigned team. |
| All-team access | User can see all regular team data. |
| View referral and SMS | User can see Referral/SMS cost buckets even if team-limited. |
| Can export | User can export only the data they are allowed to see. |
| Upload invoice files | Editor can upload invoice images/documents. |
| Upload payment receipts | Editor can upload payment proof files. |

Multiple access rows combine. Example: Editor for Growth + Observer for Brand means editable Growth
data and read-only Brand data.

## Capability Matrix

| Capability | Admin | Manager | Editor | Observer |
|---|:---:|:---:|:---:|:---:|
| Log in to custom panel | Yes | Yes | Yes | Yes |
| See dashboard within scope | All data | Scope only | Scope only | Scope only |
| See invoices within scope | All data | Scope only | Scope only | Scope only |
| See vendor/campaign reports within scope | All data | Scope only | Scope only | Scope only |
| See budget lines within scope | All data | Scope only | Scope only | Scope only |
| See Referral/SMS | Yes | Global or flag | Global or flag | Global or flag |
| Create invoices | Yes | No | Assigned/global scope | No |
| Edit invoices | Yes | No | Assigned/global scope | No |
| Update payment stage | Yes | No | Assigned/global scope | No |
| Upload invoice files | Yes | No | If upload flag enabled | No |
| Upload payment receipts | Yes | No | If payment-proof flag enabled | No |
| Export Excel/PDF | Yes | If export flag enabled | If export flag enabled | If export flag enabled |
| Import workbook | Yes | No | No | No |
| Create/deactivate users | Yes | No | No | No |
| Assign roles/team access | Yes | No | No | No |
| Django Admin `/admin/` | Yes | No | No | No |

## Route-Level Summary

| Route | Admin | Manager | Editor | Observer |
|---|:---:|:---:|:---:|:---:|
| `/` dashboard | Yes | Scoped | Scoped | Scoped |
| `/teams/` and `/teams/<id>/` | Yes | Scoped | Scoped | Scoped |
| `/invoices/` | Yes | Scoped | Scoped | Scoped |
| `/invoices/new/` | Yes | No | Scoped | No |
| `/invoices/<id>/edit/` | Yes | No | Scoped | No |
| `/invoices/<id>/stage/` | Yes | No | Scoped | No |
| `/invoices/<id>/attachments/` | Yes | No | Scoped + flag | No |
| `/vendors/` | Yes | Scoped | Scoped | Scoped |
| `/campaigns/` | Yes | Scoped | Scoped | Scoped |
| `/budgets/` | Yes | Scoped | Scoped | Scoped |
| `/imports/` | Yes | No | No | No |
| `/users/` | Yes | No | No | No |
| `/exports/*.xlsx` | Yes | Scoped + flag | Scoped + flag | Scoped + flag |
| `/reports/*.pdf` | Yes | Scoped + flag | Scoped + flag | Scoped + flag |

## Data Filtering

| Data type | Admin/global | Team-limited users |
|---|---|---|
| Teams | All active teams | Assigned teams only |
| Invoices | All invoices | Assigned team invoices, excluding Referral/SMS unless flag enabled |
| Budgets | All budget lines | Assigned team budget lines only |
| Campaigns | All campaigns | Assigned team campaigns plus teamless/shared campaigns |
| Referral/SMS | All | Only with global access or View referral and SMS flag |

## Local Testing Scenarios

Use these when manually checking permissions:

```text
Admin
  Can open /users/, /imports/, create invoice, export, upload files.

Growth Editor
  Can see Growth data.
  Can create/edit Growth invoices.
  Cannot see Brand invoices.
  Cannot upload unless upload flags are enabled.

Growth Observer
  Can see Growth data.
  Cannot create/edit invoices.
  Cannot upload.

Manager with export flag
  Can see reports for scope.
  Can export only scoped data.
  Cannot create/edit invoices.
```

## Enforcement Points

```text
marketing/permissions.py
  Central queryset filtering and action checks.

marketing/forms.py
  Form-level validation for team/cost assignment and uploads.

marketing/views.py
  Applies permission helpers before render, edit, upload, import, or export.
```

The UI may hide buttons, but the server-side checks are the security boundary.
