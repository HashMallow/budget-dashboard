from __future__ import annotations

from django.contrib import admin

from .models import (
    BudgetLine,
    Campaign,
    Contract,
    ContractAttachment,
    ContractStatusHistory,
    Invoice,
    InvoiceAttachment,
    InvoiceStatusHistory,
    Requester,
    SpendCategory,
    SubTeam,
    Team,
    TeamAlias,
    UserTeamAccess,
    Vendor,
)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(TeamAlias)
class TeamAliasAdmin(admin.ModelAdmin):
    list_display = ("raw_name", "team", "is_active", "updated_at")
    list_filter = ("is_active", "team")
    search_fields = ("raw_name", "normalized_raw_name", "team__name")
    autocomplete_fields = ("team",)
    readonly_fields = ("normalized_raw_name",)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "normalized_name", "tax_id", "updated_at")
    search_fields = ("name", "normalized_name", "tax_id")
    readonly_fields = ("normalized_name",)


@admin.register(SpendCategory)
class SpendCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "normalized_name", "is_active", "source_sheet", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "normalized_name")
    readonly_fields = ("normalized_name",)


@admin.register(SubTeam)
class SubTeamAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "is_active", "source_sheet", "updated_at")
    list_filter = ("is_active", "team")
    search_fields = ("name", "normalized_name")
    autocomplete_fields = ("team",)
    readonly_fields = ("normalized_name",)


@admin.register(Requester)
class RequesterAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "source_sheet", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "normalized_name")
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


class ContractAttachmentInline(admin.TabularInline):
    model = ContractAttachment
    extra = 0
    fields = ("attachment_type", "file", "uploaded_by", "uploaded_at", "notes")
    readonly_fields = ("uploaded_at",)
    autocomplete_fields = ("uploaded_by",)


class ContractStatusHistoryInline(admin.TabularInline):
    model = ContractStatusHistory
    extra = 0
    fields = ("old_stage", "new_stage", "changed_by", "changed_at", "note")
    readonly_fields = ("old_stage", "new_stage", "changed_by", "changed_at", "note")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "vendor",
        "team",
        "stage",
        "start_date",
        "end_date",
        "days_in_current_stage",
    )
    list_filter = ("stage", "team", "currency", "end_date")
    search_fields = ("title", "contract_number", "vendor__name", "description")
    autocomplete_fields = ("vendor", "team", "created_by", "updated_by")
    readonly_fields = ("stage_changed_at", "days_in_current_stage")
    inlines = (ContractAttachmentInline, ContractStatusHistoryInline)

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ContractAttachment)
class ContractAttachmentAdmin(admin.ModelAdmin):
    list_display = ("contract", "attachment_type", "uploaded_by", "uploaded_at")
    list_filter = ("attachment_type", "uploaded_at")
    search_fields = ("contract__title", "contract__vendor__name", "notes")
    autocomplete_fields = ("contract", "uploaded_by")


@admin.register(ContractStatusHistory)
class ContractStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("contract", "old_stage", "new_stage", "changed_by", "changed_at")
    list_filter = ("old_stage", "new_stage", "changed_at")
    search_fields = ("contract__title", "contract__vendor__name", "note")
    autocomplete_fields = ("contract", "changed_by")
    readonly_fields = ("contract", "old_stage", "new_stage", "changed_by", "changed_at", "note")
