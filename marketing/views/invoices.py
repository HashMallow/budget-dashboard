from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from ..business_section import distinct_business_sections
from .core import (
    distinct_jalali_years,
    filter_invoice_queryset,
    forbidden,
    get_ui_lang,
    visible_invoice_queryset,
    visible_team_queryset,
)
from ..forms import (
    InvoiceAttachmentForm,
    InvoiceForm,
    InvoiceStatusForm,
    user_can_create_invoice,
)
from ..models import (
    CostBucket,
    InvoiceAttachment,
    PaymentStage,
)
from ..permissions import (
    can_edit_invoice,
    can_export,
    can_view_invoice,
)
from ..table_sort import apply_ordering, parse_sort

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
    "entered": "created_at",
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
    "entered": "desc",
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


def invoice_list(request):
    queryset, filters = filter_invoice_queryset(request, visible_invoice_queryset(request))
    sort = parse_sort(
        request,
        allowed=INVOICE_SORT_FIELDS,
        default_field="entered",
        default_dir="desc",
        default_dirs=INVOICE_SORT_DEFAULTS,
    )
    queryset = apply_ordering(
        queryset,
        sort,
        fields=INVOICE_SORT_FIELDS,
        default_field="entered",
        inverted={"days"},
        tiebreaker="-id",
    )
    paginator = Paginator(queryset, 25)
    scope_queryset = visible_invoice_queryset(request)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "page_obj": page_obj,
        "filters": filters,
        "teams": visible_team_queryset(request),
        "business_sections": distinct_business_sections(scope_queryset),
        "years": distinct_jalali_years(scope_queryset),
        "payment_stages": PaymentStage.choices,
        "cost_buckets": CostBucket.choices,
        "can_create_invoice": user_can_create_invoice(request.user),
        "can_export_data": can_export(request.user),
        "table_sort": sort,
        "table_sort_defaults": INVOICE_SORT_DEFAULTS,
    }
    return render(request, "marketing/invoices/list.html", context)


def invoice_detail(request, pk: int):
    invoice = get_object_or_404(visible_invoice_queryset(request), pk=pk)
    status_form = InvoiceStatusForm(invoice=invoice, ui_lang=get_ui_lang(request))
    attachment_form = InvoiceAttachmentForm(user=request.user, invoice=invoice, ui_lang=get_ui_lang(request))
    context = {
        "invoice": invoice,
        "status_form": status_form,
        "attachment_form": attachment_form,
        "can_edit": can_edit_invoice(request.user, invoice),
        "can_upload": attachment_form.has_allowed_types,
    }
    return render(request, "marketing/invoices/detail.html", context)


def invoice_create(request):
    if not user_can_create_invoice(request.user):
        return forbidden()
    if request.method == "POST":
        form = InvoiceForm(request.POST, user=request.user, ui_lang=get_ui_lang(request))
        if form.is_valid():
            invoice = form.save()
            messages.success(request, "Invoice saved.")
            return redirect("marketing:invoice_detail", pk=invoice.pk)
    else:
        form = InvoiceForm(user=request.user, ui_lang=get_ui_lang(request))
    return render(request, "marketing/invoices/form.html", {"form": form, "mode": "create"})


def invoice_edit(request, pk: int):
    invoice = get_object_or_404(visible_invoice_queryset(request), pk=pk)
    if not can_edit_invoice(request.user, invoice):
        return forbidden()
    if request.method == "POST":
        form = InvoiceForm(request.POST, user=request.user, instance=invoice, ui_lang=get_ui_lang(request))
        if form.is_valid():
            invoice = form.save()
            messages.success(request, "Invoice updated.")
            return redirect("marketing:invoice_detail", pk=invoice.pk)
    else:
        form = InvoiceForm(user=request.user, instance=invoice, ui_lang=get_ui_lang(request))
    return render(request, "marketing/invoices/form.html", {"form": form, "invoice": invoice, "mode": "edit"})


def invoice_stage_update(request, pk: int):
    invoice = get_object_or_404(visible_invoice_queryset(request), pk=pk)
    if not can_edit_invoice(request.user, invoice):
        return forbidden()
    wants_json = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.headers.get(
        "Accept", ""
    ).startswith("application/json")
    form = InvoiceStatusForm(request.POST, invoice=invoice, ui_lang=get_ui_lang(request))
    if form.is_valid():
        invoice.set_payment_stage(
            form.cleaned_data["payment_stage"],
            changed_by=request.user,
            note=form.cleaned_data.get("note", ""),
        )
        if wants_json:
            return JsonResponse({"ok": True, "new_stage": invoice.payment_stage})
        messages.success(request, "Payment stage updated.")
    else:
        if wants_json:
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
        messages.error(request, "Invalid payment stage.")
    return redirect("marketing:invoice_detail", pk=invoice.pk)


def invoice_attachment_upload(request, pk: int):
    invoice = get_object_or_404(visible_invoice_queryset(request), pk=pk)
    form = InvoiceAttachmentForm(
        request.POST,
        request.FILES,
        user=request.user,
        invoice=invoice,
        ui_lang=get_ui_lang(request),
    )
    if not form.has_allowed_types:
        return forbidden("You are not allowed to upload files for this invoice.")
    if form.is_valid():
        attachment = form.save(commit=False)
        attachment.invoice = invoice
        attachment.uploaded_by = request.user
        attachment.save()
        messages.success(request, "File uploaded.")
    else:
        messages.error(request, "Upload failed. Check the file type or your permissions.")
    return redirect("marketing:invoice_detail", pk=invoice.pk)


def invoice_attachment_download(request, pk: int):
    """Serve an invoice file only to users allowed to view its invoice.

    Uploaded invoice images and payment proofs are sensitive financial documents,
    so they must never be reachable through a guessable ``/media/`` URL. Files are
    streamed through this permission-checked view and forced as downloads so an
    uploaded HTML/SVG can never execute in another user's session.
    """
    attachment = get_object_or_404(InvoiceAttachment.objects.select_related("invoice"), pk=pk)
    if not can_view_invoice(request.user, attachment.invoice):
        return forbidden("You are not allowed to view this file.")
    try:
        file_handle = attachment.file.open("rb")
    except FileNotFoundError as exc:
        raise Http404("File not found.") from exc
    response = FileResponse(file_handle, as_attachment=True, filename=Path(attachment.file.name).name)
    response["X-Content-Type-Options"] = "nosniff"
    return response
