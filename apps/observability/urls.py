from django.urls import path

from apps.observability import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("ready/", views.ready, name="ready"),
    path("metrics/", views.metrics, name="metrics"),
]
