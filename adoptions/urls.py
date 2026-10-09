from django.urls import path

from .views import (
    AdoptionListCreateView,
    AdoptionDetailView,
    AdoptionCancelView,
    AdoptionApproveView,
    AdoptionRejectView,
)


urlpatterns = [
    path(
        "",
        AdoptionListCreateView.as_view(),
        name="adoption-list-create",
    ),
    path(
        "<int:pk>/",
        AdoptionDetailView.as_view(),
        name="adoption-detail",
    ),
    path(
        "<int:pk>/cancel/",
        AdoptionCancelView.as_view(),
        name="adoption-cancel",
    ),
    path(
        "<int:pk>/approve/",
        AdoptionApproveView.as_view(),
        name="adoption-approve",
    ),
    path(
        "<int:pk>/reject/",
        AdoptionRejectView.as_view(),
        name="adoption-reject",
    ),
]