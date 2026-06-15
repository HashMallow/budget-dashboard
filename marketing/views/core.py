from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.utils import timezone

from ..cost_buckets import exclude_pseudo_teams
from ..jalali import JALALI_MONTHS, gregorian_to_jalali, jalali_year_bounds, today_jalali
from ..models import (
    Contract,
    Invoice,
    Team,
)
from ..permissions import (
    filter_contracts_for_user,
    filter_invoices_for_user,
    filter_teams_for_user,
)
from ..reports.pdf_fonts import PdfLocale

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


def get_ui_lang(request) -> str:
    ui_lang = request.session.get("ui_lang", "en")
    return ui_lang if ui_lang in {"fa", "en"} else "en"


def pdf_locale_for_request(request) -> PdfLocale:
    unit = getattr(request, "currency_unit", "rial")
    return PdfLocale(lang=get_ui_lang(request), unit=unit)


def get_months(request) -> list[tuple[int, str]]:
    """Persian (Jalali) month labels, localized to the active UI language."""
    if request.session.get("ui_lang", "en") == "fa":
        return [(number, persian) for number, persian, _latin in JALALI_MONTHS]
    return [(number, latin) for number, _persian, latin in JALALI_MONTHS]


def monthly_trend_window(selected_year: str) -> tuple[int, int, int]:
    """Window (end_year, end_month, count) for the monthly trend chart.

    Avoids showing future months: the current Jalali year stops at the current month, and the
    default ("all years") view is a trailing 12 months. A specific past year shows its 12 months.
    """
    current_year, current_month, _day = today_jalali()
    if selected_year.isdigit():
        year = int(selected_year)
        end_month = current_month if year == current_year else 12
        return year, end_month, end_month
    return current_year, current_month, 12


def filter_by_jalali_year(queryset, year: str):
    """Filter invoices by a Jalali year using the matching Gregorian date range."""
    if year and year.isdigit():
        start, end = jalali_year_bounds(int(year))
        return queryset.filter(invoice_date__range=(start, end))
    return queryset


def distinct_jalali_years(queryset) -> list[int]:
    # Small datasets: convert each invoice date. Revisit with a stored Jalali year
    # column if invoice volume grows large.
    years = {
        gregorian_to_jalali(value.year, value.month, value.day)[0]
        for value in queryset.values_list("invoice_date", flat=True)
        if value
    }
    return sorted(years, reverse=True)


def forbidden(message: str = "You are not allowed to perform this action.") -> HttpResponseForbidden:
    return HttpResponseForbidden(message)


def visible_invoice_queryset(request):
    queryset = Invoice.objects.select_related("vendor", "team", "campaign").order_by("-invoice_date", "-id")
    return filter_invoices_for_user(queryset, request.user)


def visible_team_queryset(request):
    teams = exclude_pseudo_teams(Team.objects.filter(is_active=True))
    return filter_teams_for_user(teams, request.user).order_by("name")


def visible_contract_queryset(request):
    queryset = Contract.objects.select_related("vendor", "team").order_by("end_date", "id")
    return filter_contracts_for_user(queryset, request.user)


def filter_invoice_queryset(request, queryset):
    filters = {
        "q": request.GET.get("q", "").strip(),
        "year": request.GET.get("year", "").strip(),
        "team": request.GET.get("team", "").strip(),
        "stage": request.GET.get("stage", "").strip(),
        "bucket": request.GET.get("bucket", "").strip(),
        "business_section": request.GET.get("business_section", "").strip(),
    }

    if filters["q"]:
        queryset = queryset.filter(
            Q(invoice_number__icontains=filters["q"])
            | Q(vendor__name__icontains=filters["q"])
            | Q(campaign__name__icontains=filters["q"])
            | Q(category__icontains=filters["q"])
            | Q(description__icontains=filters["q"])
            | Q(business_section__icontains=filters["q"])
        )
    if filters["year"].isdigit():
        queryset = filter_by_jalali_year(queryset, filters["year"])
    if filters["team"].isdigit():
        queryset = queryset.filter(team_id=int(filters["team"]))
    if filters["stage"]:
        queryset = queryset.filter(payment_stage=filters["stage"])
    if filters["bucket"]:
        queryset = queryset.filter(cost_bucket=filters["bucket"])
    if filters["business_section"]:
        queryset = queryset.filter(business_section=filters["business_section"])
    return queryset, filters


def filter_contract_queryset(request, queryset):
    filters = {
        "q": request.GET.get("q", "").strip(),
        "team": request.GET.get("team", "").strip(),
        "stage": request.GET.get("stage", "").strip(),
        "expiring": request.GET.get("expiring", "").strip(),
    }
    if filters["q"]:
        queryset = queryset.filter(
            Q(title__icontains=filters["q"])
            | Q(contract_number__icontains=filters["q"])
            | Q(vendor__name__icontains=filters["q"])
            | Q(counterparty_contact__icontains=filters["q"])
            | Q(description__icontains=filters["q"])
        )
    if filters["team"].isdigit():
        queryset = queryset.filter(team_id=int(filters["team"]))
    if filters["stage"]:
        queryset = queryset.filter(stage=filters["stage"])
    if filters["expiring"] == "1":
        today = timezone.now().date()
        queryset = queryset.filter(end_date__gte=today, end_date__lte=today + timedelta(days=30))
    return queryset, filters
