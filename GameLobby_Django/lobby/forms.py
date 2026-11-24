from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    BaseUserCreationForm,
)

from .models import Player


class RegisterForm(BaseUserCreationForm):
    email = forms.EmailField(
        label="Email address",
        max_length=254,
        widget=forms.EmailInput(
            attrs={"autocomplete": "email", "placeholder": "Enter your email address"}
        ),
    )

    class Meta(BaseUserCreationForm.Meta):
        model = Player
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            autocomplete="username", placeholder="Enter your username"
        )
        self.fields["password1"].widget.attrs.update(
            placeholder="Enter your password", autocomplete="new-password"
        )
        self.fields["password2"].widget.attrs.update(
            placeholder="Re-enter your password", autocomplete="new-password"
        )
        self.fields["password2"].label = "Confirm password"

    def clean_username(self):
        value = self.cleaned_data["username"].strip()
        if Player.objects.filter(username__iexact=value).exists():
            raise forms.ValidationError("That username is already in use.")
        return value

    def clean_email(self):
        value = self.cleaned_data["email"].strip().lower()
        if Player.objects.filter(email__iexact=value).exists():
            raise forms.ValidationError("That email address is already in use.")
        return value


class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, label="Remember me")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            placeholder="Enter your username", autocomplete="username"
        )
        self.fields["password"].widget.attrs.update(
            placeholder="Enter your password", autocomplete="current-password"
        )
