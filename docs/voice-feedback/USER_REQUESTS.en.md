# Product Owner Requests (from voice audio)

**Tracked copy (git):** `docs/voice-feedback/USER_REQUESTS.en.md`  
Persian transcripts (local): `.artifacts/voice-feedback/transcripts/*_transcript.fa.md` (26 files, `large-v3`, June 2026).  
Processing log: [`PROCESSING_LOG.en.md`](PROCESSING_LOG.en.md)

---

## Main topics (what the user needs)

### 1. Invoice amounts — tax and insurance

- Each invoice has an **action cost** (base marketing spend, X).
- **10% VAT** is added on top → **invoice total = X + 10%**.
- **Insurance withholding** is deducted from the vendor share (typically **16.67%** or **7.78%** of X; rate varies by vendor).
- **Paid amount** = (X − insurance) + tax — what finance actually pays (less than invoice face value).
- Show action, tax, invoice total, and paid **per invoice and per vendor**.
- Year-end reporting must separate **marketing spend**, **tax**, and **insurance deposits**.

### 2. Data entry — dropdowns and reference data

- **Business line** (Retail, Junior, Business): admin-managed dropdown, not free text.
- **Budget line / category**: hierarchical names from budget data; dropdown on invoice form.
- **Team → budget line → business line** linkage when entering invoices.
- Editors may add **vendors/campaigns** at entry; only **admin** adds business lines and budget lines.
- Admin should **merge duplicate** vendor/campaign names (typos/spacing).

### 3. Dashboard and operations

- Filter by **year, team, business line, and Jalali month**.
- **Budget vs actual** with monthly breakdown and deviation; show **remaining budget** and **% consumed**.
- **Marketing queue** (submitted, waiting on marketing) and **Finance queue** (in finance review) with **days waiting**.
- **Recently paid** invoices (e.g. last 7 days) with links to attachments.
- **Clickable vendors** → vendor page (all invoices, contracts, totals).
- **Color-code** invoice rows: paid vs unpaid.
- Invoice list: sort by **entry date** (newest submissions first); when **paid**, days-in-stage shows **—**.

### 4. Budget structure

- Budget lines match Excel hierarchy: team → sub-team → line → vendor/action.
- **Manual budget entry** in the panel (not Excel-only): monthly amounts Jan–Dec.
- At invoice entry, show **budget-line variance** (planned vs actual + %) for the selected line.
- **SMS** costs belong under **Retention**; **Referral** under **Growth** — shown separately but included in team/overall totals.

### 5. Roles and permissions

- **Admin**: full access, reference data, merges.
- **Manager**: richer reports, less edit than admin.
- **Editor**: enter/edit invoices for assigned teams; should be able to **import Excel** (requested).
- **Observer**: read-only for assigned teams.

### 6. Export and round-trip

- **Excel export** should mirror the source workbook (round-trip with Google Sheets workflow).
- **Excel upload** to preload/update invoices.
- **PDF export wizard**: pick business line, vendor, team, month before generating (requested).

### 7. Contracts and vendors

- Upload **final signed contract** text; multiple contracts/amendments per vendor per year.
- Vendor page: contracts (dates, ceiling), all invoices, payment stages, totals.

### 8. UI polish (approved direction)

- Panel look/feel is **on track**; fix confusion between **budget vs spend** on dashboards.
- Jalali dates, sort/filter by date and month across pages.
- Clearer charts (wider, centered); consolidated navigation.

---

## Implementation status (high level)

| Topic | Status |
|-------|--------|
| Tax / insurance / paid fields + form calc | Done |
| Business line + insurance rate reference CRUD | Done |
| Dashboard: business line, month, queues, recently paid | Done |
| Vendor detail page + clickable vendors | Done |
| Invoice list: entry-date sort, paid colors, days when paid | Done |
| Manual budget CRUD | Backlog |
| Budget-line variance at invoice entry | Backlog |
| Remaining budget / % on variance table | Backlog |
| PDF export wizard | Backlog |
| Vendor/campaign merge UI | Backlog |
| Editor Excel import permission | Backlog |
| Inline payment-stage edit in lists | Backlog |

Detail: [`PROCESSING_LOG.en.md`](PROCESSING_LOG.en.md) · `.artifacts/voice-feedback/transcripts/audio_requirements.en.md`
