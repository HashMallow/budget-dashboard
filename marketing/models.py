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


def contract_attachment_path(instance: ContractAttachment, filename: str) -> str:
    contract_id = instance.contract_id or "pending"
    return f"contracts/{contract_id}/{instance.attachment_type.lower()}/{filename}"


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


class ContractStage(models.TextChoices):
    """Lifecycle of a vendor contract, including the legal review back-and-forth.

    Stages model the draft "pass-kari" between our legal team and the counterparty's legal team,
    then the signed/active lifecycle. Adjust the labels/values if the legal workflow differs.
    """

    DRAFT = "DRAFT", "Draft"
    INTERNAL_LEGAL_REVIEW = "INTERNAL_LEGAL_REVIEW", "Internal legal review"
    SENT_TO_COUNTERPARTY = "SENT_TO_COUNTERPARTY", "Sent to counterparty"
    COUNTERPARTY_REVIEW = "COUNTERPARTY_REVIEW", "Counterparty legal review"
    NEGOTIATION = "NEGOTIATION", "Negotiation / revisions"
    PENDING_SIGNATURE = "PENDING_SIGNATURE", "Pending signature"
    SIGNED = "SIGNED", "Signed / active"
    EXPIRED = "EXPIRED", "Expired"
    TERMINATED = "TERMINATED", "Terminated"
    CANCELLED = "CANCELLED", "Cancelled"


# Stages that mean the contract is no longer an open legal/active item.
CONTRACT_CLOSED_STAGES = frozenset(
    {
        ContractStage.EXPIRED,
        ContractStage.TERMINATED,
        ContractStage.CANCELLED,
    }
)


class ContractAttachmentType(models.TextChoices):
    DRAFT_VERSION = "DRAFT_VERSION", "Draft version"
    FINAL_VERSION = "FINAL_VERSION", "Final signed version"
    OTHER = "OTHER", "Other document"


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


class SpendCategory(TimestampedModel):
    """Lookup category/budget-line title seeded from the workbook Data sheet."""

    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    source_sheet = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "spend categories"

    def save(self, *args, **kwargs):
        if not self.normalized_name:
            self.normalized_name = normalize_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class BusinessLine(TimestampedModel):
    """Business segment (e.g. Retail, Junior, Business) — admin-managed dropdown values."""

    name = models.CharField(max_length=120)
    normalized_name = models.CharField(max_length=120, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "business line"
        verbose_name_plural = "business lines"

    def save(self, *args, **kwargs):
        if not self.normalized_name:
            self.normalized_name = normalize_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class InsuranceRateOption(TimestampedModel):
    """Withholding rate applied to vendor action cost (e.g. 16.67% or 7.78%)."""

    label = models.CharField(max_length=80, blank=True)
    percent = models.DecimalField(max_digits=6, decimal_places=2, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["percent"]

    def __str__(self) -> str:
        if self.label:
            return f"{self.label} ({self.percent}%)"
        return f"{self.percent}%"


class SubTeam(TimestampedModel):
    """Sub-team label seeded from the workbook Data sheet."""

    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, unique=True, db_index=True)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name="sub_teams")
    is_active = models.BooleanField(default=True)
    source_sheet = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "sub team"
        verbose_name_plural = "sub teams"

    def save(self, *args, **kwargs):
        if not self.normalized_name:
            self.normalized_name = normalize_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Requester(TimestampedModel):
    """Requester name seeded from the workbook Data sheet."""

    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    source_sheet = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]

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
        constraints = [
            # One budget line per workbook source row + month. Each Budget sheet row expands into
            # one line per month, so this is the stable idempotency key. Manual lines (no source
            # row number) are exempt so they never collide.
            models.UniqueConstraint(
                fields=["source_sheet", "source_row_number", "year", "month"],
                condition=Q(source_row_number__isnull=False),
                name="unique_budget_line_source_row_month",
            ),
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
    business_section = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
        help_text="Business segment from Excel Business Section (e.g. Retail, Junior, Business).",
    )
    cost_bucket = models.CharField(max_length=20, choices=CostBucket.choices, default=CostBucket.TEAM)
    description = models.TextField(blank=True)
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=24, decimal_places=2)
    action_cost_amount = models.DecimalField(
        max_digits=24,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Base marketing action cost before VAT (X in voice notes).",
    )
    tax_amount = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    insurance_rate_percent = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    insurance_amount = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    paid_amount = models.DecimalField(
        max_digits=24,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount finance pays after insurance withholding.",
    )
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
        constraints = [
            # Imported rows: stable idempotency key (source row + vendor + invoice number).
            models.UniqueConstraint(
                fields=["source_sheet", "source_row_number", "vendor", "invoice_number"],
                condition=Q(source_row_number__isnull=False),
                name="unique_invoice_source_row_vendor_number",
            ),
            # Manual/UI-created rows: one invoice number per vendor when no source row is set.
            models.UniqueConstraint(
                fields=["invoice_number", "vendor"],
                condition=Q(source_row_number__isnull=True),
                name="unique_manual_invoice_number_vendor",
            ),
        ]

    @property
    def days_in_current_stage(self) -> int:
        if self.payment_stage == PaymentStage.PAID:
            return 0
        changed_at = self.stage_changed_at or self.created_at
        if not changed_at:
            return 0
        return max((timezone.now().date() - changed_at.date()).days, 0)

    @property
    def show_days_in_current_stage(self) -> bool:
        return self.payment_stage != PaymentStage.PAID

    @property
    def invoice_year(self) -> int:
        return self.invoice_date.year

    @property
    def invoice_month(self) -> int:
        return self.invoice_date.month

    @property
    def jalali_year(self) -> int:
        from marketing.jalali import jalali_year_of

        return jalali_year_of(self.invoice_date)

    @property
    def jalali_month(self) -> int:
        from marketing.jalali import jalali_month_of

        return jalali_month_of(self.invoice_date)

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
    can_import_excel = models.BooleanField(default=False)
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


