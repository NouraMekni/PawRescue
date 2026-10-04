from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .emails import notify_approval
from .models import BenevoleProfile, CitoyenProfile, User, VeterinaireProfile


class ApprovalEmailMixin:
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        request._pawrescue_approval_email = None
        response = super().changeform_view(request, object_id, form_url, extra_context)
        self.send_queued_approval_email(request, response)
        return response

    def send_queued_approval_email(self, request, response=None):
        if response is not None and getattr(response, "status_code", 200) >= 400:
            return
        payload = getattr(request, "_pawrescue_approval_email", None)
        request._pawrescue_approval_email = None
        if not payload:
            return
        user_id, role_label = payload
        user = User.objects.filter(pk=user_id).first()
        if user is not None:
            notify_approval(request, user, role_label)


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
class VeterinaireProfileAdmin(ApprovalEmailMixin, admin.ModelAdmin):
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

    def save_model(self, request, obj, form, change):
        previous = None
        if change and obj.pk:
            previous = (
                VeterinaireProfile.objects.filter(pk=obj.pk)
                .values_list("verification_status", flat=True)
                .first()
            )
        super().save_model(request, obj, form, change)
        if (
            obj.verification_status == VeterinaireProfile.VerificationStatus.APPROVED
            and previous != VeterinaireProfile.VerificationStatus.APPROVED
        ):
            request._pawrescue_approval_email = (obj.user_id, "vétérinaire")
