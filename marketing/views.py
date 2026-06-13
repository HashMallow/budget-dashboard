from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from openpyxl import Workbook

from .forms import (
    ExcelImportUploadForm,
    InvoiceAttachmentForm,
    InvoiceForm,
    InvoiceStatusForm,
    UserAccessCreateForm,
    user_can_create_invoice,
)
from .importers.excel import ImportResult, import_marketing_workbook
from .jalali import JALALI_MONTHS, gregorian_to_jalali, jalali_year_bounds
from .models import (
    BudgetLine,
    CostBucket,
    Invoice,
    PaymentStage,
    Team,
    UserTeamAccess,
)
from .permissions import (
    can_edit_invoice,
    can_export,
    filter_budget_lines_for_user,
    filter_invoices_for_user,
    filter_teams_for_user,
    get_user_scope,
    user_has_admin_access,
)

User = get_user_model()
ZERO = Decimal("0")


def get_months(request) -> list[tuple[int, str]]:
    """Persian (Jalali) month labels, localized to the active UI language."""
    if request.session.get("ui_lang", "en") == "fa":
        return [(number, persian) for number, persian, _latin in JALALI_MONTHS]
    return [(number, latin) for number, _persian, latin in JALALI_MONTHS]


def filter_by_jalali_year(queryset, year: str):
    """Filter invoices by a Jalali year using the matching Gregorian date range."""
    if year and year.isdigit():
        start, end = jalali_year_bounds(int(year))
        return queryset.filter(invoice_date__range=(start, end))
    return queryset


def distinct_jalali_years(queryset) -> list[int]:
    # Small datasets: convert each invoice date. Revisit with a stored Jalali year
    # column if invoice volume grows large.
    years = {
        gregorian_to_jalali(value.year, value.month, value.day)[0]
        for value in queryset.values_list("invoice_date", flat=True)
        if value
    }
    return sorted(years, reverse=True)


def forbidden(message: str = "You are not allowed to perform this action.") -> HttpResponseForbidden:
    return HttpResponseForbidden(message)


def decimal_sum(queryset, field: str = "amount") -> Decimal:
    return queryset.aggregate(total=Sum(field))["total"] or ZERO


def percent(value: Decimal, maximum: Decimal) -> int:
    """Bar width (0-100) for a value relative to a maximum.

    Any strictly positive value gets a small minimum width so that small-but-real
    amounts stay visible and distinguishable from a true zero on the chart.
    """
    if not maximum or value <= 0:
        return 0
    ratio = (float(value) / float(maximum)) * 100
    return min(max(int(round(ratio)), 2), 100)


def visible_invoice_queryset(request):
    queryset = Invoice.objects.select_related("vendor", "team", "campaign").order_by("-invoice_date", "-id")
    return filter_invoices_for_user(queryset, request.user)


def visible_team_queryset(request):
    return filter_teams_for_user(Team.objects.filter(is_active=True), request.user).order_by("name")


def filter_invoice_queryset(request, queryset):
    filters = {
        "q": request.GET.get("q", "").strip(),
        "year": request.GET.get("year", "").strip(),
        "team": request.GET.get("team", "").strip(),
        "stage": request.GET.get("stage", "").strip(),
        "bucket": request.GET.get("bucket", "").strip(),
    }

    if filters["q"]:
        queryset = queryset.filter(
            Q(invoice_number__icontains=filters["q"])
            | Q(vendor__name__icontains=filters["q"])
            | Q(campaign__name__icontains=filters["q"])
            | Q(category__icontains=filters["q"])
            | Q(description__icontains=filters["q"])
        )
    if filters["year"].isdigit():
        queryset = filter_by_jalali_year(queryset, filters["year"])
    if filters["team"].isdigit():
        queryset = queryset.filter(team_id=int(filters["team"]))
    if filters["stage"]:
        queryset = queryset.filter(payment_stage=filters["stage"])
    if filters["bucket"]:
        queryset = queryset.filter(cost_bucket=filters["bucket"])
    return queryset, filters


