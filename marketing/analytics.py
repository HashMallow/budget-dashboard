from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, QuerySet, Sum

from marketing.cost_buckets import team_spend_cost_buckets
from marketing.jalali import JALALI_MONTHS, gregorian_to_jalali
from marketing.models import CostBucket, Invoice, PaymentStage, Team
from marketing.translations import translate

ZERO = Decimal("0")

_MONTH_LABELS_FA = {number: persian for number, persian, _latin in JALALI_MONTHS}
_MONTH_LABELS_EN = {number: latin for number, _persian, latin in JALALI_MONTHS}


def decimal_sum(queryset: QuerySet, field: str = "amount") -> Decimal:
    return queryset.aggregate(total=Sum(field))["total"] or ZERO


def percent(value: Decimal, maximum: Decimal) -> int:
    if not maximum or value <= 0:
        return 0
    ratio = (float(value) / float(maximum)) * 100
    return min(max(int(round(ratio)), 2), 100)


def monthly_spend_rows(invoices: QuerySet[Invoice], months: list[tuple[int, str]]) -> list[dict]:
    monthly_map = {month_number: ZERO for month_number, _label in months}
    for row in invoices.values("invoice_date").annotate(total=Sum("amount")):
        invoice_date = row["invoice_date"]
        if not invoice_date:
            continue
        jalali_month = gregorian_to_jalali(invoice_date.year, invoice_date.month, invoice_date.day)[1]
        monthly_map[jalali_month] += row["total"] or ZERO
    max_monthly = max(monthly_map.values(), default=ZERO)
    return [
        {
            "month": month_number,
            "label": label,
            "total": monthly_map[month_number],
            "percent": percent(monthly_map[month_number], max_monthly),
        }
        for month_number, label in months
    ]


def jalali_month_totals(invoices: QuerySet[Invoice]) -> dict[tuple[int, int], Decimal]:
    """Sum invoice amounts keyed by (Jalali year, Jalali month)."""
    totals: dict[tuple[int, int], Decimal] = defaultdict(lambda: ZERO)
    for row in invoices.values("invoice_date").annotate(total=Sum("amount")):
        invoice_date = row["invoice_date"]
        if not invoice_date:
            continue
        jy, jm, _ = gregorian_to_jalali(invoice_date.year, invoice_date.month, invoice_date.day)
        totals[(jy, jm)] += row["total"] or ZERO
    return totals


def jalali_budget_month_totals(budget_lines: QuerySet) -> dict[tuple[int, int], Decimal]:
    """Sum planned budget amounts keyed by (Jalali year, Jalali month)."""
    totals: dict[tuple[int, int], Decimal] = defaultdict(lambda: ZERO)
    for row in budget_lines.values("year", "month").annotate(total=Sum("planned_amount")):
        year = row["year"]
        month = row["month"]
        if year and month:
            totals[(year, month)] += row["total"] or ZERO
    return totals


def budget_actual_variance_window_rows(
    budget_lines: QuerySet,
    invoices: QuerySet[Invoice],
    *,
    end_year: int,
    end_month: int,
    count: int,
    ui_lang: str,
    trim_leading_empty: bool = True,
) -> list[dict]:
    """Monthly planned budget, actual spend, and deviation over a trailing Jalali window.

    Deviation follows the workbook convention: actual minus planned (positive = overspend).
    """
    planned_totals = jalali_budget_month_totals(budget_lines)
    actual_totals = jalali_month_totals(invoices)
    window = _month_window(end_year, end_month, count)
    if trim_leading_empty:
        first_with_data = next(
            (
                idx
                for idx, ym in enumerate(window)
                if planned_totals.get(ym) or actual_totals.get(ym)
            ),
            None,
        )
        window = window[first_with_data:] if first_with_data is not None else window[-1:]

    show_year = len({year for year, _month in window}) > 1
    labels = _MONTH_LABELS_FA if ui_lang == "fa" else _MONTH_LABELS_EN
    max_magnitude = max(
        (
            max(planned_totals.get(ym, ZERO), actual_totals.get(ym, ZERO))
            for ym in window
        ),
        default=ZERO,
    )

    rows = []
    for year, month in window:
        planned = planned_totals.get((year, month), ZERO)
        actual = actual_totals.get((year, month), ZERO)
        deviation = actual - planned
        label = f"{labels[month]} {year}" if show_year else labels[month]
        rows.append({
            "month": month,
            "year": year,
            "label": label,
            "planned": planned,
            "actual": actual,
            "deviation": deviation,
            "percent": percent(max(planned, actual), max_magnitude),
        })
    return rows


def budget_variance_chart_data(variance_rows: list[dict]) -> dict[str, list]:
    return {
        "labels": [row["label"] for row in variance_rows],
        "planned": [float(row["planned"]) for row in variance_rows],
        "actual": [float(row["actual"]) for row in variance_rows],
        "deviation": [float(row["deviation"]) for row in variance_rows],
    }


def budget_variance_row_totals(variance_rows: list[dict]) -> dict[str, Decimal]:
    """Sum planned, actual, and deviation for the rows shown in the monthly table/chart."""
    planned = sum((row["planned"] for row in variance_rows), ZERO)
    actual = sum((row["actual"] for row in variance_rows), ZERO)
    return {
        "planned": planned,
        "actual": actual,
        "deviation": actual - planned,
    }


