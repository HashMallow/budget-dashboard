from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from marketing.forms import (
    BusinessLineForm,
    CampaignReferenceForm,
    InsuranceRateOptionForm,
    RequesterForm,
    SpendCategoryForm,
    SubTeamForm,
    VendorReferenceForm,
    apply_ui_language,
)
from marketing.models import BudgetLine, BusinessLine, Campaign, Contract, InsuranceRateOption, Invoice, Requester, SpendCategory, SubTeam, Team, Vendor
from marketing.permissions import user_has_admin_access
from marketing.views import get_ui_lang

_ENTITY_LABELS = {
    "vendor": "Vendor",
    "category": "Spend category",
    "businessline": "Business line",
    "insurancerate": "Insurance rate",
    "subteam": "Sub-team",
    "requester": "Requester",
    "campaign": "Campaign",
}
_ENTITY_LIST_URLS = {
    "vendor": "marketing:vendor_reference_list",
    "category": "marketing:category_reference_list",
    "businessline": "marketing:businessline_reference_list",
    "insurancerate": "marketing:insurancerate_reference_list",
    "subteam": "marketing:subteam_reference_list",
    "requester": "marketing:requester_reference_list",
    "campaign": "marketing:campaign_reference_list",
}


def _form_context(entity: str, mode: str, form, object=None):
    return {
        "form": form,
        "entity": entity,
        "entity_label": _ENTITY_LABELS[entity],
        "mode": mode,
        "object": object,
        "list_url": reverse(_ENTITY_LIST_URLS[entity]),
    }


def _admin_required(request):
    if not user_has_admin_access(request.user):
        return HttpResponseForbidden("You are not allowed to perform this action.")
    return None


def _reference_form(form_class, request, instance=None):
    if request.method == "POST":
        form = form_class(request.POST, instance=instance)
    else:
        form = form_class(instance=instance)
    apply_ui_language(form, get_ui_lang(request))
    return form


@login_required
def reference_data_home(request):
    denied = _admin_required(request)
    if denied:
        return denied
    counts = {
        "vendors": Vendor.objects.count(),
        "categories": SpendCategory.objects.count(),
        "business_lines": BusinessLine.objects.count(),
        "insurance_rates": InsuranceRateOption.objects.count(),
        "sub_teams": SubTeam.objects.count(),
        "requesters": Requester.objects.count(),
        "campaigns": Campaign.objects.count(),
    }
    return render(request, "marketing/reference/home.html", {"counts": counts})


def _paginated_list(request, queryset, *, template: str, extra_context: dict):
    denied = _admin_required(request)
    if denied:
        return denied
    q = request.GET.get("q", "").strip()
    if q:
        queryset = queryset.filter(name__icontains=q)
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        template,
        {
            "page_obj": page_obj,
            "filters": {"q": q},
            **extra_context,
        },
    )


@login_required
def vendor_reference_list(request):
    return _paginated_list(
        request,
        Vendor.objects.order_by("name"),
        template="marketing/reference/vendor_list.html",
        extra_context={"entity": "vendor"},
    )


@login_required
def vendor_reference_create(request):
    denied = _admin_required(request)
    if denied:
        return denied
    form = _reference_form(VendorReferenceForm, request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vendor saved.")
        return redirect("marketing:vendor_reference_list")
    return render(
        request,
        "marketing/reference/form.html",
        _form_context("vendor", "create", form),
    )


@login_required
def vendor_reference_edit(request, pk: int):
    denied = _admin_required(request)
    if denied:
        return denied
    vendor = get_object_or_404(Vendor, pk=pk)
    form = _reference_form(VendorReferenceForm, request, instance=vendor)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Vendor updated.")
        return redirect("marketing:vendor_reference_list")
    return render(
        request,
        "marketing/reference/form.html",
        _form_context("vendor", "edit", form, vendor),
    )


@login_required
def category_reference_list(request):
    queryset = SpendCategory.objects.select_related().order_by("name")
    active = request.GET.get("active", "").strip()
    if active == "1":
        queryset = queryset.filter(is_active=True)
    elif active == "0":
        queryset = queryset.filter(is_active=False)
    denied = _admin_required(request)
    if denied:
        return denied
    q = request.GET.get("q", "").strip()
    if q:
        queryset = queryset.filter(name__icontains=q)
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "marketing/reference/category_list.html",
        {"page_obj": page_obj, "filters": {"q": q, "active": active}, "entity": "category"},
    )


