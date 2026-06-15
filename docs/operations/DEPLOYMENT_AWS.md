# Deploying this dashboard on AWS

Copy-paste runbook for the **Marketing Finance Hub** (Django 5 + gunicorn + WhiteNoise).
This document covers the **preferred path only**: one **EC2** instance with **Caddy** and **gunicorn**.

For a gentler, step-by-step Console + CLI walkthrough with checkpoints and diagrams, use the
companion PDF:

**[`docs/reference/AWS_EC2_Deployment_Path_Field_Guide.pdf`](reference/AWS_EC2_Deployment_Path_Field_Guide.pdf)**

> **Pricing.** AWS prices and free tiers change by region and account. Set an **AWS Budget** alert
> before creating always-on resources (EC2, RDS, Elastic IP). Verify current pricing on the AWS site.

---

## What you are deploying

```text
Browser → DNS → EC2 (ports 80/443) → Caddy (HTTPS) → gunicorn 127.0.0.1:8000 → Django
                                                              ├─ SQLite or Postgres (DATABASE_URL)
                                                              └─ media/ on disk (S3 later)
```

| Piece | This project |
|-------|----------------|
| App | Django 5, WSGI `config.wsgi:application` |
| Process | `gunicorn` via `make prod-run` / systemd |
| Python | 3.13 via **`uv`** (`uv.lock`, `.python-version`) |
| Static files | **WhiteNoise** (no separate CDN required) |
| Uploads | `media/` on the EC2 disk first; move to **S3** when needed |
| Dev DB | SQLite (`db.sqlite3`) |
| Prod DB | Postgres via `DATABASE_URL` (optional at first; **RDS** when ready) |
| Config | Environment variables (see below); prod mode when `DJANGO_DEBUG=false` |
| Initial data | Workbook import: `make load-data` (see `docs/discovery/README.md` for mapping vs local override) |

You do **not** need ECS, EKS, CloudFront, or a separate static host for v1.

---

## Recommended upgrade order

Add managed AWS services only after the single-box deploy works:

```text
1. EC2 + Caddy + gunicorn          ← this guide
2. RDS PostgreSQL                  ← when you need managed backups / concurrent writers
3. S3 for uploads                  ← when media must survive instance replacement
4. CloudWatch Logs + CI/CD         ← when SSH/journalctl is not enough
5. ALB / Terraform                 ← only for redundancy or repeatability at scale
```

---

## 0. Guardrails (do this first)

1. **AWS Budget** — Billing → Budgets → monthly alert with a low threshold.
2. **Tags** — use on every resource: `Project=marketing-dashboard`, `Environment=prod`, `Owner=<you>`.
3. **One region** — pick it once (e.g. `eu-central-1`, `me-south-1`) and stay there.
4. **CLI identity check:**

```bash
aws configure --profile dashboard
aws sts get-caller-identity --profile dashboard
```

5. **Local sanity check** (on your laptop, before touching AWS):

```bash
make check
make prod-install
uv run python manage.py check --deploy
```

---

## 1. Network: security group

Create **before** launching EC2.

| Inbound | Source | Why |
|---------|--------|-----|
| HTTP 80 | `0.0.0.0/0`, `::/0` | Caddy + Let's Encrypt |
| HTTPS 443 | `0.0.0.0/0`, `::/0` | Users |
| SSH 22 | **your IP only** | Admin access |

Do **not** open PostgreSQL (5432) to the internet.

```bash
aws ec2 describe-security-groups --profile dashboard \
  --query "SecurityGroups[*].{Name:GroupName,Id:GroupId}" --output table
```

---

## 2. Launch EC2

- **AMI:** Ubuntu LTS (commands below assume `ubuntu` user).
- **Type:** `t3.small` or `t4g.small` (enough for a small internal dashboard).
- **Network:** default VPC is fine for v1.
- **Storage:** default EBS volume (holds app, SQLite, `media/`).
- **Name / tags:** e.g. `marketing-dashboard-prod-web`.

