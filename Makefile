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
AUDIO ?=
TRANSCRIPT_OUT ?= docs/discovery
TRANSCRIPT_WAV_DIR ?=
TRANSCRIPT_LANG ?= fa
TRANSCRIPT_MODEL ?= auto
TRANSCRIPT_DEVICE ?= auto
TRANSCRIPT_COMPUTE ?= auto
TRANSCRIPT_PACKAGES ?= --with faster-whisper
# For Mac (Apple Silicon), mlx-whisper is highly optimized and runs fast on the GPU.
# You can override this to: TRANSCRIPT_PACKAGES="--with mlx-whisper"
# GPU run uses the system CUDA/cuDNN/cuBLAS libraries (e.g. /usr/local/cuda). If your machine
# lacks them, append the runtime wheels: TRANSCRIPT_GPU_PACKAGES="--with faster-whisper \
# --with nvidia-cublas-cu12 --with nvidia-cudnn-cu12" (a ~1.3 GB one-time download).
TRANSCRIPT_GPU_PACKAGES ?= --with faster-whisper
TRANSCRIPT_OUTPUT_NAME ?= $(notdir $(basename $(AUDIO)))_transcript.$(TRANSCRIPT_LANG).md
TRANSCRIPT_WAV_FLAG = $(if $(TRANSCRIPT_WAV_DIR),--wav-dir "$(TRANSCRIPT_WAV_DIR)",)
TRANSCRIPT_MAC_PACKAGES ?= --with mlx-whisper

.PHONY: help check-uv setup migrate superuser dev-admin groups import-dry-run import seed-reference seed-reference-dry-run load-data-dry-run load-data transcribe-audio transcribe-audio-mac transcribe-audio-gpu transcribe-audio-high transcribe-voice run dev panel first-run check test lint django-check shell clean-artifacts clean-local-db prod-install collectstatic prod-run

help:
	@echo "Marketing Spend Dashboard — local commands"
	@echo ""
	@echo "First-time setup:"
	@echo "  make setup                 uv sync, migrate, seed auth groups"
	@echo "  make dev-admin             Create/update local admin ($(ADMIN_USER) / $(ADMIN_PASSWORD))"
	@echo "  make load-data-dry-run     Preview Excel import + Data-sheet lookups (no DB writes)"
	@echo "  make load-data             Import workbook + seed vendors/categories/sub-teams/requesters"
	@echo "  make dev                   Start server with auto-reload at http://$(HOST):$(PORT)/login/"
	@echo ""
	@echo "Day-to-day:"
	@echo "  make dev                   Dev server with auto-reload (default $(HOST):$(PORT))"
	@echo "  make run                   Dev server without auto-reload"
	@echo "  make panel                 dev-admin + run (quick local login)"
	@echo "  make check                 Django check + pytest + ruff"
	@echo "  make shell                 Django shell"
	@echo ""
	@echo "Excel / reference data:"
	@echo "  make import-dry-run        Preview invoice + budget import"
	@echo "  make import                Import invoices and budget lines"
	@echo "  make import FILE=path.xlsx Import a specific workbook"
	@echo "  make seed-reference-dry-run Preview Data-sheet lookup seeding"
	@echo "  make seed-reference        Seed vendors/categories/sub-teams/requesters"
	@echo "  make load-data-dry-run     import-dry-run + seed-reference-dry-run"
	@echo "  make load-data             import + seed-reference"
	@echo ""
	@echo "Voice notes (optional, not required for the panel):"
	@echo "  make transcribe-audio AUDIO=path.ogg"
	@echo "  make transcribe-audio-mac AUDIO=path.ogg (Uses Apple GPU/mlx-whisper)"
	@echo "  make transcribe-audio-gpu AUDIO=path.ogg [TRANSCRIPT_MODEL=large-v3]"
	@echo "  make transcribe-audio-high AUDIO=path.ogg"
	@echo "  make transcribe-voice AUDIO=.artifacts/voice-feedback/audio/note.ogg"
	@echo ""
	@echo "Shortcuts:"
	@echo "  make first-run             setup + dev-admin + load-data + run"
	@echo "  make superuser             Interactive createsuperuser"
	@echo "  make migrate               Apply migrations only"
	@echo "  make groups                Re-seed Admin/Manager/Editor/Observer groups"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean-artifacts       Remove __pycache__, pytest/ruff caches, staticfiles, discovery WAV/transcripts, whisper model cache"
	@echo "  make clean-local-db        Delete db.sqlite3 (destructive — re-run setup after)"
	@echo ""
	@echo "Production (see docs/operations/DEPLOYMENT_AWS.md):"
	@echo "  make prod-install          uv sync --extra prod"
	@echo "  make collectstatic         Collect static files into STATIC_ROOT"
	@echo "  make prod-run              gunicorn (expects production .env)"
	@echo ""
	@echo "Variables: FILE=workbook.xlsx  HOST=$(HOST)  PORT=$(PORT)"
	@echo "           ADMIN_USER / ADMIN_PASSWORD / ADMIN_EMAIL for dev-admin"
	@echo ""
	@echo "Panel (after make dev): /login/  /help/  dashboard  invoices  teams"
	@echo "  budgets  vendors  campaigns  contracts  /reference/  /imports/  /users/"

