# Containerization notes (future)

Personal reference for dockerizing **this Django app** and similar internal dashboards. Not required for v1 — EC2 + systemd + gunicorn is simpler.

---

## When containers help

- Same image runs on laptop, staging, and prod
- Reproducible Python + system deps
- Easy horizontal scale behind a load balancer
- CI builds once, deploys many

## When to skip (this project today)

- Single internal dashboard, low traffic
- One EC2 + Caddy already works
- Uploads on local disk; SQLite/Postgres on host
- Team is small — systemd is easier to debug

---

## Target architecture (future)

```text
                    ┌─────────────────┐
  Browser ──HTTPS──►│ Caddy / ALB     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ web container   │
                    │ gunicorn :8000  │
                    │ Django + WhiteNoise
                    └────────┬────────┘
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐
       │ Postgres    │ │ S3 media  │ │ (optional)│
       │ container / │ │           │ │ Redis     │
       │ RDS         │ │           │ │ cache     │
       └─────────────┘ └───────────┘ └───────────┘
```

---

## Minimal Dockerfile sketch (not in repo yet)

```dockerfile
FROM python:3.13-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"
COPY pyproject.toml uv.lock ./
RUN uv sync --extra prod --frozen --no-dev
COPY . .
RUN uv run python manage.py collectstatic --noinput
ENV DJANGO_DEBUG=false
EXPOSE 8000
CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
```

**Caveats for this app:**

- Run `migrate` as a **one-off job** or entrypoint script, not on every worker start in parallel
- Mount **volume** for `media/` until S3 is wired
- Pass all config via env (see [`ENV.md`](ENV.md))
- Do not bake secrets into the image

---

## docker-compose sketch (local staging)

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: marketing
      POSTGRES_USER: marketing
      POSTGRES_PASSWORD: devonly
    volumes:
      - pgdata:/var/lib/postgresql/data

  web:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      DATABASE_URL: postgres://marketing:devonly@db:5432/marketing
    volumes:
      - ./media:/app/media
    depends_on:
      - db

volumes:
  pgdata:
```

Use for staging only until media → S3 and secrets → parameter store.

---

## AWS container paths (later)

| Option | Fit | Notes |
|--------|-----|-------|
| **ECS Fargate** | Medium | No EC2 patching; ALB + RDS + S3 |
| **App Runner** | Simplest AWS container | Less control over Caddy |
| **EKS** | Overkill | Only if org standard |
| **EC2 + Docker** | Transitional | Same VM, compose stack |

Recommended upgrade from bare EC2: **EC2 + Docker Compose** first, then **ECS Fargate** if you need auto-scaling.

---

## Checklist before going container-native

- [ ] Stable env contract documented ([`ENV.md`](ENV.md))
- [ ] Postgres (not SQLite) in all non-dev environments
- [ ] Media on S3 (`django-storages`) — containers are ephemeral
- [ ] Health check endpoint (e.g. `/login/` 200 or dedicated `/health/`)
- [ ] CI: build image, run `make check`, push to ECR
- [ ] Migrations as separate deploy step

---

## Similar projects pattern

For other Django internal tools in the same org:

1. Copy `config/settings.py` env pattern (DATABASE_URL, DEBUG, SECRET_KEY)
2. Same stack: gunicorn + WhiteNoise + optional Postgres
3. Shared base Dockerfile with `uv sync --extra prod`
4. One compose file for local; Terraform/ECS for prod when ready