```bash
aws ec2 describe-instances --profile dashboard \
  --filters "Name=tag:Project,Values=marketing-dashboard" \
  --query "Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress]" \
  --output table
```

Connect via **EC2 Instance Connect** (console) or SSH:

```bash
ssh -i ~/.ssh/YOUR_KEY.pem ubuntu@YOUR_PUBLIC_IP
```

---

## 3. Install runtime on the server

```bash
sudo apt update && sudo apt install -y git curl ca-certificates
curl -LsSf https://astral.sh/uv/install.sh | sh
exec $SHELL

git clone <your-repo-url> /home/ubuntu/marketing
cd /home/ubuntu/marketing
```

Create production `.env` (never commit this file):

```env
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<long stable random string — set once>
DJANGO_ALLOWED_HOSTS=dashboard.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://dashboard.example.com
DJANGO_TIME_ZONE=Asia/Tehran
DJANGO_DEFAULT_CURRENCY=IRR
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_LOG_LEVEL=INFO

# Omit DATABASE_URL to use SQLite on the box; set for Postgres/RDS:
# DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/marketing?sslmode=require
```

```bash
make prod-install
```

When `DJANGO_DEBUG=false`, Django enables secure cookies, proxy SSL header trust (for Caddy), and
WhiteNoise compressed static storage.

---

## 4. Initialize the app

```bash
set -a; source .env; set +a

uv run python manage.py migrate
uv run python manage.py seed_auth_groups
uv run python manage.py collectstatic --noinput
uv run python manage.py createsuperuser    # real admin — never use admin/admin12345

# Copy the workbook to the server, then (optional local mapping override — see docs/discovery/README.md):
make load-data-dry-run FILE="./path/to/your_workbook.xlsx"
make load-data         FILE="./path/to/your_workbook.xlsx"
```

The importer is idempotent (`invoice_number` + vendor). After import, the **database** is the source
of truth; Excel is only an import format.

---

