from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import BenevoleProfile, CitoyenProfile, User, VeterinaireProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "phone", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("PawRescue", {"fields": ("role", "phone", "fcm_token")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("PawRescue", {"fields": ("role", "phone")}),
    )


@admin.register(CitoyenProfile)
class CitoyenProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "address")
    search_fields = ("user__username", "address")


@admin.register(BenevoleProfile)
class BenevoleProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_available", "latitude", "longitude", "max_missions")
    list_filter = ("is_available",)


@admin.register(VeterinaireProfile)
class VeterinaireProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "license_number",
        "governorate",
        "clinic_name",
        "verification_status",
        "is_available",
    )
    list_filter = ("verification_status", "is_available", "governorate")
    search_fields = ("user__email", "license_number", "clinic_name")
    readonly_fields = ("verification_document",)
