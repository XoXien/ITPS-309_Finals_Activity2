from functools import partial

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forms import PhotoForm, PostForm, ProfileForm, RegistrationForm
from .models import Post, Profile


def can_edit(request, profile):
    return request.user.is_authenticated and (
        profile.user_id == request.user.pk or request.user.is_staff
    )


def require_owner(request, profile):
    if not can_edit(request, profile):
        raise PermissionDenied


def can_post(request, profile):
    return request.user.is_authenticated and profile.user_id == request.user.pk


def require_post_owner(request, profile):
    if not can_post(request, profile):
        raise PermissionDenied


@never_cache
@login_required
def home(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "name": request.user.get_full_name()[:80] or request.user.username[:80]
        },
    )
    return redirect(profile)


@never_cache
@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("facebook:home")
    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data["full_name"]
            user.save()
            # Keep a profile created in this browser by the earlier project version.
            profile = (
                Profile.objects.select_for_update()
                .filter(pk=request.session.get("profile_id"), user__isnull=True)
                .first()
            )
            if profile is None:
                Profile.objects.create(user=user, name=form.cleaned_data["full_name"])
            else:
                profile.user = user
                profile.name = form.cleaned_data["full_name"]
                profile.save(update_fields=["user", "name", "updated_at"])
        request.session.pop("profile_id", None)
        login(request, user)
        messages.success(request, "Your account is ready. Welcome to your profile!")
        return redirect("facebook:home")
    return render(request, "registration/register.html", {"form": form})


@never_cache
def profile_page(request, public_id):
    profile = get_object_or_404(Profile, public_id=public_id)
    tab = request.GET.get("tab", "posts")
    if tab not in {"posts", "about", "photos"}:
        tab = "posts"
    return render(
        request,
        "profiles/profile.html",
        {
            "profile": profile,
            "can_edit": can_edit(request, profile),
            "can_post": can_post(request, profile),
            "tab": tab,
            "profile_form": ProfileForm(instance=profile),
            "picture_form": PhotoForm(prefix="profile"),
            "cover_form": PhotoForm(prefix="cover"),
            "post_form": PostForm(),
            "posts": Paginator(profile.posts.all(), 10).get_page(
                request.GET.get("page")
            )
            if tab == "posts"
            else None,
            "public_link": request.build_absolute_uri(profile.get_absolute_url()),
        },
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def create_post(request, public_id):
    profile = get_object_or_404(Profile, public_id=public_id)
    require_post_owner(request, profile)
    form = PostForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.profile = profile
        post.save()
        messages.success(request, "Your post has been published.")
        return redirect(profile)
    return render(
        request,
        "profiles/editor.html",
        {
            "profile": profile,
            "form": form,
            "heading": "Create post",
            "action": "Post",
            "can_edit": True,
        },
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def edit_post(request, public_id, post_id):
    profile = get_object_or_404(Profile, public_id=public_id)
    require_post_owner(request, profile)
    post = get_object_or_404(Post, profile=profile, pk=post_id)
    form = PostForm(request.POST if request.method == "POST" else None, instance=post)
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        updated.updated_at = timezone.now()
        updated.save(update_fields=["body", "updated_at"])
        messages.success(request, "Your post has been updated.")
        return redirect(profile)
    return render(
        request,
        "profiles/editor.html",
        {
            "profile": profile,
            "form": form,
            "heading": "Edit post",
            "action": "Save changes",
            "can_edit": True,
        },
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def delete_post(request, public_id, post_id):
    profile = get_object_or_404(Profile, public_id=public_id)
    require_post_owner(request, profile)
    post = get_object_or_404(Post, profile=profile, pk=post_id)
    if request.method == "POST":
        post.delete()
        messages.success(request, "Your post has been deleted.")
        return redirect(profile)
    return render(
        request,
        "profiles/delete_post.html",
        {
            "profile": profile,
            "post": post,
            "can_edit": True,
        },
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def edit_profile(request, public_id):
    profile = get_object_or_404(Profile, public_id=public_id)
    require_owner(request, profile)
    form = ProfileForm(
        request.POST if request.method == "POST" else None, instance=profile
    )
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        updated.save(update_fields=[*ProfileForm.Meta.fields, "updated_at"])
        messages.success(request, "Your profile is updated.")
        return redirect(profile)
    return render(
        request,
        "profiles/editor.html",
        {
            "profile": profile,
            "form": form,
            "heading": "Edit profile",
            "action": "Save changes",
            "can_edit": True,
        },
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def upload_photo(request, public_id, kind):
    if kind not in {"profile", "cover"}:
        raise Http404
    profile = get_object_or_404(Profile, public_id=public_id)
    require_owner(request, profile)
    form = PhotoForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
        prefix=kind,
    )
    if request.method == "POST" and form.is_valid():
        field_name = "profile_picture" if kind == "profile" else "cover_photo"
        new_name = None
        storage = Profile._meta.get_field(field_name).storage
        try:
            with transaction.atomic():
                profile = get_object_or_404(
                    Profile.objects.select_for_update(), pk=profile.pk
                )
                photo = getattr(profile, field_name)
                old_name = photo.name
                prepared = form.cleaned_data["image"]
                photo.save(prepared.name, prepared, save=False)
                new_name = photo.name
                fields = [field_name, "updated_at"]
                if kind == "profile":
                    profile.picture_updated_at = timezone.now()
                    fields.append("picture_updated_at")
                profile.save(update_fields=fields)
                if old_name:
                    transaction.on_commit(
                        partial(storage.delete, old_name), robust=True
                    )
        except Exception:
            if new_name:
                storage.delete(new_name)
            raise
        messages.success(
            request,
            "Your profile picture is updated."
            if kind == "profile"
            else "Your cover photo is updated.",
        )
        return redirect(profile)
    return render(
        request,
        "profiles/editor.html",
        {
            "profile": profile,
            "form": form,
            "heading": "Update profile picture"
            if kind == "profile"
            else "Update cover photo",
            "action": "Save photo",
            "photo_editor": True,
            "can_edit": True,
        },
    )
