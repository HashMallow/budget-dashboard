# Simple Local Setup

Use this guide for a fresh local setup on macOS or Linux.

> Already set up before and just want the newest version? Jump to
> [Get The Latest Changes (git pull)](#get-the-latest-changes-git-pull).

## 1. Open The Project

Open a terminal and go to the project folder:

```bash
cd /path/to/budget-dashboard-main
```

If you do not have the project yet, clone it first:

```bash
git clone <your-repo-url> budget-dashboard
cd budget-dashboard
```

## 2. Install Prerequisites

You need `make` and `uv`.

On macOS, install Apple command line tools if needed:

```bash
xcode-select --install
```

Install `uv` with Homebrew:

```bash
brew install uv
```

If you do not use Homebrew, install `uv` with:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

If the installer finishes but `uv` is still not found, run:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Verify:

```bash
uv --version
make --version
```

## 3. Add The Excel Workbook

Put the `.xlsx` workbook in the project folder.

Example:

```text
marketing_spend_workbook.xlsx
```

## 4. Run The App

Paste only these command lines into the terminal, in this order:

```bash
make setup
make dev-admin
make load-data-dry-run
make load-data
make dev
```

What each step does (run them in this exact order):

```text
make setup              Install dependencies, create the database, run migrations, seed roles.
make dev-admin          Create the local admin login (admin / admin12345).
make load-data-dry-run  Preview the Excel import. Nothing is written to the database yet.
make load-data          Import the workbook into the database (invoices, budgets, lookups).
make dev                Start the local server (with auto-reload).
```

Then open:

```text
http://127.0.0.1:8000/login/
```

Login:

```text
username: admin
password: admin12345
```

Main panel routes (after login):

```text
/                 Finance overview dashboard
/help/            In-app guide
/teams/           Team dashboards
/invoices/        Invoices (business line filter)
/vendors/         Vendor report
/campaigns/       Campaign report
/budgets/         Budget
/contracts/       Contracts
/reference/       Reference data (admin: vendors, categories, sub-teams, campaigns, requesters)
/imports/         Excel import (admin)
/users/           Users and access (admin)
```

Sidebar is grouped: **Overview** · **Spend & teams** · **Reports** · **Administration** · **Help** (bottom).

Run `make help` anytime for the full command list.

The order matters: `make setup` must create the database before `make dev-admin` can add
the admin user, and the data must be imported with `make load-data` before it shows up in the
dashboard. If you run `make dev` first, you will see an empty app or a login error because the
database and admin user do not exist yet.

## Get The Latest Changes (git pull)

Use this when you already set the project up once and just want the newest code.

Git only carries **code**, not your data. The Excel workbook, the database (`db.sqlite3`), uploads,
and voice files are intentionally kept out of git, so a `git pull` never changes your local data.

```bash
git pull
make setup
make dev
```

What each step does after a pull:

```text
git pull     Download the latest code changes from GitHub.
make setup   Install any new dependencies and apply any new database migrations.
make dev     Start the server again.
```

Notes:

- You do **not** need `make dev-admin` again — your admin user is already in the local database.
- You only need `make load-data` again if you received a **new Excel workbook** or want to
  re-import. Re-importing updates existing rows instead of duplicating them.
- If `git pull` reports a conflict on a data file (for example the `.xlsx` or `db.sqlite3`), it
  usually means that file was committed by mistake earlier. Those files are now ignored, so keep
  your local copy and continue.

## If There Is More Than One Excel File

Use the exact workbook path:

```bash
make setup
make dev-admin
make load-data-dry-run FILE=./marketing_spend_workbook.xlsx
make load-data FILE=./marketing_spend_workbook.xlsx
make dev
```

## Optional Check

Run:

```bash
make check
```

If only the LibreOffice conversion test fails because of a local LibreOffice/Snap/AppArmor issue, the app can still run. Use this app-level check instead:

```bash
UV_CONFIG_FILE=uv.toml UV_CACHE_DIR=.uv-cache uv run pytest -q -k 'not workbook_converts_with_libreoffice'
UV_CONFIG_FILE=uv.toml UV_CACHE_DIR=.uv-cache uv run ruff check .
```

## Common Errors

`uv: command not found`

Install `uv`, restart the terminal, or run:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

`zsh: command not found: #`

You pasted explanation comments into the terminal. Paste only command lines from the code blocks.

`Multiple .xlsx workbooks found`

Run the import with `FILE=...` as shown above.

`That port is already in use`

Run the server on another port:

```bash
make dev PORT=8001
```

Then open:

```text
http://127.0.0.1:8001/login/
```
