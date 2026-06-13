# Deployment Guide (AWS + cheaper alternatives)

This guide explains how to deploy the **Marketing Spend Dashboard** to AWS, and lists
simpler/cheaper alternatives.

> **Important reality check.** The `AWS_Infrastructure_Research_Project.pdf` whitepaper
> describes a **FastAPI + React + PostgreSQL** learning project. This repository is a
> **Django (server-rendered templates) + SQLite** app. The PDF's *roadmap and AWS
> service choices still apply*, but the implementation details below are written for the
> stack that actually exists here. Where the PDF says "FastAPI", read "Django/gunicorn";
> where it says "React dashboard", this app already renders its own HTML.

> **Pricing note (from the PDF).** Do not trust any fixed price. AWS prices and free-tier
> rules change by Region, account age, and configuration. Verify on the official AWS
> pricing pages before creating always-on resources (EC2, RDS, ALB, NAT Gateway, ElastiCache).

---

## 0. Where this project already is on the PDF roadmap

The PDF's path is: `local -> Docker -> EC2 -> RDS -> S3 -> CloudWatch -> CI/CD -> ALB -> Terraform -> ECS -> Valkey -> SQS -> EKS`.

Already done in this repo (no AWS needed):
- Core app, models, migrations, tests, lint.
- Backend-enforced RBAC (admin / manager / editor / observer) — the PDF's #1 security rule.
- XLSX import with raw-row traceability + Excel export.
- "Excel is an import format, not the runtime database" (matches PDF §11.2).

Not done yet (needed before/at deploy):
- Production settings (`DEBUG=False`, real `ALLOWED_HOSTS`, secret from env).
- A real database (move off SQLite to PostgreSQL/RDS).
- Static files served properly (`collectstatic` + WhiteNoise or S3/CloudFront).
- Uploaded files (invoice/payment images) on durable storage (local disk is fine on one box; S3 is better).
- A WSGI server (gunicorn) behind a reverse proxy (nginx/Caddy) with HTTPS.

---

## 1. Make the app production-ready (do this regardless of host)

These changes are required for **any** real deployment.

### 1.1 Add production dependencies

```bash
uv add gunicorn "psycopg[binary]" whitenoise dj-database-url
# Optional, only if you store uploads/static on S3:
uv add django-storages boto3
```

### 1.2 Settings changes (`config/settings.py`)

- `DEBUG` already reads `DJANGO_DEBUG` — set it to `false` in production.
- `ALLOWED_HOSTS` already reads `DJANGO_ALLOWED_HOSTS` — set your domain/IP.
- `SECRET_KEY` already reads `DJANGO_SECRET_KEY` — **always set a fixed value in prod**
  (the current fallback generates a new key each boot, which would invalidate every session).
- Add WhiteNoise so the single server can serve CSS/JS without nginx static config:

```python
# In MIDDLEWARE, right after SecurityMiddleware:
"whitenoise.middleware.WhiteNoiseMiddleware",

# Near static settings:
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
```

- Switch the database to read a URL (so SQLite stays for local, Postgres for prod):

```python
import dj_database_url
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}
```

- Production security headers (only when not DEBUG):

```python
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = [
        o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
    ]
```

### 1.3 Production `.env`

```env
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<a long random string, keep it stable>
DJANGO_ALLOWED_HOSTS=dashboard.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://dashboard.example.com
DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/marketing
DJANGO_TIME_ZONE=Asia/Tehran
DJANGO_DEFAULT_CURRENCY=IRR
```

### 1.4 Build/run commands in production

```bash
uv sync --no-dev
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
uv run python manage.py seed_auth_groups
uv run python manage.py createsuperuser        # real admin; do NOT use make dev-admin in prod
uv run gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

---

## 2. Recommended AWS path (matches the PDF, simplest first)

The PDF strongly recommends **not** starting with ECS/Fargate/EKS. Start with one EC2 box.

### Phase A — single EC2 + Caddy (cheapest real AWS deploy)

Goal: one always-on Linux VM running gunicorn behind Caddy (which auto-provisions HTTPS).
Database can stay SQLite at first or be a local Postgres on the same box.

1. **AWS Budgets alert first** (PDF §9): set a monthly budget + email alert before anything.
2. Launch an EC2 instance (e.g. a small `t3.small`/`t4g.small`), Ubuntu LTS, in a default VPC.
3. Security group: allow inbound `80`, `443`, and `22` (SSH) **from your IP only**.
4. Install Python 3.13 + `uv`, clone the repo, create the production `.env`.
5. Run gunicorn as a `systemd` service (sample below).
6. Put **Caddy** in front for automatic HTTPS (sample below). Point your domain's DNS at the EC2 public IP (Route 53 or any registrar).

`systemd` unit (`/etc/systemd/system/marketing.service`):

```ini
[Unit]
Description=Marketing dashboard (gunicorn)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/marketing
EnvironmentFile=/home/ubuntu/marketing/.env
ExecStart=/home/ubuntu/.local/bin/uv run gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```

`Caddyfile`:

```text
dashboard.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

