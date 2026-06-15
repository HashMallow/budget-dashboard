from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from marketing.forms import InvoiceForm
from marketing.models import CostBucket, Invoice, PaymentStage, Role, Team, UserTeamAccess, Vendor

pytestmark = pytest.mark.django_db


def test_manual_invoice_unique_per_vendor():
    vendor = Vendor.objects.create(name="Vendor")
    Invoice.objects.create(
        invoice_number="INV-1",
        vendor=vendor,
        category="Performance",
        invoice_date=date(2026, 1, 1),
        amount=Decimal("100"),
    )
    with pytest.raises(IntegrityError):
        Invoice.objects.create(
            invoice_number="INV-1",
            vendor=vendor,
            category="Performance",
            invoice_date=date(2026, 1, 2),
            amount=Decimal("200"),
        )


def test_imported_rows_allow_duplicate_number_vendor_on_different_source_rows():
    vendor = Vendor.objects.create(name="Vendor")
    common = {
        "invoice_number": "INV-1",
        "vendor": vendor,
        "category": "Performance",
        "invoice_date": date(2026, 1, 1),
        "amount": Decimal("100"),
        "source_sheet": "Marketing Spend Input",
    }
    Invoice.objects.create(source_row_number=2, **common)
    Invoice.objects.create(source_row_number=3, **common)
    assert Invoice.objects.filter(invoice_number="INV-1", vendor=vendor).count() == 2


def test_invoice_form_rejects_unauthorized_team():
    user_model = get_user_model()
    growth = Team.objects.create(name="Growth", slug="growth")
    brand = Team.objects.create(name="Brand", slug="brand")
    vendor = Vendor.objects.create(name="Vendor")
    editor = user_model.objects.create_user(username="editor")
    UserTeamAccess.objects.create(user=editor, team=growth, role=Role.EDITOR)

    form = InvoiceForm(
        data={
            "invoice_number": "NEW-1",
            "vendor": vendor.pk,
            "team": brand.pk,
            "category": "Performance",
            "cost_bucket": CostBucket.TEAM,
            "invoice_date": "2026-04-01",
            "amount": "1000",
            "currency": "IRR",
            "payment_stage": PaymentStage.DRAFT,
        },
        user=editor,
    )

    assert not form.is_valid()
    assert "team" in form.errors
