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


def test_shape_pdf_text_uses_bidi_for_rtl_and_skips_ascii():
    import arabic_reshaper
    from bidi.algorithm import get_display

    from marketing.reports.pdf_fonts import PdfLocale, shape_pdf_parts, shape_pdf_text

    expected = get_display(arabic_reshaper.reshape("ریال"))
    assert shape_pdf_text("ریال", PdfLocale(lang="fa")) == expected
    assert shape_pdf_text("ریال", PdfLocale(lang="en")) == expected
    assert shape_pdf_text("123, 456", PdfLocale(lang="fa")) == "123, 456"
    assert shape_pdf_text("Vendor", PdfLocale(lang="en")) == "Vendor"


def test_shape_pdf_parts_runs_single_bidi_pass_for_mixed_text():
    from marketing.reports.pdf_fonts import PdfLocale, shape_pdf_parts, shape_pdf_text

    logical = "فیلترها: خط کسب‌وکار: Business"
    once = shape_pdf_parts(["فیلترها: ", "خط کسب‌وکار: ", "Business"], PdfLocale(lang="fa"))
    assert once == shape_pdf_text(logical, PdfLocale(lang="fa"))
    # Double shaping corrupts Persian — must never happen in headers.
    assert shape_pdf_text(once, PdfLocale(lang="fa")) != once


def test_persian_pdf_filter_header_mixed_english_value():
    from datetime import datetime
    from unittest.mock import MagicMock

    from marketing.reports.pdf import build_vendor_report_pdf

    vendor = MagicMock()
    vendor.name = "وندور نمونه"
    pdf_bytes = build_vendor_report_pdf(
        title="گزارش هزینه وندورها",
        generated_at=datetime(2026, 6, 17, 7, 54),
        vendor_rows=[
            {
                "vendor": vendor,
                "invoice_count": 1,
                "invoice_numbers": ["100"],
                "stages": ["Paid"],
                "total": Decimal("88000000"),
            }
        ],
        filters={"business_section": "Business"},
        locale=PdfLocale(lang="fa", unit="toman"),
    )
    assert pdf_bytes.startswith(b"%PDF")
    # Garbled double-bidi artifacts (isolated reversed letters) must not appear.
    assert "راکوب".encode() not in pdf_bytes
    assert "ط‌خ".encode() not in pdf_bytes


def test_pdf_fonts_use_vazirmatn_for_all_locales():
    from marketing.reports.pdf_fonts import PdfLocale, pdf_font_names, register_pdf_fonts

    assert register_pdf_fonts()
    assert pdf_font_names(PdfLocale(lang="en")) == ("Vazirmatn", "Vazirmatn-Bold")
    assert pdf_font_names(PdfLocale(lang="fa")) == ("Vazirmatn", "Vazirmatn-Bold")


def test_english_pdf_renders_persian_vendor_names():
    from datetime import datetime
    from unittest.mock import MagicMock

    from marketing.reports.pdf import build_vendor_report_pdf

    vendor = MagicMock()
    vendor.name = "شرکت تبلیغات ایران"
    pdf_bytes = build_vendor_report_pdf(
        title="Vendor spend report",
        generated_at=datetime(2026, 6, 16, 7, 2),
        vendor_rows=[
            {
                "vendor": vendor,
                "invoice_count": 1,
                "invoice_numbers": ["INV-001"],
                "stages": ["Paid"],
                "total": Decimal("1000"),
            }
        ],
        locale=PdfLocale(lang="en", unit="rial"),
    )
    assert pdf_bytes.startswith(b"%PDF")
    assert b"Vazirmatn" in pdf_bytes
    assert b"\xe2\x96\xa0" not in pdf_bytes  # ReportLab tofu when glyph missing


def test_persian_vendor_pdf_keeps_rtl_words_in_logical_order():
    from datetime import datetime
    from unittest.mock import MagicMock

    from marketing.reports.pdf import build_vendor_report_pdf

    vendor = MagicMock()
    vendor.name = "Sample Vendor Co."
    pdf_bytes = build_vendor_report_pdf(
        title="گزارش هزینه وندورها",
        generated_at=datetime(2026, 6, 15, 7, 2),
        vendor_rows=[
            {
                "vendor": vendor,
                "invoice_count": 1,
                "invoice_numbers": ["123"],
                "stages": ["Paid"],
                "total": Decimal("1000"),
            }
        ],
        locale=PdfLocale(lang="fa", unit="rial"),
    )
    # Reversed-by-bidi artifacts must not appear as literal UTF-8 in the PDF stream.
    assert "لایر".encode() not in pdf_bytes
    assert "دیلوت".encode() not in pdf_bytes
    assert "اهرودنو".encode() not in pdf_bytes


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


def test_fa_budget_page_uses_persian_ui_strings(client, frontend_data):
    session = client.session
    session["ui_lang"] = "fa"
    session.save()
    client.force_login(frontend_data["admin"])
    response = client.get(reverse("marketing:budget_list"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "ردیف بودجه جدید" in html
    assert "ردیف‌های بودجه به تفکیک تیم، دسته و ماه" in html
    assert "New budget line" not in html
    assert "Budget lines by team, category and month" not in html


def test_translation_catalog_covers_template_and_export_strings():
    import re
    from pathlib import Path

    from marketing.translations import FA

    pattern = re.compile(r'\{%\s*t\s+"([^"]+)"')
    pattern2 = re.compile(r"\{%\s*t\s+'([^']+)'")
    missing: set[str] = set()
    for path in Path("templates").rglob("*.html"):
        text = path.read_text()
        for matcher in (pattern, pattern2):
            for match in matcher.finditer(text):
                key = match.group(1)
                if key not in FA:
                    missing.add(key)
    cp = Path("marketing/context_processors.py").read_text()
    for match in re.finditer(r'"label":\s*"([^"]+)"|"title":\s*"([^"]+)"', cp):
        key = match.group(1) or match.group(2)
        if key and key not in FA:
            missing.add(key)
    assert not missing, f"Missing FA translations: {sorted(missing)[:20]}"


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


def test_login_page_shows_persian_year_when_fa(client):
    session = client.session
    session["ui_lang"] = "fa"
    session.save()
    response = client.get(reverse("marketing:login"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "۲۰۲۶" in html
    assert 'class="ui-fa' in html or "ui-fa" in html


def test_login_page_shows_latin_year_when_en(client):
    session = client.session
    session["ui_lang"] = "en"
    session.save()
    response = client.get(reverse("marketing:login"))
    html = response.content.decode()
    assert "2026" in html
    assert "۲۰۲۶" not in html


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
