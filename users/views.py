# Django / third-party
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.db import transaction
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

# Third-party storage
from storages.backends.s3boto3 import S3Boto3Storage

# Local apps
from .models import CustomUser

# S3 storage instance
storage = S3Boto3Storage(bucket_name=settings.BUCKET_PROFILE_IMAGES)


# Local app imports
from .forms import CustomUserCreationForm, CustomUserChangeForm, PasswordChangeForm

User = get_user_model()

@login_required
def user_profile_image(request, username):
    user = get_object_or_404(CustomUser, username=username)
    
    if user != request.user:
        return HttpResponse("Unauthorized", status=403)

    if not user.profile_image:
        raise Http404("No image found")
    
    try:
        file_content = storage.open(user.profile_image.name).read()
        content_type = 'image/jpeg'  # sesuaikan tipe file
        return HttpResponse(file_content, content_type=content_type)
    except Exception:
        raise Http404("Image not found")


# Registration View
class UserRegistrationView(View):
    @method_decorator(csrf_protect)
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("chat")
        form = CustomUserCreationForm()
        return render(request, "users/register.html", {"form": form})

    @method_decorator(csrf_protect)
    def post(self, request):
        if request.user.is_authenticated:
            return redirect("chat")

        form = CustomUserCreationForm(request.POST, request.FILES)
        print(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)

                user.save()

                login(request, user)

                messages.success(
                    request,
                    "Your account has been created! You can now start chatting.",
                )
                return redirect("new_chat")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return render(request, "users/register.html", {"form": form})


# Profile View
class UserProfileView(LoginRequiredMixin, View):
    def get(self, request):
        user_form = CustomUserChangeForm(instance=request.user)
        password_form = PasswordChangeForm(user=request.user)
        context = {
            "user_form": user_form,
            "password_form": password_form,
        }
        return render(request, "users/profile.html", context)

    def handle_password_change(self, request):
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, "Password updated successfully!")
        else:
            for field, errors in password_form.errors.items():
                for error in errors:
                    messages.error(request, f"Password {field}: {error}")
        return redirect("profile")

    def post(self, request):
        action = request.POST.get("action")
        print(request.POST)
        if action == "update_profile":
            user_form = CustomUserChangeForm(
                request.POST, request.FILES, instance=request.user
            )
            if user_form.is_valid():
                user = user_form.save(commit=False)

                user.save()

                messages.success(request, "Profile updated successfully!")
            else:
                for field, errors in user_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

        elif action == "change_password":
            return self.handle_password_change(request)

        return redirect("profile")


# Logout View
class LogoutView(DjangoLogoutView):
    next_page = reverse_lazy("login")

    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect(self.next_page)
