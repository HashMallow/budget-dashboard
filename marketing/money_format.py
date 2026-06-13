from __future__ import annotations

from contextvars import ContextVar, Token
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

FULL = "full"
COMPACT = "compact"
MODES = {FULL, COMPACT}

# Currency display units. Source data is stored in Rial (IRR). Toman is a display-only
# convenience: 1 Toman = 10 Rial, so the unit conversion never touches stored values.
RIAL = "rial"
TOMAN = "toman"
UNITS = {RIAL, TOMAN}
_UNIT_DIVISOR = {RIAL: Decimal("1"), TOMAN: Decimal("10")}

_UNIT_LABELS = {
    RIAL: {"en": "IRR", "fa": "ریال"},
    TOMAN: {"en": "Toman", "fa": "تومان"},
}

_DEFAULT_DISPLAY = {"mode": COMPACT, "lang": "en", "unit": RIAL}

_display_ctx: ContextVar[dict[str, str] | None] = ContextVar(
    "money_display_ctx",
    default=None,
)

_FA_COMPACT_SUFFIXES = ("تریلیون", "میلیارد", "میلیون", "هزار")


def split_fa_compact_amount(formatted: str) -> tuple[str, str] | None:
    """Split ``25 میلیون`` into number and Persian scale word."""
    for suffix in _FA_COMPACT_SUFFIXES:
        token = f" {suffix}"
        if formatted.endswith(token):
            return formatted[: -len(token)], suffix
    return None


# (minimum absolute value, divisor, English suffix, Persian suffix)
_COMPACT_SCALES = (
    (Decimal("1000000000000"), Decimal("1000000000000"), "T", "تریلیون"),
    (Decimal("1000000000"), Decimal("1000000000"), "B", "میلیارد"),
    (Decimal("1000000"), Decimal("1000000"), "M", "میلیون"),
    (Decimal("1000"), Decimal("1000"), "K", "هزار"),
)


def _to_decimal(value) -> Decimal | None:
    if value in {None, ""}:
        return Decimal("0")
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _convert_unit(amount: Decimal, unit: str) -> Decimal:
    divisor = _UNIT_DIVISOR.get(unit, Decimal("1"))
    if divisor == Decimal("1"):
        return amount
    return amount / divisor


def _format_integer(amount: Decimal) -> str:
    quantized = amount.to_integral_value(rounding=ROUND_HALF_UP)
    return f"{quantized:,}"


def _compact_decimals(abs_amount: Decimal, divisor: Decimal) -> int:
    scaled = abs_amount / divisor
    if scaled >= Decimal("100"):
        return 0
    if scaled >= Decimal("10"):
        return 1
    return 2


def unit_label(unit: str = RIAL, lang: str = "en") -> str:
    labels = _UNIT_LABELS.get(unit, _UNIT_LABELS[RIAL])
    return labels.get(lang, labels["en"])


def format_money(value, mode: str = FULL, lang: str = "en", unit: str = RIAL) -> str:
    """Format a stored Rial amount for display.

    ``mode`` controls ``compact`` (K/M/B/T or Persian equivalents) vs ``full`` grouping.
    ``unit`` controls Rial vs Toman; Toman divides the stored Rial value by 10. The two are
    independent, so Toman works the same in compact and full modes.
    """
    amount = _to_decimal(value)
    if amount is None:
        return str(value)

    amount = _convert_unit(amount, unit)

    if mode != COMPACT:
        return _format_integer(amount)

    abs_amount = abs(amount)
    if abs_amount < Decimal("1000"):
        return _format_integer(amount)

    for threshold, divisor, en_suffix, fa_suffix in _COMPACT_SCALES:
        if abs_amount >= threshold:
            decimals = _compact_decimals(abs_amount, divisor)
            scaled = (amount / divisor).quantize(
                Decimal("1").scaleb(-decimals),
                rounding=ROUND_HALF_UP,
            )
            suffix = fa_suffix if lang == "fa" else en_suffix
            if decimals:
                formatted = f"{scaled:,.{decimals}f}".rstrip("0").rstrip(".")
            else:
                formatted = f"{scaled:,.0f}"
            if lang == "fa":
                return f"{formatted} {suffix}"
            return f"{formatted}{suffix}"

    return _format_integer(amount)


def format_money_full(value, unit: str = RIAL) -> str:
    """Always return the exact comma-separated integer (for titles/tooltips)."""
    return format_money(value, FULL, "en", unit)


def activate_money_display(mode: str, lang: str, unit: str = RIAL) -> Token:
    return _display_ctx.set({"mode": mode, "lang": lang, "unit": unit})


def reset_money_display(token: Token) -> None:
    _display_ctx.reset(token)


def current_money_display() -> dict[str, str]:
    ctx = _display_ctx.get()
    if ctx is None:
        return dict(_DEFAULT_DISPLAY)
    return ctx