check-uv:
	@command -v "$(UV)" >/dev/null 2>&1 || ( \
		echo "Error: uv is not installed or is not on PATH."; \
		echo ""; \
		echo "Install uv first:"; \
		echo "  macOS with Homebrew: brew install uv"; \
		echo "  macOS/Linux installer: curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		echo ""; \
		echo "After installing, restart the terminal or run:"; \
		echo '  export PATH="$$HOME/.local/bin:$$PATH"'; \
		exit 127; \
	)

setup: check-uv
	$(UV_RUN) sync --all-groups
	$(MANAGE) migrate
	$(MANAGE) seed_auth_groups
	@echo ""
	@echo "Setup complete. Run 'make dev-admin' for the local admin login."

migrate: check-uv
	$(MANAGE) migrate

groups: check-uv
	$(MANAGE) seed_auth_groups

superuser: check-uv
	$(MANAGE) createsuperuser

dev-admin: check-uv
	$(MANAGE) bootstrap_dev_admin --username "$(ADMIN_USER)" --email "$(ADMIN_EMAIL)" --password "$(ADMIN_PASSWORD)"
	@echo "Local login: $(ADMIN_USER) / $(ADMIN_PASSWORD)"

import-dry-run: check-uv
	$(MANAGE) import_marketing_excel --dry-run $(if $(FILE),--file "$(FILE)",)

import: check-uv
	$(MANAGE) import_marketing_excel $(if $(FILE),--file "$(FILE)",)

seed-reference-dry-run: check-uv
	$(MANAGE) seed_reference_data --dry-run $(if $(FILE),--file "$(FILE)",)

seed-reference: check-uv
	$(MANAGE) seed_reference_data $(if $(FILE),--file "$(FILE)",)

load-data-dry-run: import-dry-run seed-reference-dry-run

load-data: import seed-reference

transcribe-audio: check-uv
	@test -n "$(AUDIO)" || (echo "Usage: make transcribe-audio AUDIO=path/to/audio.ogg" && exit 2)
	$(UV_RUN) run $(TRANSCRIPT_PACKAGES) python .agents/skills/audio-transcription/scripts/transcribe_audio.py "$(AUDIO)" --out-dir "$(TRANSCRIPT_OUT)" --language "$(TRANSCRIPT_LANG)" --model "$(TRANSCRIPT_MODEL)" --device "$(TRANSCRIPT_DEVICE)" --compute-type "$(TRANSCRIPT_COMPUTE)" --output-name "$(TRANSCRIPT_OUTPUT_NAME)" $(TRANSCRIPT_WAV_FLAG)

transcribe-audio-gpu: check-uv
	@test -n "$(AUDIO)" || (echo "Usage: make transcribe-audio-gpu AUDIO=path/to/audio.ogg [TRANSCRIPT_MODEL=large-v3]" && exit 2)
	$(UV_RUN) run $(TRANSCRIPT_GPU_PACKAGES) python .agents/skills/audio-transcription/scripts/transcribe_audio.py "$(AUDIO)" --out-dir "$(TRANSCRIPT_OUT)" --language "$(TRANSCRIPT_LANG)" --model "$(TRANSCRIPT_MODEL)" --device cuda --compute-type float16 --output-name "$(TRANSCRIPT_OUTPUT_NAME)" $(TRANSCRIPT_WAV_FLAG)

transcribe-audio-mac: check-uv
	@test -n "$(AUDIO)" || (echo "Usage: make transcribe-audio-mac AUDIO=path/to/audio.ogg" && exit 2)
	$(UV_RUN) run $(TRANSCRIPT_MAC_PACKAGES) python .agents/skills/audio-transcription/scripts/transcribe_audio.py "$(AUDIO)" --out-dir "$(TRANSCRIPT_OUT)" --language "$(TRANSCRIPT_LANG)" --model "$(TRANSCRIPT_MODEL)" --output-name "$(TRANSCRIPT_OUTPUT_NAME)" $(TRANSCRIPT_WAV_FLAG)

# Highest-accuracy transcription: large-v3 on the GPU (needs a CUDA GPU; ~3 GB VRAM in float16).
transcribe-audio-high:
	@test -n "$(AUDIO)" || (echo "Usage: make transcribe-audio-high AUDIO=path/to/audio.ogg" && exit 2)
	$(MAKE) transcribe-audio-gpu AUDIO="$(AUDIO)" TRANSCRIPT_MODEL=large-v3 TRANSCRIPT_OUTPUT_NAME="$(TRANSCRIPT_OUTPUT_NAME)"

# Voice-feedback layout: audio under .artifacts/voice-feedback/audio/, WAV + transcript elsewhere.
transcribe-voice:
	@test -n "$(AUDIO)" || (echo "Usage: make transcribe-voice AUDIO=.artifacts/voice-feedback/audio/note.ogg" && exit 2)
	$(MAKE) transcribe-audio AUDIO="$(AUDIO)" TRANSCRIPT_OUT=.artifacts/voice-feedback/transcripts TRANSCRIPT_WAV_DIR=.artifacts/voice-feedback/converted

run: check-uv
	$(MANAGE) runserver $(HOST):$(PORT) --noreload

dev: check-uv
	$(MANAGE) runserver $(HOST):$(PORT)

panel: dev-admin run

first-run: setup dev-admin load-data run

check: check-uv django-check test lint

django-check: check-uv
	$(MANAGE) check

test: check-uv
	$(UV_RUN) run pytest -q

lint: check-uv
	$(UV_RUN) run ruff check .

shell: check-uv
	$(MANAGE) shell

prod-install: check-uv
	$(UV_RUN) sync --extra prod

collectstatic: check-uv
	$(MANAGE) collectstatic --noinput

prod-run: check-uv
	$(UV_RUN) run gunicorn config.wsgi:application --bind $(HOST):$(PORT) --workers 3

clean-artifacts:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache staticfiles
	rm -rf docs/discovery/faster-whisper-models
	rm -f docs/discovery/*.wav docs/discovery/audio_*.md docs/discovery/workbook_*.md docs/discovery/import_risks.md
	rm -f db.sqlite3.verifytest db.sqlite3.*

clean-local-db:
	rm -f db.sqlite3
