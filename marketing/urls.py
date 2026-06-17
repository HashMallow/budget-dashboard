from __future__ import annotations

from django.contrib.auth import views as auth_views
from django.urls import path

from . import reference_views, views

app_name = "marketing"

urlpatterns = [
    path("favicon.svg", views.favicon_svg, name="favicon_svg"),
    path("assets/fonts/<str:filename>", views.brand_font, name="brand_font"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("help/", views.help_sitemap, name="help_sitemap"),
    path("preferences/", views.set_display_preferences, name="set_display_preferences"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/new/", views.invoice_create, name="invoice_create"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:pk>/edit/", views.invoice_edit, name="invoice_edit"),
    path("invoices/<int:pk>/stage/", views.invoice_stage_update, name="invoice_stage_update"),
    path("invoices/<int:pk>/attachments/", views.invoice_attachment_upload, name="invoice_attachment_upload"),
    path(
        "invoices/attachments/<int:pk>/download/",
        views.invoice_attachment_download,
        name="invoice_attachment_download",
    ),
    path("contracts/", views.contract_list, name="contract_list"),
    path("contracts/new/", views.contract_create, name="contract_create"),
    path("contracts/<int:pk>/", views.contract_detail, name="contract_detail"),
    path("contracts/<int:pk>/edit/", views.contract_edit, name="contract_edit"),
    path("contracts/<int:pk>/stage/", views.contract_stage_update, name="contract_stage_update"),
    path("contracts/<int:pk>/attachments/", views.contract_attachment_upload, name="contract_attachment_upload"),
    path(
        "contracts/attachments/<int:pk>/download/",
        views.contract_attachment_download,
        name="contract_attachment_download",
    ),
    path("vendors/", views.vendor_report, name="vendor_report"),
    path("vendors/<int:pk>/", views.vendor_detail, name="vendor_detail"),
    path("campaigns/", views.campaign_report, name="campaign_report"),
    path("teams/", views.team_list, name="team_list"),
    path("teams/<int:pk>/", views.team_dashboard, name="team_dashboard"),
    path("budgets/", views.budget_list, name="budget_list"),
    path("budgets/new/", views.budget_create, name="budget_create"),
    path("budgets/<int:pk>/edit/", views.budget_edit, name="budget_edit"),
    path("budgets/<int:pk>/delete/", views.budget_delete, name="budget_delete"),
    path("api/budget-variance/", views.budget_variance_api, name="budget_variance_api"),
    path("api/categories-for-team/", views.categories_for_team_api, name="categories_for_team_api"),
    path("imports/", views.import_workbook, name="import_workbook"),
    path("users/", views.user_access, name="user_access"),
    path("reference/", reference_views.reference_data_home, name="reference_data_home"),
    path("reference/vendors/", reference_views.vendor_reference_list, name="vendor_reference_list"),
    path("reference/vendors/new/", reference_views.vendor_reference_create, name="vendor_reference_create"),
    path("reference/vendors/<int:pk>/edit/", reference_views.vendor_reference_edit, name="vendor_reference_edit"),
    path("reference/categories/", reference_views.category_reference_list, name="category_reference_list"),
    path("reference/categories/new/", reference_views.category_reference_create, name="category_reference_create"),
    path(
        "reference/categories/<int:pk>/edit/", reference_views.category_reference_edit, name="category_reference_edit"
    ),
    path("reference/business-lines/", reference_views.businessline_reference_list, name="businessline_reference_list"),
    path(
        "reference/business-lines/new/",
        reference_views.businessline_reference_create,
        name="businessline_reference_create",
    ),
    path(
        "reference/business-lines/<int:pk>/edit/",
        reference_views.businessline_reference_edit,
        name="businessline_reference_edit",
    ),
    path("reference/insurance-rates/", reference_views.insurancerate_reference_list, name="insurancerate_reference_list"),
    path(
        "reference/insurance-rates/new/",
        reference_views.insurancerate_reference_create,
        name="insurancerate_reference_create",
    ),
    path(
        "reference/insurance-rates/<int:pk>/edit/",
        reference_views.insurancerate_reference_edit,
        name="insurancerate_reference_edit",
    ),
    path("reference/sub-teams/", reference_views.subteam_reference_list, name="subteam_reference_list"),
    path("reference/sub-teams/new/", reference_views.subteam_reference_create, name="subteam_reference_create"),
    path("reference/sub-teams/<int:pk>/edit/", reference_views.subteam_reference_edit, name="subteam_reference_edit"),
    path("reference/requesters/", reference_views.requester_reference_list, name="requester_reference_list"),
    path("reference/requesters/new/", reference_views.requester_reference_create, name="requester_reference_create"),
    path(
        "reference/requesters/<int:pk>/edit/", reference_views.requester_reference_edit, name="requester_reference_edit"
    ),
    path("reference/campaigns/", reference_views.campaign_reference_list, name="campaign_reference_list"),
    path("reference/campaigns/new/", reference_views.campaign_reference_create, name="campaign_reference_create"),
    path("reference/campaigns/<int:pk>/edit/", reference_views.campaign_reference_edit, name="campaign_reference_edit"),
    path("reference/vendors/merge/", reference_views.vendor_merge, name="vendor_merge"),
    path("reference/campaigns/merge/", reference_views.campaign_merge, name="campaign_merge"),
    path("exports/pdf/", views.pdf_export_wizard, name="pdf_export_wizard"),
    path("exports/invoices.xlsx", views.export_invoices_excel, name="export_invoices_excel"),
    path("exports/vendors.xlsx", views.export_vendors_excel, name="export_vendors_excel"),
    path("exports/campaigns.xlsx", views.export_campaigns_excel, name="export_campaigns_excel"),
    path("exports/workbook.xlsx", views.export_workbook_excel, name="export_workbook_excel"),
    path("reports/dashboard.pdf", views.dashboard_report_pdf, name="dashboard_report_pdf"),
    path("reports/vendors.pdf", views.export_vendors_pdf, name="export_vendors_pdf"),
    path("reports/campaigns.pdf", views.export_campaigns_pdf, name="export_campaigns_pdf"),
    path("exports/contracts.xlsx", views.export_contracts_excel, name="export_contracts_excel"),
    path("reports/contracts.pdf", views.export_contracts_pdf, name="export_contracts_pdf"),
    path("reports/invoices/print/", views.invoice_report_print, name="invoice_report_print"),
]
