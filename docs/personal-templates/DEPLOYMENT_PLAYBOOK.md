# Django production deployment — usual procedure

Personal notes for **this project** and similar internal Django dashboards. Complements the tracked runbook at [`../operations/DEPLOYMENT_AWS.md`](../operations/DEPLOYMENT_AWS.md).

---

## Mental model

```text
Users → TLS terminator (Caddy / nginx / load balancer)
     → WSGI server (gunicorn)
     → Django (settings from env)
     → Database (Postgres in prod; SQLite OK for tiny single-box pilots)
     → File storage (local media/ first; S3 when you need durability)
```

Django does **not** serve production traffic with `runserver`. You always use **gunicorn** (or uwsgi) behind a reverse proxy.

---

## Standard sequence (any host)

1. **Prepare code** — tests pass locally (`make check`).
2. **Provision server** — VM, EC2, Lightsail, or PaaS web service.
3. **Install runtime** — Python 3.13 + `uv`, clone repo.
4. **Configure env** — see [`ENV.md`](ENV.md); `.env` on server, never in git.
5. **Install deps** — `make prod-install` (gunicorn, whitenoise, psycopg).
6. **Migrate DB** — `uv run python manage.py migrate`.
7. **Static files** — `uv run python manage.py collectstatic --noinput` (WhiteNoise serves them).
8. **Bootstrap auth** — `seed_auth_groups`, `createsuperuser` (not dev bootstrap password).
9. **Import data** — workbook via `make load-data` if starting from Excel.
10. **Process manager** — systemd unit for gunicorn on `127.0.0.1:8000`.
11. **Reverse proxy** — Caddy/nginx for HTTPS + optional `/media/` static.
12. **DNS** — point domain to server; verify `ALLOWED_HOSTS` + `CSRF_TRUSTED_ORIGINS`.
13. **Smoke test** — login, dashboard, upload, export, role-limited user.

---

## This project specifics

| Topic | This app |
|-------|----------|
| WSGI entry | `config.wsgi:application` |
| Prod command | `make prod-run` or gunicorn via systemd (see AWS runbook) |
| Static | WhiteNoise — no separate nginx static block required |
| Media | `media/` on disk; invoice/contract uploads |
| Sessions | DB-backed default; stable `DJANGO_SECRET_KEY` required |
| Auth | All pages login-required except login/help/fonts |
| Time zone | `Asia/Tehran` — Jalali month filters |

---

## Deploy an update (rolling)

```bash
cd /path/to/marketing
git pull
make prod-install          # if pyproject.toml / uv.lock changed
set -a; source .env; set +a
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
sudo systemctl restart marketing   # or your unit name
```

Expect **~30s downtime** on a single gunicorn box. For zero-downtime you need two instances + load balancer (usually not worth it for an internal dashboard).

---

## Common production failures

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Redirect loop | `SECURE_SSL_REDIRECT` without HTTPS | Fix proxy TLS or disable redirect |
| Logged out every click | `SESSION_COOKIE_SECURE` on HTTP | HTTPS or unset secure cookie flag |
| Logged out after restart | New random `SECRET_KEY` each boot | Set stable `DJANGO_SECRET_KEY` in `.env` |
| 400 Bad Request | Host not in `ALLOWED_HOSTS` | Add domain to env |
| CSRF failed on POST | Missing `CSRF_TRUSTED_ORIGINS` | Add `https://your-domain` |
| 502 from proxy | gunicorn not running | `systemctl status marketing` |
| Static 404 | Forgot collectstatic | Re-run collectstatic; check WhiteNoise |
| Uploads vanish | Ephemeral PaaS disk | Move media to S3 |

---

## When to add what

| Milestone | Add |
|-----------|-----|
| First internal pilot | Single EC2 + SQLite + Caddy |
| Real users + backups | RDS Postgres |
| Replace server safely | S3 for `media/` |
| Team deploys | GitHub Actions → SSH or OIDC |
| High availability | ALB + 2+ instances (rare for this product) |

---

## Related docs

- Tracked AWS runbook: [`../operations/DEPLOYMENT_AWS.md`](../operations/DEPLOYMENT_AWS.md)
- Env reference: [`ENV.md`](ENV.md)
- AWS checklist: [`AWS_CHECKLIST.md`](AWS_CHECKLIST.md)
- Containers: [`CONTAINERS.md`](CONTAINERS.md)
