# Voice feedback processing log

**Tracked copy (git):** `docs/voice-feedback/PROCESSING_LOG.en.md` — edit here so changes are visible in the repo.  
Local transcripts: `.artifacts/voice-feedback/transcripts/` (gitignored).

Track **transcription quality**, **what was requested**, and **what was fixed** after each voice batch.  
Append a new dated section when you transcribe new audio or ship fixes.

**Related files:** [`USER_REQUESTS.en.md`](USER_REQUESTS.en.md) · `.artifacts/voice-feedback/transcripts/audio_requirements.en.md` · `.artifacts/voice-feedback/batch_transcribe.log`

---

## How to verify audio was processed correctly

Run from repo root:

```bash
# 1) Count source .ogg files vs large-v3 transcripts
find .artifacts -name '*.ogg' | wc -l
grep -rl 'Model: `large-v3`' .artifacts/voice-feedback/transcripts/*.fa.md | wc -l

# 2) Batch script: lists pending (needs re-run if any)
conda run -n ml-env python tools/batch_transcribe_artifacts.py
# Expect: "No pending audio" or only new files

# 3) Spot-check a transcript header (model, runtime, language)
head -15 .artifacts/voice-feedback/transcripts/voice_20260616_124523_250394750_2_transcript.fa.md
```

**Pass criteria**

| Check | Expected |
|-------|----------|
| Every `.ogg` under `.artifacts/audio/` and `.artifacts/voice-feedback/audio/` has `{stem}_transcript.fa.md` | Yes |
| Transcript header contains `Model: \`large-v3\`` | Yes (batch target) |
| English summary updated | `USER_REQUESTS.en.md` + **this log** |
| Requirements mapped to code or backlog | Section below |

---

## Transcription inventory (last full batch: 2026-06-16)

| Metric | Value |
|--------|-------|
| Environment | conda `ml-env`, CUDA, RTX 4070 Ti SUPER |
| Model | `faster-whisper large-v3` (`cuda/float16 batch=16`) |
| Batch tool | `tools/batch_transcribe_artifacts.py` |
| Batch result | `BATCH_DONE ok=24 fail=0` (2 skipped — already `large-v3`) |
| `.ogg` sources | 26 |
| `large-v3` transcripts | 26 |

### Sources covered (all `large-v3`)

**June 12 evening (5)**  
`audio_2026-06-12_21-52-39` · `22-05-26` · `22-09-58` · `22-13-57` · `22-29-43`

**June 16 batch (21)**  
`voice_20260616_124523_250394750_2` … `_22` (stems `_2` through `_22`, including `_9` and `_10`)

### Older transcripts (not in current `.ogg` scan — re-transcribe if audio returns)

| File | Model | Note |
|------|-------|------|
| `audio_2026-06-13_11-14-02_transcript.fa.md` | medium | No matching `.ogg` in repo at last check |
| `audio_2026-06-13_11-14-07_transcript.fa.md` | medium | same |
| `audio_2026-06-13_11-14-12_transcript.fa.md` | medium | same |
| `audio_2026-06-13_11-14-15_transcript.fa.md` | medium | same |
| `audio_2026-06-13_11-20-43_transcript.fa.md` | medium | same |
| `audio_2026-06-12_*_transcript.medium.fa.md` | medium | Superseded by `large-v3` `.fa.md` siblings |

---

## 2026-06-16 — Requests extracted from voice (English)

| # | Topic | Source stems (examples) |
|---|--------|-------------------------|
| 1 | Invoice: action cost + 10% VAT + insurance + paid amount | `_2`, `_12` |
| 2 | Business line & budget line as admin dropdowns | `_4`, `_19`, `_21` |
| 3 | Dashboard: business-line filter, Jalali month, queues, recently paid | `_3`, `_17`, `_20`, `_22` |
| 4 | Clickable vendors + vendor detail page | `_8` |
| 5 | Invoice list: sort by entry date; paid row colors; days **—** when paid | `_15`, `_16`, `_8` |
| 6 | Budget hierarchy + manual budget entry | `_5`, `_18`, `_19` |
| 7 | Budget-line variance at invoice entry | `_6` |
| 8 | PDF export picker (business line, vendor, team, month) | `_10` |
| 9 | Roles: Editor import Excel; admin merge duplicates | `21-52-39`, `_21` |
| 10 | Inline payment-stage edit in lists | `_14` |
| 11 | Referral/SMS placement (Growth/Retention) | `22-13-57` |
| 12 | Excel round-trip export/import | `22-09-58` |
| 13 | Contracts: final signed upload | `_9` |
| 14 | UI: charts wider; consolidated nav; Jalali dates | `_7`, `_11`, `22-29-43` |

Full detail: [`USER_REQUESTS.en.md`](USER_REQUESTS.en.md)

---

## 2026-06-16 — Fixes shipped from voice feedback

