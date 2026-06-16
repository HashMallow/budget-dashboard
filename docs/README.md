# Documentation Map

A guide to every doc in this repo, grouped by purpose so you can find the right one fast.

**Keep in sync:** When changing panel navigation, dashboard layout, or user-facing flows, update the 🟢 **Living** docs — especially [`guides/USER_SITEMAP.md`](guides/USER_SITEMAP.md), in-app **Help** (`templates/marketing/help_sitemap.html`), and [`guides/CURRENT_STATE_AND_RUN_GUIDE.md`](guides/CURRENT_STATE_AND_RUN_GUIDE.md).

**Status legend**
- 🟢 **Living** — kept in sync with the running app; trust these first.
- 📘 **Spec** — design reference written before/while building; mostly stable.
- 🗂️ **Reference** — generated or lookup material.
- 🕰️ **Historical** — planning/process notes kept for context; may be out of date.

---

## Start here

1. [`../README.md`](../README.md) — install, run, import data, verify. 🟢
2. [`guides/USER_SITEMAP.md`](guides/USER_SITEMAP.md) — **for end users:** what each menu and page does (also in-app under **Help**). 🟢
3. [`guides/PROJECT_EXPLAINED.md`](guides/PROJECT_EXPLAINED.md) — a plain-language guided tour of the whole project. 🟢
4. [`guides/CURRENT_STATE_AND_RUN_GUIDE.md`](guides/CURRENT_STATE_AND_RUN_GUIDE.md) — the authoritative list of what works today + run commands. 🟢

---

## Orientation & status

| Doc | Purpose | Status |
|---|---|---|
| [`guides/USER_SITEMAP.md`](guides/USER_SITEMAP.md) | End-user site map: what each screen does | 🟢 Living |
| [`guides/PROJECT_EXPLAINED.md`](guides/PROJECT_EXPLAINED.md) | Guided tour: what it is, how the pieces fit | 🟢 Living |
| [`guides/CURRENT_STATE_AND_RUN_GUIDE.md`](guides/CURRENT_STATE_AND_RUN_GUIDE.md) | Current capabilities + how to run locally | 🟢 Living |
| [`architecture/PROJECT_BLUEPRINT.md`](architecture/PROJECT_BLUEPRINT.md) | High-level architecture and intent | 🟢 Living |
| [`architecture/PROJECT_FILE_REFERENCE.md`](architecture/PROJECT_FILE_REFERENCE.md) | What each file/module is for | 🟢 Living |
| [`project/PHASE_2.md`](project/PHASE_2.md) | Roadmap: shipped vs. next features | 🟢 Living |

## Access & permissions

| Doc | Purpose | Status |
|---|---|---|
| [`operations/ACCESS_BY_ROLE.md`](operations/ACCESS_BY_ROLE.md) | Who can see/do what, in plain language | 🟢 Living |
| [`operations/PASSWORDS_AND_USERS.md`](operations/PASSWORDS_AND_USERS.md) | Admin password change, creating users, better password options | 🟢 Living |
| [`operations/PERMISSIONS_MATRIX.md`](operations/PERMISSIONS_MATRIX.md) | Role × capability matrix | 🟢 Living |
| [`specs/RBAC_SPEC.md`](specs/RBAC_SPEC.md) | Original RBAC design spec | 📘 Spec |

## Operations & deployment

| Doc | Purpose | Status |
|---|---|---|
| [`operations/DEPLOYMENT_AWS.md`](operations/DEPLOYMENT_AWS.md) | Preferred path: EC2 + Caddy + gunicorn (copy-paste runbook) | 🟢 Living |
| [`reference/AWS_EC2_Deployment_Path_Field_Guide.pdf`](reference/AWS_EC2_Deployment_Path_Field_Guide.pdf) | Gentle Console + CLI companion (checkpoints, diagrams) | 🗂️ Reference |

## Design specs (reference)

| Doc | Purpose | Status |
|---|---|---|
| [`specs/PRODUCT_REQUIREMENTS.md`](specs/PRODUCT_REQUIREMENTS.md) | What the product must do | 📘 Spec |
| [`architecture/DATA_MODEL.md`](architecture/DATA_MODEL.md) | Models, fields, cost buckets | 📘 Spec |
| [`specs/DASHBOARD_SPEC.md`](specs/DASHBOARD_SPEC.md) | Dashboard + reporting requirements | 📘 Spec |
| [`specs/EXCEL_IMPORT_SPEC.md`](specs/EXCEL_IMPORT_SPEC.md) | Importer behavior and rules | 📘 Spec |
| [`specs/AUDIO_TRANSCRIPTION_AND_XLSX_DISCOVERY.md`](specs/AUDIO_TRANSCRIPTION_AND_XLSX_DISCOVERY.md) | Discovery workflow spec | 📘 Spec |

