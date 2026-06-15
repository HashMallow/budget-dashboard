from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from .cost_buckets import exclude_pseudo_teams
from .jalali import format_jalali_date, normalize_digits, parse_jalali_date_text
from .models import (
    AttachmentType,
    Campaign,
    Contract,
    ContractAttachment,
    ContractStage,
    CostBucket,
    Invoice,
    InvoiceAttachment,
    PaymentStage,
    Requester,
    Role,
    SpendCategory,
    SubTeam,
    Team,
    UserTeamAccess,
    Vendor,
    normalize_name,
)
from .permissions import (
    can_create_contract_for_team,
    can_create_invoice_for_team,
    can_upload_invoice_file,
    can_upload_payment_proof,
    filter_campaigns_for_user,
    filter_teams_for_user,
    get_user_scope,
    user_has_admin_access,
)
from .translations import translate

User = get_user_model()


def apply_ui_language(form: forms.BaseForm, ui_lang: str) -> None:
    """Translate labels and static choice text for the active UI language."""
    if ui_lang == "en":
        return
    for field in form.fields.values():
        if field.label:
            field.label = translate(field.label, ui_lang)
        if isinstance(field, forms.ModelChoiceField):
            if field.empty_label:
                field.empty_label = translate(field.empty_label, ui_lang)
            continue
        choices = getattr(field, "choices", None)
        if choices:
            field.choices = [(value, translate(str(label), ui_lang)) for value, label in choices]


class DateInput(forms.DateInput):
    input_type = "date"


class FlexibleDateField(forms.DateField):
    """Accept Gregorian ISO dates and Jalali/Shamsi dates in invoice forms."""

    default_error_messages = {
        "invalid": "Enter a valid date. Use 1405/01/10 or 2026-03-30.",
    }

    def __init__(self, *args, display_jalali: bool = False, **kwargs):
        kwargs.setdefault(
            "widget",
            forms.TextInput(attrs={"dir": "ltr", "inputmode": "numeric", "placeholder": "1405/01/10"}),
        )
        self.display_jalali = display_jalali
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            return format_jalali_date(value) if self.display_jalali else value.isoformat()
        return value

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        text = normalize_digits(value)
        jalali_value = parse_jalali_date_text(text)
        if jalali_value:
            return jalali_value

        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            pass

        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                pass
        raise ValidationError(self.error_messages["invalid"], code="invalid")


def apply_form_control(field: forms.Field) -> None:
    widget = field.widget
    if isinstance(widget, forms.CheckboxInput):
        widget.attrs["class"] = "form-check-input"
        return
    current = widget.attrs.get("class", "")
    widget.attrs["class"] = f"{current} form-control".strip()


class StyledFormMixin:
    def _style_fields(self) -> None:
        for field in self.fields.values():
            apply_form_control(field)


