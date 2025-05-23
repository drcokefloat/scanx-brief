"""
ScanX URL Configuration
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path, include
from django.views.generic import TemplateView

from brief import views as brief_views

# Authentication URLs
auth_patterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="/"), name="logout"),
    path("signup/", brief_views.signup, name="signup"), 
]

# Brief URLs
brief_patterns = [
    path("", brief_views.brief_list, name="brief_list"),
    path("create/", brief_views.create_brief, name="create_brief"),
    path("<uuid:brief_id>/", brief_views.brief_dashboard, name="brief_dashboard"),
    path("<uuid:brief_id>/status/", brief_views.brief_status, name="brief_status"),
    path("<uuid:brief_id>/delete/", brief_views.delete_brief, name="delete_brief"),
    path("<uuid:brief_id>/refresh/", brief_views.refresh_brief_view, name="refresh_brief"),
]

# Main URL patterns
urlpatterns = [
    # Home
    path("", brief_views.landing_page, name="landing"),
    
    # Admin
    path("admin/", admin.site.urls),
    
    # Authentication
    path("accounts/", include(auth_patterns)),
    
    # Brief management
    path("briefs/", include(brief_patterns)),
]

