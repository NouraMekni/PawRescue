from django.urls import path

from .views import ReportDetailView, ReportListCreateView, ReportNearbyView

urlpatterns = [
    path("", ReportListCreateView.as_view(), name="report-list"),
    path("nearby/", ReportNearbyView.as_view(), name="report-nearby"),
    path("<int:pk>/", ReportDetailView.as_view(), name="report-detail"),
]
