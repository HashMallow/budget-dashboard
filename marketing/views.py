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
MONTHS = [
    (1, "فروردین / Jan"),
    (2, "اردیبهشت / Feb"),
    (3, "خرداد / Mar"),
    (4, "تیر / Apr"),
    (5, "مرداد / May"),
    (6, "شهریور / Jun"),
    (7, "مهر / Jul"),
    (8, "آبان / Aug"),
    (9, "آذر / Sep"),
    (10, "دی / Oct"),
    (11, "بهمن / Nov"),
    (12, "اسفند / Dec"),
]


def forbidden(message: str = "شما اجازه انجام این عملیات را ندارید.") -> HttpResponseForbidden:
    return HttpResponseForbidden(message)


def decimal_sum(queryset, field: str = "amount") -> Decimal:
    return queryset.aggregate(total=Sum(field))["total"] or ZERO


def percent(value: Decimal, maximum: Decimal) -> int:
    if not maximum:
        return 0
    return min(int((float(value) / float(maximum)) * 100), 100)


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
        queryset = queryset.filter(invoice_date__year=int(filters["year"]))
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
            "label": "تیم‌ها",
            "created": result.teams.created,
            "updated": result.teams.updated,
            "skipped": result.teams.skipped,
        },
        {
            "label": "وندورها",
            "created": result.vendors.created,
            "updated": result.vendors.updated,
            "skipped": result.vendors.skipped,
        },
        {
            "label": "کمپین‌ها",
            "created": result.campaigns.created,
            "updated": result.campaigns.updated,
            "skipped": result.campaigns.skipped,
        },
        {
            "label": "فاکتورها",
            "created": result.invoices.created,
            "updated": result.invoices.updated,
            "skipped": result.invoices.skipped,
        },
        {
            "label": "بودجه",
            "created": result.budget_lines.created,
            "updated": result.budget_lines.updated,
            "skipped": result.budget_lines.skipped,
        },
    ]


@login_required
def dashboard(request):
    base_queryset = visible_invoice_queryset(request)
    years = list(
        base_queryset.order_by("-invoice_date__year")
        .values_list("invoice_date__year", flat=True)
        .distinct()
    )
    selected_year = request.GET.get("year", "").strip()
    selected_team = request.GET.get("team", "").strip()

    invoices = base_queryset
    if selected_year.isdigit():
        invoices = invoices.filter(invoice_date__year=int(selected_year))
    if selected_team.isdigit():
        invoices = invoices.filter(team_id=int(selected_team))

    total_spend = decimal_sum(invoices)
    paid_spend = decimal_sum(invoices.filter(payment_stage=PaymentStage.PAID))
    invoice_count = invoices.count()
    referral_total = decimal_sum(invoices.filter(cost_bucket=CostBucket.REFERRAL))
    sms_total = decimal_sum(invoices.filter(cost_bucket=CostBucket.SMS))

    monthly_map = {month_number: ZERO for month_number, _label in MONTHS}
    for row in invoices.values("invoice_date__month").annotate(total=Sum("amount")):
        monthly_map[row["invoice_date__month"]] = row["total"] or ZERO
    max_monthly = max(monthly_map.values(), default=ZERO)
    monthly_rows = [
        {
            "month": month_number,
            "label": label,
            "total": monthly_map[month_number],
            "percent": percent(monthly_map[month_number], max_monthly),
        }
        for month_number, label in MONTHS
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
        row["team_name"] = row["team__name"] or "بدون تیم"

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
        "years": queryset.order_by("-invoice_date__year").values_list("invoice_date__year", flat=True).distinct(),
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
            messages.success(request, "فاکتور ثبت شد.")
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
            messages.success(request, "فاکتور به‌روزرسانی شد.")
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
        messages.success(request, "مرحله پرداخت به‌روزرسانی شد.")
    else:
        messages.error(request, "مرحله پرداخت معتبر نیست.")
    return redirect("marketing:invoice_detail", pk=invoice.pk)


@login_required
@require_POST
def invoice_attachment_upload(request, pk: int):
    invoice = get_object_or_404(visible_invoice_queryset(request), pk=pk)
    form = InvoiceAttachmentForm(request.POST, request.FILES, user=request.user, invoice=invoice)
    if not form.has_allowed_types:
        return forbidden("برای این فاکتور اجازه آپلود فایل ندارید.")
    if form.is_valid():
        attachment = form.save(commit=False)
        attachment.invoice = invoice
        attachment.uploaded_by = request.user
        attachment.save()
        messages.success(request, "فایل آپلود شد.")
    else:
        messages.error(request, "آپلود فایل انجام نشد. نوع فایل یا دسترسی را بررسی کنید.")
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

    monthly_campaigns = defaultdict(lambda: {month: ZERO for month, _label in MONTHS})
    for row in (
        queryset.filter(campaign__isnull=False)
        .values("campaign__name", "invoice_date__month")
        .annotate(total=Sum("amount"))
    ):
        monthly_campaigns[row["campaign__name"]][row["invoice_date__month"]] = row["total"] or ZERO

    context = {
        "campaign_rows": campaign_totals,
        "monthly_campaigns": dict(monthly_campaigns),
        "months": MONTHS,
        "filters": filters,
        "teams": visible_team_queryset(request),
        "payment_stages": PaymentStage.choices,
        "cost_buckets": CostBucket.choices,
    }
    return render(request, "marketing/campaigns/report.html", context)


@login_required
def budget_list(request):
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
        key = (line.team.name if line.team else "بدون تیم", line.category)
        if key not in pivot:
            pivot[key] = {
                "team": key[0],
                "category": key[1],
                "months": {month_number: ZERO for month_number, _label in MONTHS},
                "total": ZERO,
            }
        if line.month:
            pivot[key]["months"][line.month] += line.planned_amount or ZERO
        pivot[key]["total"] += line.planned_amount or ZERO

    paginator = Paginator(queryset, 50)
    context = {
        "page_obj": paginator.get_page(request.GET.get("page")),
        "pivot_rows": sorted(pivot.values(), key=lambda item: (item["team"], item["category"])),
        "months": MONTHS,
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
                messages.error(request, "هیچ فایل آماده‌ای برای import وجود ندارد.")
            else:
                result = import_marketing_workbook(pending_path, dry_run=False)
                summary = result_summary(result)
                messages.success(request, "اطلاعات اکسل وارد دیتابیس شد.")
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
                messages.info(request, "Dry-run انجام شد. اگر نتیجه درست است، import را تایید کنید.")

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
                messages.error(request, "نمی‌توانید کاربر فعلی خودتان را غیرفعال کنید.")
            else:
                target.is_active = action == "activate"
                target.save(update_fields=["is_active"])
                UserTeamAccess.objects.filter(user=target).update(is_active=target.is_active)
                messages.success(request, "وضعیت کاربر به‌روزرسانی شد.")
            return redirect("marketing:user_access")

        form = UserAccessCreateForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "کاربر جدید ساخته شد.")
            return redirect("marketing:user_access")

    users = User.objects.prefetch_related("groups", "team_access__team").order_by("username")
    return render(request, "marketing/users/access.html", {"form": form, "users": users})


@login_required
def export_invoices_excel(request):
    if not can_export(request.user):
        return forbidden("برای خروجی گرفتن دسترسی ندارید.")
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
        return forbidden("برای گزارش گرفتن دسترسی ندارید.")
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
