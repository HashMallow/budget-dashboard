UV ?= uv
UV_CONFIG ?= uv.toml
UV_CACHE ?= .uv-cache
UV_RUN := UV_CONFIG_FILE=$(UV_CONFIG) UV_CACHE_DIR=$(UV_CACHE) $(UV)
MANAGE := $(UV_RUN) run python manage.py
FILE ?=
HOST ?= 127.0.0.1
PORT ?= 8000
ADMIN_USER ?= admin
ADMIN_PASSWORD ?= admin12345
ADMIN_EMAIL ?= admin@example.com

.PHONY: help setup migrate superuser dev-admin groups import-dry-run import run dev panel first-run check test lint django-check shell clean-artifacts clean-local-db prod-install collectstatic prod-run

help:
	@echo "Marketing dashboard local commands"
	@echo ""
	@echo "  make setup                 uv sync, migrate, seed groups"
	@echo "  make superuser             Create an admin login"
	@echo "  make dev-admin             Create/update local admin admin/admin12345"
	@echo "  make import-dry-run        Preview Excel import using auto-detected workbook"
	@echo "  make import                Import Excel using auto-detected workbook"
	@echo "  make import FILE=path.xlsx Import a specific workbook"
	@echo "  make run                   Start local server (no auto-reload)"
	@echo "  make dev                   Start local server WITH auto-reload"
	@echo "  make panel                 Ensure local admin, then start server"
	@echo "  make first-run             Setup, create local admin, import workbook, start server"
	@echo "  make check                 Run Django checks, tests, and lint"
	@echo "  make shell                 Open Django shell"
	@echo "  make clean-artifacts       Remove caches and generated local artifacts"
	@echo "  make clean-local-db        Remove local SQLite DB (destructive)"
	@echo ""
	@echo "  Production (see docs/DEPLOYMENT_AWS.md):"
	@echo "  make prod-install          uv sync with the 'prod' extra (gunicorn/psycopg/whitenoise/dj-database-url)"
	@echo "  make collectstatic         Collect static files into STATIC_ROOT"
	@echo "  make prod-run              Run gunicorn (expects production .env: DEBUG=false, DATABASE_URL, etc.)"

setup:
	$(UV_RUN) sync --all-groups
	$(MANAGE) migrate
	$(MANAGE) seed_auth_groups
	@echo ""
	@echo "Setup complete. Run 'make dev-admin' for the local admin login."

migrate:
	$(MANAGE) migrate

groups:
	$(MANAGE) seed_auth_groups

superuser:
	$(MANAGE) createsuperuser

dev-admin:
	$(MANAGE) bootstrap_dev_admin --username "$(ADMIN_USER)" --email "$(ADMIN_EMAIL)" --password "$(ADMIN_PASSWORD)"
	@echo "Local login: $(ADMIN_USER) / $(ADMIN_PASSWORD)"

import-dry-run:
	$(MANAGE) import_marketing_excel --dry-run $(if $(FILE),--file "$(FILE)",)

import:
	$(MANAGE) import_marketing_excel $(if $(FILE),--file "$(FILE)",)

run:
	$(MANAGE) runserver $(HOST):$(PORT) --noreload

dev:
	$(MANAGE) runserver $(HOST):$(PORT)

panel: dev-admin run

first-run: setup dev-admin import run

check: django-check test lint

django-check:
	$(MANAGE) check

test:
	$(UV_RUN) run pytest -q

lint:
	$(UV_RUN) run ruff check .

shell:
	$(MANAGE) shell

prod-install:
	$(UV_RUN) sync --extra prod

collectstatic:
	$(MANAGE) collectstatic --noinput

prod-run:
	$(UV_RUN) run gunicorn config.wsgi:application --bind $(HOST):$(PORT) --workers 3

clean-artifacts:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache staticfiles
	rm -f docs/discovery/*.wav

clean-local-db:
	rm -f db.sqlite3
