from __future__ import annotations

from pathlib import Path

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from .models import (
    AttachmentType,
    Campaign,
    CostBucket,
    Invoice,
    InvoiceAttachment,
    PaymentStage,
    Role,
    Team,
    UserTeamAccess,
    Vendor,
    normalize_name,
)
from .permissions import (
    can_create_invoice_for_team,
    can_upload_invoice_file,
    can_upload_payment_proof,
    filter_campaigns_for_user,
    filter_teams_for_user,
    get_user_scope,
    user_has_admin_access,
)

User = get_user_model()


class DateInput(forms.DateInput):
    input_type = "date"


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
    new_vendor_name = forms.CharField(label="وندور جدید", required=False, max_length=255)

    class Meta:
        model = Invoice
        fields = [
            "invoice_number",
            "vendor",
            "new_vendor_name",
            "team",
            "campaign",
            "category",
            "cost_bucket",
            "description",
            "invoice_date",
            "due_date",
            "amount",
            "currency",
            "payment_stage",
        ]
        widgets = {
            "invoice_date": DateInput(format="%Y-%m-%d"),
            "due_date": DateInput(format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "invoice_number": "شماره فاکتور",
            "vendor": "وندور",
            "team": "تیم",
            "campaign": "کمپین",
            "category": "دسته‌بندی / ردیف بودجه",
            "cost_bucket": "نوع هزینه",
            "description": "توضیحات",
            "invoice_date": "تاریخ فاکتور",
            "due_date": "سررسید",
            "amount": "مبلغ",
            "currency": "واحد پول",
            "payment_stage": "مرحله پرداخت",
        }

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["vendor"].queryset = Vendor.objects.order_by("name")
        self.fields["vendor"].required = False
        self.fields["team"].queryset = filter_teams_for_user(Team.objects.filter(is_active=True), user)
        self.fields["team"].required = False
        self.fields["campaign"].queryset = filter_campaigns_for_user(Campaign.objects.select_related("team"), user)
        self.fields["campaign"].required = False
        self.fields["invoice_date"].input_formats = ["%Y-%m-%d"]
        self.fields["due_date"].input_formats = ["%Y-%m-%d"]
        self._style_fields()

    def clean(self):
        cleaned = super().clean()
        vendor = cleaned.get("vendor")
        new_vendor_name = (cleaned.get("new_vendor_name") or "").strip()
        team = cleaned.get("team")
        cost_bucket = cleaned.get("cost_bucket") or CostBucket.TEAM

        if not vendor and not new_vendor_name:
            raise ValidationError("یک وندور انتخاب کنید یا نام وندور جدید را وارد کنید.")
        if cost_bucket == CostBucket.TEAM and team is None:
            raise ValidationError("برای هزینه تیمی، انتخاب تیم الزامی است.")
        if not can_create_invoice_for_team(self.user, team, cost_bucket):
            raise ValidationError("شما اجازه ثبت یا ویرایش فاکتور برای این تیم/نوع هزینه را ندارید.")
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
    payment_stage = forms.ChoiceField(label="مرحله پرداخت", choices=PaymentStage.choices)
    note = forms.CharField(label="یادداشت", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, invoice: Invoice, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["payment_stage"].initial = invoice.payment_stage
        self._style_fields()


class InvoiceAttachmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = InvoiceAttachment
        fields = ["attachment_type", "file", "notes"]
        labels = {
            "attachment_type": "نوع فایل",
            "file": "فایل",
            "notes": "یادداشت",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user, invoice: Invoice, **kwargs):
        self.user = user
        self.invoice = invoice
        super().__init__(*args, **kwargs)
        choices = []
        if can_upload_invoice_file(user, invoice):
            choices.extend([
                (AttachmentType.INVOICE_IMAGE, "تصویر / فایل فاکتور"),
                (AttachmentType.OTHER, "سایر مدارک"),
            ])
        if can_upload_payment_proof(user, invoice):
            choices.append((AttachmentType.PAYMENT_PROOF, "فیش / رسید پرداخت"))
        self.fields["attachment_type"].choices = choices
        self._style_fields()

    @property
    def has_allowed_types(self) -> bool:
        return bool(self.fields["attachment_type"].choices)

    def clean_attachment_type(self):
        attachment_type = self.cleaned_data["attachment_type"]
        if attachment_type == AttachmentType.PAYMENT_PROOF and not can_upload_payment_proof(self.user, self.invoice):
            raise ValidationError("اجازه آپلود فیش پرداخت ندارید.")
        if attachment_type in {AttachmentType.INVOICE_IMAGE, AttachmentType.OTHER} and not can_upload_invoice_file(
            self.user,
            self.invoice,
        ):
            raise ValidationError("اجازه آپلود فایل فاکتور ندارید.")
        return attachment_type


class ExcelImportUploadForm(StyledFormMixin, forms.Form):
    workbook = forms.FileField(label="فایل اکسل")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_workbook(self):
        workbook = self.cleaned_data["workbook"]
        suffix = Path(workbook.name).suffix.lower()
        if suffix != ".xlsx":
            raise ValidationError("فقط فایل xlsx قابل قبول است.")
        return workbook


class UserAccessCreateForm(StyledFormMixin, forms.Form):
    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        (Role.MANAGER, "Manager"),
        (Role.EDITOR, "Editor"),
        (Role.OBSERVER, "Observer"),
    ]

    username = forms.CharField(label="نام کاربری", max_length=150)
    password = forms.CharField(label="رمز عبور", widget=forms.PasswordInput)
    first_name = forms.CharField(label="نام", required=False, max_length=150)
    last_name = forms.CharField(label="نام خانوادگی", required=False, max_length=150)
    email = forms.EmailField(label="ایمیل", required=False)
    role = forms.ChoiceField(label="سطح دسترسی", choices=ROLE_CHOICES)
    team = forms.ModelChoiceField(label="تیم", queryset=Team.objects.none(), required=False)
    is_global = forms.BooleanField(label="دسترسی همه تیم‌ها", required=False)
    can_view_referral_sms = forms.BooleanField(label="مشاهده ریفرال و SMS", required=False)
    can_export = forms.BooleanField(label="خروجی اکسل/گزارش", required=False)
    can_upload_invoice_files = forms.BooleanField(label="آپلود فایل فاکتور", required=False)
    can_upload_payment_proofs = forms.BooleanField(label="آپلود فیش پرداخت", required=False)

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["team"].queryset = Team.objects.filter(is_active=True).order_by("name")
        self._style_fields()

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise ValidationError("این نام کاربری قبلا ثبت شده است.")
        return username

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        team = cleaned.get("team")
        is_global = cleaned.get("is_global")
        if role != "ADMIN" and not is_global and team is None:
            raise ValidationError("برای کاربر غیر ادمین، تیم را انتخاب کنید یا دسترسی همه تیم‌ها را فعال کنید.")
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


def user_can_create_invoice(user) -> bool:
    scope = get_user_scope(user)
    return scope.is_admin or Role.EDITOR in scope.roles
