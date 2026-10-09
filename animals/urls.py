from django.urls import path

from .views import (
    AnimalListCreateView,
    AdoptableAnimalListView,
    AnimalDetailView,
    AnimalMakeAdoptableView,
    AnimalRemoveFromAdoptionView,
    AnimalPhotoCreateView,
    AnimalMedicalRecordCreateView,
    AnimalMedicalRecordDetailView,
    MedicalEntryCreateView,
)


urlpatterns = [

    # Animals
    path(
        "",
        AnimalListCreateView.as_view(),
        name="animal-list-create",
    ),

    path(
        "adoptable/",
        AdoptableAnimalListView.as_view(),
        name="animal-adoptable-list",
    ),

    path(
        "<int:pk>/",
        AnimalDetailView.as_view(),
        name="animal-detail",
    ),

    # Adoption availability
    path(
        "<int:pk>/make-adoptable/",
        AnimalMakeAdoptableView.as_view(),
        name="animal-make-adoptable",
    ),

    path(
        "<int:pk>/remove-from-adoption/",
        AnimalRemoveFromAdoptionView.as_view(),
        name="animal-remove-from-adoption",
    ),

    # Photos
    path(
        "<int:pk>/photos/",
        AnimalPhotoCreateView.as_view(),
        name="animal-photo-create",
    ),

    # Medical
    path(
        "<int:pk>/medical/",
        AnimalMedicalRecordCreateView.as_view(),
        name="animal-medical-create",
    ),

    path(
        "<int:pk>/medical/detail/",
        AnimalMedicalRecordDetailView.as_view(),
        name="animal-medical-detail",
    ),

    path(
        "<int:pk>/medical/entries/",
        MedicalEntryCreateView.as_view(),
        name="animal-medical-entry-create",
    ),
]