## 5. gunicorn via systemd

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
sudo systemctl status marketing
journalctl -u marketing -n 50 --no-pager
```

gunicorn must bind **127.0.0.1:8000** only — not `0.0.0.0`.

---

## 6. Caddy (HTTPS + reverse proxy)

```bash
sudo apt install -y caddy
```

`/etc/caddy/Caddyfile`:

```text
dashboard.example.com {
    encode zstd gzip

    handle_path /media/* {
        root * /home/ubuntu/marketing/media
        file_server
    }

    reverse_proxy 127.0.0.1:8000
}
```

```bash
sudo systemctl reload caddy
sudo systemctl status caddy
```

Caddy obtains Let's Encrypt certificates and sets `X-Forwarded-Proto`, which Django trusts via
`SECURE_PROXY_SSL_HEADER`.

---

## 7. DNS and verify

1. Create an **A record**: `dashboard.example.com` → EC2 public IP (Route 53 or your registrar).
2. Wait for DNS, then:

```bash
dig +short dashboard.example.com
curl -I https://dashboard.example.com
```

3. In the browser: login, dashboard charts, an invoice with an upload, Excel/PDF export.

**Troubleshooting order:** DNS → security group → Caddy → `systemctl status marketing` → Django logs
→ database/media path.

```bash
# on server
sudo systemctl status marketing caddy
journalctl -u marketing -n 100 --no-pager
journalctl -u caddy -n 100 --no-pager
ss -tulpn | grep -E ':(80|443|8000)'
```

---

## 8. Deploy updates

Manual deploy shape (automate with GitHub Actions **after** this works once):

```bash
cd /home/ubuntu/marketing
git pull
make prod-install                    # only if dependencies changed
set -a; source .env; set +a
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
sudo systemctl restart marketing
```

Run `make check` locally (or in CI) before every deploy.

---

## 9. Managed upgrades (after EC2 is stable)

### RDS PostgreSQL

Use when you need managed backups, PITR, or separation from the web server.

1. Create smallest suitable RDS Postgres in the **same VPC** (private preferred).
2. Security group: allow **5432 only from the EC2 security group**.
3. Set `DATABASE_URL`, then `migrate` and re-import the workbook if needed.

```bash
aws rds describe-db-instances --profile dashboard \
  --query "DBInstances[*].{DB:DBInstanceIdentifier,Endpoint:Endpoint.Address}" --output table
```

### S3 for uploads

Use when uploads must survive instance replacement or you run multiple app servers.

1. Private bucket (Block Public Access **on**).
2. **IAM role** on the EC2 instance (not access keys in `.env`).
3. Add `django-storages` + `boto3`; point default file storage to S3; remove Caddy `file_server` for `/media/`.

### CloudWatch + CI/CD

- Ship gunicorn/Caddy logs; **set log retention**.
- GitHub Actions with **OIDC** (no long-lived AWS keys): run `make check`, then SSH deploy the §8 steps.

Skip ElastiCache, SQS workers, ECS, and EKS unless traffic or import volume forces them.

---

## 10. Pre-deploy checklist

- [ ] AWS Budget alert configured; resources tagged.
- [ ] `DJANGO_DEBUG=false`, stable `DJANGO_SECRET_KEY`, correct `ALLOWED_HOSTS` + `CSRF_TRUSTED_ORIGINS`.
- [ ] `make prod-install` and `collectstatic` completed; `/static/` loads over HTTPS.
- [ ] Real superuser via `createsuperuser` (not dev bootstrap password).
- [ ] Workbook imported; spot-check totals against source.
- [ ] HTTPS works with no redirect loop; media uploads persist on disk (or S3).
- [ ] `make check` passes before deploy.
- [ ] You know how to stop/delete idle EC2/RDS to avoid surprise bills.

---

## Appendix — alternative deployment paths

Use these only if AWS EC2 is **not** the right fit. The **preferred** path for this project remains
**EC2 + Caddy + gunicorn** (§1–8 above and the [field guide PDF](reference/AWS_EC2_Deployment_Path_Field_Guide.pdf)).

### PaaS (fastest time-to-live)

**Render / Railway / Fly.io** — no server patching, platform handles TLS and often Postgres.

1. Connect the GitHub repo as a web service.
2. **Build:** `uv sync --extra prod && uv run python manage.py collectstatic --noinput`
3. **Start:** `uv run gunicorn config.wsgi:application`
4. Add managed Postgres; platform injects `DATABASE_URL`.
5. Set the same `.env` keys as §3 (`DJANGO_DEBUG=false`, secret key, allowed hosts, CSRF origins).
6. Shell: `migrate`, `seed_auth_groups`, `createsuperuser`, `make load-data`.
7. **Caveat:** ephemeral disks → plan **S3** for invoice/payment uploads on most PaaS tiers.

### AWS Lightsail

Fixed monthly price, simpler console than raw EC2. Same server steps as §3–8 (Ubuntu + uv +
gunicorn + Caddy). Good when you want AWS billing predictability without VPC complexity.

### Docker on a cheap VPS (Hetzner / DigitalOcean)

Lowest cost if AWS is not required. Run the same gunicorn + Caddy stack in containers or directly on
the VM; use managed Postgres from the provider or RDS over the public internet (not ideal).

### What we deliberately skip for v1

| Approach | Why skip for now |
|----------|------------------|
| ECS / Fargate / EKS | Overkill for one internal dashboard |
| CloudFront + S3 static site | WhiteNoise serves static from the app |
| ALB + multiple EC2 | Add only for zero-downtime / scale |
| Async import workers (SQS) | Imports are synchronous; fine at current volume |

For deeper AWS learning (Console habits, component cards, lab links), work through the
**[EC2 Deployment Path Field Guide PDF](reference/AWS_EC2_Deployment_Path_Field_Guide.pdf)** step
by step alongside this runbook.
