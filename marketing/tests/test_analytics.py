from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from marketing.analytics import monthly_spend_rows
from marketing.jalali import JALALI_MONTHS, gregorian_to_jalali, jalali_year_bounds
from marketing.models import CostBucket, Invoice, PaymentStage, Team, Vendor

pytestmark = pytest.mark.django_db


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
