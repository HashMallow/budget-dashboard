# Access by Role (who can see and do what)

This document explains, in practical terms, what each user group/role can access in the
Marketing Spend Dashboard. It reflects what the code actually enforces (see
`marketing/permissions.py` and `marketing/forms.py`). For the underlying design spec, see
`docs/RBAC_SPEC.md`.

> **Golden rule:** access is enforced **server-side** on every queryset, view, and export.
> Hiding a button in the UI is never the security boundary — the data is filtered for the
> logged-in user before it is ever sent to the page.

---

## The two kinds of users

1. **Admin** — a Django **superuser** *or* a member of the **`Admin`** group.
   Admins bypass all team-level rules and see/do everything.
2. **Everyone else** — gets one or more **access rows** (`UserTeamAccess`) created by an admin
   on the `/users/` page. Each row grants a **role** over a **scope**.

A non-admin user with **no active access rows sees nothing** (empty lists everywhere). This is
intentional and safe.

---

## Roles

There are four effective roles:

| Role | Core idea |
|---|---|
| **Admin** | Full control of all data, users, imports, and exports. |
| **Manager** | Read/report access for the permitted scope. No editing, no user management. |
| **Editor** | Can create and edit invoices/spend for the permitted scope (uploads are opt-in). |
| **Observer** | Read-only access for the permitted scope. No edits, no uploads. |

(`Manager`, `Editor`, `Observer` are the values stored on each access row. `Admin` is the
superuser/`Admin`-group case.)

---

## Scope: which data a user can reach

Each access row is either:

- **Team-specific** — grants access to **one team**, or
- **Global** (`All teams`) — grants access to **all marketing data** at that role.

**Referral and SMS** spend is *not* normal team data. A non-admin user sees Referral/SMS rows
only if they have **global** access **or** the **`View referral and SMS`** flag is on.

### Per-user flags (set per access row on `/users/`)

| Flag | Effect |
|---|---|
| `All teams` (global) | Role applies across every team + Referral/SMS. |
| `View referral and SMS` | Lets a team-limited user also see Referral/SMS rows. |
| `Upload invoice files` | Editor may attach invoice images/documents. |
| `Upload payment receipts` | Editor may attach payment proof images. |
| `Can export` | User may run Excel/PDF exports for their scope. |

### Multiple rows combine (union)

If a user has several active rows, their effective scope is the **union**: every team listed,
plus global if any row is global, plus any flag that is enabled on any row, plus every role
listed. Example: a user with `Editor`/Team A and `Observer`/Team B can edit Team A invoices and
read Team B invoices.

---

## What each role can see and do

| Capability | Admin | Manager | Editor | Observer |
|---|:---:|:---:|:---:|:---:|
| See dashboard & charts (within scope) | ✅ all | ✅ scope | ✅ scope | ✅ scope |
| See invoices / vendors / campaigns / budgets (within scope) | ✅ all | ✅ scope | ✅ scope | ✅ scope |
| See Referral / SMS spend | ✅ | only if global or `View referral and SMS` | only if global or `View referral and SMS` | only if global or `View referral and SMS` |
| Create invoices | ✅ | ❌ | ✅ for permitted teams | ❌ |
| Edit invoices | ✅ | ❌ | ✅ for permitted teams | ❌ |
| Update payment stage (writes status history) | ✅ | ❌ | ✅ for permitted teams | ❌ |
| Upload invoice image/document | ✅ | ❌ | ✅ if `Upload invoice files` | ❌ |
| Upload payment proof | ✅ | ❌ | ✅ if `Upload payment receipts` | ❌ |
| Export to Excel / PDF | ✅ | ✅ if `Can export` | ✅ if `Can export` | ✅ if `Can export` |
| Import Excel workbook (`/imports/`) | ✅ | ❌ | ❌ | ❌ |
| Manage users & access (`/users/`) | ✅ | ❌ | ❌ | ❌ |
| Django Admin (`/admin/`) | ✅ (staff/superuser) | ❌ | ❌ | ❌ |

Notes:

- **Create/edit is tied to the `Editor` role**, not just team membership: a user must hold an
  `Editor` row for the invoice's team (or a global `Editor` row) to create/edit it. Creating a
  Referral/SMS invoice additionally requires global access or the `View referral and SMS` flag.
- **Editing is what gates payment-stage changes** — anyone who can edit an invoice can move it
  through the payment stages, and each change is recorded in the invoice's status history.
- **Uploads require the `Editor` role *and* the matching upload flag.** A Manager or Observer can
  never upload, even if a flag were set.
- **Exporting** is allowed for any role (including Manager/Observer) when `Can export` is on, but
  the exported data is still limited to the user's scope.

---

## Visibility rules in detail (per data type)

These are the server-side filters applied to every list, report, chart, and export:

- **Invoices** — Admin/global: all. Otherwise: invoices of the user's teams (excluding
  Referral/SMS buckets), **plus** Referral/SMS invoices only if `View referral and SMS`. No teams
  and no referral/SMS access → nothing.
- **Budget lines** — Admin/global: all. Otherwise: budget lines for the user's teams only.
- **Campaigns** — Admin/global: all. Otherwise: campaigns for the user's teams **and** campaigns
  with no team (shared/company-wide).
- **Teams** — Admin/global: all. Otherwise: only the user's teams.

---

## How to assign access (admin workflow)

1. Sign in as admin and open **`/users/`** (Users and access).
2. Create the user (username + password) or pick an existing one.
3. Add an access row: choose the **role**, then either a **team** or **All teams** (global).
4. Toggle the flags as needed: `View referral and SMS`, `Upload invoice files`,
   `Upload payment receipts`, `Can export`.
5. Add more rows for the same user to combine scopes (e.g. Editor on one team + Observer on
   another). Deactivating a row (or the user) removes that access without deleting history.

> Day-to-day users live in the **database**, created here — not in `.env`. The `.env` file is only
> for deployment settings/secrets (`SECRET_KEY`, `DATABASE_URL`, allowed hosts).

---

## Where this is enforced (for developers)

All checks route through `marketing/permissions.py`:

- `get_user_scope(user)` — resolves the effective scope (admin/global/team_ids/roles/flags).
- `filter_invoices_for_user`, `filter_budget_lines_for_user`, `filter_campaigns_for_user`,
  `filter_teams_for_user` — scope every queryset before display/export.
- `can_create_invoice_for_team`, `can_edit_invoice`, `can_upload_invoice_file`,
  `can_upload_payment_proof`, `can_export` — gate write/upload/export actions.
- `user_has_admin_access` — superuser or `Admin` group; gates `/users/` and `/imports/`.

Permission behavior is covered by tests in `marketing/tests/test_permissions.py`.
