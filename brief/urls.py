from django.urls import path
from . import views

urlpatterns = [
    path("briefs/<uuid:brief_id>/", views.brief_dashboard, name="brief_dashboard"),
    path("briefs/", views.brief_list, name="brief_list"),
]
