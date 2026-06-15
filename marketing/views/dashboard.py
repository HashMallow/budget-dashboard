from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from ..analytics import (
    attention_invoices,
    budget_actual_variance_window_rows,
    budget_variance_chart_data,
    budget_variance_row_totals,
    decimal_sum,
    monthly_chart_data,
    monthly_spend_window_rows,
    overall_spend_pie,
    team_budget_variance_rows,
    team_chart_data,
    team_spend_rows,
    vendor_grouped_rows,
)
from .core import (
    distinct_jalali_years,
    filter_by_jalali_year,
    get_ui_lang,
    monthly_trend_window,
    visible_invoice_queryset,
    visible_team_queryset,
)
from ..cost_buckets import team_spend_cost_buckets
from ..forms import (
    user_can_create_invoice,
)
from ..models import (
    BudgetLine,
    Contract,
    ContractStage,
    CostBucket,
    PaymentStage,
)
from ..permissions import (
    can_export,
    filter_budget_lines_for_user,
    filter_contracts_for_user,
    get_user_scope,
)
from ..table_sort import parse_sort, sort_rows

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


def dashboard(request):
    base_queryset = visible_invoice_queryset(request)
    years = distinct_jalali_years(base_queryset)
    selected_year = request.GET.get("year", "").strip()
    selected_team = request.GET.get("team", "").strip()

    invoices = base_queryset
    if selected_year.isdigit():
        invoices = filter_by_jalali_year(invoices, selected_year)
    if selected_team.isdigit():
        invoices = invoices.filter(team_id=int(selected_team))

    total_spend = decimal_sum(invoices)
    paid_spend = decimal_sum(invoices.filter(payment_stage=PaymentStage.PAID))
    invoice_count = invoices.count()
    referral_total = decimal_sum(invoices.filter(cost_bucket=CostBucket.REFERRAL))
    sms_total = decimal_sum(invoices.filter(cost_bucket=CostBucket.SMS))

    contracts = filter_contracts_for_user(Contract.objects.all(), request.user)
    if selected_team.isdigit():
        contracts = contracts.filter(team_id=int(selected_team))
    today = timezone.now().date()
    contracts_expiring_soon = contracts.filter(
        end_date__gte=today,
        end_date__lte=today + timedelta(days=30),
    ).count()
    contracts_expired = contracts.filter(end_date__lt=today).exclude(stage=ContractStage.CANCELLED).count()

    budget_lines = filter_budget_lines_for_user(BudgetLine.objects.all(), request.user)
    if selected_year.isdigit():
        budget_lines = budget_lines.filter(year=int(selected_year))
    if selected_team.isdigit():
        budget_lines = budget_lines.filter(team_id=int(selected_team))

    end_year, end_month, window_count = monthly_trend_window(selected_year)
    ui_lang = get_ui_lang(request)
    monthly_rows = monthly_spend_window_rows(
        invoices,
        end_year=end_year,
        end_month=end_month,
        count=window_count,
        ui_lang=ui_lang,
    )
    monthly_chart = monthly_chart_data(monthly_rows)
    budget_variance_rows = budget_actual_variance_window_rows(
        budget_lines,
        invoices,
        end_year=end_year,
        end_month=end_month,
        count=window_count,
        ui_lang=ui_lang,
    )
    budget_variance_chart = budget_variance_chart_data(budget_variance_rows)
    budget_variance_totals = budget_variance_row_totals(budget_variance_rows)
    budget_total = decimal_sum(budget_lines, "planned_amount")
    budget_deviation = total_spend - budget_total
    scoped_teams = visible_team_queryset(request)
    if selected_team.isdigit():
        scoped_teams = scoped_teams.filter(pk=int(selected_team))
    team_budget_rows = team_budget_variance_rows(
        budget_lines,
        invoices,
        scoped_teams,
        ui_lang=ui_lang,
    )

    team_total_rows = team_spend_rows(invoices)
    team_chart = team_chart_data(team_total_rows, get_ui_lang(request))

    vendor_rows = vendor_grouped_rows(invoices)[:8]

    campaign_rows = list(
        invoices.filter(campaign__isnull=False)
        .values("campaign_id", "campaign__name", "campaign__year")
        .annotate(total=Sum("amount"), invoice_count=Count("id"))
        .order_by("-total")[:8]
    )

    stage_rows = list(
        invoices.values("payment_stage")
        .annotate(invoice_count=Count("id"), total=Sum("amount"))
        .order_by("-invoice_count")
    )

    attention = attention_invoices(invoices)

    spend_pie = overall_spend_pie(team_total_rows, referral_total, sms_total, ui_lang)
    # Hide multi-team breakdown charts when the dashboard is filtered to one team.
    show_spend_pie = not selected_team.isdigit()
    is_team_filtered = selected_team.isdigit()
    filtered_team = None
    if is_team_filtered:
        filtered_team = visible_team_queryset(request).filter(pk=int(selected_team)).first()

    context = {
        "scope": get_user_scope(request.user),
        "years": years,
        "selected_year": selected_year,
        "selected_team": selected_team,
        "is_team_filtered": is_team_filtered,
        "filtered_team": filtered_team,
        "show_team_budget_table": len(team_budget_rows) > 1,
        "teams": visible_team_queryset(request),
        "total_spend": total_spend,
        "paid_spend": paid_spend,
        "invoice_count": invoice_count,
        "referral_total": referral_total,
        "sms_total": sms_total,
        "budget_total": budget_total,
        "budget_deviation": budget_deviation,
        "contracts_expiring_soon": contracts_expiring_soon,
        "contracts_expired": contracts_expired,
        "monthly_rows": monthly_rows,
        "budget_variance_rows": budget_variance_rows,
        "budget_variance_totals": budget_variance_totals,
        "team_budget_rows": team_budget_rows,
        "team_total_rows": team_total_rows,
        "vendor_rows": vendor_rows,
        "campaign_rows": campaign_rows,
        "stage_rows": stage_rows,
        "attention_invoices": attention,
        "spend_pie": spend_pie,
        "show_spend_pie": show_spend_pie,
        "spend_pie_has_data": show_spend_pie and bool(spend_pie["values"]),
        "monthly_chart": monthly_chart,
        "monthly_chart_has_data": any(value for value in monthly_chart["values"]),
        "budget_variance_chart": budget_variance_chart,
        "budget_variance_chart_has_data": any(
            value for value in budget_variance_chart["planned"] + budget_variance_chart["actual"]
        ),
        "team_chart": team_chart,
        "team_chart_has_data": show_spend_pie and bool(team_chart["values"]),
        "can_create_invoice": user_can_create_invoice(request.user),
        "can_export_data": can_export(request.user),
    }
    return render(request, "marketing/dashboard.html", context)