def result_summary(result: ImportResult) -> list[dict[str, int | str]]:
    return [
        {
            "label": "Teams",
            "created": result.teams.created,
            "updated": result.teams.updated,
            "skipped": result.teams.skipped,
        },
        {
            "label": "Vendors",
            "created": result.vendors.created,
            "updated": result.vendors.updated,
            "skipped": result.vendors.skipped,
        },
        {
            "label": "Campaigns",
            "created": result.campaigns.created,
            "updated": result.campaigns.updated,
            "skipped": result.campaigns.skipped,
        },
        {
            "label": "Invoices",
            "created": result.invoices.created,
            "updated": result.invoices.updated,
            "skipped": result.invoices.skipped,
        },
        {
            "label": "Budget",
            "created": result.budget_lines.created,
            "updated": result.budget_lines.updated,
            "skipped": result.budget_lines.skipped,
        },
    ]


@login_required
def dashboard(request):
    months = get_months(request)
    base_queryset = visible_invoice_queryset(request)
    years = distinct_jalali_years(base_queryset)
    selected_year = request.GET.get("year", "").strip()
    selected_team = request.GET.get("team", "").strip()

    invoices = base_queryset
    if selected_year.isdigit():
        invoices = filter_by_jalali_year(invoices, selected_year)
    if selected_team.isdigit():
        invoices = invoices.filter(team_id=int(selected_team))

    total_spend = decimal_sum(invoices)
    paid_spend = decimal_sum(invoices.filter(payment_stage=PaymentStage.PAID))
    invoice_count = invoices.count()
    referral_total = decimal_sum(invoices.filter(cost_bucket=CostBucket.REFERRAL))
    sms_total = decimal_sum(invoices.filter(cost_bucket=CostBucket.SMS))

    monthly_map = {month_number: ZERO for month_number, _label in months}
    for row in invoices.values("invoice_date").annotate(total=Sum("amount")):
        invoice_date = row["invoice_date"]
        jalali_month = gregorian_to_jalali(invoice_date.year, invoice_date.month, invoice_date.day)[1]
        monthly_map[jalali_month] += row["total"] or ZERO
    max_monthly = max(monthly_map.values(), default=ZERO)
    monthly_rows = [
        {
            "month": month_number,
            "label": label,
            "total": monthly_map[month_number],
            "percent": percent(monthly_map[month_number], max_monthly),
        }
        for month_number, label in months
    ]

    team_total_rows = list(
        invoices.filter(cost_bucket=CostBucket.TEAM)
        .values("team__name")
        .annotate(total=Sum("amount"), invoice_count=Count("id"))
        .order_by("-total")[:10]
    )
    max_team_total = max((row["total"] or ZERO for row in team_total_rows), default=ZERO)
    for row in team_total_rows:
        row["percent"] = percent(row["total"] or ZERO, max_team_total)
        row["team_name"] = row["team__name"] or "No team"

    vendor_rows = list(
        invoices.values("vendor_id", "vendor__name")
        .annotate(total=Sum("amount"), invoice_count=Count("id"))
        .order_by("-total")[:8]
    )

    campaign_rows = list(
        invoices.filter(campaign__isnull=False)
        .values("campaign_id", "campaign__name", "campaign__year")
        .annotate(total=Sum("amount"), invoice_count=Count("id"))
        .order_by("-total")[:8]
    )

    stage_rows = list(
        invoices.values("payment_stage")
        .annotate(invoice_count=Count("id"), total=Sum("amount"))
        .order_by("-invoice_count")
    )

    attention_invoices = sorted(
        invoices.filter(payment_stage=PaymentStage.FINANCE_REVIEW)[:20],
        key=lambda item: item.days_in_current_stage,
        reverse=True,
    )[:6]

    context = {
        "scope": get_user_scope(request.user),
        "years": years,
        "selected_year": selected_year,
        "selected_team": selected_team,
        "teams": visible_team_queryset(request),
        "total_spend": total_spend,
        "paid_spend": paid_spend,
        "invoice_count": invoice_count,
        "referral_total": referral_total,
        "sms_total": sms_total,
        "monthly_rows": monthly_rows,
        "team_total_rows": team_total_rows,
        "vendor_rows": vendor_rows,
        "campaign_rows": campaign_rows,
        "stage_rows": stage_rows,
        "attention_invoices": attention_invoices,
        "can_create_invoice": user_can_create_invoice(request.user),
        "can_export_data": can_export(request.user),
    }
    return render(request, "marketing/dashboard.html", context)