@login_required
def category_reference_create(request):
    denied = _admin_required(request)
    if denied:
        return denied
    form = _reference_form(SpendCategoryForm, request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category saved.")
        return redirect("marketing:category_reference_list")
    return render(request, "marketing/reference/form.html", _form_context("category", "create", form))


@login_required
def category_reference_edit(request, pk: int):
    denied = _admin_required(request)
    if denied:
        return denied
    category = get_object_or_404(SpendCategory, pk=pk)
    form = _reference_form(SpendCategoryForm, request, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category updated.")
        return redirect("marketing:category_reference_list")
    return render(request, "marketing/reference/form.html", _form_context("category", "edit", form, category))


@login_required
def subteam_reference_list(request):
    queryset = SubTeam.objects.select_related("team").order_by("name")
    active = request.GET.get("active", "").strip()
    if active == "1":
        queryset = queryset.filter(is_active=True)
    elif active == "0":
        queryset = queryset.filter(is_active=False)
    team_id = request.GET.get("team", "").strip()
    if team_id.isdigit():
        queryset = queryset.filter(team_id=int(team_id))
    denied = _admin_required(request)
    if denied:
        return denied
    q = request.GET.get("q", "").strip()
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(team__name__icontains=q))
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "marketing/reference/subteam_list.html",
        {
            "page_obj": page_obj,
            "filters": {"q": q, "active": active, "team": team_id},
            "teams": Team.objects.filter(is_active=True).order_by("name"),
            "entity": "subteam",
        },
    )


@login_required
def subteam_reference_create(request):
    denied = _admin_required(request)
    if denied:
        return denied
    form = _reference_form(SubTeamForm, request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Sub-team saved.")
        return redirect("marketing:subteam_reference_list")
    return render(request, "marketing/reference/form.html", _form_context("subteam", "create", form))


@login_required
def subteam_reference_edit(request, pk: int):
    denied = _admin_required(request)
    if denied:
        return denied
    subteam = get_object_or_404(SubTeam, pk=pk)
    form = _reference_form(SubTeamForm, request, instance=subteam)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Sub-team updated.")
        return redirect("marketing:subteam_reference_list")
    return render(request, "marketing/reference/form.html", _form_context("subteam", "edit", form, subteam))


@login_required
def requester_reference_list(request):
    queryset = Requester.objects.order_by("name")
    active = request.GET.get("active", "").strip()
    if active == "1":
        queryset = queryset.filter(is_active=True)
    elif active == "0":
        queryset = queryset.filter(is_active=False)
    denied = _admin_required(request)
    if denied:
        return denied
    q = request.GET.get("q", "").strip()
    if q:
        queryset = queryset.filter(name__icontains=q)
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "marketing/reference/requester_list.html",
        {"page_obj": page_obj, "filters": {"q": q, "active": active}, "entity": "requester"},
    )


