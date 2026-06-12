from __future__ import annotations

import argparse
import datetime as dt
import posixpath
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


DATE_NUM_FMT_IDS = {
    14,
    15,
    16,
    17,
    22,
    27,
    30,
    36,
    45,
    46,
    47,
    50,
    57,
}


CONCEPT_ALIASES = {
    "invoice_number": [
        "invoice no",
        "invoice number",
        "شماره فاکتور",
        "شماره فاکتور",
        "شماره سند",
    ],
    "vendor_name": [
        "vendor",
        "supplier",
        "فروشنده",
        "تامین کننده",
        "تأمین کننده",
        "طرف قرارداد",
        "وندور",
    ],
    "team": [
        "team",
        "department",
        "تیم",
        "دپارتمان",
        "واحد",
        "معاونت",
    ],
    "campaign_name": [
        "campaign",
        "کمپین",
        "پویش",
        "نام کمپین",
    ],
    "category": [
        "category",
        "channel",
        "type",
        "دسته",
        "دسته بندی",
        "دسته‌بندی",
        "کانال",
        "نوع",
        "رسانه",
    ],
    "amount": [
        "amount",
        "spend",
        "price",
        "مبلغ",
        "هزینه",
        "قیمت",
        "پرداختی",
    ],
    "invoice_date": [
        "date",
        "invoice date",
        "تاریخ",
        "تاریخ فاکتور",
        "تاریخ ثبت",
    ],
    "due_date": [
        "due",
        "due date",
        "سررسید",
        "موعد",
    ],
    "payment_stage": [
        "payment stage",
        "payment status",
        "status",
        "وضعیت پرداخت",
        "مرحله پرداخت",
        "وضعیت",
        "استاتوس",
    ],
    "description": [
        "description",
        "desc",
        "شرح",
        "توضیحات",
    ],
    "planned_amount": [
        "planned",
        "projection",
        "target",
        "بودجه",
        "برنامه",
        "تارگت",
    ],
    "year": [
        "year",
        "سال",
        "۱۴۰۵",
        "1405",
        "2026",
    ],
    "month": [
        "month",
        "ماه",
        "فروردین",
        "اردیبهشت",
        "خرداد",
        "تیر",
        "مرداد",
        "شهریور",
        "مهر",
        "آبان",
        "ابان",
        "آذر",
        "اذر",
        "دی",
        "بهمن",
        "اسفند",
    ],
    "referral_cost": [
        "referral",
        "referal",
        "ریفرال",
        "ارجاع",
        "معرفی",
    ],
    "sms_cost": [
        "sms",
        "پیامک",
        "اس ام اس",
        "sms marketing",
    ],
}


PURPOSE_ALIASES = {
    "input data": ["input", "data", "invoice", "spend", "actual", "ورودی", "دیتا", "فاکتور", "هزینه"],
    "budget data": ["budget", "target", "plan", "بودجه", "تارگت", "برنامه"],
    "dashboard/pivot": ["dashboard", "pivot", "chart", "داشبورد", "گزارش", "چارت"],
    "lookup/reference": ["lookup", "list", "master", "reference", "لیست", "مرجع"],
}


PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٤٥٦", "0123456789456")


@dataclass
class SheetInfo:
    name: str
    state: str
    path: str
    dimension: str | None
    max_row: int
    max_col: int
    merged_ranges: list[str]
    rows: dict[int, dict[int, Any]]
    formulas: list[str]
    date_cells: list[str]
    hidden_rows: list[int]
    hidden_cols: list[str]
    header_row: int | None = None
    columns: list[str] | None = None
    purpose: str = "unknown"
    concept_columns: dict[str, list[str]] | None = None


def qname(tag: str, namespace: str = NS_MAIN) -> str:
    return f"{{{namespace}}}{tag}"


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u200c", " ")
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = text.translate(PERSIAN_DIGITS)
    text = re.sub(r"[\s_\-:/\\|()\[\]{}.,،؛؛]+", " ", text)
    return text.strip().lower()


