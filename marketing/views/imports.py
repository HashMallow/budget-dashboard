from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render

from .core import (
    forbidden,
    get_ui_lang,
)
from ..forms import (
    ExcelImportUploadForm,
)
from ..permissions import (
    can_export,
    can_import,
)
from ..reference_data import load_workbook_data, workbook_load_summary

User = get_user_model()
ZERO = Decimal("0")
_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#ca8a04"/><stop offset="1" stop-color="#facc15"/>'
    "</linearGradient></defs>"
    '<rect width="64" height="64" rx="14" fill="url(#g)"/>'
    '<rect x="18" y="14" width="28" height="36" rx="3" fill="#fff"/>'
    '<circle cx="24" cy="20" r="3" fill="#2563eb"/>'
    '<line x1="22" y1="26" x2="42" y2="26" stroke="#2563eb" stroke-width="2" stroke-linecap="round"/>'
    '<line x1="22" y1="32" x2="42" y2="32" stroke="#2563eb" stroke-width="2" stroke-linecap="round"/>'
    '<line x1="22" y1="38" x2="38" y2="38" stroke="#2563eb" stroke-width="2" stroke-linecap="round"/>'
    "</svg>"
)
INVOICE_SORT_FIELDS = {
    "number": "invoice_number",
    "vendor": "vendor__name",
    "team": "team__name",
    "category": "category",
    "date": "invoice_date",
    "amount": "amount",
    "stage": "payment_stage",
    "days": "stage_changed_at",
}
INVOICE_SORT_DEFAULTS = {
    "number": "asc",
    "vendor": "asc",
    "team": "asc",
    "category": "asc",
    "date": "desc",
    "amount": "desc",
    "stage": "asc",
    "days": "desc",
}
VENDOR_SORT_KEYS = {
    "vendor": lambda row: row["vendor"].name.lower(),
    "invoices": lambda row: row["invoice_count"],
    "amount": lambda row: row["total"],
}
VENDOR_SORT_DEFAULTS = {"vendor": "asc", "invoices": "desc", "amount": "desc"}
CAMPAIGN_SORT_FIELDS = {
    "campaign": "campaign__name",
    "year": "campaign__year",
    "team": "campaign__team__name",
    "invoices": "invoice_count",
    "amount": "total",
}
CAMPAIGN_SORT_DEFAULTS = {
    "campaign": "asc",
    "year": "desc",
    "team": "asc",
    "invoices": "desc",
    "amount": "desc",
}
TEAM_SORT_KEYS = {
    "team": lambda row: row["team"].name.lower(),
    "invoices": lambda row: row["invoice_count"],
    "amount": lambda row: row["total_spend"],
}
TEAM_SORT_DEFAULTS = {"team": "asc", "invoices": "desc", "amount": "desc"}
BUDGET_SORT_FIELDS = {
    "year": "year",
    "month": "month",
    "team": "team__name",
    "campaign": "campaign__name",
    "category": "category",
    "amount": "planned_amount",
}
BUDGET_SORT_DEFAULTS = {
    "year": "desc",
    "month": "asc",
    "team": "asc",
    "campaign": "asc",
    "category": "asc",
    "amount": "desc",
}
BUDGET_PIVOT_SORT_KEYS = {
    "team": lambda row: row["team"].lower(),
    "category": lambda row: row["category"].lower(),
    "total": lambda row: row["total"],
}
CONTRACT_SORT_FIELDS = {
    "title": "title",
    "vendor": "vendor__name",
    "team": "team__name",
    "stage": "stage",
    "end": "end_date",
    "days": "stage_changed_at",
}
CONTRACT_SORT_DEFAULTS = {
    "title": "asc",
    "vendor": "asc",
    "team": "asc",
    "stage": "asc",
    "end": "asc",
    "days": "desc",
}


def import_workbook(request):
    if not can_import(request.user):
        return forbidden()

    form = ExcelImportUploadForm(ui_lang=get_ui_lang(request))
    result = None
    summary = None
    pending_path = request.session.get("pending_import_path")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "confirm":
            if not pending_path:
                messages.error(request, "There is no file ready to import.")
            else:
                load_result = load_workbook_data(pending_path, dry_run=False)
                result = load_result.import_result
                summary = workbook_load_summary(load_result)
                messages.success(request, "Excel data and reference lookups imported into the database.")
                request.session.pop("pending_import_path", None)
                pending_path = None
        else:
            form = ExcelImportUploadForm(request.POST, request.FILES, ui_lang=get_ui_lang(request))
            if form.is_valid():
                storage = FileSystemStorage(location=Path(settings.MEDIA_ROOT) / "imports")
                filename = f"{uuid4().hex}.xlsx"
                stored_name = storage.save(filename, form.cleaned_data["workbook"])
                workbook_path = storage.path(stored_name)
                load_result = load_workbook_data(workbook_path, dry_run=True)
                result = load_result.import_result
                summary = workbook_load_summary(load_result)
                request.session["pending_import_path"] = workbook_path
                pending_path = workbook_path
                messages.info(request, "Dry-run complete. If the result looks correct, confirm the import.")

    context = {
        "form": form,
        "result": result,
        "summary": summary,
        "pending_path": pending_path,
        "skipped_preview": result.skipped_rows[:20] if result else [],
        "can_export_data": can_export(request.user),
    }
    return render(request, "marketing/imports/upload.html", context)
