from __future__ import annotations

from marketing.money_format import (
    COMPACT,
    FULL,
    RIAL,
    TOMAN,
    activate_money_display,
    reset_money_display,
)


class MoneyDisplayMiddleware:
    """Expose money-display preferences on the request and in template filters."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        mode = request.session.get("money_format", COMPACT)
        if mode not in {FULL, COMPACT}:
            mode = COMPACT
        request.money_format = mode

        unit = request.session.get("currency_unit", RIAL)
        if unit not in {RIAL, TOMAN}:
            unit = RIAL
        request.currency_unit = unit

        ui_lang = request.session.get("ui_lang", "en")
        if ui_lang not in {"fa", "en"}:
            ui_lang = "en"

        token = activate_money_display(mode, ui_lang, unit)
        try:
            return self.get_response(request)
        finally:
            reset_money_display(token)