def display_value(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > 80:
        return text[:77] + "..."
    return text


def column_index(column: str) -> int:
    total = 0
    for char in column:
        total = total * 26 + ord(char.upper()) - ord("A") + 1
    return total


def column_letter(index: int) -> str:
    chars = []
    while index:
        index, remainder = divmod(index - 1, 26)
        chars.append(chr(65 + remainder))
    return "".join(reversed(chars)) or "A"


def split_cell_ref(ref: str) -> tuple[int, int]:
    match = re.match(r"([A-Z]+)([0-9]+)", ref or "")
    if not match:
        return 0, 0
    return int(match.group(2)), column_index(match.group(1))


def read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values = []
    for si in root.findall(qname("si")):
        parts = []
        for text in si.iter(qname("t")):
            parts.append(text.text or "")
        values.append("".join(parts))
    return values


def read_styles(zf: zipfile.ZipFile) -> list[bool]:
    if "xl/styles.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/styles.xml"))
    custom_formats: dict[int, str] = {}
    for num_fmt in root.findall(f"{qname('numFmts')}/{qname('numFmt')}"):
        num_fmt_id = int(num_fmt.attrib.get("numFmtId", "0"))
        custom_formats[num_fmt_id] = num_fmt.attrib.get("formatCode", "")

    date_style_flags: list[bool] = []
    cell_xfs = root.find(qname("cellXfs"))
    if cell_xfs is None:
        return date_style_flags

    for xf in cell_xfs.findall(qname("xf")):
        num_fmt_id = int(xf.attrib.get("numFmtId", "0"))
        format_code = normalize_text(custom_formats.get(num_fmt_id, ""))
        is_date = num_fmt_id in DATE_NUM_FMT_IDS or any(token in format_code for token in ["yy", "yyyy", "dd", "mm/dd", "d/m"])
        date_style_flags.append(is_date)
    return date_style_flags


def rel_target(base_path: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(base_path), target))


def read_workbook_relationships(zf: zipfile.ZipFile) -> dict[str, str]:
    rels_path = "xl/_rels/workbook.xml.rels"
    root = ET.fromstring(zf.read(rels_path))
    result = {}
    for rel in root.findall(f"{{{NS_PACKAGE_REL}}}Relationship"):
        result[rel.attrib["Id"]] = rel_target("xl/workbook.xml", rel.attrib["Target"])
    return result


def read_workbook_sheets(zf: zipfile.ZipFile) -> list[tuple[str, str, str]]:
    root = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = read_workbook_relationships(zf)
    sheets = []
    for sheet in root.findall(f"{qname('sheets')}/{qname('sheet')}"):
        name = sheet.attrib["name"]
        state = sheet.attrib.get("state", "visible")
        rel_id = sheet.attrib[f"{{{NS_REL}}}id"]
        sheets.append((name, state, rels[rel_id]))
    return sheets


def parse_cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    value_node = cell.find(qname("v"))
    if cell_type == "inlineStr":
        parts = []
        inline = cell.find(qname("is"))
        if inline is not None:
            for text in inline.iter(qname("t")):
                parts.append(text.text or "")
        return "".join(parts)
    if value_node is None:
        return None
    raw = value_node.text
    if raw is None:
        return None
    if cell_type == "s":
        index = int(raw)
        return shared_strings[index] if 0 <= index < len(shared_strings) else raw
    if cell_type == "b":
        return "TRUE" if raw == "1" else "FALSE"
    return raw


