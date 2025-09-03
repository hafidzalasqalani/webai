# Django / third-party
# from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    # path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="chat/", permanent=True), name="chat"),
    path("chat/", include("chat.urls")),
    path("users/", include("users.urls")),
]
