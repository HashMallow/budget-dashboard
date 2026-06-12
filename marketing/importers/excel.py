from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils.datetime import from_excel

from marketing.models import BudgetLine, Campaign, CostBucket, Invoice, PaymentStage, Team, Vendor, normalize_name


class DryRunRollback(Exception):
    pass


@dataclass
class ImportCounter:
    created: int = 0
    updated: int = 0
    skipped: int = 0


@dataclass
class SkippedRow:
    sheet: str
    row_number: int
    reason: str


@dataclass
class ImportResult:
    workbook: Path
    dry_run: bool
    teams: ImportCounter = field(default_factory=ImportCounter)
    vendors: ImportCounter = field(default_factory=ImportCounter)
    campaigns: ImportCounter = field(default_factory=ImportCounter)
    invoices: ImportCounter = field(default_factory=ImportCounter)
    budget_lines: ImportCounter = field(default_factory=ImportCounter)
    skipped_rows: list[SkippedRow] = field(default_factory=list)
    dry_run_teams: dict[str, Team] = field(default_factory=dict, repr=False)
    dry_run_vendors: dict[str, Vendor] = field(default_factory=dict, repr=False)
    dry_run_campaigns: dict[tuple[str, int, str | None], Campaign] = field(default_factory=dict, repr=False)

    def skip(self, sheet: str, row_number: int, reason: str, counter: ImportCounter | None = None) -> None:
        if counter is not None:
            counter.skipped += 1
        self.skipped_rows.append(SkippedRow(sheet=sheet, row_number=row_number, reason=reason))


def discover_workbook(explicit_path: str | Path | None = None, base_dir: Path | None = None) -> Path:
    if explicit_path:
        path = Path(explicit_path)
        if not path.exists():
            raise FileNotFoundError(f"Workbook not found: {path}")
        return path

    base = base_dir or Path.cwd()
    candidates = [
        *base.glob("*.xlsx"),
        *base.glob("data/*.xlsx"),
        *base.glob("imports/*.xlsx"),
    ]
    candidates = [path for path in candidates if not path.name.startswith("~$")]
    if not candidates:
        raise FileNotFoundError("No .xlsx workbook found in project root, data/, or imports/.")
    if len(candidates) > 1:
        formatted = "\n".join(f"- {path}" for path in candidates)
        raise ValueError(f"Multiple .xlsx workbooks found. Pass --file explicitly:\n{formatted}")
    return candidates[0]


def load_mapping(mapping_path: str | Path = "docs/discovery/column_mapping.yml") -> dict[str, Any]:
    path = Path(mapping_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Mapping file not found: {path}. Run discovery first or provide --mapping with a valid mapping YAML."
        )
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def cell_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int | float):
        return Decimal(str(value))
    cleaned = re.sub(r"[,\s]", "", str(value))
    cleaned = re.sub(r"(IRR|Rial|ریال|تومان)", "", cleaned, flags=re.IGNORECASE)
    if cleaned == "":
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_year(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def parse_excel_date(value: Any, workbook_epoch) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, int | float):
        try:
            parsed = from_excel(value, workbook_epoch)
        except (TypeError, ValueError):
            return None
        return parsed.date() if isinstance(parsed, datetime) else parsed
    text = cell_to_text(value)
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return parse_jalali_date(text)


