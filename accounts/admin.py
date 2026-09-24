from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


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