class Contract(TimestampedModel):
    """A vendor contract owned by a marketing team, tracked through legal review to signed/active."""

    title = models.CharField(max_length=255)
    contract_number = models.CharField(max_length=120, blank=True, db_index=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="contracts")
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL, related_name="contracts")
    stage = models.CharField(max_length=32, choices=ContractStage.choices, default=ContractStage.DRAFT)
    stage_changed_at = models.DateTimeField(default=timezone.now)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    signed_at = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=24, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=16, default=settings.DEFAULT_CURRENCY)
    counterparty_contact = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_contracts",
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_contracts",
    )

    class Meta:
        ordering = ["end_date", "vendor__name"]
        indexes = [
            models.Index(fields=["stage"]),
            models.Index(fields=["team", "stage"]),
            models.Index(fields=["vendor", "stage"]),
            models.Index(fields=["end_date"]),
        ]

    @property
    def days_in_current_stage(self) -> int:
        changed_at = self.stage_changed_at or self.created_at
        if not changed_at:
            return 0
        return max((timezone.now().date() - changed_at.date()).days, 0)

    @property
    def days_until_expiry(self) -> int | None:
        if not self.end_date:
            return None
        return (self.end_date - timezone.now().date()).days

    @property
    def is_expired(self) -> bool:
        days = self.days_until_expiry
        return days is not None and days < 0

    @property
    def is_expiring_soon(self) -> bool:
        """True when the contract expires within 30 days (and is not already expired)."""
        days = self.days_until_expiry
        return days is not None and 0 <= days <= 30

    @property
    def is_closed(self) -> bool:
        return self.stage in CONTRACT_CLOSED_STAGES

    def set_stage(self, new_stage: str, *, changed_by=None, note: str = "") -> None:
        self.stage = new_stage
        self.updated_by = changed_by
        self._stage_change_note = note
        self.save()

    def save(self, *args, **kwargs):
        old_stage = None
        if self.pk:
            old_stage = Contract.objects.filter(pk=self.pk).values_list("stage", flat=True).first()

        stage_changed = old_stage is not None and old_stage != self.stage
        if stage_changed or not self.stage_changed_at:
            self.stage_changed_at = timezone.now()
        if self.stage == ContractStage.SIGNED and self.signed_at is None:
            self.signed_at = timezone.now().date()

        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            update_fields = set(update_fields)
            if stage_changed:
                update_fields.add("stage_changed_at")
            if self.stage == ContractStage.SIGNED:
                update_fields.add("signed_at")
            kwargs["update_fields"] = update_fields

        super().save(*args, **kwargs)

        if stage_changed:
            ContractStatusHistory.objects.create(
                contract=self,
                old_stage=old_stage,
                new_stage=self.stage,
                changed_by=self.updated_by,
                note=getattr(self, "_stage_change_note", ""),
            )

    def __str__(self) -> str:
        return f"{self.title} - {self.vendor}"


class ContractAttachment(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="attachments")
    attachment_type = models.CharField(max_length=24, choices=ContractAttachmentType.choices)
    file = models.FileField(upload_to=contract_attachment_path)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="contract_attachments")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["contract", "attachment_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.contract} {self.attachment_type}"


class ContractStatusHistory(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="status_history")
    old_stage = models.CharField(max_length=32, choices=ContractStage.choices, blank=True)
    new_stage = models.CharField(max_length=32, choices=ContractStage.choices)
    changed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["contract", "-changed_at"]),
            models.Index(fields=["new_stage", "-changed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.contract}: {self.old_stage} -> {self.new_stage}"
