from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from marketing.models import BudgetLine, Campaign, Contract, Invoice, Role, UserTeamAccess, Vendor

pytestmark = pytest.mark.django_db


def test_admin_can_create_budget_line(client, frontend_data):
    client.force_login(frontend_data["admin"])
    response = client.post(
        reverse("marketing:budget_create"),
        {
            "year": 1405,
            "month": 1,
            "team": frontend_data["growth"].id,
            "campaign": "",
            "category": "Performance",
            "planned_amount": "5000000",
            "currency": "IRR",
        },
    )
    assert response.status_code == 302
    assert BudgetLine.objects.filter(team=frontend_data["growth"], category="Performance", year=1405, month=1).exists()
    list_response = client.get(reverse("marketing:budget_list"))
    assert list_response.status_code == 200
    assert b"5000000" in list_response.content or b"5,000,000" in list_response.content


def test_non_admin_cannot_create_budget_line(client, frontend_data):
    client.force_login(frontend_data["growth_editor"])
    response = client.get(reverse("marketing:budget_create"))
    assert response.status_code == 403


def test_budget_variance_api(client, frontend_data):
    BudgetLine.objects.create(
        year=1405,
        month=1,
        team=frontend_data["growth"],
        category="Performance",
        planned_amount=Decimal("10000"),
    )
    client.force_login(frontend_data["admin"])
    response = client.get(
        reverse("marketing:budget_variance_api"),
        {
            "team_id": frontend_data["growth"].id,
            "category": "Performance",
            "year": 1405,
            "month": 1,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert Decimal(payload["planned"]) == Decimal("10000")
    assert "percent_consumed" in payload


def test_categories_for_team_api(client, frontend_data):
    BudgetLine.objects.create(
        year=1405,
        month=2,
        team=frontend_data["growth"],
        category="Performance",
        planned_amount=Decimal("1000"),
    )
    client.force_login(frontend_data["admin"])
    response = client.get(
        reverse("marketing:categories_for_team_api"),
        {"team_id": frontend_data["growth"].id},
    )
    assert response.status_code == 200
    assert "Performance" in response.json()["categories"]


def test_pdf_export_wizard_redirects(client, frontend_data):
    client.force_login(frontend_data["admin"])
    response = client.post(
        reverse("marketing:pdf_export_wizard"),
        {"report_type": "dashboard", "year": "1405"},
    )
    assert response.status_code == 302
    assert "reports/dashboard.pdf" in response.url


def test_pdf_export_applies_vendor_team_and_month_filters(client, frontend_data):
    from datetime import date

    from django.test import RequestFactory

    from marketing.models import PaymentStage
    from marketing.views.core import filter_invoice_queryset, visible_invoice_queryset

    other_vendor = Vendor.objects.create(name="Other Vendor")
    Invoice.objects.create(
        invoice_number="OTHER-1",
        vendor=other_vendor,
        team=frontend_data["brand"],
        category="Brand",
        invoice_date=date(2026, 5, 1),
        amount=Decimal("500.00"),
        payment_stage=PaymentStage.PAID,
    )
    factory = RequestFactory()
    admin = frontend_data["admin"]

    vendor_request = factory.get("/", {"vendor": str(frontend_data["vendor"].pk)})
    vendor_request.user = admin
    vendor_qs, vendor_filters = filter_invoice_queryset(vendor_request, visible_invoice_queryset(vendor_request))
    assert vendor_filters["vendor_label"] == "Frontend Vendor"
    assert vendor_qs.filter(vendor=frontend_data["vendor"]).count() == vendor_qs.count()
    assert vendor_qs.count() == 2

    team_request = factory.get("/", {"team": str(frontend_data["growth"].pk)})
    team_request.user = admin
    team_qs, team_filters = filter_invoice_queryset(team_request, visible_invoice_queryset(team_request))
    assert team_filters["team_label"] == "Growth"
    assert team_qs.count() == 1
    assert team_qs.first().invoice_number == "G-UI-1"

    month_request = factory.get("/", {"year": "1405", "month": "1"})
    month_request.user = admin
    month_qs, month_filters = filter_invoice_queryset(month_request, visible_invoice_queryset(month_request))
    assert month_filters["month_label"]
    assert month_qs.filter(invoice_number="OTHER-1").count() == 0

    client.force_login(admin)
    response = client.get(
        reverse("marketing:export_vendors_pdf"),
        {"team": frontend_data["growth"].pk},
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"


def test_invoice_stage_update_json(client, frontend_data):
    client.force_login(frontend_data["admin"])
    invoice = frontend_data["growth_invoice"]
    response = client.post(
        reverse("marketing:invoice_stage_update", args=[invoice.pk]),
        {"payment_stage": "PAID"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    invoice.refresh_from_db()
    assert invoice.payment_stage == "PAID"


def test_vendor_merge_reassigns_invoices(client, frontend_data):
    duplicate = Vendor.objects.create(name="Dup Vendor")
    Invoice.objects.create(
        invoice_number="DUP-1",
        vendor=duplicate,
        team=frontend_data["growth"],
        category="Performance",
        invoice_date=frontend_data["growth_invoice"].invoice_date,
        amount=Decimal("100"),
    )
    client.force_login(frontend_data["admin"])
    preview = client.post(
        reverse("marketing:vendor_merge"),
        {"vendor_ids": [frontend_data["vendor"].pk, duplicate.pk]},
    )
    assert preview.status_code == 200
    confirm = client.post(
        reverse("marketing:vendor_merge"),
        {
            "confirm": "1",
            "target_id": frontend_data["vendor"].pk,
            "vendor_ids": [frontend_data["vendor"].pk, duplicate.pk],
        },
    )
    assert confirm.status_code == 302
    assert not Vendor.objects.filter(pk=duplicate.pk).exists()
    assert Invoice.objects.filter(vendor=frontend_data["vendor"], invoice_number="DUP-1").exists()


def test_editor_with_import_permission_can_open_import_page(client, frontend_data):
    UserTeamAccess.objects.filter(user=frontend_data["growth_editor"]).update(can_import_excel=True)
    client.force_login(frontend_data["growth_editor"])
    response = client.get(reverse("marketing:import_workbook"))
    assert response.status_code == 200


def test_editor_without_import_permission_gets_403(client, frontend_data):
    client.force_login(frontend_data["growth_editor"])
    response = client.get(reverse("marketing:import_workbook"))
    assert response.status_code == 403
