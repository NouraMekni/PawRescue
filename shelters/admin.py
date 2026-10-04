from django.contrib import admin

from accounts.admin import ApprovalEmailMixin

from .models import Refuge, RefugeMembership


class RefugeMembershipInline(admin.TabularInline):
    model = RefugeMembership
    extra = 0


@admin.register(Refuge)
class RefugeAdmin(ApprovalEmailMixin, admin.ModelAdmin):
    list_display = ("name", "account_email", "structure", "governorate", "is_verified")
    list_filter = ("is_verified", "governorate", "structure")
    search_fields = ("name", "rne", "official_email", "user__email", "user__username")
    readonly_fields = ("verification_document",)
    list_select_related = ("user",)
    filter_horizontal = ("accepted_species",)
    inlines = [RefugeMembershipInline]
    fieldsets = (
        (
            "Vérification",
            {"fields": ("is_verified", "verification_document")},
        ),
        (
            "Organisation",
            {
                "fields": (
                    "user",
                    "name",
                    "structure",
                    "rne",
                    "governorate",
                    "address",
                    "phone",
                    "official_email",
                    "representative_name",
                )
            },
        ),
        (
            "Fiche",
            {
                "fields": (
                    "description",
                    "capacity",
                    "action_radius_km",
                    "latitude",
                    "longitude",
                    "logo",
                    "accepted_species",
                )
            },
        ),
    )

    @admin.display(description="E-mail du compte")
    def account_email(self, obj):
        return obj.user.email

    def save_model(self, request, obj, form, change):
        was_verified = False
        if change and obj.pk:
            was_verified = (
                Refuge.objects.filter(pk=obj.pk).values_list("is_verified", flat=True).first()
                is True
            )
        super().save_model(request, obj, form, change)
        if obj.is_verified and not was_verified:
            request._pawrescue_approval_email = (obj.user_id, "refuge")


@admin.register(RefugeMembership)
class RefugeMembershipAdmin(admin.ModelAdmin):
    list_display = ("refuge", "user", "member_type", "status", "joined_at")
    list_filter = ("member_type", "status")
