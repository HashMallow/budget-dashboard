from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from marketing.models import CostBucket, Invoice, PaymentStage, Role, Team, UserTeamAccess, Vendor


@pytest.fixture
def frontend_data():
    user_model = get_user_model()
    admin = user_model.objects.create_superuser(username="admin", password="test-pass")
    growth_editor = user_model.objects.create_user(username="growth-editor", password="test-pass")
    observer = user_model.objects.create_user(username="observer", password="test-pass")
    growth = Team.objects.create(name="Growth", slug="growth")
    brand = Team.objects.create(name="Brand", slug="brand")
    vendor = Vendor.objects.create(name="Frontend Vendor")
    UserTeamAccess.objects.create(user=growth_editor, team=growth, role=Role.EDITOR)
    UserTeamAccess.objects.create(user=observer, team=growth, role=Role.OBSERVER)
    growth_invoice = Invoice.objects.create(
        invoice_number="G-UI-1",
        vendor=vendor,
        team=growth,
        category="Performance",
        cost_bucket=CostBucket.TEAM,
        invoice_date=date(2026, 4, 1),
        amount=Decimal("1000.00"),
        payment_stage=PaymentStage.FINANCE_REVIEW,
    )
    brand_invoice = Invoice.objects.create(
        invoice_number="B-UI-1",
        vendor=vendor,
        team=brand,
        category="Brand",
        cost_bucket=CostBucket.TEAM,
        invoice_date=date(2026, 4, 2),
        amount=Decimal("2000.00"),
        payment_stage=PaymentStage.PAID,
    )
    return {
        "admin": admin,
        "growth_editor": growth_editor,
        "observer": observer,
        "growth": growth,
        "brand": brand,
        "vendor": vendor,
        "growth_invoice": growth_invoice,
        "brand_invoice": brand_invoice,
    }