@login_required
def requester_reference_create(request):
    denied = _admin_required(request)
    if denied:
        return denied
    form = _reference_form(RequesterForm, request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Requester saved.")
        return redirect("marketing:requester_reference_list")
    return render(request, "marketing/reference/form.html", _form_context("requester", "create", form))


@login_required
def requester_reference_edit(request, pk: int):
    denied = _admin_required(request)
    if denied:
        return denied
    requester = get_object_or_404(Requester, pk=pk)
    form = _reference_form(RequesterForm, request, instance=requester)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Requester updated.")
        return redirect("marketing:requester_reference_list")
    return render(request, "marketing/reference/form.html", _form_context("requester", "edit", form, requester))


@login_required
def campaign_reference_list(request):
    queryset = Campaign.objects.select_related("team").order_by("-year", "name")
    year = request.GET.get("year", "").strip()
    if year.isdigit():
        queryset = queryset.filter(year=int(year))
    team_id = request.GET.get("team", "").strip()
    if team_id.isdigit():
        queryset = queryset.filter(team_id=int(team_id))
    denied = _admin_required(request)
    if denied:
        return denied
    q = request.GET.get("q", "").strip()
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(team__name__icontains=q))
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    years = Campaign.objects.order_by("-year").values_list("year", flat=True).distinct()
    return render(
        request,
        "marketing/reference/campaign_list.html",
        {
            "page_obj": page_obj,
            "filters": {"q": q, "year": year, "team": team_id},
            "teams": Team.objects.filter(is_active=True).order_by("name"),
            "years": years,
            "entity": "campaign",
        },
    )


@login_required
def campaign_reference_create(request):
    denied = _admin_required(request)
    if denied:
        return denied
    form = _reference_form(CampaignReferenceForm, request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Campaign saved.")
        return redirect("marketing:campaign_reference_list")
    return render(request, "marketing/reference/form.html", _form_context("campaign", "create", form))


@login_required
def campaign_reference_edit(request, pk: int):
    denied = _admin_required(request)
    if denied:
        return denied
    campaign = get_object_or_404(Campaign, pk=pk)
    form = _reference_form(CampaignReferenceForm, request, instance=campaign)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Campaign updated.")
        return redirect("marketing:campaign_reference_list")
    return render(request, "marketing/reference/form.html", _form_context("campaign", "edit", form, campaign))


@login_required
def businessline_reference_list(request):
    queryset = BusinessLine.objects.order_by("name")
    active = request.GET.get("active", "").strip()
    if active == "1":
        queryset = queryset.filter(is_active=True)
    elif active == "0":
        queryset = queryset.filter(is_active=False)
    denied = _admin_required(request)
    if denied:
        return denied
    q = request.GET.get("q", "").strip()
    if q:
        queryset = queryset.filter(name__icontains=q)
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "marketing/reference/businessline_list.html",
        {"page_obj": page_obj, "filters": {"q": q, "active": active}, "entity": "businessline"},
    )


@login_required
def businessline_reference_create(request):
    denied = _admin_required(request)
    if denied:
        return denied
    form = _reference_form(BusinessLineForm, request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Business line saved.")
        return redirect("marketing:businessline_reference_list")
    return render(request, "marketing/reference/form.html", _form_context("businessline", "create", form))


@login_required
def businessline_reference_edit(request, pk: int):
    denied = _admin_required(request)
    if denied:
        return denied
    line = get_object_or_404(BusinessLine, pk=pk)
    form = _reference_form(BusinessLineForm, request, instance=line)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Business line updated.")
        return redirect("marketing:businessline_reference_list")
    return render(request, "marketing/reference/form.html", _form_context("businessline", "edit", form, line))


@login_required
def insurancerate_reference_list(request):
    denied = _admin_required(request)
    if denied:
        return denied
    queryset = InsuranceRateOption.objects.order_by("percent")
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "marketing/reference/insurancerate_list.html",
        {"page_obj": page_obj, "filters": {}, "entity": "insurancerate"},
    )


