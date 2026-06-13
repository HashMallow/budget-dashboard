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
