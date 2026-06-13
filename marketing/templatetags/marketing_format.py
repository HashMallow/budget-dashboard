from __future__ import annotations

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from marketing.jalali import format_jalali_date
from marketing.models import CostBucket, PaymentStage
from marketing.money_format import (
    COMPACT,
    FULL,
    current_money_display,
    format_money,
    format_money_full,
    split_fa_compact_amount,
)
from marketing.permissions import user_has_admin_access
from marketing.table_sort import sort_href
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


@register.simple_tag(takes_context=True)
def display_date(context, value):
    if not value:
        return "-"
    if context.get("ui_lang", "en") == "fa":
        return format_jalali_date(value)
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


@register.filter
def money(value, mode_override: str = "") -> str:
    ctx = current_money_display()
    mode = mode_override or ctx["mode"]
    if mode not in {FULL, COMPACT}:
        mode = FULL
    lang = ctx["lang"]
    unit = ctx.get("unit", "rial")
    formatted = format_money(value, mode, lang, unit)

    def _display_html(text: str) -> str:
        if lang == "fa" and mode == COMPACT:
            parts = split_fa_compact_amount(text)
            if parts:
                num, suffix = parts
                # RTL isolate: number is read first, scale word (میلیون/…) immediately after.
                return mark_safe(
                    f'<span class="money-compact-fa" dir="rtl">'
                    f"{conditional_escape(num)} {suffix}</span>"
                )
        return text

    if mode == COMPACT and mode_override != FULL:
        full = format_money_full(value, unit)
        if full != formatted:
            display = _display_html(formatted)
            return mark_safe(
                f'<span class="money-value" title="{conditional_escape(full)}">{display}</span>'
            )
    return _display_html(formatted)


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


@register.simple_tag(takes_context=True)
def sortable_th(context, label, field, css_class=""):
    request = context["request"]
    sort = context.get("table_sort")
    default_dirs = context.get("table_sort_defaults")
    if sort is None:
        return translate(label, context.get("ui_lang", "en"))
    href = sort_href(request, sort, field, default_dirs=default_dirs)
    active = "is-active" if sort.field == field else ""
    direction_class = sort.css_class(field)
    indicator = sort.indicator(field)
    text = translate(label, context.get("ui_lang", "en"))
    classes = " ".join(part for part in ("sortable-th", css_class, direction_class, active) if part)
    return mark_safe(
        f'<a class="{classes}" href="{conditional_escape(href)}">'
        f"{conditional_escape(text)}"
        f'<span class="sort-indicator" aria-hidden="true">{indicator}</span>'
        f"</a>"
    )


@register.simple_tag(takes_context=True)
def qs(context, **overrides):
    request = context["request"]
    from marketing.table_sort import query_string

    return query_string(request, **overrides)
