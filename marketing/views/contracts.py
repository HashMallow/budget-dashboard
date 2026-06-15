from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .core import (
    filter_contract_queryset,
    forbidden,
    get_ui_lang,
    visible_contract_queryset,
    visible_team_queryset,
)
from ..forms import (
    ContractAttachmentForm,
    ContractForm,
    ContractStageForm,
)
from ..models import (
    ContractStage,
)
from ..permissions import (
    can_edit_contract,
    can_upload_contract_file,
    user_can_create_contract,
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


def contract_list(request):
    base_queryset = visible_contract_queryset(request)
    queryset, filters = filter_contract_queryset(request, base_queryset)
    sort = parse_sort(
        request,
        allowed=CONTRACT_SORT_FIELDS,
        default_field="end",
        default_dir="asc",
        default_dirs=CONTRACT_SORT_DEFAULTS,
    )
    queryset = apply_ordering(
        queryset,
        sort,
        fields=CONTRACT_SORT_FIELDS,
        default_field="end",
        inverted={"days"},
        tiebreaker="id",
    )

    today = timezone.now().date()
    summary = {
        "total": base_queryset.count(),
        "active": base_queryset.filter(stage=ContractStage.SIGNED).count(),
        "in_legal": base_queryset.filter(
            stage__in=[
                ContractStage.INTERNAL_LEGAL_REVIEW,
                ContractStage.SENT_TO_COUNTERPARTY,
                ContractStage.COUNTERPARTY_REVIEW,
                ContractStage.NEGOTIATION,
            ]
        ).count(),
        "expiring_soon": base_queryset.filter(
            end_date__gte=today,
            end_date__lte=today + timedelta(days=30),
        ).count(),
        "expired": base_queryset.filter(end_date__lt=today).exclude(stage=ContractStage.CANCELLED).count(),
    }

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "page_obj": page_obj,
        "filters": filters,
        "teams": visible_team_queryset(request),
        "contract_stages": ContractStage.choices,
        "summary": summary,
        "can_create_contract": user_can_create_contract(request.user),
        "table_sort": sort,
        "table_sort_defaults": CONTRACT_SORT_DEFAULTS,
    }
    return render(request, "marketing/contracts/list.html", context)


def contract_detail(request, pk: int):
    contract = get_object_or_404(visible_contract_queryset(request), pk=pk)
    stage_form = ContractStageForm(contract=contract, ui_lang=get_ui_lang(request))
    attachment_form = ContractAttachmentForm(ui_lang=get_ui_lang(request))
    context = {
        "contract": contract,
        "stage_form": stage_form,
        "attachment_form": attachment_form,
        "can_edit": can_edit_contract(request.user, contract),
        "can_upload": can_upload_contract_file(request.user, contract),
    }
    return render(request, "marketing/contracts/detail.html", context)


def contract_create(request):
    if not user_can_create_contract(request.user):
        return forbidden()
    if request.method == "POST":
        form = ContractForm(request.POST, user=request.user, ui_lang=get_ui_lang(request))
        if form.is_valid():
            contract = form.save()
            messages.success(request, "Contract saved.")
            return redirect("marketing:contract_detail", pk=contract.pk)
    else:
        form = ContractForm(user=request.user, ui_lang=get_ui_lang(request))
    return render(request, "marketing/contracts/form.html", {"form": form, "mode": "create"})


def contract_edit(request, pk: int):
    contract = get_object_or_404(visible_contract_queryset(request), pk=pk)
    if not can_edit_contract(request.user, contract):
        return forbidden()
    if request.method == "POST":
        form = ContractForm(request.POST, user=request.user, instance=contract, ui_lang=get_ui_lang(request))
        if form.is_valid():
            contract = form.save()
            messages.success(request, "Contract updated.")
            return redirect("marketing:contract_detail", pk=contract.pk)
    else:
        form = ContractForm(user=request.user, instance=contract, ui_lang=get_ui_lang(request))
    return render(request, "marketing/contracts/form.html", {"form": form, "contract": contract, "mode": "edit"})


def contract_stage_update(request, pk: int):
    contract = get_object_or_404(visible_contract_queryset(request), pk=pk)
    if not can_edit_contract(request.user, contract):
        return forbidden()
    form = ContractStageForm(request.POST, contract=contract, ui_lang=get_ui_lang(request))
    if form.is_valid():
        contract.set_stage(
            form.cleaned_data["stage"],
            changed_by=request.user,
            note=form.cleaned_data.get("note", ""),
        )
        messages.success(request, "Contract stage updated.")
    else:
        messages.error(request, "Invalid contract stage.")
    return redirect("marketing:contract_detail", pk=contract.pk)


def contract_attachment_upload(request, pk: int):
    contract = get_object_or_404(visible_contract_queryset(request), pk=pk)
    if not can_upload_contract_file(request.user, contract):
        return forbidden("You are not allowed to upload documents for this contract.")
    form = ContractAttachmentForm(request.POST, request.FILES, ui_lang=get_ui_lang(request))
    if form.is_valid():
        attachment = form.save(commit=False)
        attachment.contract = contract
        attachment.uploaded_by = request.user
        attachment.save()
        messages.success(request, "Document uploaded.")
    else:
        messages.error(request, "Upload failed. Check the file or your permissions.")
    return redirect("marketing:contract_detail", pk=contract.pk)
