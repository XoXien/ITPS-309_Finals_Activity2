from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "headline", "city", "created_at")
    search_fields = ("name", "headline", "city", "user__username")
    readonly_fields = ("public_id", "created_at", "updated_at")