Caddy handles TLS certificates automatically, so you get HTTPS with no extra config.
This single-box setup is the cheapest legitimate AWS deployment and covers everything an
internal dashboard needs.

### Phase B — add RDS PostgreSQL (PDF milestone 3)

When you want managed backups and to stop worrying about the DB:
1. Create an RDS PostgreSQL instance (smallest dev size) in a **private** subnet.
2. Security group: allow `5432` **only** from the EC2 instance's security group.
3. Set `DATABASE_URL` to the RDS endpoint, run `migrate`, then re-import the workbook.
4. Take a snapshot before big changes. **Delete it when idle** — RDS bills while running.

### Phase C — add S3 for uploads (PDF milestone 4)

Invoice/payment-proof images and the raw XLSX uploads are the natural fit for S3 so they
survive instance replacement:
1. Create a bucket with **Block Public Access ON**.
2. Give the EC2 instance an IAM **role** (not access keys) with least-privilege bucket access.
3. Configure `django-storages` so `MEDIA` (and optionally static) live in S3.

### Phase D — CloudWatch, CI/CD, ALB, Terraform (PDF milestones 5–8)

Only once the above is stable:
- **CloudWatch**: ship gunicorn/nginx logs and add an alarm on 5xx + a budget alarm.
- **CI/CD**: GitHub Actions with **OIDC** (no long-lived AWS keys) to run tests and deploy.
- **ALB + 2 instances**: only if you need zero-downtime/redundancy (ALB has idle cost).
- **Terraform**: codify the VPC/EC2/RDS/S3 once you understand them manually.

Valkey/ElastiCache, SQS, ECS/Fargate, and EKS are explicitly **later/optional** in the PDF.
This dashboard has low traffic, so you very likely never need them.

---

## 3. Cheaper / easier alternatives (often better for an internal dashboard)

Ranked roughly from least to most ops effort. All are valid; AWS is not required.

| Option | What it is | Effort | Rough monthly cost | Best when |
|---|---|---|---|---|
| **Render / Railway / Fly.io** (PaaS) | Push the repo; the platform builds, runs gunicorn, gives HTTPS + managed Postgres | **Lowest** | Free tier → low | You want it live fast with the least DevOps |
| **AWS Lightsail** | Fixed-price AWS VPS with a predictable bill | Low | Low, flat | You want AWS but predictable pricing, not metered surprises |
| **Single EC2 + Caddy** (Phase A above) | One VM you manage | Medium | Low (one small instance) | You want the PDF's learning value + control |
| **EC2 + RDS + S3 + ALB** (Phase B–D) | Full managed AWS | High | Medium+ (several always-on services) | You need the portfolio evidence or real scale |
| **Docker on any VPS** (DigitalOcean/Hetzner) | `docker compose up` on a cheap droplet | Medium | Very low | Cost is the top priority |

### Recommendations

- **If the goal is a working internal tool quickly and cheaply:** use a PaaS
  (Render/Railway/Fly.io) with managed Postgres. You skip servers, TLS, and OS patching
  entirely, and the free/low tiers fit a small internal dashboard.
- **If the goal is the AWS/DevOps portfolio** described in the PDF: do **Phase A → B → C**
  on AWS, write an ADR per phase, and capture CloudWatch/cost screenshots. That produces
  exactly the artifacts the whitepaper asks for, without the expensive ECS/EKS detour.
- **Either way:** keep PostgreSQL as the source of truth, keep secrets in env/SSM/Secrets
  Manager, set a budget alert first, and tear down idle managed services.

---

## 4. Pre-deploy checklist

- [ ] `DEBUG=false`, fixed `SECRET_KEY`, correct `ALLOWED_HOSTS` + `CSRF_TRUSTED_ORIGINS`.
- [ ] Database is PostgreSQL (not SQLite) for anything multi-user/long-lived.
- [ ] `collectstatic` runs and static files are served (WhiteNoise or S3/CloudFront).
- [ ] Uploaded media persists across restarts (durable disk or S3).
- [ ] HTTPS enabled (Caddy/ALB/PaaS).
- [ ] A **real** admin created via `createsuperuser` (never ship `admin/admin12345`).
- [ ] Budget alert + log retention configured.
- [ ] `make check` passes (Django checks + tests + ruff) in CI before deploy.