def team_list(request):
    sort = parse_sort(
        request,
        allowed=TEAM_SORT_KEYS,
        default_field="amount",
        default_dir="desc",
        default_dirs=TEAM_SORT_DEFAULTS,
    )
    teams = visible_team_queryset(request)
    team_summaries = []
    for team in teams:
        invoices = visible_invoice_queryset(request).filter(
            team=team,
            cost_bucket__in=team_spend_cost_buckets(team),
        )
        team_summaries.append(
            {
                "team": team,
                "total_spend": decimal_sum(invoices),
                "invoice_count": invoices.count(),
            }
        )
    team_summaries = sort_rows(
        team_summaries,
        sort,
        keys=TEAM_SORT_KEYS,
        default_field="amount",
    )
    return render(
        request,
        "marketing/teams/list.html",
        {
            "team_summaries": team_summaries,
            "table_sort": sort,
            "table_sort_defaults": TEAM_SORT_DEFAULTS,
        },
    )


def team_dashboard(request, pk: int):
    team = get_object_or_404(visible_team_queryset(request), pk=pk)
    selected_year = request.GET.get("year", "").strip()

    invoices = visible_invoice_queryset(request).filter(
        team=team,
        cost_bucket__in=team_spend_cost_buckets(team),
    )
    if selected_year.isdigit():
        invoices = filter_by_jalali_year(invoices, selected_year)

    total_spend = decimal_sum(invoices)
    invoice_count = invoices.count()
    end_year, end_month, window_count = monthly_trend_window(selected_year)
    ui_lang = get_ui_lang(request)
    budget_lines = filter_budget_lines_for_user(BudgetLine.objects.filter(team=team), request.user)
    if selected_year.isdigit():
        budget_lines = budget_lines.filter(year=int(selected_year))
    budget_variance_rows = budget_actual_variance_window_rows(
        budget_lines,
        invoices,
        end_year=end_year,
        end_month=end_month,
        count=window_count,
        ui_lang=ui_lang,
    )
    budget_variance_chart = budget_variance_chart_data(budget_variance_rows)
    budget_variance_totals = budget_variance_row_totals(budget_variance_rows)
    budget_total = decimal_sum(budget_lines, "planned_amount")
    budget_deviation = total_spend - budget_total
    monthly_rows = monthly_spend_window_rows(
        invoices,
        end_year=end_year,
        end_month=end_month,
        count=window_count,
        ui_lang=ui_lang,
    )
    monthly_chart = monthly_chart_data(monthly_rows)
    vendor_rows = vendor_grouped_rows(invoices)
    campaign_rows = list(
        invoices.filter(campaign__isnull=False)
        .values("campaign_id", "campaign__name", "campaign__year")
        .annotate(total=Sum("amount"), invoice_count=Count("id"))
        .order_by("-total")
    )
    attention = attention_invoices(invoices)

    export_query = f"team={team.id}"
    if selected_year.isdigit():
        export_query += f"&year={selected_year}"

    context = {
        "team": team,
        "years": distinct_jalali_years(visible_invoice_queryset(request).filter(team=team)),
        "selected_year": selected_year,
        "total_spend": total_spend,
        "budget_total": budget_total,
        "budget_deviation": budget_deviation,
        "invoice_count": invoice_count,
        "monthly_rows": monthly_rows,
        "budget_variance_rows": budget_variance_rows,
        "budget_variance_totals": budget_variance_totals,
        "monthly_chart": monthly_chart,
        "monthly_chart_has_data": any(value for value in monthly_chart["values"]),
        "budget_variance_chart": budget_variance_chart,
        "budget_variance_chart_has_data": any(
            value for value in budget_variance_chart["planned"] + budget_variance_chart["actual"]
        ),
        "vendor_rows": vendor_rows,
        "campaign_rows": campaign_rows,
        "attention_invoices": attention,
        "can_create_invoice": user_can_create_invoice(request.user),
        "can_export_data": can_export(request.user),
        "export_query": export_query,
    }
    return render(request, "marketing/teams/dashboard.html", context)
