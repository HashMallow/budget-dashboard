from __future__ import annotations

import re
import unicodedata
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

User = get_user_model()


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[^\w\sآ-ی]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip().casefold()


def invoice_attachment_path(instance: InvoiceAttachment, filename: str) -> str:
    invoice_id = instance.invoice_id or "pending"
    return f"invoices/{invoice_id}/{instance.attachment_type.lower()}/{filename}"


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Role(models.TextChoices):
    MANAGER = "MANAGER", "Manager"
    EDITOR = "EDITOR", "Editor"
    OBSERVER = "OBSERVER", "Observer"


class CostBucket(models.TextChoices):
    TEAM = "TEAM", "Team"
    REFERRAL = "REFERRAL", "Referral"
    SMS = "SMS", "SMS"
    GENERAL = "GENERAL", "General"


class PaymentStage(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    FINANCE_REVIEW = "FINANCE_REVIEW", "Finance review"
    APPROVED = "APPROVED", "Approved"
    PAID = "PAID", "Paid"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class AttachmentType(models.TextChoices):
    INVOICE_IMAGE = "INVOICE_IMAGE", "Invoice image"
    PAYMENT_PROOF = "PAYMENT_PROOF", "Payment proof"
    OTHER = "OTHER", "Other"


class Team(TimestampedModel):
    name = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=180, unique=True, allow_unicode=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True) or normalize_name(self.name).replace(" ", "-")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class TeamAlias(TimestampedModel):
    raw_name = models.CharField(max_length=160, unique=True)
    normalized_raw_name = models.CharField(max_length=180, unique=True, db_index=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="aliases")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["raw_name"]
        indexes = [
            models.Index(fields=["normalized_raw_name", "is_active"]),
        ]
        verbose_name_plural = "team aliases"

    def save(self, *args, **kwargs):
        self.normalized_raw_name = normalize_name(self.raw_name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.raw_name} -> {self.team.name}"


