from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from marketing.models import CostBucket, PaymentStage
from marketing.money_format import FULL, format_money
from marketing.reports.pdf_fonts import (
    PdfLocale,
    pdf_font_names,
    pdf_styles,
    register_pdf_fonts,
    shape_pdf_text,
)
from marketing.translations import translate

ZERO = Decimal("0")

_PDF_STRINGS = {
    "generated": ("Generated", "تولید"),
    "filters": ("Filters", "فیلترها"),
    "vendors": ("Vendors", "وندورها"),
    "campaigns": ("Campaigns", "کمپین‌ها"),
    "contracts": ("Contracts", "قراردادها"),
    "total_spend": ("Total spend", "جمع هزینه"),
    "invoice_count": ("Invoice count", "تعداد فاکتور"),
    "vendor": ("Vendor", "وندور"),
    "invoices": ("Invoices", "فاکتورها"),
    "invoice_numbers": ("Invoice numbers", "شماره فاکتورها"),
    "stages": ("Stages", "مراحل"),
    "total": ("Total", "جمع"),
    "campaign": ("Campaign", "کمپین"),
    "year": ("Year", "سال"),
    "month": ("Month", "ماه"),
    "team": ("Team", "تیم"),
    "business_line": ("Business line", "خط کسب‌وکار"),
    "title": ("Title", "عنوان"),
    "stage": ("Stage", "مرحله"),
    "end_date": ("End date", "تاریخ پایان"),
    "days_left": ("Days left", "روز مانده"),
    "top_vendors": ("Top vendors", "برترین وندورها"),
    "payment_stages": ("Payment stages", "مراحل پرداخت"),
    "count": ("Count", "تعداد"),
    "search": ("Search", "جستجو"),
    "cost_bucket": ("Cost type", "نوع هزینه"),
}


def _label(key: str, locale: PdfLocale) -> str:
    en, fa = _PDF_STRINGS[key]
    return fa if locale.rtl else en


def _money_raw(value: Decimal | float | int | None, locale: PdfLocale) -> str:
    amount = value or ZERO
    return format_money(amount, FULL, locale.lang, locale.unit)


def _pdf_markup(text: str) -> str:
    return escape(text)


def _filter_line(filters: dict | None, locale: PdfLocale) -> str:
    if not filters:
        return ""
    bits: list[str] = []
    spec = (
        ("year", "year", None),
        ("month", "month", "month_label"),
        ("team", "team", "team_label"),
        ("business_section", "business_line", None),
        ("vendor", "vendor", "vendor_label"),
        ("stage", "stage", None),
        ("bucket", "cost_bucket", None),
        ("q", "search", None),
    )
    for key, label_key, display_key in spec:
        value = filters.get(key)
        if not value:
            continue
        display = filters.get(display_key) if display_key else value
        if key == "stage":
            stage_labels = dict(PaymentStage.choices)
            display = _localized_label(stage_labels.get(str(value), str(value)), locale)
        elif key == "bucket":
            bucket_labels = dict(CostBucket.choices)
            display = _localized_label(bucket_labels.get(str(value), str(value)), locale)
        elif not display:
            display = value
        label = _label(label_key, locale)
        bits.append(f"{label}: {display}")
    return ", ".join(bits)


def _doc(buffer: BytesIO, locale: PdfLocale) -> SimpleDocTemplate:
    left = right = 18 * mm
    if locale.rtl:
        left, right = 22 * mm, 14 * mm
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=left,
        rightMargin=right,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )


def _paragraph(text: str, style_name: str, locale: PdfLocale, styles: dict) -> Paragraph:
    return Paragraph(_pdf_markup(shape_pdf_text(text, locale)), styles[style_name])


def _header_story(
    styles: dict,
    locale: PdfLocale,
    title: str,
    generated_at,
    filters: dict | None,
) -> list:
    generated_stamp = generated_at.strftime("%Y-%m-%d %H:%M")
    generated_line = f"{_label('generated', locale)}: {generated_stamp}"

    story = [
        _paragraph(title, "title", locale, styles),
        _paragraph(generated_line, "subtitle", locale, styles),
    ]
    filter_line = _filter_line(filters, locale)
    if filter_line:
        filters_line = f"{_label('filters', locale)}: {filter_line}"
        story.append(_paragraph(filters_line, "subtitle", locale, styles))
    return story


def _build_header_row(
    items: list[str],
    locale: PdfLocale,
    styles: dict,
) -> list[Paragraph]:
    if locale.rtl:
        items = list(reversed(items))
    return [_cell(text, locale, styles) for text in items]


def _table_style(header_color: str, locale: PdfLocale, *, body_font: str, header_font: str) -> TableStyle:
    align = "RIGHT" if locale.rtl else "LEFT"
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), header_font),
            ("FONTNAME", (0, 1), (-1, -1), body_font),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), align),
        ]
    )


