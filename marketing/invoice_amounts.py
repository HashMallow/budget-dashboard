"""Invoice amount breakdown: action cost, VAT, insurance withholding, paid amount.

Business rules (from voice feedback, June 2026):
- Invoice total = action cost + 10% VAT (unless tax is entered explicitly).
- Insurance is withheld from the vendor share of action cost (16.67% or 7.78% typical).
- Paid amount = (action cost − insurance) + tax.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

DEFAULT_TAX_RATE_PERCENT = Decimal("10")
ZERO = Decimal("0")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def calculate_tax_amount(
    action_cost: Decimal,
    *,
    tax_amount: Decimal | None = None,
    apply_tax: bool = True,
) -> Decimal:
    if tax_amount is not None:
        return quantize_money(tax_amount)
    if apply_tax and action_cost > ZERO:
        return quantize_money(action_cost * DEFAULT_TAX_RATE_PERCENT / Decimal("100"))
    return ZERO


def calculate_insurance_amount(action_cost: Decimal, insurance_rate_percent: Decimal | None) -> Decimal:
    if not insurance_rate_percent or insurance_rate_percent <= ZERO or action_cost <= ZERO:
        return ZERO
    return quantize_money(action_cost * insurance_rate_percent / Decimal("100"))


def calculate_invoice_amounts(
    action_cost: Decimal,
    *,
    tax_amount: Decimal | None = None,
    apply_tax: bool = True,
    insurance_rate_percent: Decimal | None = None,
    paid_amount: Decimal | None = None,
) -> dict[str, Decimal]:
    """Return action/tax/insurance/invoice-total/paid amounts from action cost."""
    tax = calculate_tax_amount(action_cost, tax_amount=tax_amount, apply_tax=apply_tax)
    insurance = calculate_insurance_amount(action_cost, insurance_rate_percent)
    invoice_total = quantize_money(action_cost + tax)
    if paid_amount is not None:
        net_paid = quantize_money(paid_amount)
    else:
        net_paid = quantize_money(action_cost - insurance + tax)
    return {
        "action_cost_amount": quantize_money(action_cost),
        "tax_amount": tax,
        "insurance_amount": insurance,
        "amount": invoice_total,
        "paid_amount": net_paid,
    }


def infer_action_cost_from_invoice_total(invoice_total: Decimal, *, has_tax: bool = True) -> Decimal:
    """Best-effort backfill when only invoice total is known."""
    if invoice_total <= ZERO:
        return ZERO
    if has_tax:
        return quantize_money(invoice_total / (Decimal("1") + DEFAULT_TAX_RATE_PERCENT / Decimal("100")))
    return quantize_money(invoice_total)
