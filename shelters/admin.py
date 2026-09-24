from django.contrib import admin

from .models import Refuge, RefugeMembership


class RefugeMembershipInline(admin.TabularInline):
    model = RefugeMembership
    extra = 0


@admin.register(Refuge)
class RefugeAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "latitude", "longitude", "action_radius_km", "is_verified")
    list_filter = ("is_verified",)
    search_fields = ("name", "address", "user__username")
    filter_horizontal = ("accepted_species",)
    inlines = [RefugeMembershipInline]


@admin.register(RefugeMembership)
class RefugeMembershipAdmin(admin.ModelAdmin):
    list_display = ("refuge", "user", "member_type", "status", "joined_at")
    list_filter = ("member_type", "status")