@login_required
def invoice_list(request):
    queryset, filters = filter_invoice_queryset(request, visible_invoice_queryset(request))
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "page_obj": page_obj,
        "filters": filters,
        "teams": visible_team_queryset(request),
        "years": distinct_jalali_years(visible_invoice_queryset(request)),
        "payment_stages": PaymentStage.choices,
        "cost_buckets": CostBucket.choices,
        "can_create_invoice": user_can_create_invoice(request.user),
        "can_export_data": can_export(request.user),
    }
    return render(request, "marketing/invoices/list.html", context)


@login_required
def invoice_detail(request, pk: int):
    invoice = get_object_or_404(visible_invoice_queryset(request), pk=pk)
    status_form = InvoiceStatusForm(invoice=invoice)
    attachment_form = InvoiceAttachmentForm(user=request.user, invoice=invoice)
    context = {
        "invoice": invoice,
        "status_form": status_form,
        "attachment_form": attachment_form,
        "can_edit": can_edit_invoice(request.user, invoice),
        "can_upload": attachment_form.has_allowed_types,
    }
    return render(request, "marketing/invoices/detail.html", context)


@login_required
def invoice_create(request):
    if not user_can_create_invoice(request.user):
        return forbidden()
    if request.method == "POST":
        form = InvoiceForm(request.POST, user=request.user)
        if form.is_valid():
            invoice = form.save()
            messages.success(request, "Invoice saved.")
            return redirect("marketing:invoice_detail", pk=invoice.pk)
    else:
        form = InvoiceForm(user=request.user)
    return render(request, "marketing/invoices/form.html", {"form": form, "mode": "create"})


@login_required
def invoice_edit(request, pk: int):
    invoice = get_object_or_404(visible_invoice_queryset(request), pk=pk)
    if not can_edit_invoice(request.user, invoice):
        return forbidden()
    if request.method == "POST":
        form = InvoiceForm(request.POST, user=request.user, instance=invoice)
        if form.is_valid():
            invoice = form.save()
            messages.success(request, "Invoice updated.")
            return redirect("marketing:invoice_detail", pk=invoice.pk)
    else:
        form = InvoiceForm(user=request.user, instance=invoice)
    return render(request, "marketing/invoices/form.html", {"form": form, "invoice": invoice, "mode": "edit"})


@login_required
@require_POST
def invoice_stage_update(request, pk: int):
    invoice = get_object_or_404(visible_invoice_queryset(request), pk=pk)
    if not can_edit_invoice(request.user, invoice):
        return forbidden()
    form = InvoiceStatusForm(request.POST, invoice=invoice)
    if form.is_valid():
        invoice.set_payment_stage(
            form.cleaned_data["payment_stage"],
            changed_by=request.user,
            note=form.cleaned_data.get("note", ""),
        )
        messages.success(request, "Payment stage updated.")
    else:
        messages.error(request, "Invalid payment stage.")
    return redirect("marketing:invoice_detail", pk=invoice.pk)


@login_required
@require_POST
def invoice_attachment_upload(request, pk: int):
    invoice = get_object_or_404(visible_invoice_queryset(request), pk=pk)
    form = InvoiceAttachmentForm(request.POST, request.FILES, user=request.user, invoice=invoice)
    if not form.has_allowed_types:
        return forbidden("You are not allowed to upload files for this invoice.")
    if form.is_valid():
        attachment = form.save(commit=False)
        attachment.invoice = invoice
        attachment.uploaded_by = request.user
        attachment.save()
        messages.success(request, "File uploaded.")
    else:
        messages.error(request, "Upload failed. Check the file type or your permissions.")
    return redirect("marketing:invoice_detail", pk=invoice.pk)


