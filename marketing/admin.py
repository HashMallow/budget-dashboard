from __future__ import annotations

from django.contrib import admin

from .models import (
    BudgetLine,
    Campaign,
    Invoice,
    InvoiceAttachment,
    InvoiceStatusHistory,
    Team,
    UserTeamAccess,
    Vendor,
)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "normalized_name", "tax_id", "updated_at")
    search_fields = ("name", "normalized_name", "tax_id")
    readonly_fields = ("normalized_name",)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "year", "team", "status", "planned_start_date", "planned_end_date")
    list_filter = ("year", "status", "team")
    search_fields = ("name", "notes")
    autocomplete_fields = ("team",)


@admin.register(BudgetLine)
class BudgetLineAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "team", "campaign", "category", "planned_amount", "currency")
    list_filter = ("year", "month", "team", "currency")
    search_fields = ("category", "source_sheet")
    autocomplete_fields = ("team", "campaign")
    readonly_fields = ("raw_data_json",)


class InvoiceAttachmentInline(admin.TabularInline):
    model = InvoiceAttachment
    extra = 0
    fields = ("attachment_type", "file", "uploaded_by", "uploaded_at", "notes")
    readonly_fields = ("uploaded_at",)
    autocomplete_fields = ("uploaded_by",)


class InvoiceStatusHistoryInline(admin.TabularInline):
    model = InvoiceStatusHistory
    extra = 0
    fields = ("old_stage", "new_stage", "changed_by", "changed_at", "note")
    readonly_fields = ("old_stage", "new_stage", "changed_by", "changed_at", "note")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "vendor",
        "team",
        "cost_bucket",
        "invoice_date",
        "amount",
        "currency",
        "payment_stage",
        "days_in_current_stage",
    )
    list_filter = ("payment_stage", "cost_bucket", "team", "currency", "invoice_date")
    search_fields = ("invoice_number", "vendor__name", "description", "category")
    autocomplete_fields = ("vendor", "team", "campaign", "created_by", "updated_by")
    readonly_fields = ("stage_changed_at", "paid_at", "raw_data_json", "days_in_current_stage")
    inlines = (InvoiceAttachmentInline, InvoiceStatusHistoryInline)

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(InvoiceAttachment)
class InvoiceAttachmentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "attachment_type", "uploaded_by", "uploaded_at")
    list_filter = ("attachment_type", "uploaded_at")
    search_fields = ("invoice__invoice_number", "invoice__vendor__name", "notes")
    autocomplete_fields = ("invoice", "uploaded_by")


@admin.register(UserTeamAccess)
class UserTeamAccessAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "team",
        "is_global",
        "can_view_referral_sms",
        "can_export",
        "is_active",
    )
    list_filter = ("role", "is_global", "is_active", "can_export", "can_view_referral_sms")
    search_fields = ("user__username", "user__email", "team__name")
    autocomplete_fields = ("user", "team")


@admin.register(InvoiceStatusHistory)
class InvoiceStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("invoice", "old_stage", "new_stage", "changed_by", "changed_at")
    list_filter = ("old_stage", "new_stage", "changed_at")
    search_fields = ("invoice__invoice_number", "invoice__vendor__name", "note")
    autocomplete_fields = ("invoice", "changed_by")
    readonly_fields = ("invoice", "old_stage", "new_stage", "changed_by", "changed_at", "note")
