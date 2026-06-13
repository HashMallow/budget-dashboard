# Project Explained (a guided tour)

This is a plain-language walkthrough of how the **Marketing Spend Dashboard** works, written to
get you a full mental model fast. It assumes you're comfortable with intermediate Python (classes,
decorators, iterators, enums, context managers) and have seen SQLAlchemy, FastAPI, Docker, and Go,
but are newer to **Django**. Where useful, it maps Django ideas onto things you already know.

If you only read one section, read **"2. The mental model"** and **"4. How one page request
works"**.

---

## 1. What the app is, in one paragraph

It's an internal web dashboard for tracking marketing spend. An admin imports an Excel workbook
(invoices + budgets), the data is normalized into a relational database, and then users log in and
see dashboards, invoice lists, vendor/campaign reports, and budgets — **but only the slice of data
their role allows**. Admins can enter/edit invoices, track payment stages, upload invoice/receipt
images, and export to Excel/PDF. The UI is bilingual (Persian/English). Excel is only an
import/export format; once imported, **the database is the source of truth**.

---

## 2. The mental model (mapping to what you know)

| You already know | Here it's called | Notes |
|---|---|---|
| FastAPI (web framework) | **Django** | Batteries-included: ORM, auth, templates, admin, forms all built in. |
| SQLAlchemy mapped classes | **Django models** (`models.py`) | A class = a table; an attribute = a column. |
| SQLAlchemy `Session` / queries | **QuerySets** (`Model.objects...`) | Lazy: building a query doesn't hit the DB until you iterate it. |
| Alembic migrations | **Django migrations** (`manage.py makemigrations` / `migrate`) | Versioned schema changes as Python files. |
| `enum.Enum` (your Enum notebook) | **`models.TextChoices`** | e.g. `PaymentStage`, `Role`, `CostBucket` — DB-stored strings with labels. |
| Decorators (your Decorators notebook) | **View decorators** | `@login_required`, `@require_POST` wrap view functions. |
| Iterators (your Iterator notebook) | **QuerySets are lazy iterables** | They stream rows; you can filter/slice before evaluation. |
| Jinja-style templates | **Django Templates** (`templates/…/*.html`) | `{{ value }}`, `{% for %}`, custom tags like `{% t %}`. |
| `python-dotenv` / env config | **`os.environ` in `config/settings.py`** | `DEBUG`, `SECRET_KEY`, `DATABASE_URL`, etc. |
| ASGI/WSGI app object | **`config/wsgi.py` → gunicorn in prod** | `runserver` locally, gunicorn in production. |

**The one big idea that's different from a hand-rolled FastAPI app:** in Django you mostly *declare*
things (models, forms, URL routes) and the framework wires them together. Less plumbing, more
convention.

---

## 3. The big picture (data flow)

```text
Excel workbook (.xlsx)            docs/discovery/column_mapping.yml
        |                                   |
        |  (admin runs import, or uploads)  |  (tells the importer which column = which field)
        v                                   v
  marketing/importers/excel.py  --------- reads mapping, normalizes, de-duplicates
        |
        v
  Relational database  (SQLite in dev, PostgreSQL in prod)
   Team / Vendor / Campaign / Invoice / BudgetLine / UserTeamAccess / …
        |
        v
  marketing/views.py   --- filters data by the logged-in user's permissions,
        |                   aggregates totals for charts/reports
        v
  templates/marketing/*.html  --- renders HTML (bilingual), pie chart via Chart.js
        |
        v
  Browser
```

Everything the user sees is **aggregated and permission-filtered on the server first**. The
browser never receives rows the user isn't allowed to see.

---

## 4. How one page request works (the request lifecycle)

Take opening the dashboard at `/`:

1. **URL routing** — `config/urls.py` includes `marketing/urls.py`, which maps the path `/` to the
   `dashboard` view function.
2. **The view runs** (`marketing/views.py: dashboard`). It's wrapped in `@login_required`
   (a decorator), so anonymous users get bounced to the login page first.
3. **Permission filtering** — the view calls helpers like `visible_invoice_queryset(request)`,
   which internally use `filter_invoices_for_user(...)` from `marketing/permissions.py`. This is
   where a non-admin user's data is narrowed to their teams.
4. **Aggregation** — the view runs database aggregates (`Sum`, `Count`) to compute totals, monthly
   trends, per-team spend, vendor/campaign breakdowns, and the pie-chart slices. These are real DB
   queries, not spreadsheet math.
5. **Context dict** — the view builds a Python dict (`context`) of everything the template needs.
6. **Template rendering** — `render(request, "marketing/dashboard.html", context)` fills the HTML.
   A **context processor** (`marketing/context_processors.py`) also injects language/direction
   variables into *every* template automatically.
7. **Response** — HTML goes back to the browser. Chart.js draws the pie from JSON embedded via
   Django's `json_script`.

