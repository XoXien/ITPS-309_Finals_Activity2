import uuid
from io import BytesIO

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from PIL import Image, ImageOps

from lobby.forms import RegisterForm

from .models import Post, Profile


class RegistrationForm(RegisterForm):
    full_name = forms.CharField(
        max_length=80,
        label="Full name",
        widget=forms.TextInput(attrs={"autocomplete": "name", "autofocus": True}),
    )

    class Meta(RegisterForm.Meta):
        fields = ("full_name", "username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"autocomplete": "username", "autofocus": False}
        )
        self.fields["username"].help_text = "Choose a username to log in with."
        self.fields[
            "password1"
        ].help_text = "Use at least 8 characters. Avoid common passwords and your name."
        self.fields["password2"].label = "Confirm password"
        self.fields["password2"].help_text = ""


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"


class PostForm(forms.ModelForm):
    body = forms.CharField(
        label="What's on your mind?",
        max_length=2000,
        strip=True,
        help_text="Your post will be public on your profile. Maximum 2,000 characters.",
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Share an update..."}),
    )

    class Meta:
        model = Post
        fields = ("body",)


class ProfileForm(forms.ModelForm):
    website = forms.URLField(
        required=False,
        assume_scheme="https",
        validators=[URLValidator(schemes=["http", "https"])],
    )

    class Meta:
        model = Profile
        fields = ("name", "headline", "bio", "city", "school", "workplace", "website")
        labels = {
            "name": "Name",
            "city": "Lives in",
            "school": "School or university",
            "workplace": "Works at",
        }
        widgets = {
            "bio": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Share a little about yourself."}
            ),
            "headline": forms.TextInput(
                attrs={"placeholder": "A few words about you."}
            ),
        }


class PhotoForm(forms.Form):
    image = forms.ImageField(
        label="Choose a photo",
        help_text="JPG, PNG, or WebP · up to 5 MB",
        widget=forms.ClearableFileInput(
            attrs={"accept": "image/jpeg,image/png,image/webp", "data-photo-input": ""}
        ),
    )

    def clean_image(self):
        uploaded = self.cleaned_data["image"]
        if uploaded.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Choose an image smaller than 5 MB.")
        uploaded.seek(0)
        try:
            with Image.open(uploaded) as original:
                if original.format not in {"JPEG", "PNG", "WEBP"}:
                    raise forms.ValidationError("Choose a JPG, PNG, or WebP image.")
                if original.width * original.height > 16_000_000:
                    raise forms.ValidationError(
                        "Choose an image with fewer than 16 million pixels."
                    )
                image = ImageOps.exif_transpose(original).convert("RGBA")
                image.thumbnail((2200, 2200))
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                output = BytesIO()
                background.save(output, format="JPEG", quality=88, optimize=True)
        except (OSError, ValueError) as exc:
            raise forms.ValidationError(
                "This image could not be read. Please choose another photo."
            ) from exc
        return ContentFile(output.getvalue(), name=f"{uuid.uuid4().hex}.jpg")
