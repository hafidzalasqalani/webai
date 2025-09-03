# Standard library
import uuid

# Django / third-party
from django.db import models
from django.contrib.auth.models import AbstractUser
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

profile_images = S3Boto3Storage(bucket_name=settings.BUCKET_PROFILE_IMAGES)


# Function Rename File
def user_profile_image_path(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    return filename


# Table CustomUser
class CustomUser(AbstractUser):
    email = models.EmailField(unique=False)
    profile_image = models.ImageField(
        upload_to=user_profile_image_path,
        blank=True,
        null=True,
        storage=profile_images,
    )

    def __str__(self):
        return self.email
