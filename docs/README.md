# Documentation Map

A guide to every doc in this repo, grouped by purpose so you can find the right one fast.

**Status legend**
- 🟢 **Living** — kept in sync with the running app; trust these first.
- 📘 **Spec** — design reference written before/while building; mostly stable.
- 🗂️ **Reference** — generated or lookup material.
- 🕰️ **Historical** — planning/process notes kept for context; may be out of date.

---

## Start here

1. [`../README.md`](../README.md) — install, run, import data, verify. 🟢
2. [`PROJECT_EXPLAINED.md`](PROJECT_EXPLAINED.md) — a plain-language guided tour of the whole project. 🟢
3. [`CURRENT_STATE_AND_RUN_GUIDE.md`](CURRENT_STATE_AND_RUN_GUIDE.md) — the authoritative list of what works today + run commands. 🟢

---

## Orientation & status

| Doc | Purpose | Status |
|---|---|---|
| [`PROJECT_EXPLAINED.md`](PROJECT_EXPLAINED.md) | Guided tour: what it is, how the pieces fit | 🟢 Living |
| [`CURRENT_STATE_AND_RUN_GUIDE.md`](CURRENT_STATE_AND_RUN_GUIDE.md) | Current capabilities + how to run locally | 🟢 Living |
| [`PROJECT_BLUEPRINT.md`](PROJECT_BLUEPRINT.md) | High-level architecture and intent | 🟢 Living |
| [`PROJECT_FILE_REFERENCE.md`](PROJECT_FILE_REFERENCE.md) | What each file/module is for | 🟢 Living |
| [`PHASE_2.md`](PHASE_2.md) | Roadmap: shipped vs. next features | 🟢 Living |

## Access & permissions

| Doc | Purpose | Status |
|---|---|---|
| [`ACCESS_BY_ROLE.md`](ACCESS_BY_ROLE.md) | Who can see/do what, in plain language | 🟢 Living |
| [`PERMISSIONS_MATRIX.md`](PERMISSIONS_MATRIX.md) | Role × capability matrix | 🟢 Living |
| [`RBAC_SPEC.md`](RBAC_SPEC.md) | Original RBAC design spec | 📘 Spec |

## Operations & deployment

| Doc | Purpose | Status |
|---|---|---|
| [`DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md) | Copy-pasteable runbook: single EC2 + Caddy, then RDS/S3/CloudWatch | 🟢 Living |
| [`../AWS_Infrastructure_Field_Guide_Gentle_Steps.md`](../AWS_Infrastructure_Field_Guide_Gentle_Steps.md) | AWS learning background (concepts, not steps for this app) | 🗂️ Reference |

## Design specs (reference)

| Doc | Purpose | Status |
|---|---|---|
| [`PRODUCT_REQUIREMENTS.md`](PRODUCT_REQUIREMENTS.md) | What the product must do | 📘 Spec |
| [`DATA_MODEL.md`](DATA_MODEL.md) | Models, fields, cost buckets | 📘 Spec |
| [`DASHBOARD_SPEC.md`](DASHBOARD_SPEC.md) | Dashboard + reporting requirements | 📘 Spec |
| [`EXCEL_IMPORT_SPEC.md`](EXCEL_IMPORT_SPEC.md) | Importer behavior and rules | 📘 Spec |
| [`AUDIO_TRANSCRIPTION_AND_XLSX_DISCOVERY.md`](AUDIO_TRANSCRIPTION_AND_XLSX_DISCOVERY.md) | Discovery workflow spec | 📘 Spec |

## Discovery outputs

| Doc | Purpose | Status |
|---|---|---|
| [`discovery/column_mapping.yml`](discovery/column_mapping.yml) | Workbook → model column mapping (consumed by the importer) | 🗂️ Reference |
| [`discovery/workbook_structure.md`](discovery/workbook_structure.md) | Detected sheets/columns | 🗂️ Reference |
| [`discovery/workbook_sample_rows.md`](discovery/workbook_sample_rows.md) | Sample rows captured during discovery | 🗂️ Reference |
| [`discovery/import_risks.md`](discovery/import_risks.md) | Known import edge cases/risks | 🗂️ Reference |

## Process & history

| Doc | Purpose | Status |
|---|---|---|
| [`DEVELOPER_NOTES.md`](DEVELOPER_NOTES.md) | Assumptions and developer decisions | 🟢 Living |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Original build order | 🕰️ Historical |
| [`ACCEPTANCE_TESTS.md`](ACCEPTANCE_TESTS.md) | Original acceptance checklist | 🕰️ Historical |
| [`CODEX_PROMPTS.md`](CODEX_PROMPTS.md) | Prompts used to scaffold the project | 🕰️ Historical |
| [`END_STATE_CLEANUP_PLAN.md`](END_STATE_CLEANUP_PLAN.md) | Cleanup plan toward the final state | 🕰️ Historical |

## Agent / build instructions (repo root)

| Doc | Purpose | Status |
|---|---|---|
| [`../AGENTS.md`](../AGENTS.md) | Product + engineering requirements for AI agents | 🟢 Living |
| [`../CLAUDE.md`](../CLAUDE.md) | Pointer to `AGENTS.md` | 🟢 Living |
| [`../README_FOR_CODEX.md`](../README_FOR_CODEX.md) | Codex onboarding + mandatory discovery step | 🟢 Living |

---

## Common tasks → which doc

- **Run it locally** → [`../README.md`](../README.md) or [`CURRENT_STATE_AND_RUN_GUIDE.md`](CURRENT_STATE_AND_RUN_GUIDE.md)
- **Deploy to AWS** → [`DEPLOYMENT_AWS.md`](DEPLOYMENT_AWS.md)
- **Understand roles/permissions** → [`ACCESS_BY_ROLE.md`](ACCESS_BY_ROLE.md) + [`PERMISSIONS_MATRIX.md`](PERMISSIONS_MATRIX.md)
- **Change the import / column mapping** → [`EXCEL_IMPORT_SPEC.md`](EXCEL_IMPORT_SPEC.md) + [`discovery/column_mapping.yml`](discovery/column_mapping.yml)
- **Add a model field** → [`DATA_MODEL.md`](DATA_MODEL.md) + [`PROJECT_FILE_REFERENCE.md`](PROJECT_FILE_REFERENCE.md)
- **See what's next** → [`PHASE_2.md`](PHASE_2.md)