def _styled_table(
    data: list,
    col_widths: list,
    header_color: str,
    locale: PdfLocale,
) -> Table:
    body_font, header_font = pdf_font_names(locale)
    register_pdf_fonts()
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_table_style(header_color, locale, body_font=body_font, header_font=header_font))
    return table


def _cell(text: str, locale: PdfLocale, styles: dict) -> Paragraph:
    return Paragraph(_pdf_markup(shape_pdf_text(text, locale)), styles["cell"])


def _total_currency_header(locale: PdfLocale) -> str:
    return f"{_label('total', locale)} ({locale.currency_label})"


def _total_spend_currency_header(locale: PdfLocale) -> str:
    return f"{_label('total_spend', locale)} ({locale.currency_label})"


def _currency_header_cell(locale: PdfLocale, styles: dict, *, spend: bool = False) -> Paragraph:
    text = _total_spend_currency_header(locale) if spend else _total_currency_header(locale)
    return _cell(text, locale, styles)


def _localized_label(label: str, locale: PdfLocale) -> str:
    if not label:
        return ""
    if locale.lang == "fa":
        return translate(label, "fa")
    return label


def _append_count_and_spend_meta(
    story: list,
    styles: dict,
    locale: PdfLocale,
    *,
    count_label_key: str,
    count: int,
    total_spend: Decimal,
) -> None:
    meta = (
        f"{_label(count_label_key, locale)}: {count}"
        f"    {_label('total_spend', locale)} ({locale.currency_label}): {_money_raw(total_spend, locale)}"
    )
    story.append(_paragraph(meta, "meta", locale, styles))


def build_vendor_report_pdf(
    *,
    title: str,
    generated_at,
    vendor_rows: list[dict],
    filters: dict | None = None,
    locale: PdfLocale | None = None,
) -> bytes:
    locale = locale or PdfLocale()
    styles = pdf_styles(locale)
    buffer = BytesIO()
    doc = _doc(buffer, locale)
    story = _header_story(styles, locale, title, generated_at, filters)

    total_spend = sum((row.get("total") or ZERO for row in vendor_rows), ZERO)
    _append_count_and_spend_meta(
        story,
        styles,
        locale,
        count_label_key="vendors",
        count=len(vendor_rows),
        total_spend=total_spend,
    )

    table_data = [
        _build_header_row(
            [
                _label("vendor", locale),
                _label("invoices", locale),
                _label("invoice_numbers", locale),
                _label("stages", locale),
                _total_currency_header(locale),
            ],
            locale,
            styles,
        )
    ]
    for row in vendor_rows:
        vendor = row.get("vendor")
        vendor_name = vendor.name if vendor is not None else (row.get("vendor__name") or "")
        numbers = ", ".join(row.get("invoice_numbers", []))
        stages = ", ".join(_localized_label(stage, locale) for stage in row.get("stages", []))
        cells = [
            _cell(vendor_name, locale, styles),
            _cell(str(row.get("invoice_count", "")), locale, styles),
            _cell(numbers, locale, styles),
            _cell(stages, locale, styles),
            _cell(_money_raw(row.get("total"), locale), locale, styles),
        ]
        if locale.rtl:
            cells.reverse()
        table_data.append(cells)

    widths = [42 * mm, 16 * mm, 50 * mm, 30 * mm, 28 * mm]
    if locale.rtl:
        widths.reverse()
    story.append(_styled_table(table_data, widths, "#0f766e", locale))
    doc.build(story)
    return buffer.getvalue()


def build_campaign_report_pdf(
    *,
    title: str,
    generated_at,
    campaign_rows: list[dict],
    filters: dict | None = None,
    locale: PdfLocale | None = None,
) -> bytes:
    locale = locale or PdfLocale()
    styles = pdf_styles(locale)
    buffer = BytesIO()
    doc = _doc(buffer, locale)
    story = _header_story(styles, locale, title, generated_at, filters)

    total_spend = sum((row.get("total") or ZERO for row in campaign_rows), ZERO)
    _append_count_and_spend_meta(
        story,
        styles,
        locale,
        count_label_key="campaigns",
        count=len(campaign_rows),
        total_spend=total_spend,
    )

    table_data = [
        _build_header_row(
            [
                _label("campaign", locale),
                _label("year", locale),
                _label("team", locale),
                _label("invoices", locale),
                _total_currency_header(locale),
            ],
            locale,
            styles,
        )
    ]
    for row in campaign_rows:
        cells = [
            _cell(row.get("campaign__name") or "", locale, styles),
            _cell(str(row.get("campaign__year") or ""), locale, styles),
            _cell(row.get("campaign__team__name") or "", locale, styles),
            _cell(str(row.get("invoice_count", "")), locale, styles),
            _cell(_money_raw(row.get("total"), locale), locale, styles),
        ]
        if locale.rtl:
            cells.reverse()
        table_data.append(cells)

    widths = [55 * mm, 16 * mm, 40 * mm, 20 * mm, 28 * mm]
    if locale.rtl:
        widths.reverse()
    story.append(_styled_table(table_data, widths, "#7c3aed", locale))
    doc.build(story)
    return buffer.getvalue()


