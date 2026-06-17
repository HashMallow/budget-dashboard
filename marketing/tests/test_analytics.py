from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from marketing.analytics import (
    attention_invoices,
    budget_actual_variance_window_rows,
    budget_variance_row_totals,
    monthly_spend_rows,
    monthly_spend_window_rows,
    overall_spend_pie,
    team_budget_variance_rows,
    vendor_grouped_rows,
)
from marketing.jalali import JALALI_MONTHS, gregorian_to_jalali, jalali_to_gregorian, jalali_year_bounds
from marketing.models import BudgetLine, CostBucket, Invoice, PaymentStage, Team, Vendor

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
    rows = monthly_spend_window_rows(Invoice.objects.all(), end_year=1405, end_month=3, count=12, ui_lang="en")

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

    rows = monthly_spend_window_rows(Invoice.objects.all(), end_year=1405, end_month=3, count=3, ui_lang="en")

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


def test_attention_invoices_includes_all_current_finance_review_rows_up_to_default_limit():
    team = Team.objects.create(name="Growth", slug="growth")
    vendor = Vendor.objects.create(name="Vendor")
    now = timezone.now()

    for index in range(12):
        Invoice.objects.create(
            invoice_number=f"FR-{index}",
            vendor=vendor,
            team=team,
            category="Performance",
            cost_bucket=CostBucket.TEAM,
            invoice_date=date(2026, 6, 3),
            amount=Decimal("1000"),
            payment_stage=PaymentStage.FINANCE_REVIEW,
            stage_changed_at=now - timedelta(days=index),
        )
    Invoice.objects.create(
        invoice_number="PAID-1",
        vendor=vendor,
        team=team,
        category="Performance",
        cost_bucket=CostBucket.TEAM,
        invoice_date=date(2026, 6, 3),
        amount=Decimal("1000"),
        payment_stage=PaymentStage.PAID,
    )

    rows = attention_invoices(Invoice.objects.all())

    assert len(rows) == 12
    assert [invoice.invoice_number for invoice in rows[:3]] == ["FR-11", "FR-10", "FR-9"]
    assert all(invoice.payment_stage == PaymentStage.FINANCE_REVIEW for invoice in rows)


def test_budget_variance_window_matches_planned_actual_and_deviation():
    team = Team.objects.create(name="Growth", slug="growth")
    vendor = Vendor.objects.create(name="Vendor")
    _make_invoice(team, vendor, 1405, 1, "300")
    _make_invoice(team, vendor, 1405, 2, "100")
    BudgetLine.objects.create(
        year=1405,
        month=1,
        team=team,
        category="Performance",
        planned_amount=Decimal("250"),
    )
    BudgetLine.objects.create(
        year=1405,
        month=2,
        team=team,
        category="Performance",
        planned_amount=Decimal("150"),
    )

    rows = budget_actual_variance_window_rows(
        BudgetLine.objects.all(),
        Invoice.objects.all(),
        end_year=1405,
        end_month=2,
        count=2,
        ui_lang="en",
    )

    assert len(rows) == 2
    assert rows[0]["planned"] == Decimal("250")
    assert rows[0]["actual"] == Decimal("300")
    assert rows[0]["deviation"] == Decimal("50")
    assert rows[1]["planned"] == Decimal("150")
    assert rows[1]["actual"] == Decimal("100")
    assert rows[1]["deviation"] == Decimal("-50")


def test_budget_variance_row_totals_sum_visible_rows():
    rows = [
        {"planned": Decimal("100"), "actual": Decimal("120"), "deviation": Decimal("20")},
        {"planned": Decimal("50"), "actual": Decimal("40"), "deviation": Decimal("-10")},
    ]
    totals = budget_variance_row_totals(rows)
    assert totals["planned"] == Decimal("150")
    assert totals["actual"] == Decimal("160")
    assert totals["deviation"] == Decimal("10")


