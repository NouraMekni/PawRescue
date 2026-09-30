from django.urls import path

from .views import (
    ConversationAcceptView,
    ConversationBlockView,
    ConversationDetailView,
    ConversationListCreateView,
    MessageCreateView,
    RefugeListView,
    VeterinaireListView,
)

urlpatterns = [
    path("refuges/", RefugeListView.as_view(), name="messaging-refuges"),
    path("veterinaires/", VeterinaireListView.as_view(), name="messaging-vets"),
    path("conversations/", ConversationListCreateView.as_view(), name="messaging-conversations"),
    path("conversations/<int:pk>/", ConversationDetailView.as_view(), name="messaging-conversation"),
    path("conversations/<int:pk>/messages/", MessageCreateView.as_view(), name="messaging-messages"),
    path("conversations/<int:pk>/accept/", ConversationAcceptView.as_view(), name="messaging-accept"),
    path("conversations/<int:pk>/block/", ConversationBlockView.as_view(), name="messaging-block"),
]