class Vendor(TimestampedModel):
    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, db_index=True)
    tax_id = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["normalized_name"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["normalized_name"], name="unique_vendor_normalized_name"),
        ]

    def save(self, *args, **kwargs):
        if not self.normalized_name:
            self.normalized_name = normalize_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Campaign(TimestampedModel):
    name = models.CharField(max_length=255)
    year = models.PositiveIntegerField()
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name="campaigns")
    planned_start_date = models.DateField(null=True, blank=True)
    planned_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=40, default="PLANNED")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-year", "name"]
        indexes = [
            models.Index(fields=["year", "name"]),
            models.Index(fields=["team", "year"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["name", "year", "team"], name="unique_campaign_name_year_team"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.year})"


class BudgetLine(TimestampedModel):
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField(null=True, blank=True)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name="budget_lines")
    campaign = models.ForeignKey(
        Campaign,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="budget_lines",
    )
    category = models.CharField(max_length=180)
    planned_amount = models.DecimalField(max_digits=24, decimal_places=2, default=Decimal("0"))
    currency = models.CharField(max_length=16, default=settings.DEFAULT_CURRENCY)
    source_sheet = models.CharField(max_length=255, blank=True)
    source_row_number = models.PositiveIntegerField(null=True, blank=True)
    raw_data_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["year", "month", "team__name", "category"]
        indexes = [
            models.Index(fields=["year", "month"]),
            models.Index(fields=["team", "year", "month"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self) -> str:
        month = f"{self.month:02d}" if self.month else "annual"
        team = self.team.name if self.team else "All teams"
        return f"{self.year}-{month} {team} {self.category}"


class Invoice(TimestampedModel):
    invoice_number = models.CharField(max_length=120, db_index=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="invoices")
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    campaign = models.ForeignKey(Campaign, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    category = models.CharField(max_length=180)
    cost_bucket = models.CharField(max_length=20, choices=CostBucket.choices, default=CostBucket.TEAM)
    description = models.TextField(blank=True)
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=24, decimal_places=2)
    currency = models.CharField(max_length=16, default=settings.DEFAULT_CURRENCY)
    payment_stage = models.CharField(max_length=24, choices=PaymentStage.choices, default=PaymentStage.DRAFT)
    stage_changed_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_invoices",
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_invoices",
    )
    source_sheet = models.CharField(max_length=255, blank=True)
    source_row_number = models.PositiveIntegerField(null=True, blank=True)
    raw_data_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-invoice_date", "-created_at"]
        indexes = [
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["vendor", "invoice_number"]),
            models.Index(fields=["team", "invoice_date"]),
            models.Index(fields=["cost_bucket", "invoice_date"]),
            models.Index(fields=["payment_stage"]),
        ]

    @property
    def days_in_current_stage(self) -> int:
        changed_at = self.stage_changed_at or self.created_at
        if not changed_at:
            return 0
        return max((timezone.now().date() - changed_at.date()).days, 0)

    @property
    def invoice_year(self) -> int:
        return self.invoice_date.year

    @property
    def invoice_month(self) -> int:
        return self.invoice_date.month

    def set_payment_stage(self, new_stage: str, *, changed_by=None, note: str = "") -> None:
        self.payment_stage = new_stage
        self.updated_by = changed_by
        self._status_change_note = note
        self.save()

    def save(self, *args, **kwargs):
        old_stage = None
        if self.pk:
            old_stage = Invoice.objects.filter(pk=self.pk).values_list("payment_stage", flat=True).first()

        stage_changed = old_stage is not None and old_stage != self.payment_stage
        if stage_changed or not self.stage_changed_at:
            self.stage_changed_at = timezone.now()
        if self.payment_stage == PaymentStage.PAID and self.paid_at is None:
            self.paid_at = timezone.now()

        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            update_fields = set(update_fields)
            if stage_changed:
                update_fields.add("stage_changed_at")
            if self.payment_stage == PaymentStage.PAID:
                update_fields.add("paid_at")
            kwargs["update_fields"] = update_fields

        super().save(*args, **kwargs)

        if stage_changed:
            InvoiceStatusHistory.objects.create(
                invoice=self,
                old_stage=old_stage,
                new_stage=self.payment_stage,
                changed_by=self.updated_by,
                note=getattr(self, "_status_change_note", ""),
            )

    def __str__(self) -> str:
        return f"{self.invoice_number} - {self.vendor}"


class InvoiceAttachment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="attachments")
    attachment_type = models.CharField(max_length=24, choices=AttachmentType.choices)
    file = models.FileField(upload_to=invoice_attachment_path)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="invoice_attachments")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["invoice", "attachment_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.invoice} {self.attachment_type}"


class UserTeamAccess(TimestampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="team_access")
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.CASCADE, related_name="user_access")
    role = models.CharField(max_length=16, choices=Role.choices)
    can_upload_invoice_files = models.BooleanField(default=False)
    can_upload_payment_proofs = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)
    can_view_referral_sms = models.BooleanField(default=False)
    is_global = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["user__username", "role", "team__name"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["team", "role"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(is_global=True) | Q(team__isnull=False),
                name="team_required_when_access_is_not_global",
            ),
            models.UniqueConstraint(
                fields=["user", "team", "role"],
                condition=Q(is_global=False),
                name="unique_team_role_access_per_user",
            ),
            models.UniqueConstraint(
                fields=["user", "role"],
                condition=Q(is_global=True),
                name="unique_global_role_access_per_user",
            ),
        ]

    def clean(self):
        if not self.is_global and self.team_id is None:
            raise ValidationError({"team": "Team is required for non-global access."})
        if self.is_global and self.team_id is not None:
            raise ValidationError({"team": "Global access must not be tied to a specific team."})

    def __str__(self) -> str:
        scope = "Global" if self.is_global else str(self.team)
        return f"{self.user} {self.role} {scope}"


class InvoiceStatusHistory(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="status_history")
    old_stage = models.CharField(max_length=24, choices=PaymentStage.choices, blank=True)
    new_stage = models.CharField(max_length=24, choices=PaymentStage.choices)
    changed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["invoice", "-changed_at"]),
            models.Index(fields=["new_stage", "-changed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.invoice}: {self.old_stage} -> {self.new_stage}"
