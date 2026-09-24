from django.contrib import admin

from .models import Report, ReportPhoto


class ReportPhotoInline(admin.TabularInline):
    model = ReportPhoto
    extra = 0


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "type",
        "status",
        "severity",
        "reporter",
        "assigned_refuge",
        "latitude",
        "longitude",
        "created_at",
    )
    list_filter = ("type", "status", "severity")
    search_fields = ("description", "address_text", "reporter__username")
    inlines = [ReportPhotoInline]


@admin.register(ReportPhoto)
class ReportPhotoAdmin(admin.ModelAdmin):
    list_display = ("report", "order", "taken_at")
