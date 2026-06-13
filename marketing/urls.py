from __future__ import annotations

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "marketing"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("preferences/", views.set_display_preferences, name="set_display_preferences"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/new/", views.invoice_create, name="invoice_create"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:pk>/edit/", views.invoice_edit, name="invoice_edit"),
    path("invoices/<int:pk>/stage/", views.invoice_stage_update, name="invoice_stage_update"),
    path("invoices/<int:pk>/attachments/", views.invoice_attachment_upload, name="invoice_attachment_upload"),
    path("vendors/", views.vendor_report, name="vendor_report"),
    path("campaigns/", views.campaign_report, name="campaign_report"),
    path("budgets/", views.budget_list, name="budget_list"),
    path("imports/", views.import_workbook, name="import_workbook"),
    path("users/", views.user_access, name="user_access"),
    path("exports/invoices.xlsx", views.export_invoices_excel, name="export_invoices_excel"),
    path("reports/invoices/print/", views.invoice_report_print, name="invoice_report_print"),
]