## Discovery outputs

| Doc | Purpose | Status |
|---|---|---|
| [`voice-feedback/PROCESSING_LOG.en.md`](voice-feedback/PROCESSING_LOG.en.md) | Voice batch verification, requests, fixes, backlog | 🟢 Living |
| [`voice-feedback/USER_REQUESTS.en.md`](voice-feedback/USER_REQUESTS.en.md) | Main topics from product-owner audio | 🟢 Living |
| [`voice-feedback/README.md`](voice-feedback/README.md) | Voice-feedback doc index | 🟢 Living |
| [`requirements_audit.md`](requirements_audit.md) | Full gap analysis: transcripts vs codebase | 🟢 Living |
| [`cursor_prompts.md`](cursor_prompts.md) | 9 copy-paste prompts for backlog features | 🟢 Living |
| [`discovery/column_mapping.yml`](discovery/column_mapping.yml) | Anonymized import template (columns/rows/rules); merged with optional gitignored `column_mapping.local.yml` | 🗂️ Reference |
| [`discovery/column_mapping.local.yml.example`](discovery/column_mapping.local.yml.example) | Example local override (copy → `column_mapping.local.yml`) | 🗂️ Reference |
| [`discovery/README.md`](discovery/README.md) | How mapping, auto-detect, and local overrides work | 🟢 Living |
| [`discovery/workbook_structure.md`](discovery/workbook_structure.md) | Detected sheets/columns | 🗂️ Reference |
| [`discovery/workbook_sample_rows.md`](discovery/workbook_sample_rows.md) | Sample rows captured during discovery | 🗂️ Reference |
| [`discovery/import_risks.md`](discovery/import_risks.md) | Known import edge cases/risks | 🗂️ Reference |

## Process & history

| Doc | Purpose | Status |
|---|---|---|
| [`guides/DEVELOPER_NOTES.md`](guides/DEVELOPER_NOTES.md) | Assumptions and developer decisions | 🟢 Living |
| [`guides/SIMPLE_LOCAL_SETUP.md`](guides/SIMPLE_LOCAL_SETUP.md) | Short Mac/Linux setup guide | 🟢 Living |

## Agent / build instructions (repo root)

| Doc | Purpose | Status |
|---|---|---|
| [`../AGENTS.md`](../AGENTS.md) | Product + engineering requirements for AI agents | 🟢 Living |
| [`../CLAUDE.md`](../CLAUDE.md) | Pointer to `AGENTS.md` | 🟢 Living |

---

## Common tasks → which doc

- **Run it locally** → [`../README.md`](../README.md) or [`guides/CURRENT_STATE_AND_RUN_GUIDE.md`](guides/CURRENT_STATE_AND_RUN_GUIDE.md)
- **Deploy to AWS** → [`operations/DEPLOYMENT_AWS.md`](operations/DEPLOYMENT_AWS.md)
- **Understand roles/permissions** → [`operations/ACCESS_BY_ROLE.md`](operations/ACCESS_BY_ROLE.md) + [`operations/PERMISSIONS_MATRIX.md`](operations/PERMISSIONS_MATRIX.md)
- **Change admin password / onboard users** → [`operations/PASSWORDS_AND_USERS.md`](operations/PASSWORDS_AND_USERS.md)
- **Explain the panel to a colleague** → [`guides/USER_SITEMAP.md`](guides/USER_SITEMAP.md) or in-app **Help** (`/help/`)
- **Voice feedback / what was fixed from audio** → [`voice-feedback/PROCESSING_LOG.en.md`](voice-feedback/PROCESSING_LOG.en.md)
- **Gap analysis (transcripts vs code)** → [`requirements_audit.md`](requirements_audit.md)
- **Copy-paste fixes for backlog** → [`cursor_prompts.md`](cursor_prompts.md)
- **Change the import / column mapping** → [`specs/EXCEL_IMPORT_SPEC.md`](specs/EXCEL_IMPORT_SPEC.md) + [`discovery/README.md`](discovery/README.md) + [`discovery/column_mapping.yml`](discovery/column_mapping.yml)
- **Add a model field** → [`architecture/DATA_MODEL.md`](architecture/DATA_MODEL.md) + [`architecture/PROJECT_FILE_REFERENCE.md`](architecture/PROJECT_FILE_REFERENCE.md)
- **See what's next** → [`project/PHASE_2.md`](project/PHASE_2.md)