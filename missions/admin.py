from django.contrib import admin

from .models import Mission, MissionResponse, MissionStatusHistory


class MissionStatusHistoryInline(admin.TabularInline):
    model = MissionStatusHistory
    extra = 0
    readonly_fields = ("created_at",)


class MissionResponseInline(admin.TabularInline):
    model = MissionResponse
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "type",
        "status",
        "refuge",
        "assigned_benevole",
        "assigned_veterinaire",
        "created_at",
    )
    list_filter = ("type", "status")
    inlines = [MissionStatusHistoryInline, MissionResponseInline]


@admin.register(MissionStatusHistory)
class MissionStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("mission", "status", "changed_by", "created_at")
    list_filter = ("status",)


@admin.register(MissionResponse)
class MissionResponseAdmin(admin.ModelAdmin):
    list_display = ("mission", "user", "response", "created_at")
    list_filter = ("response",)
