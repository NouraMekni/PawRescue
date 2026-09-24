from django.contrib import admin

from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("donor", "refuge", "animal", "type", "amount", "currency", "status", "created_at")
    list_filter = ("type", "status", "currency")
    search_fields = ("donor__username", "refuge__name", "payment_ref")
