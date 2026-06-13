from __future__ import annotations

from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ZERO = Decimal("0")


def _money(value: Decimal | float | int | None) -> str:
    amount = value or ZERO
    return f"{amount:,.0f}"


def _filter_line(filters: dict | None) -> str:
    bits = []
    for key in ("year", "team", "stage", "bucket", "q"):
        value = (filters or {}).get(key)
        if value:
            bits.append(f"{key}={value}")
    return ", ".join(bits)


def _doc(buffer: BytesIO) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )


def _header_story(styles, title: str, generated_at, filters: dict | None) -> list:
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, spaceAfter=8)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], textColor=colors.grey, spaceAfter=12)
    story = [
        Paragraph(title, title_style),
        Paragraph(f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M')}", subtitle_style),
    ]
    filter_line = _filter_line(filters)
    if filter_line:
        story.append(Paragraph("Filters: " + filter_line, subtitle_style))
    return story


def _styled_table(data: list, col_widths: list, header_color: str) -> Table:
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def build_vendor_report_pdf(
    *,
    title: str,
    generated_at,
    vendor_rows: list[dict],
    filters: dict | None = None,
) -> bytes:
    """Vendor spend report (highest to lowest) with invoice numbers and payment stages."""
    buffer = BytesIO()
    doc = _doc(buffer)
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8, leading=10)
    story = _header_story(styles, title, generated_at, filters)

    total_spend = sum((row.get("total") or ZERO for row in vendor_rows), ZERO)
    story.append(Paragraph(f"Vendors: {len(vendor_rows)} &nbsp;&nbsp; Total spend (IRR): {_money(total_spend)}",
                           ParagraphStyle("meta", parent=styles["Normal"], spaceAfter=10)))

    table_data = [["Vendor", "Invoices", "Invoice numbers", "Stages", "Total (IRR)"]]
    for row in vendor_rows:
        vendor = row.get("vendor")
        vendor_name = vendor.name if vendor is not None else (row.get("vendor__name") or "")
        numbers = ", ".join(row.get("invoice_numbers", []))
        stages = ", ".join(row.get("stages", []))
        table_data.append([
            Paragraph(vendor_name, cell_style),
            str(row.get("invoice_count", "")),
            Paragraph(numbers, cell_style),
            Paragraph(stages, cell_style),
            _money(row.get("total")),
        ])
    story.append(_styled_table(table_data, [42 * mm, 16 * mm, 50 * mm, 30 * mm, 28 * mm], "#0f766e"))
    doc.build(story)
    return buffer.getvalue()


def build_campaign_report_pdf(
    *,
    title: str,
    generated_at,
    campaign_rows: list[dict],
    filters: dict | None = None,
) -> bytes:
    """Campaign spend report for the year (highest to lowest)."""
    buffer = BytesIO()
    doc = _doc(buffer)
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8, leading=10)
    story = _header_story(styles, title, generated_at, filters)

    total_spend = sum((row.get("total") or ZERO for row in campaign_rows), ZERO)
    story.append(Paragraph(f"Campaigns: {len(campaign_rows)} &nbsp;&nbsp; Total spend (IRR): {_money(total_spend)}",
                           ParagraphStyle("meta", parent=styles["Normal"], spaceAfter=10)))

    table_data = [["Campaign", "Year", "Team", "Invoices", "Total (IRR)"]]
    for row in campaign_rows:
        table_data.append([
            Paragraph(row.get("campaign__name") or "", cell_style),
            str(row.get("campaign__year") or ""),
            Paragraph(row.get("campaign__team__name") or "", cell_style),
            str(row.get("invoice_count", "")),
            _money(row.get("total")),
        ])
    story.append(_styled_table(table_data, [55 * mm, 16 * mm, 40 * mm, 20 * mm, 28 * mm], "#7c3aed"))
    doc.build(story)
    return buffer.getvalue()


def build_contract_report_pdf(
    *,
    title: str,
    generated_at,
    contracts,
    filters: dict | None = None,
) -> bytes:
    """Vendor contract report: stage and expiry per contract, soonest expiry first."""
    buffer = BytesIO()
    doc = _doc(buffer)
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8, leading=10)
    story = _header_story(styles, title, generated_at, filters)

    contracts = list(contracts)
    story.append(Paragraph(
        f"Contracts: {len(contracts)}",
        ParagraphStyle("meta", parent=styles["Normal"], spaceAfter=10),
    ))

    table_data = [["Title", "Vendor", "Team", "Stage", "End date", "Days left"]]
    for contract in contracts:
        days = contract.days_until_expiry
        days_text = "-" if days is None else str(days)
        end_text = contract.end_date.isoformat() if contract.end_date else "-"
        table_data.append([
            Paragraph(contract.title, cell_style),
            Paragraph(contract.vendor.name, cell_style),
            Paragraph(contract.team.name if contract.team else "-", cell_style),
            Paragraph(contract.get_stage_display(), cell_style),
            end_text,
            days_text,
        ])
    story.append(_styled_table(table_data, [40 * mm, 36 * mm, 28 * mm, 30 * mm, 22 * mm, 18 * mm], "#b45309"))
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
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, spaceAfter=8)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], textColor=colors.grey, spaceAfter=12)
    story = [
        Paragraph(title, title_style),
        Paragraph(f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M')}", subtitle_style),
    ]

    filter_bits = []
    filters = filters or {}
    for key in ("year", "team", "stage", "bucket", "q"):
        value = filters.get(key)
        if value:
            filter_bits.append(f"{key}={value}")
    if filter_bits:
        story.append(Paragraph("Filters: " + ", ".join(filter_bits), subtitle_style))

    summary_data = [
        ["Total spend (IRR)", _money(total_spend)],
        ["Invoice count", str(invoice_count)],
    ]
    summary_table = Table(summary_data, colWidths=[70 * mm, 90 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3f7")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ]
        )
    )
    story.extend([summary_table, Spacer(1, 10)])

    if vendor_rows:
        story.append(Paragraph("Top vendors", styles["Heading2"]))
        vendor_table_data = [["Vendor", "Invoices", "Total spend (IRR)"]]
        for row in vendor_rows[:15]:
            vendor_table_data.append([
                row.get("vendor__name") or getattr(row.get("vendor"), "name", ""),
                str(row.get("invoice_count", "")),
                _money(row.get("total")),
            ])
        vendor_table = Table(vendor_table_data, colWidths=[80 * mm, 25 * mm, 55 * mm], repeatRows=1)
        vendor_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        story.extend([vendor_table, Spacer(1, 10)])

    if stage_rows:
        story.append(Paragraph("Payment stages", styles["Heading2"]))
        stage_table_data = [["Stage", "Count"]]
        for row in stage_rows:
            stage_table_data.append([str(row.get("payment_stage", "")), str(row.get("invoice_count", ""))])
        stage_table = Table(stage_table_data, colWidths=[80 * mm, 40 * mm], repeatRows=1)
        stage_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        story.append(stage_table)

    doc.build(story)
    return buffer.getvalue()
