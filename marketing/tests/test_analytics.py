from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from marketing.analytics import monthly_spend_rows, monthly_spend_window_rows
from marketing.jalali import JALALI_MONTHS, gregorian_to_jalali, jalali_to_gregorian, jalali_year_bounds
from marketing.models import CostBucket, Invoice, PaymentStage, Team, Vendor

pytestmark = pytest.mark.django_db


def _make_invoice(team, vendor, jalali_year, jalali_month, amount):
    return Invoice.objects.create(
        invoice_number=f"{jalali_year}-{jalali_month}",
        vendor=vendor,
        team=team,
        category="Performance",
        cost_bucket=CostBucket.TEAM,
        invoice_date=jalali_to_gregorian(jalali_year, jalali_month, 10),
        amount=Decimal(amount),
        payment_stage=PaymentStage.PAID,
    )


def test_monthly_window_excludes_future_months_and_trims_leading_empty():
    team = Team.objects.create(name="Growth", slug="growth")
    vendor = Vendor.objects.create(name="Vendor")
    _make_invoice(team, vendor, 1404, 12, "100")
    _make_invoice(team, vendor, 1405, 1, "200")
    _make_invoice(team, vendor, 1405, 3, "300")

    # "Now" is Khordad (month 3) of 1405; trailing 12-month window, no year filter.
    rows = monthly_spend_window_rows(
        Invoice.objects.all(), end_year=1405, end_month=3, count=12, ui_lang="en"
    )

    # No future months (nothing past 1405-03) and leading empties before 1404-12 are trimmed.
    assert (rows[0]["year"], rows[0]["month"]) == (1404, 12)
    assert (rows[-1]["year"], rows[-1]["month"]) == (1405, 3)
    assert all(not (r["year"] == 1405 and r["month"] > 3) for r in rows)
    totals = {(r["year"], r["month"]): r["total"] for r in rows}
    assert totals[(1404, 12)] == Decimal("100")
    assert totals[(1405, 2)] == Decimal("0")
    assert totals[(1405, 3)] == Decimal("300")
    # Cross-year window labels include the year for disambiguation.
    assert "1404" in rows[0]["label"]


def test_monthly_window_for_current_year_stops_at_current_month():
    team = Team.objects.create(name="Growth", slug="growth")
    vendor = Vendor.objects.create(name="Vendor")
    _make_invoice(team, vendor, 1405, 1, "200")
    _make_invoice(team, vendor, 1405, 3, "300")

    rows = monthly_spend_window_rows(
        Invoice.objects.all(), end_year=1405, end_month=3, count=3, ui_lang="en"
    )

    assert [r["month"] for r in rows] == [1, 2, 3]
    assert all(r["year"] == 1405 for r in rows)


def test_monthly_spend_rows_groups_by_jalali_month():
    team = Team.objects.create(name="Growth", slug="growth")
    vendor = Vendor.objects.create(name="Vendor")
    invoice_date = date(2026, 6, 3)
    jalali_month = gregorian_to_jalali(invoice_date.year, invoice_date.month, invoice_date.day)[1]
    Invoice.objects.create(
        invoice_number="J-1",
        vendor=vendor,
        team=team,
        category="Performance",
        cost_bucket=CostBucket.TEAM,
        invoice_date=invoice_date,
        amount=Decimal("5000"),
        payment_stage=PaymentStage.PAID,
    )
    months = [(number, latin) for number, _persian, latin in JALALI_MONTHS]
    rows = monthly_spend_rows(Invoice.objects.all(), months)

    assert rows[jalali_month - 1]["total"] == Decimal("5000")
    assert sum(row["total"] for row in rows if row["month"] != jalali_month) == Decimal("0")


def test_jalali_year_bounds_filter_matches_converted_year():
    team = Team.objects.create(name="Growth", slug="growth")
    vendor = Vendor.objects.create(name="Vendor")
    invoice_date = date(2026, 6, 3)
    jalali_year = gregorian_to_jalali(invoice_date.year, invoice_date.month, invoice_date.day)[0]
    Invoice.objects.create(
        invoice_number="Y-1",
        vendor=vendor,
        team=team,
        category="Performance",
        cost_bucket=CostBucket.TEAM,
        invoice_date=invoice_date,
        amount=Decimal("1000"),
        payment_stage=PaymentStage.PAID,
    )
    start, end = jalali_year_bounds(jalali_year)
    filtered = Invoice.objects.filter(invoice_date__range=(start, end))

    assert filtered.count() == 1
