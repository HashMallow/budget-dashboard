from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from marketing.models import Invoice, SpendCategory, Team, Vendor
from marketing.tests.test_excel_importer import write_mapping, write_workbook
from marketing.tests.test_phase2_features import _append_data_sheet

pytestmark = pytest.mark.django_db


@pytest.fixture
def full_workbook(tmp_path):
    import yaml

    workbook_path = tmp_path / "full.xlsx"
    mapping_path = tmp_path / "column_mapping.yml"
    write_workbook(workbook_path)
    _append_data_sheet(workbook_path)
    write_mapping(mapping_path, workbook_path)
    mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8"))
    mapping["sheets"]["lookup_data"] = {
        "actual_sheet_name": "Data",
        "header_row": 1,
        "columns": {
            "requester_name": "requester",
            "vendor_name": "Vendor List",
            "unique_vendor_name": "Vendor list unique",
            "title": "Title",
            "unique_title": "Title list unique",
            "sub_team": "sub team",
        },
    }
    mapping_path.write_text(yaml.safe_dump(mapping, allow_unicode=True), encoding="utf-8")
    return workbook_path


def test_import_page_loads_for_admin(client):
    admin = get_user_model().objects.create_superuser(username="import-admin", password="test-pass")
    client.force_login(admin)

    response = client.get(reverse("marketing:import_workbook"))

    assert response.status_code == 200
    assert b"Confirm and import to database" not in response.content
    assert b"No file checked yet." in response.content


def test_import_page_forbidden_for_non_admin(client):
    user = get_user_model().objects.create_user(username="regular", password="test-pass")
    client.force_login(user)

    response = client.get(reverse("marketing:import_workbook"))

    assert response.status_code == 403


def test_dry_run_does_not_persist_data(client, full_workbook):
    admin = get_user_model().objects.create_superuser(username="import-admin", password="test-pass")
    client.force_login(admin)

    with full_workbook.open("rb") as workbook_file:
        response = client.post(
            reverse("marketing:import_workbook"),
            {"action": "dry_run", "workbook": workbook_file},
        )

    assert response.status_code == 200
    assert b"Confirm and import to database" in response.content
    assert Invoice.objects.count() == 0
    assert SpendCategory.objects.count() == 0


def test_confirm_imports_invoices_budget_and_lookups(client, full_workbook):
    admin = get_user_model().objects.create_superuser(username="import-admin", password="test-pass")
    client.force_login(admin)

    with full_workbook.open("rb") as workbook_file:
        client.post(
            reverse("marketing:import_workbook"),
            {"action": "dry_run", "workbook": workbook_file},
        )

    response = client.post(reverse("marketing:import_workbook"), {"action": "confirm"})

    assert response.status_code == 200
    assert Invoice.objects.count() == 2
    assert Team.objects.filter(name="Growth").exists()
    assert Vendor.objects.filter(name="Test Vendor").exists()
    assert SpendCategory.objects.filter(name="Performance").exists()
    assert b"Excel data and reference lookups imported into the database." in response.content


def test_confirm_without_pending_file_shows_error(client):
    admin = get_user_model().objects.create_superuser(username="import-admin", password="test-pass")
    client.force_login(admin)

    response = client.post(reverse("marketing:import_workbook"), {"action": "confirm"})

    assert response.status_code == 200
    assert b"There is no file ready to import." in response.content
    assert Invoice.objects.count() == 0


def test_dry_run_summary_includes_invoice_and_lookup_sections(client, full_workbook):
    admin = get_user_model().objects.create_superuser(username="import-admin", password="test-pass")
    client.force_login(admin)

    with full_workbook.open("rb") as workbook_file:
        response = client.post(
            reverse("marketing:import_workbook"),
            {"action": "dry_run", "workbook": workbook_file},
        )

    html = response.content.decode()
    for label in (
        "Teams",
        "Vendors (invoices)",
        "Invoices",
        "Budget",
        "Vendors (lookup)",
        "Categories",
        "Sub teams",
        "Requesters",
    ):
        assert label in html