def parse_jalali_date(value: str) -> date | None:
    match = re.fullmatch(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", value.strip())
    if not match:
        return None
    year, month, day = (int(part) for part in match.groups())
    if not 1200 <= year <= 1600:
        return None
    try:
        return jalali_to_gregorian(year, month, day)
    except ValueError:
        return None


def jalali_to_gregorian(jalali_year: int, jalali_month: int, jalali_day: int) -> date:
    if not 1 <= jalali_month <= 12:
        raise ValueError("Invalid Jalali month")
    max_day = 31 if jalali_month <= 6 else 30
    if jalali_month == 12:
        max_day = 30
    if not 1 <= jalali_day <= max_day:
        raise ValueError("Invalid Jalali day")

    jy = jalali_year + 1595
    days = (
        -355668
        + (365 * jy)
        + ((jy // 33) * 8)
        + (((jy % 33) + 3) // 4)
        + jalali_day
        + ((jalali_month - 1) * 31 if jalali_month < 7 else ((jalali_month - 7) * 30) + 186)
    )

    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1

    leap = (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)
    month_lengths = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gregorian_month = 1
    for month_length in month_lengths:
        if gd <= month_length:
            return date(gy, gregorian_month, gd)
        gd -= month_length
        gregorian_month += 1
    return None


def normalize_currency(value: Any) -> str:
    text = cell_to_text(value)
    if not text:
        return settings.DEFAULT_CURRENCY
    normalized = normalize_name(text)
    if normalized in {"rial", "ریال", "irr"}:
        return "IRR"
    return text[:16]


def header_map_for_sheet(sheet, header_row: int) -> dict[str, int]:
    headers: dict[str, int] = {}
    seen: dict[str, int] = {}
    for index, cell in enumerate(sheet[header_row], start=1):
        value = cell_to_text(cell.value)
        if not value:
            value = f"blank_{get_column_letter(index)}"
        seen[value] = seen.get(value, 0) + 1
        key = value if seen[value] == 1 else f"{value} ({seen[value]})"
        headers[key] = index
    return headers


def row_data(sheet, row_number: int, headers: dict[str, int]) -> dict[str, Any]:
    data = {}
    for header, column_index in headers.items():
        data[header] = json_safe(sheet.cell(row=row_number, column=column_index).value)
    return data


def mapped_value(row: dict[str, Any], columns: dict[str, str | None], key: str) -> Any:
    column = columns.get(key)
    if not column:
        return None
    return row.get(column)


def get_or_create_team(name: str, result: ImportResult, dry_run: bool) -> Team:
    slug = slugify(name, allow_unicode=True) or normalize_name(name).replace(" ", "-")
    team = Team.objects.filter(slug=slug).first() or Team.objects.filter(name=name).first()
    if team:
        return team
    if dry_run:
        if slug in result.dry_run_teams:
            return result.dry_run_teams[slug]
        result.teams.created += 1
        team = Team(name=name, slug=slug)
        result.dry_run_teams[slug] = team
        return team
    team = Team.objects.create(name=name, slug=slug)
    result.teams.created += 1
    return team


def get_or_create_vendor(name: str, result: ImportResult, dry_run: bool) -> Vendor:
    normalized = normalize_name(name)
    vendor = Vendor.objects.filter(normalized_name=normalized).first()
    if vendor:
        return vendor
    if dry_run:
        if normalized in result.dry_run_vendors:
            return result.dry_run_vendors[normalized]
        result.vendors.created += 1
        vendor = Vendor(name=name, normalized_name=normalized)
        result.dry_run_vendors[normalized] = vendor
        return vendor
    vendor = Vendor.objects.create(name=name, normalized_name=normalized)
    result.vendors.created += 1
    return vendor


def get_or_create_campaign(
    name: str,
    year: int,
    team: Team | None,
    result: ImportResult,
    dry_run: bool,
) -> Campaign | None:
    if not name:
        return None
    campaign = Campaign.objects.filter(name=name, year=year, team=team if team and team.pk else None).first()
    if campaign:
        return campaign
    if dry_run:
        team_key = team.slug if team else None
        cache_key = (name, year, team_key)
        if cache_key in result.dry_run_campaigns:
            return result.dry_run_campaigns[cache_key]
        result.campaigns.created += 1
        campaign = Campaign(name=name, year=year, team=team if team and team.pk else None)
        result.dry_run_campaigns[cache_key] = campaign
        return campaign
    campaign = Campaign.objects.create(name=name, year=year, team=team if team and team.pk else None)
    result.campaigns.created += 1
    return campaign


def detect_cost_bucket(row: dict[str, Any], bucket_mapping: dict[str, Any]) -> str:
    default = bucket_mapping.get("default", CostBucket.TEAM)
    for rule in bucket_mapping.get("rules", []):
        keywords = [normalize_name(keyword) for keyword in rule.get("when_any_source_column_contains", [])]
        source_columns = rule.get("source_columns", [])
        text = " ".join(cell_to_text(row.get(column)) for column in source_columns)
        normalized_text = normalize_name(text)
        if any(keyword and keyword in normalized_text for keyword in keywords):
            return rule.get("bucket", default)
    return default


def map_payment_stage(value: Any, stage_mapping: dict[str, str]) -> str:
    text = cell_to_text(value)
    if not text:
        return PaymentStage.DRAFT
    if text in stage_mapping:
        return stage_mapping[text]
    normalized = normalize_name(text)
    for source, target in stage_mapping.items():
        if normalize_name(source) == normalized:
            return target
    if normalized in {"paid", "پرداخت شده"}:
        return PaymentStage.PAID
    if normalized in {"finance", "مالی"}:
        return PaymentStage.FINANCE_REVIEW
    return PaymentStage.SUBMITTED


def duplicate_invoice_vendor_keys(
    sheet,
    invoice_mapping: dict[str, Any],
    headers: dict[str, int],
) -> set[tuple[str, str]]:
    columns = invoice_mapping["columns"]
    counts: dict[tuple[str, str], int] = {}
    for row_number in range(invoice_mapping["data_start_row"], invoice_mapping["data_end_row"] + 1):
        raw = row_data(sheet, row_number, headers)
        invoice_number = cell_to_text(mapped_value(raw, columns, "invoice_number"))
        vendor_name = cell_to_text(mapped_value(raw, columns, "vendor_name"))
        if not invoice_number or not vendor_name:
            continue
        key = (invoice_number, normalize_name(vendor_name))
        counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count > 1}


def find_existing_invoice(
    vendor: Vendor,
    invoice_number: str,
    source_sheet: str,
    source_row: int,
    *,
    allow_invoice_vendor_fallback: bool,
) -> Invoice | None:
    if vendor.pk:
        source_match = Invoice.objects.filter(
            source_sheet=source_sheet,
            source_row_number=source_row,
            vendor=vendor,
            invoice_number=invoice_number,
        ).first()
        if source_match:
            return source_match

        if allow_invoice_vendor_fallback:
            candidates = Invoice.objects.filter(vendor=vendor, invoice_number=invoice_number)
            if candidates.count() == 1:
                return candidates.first()
    return None


def update_or_create_invoice(
    *,
    vendor: Vendor,
    team: Team | None,
    campaign: Campaign | None,
    invoice_number: str,
    category: str,
    cost_bucket: str,
    description: str,
    invoice_date: date,
    amount: Decimal,
    currency: str,
    payment_stage: str,
    source_sheet: str,
    source_row: int,
    raw_data: dict[str, Any],
    result: ImportResult,
    dry_run: bool,
    allow_invoice_vendor_fallback: bool = True,
) -> None:
    existing = find_existing_invoice(
        vendor,
        invoice_number,
        source_sheet,
        source_row,
        allow_invoice_vendor_fallback=allow_invoice_vendor_fallback,
    )
    if dry_run:
        if existing:
            result.invoices.updated += 1
        else:
            result.invoices.created += 1
        return

    values = {
        "team": team,
        "campaign": campaign,
        "category": category,
        "cost_bucket": cost_bucket,
        "description": description,
        "invoice_date": invoice_date,
        "amount": amount,
        "currency": currency,
        "payment_stage": payment_stage,
        "source_sheet": source_sheet,
        "source_row_number": source_row,
        "raw_data_json": raw_data,
    }
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        existing.save()
        result.invoices.updated += 1
        return

    Invoice.objects.create(invoice_number=invoice_number, vendor=vendor, **values)
    result.invoices.created += 1


def import_invoices(workbook, mapping: dict[str, Any], result: ImportResult, dry_run: bool) -> None:
    invoice_mapping = mapping["sheets"]["invoices"]
    sheet_name = invoice_mapping["actual_sheet_name"]
    if sheet_name not in workbook.sheetnames:
        raise ValueError(f"Invoice sheet not found: {sheet_name}")

    sheet = workbook[sheet_name]
    headers = header_map_for_sheet(sheet, invoice_mapping["header_row"])
    columns = invoice_mapping["columns"]
    bucket_mapping = invoice_mapping.get("derived_values", {}).get("cost_bucket", {})
    stage_mapping = invoice_mapping.get("derived_values", {}).get("payment_stage_mapping", {})
    currency = invoice_mapping.get("derived_values", {}).get("currency", settings.DEFAULT_CURRENCY)
    duplicate_invoice_keys = duplicate_invoice_vendor_keys(sheet, invoice_mapping, headers)

    for row_number in range(invoice_mapping["data_start_row"], invoice_mapping["data_end_row"] + 1):
        raw = row_data(sheet, row_number, headers)
        if not any(cell_to_text(value) for value in raw.values()):
            result.skip(sheet_name, row_number, "empty row", result.invoices)
            continue

        invoice_number = cell_to_text(mapped_value(raw, columns, "invoice_number"))
        vendor_name = cell_to_text(mapped_value(raw, columns, "vendor_name"))
        amount = parse_decimal(mapped_value(raw, columns, "amount"))
        invoice_date = parse_excel_date(mapped_value(raw, columns, "invoice_date_gregorian_serial"), workbook.epoch)
        invoice_date = invoice_date or parse_excel_date(
            mapped_value(raw, columns, "invoice_date_jalali_serial"),
            workbook.epoch,
        )
        invoice_date = invoice_date or parse_excel_date(
            mapped_value(raw, columns, "jalali_invoice_date_text_candidate"),
            workbook.epoch,
        )
        year = parse_year(mapped_value(raw, columns, "year")) or (invoice_date.year if invoice_date else None)
        category = cell_to_text(mapped_value(raw, columns, "category")) or "Uncategorized"

        missing = []
        if not invoice_number:
            missing.append("invoice_number")
        if not vendor_name:
            missing.append("vendor_name")
        if amount is None:
            missing.append("amount")
        if invoice_date is None:
            missing.append("invoice_date")
        if year is None:
            missing.append("year")
        if missing:
            result.skip(sheet_name, row_number, f"missing required fields: {', '.join(missing)}", result.invoices)
            continue

        vendor = get_or_create_vendor(vendor_name, result, dry_run)
        invoice_key = (invoice_number, normalize_name(vendor_name))
        cost_bucket = detect_cost_bucket(raw, bucket_mapping)
        team_name = cell_to_text(mapped_value(raw, columns, "team"))
        team = get_or_create_team(team_name, result, dry_run) if team_name else None
        campaign_name = cell_to_text(mapped_value(raw, columns, "campaign_name"))
        campaign = get_or_create_campaign(campaign_name, year, team, result, dry_run) if year else None
        description = cell_to_text(mapped_value(raw, columns, "description"))
        payment_stage = map_payment_stage(mapped_value(raw, columns, "payment_stage"), stage_mapping)

        update_or_create_invoice(
            vendor=vendor,
            team=team,
            campaign=campaign,
            invoice_number=invoice_number,
            category=category,
            cost_bucket=cost_bucket,
            description=description,
            invoice_date=invoice_date,
            amount=amount,
            currency=currency,
            payment_stage=payment_stage,
            source_sheet=sheet_name,
            source_row=row_number,
            raw_data=raw,
            result=result,
            dry_run=dry_run,
            allow_invoice_vendor_fallback=invoice_key not in duplicate_invoice_keys,
        )


def find_existing_budget_line(
    *,
    source_sheet: str,
    source_row: int,
    year: int,
    month: int,
    team: Team | None,
    category: str,
) -> BudgetLine | None:
    queryset = BudgetLine.objects.filter(
        source_sheet=source_sheet,
        source_row_number=source_row,
        year=year,
        month=month,
        category=category,
    )
    queryset = queryset.filter(team=team) if team and team.pk else queryset.filter(team__isnull=True)
    return queryset.first()


def update_or_create_budget_line(
    *,
    year: int,
    month: int,
    team: Team | None,
    category: str,
    planned_amount: Decimal,
    currency: str,
    source_sheet: str,
    source_row: int,
    raw_data: dict[str, Any],
    result: ImportResult,
    dry_run: bool,
) -> None:
    existing = find_existing_budget_line(
        source_sheet=source_sheet,
        source_row=source_row,
        year=year,
        month=month,
        team=team,
        category=category,
    )
    if dry_run:
        if existing:
            result.budget_lines.updated += 1
        else:
            result.budget_lines.created += 1
        return

    values = {
        "team": team,
        "category": category,
        "planned_amount": planned_amount,
        "currency": currency,
        "source_sheet": source_sheet,
        "source_row_number": source_row,
        "raw_data_json": raw_data,
    }
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        existing.save()
        result.budget_lines.updated += 1
        return

    BudgetLine.objects.create(year=year, month=month, **values)
    result.budget_lines.created += 1


def import_budget_lines(workbook, mapping: dict[str, Any], result: ImportResult, dry_run: bool) -> None:
    budget_mapping = mapping["sheets"]["budget"]
    sheet_name = budget_mapping["actual_sheet_name"]
    if sheet_name not in workbook.sheetnames:
        raise ValueError(f"Budget sheet not found: {sheet_name}")

    sheet = workbook[sheet_name]
    header_row = budget_mapping["header_row"]
    headers = header_map_for_sheet(sheet, header_row)
    context_columns = budget_mapping["row_context_columns"]
    year = int(budget_mapping["budget_line_mapping"]["year"])

    for row_number in range(budget_mapping["data_start_row"], budget_mapping["data_end_row"] + 1):
        raw = row_data(sheet, row_number, headers)
        if not any(cell_to_text(value) for value in raw.values()):
            result.skip(sheet_name, row_number, "empty row", result.budget_lines)
            continue

        team_name = cell_to_text(raw.get(context_columns["team"]))
        title = cell_to_text(raw.get(context_columns["category_or_title"]))
        description = cell_to_text(raw.get(context_columns["description"]))
        category = title or description
        if not team_name or not category:
            result.skip(sheet_name, row_number, "missing team or category/title", result.budget_lines)
            continue

        team = get_or_create_team(team_name, result, dry_run)
        currency = normalize_currency(raw.get(context_columns["currency"]))

        for month_info in budget_mapping["monthly_columns"]:
            month = int(month_info["month_number"])
            projection_cell = sheet[f"{month_info['projection_column']}{row_number}"]
            actual_cell = sheet[f"{month_info['actual_column']}{row_number}"]
            planned_amount = parse_decimal(projection_cell.value)
            if planned_amount is None:
                result.skip(
                    sheet_name,
                    row_number,
                    f"missing planned amount for month {month}",
                    result.budget_lines,
                )
                continue

            monthly_raw = {
                **raw,
                "_import_month": month,
                "_import_month_label": month_info["month_label"],
                "_projection_column": month_info["projection_column"],
                "_actual_column": month_info["actual_column"],
                "_actual_amount_reference": json_safe(actual_cell.value),
            }
            update_or_create_budget_line(
                year=year,
                month=month,
                team=team,
                category=category,
                planned_amount=planned_amount,
                currency=currency,
                source_sheet=sheet_name,
                source_row=row_number,
                raw_data=monthly_raw,
                result=result,
                dry_run=dry_run,
            )


def import_marketing_workbook(
    workbook_path: str | Path,
    *,
    mapping_path: str | Path = "docs/discovery/column_mapping.yml",
    dry_run: bool = False,
) -> ImportResult:
    workbook_file = Path(workbook_path)
    mapping = load_mapping(mapping_path)
    result = ImportResult(workbook=workbook_file, dry_run=dry_run)

    workbook = load_workbook(workbook_file, data_only=True)
    try:
        with transaction.atomic():
            import_invoices(workbook, mapping, result, dry_run)
            import_budget_lines(workbook, mapping, result, dry_run)
            if dry_run:
                raise DryRunRollback
    except DryRunRollback:
        pass
    finally:
        workbook.close()
    if not dry_run:
        # Status history rows created from import updates should not inherit stale note attributes.
        timezone.now()
    return result
