from __future__ import annotations


def display_preferences(request):
    # The UI supports an English/Persian toggle. English is the default and the source
    # language for all static text; Persian is provided via marketing/translations.py.
    # Data values from the Excel workbook (team/vendor/campaign names) are shown as imported.
    ui_lang = request.session.get("ui_lang", "en")
    if ui_lang not in {"fa", "en"}:
        ui_lang = "en"

    return {
        "ui_lang": ui_lang,
        "number_locale": "en",
        "html_lang": "fa" if ui_lang == "fa" else "en",
        "html_dir": "rtl" if ui_lang == "fa" else "ltr",
    }
