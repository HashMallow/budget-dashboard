PYTHON ?= python
VENV := .venv
BIN := $(VENV)/bin
MANAGE := $(BIN)/python manage.py
FILE ?=
HOST ?= 127.0.0.1
PORT ?= 8000
ADMIN_USER ?= admin
ADMIN_PASSWORD ?= admin12345
ADMIN_EMAIL ?= admin@example.com

.PHONY: help setup migrate superuser dev-admin groups import-dry-run import run panel first-run check test lint django-check shell clean-artifacts clean-local-db

help:
	@echo "Marketing dashboard local commands"
	@echo ""
	@echo "  make setup                 Create .venv, install deps, migrate, seed groups"
	@echo "  make superuser             Create an admin login"
	@echo "  make dev-admin             Create/update local admin admin/admin12345"
	@echo "  make import-dry-run        Preview Excel import using auto-detected workbook"
	@echo "  make import                Import Excel using auto-detected workbook"
	@echo "  make import FILE=path.xlsx Import a specific workbook"
	@echo "  make run                   Start local server at http://127.0.0.1:8000/"
	@echo "  make panel                 Ensure local admin, then start server"
	@echo "  make first-run             Setup, create local admin, import workbook, start server"
	@echo "  make check                 Run Django checks, tests, and lint"
	@echo "  make shell                 Open Django shell"
	@echo "  make clean-artifacts       Remove caches and generated local artifacts"
	@echo "  make clean-local-db        Remove local SQLite DB (destructive)"

$(BIN)/python:
	$(PYTHON) -m venv $(VENV)

setup: $(BIN)/python
	$(BIN)/python -m pip install -r requirements.txt
	$(MANAGE) migrate
	$(MANAGE) seed_auth_groups
	@echo ""
	@echo "Setup complete. Run 'make superuser' once if you do not have an admin login."

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

panel: dev-admin run

first-run: setup dev-admin import run

check: django-check test lint

django-check:
	$(MANAGE) check

test:
	$(BIN)/pytest -q

lint:
	$(BIN)/ruff check .

shell:
	$(MANAGE) shell

clean-artifacts:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache staticfiles
	rm -f docs/discovery/audio.wav

clean-local-db:
	rm -f db.sqlite3