@login_required
def vendor_report(request):
    queryset, filters = filter_invoice_queryset(request, visible_invoice_queryset(request))
    grouped: dict[int, dict] = {}
    for invoice in queryset:
        vendor_id = invoice.vendor_id
        if vendor_id not in grouped:
            grouped[vendor_id] = {
                "vendor": invoice.vendor,
                "total": ZERO,
                "invoice_count": 0,
                "invoice_numbers": [],
                "stages": set(),
            }
        row = grouped[vendor_id]
        row["total"] += invoice.amount or ZERO
        row["invoice_count"] += 1
        row["invoice_numbers"].append(invoice.invoice_number)
        row["stages"].add(invoice.get_payment_stage_display())

    vendor_rows = sorted(grouped.values(), key=lambda item: item["total"], reverse=True)
    for row in vendor_rows:
        row["stages"] = sorted(row["stages"])
        row["visible_invoice_numbers"] = row["invoice_numbers"][:8]
        row["remaining_invoice_count"] = max(len(row["invoice_numbers"]) - 8, 0)

    context = {
        "vendor_rows": vendor_rows,
        "filters": filters,
        "teams": visible_team_queryset(request),
        "payment_stages": PaymentStage.choices,
        "cost_buckets": CostBucket.choices,
        "can_export_data": can_export(request.user),
    }
    return render(request, "marketing/vendors/report.html", context)


@login_required
def campaign_report(request):
    months = get_months(request)
    queryset, filters = filter_invoice_queryset(request, visible_invoice_queryset(request))
    campaign_totals = list(
        queryset.filter(campaign__isnull=False)
        .values("campaign_id", "campaign__name", "campaign__year", "campaign__team__name")
        .annotate(total=Sum("amount"), invoice_count=Count("id"))
        .order_by("-total")
    )
    max_total = max((row["total"] or ZERO for row in campaign_totals), default=ZERO)
    for row in campaign_totals:
        row["percent"] = percent(row["total"] or ZERO, max_total)

    monthly_campaigns = defaultdict(lambda: {month: ZERO for month, _label in months})
    for row in (
        queryset.filter(campaign__isnull=False)
        .values("campaign__name", "invoice_date")
        .annotate(total=Sum("amount"))
    ):
        invoice_date = row["invoice_date"]
        jalali_month = gregorian_to_jalali(invoice_date.year, invoice_date.month, invoice_date.day)[1]
        monthly_campaigns[row["campaign__name"]][jalali_month] += row["total"] or ZERO

    context = {
        "campaign_rows": campaign_totals,
        "monthly_campaigns": dict(monthly_campaigns),
        "months": months,
        "filters": filters,
        "teams": visible_team_queryset(request),
        "years": distinct_jalali_years(visible_invoice_queryset(request)),
        "payment_stages": PaymentStage.choices,
        "cost_buckets": CostBucket.choices,
    }
    return render(request, "marketing/campaigns/report.html", context)


@login_required
def budget_list(request):
    months = get_months(request)
    queryset = filter_budget_lines_for_user(
        BudgetLine.objects.select_related("team", "campaign").order_by("year", "team__name", "category", "month"),
        request.user,
    )
    year = request.GET.get("year", "").strip()
    team = request.GET.get("team", "").strip()
    q = request.GET.get("q", "").strip()
    if year.isdigit():
        queryset = queryset.filter(year=int(year))
    if team.isdigit():
        queryset = queryset.filter(team_id=int(team))
    if q:
        queryset = queryset.filter(Q(category__icontains=q) | Q(team__name__icontains=q))

    years = (
        filter_budget_lines_for_user(BudgetLine.objects.all(), request.user)
        .order_by("-year")
        .values_list("year", flat=True)
        .distinct()
    )
    pivot = {}
    for line in queryset:
        key = (line.team.name if line.team else "No team", line.category)
        if key not in pivot:
            pivot[key] = {
                "team": key[0],
                "category": key[1],
                "months": {month_number: ZERO for month_number, _label in months},
                "total": ZERO,
            }
        if line.month:
            pivot[key]["months"][line.month] += line.planned_amount or ZERO
        pivot[key]["total"] += line.planned_amount or ZERO

    paginator = Paginator(queryset, 50)
    context = {
        "page_obj": paginator.get_page(request.GET.get("page")),
        "pivot_rows": sorted(pivot.values(), key=lambda item: (item["team"], item["category"])),
        "months": months,
        "years": years,
        "teams": visible_team_queryset(request),
        "filters": {"year": year, "team": team, "q": q},
    }
    return render(request, "marketing/budgets/list.html", context)