@login_required
def insurancerate_reference_create(request):
    denied = _admin_required(request)
    if denied:
        return denied
    form = _reference_form(InsuranceRateOptionForm, request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Insurance rate saved.")
        return redirect("marketing:insurancerate_reference_list")
    return render(request, "marketing/reference/form.html", _form_context("insurancerate", "create", form))


@login_required
def insurancerate_reference_edit(request, pk: int):
    denied = _admin_required(request)
    if denied:
        return denied
    rate = get_object_or_404(InsuranceRateOption, pk=pk)
    form = _reference_form(InsuranceRateOptionForm, request, instance=rate)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Insurance rate updated.")
        return redirect("marketing:insurancerate_reference_list")
    return render(request, "marketing/reference/form.html", _form_context("insurancerate", "edit", form, rate))


@login_required
def vendor_merge(request):
    denied = _admin_required(request)
    if denied:
        return denied

    vendors = (
        Vendor.objects.annotate(
            invoice_count=Count("invoices", distinct=True),
            contract_count=Count("contracts", distinct=True),
        )
        .order_by("name")
    )

    if request.method == "POST":
        source_ids = [int(pk) for pk in request.POST.getlist("vendor_ids") if pk.isdigit()]
        target_id = request.POST.get("target_id", "").strip()
        if request.POST.get("confirm") == "1" and target_id.isdigit():
            target = get_object_or_404(Vendor, pk=int(target_id))
            duplicates = [pk for pk in source_ids if pk != target.pk]
            if not duplicates:
                messages.error(request, "Select at least one duplicate vendor to merge.")
                return redirect("marketing:vendor_merge")
            with transaction.atomic():
                invoice_count = Invoice.objects.filter(vendor_id__in=duplicates).update(vendor=target)
                contract_count = Contract.objects.filter(vendor_id__in=duplicates).update(vendor=target)
                removed = Vendor.objects.filter(pk__in=duplicates).delete()[0]
            messages.success(
                request,
                f"Merged {removed} vendor(s): {invoice_count} invoices and {contract_count} contracts reassigned to {target.name}.",
            )
            return redirect("marketing:vendor_reference_list")

        if len(source_ids) < 2:
            messages.error(request, "Select at least two vendors to merge.")
            return redirect("marketing:vendor_merge")

        target_candidates = vendors.filter(pk__in=source_ids)
        preview = {
            "sources": list(target_candidates),
            "invoice_total": sum(v.invoice_count for v in target_candidates),
            "contract_total": sum(v.contract_count for v in target_candidates),
            "source_ids": source_ids,
        }
        return render(request, "marketing/reference/vendor_merge.html", {"vendors": vendors, "preview": preview})

    return render(request, "marketing/reference/vendor_merge.html", {"vendors": vendors, "preview": None})


@login_required
def campaign_merge(request):
    denied = _admin_required(request)
    if denied:
        return denied

    campaigns = (
        Campaign.objects.select_related("team")
        .annotate(
            invoice_count=Count("invoices", distinct=True),
            budget_count=Count("budget_lines", distinct=True),
        )
        .order_by("-year", "name")
    )

    if request.method == "POST":
        source_ids = [int(pk) for pk in request.POST.getlist("campaign_ids") if pk.isdigit()]
        target_id = request.POST.get("target_id", "").strip()
        if request.POST.get("confirm") == "1" and target_id.isdigit():
            target = get_object_or_404(Campaign, pk=int(target_id))
            duplicates = [pk for pk in source_ids if pk != target.pk]
            if not duplicates:
                messages.error(request, "Select at least one duplicate campaign to merge.")
                return redirect("marketing:campaign_merge")
            with transaction.atomic():
                invoice_count = Invoice.objects.filter(campaign_id__in=duplicates).update(campaign=target)
                budget_count = BudgetLine.objects.filter(campaign_id__in=duplicates).update(campaign=target)
                removed = Campaign.objects.filter(pk__in=duplicates).delete()[0]
            messages.success(
                request,
                f"Merged {removed} campaign(s): {invoice_count} invoices and {budget_count} budget lines reassigned to {target.name}.",
            )
            return redirect("marketing:campaign_reference_list")

        if len(source_ids) < 2:
            messages.error(request, "Select at least two campaigns to merge.")
            return redirect("marketing:campaign_merge")

        target_candidates = campaigns.filter(pk__in=source_ids)
        preview = {
            "sources": list(target_candidates),
            "invoice_total": sum(c.invoice_count for c in target_candidates),
            "budget_total": sum(c.budget_count for c in target_candidates),
            "source_ids": source_ids,
        }
        return render(request, "marketing/reference/campaign_merge.html", {"campaigns": campaigns, "preview": preview})

    return render(request, "marketing/reference/campaign_merge.html", {"campaigns": campaigns, "preview": None})
