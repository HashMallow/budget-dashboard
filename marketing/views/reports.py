from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, render

from ..analytics import (
    decimal_sum,
    percent,
    vendor_grouped_rows,
)
from .core import (
    distinct_jalali_years,
    filter_invoice_queryset,
    forbidden,
    get_months,
    visible_contract_queryset,
    visible_invoice_queryset,
    visible_team_queryset,
)
from ..jalali import gregorian_to_jalali
from ..models import (
    Contract,
    CostBucket,
    PaymentStage,
    Vendor,
)
from ..permissions import (
    can_export,
)
from ..table_sort import apply_ordering, parse_sort, sort_rows

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


def vendor_report(request):
    queryset, filters = filter_invoice_queryset(request, visible_invoice_queryset(request))
    sort = parse_sort(
        request,
        allowed=VENDOR_SORT_KEYS,
        default_field="amount",
        default_dir="desc",
        default_dirs=VENDOR_SORT_DEFAULTS,
    )
    vendor_rows = sort_rows(
        vendor_grouped_rows(queryset),
        sort,
        keys=VENDOR_SORT_KEYS,
        default_field="amount",
    )

    context = {
        "vendor_rows": vendor_rows,
        "filters": filters,
        "teams": visible_team_queryset(request),
        "payment_stages": PaymentStage.choices,
        "cost_buckets": CostBucket.choices,
        "can_export_data": can_export(request.user),
        "table_sort": sort,
        "table_sort_defaults": VENDOR_SORT_DEFAULTS,
    }
    return render(request, "marketing/vendors/report.html", context)


def vendor_detail(request, pk: int):
    vendor = get_object_or_404(Vendor, pk=pk)
    invoices = visible_invoice_queryset(request).filter(vendor=vendor).order_by("-created_at")
    if not invoices.exists():
        return forbidden("You are not allowed to view this vendor.")

    contracts = visible_contract_queryset(request).filter(vendor=vendor).order_by("-end_date")
    total_spend = decimal_sum(invoices)
    total_action = decimal_sum(invoices, "action_cost_amount")
    total_tax = decimal_sum(invoices, "tax_amount")
    total_paid = decimal_sum(invoices, "paid_amount")

    context = {
        "vendor": vendor,
        "invoices": invoices[:50],
        "invoice_count": invoices.count(),
        "contracts": contracts,
        "total_spend": total_spend,
        "total_action": total_action,
        "total_tax": total_tax,
        "total_paid": total_paid,
    }
    return render(request, "marketing/vendors/detail.html", context)


def campaign_report(request):
    months = get_months(request)
    queryset, filters = filter_invoice_queryset(request, visible_invoice_queryset(request))
    sort = parse_sort(
        request,
        allowed=CAMPAIGN_SORT_FIELDS,
        default_field="amount",
        default_dir="desc",
        default_dirs=CAMPAIGN_SORT_DEFAULTS,
    )
    campaign_qs = (
        queryset.filter(campaign__isnull=False)
        .values("campaign_id", "campaign__name", "campaign__year", "campaign__team__name")
        .annotate(total=Sum("amount"), invoice_count=Count("id"))
    )
    campaign_qs = apply_ordering(
        campaign_qs,
        sort,
        fields=CAMPAIGN_SORT_FIELDS,
        default_field="amount",
        tiebreaker="campaign__name",
    )
    campaign_totals = list(campaign_qs)
    max_total = max((row["total"] or ZERO for row in campaign_totals), default=ZERO)
    for row in campaign_totals:
        row["percent"] = percent(row["total"] or ZERO, max_total)

    monthly_campaigns = defaultdict(lambda: {month: ZERO for month, _label in months})
    for row in (
        queryset.filter(campaign__isnull=False).values("campaign__name", "invoice_date").annotate(total=Sum("amount"))
    ):
        invoice_date = row["invoice_date"]
        if not invoice_date:
            continue
        jalali_month = gregorian_to_jalali(invoice_date.year, invoice_date.month, invoice_date.day)[1]
        monthly_campaigns[row["campaign__name"]][jalali_month] += row["total"] or ZERO

    context = {
        "campaign_rows": campaign_totals,
        "monthly_campaigns": dict(monthly_campaigns),
        "months": months,
        "filters": filters,
        "teams": visible_team_queryset(request),
        "years": distinct_jalali_years(visible_invoice_queryset(request)),
        "payment_stages": PaymentStage.choices,
        "cost_buckets": CostBucket.choices,
        "can_export_data": can_export(request.user),
        "table_sort": sort,
        "table_sort_defaults": CAMPAIGN_SORT_DEFAULTS,
    }
    return render(request, "marketing/campaigns/report.html", context)
