# Simple Local Setup

Use this guide for a fresh local setup on macOS or Linux.

## 1. Open The Project

Open a terminal and go to the project folder:

```bash
cd /path/to/budget-dashboard-main
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

Paste only these command lines into the terminal:

```bash
make setup
make dev-admin
make load-data-dry-run
make load-data
make dev
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
