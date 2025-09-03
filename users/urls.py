# Django / third-party
from django.urls import path
from django.contrib.auth.views import LoginView

# Local app imports
from .views import UserRegistrationView, UserProfileView, LogoutView, user_profile_image

urlpatterns = [
    path(
        "login/",
        LoginView.as_view(
            template_name="users/login.html", redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("user_image/<str:username>/", user_profile_image, name="user_profile_image"),
]
