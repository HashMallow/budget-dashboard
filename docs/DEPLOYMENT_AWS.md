# Deploying *this* dashboard

A concrete, copy-pasteable runbook for putting **this** project — the Marketing Spend Dashboard
(Django + gunicorn, server-rendered templates) — online. It is written around what is already in
this repo, not a generic tutorial.

The AWS field guide in the repo
([`../AWS_Infrastructure_Field_Guide_Gentle_Steps.md`](../AWS_Infrastructure_Field_Guide_Gentle_Steps.md))
is used only as **background** (cost discipline, CLI-first habits, the "add managed services later"
philosophy). Where its assumptions differ from this app, see
[§9 — How this maps to the AWS field guide](#9-how-this-maps-to-the-aws-field-guide).

> **Pricing note.** Don't trust any fixed price below. AWS pricing and free-tier rules change by
> Region, account age, and configuration. Check the official AWS pricing pages before creating
> **always-on** resources (EC2, RDS, ALB, NAT Gateway, ElastiCache).

---

## 1. What you're actually deploying

These are the deployment-relevant facts about this codebase (don't assume the generic Django defaults):

| Thing | This project |
|---|---|
| Web app | Django 5, WSGI entrypoint `config.wsgi:application` |
| App server | `gunicorn` (in the `prod` extra; run via `make prod-run`) |
| Python | 3.13, managed by **`uv`** (see `.python-version`, `uv.lock`) |
| Static files | **WhiteNoise** — gunicorn serves them itself; no separate static server/CDN needed |
| Uploaded media | invoice images + payment proofs + raw XLSX, on disk under `media/` (move to S3 later, §6) |
| DB (dev) | SQLite (`db.sqlite3`) |
| DB (prod) | any Postgres via `DATABASE_URL` (psycopg3 is in the `prod` extra) |
| Initial data | imported from the workbook via management commands; `load-data` imports invoice/budget facts and seeds Data-sheet lookups |
| Config | all via env vars (see §3); `config/settings.py` flips to "prod mode" when `DJANGO_DEBUG=false` |
| Locale defaults | `TIME_ZONE=Asia/Tehran`, `DEFAULT_CURRENCY=IRR` (both env-overridable) |

**Implication:** because WhiteNoise handles static files and the app is a single long-running WSGI
process, the simplest correct deploy is **one small Linux box running gunicorn behind a reverse
proxy that terminates HTTPS**. You do *not* need ECS/EKS/CloudFront/an S3 static site to go live.

---

## 2. Pick a path

| Option | Effort | Rough cost | Choose when |
|---|---|---|---|
| **PaaS** (Render / Railway / Fly.io) | Lowest | Free → low | You just want it live fast; platform gives HTTPS + managed Postgres |
| **AWS — single EC2 + Caddy** (this guide, §4) | Medium | One small instance | You want AWS specifically and full control / learning value |
| **AWS Lightsail** | Low | Flat, predictable | You want AWS but a fixed monthly bill |
| **Docker on a cheap VPS** (Hetzner/DigitalOcean) | Medium | Very low | Cost is the top priority |

**Chosen path for this project:** use the AWS learning path:

```text
1. EC2 + Caddy + Gunicorn
2. Add RDS PostgreSQL
3. Add S3 for uploads/media
4. Add CloudWatch + CI/CD
5. Add ALB / multiple instances / Terraform only if scale or reliability requires it
```

This guide walks the **single EC2 + Caddy** path in full because it is the most instructive AWS
option and maps cleanly onto how the app actually runs. §6 lists the managed-AWS upgrades
(RDS, S3, CloudWatch, CI/CD, ALB) in the order we want to add them. §8 covers the PaaS shortcut
only as a fallback.

For this project, continue with §4 first, then add §6A and §6B after the EC2 version is stable.

---

## 3. Production environment variables

`config/settings.py` already reads all of these. Create a production `.env` (this exact set is
what the app consumes — anything else is ignored):

```env
# Core
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<a long, STABLE random string>   # set once; never regenerate per boot in prod
DJANGO_ALLOWED_HOSTS=dashboard.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://dashboard.example.com

# Database (omit entirely to keep SQLite; set it to use Postgres/RDS)
DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/marketing

# Locale
DJANGO_TIME_ZONE=Asia/Tehran
DJANGO_DEFAULT_CURRENCY=IRR

# HTTPS hardening (active only because DEBUG=false)
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_SECURE_HSTS_SECONDS=31536000     # enable HSTS once HTTPS is confirmed working
DJANGO_LOG_LEVEL=INFO
```

What flips on automatically when `DJANGO_DEBUG=false`:
- `SECURE_SSL_REDIRECT`, secure session/CSRF cookies, and `SECURE_PROXY_SSL_HEADER`
  (so a TLS-terminating proxy like Caddy doesn't cause a redirect loop), plus optional HSTS.
- WhiteNoise compressed/hashed static storage (only if the `prod` extra is installed).

---

## 4. Walkthrough: single EC2 + Caddy

A single always-on Linux VM running gunicorn, with Caddy in front for automatic HTTPS.

### 4.0 Before anything — guardrails (AWS field guide: set guardrails first)
- Set an **AWS Budget alert** in Billing so a mistake can't run up a surprise bill.
- Decide on tags and apply them to every resource: `Project=marketing-dashboard`, `Environment=prod`, `Owner=alireza`.
- Confirm which account/region you're in before creating anything:

```bash
aws configure --profile dashboard          # keys, region (e.g. eu-central-1 / me-central-1), output json
aws sts get-caller-identity --profile dashboard
```

### 4.1 Launch the instance
- EC2 → Ubuntu LTS, `t3.small` or `t4g.small` (1–2 GB RAM is plenty for low internal traffic), default VPC.
- Tag it as above.
- **Security group:** inbound `80` and `443` from anywhere; `22` (SSH) **from your IP only**.

```bash
aws ec2 describe-instances \
  --filters 'Name=tag:Project,Values=marketing-dashboard' \
  --query 'Reservations[*].Instances[*].{Id:InstanceId,State:State.Name,PublicIp:PublicIpAddress}' \
  --output table
```

### 4.2 Install runtime + the app
SSH in, then:

```bash
sudo apt update && sudo apt install -y git curl
curl -LsSf https://astral.sh/uv/install.sh | sh        # installs uv (+ manages Python 3.13)
exec $SHELL                                             # reload PATH so `uv` is found

git clone <your-repo-url> /home/ubuntu/marketing
cd /home/ubuntu/marketing

# Create the production env file from §3
nano .env                                               # paste + edit the values

make prod-install                                       # uv sync --extra prod (gunicorn, psycopg, whitenoise, dj-database-url)
```

### 4.3 Initialize the database + load data

```bash
set -a; source .env; set +a                             # export the env for these one-off commands

uv run python manage.py migrate
uv run python manage.py seed_auth_groups                # creates the RBAC groups
uv run python manage.py collectstatic --noinput         # = make collectstatic
uv run python manage.py createsuperuser                 # REAL admin — never ship admin/admin12345

# Load the initial spend data from the workbook (preview first)
make load-data-dry-run FILE="marketing_spend_workbook.xlsx"
make load-data         FILE="marketing_spend_workbook.xlsx"
```

> The importer is idempotent on `invoice_number + vendor`, so re-running it updates rather than
> duplicates. The reference seed upserts vendors/categories/sub-teams/requesters by normalized name.
> Excel is an import format only — after this, the database is the source of truth.
>
> On import the loader also: (a) **merges workbook team spelling variants** into one canonical team
> (e.g. `Operation & Analysis` → `Ops & Analytics`, `Brand (PR & Social & CSR)` → `Brand`), and
> (b) treats **Referral** and **SMS** as **cost buckets, not teams** — Referral rolls into Growth and
> SMS into Retention while still shown separately. So a fresh prod import yields the canonical team
> list automatically; no manual cleanup needed.

### 4.4 Run gunicorn as a service
`/etc/systemd/system/marketing.service`:

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

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now marketing
sudo systemctl status marketing            # confirm it's running
```

### 4.5 HTTPS + media with Caddy
Install Caddy (`sudo apt install caddy`), then `/etc/caddy/Caddyfile`:

```text
dashboard.example.com {
    encode zstd gzip

    # Serve uploaded invoice/payment images straight from disk (MEDIA_ROOT)
    handle_path /media/* {
        root * /home/ubuntu/marketing/media
        file_server
    }

    # Everything else (incl. WhiteNoise-served /static/) goes to gunicorn
    reverse_proxy 127.0.0.1:8000
}
```

```bash
sudo systemctl reload caddy
```

Caddy automatically obtains a Let's Encrypt cert and forwards `X-Forwarded-Proto`, which Django
trusts via `SECURE_PROXY_SSL_HEADER` — so the `SECURE_SSL_REDIRECT` setting won't loop.

### 4.6 DNS + verify
- Point an `A` record for `dashboard.example.com` at the instance's public IP (Route 53 or any registrar).
- Browse to `https://dashboard.example.com`, log in as the superuser, confirm the dashboard, charts,
  an invoice with an uploaded image, and an Excel export all work.

### 4.7 Deploying updates later

Manual deployment workflow for the first server:

```bash
cd /home/ubuntu/marketing
make check                            # optional on the server; mandatory locally/CI before deploy
git pull
make prod-install                     # only if dependencies changed
set -a; source .env; set +a
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
sudo systemctl restart marketing
```

CI/CD later should automate the same shape:

```text
push to Git
    |
    v
run make check
    |
    v
deploy only if checks pass
    |
    v
pull code, install deps, migrate, collectstatic, restart
```

> **Cost hygiene:** stop the instance when it's idle for long periods; watch EBS volume and public
> IPv4 charges. Snapshot before risky changes.

---

## 5. SQLite vs. Postgres on this box

For a single low-traffic internal box, **SQLite on the instance can be enough** (leave `DATABASE_URL`
unset). Move to Postgres when you want concurrent writers, backups/PITR, or you outgrow one box.
Two options:
- **Local Postgres** on the same EC2 instance (`apt install postgresql`), set `DATABASE_URL=postgres://…@127.0.0.1:5432/marketing`.
- **Managed RDS** — §6.

Either way, after pointing `DATABASE_URL` at Postgres: `migrate`, then re-run the workbook import.

---

## 6. Managed-AWS upgrades (add only when needed)

### 6A. RDS PostgreSQL — second step after EC2 works
Use when you want managed backups, failover, or to separate DB from the web box.
1. Create the smallest dev-size RDS PostgreSQL in a **private** subnet; tag it.
2. Security group: allow `5432` **only** from the EC2 instance's security group.
3. Set `DATABASE_URL=postgres://USER:PASSWORD@<rds-endpoint>:5432/marketing?sslmode=require`,
   then `migrate` and re-import.
4. Snapshot before big changes; **stop/delete when idle** — RDS bills while running.

```bash
aws rds describe-db-instances \
  --query 'DBInstances[*].{DB:DBInstanceIdentifier,Status:DBInstanceStatus,Endpoint:Endpoint.Address}' \
  --output table
```

### 6B. S3 for uploaded media — third step after RDS works
Use when uploads must survive instance replacement, or when you run more than one web box.
1. Create a bucket with **Block Public Access ON**; tag it.
2. Give the EC2 instance an IAM **role** (not access keys) with least-privilege access to that bucket.
3. Add `django-storages` + `boto3`, set the default file storage to S3, and serve `/media/` from
   there instead of the Caddy `file_server` block.

```bash
aws s3api head-object --bucket YOUR-BUCKET --key imports/sample.xlsx
```

### 6C. Operations layer — after EC2 + RDS + S3
- **CloudWatch:** ship gunicorn/Caddy logs; alarm on 5xx; **set log retention** (otherwise it bills forever).
- **CI/CD:** GitHub Actions with **OIDC** (no long-lived AWS keys) running `make check` then deploying over SSH.
- **ALB + 2 instances:** only for zero-downtime/redundancy (the ALB has a standing hourly cost).
- **Terraform:** codify VPC/EC2/RDS/S3 once the manual version is stable.

ElastiCache/Valkey, SQS, ECS/Fargate, and EKS are **not needed** for this app's traffic. Skip them.

---

## 7. Background jobs (only if imports get slow)

Today the XLSX import runs **synchronously** inside the Django request, which is fine at the current
volume. Only if imports grow large enough to time out a request (or you want progress/retries) should
you move imports to a queue: store the upload in S3, create an import row (`status=queued`), send an
SQS message, and have a small worker process it idempotently with a DLQ. The AWS field guide builds
this as a Go service; a Django management command or a tiny Python consumer would be the natural fit
here. This is
explicitly a *future* concern, not a launch requirement.

---

## 8. PaaS shortcut (fastest to live)

If you don't specifically need AWS, a PaaS removes servers, TLS, and OS patching:
1. Push the repo to GitHub.
2. On Render/Railway/Fly.io: create a **Web Service** from the repo.
   - Build: install `uv`, then `uv sync --extra prod` and `uv run python manage.py collectstatic --noinput`.
   - Start: `uv run gunicorn config.wsgi:application`.
   - Add a **managed Postgres** add-on; the platform injects `DATABASE_URL` automatically.
   - Set the §3 env vars (`DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`=the platform domain, `DJANGO_CSRF_TRUSTED_ORIGINS`).
3. Run `migrate` + `seed_auth_groups` + `createsuperuser` from the platform's shell, then import the workbook.
4. Free/low tiers fit a small internal dashboard. Note: ephemeral disks mean **uploaded media needs
   S3** (§6B) on most PaaS plans.

---

## 9. How this maps to the AWS field guide

The field guide describes generic learning projects built around **FastAPI + a Go SQS worker + React +
PostgreSQL**. This repo is **Django (server-rendered) + WhiteNoise + SQLite-for-dev**. The guide's
*roadmap, CLI-first discipline, tagging/budget rules, and "managed services later" philosophy apply
directly*; only the runtime specifics differ:

| AWS field guide | This project |
|---|---|
| FastAPI app | Django + gunicorn (`config.wsgi`) |
| React dashboard | Django templates (a React front-end is a separate, later project) |
| Static site on S3/CloudFront | WhiteNoise serves static from the app — none needed |
| Go SQS worker | Not needed; imports are synchronous (see §7) |
| Alembic migrations | Django migrations (`manage.py migrate`) |
| SQLAlchemy models | Django ORM models |

The guide's recommended progression — `local → EC2 → RDS → S3 → CloudWatch → CI/CD → ALB → Terraform`,
adding each piece only when it earns its keep — is exactly the order of §4 → §6 here.

---

## 10. Pre-deploy checklist

- [ ] `DJANGO_DEBUG=false`, fixed `DJANGO_SECRET_KEY`, correct `DJANGO_ALLOWED_HOSTS` + `DJANGO_CSRF_TRUSTED_ORIGINS`.
- [ ] `make prod-install` then `collectstatic` run; `/static/` loads over HTTPS.
- [ ] DB chosen: SQLite-on-box for tiny use, or `DATABASE_URL` → Postgres/RDS for multi-user.
- [ ] Workbook imported (`import_marketing_excel`); spot-check totals against the source.
- [ ] Uploaded media persists across restarts (Caddy `file_server` on durable disk, or S3).
- [ ] HTTPS works (Caddy/ALB/PaaS) with no redirect loop.
- [ ] A **real** admin created via `createsuperuser` (never ship `admin/admin12345`).
- [ ] AWS Budget alert set; CloudWatch log retention configured if logs are shipped.
- [ ] Every AWS resource tagged `Project=marketing-dashboard`.
- [ ] `make check` (Django checks + tests + ruff) passes before deploying.
- [ ] A short note lists idle resources to stop/delete after labs.
