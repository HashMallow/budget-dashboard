from __future__ import annotations

from django.urls import path

from . import views

app_name = "marketing"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
