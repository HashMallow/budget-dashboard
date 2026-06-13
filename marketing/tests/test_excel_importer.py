from __future__ import annotations

from datetime import date

import pytest
import yaml
from openpyxl import Workbook

from marketing.importers.excel import import_marketing_workbook
from marketing.models import BudgetLine, CostBucket, Invoice, PaymentStage, Team, TeamAlias, Vendor

pytestmark = pytest.mark.django_db


def write_mapping(path, workbook_path):
    mapping = {
        "workbook": str(workbook_path),
        "sheets": {
            "invoices": {
                "actual_sheet_name": "Invoices",
                "header_row": 1,
                "data_start_row": 2,
                "data_end_row": 3,
                "columns": {
                    "year": "Year",
                    "team": "MKT Team",
                    "category": "Budget Line",
                    "campaign_name": "Campaign Name",
                    "vendor_name": "Vendor Name",
                    "description": "Description",
                    "invoice_date_gregorian_serial": "invoice date in gregorian",
                    "invoice_date_jalali_serial": "invoice date in Jalali",
                    "invoice_number": "Invoice Number",
                    "amount": "Invoice Amount (IRR)",
                    "payment_stage": "payment state",
                    "jalali_invoice_date_text_candidate": "blank_AC",
                },
                "derived_values": {
                    "currency": "IRR",
                    "cost_bucket": {
                        "default": "TEAM",
                        "rules": [
                            {
                                "bucket": "REFERRAL",
                                "when_any_source_column_contains": ["referral", "ریفرال"],
                                "source_columns": ["MKT Team", "Budget Line", "Vendor Name", "Description"],
                            }
                        ],
                    },
                    "payment_stage_mapping": {"Paid": "PAID", "Finance": "FINANCE_REVIEW"},
                },
            },
            "budget": {
                "actual_sheet_name": "Budget",
                "header_row": 1,
                "data_start_row": 2,
                "data_end_row": 2,
                "row_context_columns": {
                    "team": "Team",
                    "category_or_title": "Title",
                    "description": "Description",
                    "currency": "Unit Price",
                },
                "budget_line_mapping": {"year": 1405},
                "monthly_columns": [
                    {
                        "month_number": 1,
                        "month_label": "Farvardin",
                        "projection_column": "E",
                        "actual_column": "F",
                    },
                    {
                        "month_number": 2,
                        "month_label": "Ordibehesht",
                        "projection_column": "G",
                        "actual_column": "H",
                    },
                ],
            },
        },
    }
    path.write_text(yaml.safe_dump(mapping, allow_unicode=True), encoding="utf-8")


def write_workbook(path):
    workbook = Workbook()
    invoices = workbook.active
    invoices.title = "Invoices"
    invoices.append(
        [
            "Year",
            "MKT Team",
            "Budget Line",
            "Campaign Name",
            "Vendor Name",
            "Description",
            "invoice date in gregorian",
            "invoice date in Jalali",
            "Invoice Number",
            "Invoice Amount (IRR)",
            "payment state",
            None,
            None,
            None,
            "blank_AC",
        ]
    )
    invoices.append(
        [
            1405,
            "Growth",
            "Performance",
            "on going",
            "Test Vendor",
            "Regular invoice",
            date(2026, 3, 30),
            None,
            "1",
            1000,
            "Paid",
            None,
            None,
            None,
            "1405/01/10",
        ]
    )
    invoices.append(
        [
            1405,
            "Referral",
            "referral",
            "on going",
            "Test Vendor",
            "Referral invoice",
            date(2026, 4, 20),
            None,
            "1",
            2000,
            "Finance",
            None,
            None,
            None,
            "1405/01/31",
        ]
    )

    budget = workbook.create_sheet("Budget")
    budget.append(["Team", "Title", "Description", "Unit Price", "projection", "Actual", "projection", "Actual"])
    budget.append(["Growth", "Performance", "test budget", "Rial", 3000, 1000, 4000, 0])
    workbook.save(path)


def test_import_workbook_creates_invoices_budget_lines_and_preserves_duplicates(tmp_path):
    workbook_path = tmp_path / "marketing.xlsx"
    mapping_path = tmp_path / "column_mapping.yml"
    write_workbook(workbook_path)
    write_mapping(mapping_path, workbook_path)

    result = import_marketing_workbook(workbook_path, mapping_path=mapping_path)

    assert result.invoices.created == 2
    assert result.budget_lines.created == 2
    assert Invoice.objects.count() == 2
    assert Vendor.objects.count() == 1
    assert Team.objects.filter(name="Growth").exists()
    assert Team.objects.filter(name="Referral").exists()
    assert Invoice.objects.filter(invoice_number="1", vendor__name="Test Vendor").count() == 2
    assert Invoice.objects.filter(cost_bucket=CostBucket.REFERRAL).count() == 1
    assert Invoice.objects.filter(payment_stage=PaymentStage.PAID).count() == 1
    assert Invoice.objects.filter(payment_stage=PaymentStage.FINANCE_REVIEW).count() == 1
    assert BudgetLine.objects.count() == 2

    second_result = import_marketing_workbook(workbook_path, mapping_path=mapping_path)

    assert second_result.invoices.created == 0
    assert second_result.invoices.updated == 2
    assert second_result.budget_lines.created == 0
    assert second_result.budget_lines.updated == 2
    assert Invoice.objects.count() == 2
    assert BudgetLine.objects.count() == 2


def test_dry_run_does_not_write_database(tmp_path):
    workbook_path = tmp_path / "marketing.xlsx"
    mapping_path = tmp_path / "column_mapping.yml"
    write_workbook(workbook_path)
    write_mapping(mapping_path, workbook_path)

    result = import_marketing_workbook(workbook_path, mapping_path=mapping_path, dry_run=True)

    assert result.invoices.created == 2
    assert result.budget_lines.created == 2
    assert Invoice.objects.count() == 0
    assert BudgetLine.objects.count() == 0
    assert Vendor.objects.count() == 0


def test_import_resolves_team_aliases(tmp_path):
    workbook_path = tmp_path / "marketing.xlsx"
    mapping_path = tmp_path / "column_mapping.yml"
    write_workbook(workbook_path)
    write_mapping(mapping_path, workbook_path)

    canonical = Team.objects.create(name="Ops & Analytics", slug="ops-analytics")
    TeamAlias.objects.create(raw_name="Growth", team=canonical)

    import_marketing_workbook(workbook_path, mapping_path=mapping_path)

    invoice = Invoice.objects.get(invoice_number="1", cost_bucket=CostBucket.TEAM)
    assert invoice.team == canonical
    assert not Team.objects.filter(name="Growth").exists()
