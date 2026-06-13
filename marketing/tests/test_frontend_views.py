from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from marketing.models import CostBucket, Invoice, PaymentStage, Role, Team, UserTeamAccess, Vendor

pytestmark = pytest.mark.django_db


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


def test_dashboard_renders_for_admin(client, frontend_data):
    client.force_login(frontend_data["admin"])

    response = client.get(reverse("marketing:dashboard"))

    assert response.status_code == 200
    assert "Spend Dashboard" in response.content.decode()


def test_invoice_list_is_scoped_for_team_editor(client, frontend_data):
    client.force_login(frontend_data["growth_editor"])

    response = client.get(reverse("marketing:invoice_list"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "G-UI-1" in content
    assert "B-UI-1" not in content


def test_observer_cannot_open_invoice_create(client, frontend_data):
    client.force_login(frontend_data["observer"])

    response = client.get(reverse("marketing:invoice_create"))

    assert response.status_code == 403


def test_editor_can_create_invoice_for_own_team(client, frontend_data):
    client.force_login(frontend_data["growth_editor"])

    response = client.post(
        reverse("marketing:invoice_create"),
        {
            "invoice_number": "G-UI-2",
            "vendor": frontend_data["vendor"].id,
            "team": frontend_data["growth"].id,
            "campaign": "",
            "category": "Performance",
            "cost_bucket": CostBucket.TEAM,
            "description": "",
            "invoice_date": "2026-04-03",
            "due_date": "",
            "amount": "1500.00",
            "currency": "IRR",
            "payment_stage": PaymentStage.SUBMITTED,
        },
    )

    assert response.status_code == 302
    assert Invoice.objects.filter(invoice_number="G-UI-2", team=frontend_data["growth"]).exists()


def test_admin_can_export_invoice_excel_and_print_report(client, frontend_data):
    client.force_login(frontend_data["admin"])

    excel_response = client.get(reverse("marketing:export_invoices_excel"))
    print_response = client.get(reverse("marketing:invoice_report_print"))

    assert excel_response.status_code == 200
    assert excel_response["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert print_response.status_code == 200
    assert "Invoice report" in print_response.content.decode()
