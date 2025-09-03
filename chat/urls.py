# Django / third-party
from django.urls import path
from django.views.generic import RedirectView

# Local app imports
from .views import (
    ChatView,
    ChatStreamView,
    create_chat,
    delete_chat,
    update_chat_title,
)

urlpatterns = [
    path("", RedirectView.as_view(url="new/", permanent=True)),
    path("new/", ChatView.as_view(), name="new_chat"),
    path("create/", create_chat, name="create_chat"),
    path("<int:chat_id>/", ChatView.as_view(), name="chat_detail"),
    path("<int:chat_id>/stream/", ChatStreamView.as_view(), name="chat_stream"),
    path("<int:chat_id>/delete/", delete_chat, name="delete_chat"),
    path("<int:chat_id>/update-title/", update_chat_title, name="update_chat_title"),
]
