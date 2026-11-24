from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, RegisterForm
from .models import Player


def home(request):
    return redirect("login")


@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return render(request, "accounts/login.html")

    form = LoginForm(
        request=request,
        data=request.POST if request.method == "POST" else None,
        initial={"username": request.session.pop("registered_username", "")},
    )
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        request.session.set_expiry(
            settings.SESSION_COOKIE_AGE if form.cleaned_data["remember_me"] else 0
        )
        return redirect("login")
    return render(request, "accounts/login.html", {"form": form})


@never_cache
@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("login")
    form = RegisterForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                player = form.save()
        except IntegrityError:
            if Player.objects.filter(
                username__iexact=form.cleaned_data["username"]
            ).exists():
                form.add_error("username", "That username is already in use.")
            elif Player.objects.filter(
                email__iexact=form.cleaned_data["email"]
            ).exists():
                form.add_error("email", "That email address is already in use.")
            else:
                raise
        else:
            request.session["registered_username"] = player.username
            messages.success(request, "Account created. You can now log in.")
            return redirect("login")
    return render(request, "accounts/register.html", {"form": form})
