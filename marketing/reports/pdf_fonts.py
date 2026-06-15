from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = Path(__file__).resolve().parent / "fonts"
REGULAR_FONT = "Vazirmatn"
BOLD_FONT = "Vazirmatn-Bold"

# Arabic/Persian blocks — used to decide when bidi shaping is required.
_RTL_CHAR_RANGES = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)


@dataclass(frozen=True)
class PdfLocale:
    lang: str = "en"
    unit: str = "rial"

    @property
    def rtl(self) -> bool:
        return self.lang == "fa"

    @property
    def currency_label(self) -> str:
        if self.lang == "fa":
            return "تومان" if self.unit == "toman" else "ریال"
        return "Toman" if self.unit == "toman" else "IRR"


def contains_rtl_script(text: str) -> bool:
    for char in text:
        code = ord(char)
        for start, end in _RTL_CHAR_RANGES:
            if start <= code <= end:
                return True
    return False


@lru_cache(maxsize=1)
def register_pdf_fonts() -> bool:
    regular = FONT_DIR / "Vazirmatn-Regular.ttf"
    bold = FONT_DIR / "Vazirmatn-Bold.ttf"
    if not regular.exists() or not bold.exists():
        return False
    if REGULAR_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(REGULAR_FONT, str(regular)))
    if BOLD_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(BOLD_FONT, str(bold)))
    return True


def shape_pdf_text(text: str | None, locale: PdfLocale) -> str:
    """Shape Persian/Arabic for ReportLab's LTR text engine.

    ReportLab places glyphs in storage order. ``arabic_reshaper`` joins letters and
    ``get_display`` reorders runs for visual RTL. Pure ASCII/Latin strings (invoice
    numbers, amounts) are left unchanged.
    """
    if text is None:
        return ""
    value = str(text)
    if not locale.rtl or not contains_rtl_script(value):
        return value
    return get_display(arabic_reshaper.reshape(value))


def shape_pdf_parts(parts: list[str], locale: PdfLocale) -> str:
    """Join logical fragments, shaping only segments that contain RTL script."""
    if not locale.rtl:
        return "".join(parts)
    return "".join(shape_pdf_text(part, locale) if contains_rtl_script(part) else part for part in parts)


def pdf_font_names(locale: PdfLocale) -> tuple[str, str]:
    if locale.rtl and register_pdf_fonts():
        return REGULAR_FONT, BOLD_FONT
    return "Helvetica", "Helvetica-Bold"


def pdf_styles(locale: PdfLocale) -> dict[str, ParagraphStyle]:
    regular, bold = pdf_font_names(locale)
    base = getSampleStyleSheet()
    align = TA_RIGHT if locale.rtl else TA_LEFT
    return {
        "title": ParagraphStyle(
            "PdfTitle",
            parent=base["Heading1"],
            fontName=bold,
            fontSize=16,
            alignment=align,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "PdfSubtitle",
            parent=base["Normal"],
            fontName=regular,
            fontSize=9,
            alignment=align,
            spaceAfter=10,
        ),
        "heading": ParagraphStyle(
            "PdfHeading",
            parent=base["Heading2"],
            fontName=bold,
            fontSize=12,
            alignment=align,
            spaceAfter=8,
        ),
        "cell": ParagraphStyle(
            "PdfCell",
            parent=base["Normal"],
            fontName=regular,
            fontSize=8,
            leading=11,
            alignment=align,
        ),
        "meta": ParagraphStyle(
            "PdfMeta",
            parent=base["Normal"],
            fontName=regular,
            fontSize=9,
            alignment=align,
            spaceAfter=10,
        ),
    }
