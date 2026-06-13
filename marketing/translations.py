"""Lightweight English -> Persian UI translation catalog.

We avoid Django's gettext machinery here because the build environment does not ship the
``gettext`` tooling (``msgfmt``/``xgettext``) needed to compile ``.po`` files. Instead the
English source string is the lookup key, and ``translate`` returns the Persian string when
the active language is ``fa`` (falling back to the English source if no translation exists).

To add or fix a translation, edit the ``FA`` mapping below. Keys must match the English
text used in templates/forms/messages exactly.
"""

from __future__ import annotations

# English source string -> Persian translation.
FA: dict[str, str] = {
    # --- Chrome / navigation (base.html) ---
    "Marketing Spend Panel": "پنل هزینه‌کرد مارکتینگ",
    "Marketing Spend": "هزینه‌کرد مارکتینگ",
    "Internal dashboard and invoice control": "داشبورد داخلی و کنترل فاکتورها",
    "Dashboard": "داشبورد",
    "Invoices": "فاکتورها",
    "Vendors": "وندورها",
    "Campaigns": "کمپین‌ها",
    "Budget": "بودجه",
    "Excel Import": "ورود اکسل",
    "Users": "کاربران",
    "Full admin": "ادمین کامل",
    "Panel user": "کاربر پنل",
    "Logout": "خروج",
    "Monitor spend, invoices and payment status": "مانیتورینگ هزینه، فاکتور و وضعیت پرداخت",
    # --- Dashboard ---
    "Spend Dashboard": "داشبورد هزینه‌کرد",
    "Overview of marketing spend, payments and team status": "نمای کلی هزینه مارکتینگ، پرداخت‌ها و وضعیت تیم‌ها",
    "New invoice": "ثبت فاکتور",
    "Excel": "اکسل",
    "PDF report": "گزارش PDF",
    "Year": "سال",
    "All years": "همه سال‌ها",
    "Team": "تیم",
    "All permitted teams": "همه تیم‌های مجاز",
    "Apply filter": "اعمال فیلتر",
    "Total spend": "هزینه کل",
    "Invoice count": "تعداد فاکتور",
    "In selected range": "در محدوده انتخاب‌شده",
    "Paid": "پرداخت‌شده",
    "Paid invoices": "فاکتورهای پرداخت‌شده",
    "Referral / SMS": "ریفرال / پیامک",
    "Separate from team breakdown": "جدا از شکست تیم‌ها",
    "Monthly trend": "روند ماهانه",
    "By Persian (Jalali) month": "بر اساس ماه شمسی",
    "Spend by team": "هزینه به تفکیک تیم",
    "Overall spend share": "سهم کلی هزینه",
    "Team spend with referral and SMS shown separately": "هزینه تیم‌ها به همراه ریفرال و پیامک به‌صورت جداگانه",
    "Referral and SMS are excluded from this breakdown": "ریفرال و پیامک در این شکست لحاظ نشده‌اند",
    "No data to display.": "داده‌ای برای نمایش وجود ندارد.",
    "Top vendors": "وندورهای برتر",
    "Sorted from highest to lowest spend": "مرتب‌شده از بیشترین به کمترین هزینه",
    "View all": "مشاهده کامل",
    "Vendor": "وندور",
    "Count": "تعداد",
    "Amount": "مبلغ",
    "Spend on campaigns recorded on invoices": "هزینه کمپین‌های ثبت‌شده در فاکتورها",
    "Campaign": "کمپین",
    "No campaigns recorded in this range.": "کمپینی در این محدوده ثبت نشده است.",
    "Payment status": "وضعیت پرداخت",
    "Invoice count per stage": "تعداد فاکتور در هر مرحله",
    "Stage": "مرحله",
    "Invoices in finance review": "فاکتورهای در مرحله مالی",
    "Sorted by days waiting in stage": "مرتب‌شده بر اساس روزهای مانده در مرحله",
    "Invoice": "فاکتور",
    "Days in stage": "روز در مرحله",
    "No invoices waiting in finance review.": "فاکتوری در مرحله مالی منتظر نیست.",
    # --- Invoice list ---
    "Search, filter, track payments and enter spend data": "جستجو، فیلتر، پیگیری پرداخت و ورود اطلاعات هزینه",
    "Search": "جستجو",
    "Number, vendor, category": "شماره، وندور، دسته‌بندی",
    "All": "همه",
    "Payment stage": "مرحله پرداخت",
    "Cost type": "نوع هزینه",
    "Filter": "فیلتر",
    "Number": "شماره",
    "Date": "تاریخ",
    "Days": "روز",
    "Category": "دسته‌بندی",
    "No invoices to display.": "فاکتوری برای نمایش وجود ندارد.",
    "Previous": "قبلی",
    "Next": "بعدی",
    "Page": "صفحه",
    "of": "از",
    # --- Invoice detail ---
    "List": "فهرست",
    "Edit": "ویرایش",
    "days in this stage": "روز در این مرحله",
    "Invoice date": "تاریخ فاکتور",
    "Due:": "سررسید:",
    "Details": "مشخصات",
    "Core invoice and cost information": "اطلاعات اصلی فاکتور و هزینه",
    "Description": "توضیحات",
    "Import source": "منبع ورود",
    "Payment tracking": "پیگیری پرداخت",
    "Stage changes for permitted users": "تغییر مرحله برای کاربران مجاز",
    "Save stage change": "ثبت تغییر مرحله",
    "You have view-only access to this invoice's status.": "شما فقط امکان مشاهده وضعیت این فاکتور را دارید.",
    "Files": "فایل‌ها",
    "Invoice image, payment receipt and related documents": "تصویر فاکتور، رسید پرداخت و مدارک مرتبط",
    "Type": "نوع",
    "File": "فایل",
    "Uploaded by": "آپلودکننده",
    "Time": "زمان",
    "No files uploaded.": "فایلی ثبت نشده است.",
    "Upload file": "آپلود فایل",
    "Status history": "تاریخچه وضعیت",
    "Payment stage changes are recorded automatically": "تغییرات مرحله پرداخت به‌صورت خودکار ثبت می‌شوند",
    "From": "از",
    "To": "به",
    "User": "کاربر",
    "No status changes recorded.": "تغییر وضعیتی ثبت نشده است.",
    # --- Invoice form ---
    "Edit invoice": "ویرایش فاکتور",
    "The invoice is saved to the database": "اطلاعات فاکتور در دیتابیس ثبت می‌شود",
    "Back": "بازگشت",
    "Save": "ذخیره",
    "Cancel": "انصراف",
    # --- Form labels ---
    "Invoice number": "شماره فاکتور",
    "New vendor": "وندور جدید",
    "Category / budget line": "دسته‌بندی / ردیف بودجه",
    "Due date": "سررسید",
    "Currency": "واحد پول",
    "Note": "یادداشت",
    "File type": "نوع فایل",
    "Excel file": "فایل اکسل",
    "Username": "نام کاربری",
    "Password": "رمز عبور",
    "First name": "نام",
    "Last name": "نام خانوادگی",
    "Email": "ایمیل",
    "Access level": "سطح دسترسی",
    "All-team access": "دسترسی به همه تیم‌ها",
    "View referral and SMS": "مشاهده ریفرال و پیامک",
    "Export Excel/reports": "خروجی اکسل/گزارش",
    "Upload invoice files": "آپلود فایل فاکتور",
    "Upload payment receipts": "آپلود رسید پرداخت",
    # --- Attachment types ---
    "Invoice image": "تصویر فاکتور",
    "Payment proof": "رسید پرداخت",
    "Other": "سایر",
    "Invoice image / file": "تصویر / فایل فاکتور",
    "Other documents": "سایر مدارک",
    "Payment receipt / proof": "رسید پرداخت",
    # --- Form / auth validation messages ---
    "Select a vendor or enter a new vendor name.": "یک وندور انتخاب کنید یا نام وندور جدید وارد کنید.",
    "A team is required for team cost.": "برای هزینه تیمی، انتخاب تیم الزامی است.",
    "You are not allowed to add or edit invoices for this team/cost type.": (
        "اجازه ثبت یا ویرایش فاکتور برای این تیم/نوع هزینه را ندارید."
    ),
    "You are not allowed to upload payment receipts.": "اجازه آپلود رسید پرداخت را ندارید.",
    "You are not allowed to upload invoice files.": "اجازه آپلود فایل فاکتور را ندارید.",
    "Only .xlsx files are accepted.": "فقط فایل‌های .xlsx پذیرفته می‌شوند.",
    "This username is already taken.": "این نام کاربری قبلاً استفاده شده است.",
    "For a non-admin user, select a team or enable all-team access.": (
        "برای کاربر غیرادمین، یک تیم انتخاب کنید یا دسترسی همه تیم‌ها را فعال کنید."
    ),
    "This field is required.": "پر کردن این فیلد الزامی است.",
    "Please enter a correct username and password. Note that both fields may be case-sensitive.": (
        "نام کاربری یا رمز عبور اشتباه است. هر دو فیلد به حروف بزرگ و کوچک حساس هستند."
    ),
    # --- Vendor report ---
    "Vendor report": "گزارش وندورها",
    "Amount, invoice count, payment stage and invoice numbers per vendor": (
        "مبلغ، تعداد فاکتور، مرحله پرداخت و شماره فاکتورهای هر وندور"
    ),
    "Vendor or invoice number": "وندور یا شماره فاکتور",
    "Invoice numbers": "شماره فاکتورها",
    "Stages": "مرحله‌ها",
    "No vendors in this range.": "وندوری در این محدوده وجود ندارد.",
    # --- Campaign report ---
    "Campaign report": "گزارش کمپین‌ها",
    "Campaign spend across the year and by month": "هزینه کمپین‌ها در طول سال و به تفکیک ماه",
    "Campaign name, vendor or invoice": "نام کمپین، وندور یا فاکتور",
    "Campaign table": "جدول کمپین‌ها",
    "From highest to lowest spend": "از بیشترین به کمترین هزینه",
    "Spend chart": "نمودار هزینه",
    "Current view by total campaign spend": "نمای فعلی بر اساس جمع کل کمپین",
    "Campaigns by month": "کمپین‌ها به تفکیک ماه",
    "Horizontal table to review the yearly trend": "جدول افقی برای بررسی روند سالانه",
    "No campaigns in this range.": "کمپینی در این محدوده وجود ندارد.",
    # --- Budget ---
    "Budget lines imported from the Budget sheet": "ردیف‌های بودجه واردشده از شیت Budget",
    "Team or category": "تیم یا دسته‌بندی",
    "Spreadsheet-style budget view": "نمای اکسل‌مانند بودجه",
    "Each row is a team/category, each column is a month": "هر ردیف تیم/دسته‌بندی و هر ستون یک ماه است",
    "Total": "جمع",
    "No budget to display.": "بودجه‌ای برای نمایش وجود ندارد.",
    "Database rows": "ردیف‌های دیتابیس",
    "Normalized structure for import, reporting and analysis": "ساختار نرمال‌شده برای ورود، گزارش و تحلیل",
    "Month": "ماه",
    "No rows to display.": "ردیفی برای نمایش وجود ندارد.",
    # --- Excel import ---
    "Excel import": "ورود اکسل",
    "Upload an xlsx file, review the dry-run, then commit to the database": (
        "آپلود فایل xlsx، بررسی اولیه، سپس ثبت در دیتابیس"
    ),
    "First a dry-run only; nothing in the database changes": "ابتدا فقط بررسی می‌شود و چیزی در دیتابیس تغییر نمی‌کند",
    "Check file": "بررسی فایل",
    "Confirm and import to database": "تایید و ورود به دیتابیس",
    "Last check result": "نتیجه آخرین بررسی",
    "created / updated / skipped": "جدید / به‌روزرسانی / ردشده",
    "Section": "بخش",
    "Created": "جدید",
    "Updated": "به‌روزرسانی",
    "Skipped": "ردشده",
    "No file checked yet.": "هنوز فایلی بررسی نشده است.",
    "Skipped rows": "ردیف‌های ردشده",
    "First 20 for a quick review": "۲۰ مورد اول برای بررسی سریع",
    "Sheet": "شیت",
    "Row": "ردیف",
    "Reason": "دلیل",
    # --- Users / access ---
    "Users and access": "کاربران و دسترسی‌ها",
    "Create users, roles, permitted teams, upload and export rights": (
        "تعریف کاربر، نقش، تیم مجاز، آپلود و خروجی"
    ),
    "New user": "کاربر جدید",
    "The user and initial access are created in the database": "کاربر و دسترسی اولیه در دیتابیس ساخته می‌شود",
    "All teams": "همه تیم‌ها",
    "Permissions": "مجوزها",
    "Referral & SMS": "ریفرال و پیامک",
    "Export": "خروجی",
    "Upload invoice": "آپلود فاکتور",
    "Upload receipt": "آپلود رسید",
    "Create user": "ساخت کاربر",
    "How user management works": "روش مدیریت کاربران",
    "Regular users are not configured in environment variables": "کاربران معمولی در متغیرهای محیطی تعریف نمی‌شوند",
    "Bootstrap admin": "ادمین اولیه",
    "Created for local development with": "برای توسعه محلی با",
    "Regular users": "کاربران عادی",
    "Created from this page and stored in the database.": "از همین صفحه ساخته و در دیتابیس ذخیره می‌شوند.",
    "Safe delete": "حذف امن",
    "A user is deactivated (not deleted) so invoice history stays intact.": (
        "کاربر غیرفعال می‌شود (حذف نمی‌شود) تا تاریخچه فاکتورها سالم بماند."
    ),
    ".env file": "فایل env",
    "Holds": "شامل",
    "server settings and the database connection — not day-to-day users.": (
        "تنظیمات سرور و اتصال دیتابیس است — نه کاربران روزمره."
    ),
    "Current users": "کاربران فعلی",
    "Roles and team-level access": "نقش‌ها و دسترسی‌های تیمی",
    "Name": "نام",
    "Group": "گروه",
    "Access": "دسترسی‌ها",
    "Status": "وضعیت",
    "Actions": "عملیات",
    "Active": "فعال",
    "Inactive": "غیرفعال",
    "Deactivate": "غیرفعال‌سازی",
    "Activate": "فعال‌سازی",
    "Current user": "کاربر فعلی",
    "No users.": "کاربری وجود ندارد.",
    # --- Print report ---
    "Invoice report": "گزارش فاکتورها",
    "Use your browser's print dialog to save as PDF": "برای ذخیره PDF از چاپ مرورگر استفاده کنید",
    "Print / Save PDF": "چاپ / ذخیره PDF",
    "Generated at": "زمان تولید",
    "No data.": "داده‌ای وجود ندارد.",
    # --- Login ---
    "Sign in": "ورود",
    "Sign in with your username and password": "با نام کاربری و رمز عبور وارد شوید",
    # --- Payment stages (PaymentStage.choices labels) ---
    "Draft": "پیش‌نویس",
    "Submitted": "ارسال‌شده",
    "Finance review": "بررسی مالی",
    "Approved": "تاییدشده",
    "Rejected": "ردشده",
    "Cancelled": "لغوشده",
    # --- Cost buckets (CostBucket.choices labels) ---
    "Referral": "ریفرال",
    "SMS": "پیامک",
    "General": "عمومی",
    # --- Roles ---
    "Manager": "مدیر",
    "Editor": "ویرایشگر",
    "Observer": "ناظر",
    "Admin": "ادمین",
    # --- Import summary labels (result_summary) ---
    "Teams": "تیم‌ها",
    # --- Flash messages ---
    "Invoice saved.": "فاکتور ثبت شد.",
    "Invoice updated.": "فاکتور به‌روزرسانی شد.",
    "Payment stage updated.": "مرحله پرداخت به‌روزرسانی شد.",
    "Invalid payment stage.": "مرحله پرداخت معتبر نیست.",
    "File uploaded.": "فایل آپلود شد.",
    "Upload failed. Check the file type or your permissions.": (
        "آپلود فایل انجام نشد. نوع فایل یا دسترسی را بررسی کنید."
    ),
    "There is no file ready to import.": "هیچ فایل آماده‌ای برای ورود وجود ندارد.",
    "Excel data imported into the database.": "اطلاعات اکسل وارد دیتابیس شد.",
    "Dry-run complete. If the result looks correct, confirm the import.": (
        "بررسی اولیه انجام شد. اگر نتیجه درست است، ورود را تایید کنید."
    ),
    "You cannot deactivate your own account.": "نمی‌توانید حساب خودتان را غیرفعال کنید.",
    "User status updated.": "وضعیت کاربر به‌روزرسانی شد.",
    "New user created.": "کاربر جدید ساخته شد.",
    # --- Misc data fallbacks ---
    "No team": "بدون تیم",
}

TRANSLATIONS: dict[str, dict[str, str]] = {"fa": FA}


def translate(text, lang: str) -> str:
    """Return the localized string for ``text`` in ``lang`` (English fallback)."""
    source = "" if text is None else str(text)
    if lang == "en":
        return source
    return TRANSLATIONS.get(lang, {}).get(source, source)
