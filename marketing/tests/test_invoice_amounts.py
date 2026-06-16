from decimal import Decimal

from marketing.invoice_amounts import calculate_invoice_amounts, infer_action_cost_from_invoice_total


def test_calculate_invoice_amounts_with_tax_and_insurance():
    result = calculate_invoice_amounts(
        Decimal("100000000"),
        insurance_rate_percent=Decimal("16.67"),
    )
    assert result["tax_amount"] == Decimal("10000000")
    assert result["amount"] == Decimal("110000000")
    assert result["insurance_amount"] == Decimal("16670000")
    assert result["paid_amount"] == Decimal("93330000")


def test_calculate_invoice_amounts_without_insurance():
    result = calculate_invoice_amounts(Decimal("50000000"))
    assert result["tax_amount"] == Decimal("5000000")
    assert result["amount"] == Decimal("55000000")
    assert result["paid_amount"] == Decimal("55000000")


def test_infer_action_cost_from_invoice_total():
    action = infer_action_cost_from_invoice_total(Decimal("110000000"))
    assert action == Decimal("100000000")