class InvoiceForm(StyledFormMixin, forms.ModelForm):
    CURRENCY_CHOICES = [
        ("IRR", "Iranian Rial (IRR)"),
    ]

    new_vendor_name = forms.CharField(label="New vendor", required=False, max_length=255)
    invoice_date = FlexibleDateField(label="Invoice date", required=True)
    due_date = FlexibleDateField(label="Due date", required=False)
    currency = forms.ChoiceField(
        label="Currency",
        choices=CURRENCY_CHOICES,
        initial=settings.DEFAULT_CURRENCY,
    )

    class Meta:
        model = Invoice
        fields = [
            "invoice_number",
            "vendor",
            "new_vendor_name",
            "team",
            "campaign",
            "category",
            "business_section",
            "cost_bucket",
            "description",
            "invoice_date",
            "due_date",
            "amount",
            "currency",
            "payment_stage",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "amount": forms.TextInput(
                attrs={
                    "inputmode": "decimal",
                    "autocomplete": "off",
                    "placeholder": "100000000",
                }
            ),
        }
        labels = {
            "invoice_number": "Invoice number",
            "vendor": "Vendor",
            "team": "Team",
            "campaign": "Campaign",
            "category": "Category / budget line",
            "business_section": "Business line",
            "cost_bucket": "Cost type",
            "description": "Description",
            "invoice_date": "Invoice date",
            "due_date": "Due date",
            "amount": "Amount (Rial)",
            "currency": "Currency",
            "payment_stage": "Payment stage",
        }

    def __init__(self, *args, user, ui_lang: str = "en", **kwargs):
        self.user = user
        self.ui_lang = ui_lang
        super().__init__(*args, **kwargs)
        self.fields["vendor"].queryset = Vendor.objects.order_by("name")
        self.fields["vendor"].required = False
        self.fields["team"].queryset = filter_teams_for_user(Team.objects.filter(is_active=True), user)
        self.fields["team"].required = False
        self.fields["campaign"].queryset = filter_campaigns_for_user(Campaign.objects.select_related("team"), user)
        self.fields["campaign"].required = False
        if not self.instance.pk and not self.initial.get("currency"):
            self.fields["currency"].initial = settings.DEFAULT_CURRENCY
        if ui_lang == "fa":
            self.fields["amount"].widget.attrs["placeholder"] = "۱۰۰۰۰۰۰۰۰"
            self.fields["amount"].widget.attrs["dir"] = "ltr"
        display_jalali = ui_lang == "fa"
        self.fields["invoice_date"].display_jalali = display_jalali
        self.fields["due_date"].display_jalali = display_jalali
        self._style_fields()
        apply_ui_language(self, ui_lang)

    def clean_team(self):
        team = self.cleaned_data.get("team")
        if team is None:
            return team
        if not filter_teams_for_user(Team.objects.filter(pk=team.pk), self.user).exists():
            raise ValidationError("You are not allowed to use this team.")
        return team

    def clean(self):
        cleaned = super().clean()
        vendor = cleaned.get("vendor")
        new_vendor_name = (cleaned.get("new_vendor_name") or "").strip()
        team = cleaned.get("team")
        cost_bucket = cleaned.get("cost_bucket") or CostBucket.TEAM

        if not vendor and not new_vendor_name:
            raise ValidationError("Select a vendor or enter a new vendor name.")
        if cost_bucket == CostBucket.TEAM and team is None:
            raise ValidationError("A team is required for team cost.")
        if not can_create_invoice_for_team(self.user, team, cost_bucket):
            raise ValidationError("You are not allowed to add or edit invoices for this team/cost type.")
        return cleaned

    def save(self, commit=True):
        invoice = super().save(commit=False)
        new_vendor_name = (self.cleaned_data.get("new_vendor_name") or "").strip()
        if new_vendor_name:
            normalized = normalize_name(new_vendor_name)
            vendor, _created = Vendor.objects.get_or_create(
                normalized_name=normalized,
                defaults={"name": new_vendor_name},
            )
            invoice.vendor = vendor
        if invoice.pk is None:
            invoice.created_by = self.user
        invoice.updated_by = self.user
        if commit:
            invoice.save()
            self.save_m2m()
        return invoice