def read_sheet(zf: zipfile.ZipFile, name: str, state: str, path: str, shared_strings: list[str], date_styles: list[bool]) -> SheetInfo:
    root = ET.fromstring(zf.read(path))
    dimension_node = root.find(qname("dimension"))
    dimension = dimension_node.attrib.get("ref") if dimension_node is not None else None

    rows: dict[int, dict[int, Any]] = defaultdict(dict)
    formulas = []
    date_cells = []
    hidden_rows = []
    hidden_cols = []
    max_row = 0
    max_col = 0

    cols = root.find(qname("cols"))
    if cols is not None:
        for col in cols.findall(qname("col")):
            if col.attrib.get("hidden") == "1":
                min_col = int(col.attrib.get("min", "0"))
                max_col_num = int(col.attrib.get("max", str(min_col)))
                if min_col == max_col_num:
                    hidden_cols.append(column_letter(min_col))
                else:
                    hidden_cols.append(f"{column_letter(min_col)}:{column_letter(max_col_num)}")

    sheet_data = root.find(qname("sheetData"))
    if sheet_data is not None:
        for row in sheet_data.findall(qname("row")):
            row_index = int(row.attrib.get("r", "0"))
            if row.attrib.get("hidden") == "1":
                hidden_rows.append(row_index)
            max_row = max(max_row, row_index)
            for cell in row.findall(qname("c")):
                ref = cell.attrib.get("r", "")
                r_index, c_index = split_cell_ref(ref)
                max_col = max(max_col, c_index)
                formula = cell.find(qname("f"))
                if formula is not None:
                    formulas.append(ref)
                style_id = int(cell.attrib.get("s", "0"))
                if 0 <= style_id < len(date_styles) and date_styles[style_id]:
                    date_cells.append(ref)
                value = parse_cell_value(cell, shared_strings)
                if value is not None:
                    rows[r_index][c_index] = value

    merged_ranges = []
    merged_cells = root.find(qname("mergeCells"))
    if merged_cells is not None:
        merged_ranges = [merge.attrib["ref"] for merge in merged_cells.findall(qname("mergeCell"))]

    return SheetInfo(
        name=name,
        state=state,
        path=path,
        dimension=dimension,
        max_row=max_row,
        max_col=max_col,
        merged_ranges=merged_ranges,
        rows=dict(rows),
        formulas=formulas,
        date_cells=date_cells,
        hidden_rows=hidden_rows,
        hidden_cols=hidden_cols,
    )


def detect_header_row(sheet: SheetInfo) -> int | None:
    best: tuple[int, int] | None = None
    keyword_values = [alias for aliases in CONCEPT_ALIASES.values() for alias in aliases]
    for row_index in sorted(sheet.rows)[:40]:
        values = [display_value(value) for _, value in sorted(sheet.rows[row_index].items())]
        non_empty = [value for value in values if value]
        if len(non_empty) < 2:
            continue
        text_count = sum(1 for value in non_empty if re.search(r"[A-Za-zآ-ی]", value))
        joined = normalize_text(" ".join(non_empty))
        keyword_hits = sum(1 for keyword in keyword_values if normalize_text(keyword) and normalize_text(keyword) in joined)
        uniqueness = len(set(normalize_text(value) for value in non_empty))
        score = text_count * 4 + keyword_hits * 8 + uniqueness + min(len(non_empty), 12)
        if best is None or score > best[0]:
            best = (score, row_index)
    return best[1] if best else None


def columns_for_header(sheet: SheetInfo, header_row: int | None) -> list[str]:
    if not header_row or header_row not in sheet.rows:
        return []
    columns = []
    seen = Counter()
    for index in range(1, sheet.max_col + 1):
        value = display_value(sheet.rows[header_row].get(index, ""))
        if not value:
            value = f"blank_{column_letter(index)}"
        seen[value] += 1
        if seen[value] > 1:
            value = f"{value} ({seen[value]})"
        columns.append(value)
    return columns


