from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from marketing.models import CostBucket, Invoice, InvoiceStatusHistory, PaymentStage, Role, Team, UserTeamAccess, Vendor
from marketing.permissions import can_edit_invoice, filter_invoices_for_user

pytestmark = pytest.mark.django_db


def make_invoice(*, team: Team | None, vendor: Vendor, invoice_number: str, bucket: str = CostBucket.TEAM) -> Invoice:
    return Invoice.objects.create(
        invoice_number=invoice_number,
        vendor=vendor,
        team=team,
        category="Performance",
        cost_bucket=bucket,
        invoice_date=date(2026, 4, 1),
        amount=Decimal("1000.00"),
        payment_stage=PaymentStage.DRAFT,
    )


@pytest.fixture
def sample_data():
    user_model = get_user_model()
    growth = Team.objects.create(name="Growth", slug="growth")
    brand = Team.objects.create(name="Brand", slug="brand")
    vendor = Vendor.objects.create(name="Test Vendor")
    growth_invoice = make_invoice(team=growth, vendor=vendor, invoice_number="G-1")
    brand_invoice = make_invoice(team=brand, vendor=vendor, invoice_number="B-1")
    referral_invoice = make_invoice(
        team=growth,
        vendor=vendor,
        invoice_number="R-1",
        bucket=CostBucket.REFERRAL,
    )
    return {
        "user_model": user_model,
        "growth": growth,
        "brand": brand,
        "growth_invoice": growth_invoice,
        "brand_invoice": brand_invoice,
        "referral_invoice": referral_invoice,
    }


def test_superuser_can_see_all_invoices(sample_data):
    admin = sample_data["user_model"].objects.create_superuser(username="admin", password="test-pass")

    visible_ids = set(filter_invoices_for_user(Invoice.objects.all(), admin).values_list("id", flat=True))

    assert visible_ids == {
        sample_data["growth_invoice"].id,
        sample_data["brand_invoice"].id,
        sample_data["referral_invoice"].id,
    }


def test_team_editor_sees_assigned_team_including_rollup_buckets(sample_data):
    editor = sample_data["user_model"].objects.create_user(username="growth-editor")
    UserTeamAccess.objects.create(user=editor, team=sample_data["growth"], role=Role.EDITOR)

    visible_ids = set(filter_invoices_for_user(Invoice.objects.all(), editor).values_list("id", flat=True))

    assert visible_ids == {
        sample_data["growth_invoice"].id,
        sample_data["referral_invoice"].id,
    }
    assert can_edit_invoice(editor, sample_data["growth_invoice"]) is True
    assert can_edit_invoice(editor, sample_data["referral_invoice"]) is True
    assert can_edit_invoice(editor, sample_data["brand_invoice"]) is False


def test_observer_cannot_edit_invoice(sample_data):
    observer = sample_data["user_model"].objects.create_user(username="observer")
    UserTeamAccess.objects.create(user=observer, team=sample_data["growth"], role=Role.OBSERVER)

    assert can_edit_invoice(observer, sample_data["growth_invoice"]) is False


def test_referral_sms_outside_assigned_team_requires_global_or_explicit_flag(sample_data):
    vendor = sample_data["growth_invoice"].vendor
    brand_referral = make_invoice(
        team=sample_data["brand"],
        vendor=vendor,
        invoice_number="R-2",
        bucket=CostBucket.REFERRAL,
    )
    manager = sample_data["user_model"].objects.create_user(username="growth-manager")
    UserTeamAccess.objects.create(user=manager, team=sample_data["growth"], role=Role.MANAGER)

    visible_ids = set(filter_invoices_for_user(Invoice.objects.all(), manager).values_list("id", flat=True))
    assert sample_data["referral_invoice"].id in visible_ids
    assert brand_referral.id not in visible_ids

    UserTeamAccess.objects.filter(user=manager).update(can_view_referral_sms=True)

    visible_ids = set(filter_invoices_for_user(Invoice.objects.all(), manager).values_list("id", flat=True))
    assert brand_referral.id in visible_ids


def test_global_manager_can_see_all_invoices(sample_data):
    manager = sample_data["user_model"].objects.create_user(username="global-manager")
    UserTeamAccess.objects.create(user=manager, role=Role.MANAGER, is_global=True)

    visible_ids = set(filter_invoices_for_user(Invoice.objects.all(), manager).values_list("id", flat=True))

    assert visible_ids == {
        sample_data["growth_invoice"].id,
        sample_data["brand_invoice"].id,
        sample_data["referral_invoice"].id,
    }


def test_payment_stage_change_creates_history(sample_data):
    editor = sample_data["user_model"].objects.create_user(username="finance-editor")
    invoice = sample_data["growth_invoice"]

    invoice.set_payment_stage(PaymentStage.PAID, changed_by=editor, note="Paid from test")

    invoice.refresh_from_db()
    history = InvoiceStatusHistory.objects.get(invoice=invoice)
    assert invoice.payment_stage == PaymentStage.PAID
    assert invoice.paid_at is not None
    assert history.old_stage == PaymentStage.DRAFT
    assert history.new_stage == PaymentStage.PAID
    assert history.changed_by == editor
    assert history.note == "Paid from test"