def test_team_budget_variance_rows_include_rollup_bucket_spend():
    growth = Team.objects.create(name="Growth", slug="growth")
    vendor = Vendor.objects.create(name="Vendor")
    Invoice.objects.create(
        invoice_number="REF-1",
        vendor=vendor,
        team=growth,
        category="Referral",
        cost_bucket=CostBucket.REFERRAL,
        invoice_date=jalali_to_gregorian(1405, 1, 10),
        amount=Decimal("400"),
        payment_stage=PaymentStage.PAID,
    )
    BudgetLine.objects.create(
        year=1405,
        month=1,
        team=growth,
        category="Performance",
        planned_amount=Decimal("500"),
    )

    rows = team_budget_variance_rows(
        BudgetLine.objects.all(),
        Invoice.objects.all(),
        Team.objects.filter(pk=growth.pk),
        ui_lang="en",
    )

    assert len(rows) == 1
    assert rows[0]["planned"] == Decimal("500")
    assert rows[0]["actual"] == Decimal("400")
    assert rows[0]["deviation"] == Decimal("-100")


def test_overall_spend_pie_rolls_referral_and_sms_into_parent_teams():
    # Referral and SMS are cost buckets, not teams: they must not appear as their
    # own pie slice but must still be counted in the overall total via Growth/Retention.
    team_rows = [
        {"team_name": "Growth", "total": Decimal("100")},
        {"team_name": "Retention", "total": Decimal("50")},
    ]
    pie = overall_spend_pie(
        team_rows,
        referral_total=Decimal("30"),
        sms_total=Decimal("20"),
        ui_lang="en",
    )

    assert "Referral" not in pie["labels"]
    assert "SMS" not in pie["labels"]
    assert set(pie["labels"]) == {"Growth", "Retention"}
    assert sum(pie["values"]) == pytest.approx(200.0)
    label_to_value = dict(zip(pie["labels"], pie["values"]))
    assert label_to_value["Growth"] == pytest.approx(130.0)
    assert label_to_value["Retention"] == pytest.approx(70.0)


def test_overall_spend_pie_adds_parent_team_when_only_bucket_spend_exists():
    pie = overall_spend_pie(
        [],
        referral_total=Decimal("40"),
        sms_total=Decimal("0"),
        ui_lang="en",
    )

    assert pie["labels"] == ["Growth"]
    assert pie["values"] == [40.0]


def test_vendor_grouped_rows_aggregates_by_vendor_descending_total():
    team = Team.objects.create(name="Growth", slug="growth")
    vendor_a = Vendor.objects.create(name="Alpha Vendor")
    vendor_b = Vendor.objects.create(name="Beta Vendor")
    Invoice.objects.create(
        invoice_number="A-1",
        vendor=vendor_a,
        team=team,
        category="Performance",
        cost_bucket=CostBucket.TEAM,
        invoice_date=date(2026, 1, 1),
        amount=Decimal("300"),
        payment_stage=PaymentStage.PAID,
    )
    Invoice.objects.create(
        invoice_number="A-2",
        vendor=vendor_a,
        team=team,
        category="Performance",
        cost_bucket=CostBucket.TEAM,
        invoice_date=date(2026, 2, 1),
        amount=Decimal("200"),
        payment_stage=PaymentStage.FINANCE_REVIEW,
    )
    Invoice.objects.create(
        invoice_number="B-1",
        vendor=vendor_b,
        team=team,
        category="Performance",
        cost_bucket=CostBucket.TEAM,
        invoice_date=date(2026, 1, 1),
        amount=Decimal("1000"),
        payment_stage=PaymentStage.PAID,
    )

    rows = vendor_grouped_rows(Invoice.objects.all())

    assert len(rows) == 2
    assert rows[0]["vendor"] == vendor_b
    assert rows[0]["total"] == Decimal("1000")
    assert rows[1]["vendor"] == vendor_a
    assert rows[1]["total"] == Decimal("500")
    assert rows[1]["invoice_count"] == 2
    assert set(rows[1]["invoice_numbers"]) == {"A-1", "A-2"}
    assert "Paid" in rows[1]["stages"]
    assert "Finance review" in rows[1]["stages"]
