from __future__ import annotations

from marketing.money_format import COMPACT, FULL, RIAL, TOMAN, unit_label
from marketing.permissions import can_export

# Catalog of every export link, keyed by a short id. ``title`` is an optional tooltip string.
_EXPORT_LINKS: dict[str, dict[str, str]] = {
    "invoices_excel": {"url": "marketing:export_invoices_excel", "label": "Invoices (Excel)", "icon": "⇩"},
    "invoices_pdf": {"url": "marketing:pdf_export_wizard", "label": "PDF report", "icon": "⎙", "query": "report=invoices"},
    "vendors_excel": {"url": "marketing:export_vendors_excel", "label": "Vendors (Excel)", "icon": "⇩"},
    "vendors_pdf": {"url": "marketing:pdf_export_wizard", "label": "Vendors (PDF)", "icon": "⎙", "query": "report=vendors"},
    "campaigns_excel": {"url": "marketing:export_campaigns_excel", "label": "Campaigns (Excel)", "icon": "⇩"},
    "campaigns_pdf": {"url": "marketing:pdf_export_wizard", "label": "Campaigns (PDF)", "icon": "⎙", "query": "report=campaigns"},
    "contracts_excel": {"url": "marketing:export_contracts_excel", "label": "Contracts (Excel)", "icon": "⇩"},
    "contracts_pdf": {"url": "marketing:pdf_export_wizard", "label": "Contracts (PDF)", "icon": "⎙", "query": "report=contracts"},
    "workbook_excel": {
        "url": "marketing:export_workbook_excel",
        "label": "Workbook (.xlsx)",
        "icon": "⇩",
        "title": "Excel shaped like the source workbook (all sheets)",
    },
    "dashboard_pdf": {"url": "marketing:pdf_export_wizard", "label": "PDF summary", "icon": "⎙", "query": "report=dashboard"},
}

# Only the exports relevant to each page are offered in the topbar (by resolved URL name).
_PAGE_EXPORTS: dict[str, list[str]] = {
    "dashboard": ["dashboard_pdf", "workbook_excel"],
    "invoice_list": ["invoices_excel", "invoices_pdf"],
    "vendor_report": ["vendors_excel", "vendors_pdf"],
    "campaign_report": ["campaigns_excel", "campaigns_pdf"],
    "contract_list": ["contracts_excel", "contracts_pdf"],
    "team_list": ["workbook_excel"],
    "team_dashboard": ["dashboard_pdf", "workbook_excel"],
    "budget_list": ["workbook_excel"],
}


def export_access(request):
    """Expose only the exports relevant to the current page so the topbar isn't a dump of everything.

    base.html renders a single button when there is one relevant export, a compact dropdown when
    there are several, and nothing when the page has no exports (or the user cannot export).
    """
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated and can_export(user)):
        return {"page_exports": []}
    url_name = getattr(getattr(request, "resolver_match", None), "url_name", "")
    keys = _PAGE_EXPORTS.get(url_name, [])
    return {"page_exports": [_EXPORT_LINKS[key] for key in keys if key in _EXPORT_LINKS]}


def display_preferences(request):
    # The UI supports an English/Persian toggle. English is the default and the source
    # language for all static text; Persian is provided via marketing/translations.py.
    # Data values from the Excel workbook (team/vendor/campaign names) are shown as imported.
    ui_lang = request.session.get("ui_lang", "en")
    if ui_lang not in {"fa", "en"}:
        ui_lang = "en"

    money_format = getattr(request, "money_format", request.session.get("money_format", COMPACT))
    if money_format not in {FULL, COMPACT}:
        money_format = COMPACT

    currency_unit = getattr(request, "currency_unit", request.session.get("currency_unit", RIAL))
    if currency_unit not in {RIAL, TOMAN}:
        currency_unit = RIAL

    theme = request.session.get("theme", "light")
    if theme not in {"light", "dark"}:
        theme = "light"

    return {
        "ui_lang": ui_lang,
        "number_locale": "fa" if ui_lang == "fa" else "en",
        "html_lang": "fa" if ui_lang == "fa" else "en",
        "html_dir": "rtl" if ui_lang == "fa" else "ltr",
        "money_format": money_format,
        "currency_unit": currency_unit,
        "currency_label": unit_label(currency_unit, ui_lang),
        "theme": theme,
    }
