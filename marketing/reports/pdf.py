from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from marketing.models import PaymentStage
from marketing.money_format import TOMAN, format_money_full
from marketing.reports.pdf_fonts import (
    PdfLocale,
    pdf_font_names,
    pdf_styles,
    register_pdf_fonts,
    shape_pdf_parts,
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
    "team": ("Team", "تیم"),
    "title": ("Title", "عنوان"),
    "stage": ("Stage", "مرحله"),
    "end_date": ("End date", "تاریخ پایان"),
    "days_left": ("Days left", "روز مانده"),
    "top_vendors": ("Top vendors", "برترین وندورها"),
    "payment_stages": ("Payment stages", "مراحل پرداخت"),
    "count": ("Count", "تعداد"),
}


def _label(key: str, locale: PdfLocale) -> str:
    en, fa = _PDF_STRINGS[key]
    return fa if locale.rtl else en


def _money_raw(value: Decimal | float | int | None, locale: PdfLocale) -> str:
    amount = value or ZERO
    if locale.unit == TOMAN:
        return format_money_full(amount, TOMAN)
    return format_money_full(amount)


def _filter_line(filters: dict | None, locale: PdfLocale) -> str:
    bits = []
    for key in ("year", "team", "stage", "bucket", "q"):
        value = (filters or {}).get(key)
        if value:
            bits.append(f"{key}={value}")
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


def _paragraph(text: str, style_name: str, locale: PdfLocale, styles: dict, *, shaped: bool = False) -> Paragraph:
    content = text if shaped else shape_pdf_text(text, locale)
    return Paragraph(content, styles[style_name])


def _header_story(
    styles: dict,
    locale: PdfLocale,
    title: str,
    generated_at,
    filters: dict | None,
) -> list:
    generated_stamp = generated_at.strftime("%Y-%m-%d %H:%M")
    if locale.rtl:
        generated_line = shape_pdf_parts([_label("generated", locale), ": ", generated_stamp], locale)
    else:
        generated_line = f"{_label('generated', locale)}: {generated_stamp}"

    story = [
        _paragraph(title, "title", locale, styles),
        _paragraph(generated_line, "subtitle", locale, styles, shaped=locale.rtl),
    ]
    filter_line = _filter_line(filters, locale)
    if filter_line:
        if locale.rtl:
            filters_line = shape_pdf_parts([_label("filters", locale), ": ", filter_line], locale)
        else:
            filters_line = f"{_label('filters', locale)}: {filter_line}"
        story.append(_paragraph(filters_line, "subtitle", locale, styles, shaped=locale.rtl))
    return story


def _build_header_row(
    items: list[tuple[str, bool]],
    locale: PdfLocale,
    styles: dict,
) -> list[Paragraph]:
    if locale.rtl:
        items = list(reversed(items))
    return [_cell(text, locale, styles, shaped=shaped) for text, shaped in items]


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


def _cell(text: str, locale: PdfLocale, styles: dict, *, shaped: bool = False) -> Paragraph:
    content = text if shaped else shape_pdf_text(text, locale)
    return Paragraph(content, styles["cell"])


def _total_currency_header(locale: PdfLocale) -> str:
    if locale.rtl:
        return shape_pdf_parts([_label("total", locale), " (", locale.currency_label, ")"], locale)
    return f"{_label('total', locale)} ({locale.currency_label})"


def _total_spend_currency_header(locale: PdfLocale) -> str:
    if locale.rtl:
        return shape_pdf_parts([_label("total_spend", locale), " (", locale.currency_label, ")"], locale)
    return f"{_label('total_spend', locale)} ({locale.currency_label})"


def _currency_header_cell(locale: PdfLocale, styles: dict, *, spend: bool = False) -> Paragraph:
    text = _total_spend_currency_header(locale) if spend else _total_currency_header(locale)
    return _cell(text, locale, styles, shaped=locale.rtl)


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
    if locale.rtl:
        meta = shape_pdf_parts(
            [
                _label(count_label_key, locale),
                ": ",
                str(count),
                "    ",
                _label("total_spend", locale),
                " (",
                locale.currency_label,
                "): ",
                _money_raw(total_spend, locale),
            ],
            locale,
        )
        story.append(_paragraph(meta, "meta", locale, styles, shaped=True))
        return
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
                (_label("vendor", locale), False),
                (_label("invoices", locale), False),
                (_label("invoice_numbers", locale), False),
                (_label("stages", locale), False),
                (_total_currency_header(locale), True),
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
                (_label("campaign", locale), False),
                (_label("year", locale), False),
                (_label("team", locale), False),
                (_label("invoices", locale), False),
                (_total_currency_header(locale), True),
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
    if locale.rtl:
        contracts_meta = shape_pdf_parts(
            [_label("contracts", locale), ": ", str(len(contracts))],
            locale,
        )
        story.append(_paragraph(contracts_meta, "meta", locale, styles, shaped=True))
    else:
        story.append(_paragraph(f"{_label('contracts', locale)}: {len(contracts)}", "meta", locale, styles))

    table_data = [
        _build_header_row(
            [
                (_label("title", locale), False),
                (_label("vendor", locale), False),
                (_label("team", locale), False),
                (_label("stage", locale), False),
                (_label("end_date", locale), False),
                (_label("days_left", locale), False),
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
                    (_label("vendor", locale), False),
                    (_label("invoices", locale), False),
                    (_total_currency_header(locale), True),
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
                    (_label("stage", locale), False),
                    (_label("count", locale), False),
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
