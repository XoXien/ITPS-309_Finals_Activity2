import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Profile


def create_user(username, **kwargs):
    kwargs.setdefault("email", username + "@example.org")
    return get_user_model().objects.create_user(username=username, **kwargs)


def picture(name="portrait.png", color="cornflowerblue"):
    content = BytesIO()
    Image.new("RGBA", (180, 240), color).save(content, format="PNG")
    return SimpleUploadedFile(name, content.getvalue(), content_type="image/png")


class ProfileTests(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.temporary.name)
        self.settings_override.enable()
        self.user = create_user(username="profileowner")
        self.client.force_login(self.user)
        self.client.get(reverse("facebook:home"))
        self.profile = Profile.objects.get(user=self.user)

    def tearDown(self):
        self.settings_override.disable()
        self.temporary.cleanup()

    def photo_url(self, kind="profile"):
        return reverse("facebook:upload_photo", args=[self.profile.public_id, kind])

    def test_home_returns_to_same_profile_and_sections_render(self):
        self.assertRedirects(
            self.client.get(reverse("facebook:home")), self.profile.get_absolute_url()
        )
        self.assertEqual(Profile.objects.count(), 1)
        for tab in ("posts", "about", "photos"):
            with self.subTest(tab=tab):
                self.assertEqual(
                    self.client.get(
                        self.profile.get_absolute_url(), {"tab": tab}
                    ).status_code,
                    200,
                )

    def test_edit_profile_updates_only_details(self):
        result = self.client.post(
            reverse("facebook:edit_profile", args=[self.profile.public_id]),
            {
                "name": "Alex Rivera",
                "headline": "BSIT student",
                "bio": "Building my first Django project.",
                "city": "Lucena City",
                "school": "My University",
                "workplace": "",
                "website": "https://example.org",
            },
        )
        self.assertRedirects(result, self.profile.get_absolute_url())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.name, "Alex Rivera")
        self.assertContains(
            self.client.get(self.profile.get_absolute_url()), "Lucena City"
        )

    def test_picture_upload_is_normalized_and_survives_reload(self):
        response = self.client.post(
            self.photo_url(), {"profile-image": picture("../../photo.php.png")}
        )
        self.assertRedirects(response, self.profile.get_absolute_url())
        self.profile.refresh_from_db()
        saved = self.profile.profile_picture
        self.assertTrue(saved.name.startswith("profile_pictures/"))
        self.assertTrue(saved.name.endswith(".jpg"))
        self.assertNotIn("photo.php", saved.name)
        with Image.open(saved.path) as image:
            self.assertEqual(
                (image.format, image.mode, image.size), ("JPEG", "RGB", (180, 240))
            )
        self.assertIsNotNone(self.profile.picture_updated_at)
        self.assertContains(self.client.get(self.profile.get_absolute_url()), saved.url)
        self.assertContains(
            self.client.get(self.profile.get_absolute_url()), "Profile picture updated"
        )

    def test_cover_upload_does_not_replace_profile_picture(self):
        self.client.post(self.photo_url(), {"profile-image": picture()})
        self.profile.refresh_from_db()
        avatar = self.profile.profile_picture.name
        self.client.post(
            self.photo_url("cover"), {"cover-image": picture("cover.png", "seagreen")}
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile_picture.name, avatar)
        self.assertTrue(self.profile.cover_photo.name.startswith("cover_photos/"))
        self.assertContains(
            self.client.get(self.profile.get_absolute_url()),
            self.profile.cover_photo.url,
        )

    def test_invalid_images_are_rejected_without_changing_saved_picture(self):
        self.client.post(self.photo_url(), {"profile-image": picture()})
        self.profile.refresh_from_db()
        original = self.profile.profile_picture.name
        bad = SimpleUploadedFile(
            "fake.jpg", b"This is a text file.", content_type="image/jpeg"
        )
        response = self.client.post(self.photo_url(), {"profile-image": bad})
        self.assertIn("image", response.context["form"].errors)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile_picture.name, original)
        valid = picture()
        oversized = SimpleUploadedFile(
            "large.png",
            valid.read() + b"\0" * (5 * 1024 * 1024),
            content_type="image/png",
        )
        response = self.client.post(self.photo_url(), {"profile-image": oversized})
        self.assertIn("image", response.context["form"].errors)
        self.assertContains(response, "5 MB")

    def test_replacing_image_removes_only_the_previous_file_after_save(self):
        self.client.post(self.photo_url(), {"profile-image": picture()})
        self.profile.refresh_from_db()
        old_path = Path(self.profile.profile_picture.path)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                self.photo_url(), {"profile-image": picture(color="seagreen")}
            )
        self.profile.refresh_from_db()
        self.assertFalse(old_path.exists())
        self.assertTrue(Path(self.profile.profile_picture.path).is_file())

    def test_database_failure_does_not_discard_the_existing_picture(self):
        self.client.post(self.photo_url(), {"profile-image": picture()})
        self.profile.refresh_from_db()
        original = self.profile.profile_picture.name
        files_before = {file.name for file in Path(self.temporary.name).rglob("*.jpg")}
        with (
            patch.object(
                Profile, "save", side_effect=RuntimeError("Test database failure")
            ),
            self.assertRaises(RuntimeError),
        ):
            self.client.post(
                self.photo_url(), {"profile-image": picture(color="seagreen")}
            )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile_picture.name, original)
        self.assertEqual(
            {file.name for file in Path(self.temporary.name).rglob("*.jpg")},
            files_before,
        )

    def test_shared_profile_is_readable_and_editing_is_owner_only(self):
        visitor = Client()
        page = visitor.get(self.profile.get_absolute_url())
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'data-open="edit-dialog"')
        other_user = create_user(username="visitor")
        visitor.force_login(other_user)
        self.assertEqual(
            visitor.post(
                reverse("facebook:edit_profile", args=[self.profile.public_id]),
                {"name": "Someone else"},
            ).status_code,
            403,
        )
        self.assertEqual(
            visitor.post(self.photo_url(), {"profile-image": picture()}).status_code,
            403,
        )
        self.assertFalse(Profile.objects.get(pk=self.profile.pk).profile_picture)
        visitor.get(reverse("facebook:home"))
        self.assertNotEqual(Profile.objects.get(user=other_user).pk, self.profile.pk)

    def test_upload_requires_a_valid_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(reverse("facebook:home"), follow=True)
        profile = Profile.objects.get(user=self.user)
        url = reverse("facebook:upload_photo", args=[profile.public_id, "profile"])
        self.assertEqual(
            client.post(url, {"profile-image": picture()}).status_code, 403
        )
        client.get(profile.get_absolute_url())
        response = client.post(
            url,
            {
                "profile-image": picture(),
                "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
            },
        )
        self.assertEqual(response.status_code, 302)
