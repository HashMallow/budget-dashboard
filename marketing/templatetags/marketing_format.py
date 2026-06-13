from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import template
from django.utils.safestring import mark_safe

from marketing.models import CostBucket, PaymentStage
from marketing.permissions import user_has_admin_access
from marketing.translations import translate

register = template.Library()


@register.simple_tag(takes_context=True)
def t(context, text):
    """Translate a UI string to the active language (English source is the key)."""
    return translate(text, context.get("ui_lang", "en"))


@register.simple_tag(takes_context=True)
def form_errors(context, errors):
    """Render a translated Django form error list."""
    lang = context.get("ui_lang", "en")
    if not errors:
        return ""
    items = "".join(f"<li>{translate(str(error), lang)}</li>" for error in errors)
    return mark_safe(f'<ul class="errorlist">{items}</ul>')


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
