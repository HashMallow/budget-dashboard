from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, QuerySet, Sum

from marketing.jalali import gregorian_to_jalali
from marketing.models import CostBucket, Invoice, PaymentStage
from marketing.translations import translate

ZERO = Decimal("0")


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


def attention_invoices(invoices: QuerySet[Invoice], *, limit: int = 6) -> list[Invoice]:
    return sorted(
        invoices.filter(payment_stage=PaymentStage.FINANCE_REVIEW)[:20],
        key=lambda item: item.days_in_current_stage,
        reverse=True,
    )[:limit]
