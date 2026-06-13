from __future__ import annotations


def display_preferences(request):
    ui_lang = request.session.get("ui_lang", "fa")
    if ui_lang not in {"fa", "en"}:
        ui_lang = "fa"

    number_locale = request.session.get("number_locale", "fa" if ui_lang == "fa" else "en")
    if number_locale not in {"fa", "en"}:
        number_locale = "fa" if ui_lang == "fa" else "en"

    return {
        "ui_lang": ui_lang,
        "number_locale": number_locale,
        "html_lang": "fa" if ui_lang == "fa" else "en",
        "html_dir": "rtl" if ui_lang == "fa" else "ltr",
    }