@login_required
def import_workbook(request):
    if not user_has_admin_access(request.user):
        return forbidden()

    form = ExcelImportUploadForm()
    result = None
    summary = None
    pending_path = request.session.get("pending_import_path")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "confirm":
            if not pending_path:
                messages.error(request, "There is no file ready to import.")
            else:
                result = import_marketing_workbook(pending_path, dry_run=False)
                summary = result_summary(result)
                messages.success(request, "Excel data imported into the database.")
                request.session.pop("pending_import_path", None)
                pending_path = None
        else:
            form = ExcelImportUploadForm(request.POST, request.FILES)
            if form.is_valid():
                storage = FileSystemStorage(location=Path(settings.MEDIA_ROOT) / "imports")
                filename = f"{uuid4().hex}.xlsx"
                stored_name = storage.save(filename, form.cleaned_data["workbook"])
                workbook_path = storage.path(stored_name)
                result = import_marketing_workbook(workbook_path, dry_run=True)
                summary = result_summary(result)
                request.session["pending_import_path"] = workbook_path
                pending_path = workbook_path
                messages.info(request, "Dry-run complete. If the result looks correct, confirm the import.")

    context = {
        "form": form,
        "result": result,
        "summary": summary,
        "pending_path": pending_path,
        "skipped_preview": result.skipped_rows[:20] if result else [],
    }
    return render(request, "marketing/imports/upload.html", context)


@login_required
def user_access(request):
    if not user_has_admin_access(request.user):
        return forbidden()

    form = UserAccessCreateForm(user=request.user)
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

        form = UserAccessCreateForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "New user created.")
            return redirect("marketing:user_access")

    users = User.objects.prefetch_related("groups", "team_access__team").order_by("username")
    return render(request, "marketing/users/access.html", {"form": form, "users": users})


@login_required
def export_invoices_excel(request):
    if not can_export(request.user):
        return forbidden("You do not have permission to export.")
    queryset, _filters = filter_invoice_queryset(request, visible_invoice_queryset(request))
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Invoices"
    sheet.append([
        "Invoice number",
        "Vendor",
        "Team",
        "Campaign",
        "Category",
        "Cost bucket",
        "Invoice date",
        "Amount",
        "Currency",
        "Payment stage",
        "Days in stage",
    ])
    for invoice in queryset:
        sheet.append([
            invoice.invoice_number,
            invoice.vendor.name,
            invoice.team.name if invoice.team else "",
            invoice.campaign.name if invoice.campaign else "",
            invoice.category,
            invoice.cost_bucket,
            invoice.invoice_date.isoformat(),
            invoice.amount,
            invoice.currency,
            invoice.payment_stage,
            invoice.days_in_current_stage,
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="marketing-invoices.xlsx"'
    workbook.save(response)
    return response


@login_required
def invoice_report_print(request):
    if not can_export(request.user):
        return forbidden("You do not have permission to view reports.")
    queryset, filters = filter_invoice_queryset(request, visible_invoice_queryset(request))
    vendor_rows = list(
        queryset.values("vendor__name")
        .annotate(total=Sum("amount"), invoice_count=Count("id"))
        .order_by("-total")[:30]
    )
    context = {
        "generated_at": timezone.now(),
        "filters": filters,
        "total_spend": decimal_sum(queryset),
        "invoice_count": queryset.count(),
        "vendor_rows": vendor_rows,
        "stage_rows": queryset.values("payment_stage").annotate(invoice_count=Count("id")).order_by("payment_stage"),
    }
    return render(request, "marketing/print/invoice_report.html", context)


@require_POST
def set_display_preferences(request):
    ui_lang = request.POST.get("ui_lang")
    number_locale = request.POST.get("number_locale")
    if ui_lang in {"fa", "en"}:
        request.session["ui_lang"] = ui_lang
    if number_locale in {"fa", "en"}:
        request.session["number_locale"] = number_locale

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = "/"
    return redirect(next_url)


@require_POST
def logout_view(request):
    logout(request)
    return redirect("marketing:login")
