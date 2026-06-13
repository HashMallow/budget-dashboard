from __future__ import annotations

from marketing.money_format import COMPACT, FULL, RIAL, TOMAN, unit_label


def display_preferences(request):
    # The UI supports an English/Persian toggle. English is the default and the source
    # language for all static text; Persian is provided via marketing/translations.py.
    # Data values from the Excel workbook (team/vendor/campaign names) are shown as imported.
    ui_lang = request.session.get("ui_lang", "en")
    if ui_lang not in {"fa", "en"}:
        ui_lang = "en"

    money_format = getattr(request, "money_format", request.session.get("money_format", COMPACT))
    if money_format not in {FULL, COMPACT}:
        money_format = COMPACT

    currency_unit = getattr(request, "currency_unit", request.session.get("currency_unit", RIAL))
    if currency_unit not in {RIAL, TOMAN}:
        currency_unit = RIAL

    theme = request.session.get("theme", "light")
    if theme not in {"light", "dark"}:
        theme = "light"

    return {
        "ui_lang": ui_lang,
        "number_locale": "fa" if ui_lang == "fa" else "en",
        "html_lang": "fa" if ui_lang == "fa" else "en",
        "html_dir": "rtl" if ui_lang == "fa" else "ltr",
        "money_format": money_format,
        "currency_unit": currency_unit,
        "currency_label": unit_label(currency_unit, ui_lang),
        "theme": theme,
    }
