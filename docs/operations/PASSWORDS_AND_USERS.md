# Passwords and user accounts

Plain-language guide for admins: how passwords work today, how to change the admin password, whether you should set passwords for colleagues, and better options as the team grows.

**Related:** [`ACCESS_BY_ROLE.md`](ACCESS_BY_ROLE.md) · in-app **Users** (`/users/`) · **Help** (`/help/`)

---

## How login works today

- Everyone signs in with a **username** and **password** stored in the database (Django auth).
- The panel does **not** read day-to-day usernames from `.env` — only server settings like `SECRET_KEY` and `DATABASE_URL`.
- There is **no “forgot password” email** and **no self-service “change my password” page** in the panel yet (see [Better approaches](#better-approaches) below).

---

## Change the admin password

Use the method that matches your environment.

### Local development (DEBUG on)

**Option A — Makefile (easiest)**

```bash
# Default user admin / password admin12345 (from Makefile)
make dev-admin

# Or set your own for one run:
make dev-admin ADMIN_PASSWORD='your-new-secret'
```

This runs `bootstrap_dev_admin`, which **only works when `DEBUG=True`**. It creates or updates the admin user and sets the password.

**Option B — Django command**

```bash
uv run python manage.py changepassword admin
```

Replace `admin` with your superuser username. You will be prompted twice for the new password (nothing is echoed).

**Option C — Interactive superuser**

```bash
make superuser
# or: uv run python manage.py createsuperuser
```

Use this when creating a **new** admin account from scratch.

### Production (DEBUG off)

**Do not use `make dev-admin` or `bootstrap_dev_admin`** — they refuse to run when `DEBUG=False`.

**Recommended:**

```bash
# On the server, in the app directory, with venv active:
python manage.py changepassword YOUR_ADMIN_USERNAME
```

Or create a new superuser if none exists:

```bash
python manage.py createsuperuser
```

**Django admin site (optional):** If your admin user has `is_staff=True`, you can open `/admin/`, go to **Users**, edit the account, and use **“change password”** there. The marketing panel’s **Users** page does not change passwords yet.

After changing the password, sign out of the panel and sign in again with the new password.

---

## Creating users and setting their passwords

### What the panel does today

On **Users** (`/users/`), an admin can:

1. Create a user with **username + password** (and name, email, role, team access).
2. Grant extra team access to existing users.
3. Activate / deactivate users (history is kept).

There is **no** “edit password” or “send reset link” on that page yet.

### Is it OK for the admin to choose each person’s password?

**Yes, for a small internal team**, if you treat it as a **temporary initial password** and follow basic hygiene:

| Do | Avoid |
|----|--------|
| Use a **unique** password per person | One shared password for everyone |
| Send the password **privately** (in person, secure chat, password manager share) | Posting passwords in Slack/email threads that stay forever |
| Use a **strong** random password (password manager generated) | Short or guessable passwords (`Welcome1`, team name + year) |
| Tell the user to **change it** once self-service exists | Reusing your own admin password for other users |
| **Deactivate** accounts when someone leaves | Leaving inactive logins enabled |

For **10+ users**, finance/compliance scrutiny, or remote staff, admin-chosen passwords become harder to scale and audit — move to one of the [better approaches](#better-approaches).

---

## Better approaches (what to implement next)

Ranked from smallest effort to most robust.

### 1. Admin “reset password” on the Users page *(recommended next step)*

- Admin picks a user → sets a **new temporary password**.
- Optional later: flag **“must change on first login”**.
- **Pros:** No email server; fits current workflow; passwords not in `.env`.
- **Cons:** Admin still knows or transmits the temp password once.

### 2. Self-service “Change my password” *(logged-in users)*

- Any user opens **Settings** or **Profile** → enters current password + new password twice.
- Uses Django’s built-in `PasswordChangeForm`.
- **Pros:** Users own their secrets after onboarding; admins only reset when locked out.
- **Cons:** Does not help first-time login without a reset path.

### 3. Email “Forgot password?” *(needs SMTP)*

- Login page link → user enters email → one-time reset link.
- Requires `EMAIL_*` settings and a real mail provider (SES, SendGrid, etc.).
- **Pros:** Standard UX; admin not in the loop for every lockout.
- **Cons:** Operational setup; must secure email delivery.

### 4. Enterprise SSO *(later)*

- Google Workspace, Microsoft Entra, SAML — users use company login.
- **Pros:** Central offboarding, MFA, compliance.
- **Cons:** Infra and integration work; overkill for a tiny pilot.

### Practical recommendation for this project

| Stage | Approach |
|-------|----------|
| **Now** | Admin creates users with a **random temp password**; deliver privately; document admin change via `changepassword` |
| **Next feature** | Admin **reset password** on `/users/` + **change my password** for logged-in users |
| **Production** | Email reset if users often forget passwords; never commit real passwords to git |
| **Avoid** | Putting user passwords in `.env`, Excel, or shared docs |

---

## Quick reference

| Task | Command / place |
|------|------------------|
| Local admin password | `make dev-admin` or `changepassword admin` |
| Production admin password | `python manage.py changepassword USERNAME` on server |
| Create panel user + password | `/users/` → New user |
| Who can access what | `/users/` + [`ACCESS_BY_ROLE.md`](ACCESS_BY_ROLE.md) |
| Lock someone out | `/users/` → Deactivate |
| Forgot password (today) | Admin sets a new password via shell `changepassword` or Django `/admin/` |

---

## Security reminders

- `bootstrap_dev_admin` / default `admin12345` is **for local dev only** — see [`DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md).
- Django validates password strength (length, common passwords, etc.) when passwords are set through supported forms/commands.
- Deactivating a user disables login but **keeps invoice history** linked to that account.