def build_contract_report_pdf(
    *,
    title: str,
    generated_at,
    contracts,
    filters: dict | None = None,
    locale: PdfLocale | None = None,
) -> bytes:
    locale = locale or PdfLocale()
    styles = pdf_styles(locale)
    buffer = BytesIO()
    doc = _doc(buffer, locale)
    story = _header_story(styles, locale, title, generated_at, filters)

    contracts = list(contracts)
    story.append(_paragraph(f"{_label('contracts', locale)}: {len(contracts)}", "meta", locale, styles))

    table_data = [
        _build_header_row(
            [
                _label("title", locale),
                _label("vendor", locale),
                _label("team", locale),
                _label("stage", locale),
                _label("end_date", locale),
                _label("days_left", locale),
            ],
            locale,
            styles,
        )
    ]
    for contract in contracts:
        days = contract.days_until_expiry
        days_text = "-" if days is None else str(days)
        end_text = contract.end_date.isoformat() if contract.end_date else "-"
        cells = [
            _cell(contract.title, locale, styles),
            _cell(contract.vendor.name, locale, styles),
            _cell(contract.team.name if contract.team else "-", locale, styles),
            _cell(_localized_label(contract.get_stage_display(), locale), locale, styles),
            _cell(end_text, locale, styles),
            _cell(days_text, locale, styles),
        ]
        if locale.rtl:
            cells.reverse()
        table_data.append(cells)

    widths = [40 * mm, 36 * mm, 28 * mm, 30 * mm, 22 * mm, 18 * mm]
    if locale.rtl:
        widths.reverse()
    story.append(_styled_table(table_data, widths, "#b45309", locale))
    doc.build(story)
    return buffer.getvalue()


def build_dashboard_summary_pdf(
    *,
    title: str,
    generated_at,
    total_spend: Decimal,
    invoice_count: int,
    vendor_rows: list[dict],
    stage_rows,
    filters: dict | None = None,
    locale: PdfLocale | None = None,
) -> bytes:
    locale = locale or PdfLocale()
    styles = pdf_styles(locale)
    buffer = BytesIO()
    doc = _doc(buffer, locale)
    story = _header_story(styles, locale, title, generated_at, filters)

    summary_data = [
        [
            _currency_header_cell(locale, styles, spend=True),
            _cell(_money_raw(total_spend, locale), locale, styles),
        ],
        [
            _cell(_label("invoice_count", locale), locale, styles),
            _cell(str(invoice_count), locale, styles),
        ],
    ]
    if locale.rtl:
        summary_data = [[row[1], row[0]] for row in summary_data]

    body_font, header_font = pdf_font_names(locale)
    summary_table = Table(summary_data, colWidths=[70 * mm, 90 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3f7")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("FONTNAME", (0, 0), (0, -1), header_font),
                ("FONTNAME", (1, 0), (1, -1), body_font),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT" if locale.rtl else "LEFT"),
            ]
        )
    )
    story.extend([summary_table, Spacer(1, 10)])

    if vendor_rows:
        story.append(_paragraph(_label("top_vendors", locale), "heading", locale, styles))
        vendor_table_data = [
            _build_header_row(
                [
                    _label("vendor", locale),
                    _label("invoices", locale),
                    _total_currency_header(locale),
                ],
                locale,
                styles,
            )
        ]
        for row in vendor_rows[:15]:
            cells = [
                _cell(row.get("vendor__name") or getattr(row.get("vendor"), "name", ""), locale, styles),
                _cell(str(row.get("invoice_count", "")), locale, styles),
                _cell(_money_raw(row.get("total"), locale), locale, styles),
            ]
            if locale.rtl:
                cells.reverse()
            vendor_table_data.append(cells)
        widths = [80 * mm, 25 * mm, 55 * mm]
        if locale.rtl:
            widths.reverse()
        story.extend([_styled_table(vendor_table_data, widths, "#0f766e", locale), Spacer(1, 10)])

    if stage_rows:
        story.append(_paragraph(_label("payment_stages", locale), "heading", locale, styles))
        stage_table_data = [
            _build_header_row(
                [
                    _label("stage", locale),
                    _label("count", locale),
                ],
                locale,
                styles,
            )
        ]
        for row in stage_rows:
            stage_key = str(row.get("payment_stage", ""))
            stage_labels = dict(PaymentStage.choices)
            stage_label = _localized_label(stage_labels.get(stage_key, stage_key), locale)
            cells = [_cell(stage_label, locale, styles), _cell(str(row.get("invoice_count", "")), locale, styles)]
            if locale.rtl:
                cells.reverse()
            stage_table_data.append(cells)
        widths = [80 * mm, 40 * mm]
        if locale.rtl:
            widths.reverse()
        story.append(_styled_table(stage_table_data, widths, "#2563eb", locale))

    doc.build(story)
    return buffer.getvalue()
