from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render

from .core import (
    forbidden,
    get_ui_lang,
)
from ..forms import (
    TeamAccessForm,
    UserAccessCreateForm,
)
from ..models import (
    UserTeamAccess,
)
from ..permissions import (
    user_has_admin_access,
)

User = get_user_model()
ZERO = Decimal("0")
_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#ca8a04"/><stop offset="1" stop-color="#facc15"/>'
    "</linearGradient></defs>"
    '<rect width="64" height="64" rx="14" fill="url(#g)"/>'
    '<rect x="18" y="14" width="28" height="36" rx="3" fill="#fff"/>'
    '<circle cx="24" cy="20" r="3" fill="#2563eb"/>'
    '<line x1="22" y1="26" x2="42" y2="26" stroke="#2563eb" stroke-width="2" stroke-linecap="round"/>'
    '<line x1="22" y1="32" x2="42" y2="32" stroke="#2563eb" stroke-width="2" stroke-linecap="round"/>'
    '<line x1="22" y1="38" x2="38" y2="38" stroke="#2563eb" stroke-width="2" stroke-linecap="round"/>'
    "</svg>"
)
INVOICE_SORT_FIELDS = {
    "number": "invoice_number",
    "vendor": "vendor__name",
    "team": "team__name",
    "category": "category",
    "date": "invoice_date",
    "amount": "amount",
    "stage": "payment_stage",
    "days": "stage_changed_at",
}
INVOICE_SORT_DEFAULTS = {
    "number": "asc",
    "vendor": "asc",
    "team": "asc",
    "category": "asc",
    "date": "desc",
    "amount": "desc",
    "stage": "asc",
    "days": "desc",
}
VENDOR_SORT_KEYS = {
    "vendor": lambda row: row["vendor"].name.lower(),
    "invoices": lambda row: row["invoice_count"],
    "amount": lambda row: row["total"],
}
VENDOR_SORT_DEFAULTS = {"vendor": "asc", "invoices": "desc", "amount": "desc"}
CAMPAIGN_SORT_FIELDS = {
    "campaign": "campaign__name",
    "year": "campaign__year",
    "team": "campaign__team__name",
    "invoices": "invoice_count",
    "amount": "total",
}
CAMPAIGN_SORT_DEFAULTS = {
    "campaign": "asc",
    "year": "desc",
    "team": "asc",
    "invoices": "desc",
    "amount": "desc",
}
TEAM_SORT_KEYS = {
    "team": lambda row: row["team"].name.lower(),
    "invoices": lambda row: row["invoice_count"],
    "amount": lambda row: row["total_spend"],
}
TEAM_SORT_DEFAULTS = {"team": "asc", "invoices": "desc", "amount": "desc"}
BUDGET_SORT_FIELDS = {
    "year": "year",
    "month": "month",
    "team": "team__name",
    "campaign": "campaign__name",
    "category": "category",
    "amount": "planned_amount",
}
BUDGET_SORT_DEFAULTS = {
    "year": "desc",
    "month": "asc",
    "team": "asc",
    "campaign": "asc",
    "category": "asc",
    "amount": "desc",
}
BUDGET_PIVOT_SORT_KEYS = {
    "team": lambda row: row["team"].lower(),
    "category": lambda row: row["category"].lower(),
    "total": lambda row: row["total"],
}
CONTRACT_SORT_FIELDS = {
    "title": "title",
    "vendor": "vendor__name",
    "team": "team__name",
    "stage": "stage",
    "end": "end_date",
    "days": "stage_changed_at",
}
CONTRACT_SORT_DEFAULTS = {
    "title": "asc",
    "vendor": "asc",
    "team": "asc",
    "stage": "asc",
    "end": "asc",
    "days": "desc",
}


def user_access(request):
    if not user_has_admin_access(request.user):
        return forbidden()

    form = UserAccessCreateForm(user=request.user, ui_lang=get_ui_lang(request))
    access_form = TeamAccessForm(admin_user=request.user, ui_lang=get_ui_lang(request))
    if request.method == "POST":
        action = request.POST.get("action")
        if action in {"deactivate", "activate"}:
            target = get_object_or_404(User, pk=request.POST.get("user_id"))
            if target == request.user and action == "deactivate":
                messages.error(request, "You cannot deactivate your own account.")
            else:
                target.is_active = action == "activate"
                target.save(update_fields=["is_active"])
                UserTeamAccess.objects.filter(user=target).update(is_active=target.is_active)
                messages.success(request, "User status updated.")
            return redirect("marketing:user_access")

        if action in {"access_enable", "access_disable", "access_remove"}:
            access = get_object_or_404(UserTeamAccess, pk=request.POST.get("access_id"))
            if action == "access_remove":
                access.delete()
                messages.success(request, "Access rule removed.")
            else:
                access.is_active = action == "access_enable"
                access.save(update_fields=["is_active"])
                messages.success(request, "Access rule updated.")
            return redirect("marketing:user_access")

        if action == "grant_access":
            access_form = TeamAccessForm(request.POST, admin_user=request.user, ui_lang=get_ui_lang(request))
            if access_form.is_valid():
                access_form.save()
                messages.success(request, "Access rule added.")
                return redirect("marketing:user_access")
        else:
            form = UserAccessCreateForm(request.POST, user=request.user, ui_lang=get_ui_lang(request))
            if form.is_valid():
                form.save()
                messages.success(request, "New user created.")
                return redirect("marketing:user_access")

    users = User.objects.prefetch_related("groups", "team_access__team").order_by("username")
    return render(
        request,
        "marketing/users/access.html",
        {"form": form, "access_form": access_form, "users": users},
    )