def detect_concepts(columns: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for column in columns:
        normalized_column = normalize_text(column)
        for concept, aliases in CONCEPT_ALIASES.items():
            for alias in aliases:
                normalized_alias = normalize_text(alias)
                if normalized_alias and normalized_alias in normalized_column:
                    result[concept].append(column)
                    break
    return dict(result)


def detect_purpose(sheet: SheetInfo) -> str:
    text = normalize_text(" ".join([sheet.name] + (sheet.columns or [])))
    sheet_name = normalize_text(sheet.name)
    if any(token in sheet_name for token in ["budget", "بودجه"]):
        return "budget data"
    if any(token in sheet_name for token in ["live spending", "dashboard", "pivot", "گزارش"]):
        return "dashboard/pivot"
    if sheet_name in {"data", "lookup", "reference"}:
        return "lookup/reference"
    scores = {}
    for purpose, aliases in PURPOSE_ALIASES.items():
        scores[purpose] = sum(1 for alias in aliases if normalize_text(alias) in text)
    if scores and max(scores.values()) > 0:
        return max(scores, key=scores.get)
    concepts = sheet.concept_columns or {}
    invoice_like = len(set(concepts) & {"invoice_number", "vendor_name", "amount", "invoice_date", "payment_stage"})
    budget_like = len(set(concepts) & {"planned_amount", "year", "month"})
    if invoice_like >= 3:
        return "input data"
    if budget_like >= 2:
        return "budget data"
    return "unknown"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    safe_headers = [header or " " for header in headers]
    output = ["| " + " | ".join(safe_headers) + " |"]
    output.append("| " + " | ".join(["---"] * len(safe_headers)) + " |")
    for row in rows:
        escaped = [cell.replace("|", "\\|") for cell in row]
        output.append("| " + " | ".join(escaped) + " |")
    return "\n".join(output)


def first_data_rows(sheet: SheetInfo, limit: int = 5) -> list[dict[str, Any]]:
    if not sheet.header_row or not sheet.columns:
        return []
    result = []
    for row_index in sorted(index for index in sheet.rows if index > sheet.header_row):
        row = sheet.rows[row_index]
        values = [display_value(row.get(index, "")) for index in range(1, sheet.max_col + 1)]
        if not any(values):
            continue
        if sum(1 for value in values if value) < 2:
            continue
        result.append({"row_number": row_index, "values": values})
        if len(result) >= limit:
            break
    return result


def classify_interesting_columns(sheet: SheetInfo) -> list[str]:
    concepts = sheet.concept_columns or {}
    lines = []
    for concept in [
        "invoice_number",
        "vendor_name",
        "team",
        "campaign_name",
        "category",
        "amount",
        "planned_amount",
        "invoice_date",
        "due_date",
        "payment_stage",
        "referral_cost",
        "sms_cost",
        "year",
        "month",
    ]:
        if concept in concepts:
            lines.append(f"- {concept}: {', '.join(concepts[concept])}")
    return lines


def write_structure(workbook: Path, sheets: list[SheetInfo], out_dir: Path) -> None:
    lines = [
        "# Workbook Structure",
        "",
        f"- File path: `{workbook}`",
        f"- Generated at: `{dt.datetime.now(dt.UTC).isoformat()}`",
        "",
        "## Sheets",
        "",
        "| Sheet | State | Dimension | Non-empty rows | Last non-empty row | Non-empty columns | Likely purpose | Header row | Formulas | Merged ranges | Hidden rows | Hidden columns |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for sheet in sheets:
        nonempty_rows = [row_index for row_index, row in sheet.rows.items() if any(display_value(value) for value in row.values())]
        nonempty_cols = sorted({column_index for row in sheet.rows.values() for column_index, value in row.items() if display_value(value)})
        lines.append(
            "| "
            + " | ".join(
                [
                    sheet.name.replace("|", "\\|"),
                    sheet.state,
                    sheet.dimension or "",
                    str(len(nonempty_rows)),
                    str(max(nonempty_rows) if nonempty_rows else ""),
                    str(len(nonempty_cols)),
                    sheet.purpose,
                    str(sheet.header_row or ""),
                    str(len(sheet.formulas)),
                    str(len(sheet.merged_ranges)),
                    str(len(sheet.hidden_rows)),
                    str(len(sheet.hidden_cols)),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Sheet Details", ""])
    for sheet in sheets:
        nonempty_rows = [row_index for row_index, row in sheet.rows.items() if any(display_value(value) for value in row.values())]
        nonempty_cols = sorted({column_index for row in sheet.rows.values() for column_index, value in row.items() if display_value(value)})
        lines.extend(
            [
                f"### {sheet.name}",
                "",
                f"- XML path: `{sheet.path}`",
                f"- Visibility: `{sheet.state}`",
                f"- Dimension: `{sheet.dimension or ''}`",
                f"- XML row/column extent: `{sheet.max_row}` rows x `{sheet.max_col}` columns",
                f"- Non-empty rows/columns: `{len(nonempty_rows)}` rows x `{len(nonempty_cols)}` columns",
                f"- Last non-empty row: `{max(nonempty_rows) if nonempty_rows else 'none'}`",
                f"- Likely purpose: `{sheet.purpose}`",
                f"- Detected header row: `{sheet.header_row or 'not detected'}`",
                f"- Formula cells: `{len(sheet.formulas)}`",
                f"- Date-formatted cells: `{len(sheet.date_cells)}`",
                f"- Hidden rows: `{', '.join(map(str, sheet.hidden_rows[:20])) if sheet.hidden_rows else 'none'}`",
                f"- Hidden columns: `{', '.join(sheet.hidden_cols[:20]) if sheet.hidden_cols else 'none'}`",
                "",
                "Detected columns:",
                "",
            ]
        )
        if sheet.columns:
            for column in sheet.columns:
                lines.append(f"- {column}")
        else:
            lines.append("- No header row detected.")
        lines.extend(["", "Detected concept-like columns:", ""])
        concept_lines = classify_interesting_columns(sheet)
        lines.extend(concept_lines or ["- None detected."])
        lines.extend(["", "Merged cell ranges:", ""])
        if sheet.merged_ranges:
            for merged_range in sheet.merged_ranges[:80]:
                lines.append(f"- `{merged_range}`")
            if len(sheet.merged_ranges) > 80:
                lines.append(f"- ... {len(sheet.merged_ranges) - 80} more")
        else:
            lines.append("- none")
        lines.extend([""])
    (out_dir / "workbook_structure.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_sample_rows(workbook: Path, sheets: list[SheetInfo], out_dir: Path) -> None:
    lines = [
        "# Workbook Sample Rows",
        "",
        f"- File path: `{workbook}`",
        "- Sample is limited to the first 5 non-empty rows after the detected header row for each relevant sheet.",
        "- Values are truncated to reduce sensitive exposure.",
        "",
    ]
    relevant = sheets
    for sheet in relevant:
        lines.extend([f"## {sheet.name}", "", f"- Likely purpose: `{sheet.purpose}`", f"- Header row: `{sheet.header_row or 'not detected'}`", ""])
        if not sheet.columns:
            lines.extend(["No columns detected.", ""])
            continue
        lines.extend(["Normalized column names:", ""])
        for original in sheet.columns:
            lines.append(f"- `{normalize_text(original)}` ← `{original}`")
        lines.extend(["", "Concept-like columns:", ""])
        lines.extend(classify_interesting_columns(sheet) or ["- None detected."])
        sample_rows = first_data_rows(sheet)
        lines.extend(["", "Sample rows:", ""])
        if sample_rows:
            headers = ["source_row"] + sheet.columns
            rows = [[str(row["row_number"])] + row["values"] for row in sample_rows]
            lines.append(markdown_table(headers, rows))
        else:
            lines.append("No non-empty sample rows found after the detected header row.")
        lines.append("")
    (out_dir / "workbook_sample_rows.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("docs/discovery"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.workbook) as zf:
        shared_strings = read_shared_strings(zf)
        date_styles = read_styles(zf)
        sheet_defs = read_workbook_sheets(zf)
        sheets = [read_sheet(zf, name, state, path, shared_strings, date_styles) for name, state, path in sheet_defs]

    for sheet in sheets:
        sheet.header_row = detect_header_row(sheet)
        sheet.columns = columns_for_header(sheet, sheet.header_row)
        sheet.concept_columns = detect_concepts(sheet.columns)
        sheet.purpose = detect_purpose(sheet)

    write_structure(args.workbook, sheets, args.out_dir)
    write_sample_rows(args.workbook, sheets, args.out_dir)
    print(f"Wrote {args.out_dir / 'workbook_structure.md'}")
    print(f"Wrote {args.out_dir / 'workbook_sample_rows.md'}")


if __name__ == "__main__":
    main()
