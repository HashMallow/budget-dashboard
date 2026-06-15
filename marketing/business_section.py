"""Business line / Business Section helpers (e.g. Consumer, Youth, Enterprise segments)."""

from __future__ import annotations

from typing import Any

# Excel header stored in Invoice.raw_data_json during import.
BUSINESS_SECTION_RAW_KEY = "Business Section"


def normalize_business_section(value: Any) -> str:
    text = "" if value is None else str(value)
    return " ".join(text.split()).strip()


def business_section_from_raw(raw: dict[str, Any] | None) -> str:
    if not raw:
        return ""
    return normalize_business_section(raw.get(BUSINESS_SECTION_RAW_KEY))


def distinct_business_sections(queryset) -> list[str]:
    return list(
        queryset.exclude(business_section="")
        .values_list("business_section", flat=True)
        .distinct()
        .order_by("business_section")
    )