| Request area | What changed | Verify |
|--------------|--------------|--------|
| Tax / insurance / paid | `Invoice` fields + `invoice_amounts.py`; form auto-calc; Excel importer | Create/edit invoice; re-import workbook |
| Business line dropdown | `BusinessLine` model + `/reference/business-lines/` | Invoice form shows select |
| Insurance rates | `InsuranceRateOption` + `/reference/insurance-rates/` | Form withholding dropdown |
| Category dropdown | `SpendCategory` on invoice form | No free-text category for editors |
| Dashboard filters | Business line + Jalali month on finance overview | Dashboard toolbar |
| Marketing / Finance queues | `SUBMITTED` + `FINANCE_REVIEW` tables | Dashboard ops section |
| Recently paid | Last 7 days, links to invoice detail | Dashboard |
| Vendor detail | `/vendors/<id>/` with invoices, contracts, totals | Click vendor on dashboard/list |
| Invoice list UX | Default sort `created_at`; paid/pending row CSS; days when paid | `/invoices/` |
| Instructions | `docs/voice-feedback/*`, `AGENTS.md`, discovery skills | Read paths |
| Tests | `test_invoice_amounts.py`, `test_cursor_prompts.py`; full suite **123 passed** | `uv run pytest -q` |

### Previously backlog — now done (see sections below)

Manual budget CRUD, budget variance on invoice form, % consumed, PDF wizard, vendor/campaign merge, editor import permission, inline stage edit, team→category cascade, contract ceiling on vendor detail, dashboard UI polish — all shipped 2026-06-16.

### Still open

- Exact Excel round-trip export (4-sheet mirror for Google Sheets)
- Year-end report: separate marketing spend vs VAT vs insurance deposits (per-invoice/vendor totals exist; no dedicated export)

## Changelog template (copy for next session)

```markdown
## YYYY-MM-DD — Transcription batch

- New audio: (list stems)
- Model / env:
- Batch result:
- Transcripts verified: yes/no
- USER_REQUESTS.en.md updated: yes/no

## YYYY-MM-DD — Fixes from voice

| Request | Status | Notes |
|---------|--------|-------|
| ... | done / partial / backlog | ... |
```

---

## 2026-06-16 — Cursor prompts 1–9 + dashboard filter UI

| Item | Status | Notes |
|------|--------|-------|
| Dashboard filter bar styling | done | Matches budget pages (`section` + standard `filter-form`) |
| Manual budget CRUD | done | `/budgets/new/`, edit, delete; admin only |
| Budget variance on invoice form | done | Live panel + `/api/budget-variance/` |
| % consumed on variance tables | done | Dashboard, team dashboard, analytics |
| PDF export wizard | done | `/exports/pdf/`; topbar PDF links route to wizard |
| Inline payment-stage edit | done | Invoice list + dashboard queues; JSON stage API |
| Vendor/campaign merge | done | `/reference/vendors/merge/`, `/reference/campaigns/merge/` |
| Team → category cascade | done | `/api/categories-for-team/` + invoice form JS |
| Editor Excel import permission | done | `UserTeamAccess.can_import_excel` migration `0012` |
| Contract ceiling on vendor detail | done | Start date + amount columns |
| Tests | done | `marketing/tests/test_cursor_prompts.py`; **123 passed** |

---

## 2026-06-16 — Dashboard UI polish (batch 2–22 backlog item)

| Item | Status | Notes |
|------|--------|-------|
| Terminology: planned budget vs actual spend | done | KPI cards, variance tables, charts, invoice variance panel; Persian labels disambiguated |
| Wider dashboard charts | done | Full-width stacked panels; `dashboard-panel-chart` min-height 320px |
| Consolidated navigation | done | Single **Finance** sidebar section (invoices → contracts) |
| Dark mode polish | done | Variance panel, deviation/consumed colors, card notes use theme tokens |
| Excel round-trip (4-sheet mirror) | backlog | Next task per `audio_feedback_batch_2_to_22.en.md` |

Sources: transcript `_7` (wider charts), `_11` (consolidated nav), `22-05-26` (spend vs budget/projection confusion).

---

## 2026-06-17 — Referral/SMS pie fix + security pass

| Item | Status | Notes |
|------|--------|-------|
| Referral/SMS not their own pie slice | done | `overall_spend_pie` now rolls Referral→Growth and SMS→Retention instead of appending standalone "Referral"/"SMS" slices; they stay in the overall total and keep their dedicated stat cards. Tests in `test_analytics.py`. |
| Sensitive uploads exposed via `/media/` | done | Invoice images, payment proofs, and signed contracts were served without auth (Django DEBUG static + Caddy `file_server`). Added permission-checked `invoice_attachment_download` / `contract_attachment_download` views (force `attachment` + `nosniff`); templates link through them; `DEPLOYMENT_AWS.md` updated to stop serving `/media/`. Test in `test_frontend_views.py`. |
| Deploy/security checks reviewed | done | `manage.py check --deploy` warnings (HSTS, secure cookies) are intentional, env-driven opt-ins documented in `ENV.md`/deploy guide. CSRF middleware on; mutations are POST-only; import path is a server UUID (no traversal); preferences redirect host-checked. |

Sources: transcript `_13` / `22-13-57` (Referral under Growth, SMS under Retention — isolate so they don't skew team charts); user instruction to remove standalone Referral/SMS pie slices and audit vulnerabilities.

---

*Last updated: 2026-06-17*
