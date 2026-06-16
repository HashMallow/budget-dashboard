from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .core import (
    forbidden,
    get_months,
    get_ui_lang,
    visible_team_queryset,
)
from ..forms import BudgetLineForm
from ..models import (
    BudgetLine,
)
from ..permissions import (
    filter_budget_lines_for_user,
    user_has_admin_access,
)
from ..table_sort import SortState, apply_ordering, parse_sort, sort_rows
from ..translations import translate

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


def budget_list(request):
    months = get_months(request)
    sort = parse_sort(
        request,
        allowed={*BUDGET_SORT_FIELDS, "total"},
        default_field="year",
        default_dir="desc",
        default_dirs={**BUDGET_SORT_DEFAULTS, "total": "desc"},
    )
    queryset = filter_budget_lines_for_user(
        BudgetLine.objects.select_related("team", "campaign"),
        request.user,
    )
    year = request.GET.get("year", "").strip()
    team = request.GET.get("team", "").strip()
    q = request.GET.get("q", "").strip()
    if year.isdigit():
        queryset = queryset.filter(year=int(year))
    if team.isdigit():
        queryset = queryset.filter(team_id=int(team))
    if q:
        queryset = queryset.filter(Q(category__icontains=q) | Q(team__name__icontains=q))

    db_sort = sort if sort.field in BUDGET_SORT_FIELDS else SortState("year", sort.direction)
    queryset = apply_ordering(
        queryset,
        db_sort,
        fields=BUDGET_SORT_FIELDS,
        default_field="year",
        tiebreaker="id",
    )

    years = (
        filter_budget_lines_for_user(BudgetLine.objects.all(), request.user)
        .order_by("-year")
        .values_list("year", flat=True)
        .distinct()
    )
    pivot = {}
    for line in queryset:
        key = (line.team.name if line.team else "No team", line.category)
        if key not in pivot:
            pivot[key] = {
                "team": key[0],
                "category": key[1],
                "months": {month_number: ZERO for month_number, _label in months},
                "total": ZERO,
            }
        if line.month:
            pivot[key]["months"][line.month] += line.planned_amount or ZERO
        pivot[key]["total"] += line.planned_amount or ZERO

    pivot_sort = SortState(
        sort.field if sort.field in BUDGET_PIVOT_SORT_KEYS else "team",
        sort.direction,
    )
    pivot_rows = sort_rows(
        list(pivot.values()),
        pivot_sort,
        keys=BUDGET_PIVOT_SORT_KEYS,
        default_field="team",
    )

    month_totals = {month_number: ZERO for month_number, _label in months}
    team_totals: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for row in pivot.values():
        for month_number, amount in row["months"].items():
            month_totals[month_number] += amount
        team_totals[row["team"]] += row["total"]

    budget_month_chart = {
        "labels": [label for _month_number, label in months],
        "values": [float(month_totals[month_number]) for month_number, _label in months],
    }
    sorted_team_totals = sorted(team_totals.items(), key=lambda item: item[1], reverse=True)
    budget_team_chart = {
        "labels": [translate(name, get_ui_lang(request)) for name, value in sorted_team_totals if value],
        "values": [float(value) for _name, value in sorted_team_totals if value],
    }
    show_budget_team_chart = not team.isdigit()

    paginator = Paginator(queryset, 50)
    context = {
        "page_obj": paginator.get_page(request.GET.get("page")),
        "pivot_rows": pivot_rows,
        "months": months,
        "years": years,
        "teams": visible_team_queryset(request),
        "filters": {"year": year, "team": team, "q": q},
        "table_sort": sort,
        "table_sort_defaults": {**BUDGET_SORT_DEFAULTS, "total": "desc"},
        "budget_month_chart": budget_month_chart,
        "budget_month_chart_has_data": any(budget_month_chart["values"]),
        "budget_team_chart": budget_team_chart,
        "show_budget_team_chart": show_budget_team_chart,
        "budget_team_chart_has_data": show_budget_team_chart and bool(budget_team_chart["values"]),
        "is_budget_admin": user_has_admin_access(request.user),
    }
    return render(request, "marketing/budgets/list.html", context)


def budget_create(request):
    if not user_has_admin_access(request.user):
        return forbidden()
    if request.method == "POST":
        form = BudgetLineForm(request.POST, ui_lang=get_ui_lang(request))
        if form.is_valid():
            form.save()
            messages.success(request, "Budget line saved.")
            return redirect("marketing:budget_list")
    else:
        form = BudgetLineForm(ui_lang=get_ui_lang(request))
    return render(request, "marketing/budgets/form.html", {"form": form, "mode": "create"})


def budget_edit(request, pk: int):
    if not user_has_admin_access(request.user):
        return forbidden()
    budget_line = get_object_or_404(BudgetLine, pk=pk)
    if request.method == "POST":
        form = BudgetLineForm(request.POST, instance=budget_line, ui_lang=get_ui_lang(request))
        if form.is_valid():
            form.save()
            messages.success(request, "Budget line updated.")
            return redirect("marketing:budget_list")
    else:
        form = BudgetLineForm(instance=budget_line, ui_lang=get_ui_lang(request))
    return render(
        request,
        "marketing/budgets/form.html",
        {"form": form, "mode": "edit", "budget_line": budget_line},
    )


@require_POST
def budget_delete(request, pk: int):
    if not user_has_admin_access(request.user):
        return forbidden()
    budget_line = get_object_or_404(BudgetLine, pk=pk)
    budget_line.delete()
    messages.success(request, "Budget line deleted.")
    return redirect("marketing:budget_list")
