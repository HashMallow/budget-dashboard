from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from ..analytics import jalali_month_totals, percent_consumed
from ..jalali import gregorian_to_jalali, parse_jalali_date_text
from ..models import BudgetLine, Campaign, Invoice
from ..permissions import filter_budget_lines_for_user, filter_invoices_for_user

ZERO = Decimal("0")


def _jalali_year_month_from_text(text: str) -> tuple[int, int] | None:
    parsed = parse_jalali_date_text(text)
    if parsed is None:
        try:
            parsed = date.fromisoformat(text.strip())
        except ValueError:
            return None
    jy, jm, _ = gregorian_to_jalali(parsed.year, parsed.month, parsed.day)
    return jy, jm


@login_required
@require_GET
def budget_variance_api(request):
    team_id = request.GET.get("team_id", "").strip()
    category = request.GET.get("category", "").strip()
    invoice_date = request.GET.get("invoice_date", "").strip()
    year = request.GET.get("year", "").strip()
    month = request.GET.get("month", "").strip()

    if not team_id.isdigit() or not category:
        return JsonResponse({"error": "team_id and category are required."}, status=400)

    if invoice_date:
        ym = _jalali_year_month_from_text(invoice_date)
        if ym is None:
            return JsonResponse({"error": "Invalid invoice date."}, status=400)
        jy, jm = ym
    elif year.isdigit() and month.isdigit():
        jy, jm = int(year), int(month)
    else:
        return JsonResponse({"error": "invoice_date or year+month required."}, status=400)

    budget_lines = filter_budget_lines_for_user(BudgetLine.objects.all(), request.user)
    planned = (
        budget_lines.filter(
            team_id=int(team_id),
            category=category,
            year=jy,
            month=jm,
        ).aggregate(total=Sum("planned_amount"))["total"]
        or ZERO
    )

    invoices = filter_invoices_for_user(
        Invoice.objects.filter(team_id=int(team_id), category=category),
        request.user,
    )
    actual = jalali_month_totals(invoices).get((jy, jm), ZERO)
    remaining = planned - actual
    pct = percent_consumed(planned, actual)

    if planned <= 0 and actual <= 0:
        return JsonResponse(
            {
                "planned": str(planned),
                "actual": str(actual),
                "remaining": str(remaining),
                "percent_consumed": None,
                "has_budget": False,
            }
        )

    return JsonResponse(
        {
            "planned": str(planned),
            "actual": str(actual),
            "remaining": str(remaining),
            "percent_consumed": pct,
            "has_budget": planned > 0,
        }
    )


@login_required
@require_GET
def categories_for_team_api(request):
    team_id = request.GET.get("team_id", "").strip()
    if not team_id.isdigit():
        return JsonResponse({"categories": [], "campaigns": []})

    budget_lines = filter_budget_lines_for_user(BudgetLine.objects.all(), request.user)
    categories = list(
        budget_lines.filter(team_id=int(team_id))
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )
    campaigns = list(
        Campaign.objects.filter(team_id=int(team_id), budget_lines__isnull=False)
        .distinct()
        .order_by("name")
        .values("id", "name", "year")
    )
    return JsonResponse({"categories": categories, "campaigns": campaigns})
