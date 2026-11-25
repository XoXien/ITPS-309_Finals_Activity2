from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Profile
from .tests import create_user


class AccountTests(TestCase):
    def registration(self, **changes):
        data = {
            "full_name": "Alex Rivera",
            "username": "alex.rivera",
            "email": "alex.rivera@example.org",
            "password1": "Demo-Passphrase-472!",
            "password2": "Demo-Passphrase-472!",
        }
        data.update(changes)
        return data

    def test_anonymous_home_shows_login_without_creating_a_profile(self):
        response = self.client.get(reverse("facebook:home"), follow=True)
        self.assertContains(response, "Welcome back")
        self.assertEqual(Profile.objects.count(), 0)
        self.assertNotContains(response, 'type="file"')

    def test_registration_creates_a_hashed_password_and_an_owned_profile(self):
        response = self.client.post(
            reverse("facebook:register"), self.registration(), follow=True
        )
        user = get_user_model().objects.get(username="alex.rivera")
        self.assertTrue(user.check_password(self.registration()["password1"]))
        self.assertNotEqual(user.password, self.registration()["password1"])
        self.assertEqual(user.profile.name, "Alex Rivera")
        self.assertFalse(user.is_staff)
        self.assertContains(response, "Log out")
        self.assertContains(response, 'data-open="edit-dialog"')

    def test_duplicate_username_is_rejected_case_insensitively(self):
        create_user(username="Alex.Rivera")
        response = self.client.post(reverse("facebook:register"), self.registration())
        self.assertIn("username", response.context["form"].errors)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(Profile.objects.count(), 0)

    def test_invalid_passwords_do_not_create_accounts(self):
        for password1, password2 in (
            ("x", "x"),
            ("password", "password"),
            ("Abcdefghi!", "different"),
        ):
            with self.subTest(password=password1):
                response = self.client.post(
                    reverse("facebook:register"),
                    self.registration(password1=password1, password2=password2),
                )
                self.assertTrue(response.context["form"].errors)
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_login_from_another_browser_restores_the_same_profile(self):
        self.client.post(reverse("facebook:register"), self.registration())
        user = get_user_model().objects.get(username="alex.rivera")
        other_browser = Client()
        response = other_browser.post(
            reverse("facebook:login"),
            {"username": user.username, "password": self.registration()["password1"]},
            follow=True,
        )
        self.assertEqual(response.request["PATH_INFO"], user.profile.get_absolute_url())
        self.assertContains(response, 'data-open="edit-dialog"')
        self.assertEqual(Profile.objects.count(), 1)

    def test_wrong_password_does_not_log_in(self):
        create_user(username="alex.rivera", password="A-valid-passphrase!")
        response = self.client.post(
            reverse("facebook:login"), {"username": "alex.rivera", "password": "wrong"}
        )
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post_and_removes_edit_access(self):
        self.client.post(reverse("facebook:register"), self.registration())
        profile = Profile.objects.get()
        self.assertEqual(self.client.get(reverse("facebook:logout")).status_code, 405)
        self.assertRedirects(
            self.client.post(reverse("facebook:logout")), reverse("facebook:login")
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        page = self.client.get(profile.get_absolute_url())
        self.assertContains(page, "Alex Rivera")
        self.assertNotContains(page, 'data-open="edit-dialog"')
        self.assertIn("no-store", page.headers["Cache-Control"])
        edit = self.client.get(
            reverse("facebook:edit_profile", args=[profile.public_id])
        )
        self.assertEqual(edit.status_code, 302)
        self.assertTrue(edit.url.startswith(reverse("facebook:login")))

    def test_registration_and_login_reject_external_redirects(self):
        self.client.post(reverse("facebook:register"), self.registration())
        self.client.post(reverse("facebook:logout"))
        response = self.client.post(
            reverse("facebook:login"),
            {
                "username": "alex.rivera",
                "password": self.registration()["password1"],
                "next": "https://example.org/",
            },
        )
        self.assertEqual(response.url, reverse("facebook:home"))

    def test_registration_claims_only_legacy_profile_from_its_own_session(self):
        legacy = Profile.objects.create(name="Old profile", bio="Keep my details")
        unrelated = Profile.objects.create(name="Someone else's old profile")
        session = self.client.session
        session["profile_id"] = legacy.pk
        session.save()
        self.client.post(reverse("facebook:register"), self.registration())
        user = get_user_model().objects.get(username="alex.rivera")
        legacy.refresh_from_db()
        unrelated.refresh_from_db()
        self.assertEqual(legacy.user_id, user.pk)
        self.assertEqual(legacy.bio, "Keep my details")
        self.assertIsNone(unrelated.user_id)
        self.assertNotIn("profile_id", self.client.session)

    def test_a_legacy_session_cannot_claim_an_account_owned_profile(self):
        owner = create_user(username="original")
        original = Profile.objects.create(user=owner, name="Original owner")
        session = self.client.session
        session["profile_id"] = original.pk
        session.save()
        self.client.post(reverse("facebook:register"), self.registration())
        original.refresh_from_db()
        self.assertEqual(original.user_id, owner.pk)
        self.assertEqual(Profile.objects.count(), 2)

    def test_registration_and_logout_require_csrf_tokens(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post(reverse("facebook:register"), self.registration()).status_code,
            403,
        )
        user = create_user(username="csrfowner")
        client.force_login(user)
        self.assertEqual(client.post(reverse("facebook:logout")).status_code, 403)

    def test_regular_accounts_cannot_edit_another_profile(self):
        self.client.post(
            reverse("facebook:register"),
            self.registration(is_staff="1", is_superuser="1"),
        )
        first = Profile.objects.get()
        self.assertFalse(first.user.is_superuser)
        other = create_user(username="other")
        self.client.force_login(other)
        edit_url = reverse("facebook:edit_profile", args=[first.public_id])
        self.assertEqual(
            self.client.post(edit_url, {"name": "Changed"}).status_code, 403
        )
        photo_url = reverse("facebook:upload_photo", args=[first.public_id, "profile"])
        self.assertEqual(self.client.get(photo_url).status_code, 403)
        first.refresh_from_db()
        self.assertEqual(first.name, "Alex Rivera")