This same shape (route → view → permission filter → queryset/aggregate → template) repeats for
invoices, vendors, campaigns, budgets, etc.

---

## 5. Directory map (what each important file does)

```text
config/
  settings.py        Project configuration (env-driven). DB switch, security, logging, apps.
  urls.py            Top-level URL routes; includes the marketing app's URLs.
  wsgi.py            Entry point gunicorn serves in production.

marketing/                         The single app that holds all the business logic.
  models.py          The data model: Team, Vendor, Campaign, Invoice, BudgetLine,
                     InvoiceAttachment, UserTeamAccess, InvoiceStatusHistory, TeamAlias,
                     plus enums (Role, PaymentStage, CostBucket, AttachmentType) and
                     normalize_name().
  views.py           One function per page. Filters + aggregates + renders.
  urls.py            Path → view mapping for the app.
  forms.py           Invoice form, status form, upload form, user-access form, plus
                     apply_ui_language() that translates labels/choices.
  permissions.py     The RBAC brain: get_user_scope() + filter_*_for_user() + can_*() checks.
  context_processors.py  Injects ui_lang / direction / number locale into all templates.
  translations.py    English→Persian dictionary used by the {% t %} template tag.
  jalali.py          Gregorian↔Jalali (Persian) calendar conversion for monthly grouping.
  admin.py           Registers models in Django's built-in /admin/ (fallback maintenance UI).
  importers/excel.py The Excel importer: read mapping, normalize, alias teams, canonicalize
                     campaign names, idempotent upsert, raw-row traceability.
  management/commands/   CLI commands: import_marketing_excel, seed_auth_groups,
                         bootstrap_dev_admin (the make targets call these).
  templatetags/marketing_format.py  Custom template tags/filters: {% t %} (translate),
                     {% form_errors %}, money/number formatting.
  migrations/        Versioned schema + data migrations (incl. team aliases, campaign canonicalize).
  tests/             pytest tests for permissions, the importer, and frontend views.

templates/marketing/   The HTML. base.html is the shell (nav, styles, language toggle,
                       Persian-digit script); the rest extend it.

docs/                  All the written docs (specs, run guide, deployment, this file, etc.).
```

A file-by-file reference also lives in `docs/PROJECT_FILE_REFERENCE.md`.

---

## 6. Key concepts, explained against your background

### 6.1 Models & migrations (≈ SQLAlchemy + Alembic)

A model class maps to a table. Example shape:

```python
class Invoice(TimestampedModel):
    invoice_number = models.CharField(max_length=64)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="invoices")
    amount = models.DecimalField(max_digits=18, decimal_places=2)  # money = Decimal, never float
    payment_stage = models.CharField(max_length=24, choices=PaymentStage.choices)
```

- `ForeignKey` is a relationship (like SQLAlchemy `relationship`/`ForeignKey`). `related_name`
  gives you the reverse accessor (`vendor.invoices.all()`).
- After editing models you run `makemigrations` (generates a migration file) then `migrate`
  (applies it) — exactly the Alembic autogenerate/upgrade rhythm. `make migrate` does the second.
- **Money is always `Decimal`**, never `float`, to avoid rounding errors.

### 6.2 QuerySets are lazy iterators (your Iterator notebook applies directly)

`Invoice.objects.filter(payment_stage="PAID")` does **not** hit the database. It builds a query
object. The SQL runs only when you iterate, slice with a bound, call `list()`, `.count()`, etc.
That laziness is why permission filtering composes cleanly:

```python
qs = Invoice.objects.all()              # nothing yet
qs = filter_invoices_for_user(qs, user) # adds WHERE clauses, still nothing
rows = qs.order_by("-amount")[:10]      # NOW one SQL query runs
```

Aggregates like `qs.aggregate(total=Sum("amount"))` and `qs.values("team__name").annotate(...)`
push the math into the database (think `GROUP BY`), which is how the charts are built.

### 6.3 Enums via `TextChoices` (your Enum notebook)

```python
class PaymentStage(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PAID = "PAID", "Paid"
    # ...
```

The first value is what's stored in the DB; the second is the human label. You compare with
`invoice.payment_stage == PaymentStage.PAID`. `Role` and `CostBucket` work the same way.

### 6.4 Decorators on views (your Decorators notebook)

```python
@login_required          # redirect anonymous users to login
def dashboard(request):
    ...

@require_POST            # only allow POST (e.g. changing a payment stage)
def invoice_stage_update(request, pk):
    ...
```

These are ordinary decorators that wrap the view function and short-circuit the request when a
condition isn't met — same pattern as the decorators you practiced, just applied to `request`.

### 6.5 The importer (the most "algorithmic" part)

`marketing/importers/excel.py` is worth reading top-to-bottom. It:

- **Reads a mapping file** (`docs/discovery/column_mapping.yml`) so column names can change in
  Excel without rewriting code.
- **Normalizes** text with `normalize_name()` (Unicode NFKC, Arabic→Persian letter fixes,
  casefold) so "same thing written two ways" collapses to one key.
