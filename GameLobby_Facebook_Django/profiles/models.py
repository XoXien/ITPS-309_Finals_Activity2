import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        null=True,
        blank=True,
    )
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=80, default="Your Name")
    headline = models.CharField(
        max_length=160,
        blank=True,
        default="Student · Learning, creating, and connecting.",
    )
    bio = models.TextField(max_length=500, blank=True)
    city = models.CharField(max_length=100, blank=True)
    school = models.CharField(max_length=140, blank=True)
    workplace = models.CharField(max_length=140, blank=True)
    website = models.URLField(blank=True)
    profile_picture = models.ImageField(upload_to="profile_pictures/", blank=True)
    cover_photo = models.ImageField(upload_to="cover_photos/", blank=True)
    picture_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("facebook:profile", args=[self.public_id])

    @property
    def initials(self):
        words = self.name.split()
        return "".join(word[0] for word in words[:2]).upper()


class Post(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="posts")
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return self.body[:80]