class InvoiceStatusForm(StyledFormMixin, forms.Form):
    payment_stage = forms.ChoiceField(label="Payment stage", choices=PaymentStage.choices)
    note = forms.CharField(label="Note", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, invoice: Invoice, ui_lang: str = "en", **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["payment_stage"].initial = invoice.payment_stage
        self._style_fields()
        apply_ui_language(self, ui_lang)


class InvoiceAttachmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = InvoiceAttachment
        fields = ["attachment_type", "file", "notes"]
        labels = {
            "attachment_type": "File type",
            "file": "File",
            "notes": "Note",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user, invoice: Invoice, ui_lang: str = "en", **kwargs):
        self.user = user
        self.invoice = invoice
        super().__init__(*args, **kwargs)
        choices = []
        if can_upload_invoice_file(user, invoice):
            choices.extend(
                [
                    (AttachmentType.INVOICE_IMAGE, "Invoice image / file"),
                    (AttachmentType.OTHER, "Other documents"),
                ]
            )
        if can_upload_payment_proof(user, invoice):
            choices.append((AttachmentType.PAYMENT_PROOF, "Payment receipt / proof"))
        self.fields["attachment_type"].choices = choices
        self._style_fields()
        apply_ui_language(self, ui_lang)

    @property
    def has_allowed_types(self) -> bool:
        return bool(self.fields["attachment_type"].choices)

    def clean_attachment_type(self):
        attachment_type = self.cleaned_data["attachment_type"]
        if attachment_type == AttachmentType.PAYMENT_PROOF and not can_upload_payment_proof(self.user, self.invoice):
            raise ValidationError("You are not allowed to upload payment receipts.")
        if attachment_type in {AttachmentType.INVOICE_IMAGE, AttachmentType.OTHER} and not can_upload_invoice_file(
            self.user,
            self.invoice,
        ):
            raise ValidationError("You are not allowed to upload invoice files.")
        return attachment_type


class ContractForm(StyledFormMixin, forms.ModelForm):
    new_vendor_name = forms.CharField(label="New vendor", required=False, max_length=255)
    start_date = FlexibleDateField(label="Start date", required=False)
    end_date = FlexibleDateField(label="End date", required=False)

    class Meta:
        model = Contract
        fields = [
            "title",
            "contract_number",
            "vendor",
            "new_vendor_name",
            "team",
            "stage",
            "start_date",
            "end_date",
            "amount",
            "currency",
            "counterparty_contact",
            "description",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "title": "Contract title",
            "contract_number": "Contract number",
            "vendor": "Vendor",
            "team": "Team",
            "stage": "Stage",
            "amount": "Contract value",
            "currency": "Currency",
            "counterparty_contact": "Counterparty contact",
            "description": "Description",
        }

    def __init__(self, *args, user, ui_lang: str = "en", **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["vendor"].queryset = Vendor.objects.order_by("name")
        self.fields["vendor"].required = False
        self.fields["team"].queryset = filter_teams_for_user(Team.objects.filter(is_active=True), user)
        self.fields["team"].required = False
        self.fields["amount"].required = False
        display_jalali = ui_lang == "fa"
        self.fields["start_date"].display_jalali = display_jalali
        self.fields["end_date"].display_jalali = display_jalali
        self._style_fields()
        apply_ui_language(self, ui_lang)

    def clean(self):
        cleaned = super().clean()
        vendor = cleaned.get("vendor")
        new_vendor_name = (cleaned.get("new_vendor_name") or "").strip()
        team = cleaned.get("team")
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")

        if not vendor and not new_vendor_name:
            raise ValidationError("Select a vendor or enter a new vendor name.")
        if start_date and end_date and end_date < start_date:
            raise ValidationError("End date cannot be before the start date.")
        if not can_create_contract_for_team(self.user, team):
            raise ValidationError("You are not allowed to add or edit contracts for this team.")
        return cleaned

    def save(self, commit=True):
        contract = super().save(commit=False)
        new_vendor_name = (self.cleaned_data.get("new_vendor_name") or "").strip()
        if new_vendor_name:
            normalized = normalize_name(new_vendor_name)
            vendor, _created = Vendor.objects.get_or_create(
                normalized_name=normalized,
                defaults={"name": new_vendor_name},
            )
            contract.vendor = vendor
        if contract.pk is None:
            contract.created_by = self.user
        contract.updated_by = self.user
        if commit:
            contract.save()
            self.save_m2m()
        return contract


class ContractStageForm(StyledFormMixin, forms.Form):
    stage = forms.ChoiceField(label="Stage", choices=ContractStage.choices)
    note = forms.CharField(label="Note", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, contract: Contract, ui_lang: str = "en", **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["stage"].initial = contract.stage
        self._style_fields()
        apply_ui_language(self, ui_lang)


class ContractAttachmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ContractAttachment
        fields = ["attachment_type", "file", "notes"]
        labels = {
            "attachment_type": "Document type",
            "file": "File",
            "notes": "Note",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, ui_lang: str = "en", **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
        apply_ui_language(self, ui_lang)


class ExcelImportUploadForm(StyledFormMixin, forms.Form):
    workbook = forms.FileField(label="Excel file")

    def __init__(self, *args, ui_lang: str = "en", **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
        apply_ui_language(self, ui_lang)

    def clean_workbook(self):
        workbook = self.cleaned_data["workbook"]
        suffix = Path(workbook.name).suffix.lower()
        if suffix != ".xlsx":
            raise ValidationError("Only .xlsx files are accepted.")
        return workbook


class UserAccessCreateForm(StyledFormMixin, forms.Form):
    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        (Role.MANAGER, "Manager"),
        (Role.EDITOR, "Editor"),
        (Role.OBSERVER, "Observer"),
    ]

    username = forms.CharField(label="Username", max_length=150)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    first_name = forms.CharField(label="First name", required=False, max_length=150)
    last_name = forms.CharField(label="Last name", required=False, max_length=150)
    email = forms.EmailField(label="Email", required=False)
    role = forms.ChoiceField(label="Access level", choices=ROLE_CHOICES)
    team = forms.ModelChoiceField(label="Team", queryset=Team.objects.none(), required=False)
    is_global = forms.BooleanField(label="All-team access", required=False)
    can_view_referral_sms = forms.BooleanField(label="View referral and SMS", required=False)
    can_export = forms.BooleanField(label="Export Excel/reports", required=False)
    can_upload_invoice_files = forms.BooleanField(label="Upload invoice files", required=False)
    can_upload_payment_proofs = forms.BooleanField(label="Upload payment receipts", required=False)

    def __init__(self, *args, user, ui_lang: str = "en", **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["team"].queryset = Team.objects.filter(is_active=True).order_by("name")
        if user_has_admin_access(user):
            self.fields["team"].queryset = exclude_pseudo_teams(self.fields["team"].queryset)
        self._style_fields()
        apply_ui_language(self, ui_lang)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        team = cleaned.get("team")
        is_global = cleaned.get("is_global")
        if role != "ADMIN" and not is_global and team is None:
            raise ValidationError("For a non-admin user, select a team or enable all-team access.")
        return cleaned

    def save(self):
        if not user_has_admin_access(self.user):
            raise PermissionError("Only admins can create users.")

        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["username"],
            password=data["password"],
            email=data.get("email", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
        )

        role = data["role"]
        group, _created = Group.objects.get_or_create(name="Admin" if role == "ADMIN" else role.title())
        user.groups.add(group)

        if role == "ADMIN":
            user.is_staff = True
            user.save(update_fields=["is_staff"])
            return user

        access = UserTeamAccess(
            user=user,
            team=None if data.get("is_global") else data.get("team"),
            role=role,
            is_global=bool(data.get("is_global")),
            can_view_referral_sms=bool(data.get("can_view_referral_sms")),
            can_export=bool(data.get("can_export")),
            can_upload_invoice_files=bool(data.get("can_upload_invoice_files")),
            can_upload_payment_proofs=bool(data.get("can_upload_payment_proofs")),
        )
        access.full_clean()
        access.save()
        return user


class TeamAccessForm(StyledFormMixin, forms.ModelForm):
    """Grant or update a single team-level access rule for an existing user.

    Admins can attach several of these rows to one user, which is how multi-team access is built up
    after the initial account is created.
    """

    class Meta:
        model = UserTeamAccess
        fields = [
            "user",
            "role",
            "team",
            "is_global",
            "can_view_referral_sms",
            "can_export",
            "can_upload_invoice_files",
            "can_upload_payment_proofs",
        ]
        labels = {
            "user": "User",
            "role": "Access level",
            "team": "Team",
            "is_global": "All-team access",
            "can_view_referral_sms": "View referral and SMS",
            "can_export": "Export Excel/reports",
            "can_upload_invoice_files": "Upload invoice files",
            "can_upload_payment_proofs": "Upload payment receipts",
        }

    def __init__(self, *args, admin_user, ui_lang: str = "en", **kwargs):
        self.admin_user = admin_user
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.order_by("username")
        self.fields["team"].queryset = exclude_pseudo_teams(Team.objects.filter(is_active=True)).order_by("name")
        self.fields["team"].required = False
        self._style_fields()
        apply_ui_language(self, ui_lang)

    def clean(self):
        cleaned = super().clean()
        is_global = cleaned.get("is_global")
        team = cleaned.get("team")
        if is_global:
            cleaned["team"] = None
        elif team is None:
            raise ValidationError("Select a team or enable all-team access.")
        return cleaned

    def save(self, commit=True):
        if not user_has_admin_access(self.admin_user):
            raise PermissionError("Only admins can manage access rules.")
        access = super().save(commit=False)
        access.is_active = True
        if commit:
            access.save()
        return access


class VendorReferenceForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "tax_id", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise ValidationError("Enter a vendor name.")
        normalized = normalize_name(name)
        queryset = Vendor.objects.filter(normalized_name=normalized)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("A vendor with this name already exists.")
        return name


class SpendCategoryForm(forms.ModelForm):
    class Meta:
        model = SpendCategory
        fields = ["name", "is_active"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise ValidationError("Enter a category name.")
        normalized = normalize_name(name)
        queryset = SpendCategory.objects.filter(normalized_name=normalized)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("A category with this name already exists.")
        return name


class SubTeamForm(forms.ModelForm):
    class Meta:
        model = SubTeam
        fields = ["name", "team", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["team"].queryset = exclude_pseudo_teams(Team.objects.filter(is_active=True).order_by("name"))
        self.fields["team"].required = False
        self.fields["team"].empty_label = "—"

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise ValidationError("Enter a sub-team name.")
        normalized = normalize_name(name)
        queryset = SubTeam.objects.filter(normalized_name=normalized)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("A sub-team with this name already exists.")
        return name


class CampaignReferenceForm(StyledFormMixin, forms.ModelForm):
    STATUS_CHOICES = [
        ("PLANNED", "Planned"),
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    class Meta:
        model = Campaign
        fields = [
            "name",
            "year",
            "team",
            "planned_start_date",
            "planned_end_date",
            "status",
            "notes",
        ]
        labels = {
            "name": "Campaign name",
            "year": "Year",
            "team": "Team",
            "planned_start_date": "Planned start",
            "planned_end_date": "Planned end",
            "status": "Status",
            "notes": "Notes",
        }
        widgets = {
            "planned_start_date": DateInput(),
            "planned_end_date": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["team"].queryset = exclude_pseudo_teams(Team.objects.filter(is_active=True).order_by("name"))
        self.fields["team"].required = False
        self.fields["team"].empty_label = "—"
        self.fields["status"] = forms.ChoiceField(
            choices=self.STATUS_CHOICES,
            initial=self.instance.status if self.instance.pk else "PLANNED",
        )
        if not self.instance.pk and "year" not in self.data:
            from django.utils import timezone

            from .jalali import gregorian_to_jalali

            today = timezone.now().date()
            self.fields["year"].initial = gregorian_to_jalali(today.year, today.month, today.day)[0]
        self._style_fields()

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise ValidationError("Enter a campaign name.")
        return name

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get("name")
        year = cleaned.get("year")
        team = cleaned.get("team")
        if name and year is not None:
            queryset = Campaign.objects.filter(name=name, year=year, team=team)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise ValidationError("A campaign with this name, year and team already exists.")
        return cleaned


class RequesterForm(forms.ModelForm):
    class Meta:
        model = Requester
        fields = ["name", "is_active"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise ValidationError("Enter a requester name.")
        normalized = normalize_name(name)
        queryset = Requester.objects.filter(normalized_name=normalized)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("A requester with this name already exists.")
        return name


def user_can_create_invoice(user) -> bool:
    scope = get_user_scope(user)
    return scope.is_admin or Role.EDITOR in scope.roles
