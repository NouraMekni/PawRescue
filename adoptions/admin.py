from django.contrib import admin

from .models import AdoptionRequest


@admin.register(AdoptionRequest)
class AdoptionRequestAdmin(admin.ModelAdmin):
    list_display = ("animal", "applicant", "refuge", "status", "created_at", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("animal__name", "applicant__username")