def team_budget_variance_rows(
    budget_lines: QuerySet,
    invoices: QuerySet[Invoice],
    teams: QuerySet[Team],
    *,
    ui_lang: str,
) -> list[dict]:
    """Per-team planned budget, actual spend, and deviation for the current filter scope."""
    planned_by_team = {
        row["team_id"]: row["total"] or ZERO
        for row in budget_lines.filter(team__isnull=False)
        .values("team_id")
        .annotate(total=Sum("planned_amount"))
    }
    rows = []
    for team in teams:
        actual = decimal_sum(
            invoices.filter(team=team, cost_bucket__in=team_spend_cost_buckets(team)),
        )
        planned = planned_by_team.get(team.id, ZERO)
        deviation = actual - planned
        rows.append({
            "team_id": team.id,
            "team_name": translate(team.name, ui_lang),
            "planned": planned,
            "actual": actual,
            "deviation": deviation,
        })
    rows.sort(key=lambda item: item["actual"], reverse=True)
    max_actual = max((row["actual"] for row in rows), default=ZERO)
    for row in rows:
        row["percent"] = percent(row["actual"], max_actual)
    return rows


def _month_window(end_year: int, end_month: int, count: int) -> list[tuple[int, int]]:
    """Return ``count`` (year, month) pairs ending at (end_year, end_month), oldest first."""
    sequence: list[tuple[int, int]] = []
    year, month = end_year, end_month
    for _ in range(max(count, 1)):
        sequence.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(sequence))


def monthly_spend_window_rows(
    invoices: QuerySet[Invoice],
    *,
    end_year: int,
    end_month: int,
    count: int,
    ui_lang: str,
    trim_leading_empty: bool = True,
) -> list[dict]:
    """Per-month spend over a trailing window that never extends past (end_year, end_month).

    Leading months with no data are dropped so the chart starts where real data begins.
    Labels include the year only when the window spans more than one Jalali year.
    """
    totals = jalali_month_totals(invoices)
    window = _month_window(end_year, end_month, count)
    if trim_leading_empty:
        first_with_data = next((idx for idx, ym in enumerate(window) if totals.get(ym)), None)
        window = window[first_with_data:] if first_with_data is not None else window[-1:]

    show_year = len({year for year, _month in window}) > 1
    labels = _MONTH_LABELS_FA if ui_lang == "fa" else _MONTH_LABELS_EN
    max_total = max((totals.get(ym, ZERO) for ym in window), default=ZERO)

    rows = []
    for year, month in window:
        total = totals.get((year, month), ZERO)
        label = f"{labels[month]} {year}" if show_year else labels[month]
        rows.append({
            "month": month,
            "year": year,
            "label": label,
            "total": total,
            "percent": percent(total, max_total),
        })
    return rows


def monthly_chart_data(monthly_rows: list[dict]) -> dict[str, list]:
    return {
        "labels": [row["label"] for row in monthly_rows],
        "values": [float(row["total"]) for row in monthly_rows],
    }


def team_spend_rows(invoices: QuerySet[Invoice], *, limit: int = 10) -> list[dict]:
    rows = list(
        invoices.filter(cost_bucket=CostBucket.TEAM)
        .values("team_id", "team__name")
        .annotate(total=Sum("amount"), invoice_count=Count("id"))
        .order_by("-total")[:limit]
    )
    max_team_total = max((row["total"] or ZERO for row in rows), default=ZERO)
    for row in rows:
        row["percent"] = percent(row["total"] or ZERO, max_team_total)
        row["team_name"] = row["team__name"] or "No team"
    return rows


def team_chart_data(team_rows: list[dict], ui_lang: str) -> dict[str, list]:
    segments = [(translate(row["team_name"], ui_lang), row["total"]) for row in team_rows if row["total"]]
    return {
        "labels": [label for label, _ in segments],
        "values": [float(value) for _, value in segments],
    }


def overall_spend_pie(team_rows: list[dict], referral_total: Decimal, sms_total: Decimal, ui_lang: str) -> dict:
    pie_segments = [
        (translate(row["team_name"], ui_lang), row["total"])
        for row in team_rows
        if row["total"]
    ]
    if referral_total:
        pie_segments.append((translate("Referral", ui_lang), referral_total))
    if sms_total:
        pie_segments.append((translate("SMS", ui_lang), sms_total))
    return {
        "labels": [label for label, _ in pie_segments],
        "values": [float(value) for _, value in pie_segments],
    }


def vendor_grouped_rows(invoices: QuerySet[Invoice]) -> list[dict]:
    grouped: dict[int, dict] = {}
    for invoice in invoices.select_related("vendor"):
        vendor_id = invoice.vendor_id
        if vendor_id not in grouped:
            grouped[vendor_id] = {
                "vendor": invoice.vendor,
                "total": ZERO,
                "invoice_count": 0,
                "invoice_numbers": [],
                "stages": set(),
            }
        row = grouped[vendor_id]
        row["total"] += invoice.amount or ZERO
        row["invoice_count"] += 1
        row["invoice_numbers"].append(invoice.invoice_number)
        row["stages"].add(invoice.get_payment_stage_display())

    vendor_rows = sorted(grouped.values(), key=lambda item: item["total"], reverse=True)
    for row in vendor_rows:
        row["stages"] = sorted(row["stages"])
        row["visible_invoice_numbers"] = row["invoice_numbers"][:8]
        row["remaining_invoice_count"] = max(len(row["invoice_numbers"]) - 8, 0)
    return vendor_rows


def attention_invoices(invoices: QuerySet[Invoice], *, limit: int = 20) -> list[Invoice]:
    return sorted(
        invoices.filter(payment_stage=PaymentStage.FINANCE_REVIEW),
        key=lambda item: item.days_in_current_stage,
        reverse=True,
    )[:limit]
