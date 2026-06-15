from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from marketing.forms import (
    CampaignReferenceForm,
    RequesterForm,
    SpendCategoryForm,
    SubTeamForm,
    VendorReferenceForm,
    apply_ui_language,
)
from marketing.models import Campaign, Requester, SpendCategory, SubTeam, Team, Vendor
from marketing.permissions import user_has_admin_access
from marketing.views import get_ui_lang

_ENTITY_LABELS = {
    "vendor": "Vendor",
    "category": "Spend category",
    "subteam": "Sub-team",
    "requester": "Requester",
    "campaign": "Campaign",
}
_ENTITY_LIST_URLS = {
    "vendor": "marketing:vendor_reference_list",
    "category": "marketing:category_reference_list",
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
