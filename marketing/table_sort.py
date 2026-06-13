from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from django.db.models import QuerySet
from django.http import HttpRequest

SORT_PARAM = "sort"
DIR_PARAM = "dir"
DIR_ASC = "asc"
DIR_DESC = "desc"


class SortState:
    __slots__ = ("field", "direction")

    def __init__(self, field: str, direction: str) -> None:
        self.field = field
        self.direction = direction

    @property
    def is_asc(self) -> bool:
        return self.direction == DIR_ASC

    def indicator(self, field: str) -> str:
        if self.field != field:
            return ""
        return "↑" if self.is_asc else "↓"

    def css_class(self, field: str) -> str:
        if self.field != field:
            return ""
        return "sort-asc" if self.is_asc else "sort-desc"


def parse_sort(
    request: HttpRequest,
    *,
    allowed: Iterable[str],
    default_field: str,
    default_dir: str = DIR_DESC,
    default_dirs: dict[str, str] | None = None,
) -> SortState:
    allowed_set = set(allowed)
    field = request.GET.get(SORT_PARAM, default_field).strip()
    direction = request.GET.get(DIR_PARAM, "").strip().lower()
    if field not in allowed_set:
        field = default_field
    if direction not in {DIR_ASC, DIR_DESC}:
        direction = (default_dirs or {}).get(field, default_dir)
    return SortState(field, direction)


def next_direction(sort: SortState, field: str, *, default_dirs: dict[str, str] | None = None) -> str:
    if sort.field == field:
        return DIR_ASC if sort.direction == DIR_DESC else DIR_DESC
    return (default_dirs or {}).get(field, DIR_ASC)


def sort_href(
    request: HttpRequest,
    sort: SortState,
    field: str,
    *,
    default_dirs: dict[str, str] | None = None,
) -> str:
    direction = next_direction(sort, field, default_dirs=default_dirs)
    params = request.GET.copy()
    params[SORT_PARAM] = field
    params[DIR_PARAM] = direction
    params.pop("page", None)
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else "?"


def query_string(request: HttpRequest, **overrides: Any) -> str:
    params = request.GET.copy()
    for key, value in overrides.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = str(value)
    return params.urlencode()


def _order_expr(field_expr: str, *, descending: bool) -> str:
    bare = field_expr.lstrip("-")
    return f"-{bare}" if descending else bare


def apply_ordering(
    queryset: QuerySet,
    sort: SortState,
    *,
    fields: dict[str, str | tuple[str, ...]],
    default_field: str,
    inverted: set[str] | None = None,
    tiebreaker: str | None = "-id",
) -> QuerySet:
    inverted = inverted or set()
    field_expr = fields.get(sort.field) or fields[default_field]
    descending = sort.direction == DIR_DESC
    if sort.field in inverted:
        descending = not descending

    order_by: list[str] = []
    if isinstance(field_expr, tuple):
        order_by.extend(_order_expr(expr, descending=descending) for expr in field_expr)
    else:
        order_by.append(_order_expr(field_expr, descending=descending))
    if tiebreaker:
        order_by.append(tiebreaker)
    return queryset.order_by(*order_by)


def sort_rows(
    rows: list[Any],
    sort: SortState,
    *,
    keys: dict[str, Callable[[Any], Any]],
    default_field: str,
) -> list[Any]:
    key_fn = keys.get(sort.field) or keys[default_field]
    return sorted(rows, key=key_fn, reverse=sort.direction == DIR_DESC)
