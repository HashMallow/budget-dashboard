from __future__ import annotations

import pytest
from django.test import RequestFactory

from marketing.models import Invoice
from marketing.table_sort import (
    SortState,
    apply_ordering,
    next_direction,
    sort_href,
    sort_rows,
)


def test_sort_href_toggles_direction():
    factory = RequestFactory()
    request = factory.get("/invoices/", {"sort": "amount", "dir": "desc"})
    sort = SortState("amount", "desc")
    href = sort_href(request, sort, "amount")
    assert "dir=asc" in href
    assert "page=" not in href


def test_next_direction_uses_column_default():
    assert next_direction(SortState("date", "desc"), "vendor", default_dirs={"vendor": "asc"}) == "asc"


def test_sort_rows_orders_python_lists():
    rows = [{"name": "b", "total": 2}, {"name": "a", "total": 9}]
    sorted_rows = sort_rows(
        rows,
        SortState("total", "desc"),
        keys={"total": lambda row: row["total"]},
        default_field="total",
    )
    assert sorted_rows[0]["name"] == "a"


@pytest.mark.django_db
def test_apply_ordering_inverts_days_field():
    sort = SortState("days", "desc")
    qs = Invoice.objects.all()
    ordered = apply_ordering(
        qs,
        sort,
        fields={"days": "stage_changed_at"},
        default_field="days",
        inverted={"days"},
        tiebreaker="-id",
    )
    sql = str(ordered.query)
    assert "stage_changed_at" in sql
    assert "ORDER BY" in sql.upper()
