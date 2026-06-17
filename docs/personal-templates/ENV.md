# Environment variables — Marketing Finance Hub

Copy to `.env` on your laptop or on the server. Never commit `.env`.

Generate a production secret once:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Local development (typical)

```env
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_TIME_ZONE=Asia/Tehran
DJANGO_DEFAULT_CURRENCY=IRR

# Optional — if empty, a stable key is stored in .django_secret_key (gitignored)
# DJANGO_SECRET_KEY=
```

Leave `DATABASE_URL` unset → SQLite at `db.sqlite3`.

---

## Production (minimum — EC2 or PaaS)

```env
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<paste long random string — set once, never rotate casually>
DJANGO_ALLOWED_HOSTS=dashboard.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://dashboard.example.com
DJANGO_TIME_ZONE=Asia/Tehran
DJANGO_DEFAULT_CURRENCY=IRR
DJANGO_LOG_LEVEL=INFO
```

With **HTTPS** (Caddy / ALB / PaaS TLS), also set:

```env
DJANGO_SESSION_COOKIE_SECURE=true
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_SECURE_HSTS_SECONDS=31536000
```

> **Session tip:** If users get logged out on every click over **plain HTTP**, either enable HTTPS or leave `DJANGO_SESSION_COOKIE_SECURE` unset/false. Secure cookies are not sent over HTTP.

---

## Production (recommended — Postgres on RDS)

Add when you move off SQLite:

```env
DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/marketing?sslmode=require
```

---

## Full reference

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `DJANGO_DEBUG` | prod: `false` | `true` | Enables debug pages; must be `false` in production |
| `DJANGO_SECRET_KEY` | **prod: yes** | auto `.django_secret_key` in dev | Signs sessions; changing it logs everyone out |
| `DJANGO_ALLOWED_HOSTS` | prod: yes | `127.0.0.1,localhost` | Comma-separated hostnames (no scheme) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | prod HTTPS: yes | empty | Comma-separated origins **with** `https://` |
| `DATABASE_URL` | optional | SQLite file | Postgres connection string when set |
| `DJANGO_TIME_ZONE` | optional | `Asia/Tehran` | Invoice dates, Jalali reporting |
| `DJANGO_DEFAULT_CURRENCY` | optional | `IRR` | Display default |
| `DJANGO_LOG_LEVEL` | optional | `INFO` | `DEBUG`, `WARNING`, `ERROR` |
| `DJANGO_SESSION_COOKIE_SECURE` | HTTPS only | auto if CSRF origins set | Set `true` when site is HTTPS-only |
| `DJANGO_SECURE_SSL_REDIRECT` | optional | `true` when `DEBUG=false` | Redirect HTTP→HTTPS |
| `DJANGO_SECURE_HSTS_SECONDS` | optional | `0` | e.g. `31536000` after HTTPS verified |

---

## Not in `.env` (by design)

- **User passwords** → Django admin / `/users/` panel
- **Workbook path** → upload via `make load-data FILE=...`
- **Column mapping override** → gitignored `docs/discovery/column_mapping.local.yml`

---

## Verify before go-live

```bash
set -a; source .env; set +a
uv run python manage.py check --deploy
make check
```
