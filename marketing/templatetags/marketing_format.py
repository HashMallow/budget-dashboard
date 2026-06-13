from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import template

from marketing.models import CostBucket, PaymentStage
from marketing.permissions import user_has_admin_access

register = template.Library()


@register.filter
def money(value) -> str:
    if value in {None, ""}:
        return "0"
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    return f"{amount:,.0f}"


@register.filter
def stage_label(value: str) -> str:
    labels = dict(PaymentStage.choices)
    return labels.get(value, value or "")


@register.filter
def bucket_label(value: str) -> str:
    labels = dict(CostBucket.choices)
    return labels.get(value, value or "")


@register.filter
def get_item(value, key):
    if value is None:
        return None
    return value.get(key)


@register.filter
def is_panel_admin(user) -> bool:
    return user_has_admin_access(user)
