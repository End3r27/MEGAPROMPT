"""URL configuration for API endpoints."""

from django.urls import path

from api import views

urlpatterns = [
    path("generate/", views.generate, name="generate"),
    path("generate/<str:job_id>/", views.get_generate_result, name="get_generate_result"),
    path("analyze/", views.analyze, name="analyze"),
    path("analyze/<str:job_id>/", views.get_analyze_result, name="get_analyze_result"),
    path("config/", views.config_view, name="config"),
    path("cache/", views.cache_view, name="cache"),
    path("checkpoints/", views.checkpoints_view, name="checkpoints"),
    path("checkpoints/<str:checkpoint_id>/", views.checkpoints_view, name="checkpoint_detail"),
]

