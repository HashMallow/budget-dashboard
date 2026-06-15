"""Workbook sheet names and examples used by export and documentation.

Values here are intentionally generic. Deployments map real Excel sheet names in
``docs/discovery/column_mapping.yml`` (or a private copy).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_WORKBOOK_FILENAME = "marketing_spend_workbook.xlsx"
DEFAULT_INVOICE_SHEET_NAME = "Marketing Spend Input"
BUSINESS_LINE_HELP_EXAMPLES = "Consumer, Youth, Enterprise"
DEFAULT_MAPPING_PATH = Path("docs/discovery/column_mapping.yml")


def load_mapping(path: str | Path = DEFAULT_MAPPING_PATH) -> dict[str, Any]:
    mapping_path = Path(path)
    if not mapping_path.exists():
        return {}
    return yaml.safe_load(mapping_path.read_text(encoding="utf-8")) or {}


def invoice_sheet_name(mapping: dict[str, Any] | None = None) -> str:
    data = mapping if mapping is not None else load_mapping()
    name = data.get("sheets", {}).get("invoices", {}).get("actual_sheet_name")
    return str(name) if name else DEFAULT_INVOICE_SHEET_NAME
