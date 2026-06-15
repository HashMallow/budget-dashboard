from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from marketing.models import CostBucket, Invoice, PaymentStage, Team, Vendor
from marketing.reports.pdf import build_dashboard_summary_pdf
from marketing.reports.pdf_fonts import PdfLocale

pytestmark = pytest.mark.django_db


def test_persian_dashboard_pdf_uses_embedded_font():
    pdf_bytes = build_dashboard_summary_pdf(
        title="خلاصه هزینه مارکتینگ",
        generated_at=date(2026, 6, 14),
        total_spend=Decimal("1000"),
        invoice_count=1,
        vendor_rows=[],
        stage_rows=[],
        locale=PdfLocale(lang="fa", unit="toman"),
    )
    assert pdf_bytes.startswith(b"%PDF")
    assert b"Vazirmatn" in pdf_bytes or b"/Font" in pdf_bytes


def test_admin_can_manage_vendor_reference_data(client):
    from django.contrib.auth import get_user_model

    admin = get_user_model().objects.create_superuser(username="admin", password="pass")
    client.force_login(admin)

    home = client.get(reverse("marketing:reference_data_home"))
    assert home.status_code == 200

    create = client.post(
        reverse("marketing:vendor_reference_create"),
        {"name": "New Vendor Co", "tax_id": "123", "notes": "Test"},
    )
    assert create.status_code == 302
    vendor = Vendor.objects.get(name="New Vendor Co")
    assert vendor.normalized_name

    edit = client.post(
        reverse("marketing:vendor_reference_edit", args=[vendor.pk]),
        {"name": "Renamed Vendor", "tax_id": "123", "notes": "Updated"},
    )
    assert edit.status_code == 302
    vendor.refresh_from_db()
    assert vendor.name == "Renamed Vendor"


def test_admin_can_manage_campaign_reference_data(client):
    from django.contrib.auth import get_user_model

    from marketing.models import Campaign, Team

    admin = get_user_model().objects.create_superuser(username="admin2", password="pass")
    team = Team.objects.create(name="Brand", slug="brand")
    client.force_login(admin)

    list_page = client.get(reverse("marketing:campaign_reference_list"))
    assert list_page.status_code == 200

    create = client.post(
        reverse("marketing:campaign_reference_create"),
        {
            "name": "Spring Push",
            "year": "1405",
            "team": team.pk,
            "status": "PLANNED",
            "notes": "",
        },
    )
    assert create.status_code == 302
    campaign = Campaign.objects.get(name="Spring Push")
    assert campaign.year == 1405
    assert campaign.team_id == team.pk

    edit = client.post(
        reverse("marketing:campaign_reference_edit", args=[campaign.pk]),
        {
            "name": "Spring Push",
            "year": "1405",
            "team": team.pk,
            "status": "ACTIVE",
            "notes": "Live",
        },
    )
    assert edit.status_code == 302
    campaign.refresh_from_db()
    assert campaign.status == "ACTIVE"


def test_non_admin_cannot_open_reference_data(client):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(username="user", password="pass")
    client.force_login(user)
    response = client.get(reverse("marketing:reference_data_home"))
    assert response.status_code == 403


def test_budget_hides_team_chart_when_team_filter_selected(client, frontend_data):
    from decimal import Decimal

    from django.urls import reverse

    from marketing.models import BudgetLine

    growth = frontend_data["growth"]
    brand = frontend_data["brand"]
    BudgetLine.objects.create(year=1405, month=1, team=growth, category="Performance", planned_amount=Decimal("1000"))
    BudgetLine.objects.create(year=1405, month=1, team=brand, category="Brand", planned_amount=Decimal("2000"))

    client.force_login(frontend_data["admin"])
    all_teams = client.get(reverse("marketing:budget_list"))
    filtered = client.get(reverse("marketing:budget_list"), {"team": growth.pk})

    assert all_teams.context["show_budget_team_chart"] is True
    assert filtered.context["show_budget_team_chart"] is False
    assert b'id="budgetTeamChart"' not in filtered.content


def test_help_page_loads_with_get(client):
    response = client.get(reverse("marketing:help_sitemap"))
    assert response.status_code == 200
    assert b"help-menu" in response.content or b"Left menu" in response.content


def test_fa_translations_flip_navigation_arrows():
    from marketing.translations import translate

    fa_path = translate("Dashboard → choose year", "fa")
    assert "←" in fa_path
    assert "→" not in fa_path
    assert translate("Dashboard → choose year", "en") == "Dashboard → choose year"


def test_help_page_shows_rtl_navigation_paths_in_fa(client):
    session = client.session
    session["ui_lang"] = "fa"
    session.save()
    response = client.get(reverse("marketing:help_sitemap"))
    assert response.status_code == 200
    html = response.content.decode()
    assert 'class="ui-path"' in html
    assert "←" in html
    assert "ui-flow" in html


def test_dashboard_hides_pie_chart_when_team_filter_selected(client):
    from django.contrib.auth import get_user_model

    admin = get_user_model().objects.create_superuser(username="admin", password="pass")
    team = Team.objects.create(name="Growth", slug="growth")
    vendor = Vendor.objects.create(name="Vendor")
    Invoice.objects.create(
        invoice_number="1",
        vendor=vendor,
        team=team,
        category="Performance",
        cost_bucket=CostBucket.TEAM,
        invoice_date=date(2026, 4, 1),
        amount=Decimal("1000"),
        payment_stage=PaymentStage.PAID,
    )

    client.force_login(admin)
    all_teams = client.get(reverse("marketing:dashboard"))
    filtered = client.get(reverse("marketing:dashboard"), {"team": team.pk})

    assert all_teams.context["show_spend_pie"] is True
    assert filtered.context["show_spend_pie"] is False
    assert all_teams.context["team_chart_has_data"] is True
    assert filtered.context["team_chart_has_data"] is False
    assert b"spendPie" not in filtered.content or b'id="spendPie"' not in filtered.content
    assert b'id="teamSpendChart"' not in filtered.content
    assert filtered.context["is_team_filtered"] is True
    assert filtered.context["filtered_team"] == team
    assert b"dashboard-layout--team" in filtered.content
    assert b'id="monthlyTrendChart"' in filtered.content
    assert b"Open team dashboard" in filtered.content or b"dashboard-scope" in filtered.content
