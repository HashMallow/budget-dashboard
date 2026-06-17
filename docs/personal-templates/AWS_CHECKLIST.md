# AWS deployment checklist (personal)

Fill in the bracketed fields. Keep this file only under `docs/personal/` (gitignored).

Tracked commands: [`../operations/DEPLOYMENT_AWS.md`](../operations/DEPLOYMENT_AWS.md)

---

## Account & guardrails

- [ ] AWS profile: `[dashboard / other: ________]`
- [ ] Region: `[eu-central-1 / me-south-1 / ________]`
- [ ] Budget alert: `$[___]` / month
- [ ] Tags: `Project=marketing-dashboard`, `Environment=prod`, `Owner=[you]`

```bash
aws sts get-caller-identity --profile [PROFILE]
```

---

## Resources (fill after creation)

| Resource | ID / name | Notes |
|----------|-----------|-------|
| EC2 instance | `i-________` | `[t3.small / t4g.small]` |
| Public IP / Elastic IP | `[___]` | |
| Security group | `sg-________` | 22 from my IP; 80/443 public |
| Domain | `[dashboard.example.com]` | |
| RDS (optional) | `[endpoint]` | Postgres 5432 from EC2 SG only |
| S3 bucket (optional) | `[bucket-name]` | media uploads later |

---

## Server paths

| Item | Path |
|------|------|
| App root | `/home/ubuntu/marketing` |
| `.env` | `/home/ubuntu/marketing/.env` |
| Media | `/home/ubuntu/marketing/media/` |
| systemd unit | `/etc/systemd/system/marketing.service` |
| Caddyfile | `/etc/caddy/Caddyfile` |

---

## Production `.env` (copy to server)

See [`ENV.md`](ENV.md). Minimum:

```env
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=[generated once — save in password manager]
DJANGO_ALLOWED_HOSTS=[dashboard.example.com]
DJANGO_CSRF_TRUSTED_ORIGINS=https://[dashboard.example.com]
DJANGO_SESSION_COOKIE_SECURE=true
DJANGO_TIME_ZONE=Asia/Tehran
DJANGO_DEFAULT_CURRENCY=IRR
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_LOG_LEVEL=INFO
# DATABASE_URL=postgres://...
```

---

## First deploy commands (on server)

```bash
git clone [REPO_URL] /home/ubuntu/marketing
cd /home/ubuntu/marketing
# create .env from template above
make prod-install
set -a; source .env; set +a
uv run python manage.py migrate
uv run python manage.py seed_auth_groups
uv run python manage.py collectstatic --noinput
uv run python manage.py createsuperuser
make load-data-dry-run FILE="./path/to/workbook.xlsx"
make load-data FILE="./path/to/workbook.xlsx"
sudo systemctl enable --now marketing
sudo systemctl reload caddy
```

---

## Verify

- [ ] `https://[domain]/login/` loads
- [ ] Login persists across Dashboard → Budget → Invoices
- [ ] FA login shows year as `۲۰۲۶`
- [ ] Upload invoice attachment
- [ ] Export PDF / Excel
- [ ] Editor user sees only assigned teams

```bash
curl -I https://[domain]/
journalctl -u marketing -n 50 --no-pager
```

---

## Update deploy (repeat)

```bash
cd /home/ubuntu/marketing && git pull
make prod-install
set -a; source .env; set +a
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
sudo systemctl restart marketing
```

---

## Diary (optional)

| Date | Change | Notes |
|------|--------|-------|
| | First prod deploy | |
| | | |