- **Resolves team aliases** via the `TeamAlias` table (e.g. "Operation & Analysis" → "Ops &
  Analytics") so reports don't fragment.
- **Canonicalizes free text** like campaign names ("on going" → "Ongoing").
- **Is idempotent**: re-running updates existing rows (matched by invoice number + vendor) instead
  of duplicating them. You can preview with a **dry run** before committing.
- **Never silently drops rows**: every skipped row is reported with a reason.
- **Keeps the raw row** as JSON on each record for traceability.

### 6.6 Permissions / RBAC (the security core)

`marketing/permissions.py` turns a user's `UserTeamAccess` rows into a `UserScope` (a frozen
dataclass), then every list/report/export is filtered through `filter_*_for_user(...)`. Admins
bypass everything. The full rules and a capability matrix are in **`docs/ACCESS_BY_ROLE.md`** —
read that next if you care about who-can-see-what.

The important principle: **the UI hiding a button is not security**; the queryset filter is. Buttons
are hidden for UX, but the server still refuses unauthorized actions.

### 6.7 Bilingual UI (how FA/EN works)

There are four moving parts:

1. `context_processors.py` reads the chosen language from the session and exposes `ui_lang`,
   text direction (`rtl`/`ltr`), and number locale to every template.
2. `translations.py` is a plain `{English: Persian}` dict.
3. The `{% t "Some text" %}` template tag (in `templatetags/marketing_format.py`) looks the string
   up. Forms get the same treatment via `apply_ui_language()` (labels + dropdown choices).
4. `jalali.py` converts dates to the Persian calendar for monthly grouping; in Persian mode a small
   JS snippet in `base.html` renders displayed digits as Persian (form inputs stay Latin so
   submitted data is unaffected).

This is a deliberately lightweight alternative to Django's full `gettext`/`.po` machinery.

### 6.8 Settings & production (env-driven config)

`config/settings.py` reads everything from environment variables and **degrades gracefully**:

- No `DATABASE_URL` → local SQLite. With one → PostgreSQL (only then is `dj_database_url`
  imported). This is a nice pattern: optional dependencies imported lazily inside an `if`/`try`.
- WhiteNoise (static files) and the security headers only switch on when their package is installed
  / when `DEBUG=False`. So dev stays simple, prod gets hardened.
- Deployment specifics live in `docs/DEPLOYMENT_AWS.md`.

---

## 7. Run it and poke at it yourself

```bash
make setup        # install deps, migrate DB, seed auth groups
make dev-admin    # create local admin -> admin / admin12345 (dev only)
make import       # load the Excel workbook into the DB
make dev          # run with auto-reload, then open http://127.0.0.1:8000/login/
make check        # Django checks + tests + ruff
make shell        # a Python REPL with Django loaded — great for exploring
```

Things to try in `make shell` (this is the fastest way to *feel* the ORM):

```python
from marketing.models import Invoice, Team
Invoice.objects.count()
Invoice.objects.filter(payment_stage="PAID").count()
from django.db.models import Sum
Invoice.objects.values("team__name").annotate(total=Sum("amount")).order_by("-total")
```

Print the SQL a queryset will run (ties back to your SQLAlchemy `echo=True` habit):

```python
print(Invoice.objects.filter(payment_stage="PAID").query)
```

---

## 8. Suggested reading order (to build the full picture)

1. `marketing/models.py` — the vocabulary of the whole app.
2. `marketing/views.py: dashboard` — see a full view end-to-end.
3. `marketing/permissions.py` — how data gets narrowed per user.
4. `marketing/importers/excel.py` — the most logic-dense file.
5. `templates/marketing/base.html` + `dashboard.html` — how it's displayed.
6. `docs/ACCESS_BY_ROLE.md`, `docs/DATA_MODEL.md`, `docs/DEPLOYMENT_AWS.md` — deeper dives.

---

## 9. Mini glossary (Django terms you'll hit)

- **App** — a self-contained feature package (here: `marketing`). A project can have many; this one
  keeps it to one for simplicity.
- **Model** — a Python class mapped to a DB table.
- **QuerySet** — a lazy, chainable database query (`Model.objects.filter(...)`).
- **Migration** — a versioned schema/data change file under `migrations/`.
- **View** — a function that takes a `request` and returns a `response` (often rendered HTML).
- **Template** — an HTML file with `{{ }}`/`{% %}` placeholders.
- **Context** — the dict of data a view hands to a template.
- **Context processor** — a function that adds variables to *every* template's context.
- **Middleware** — layers that wrap every request/response (auth, sessions, security, WhiteNoise).
- **Form** — declares fields + validation; renders inputs and cleans/validates submitted data.
- **Management command** — a CLI subcommand of `manage.py` (the `make` targets call these).
- **Superuser** — the all-powerful account; in this app, equivalent to the Admin role.
```
