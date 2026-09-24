from django.contrib import admin

from .models import Animal, AnimalPhoto, MedicalEntry, MedicalRecord, Species


class AnimalPhotoInline(admin.TabularInline):
    model = AnimalPhoto
    extra = 0


class MedicalEntryInline(admin.TabularInline):
    model = MedicalEntry
    extra = 0


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ("name", "icon")
    search_fields = ("name",)


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "refuge", "status", "is_adoptable", "created_at")
    list_filter = ("status", "species", "is_adoptable", "sex")
    search_fields = ("name", "breed", "color")
    inlines = [AnimalPhotoInline]


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("animal", "next_appointment", "updated_at")
    search_fields = ("animal__name",)
    inlines = [MedicalEntryInline]


@admin.register(MedicalEntry)
class MedicalEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "entry_type", "date", "medical_record", "performed_by")
    list_filter = ("entry_type",)


@admin.register(AnimalPhoto)
class AnimalPhotoAdmin(admin.ModelAdmin):
    list_display = ("animal", "is_primary", "order")
