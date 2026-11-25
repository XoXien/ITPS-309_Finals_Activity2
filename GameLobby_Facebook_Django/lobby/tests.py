from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Player


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AccountTests(TestCase):
    def setUp(self):
        self.data = {
            "username": "ArcPlayer",
            "email": "Arc@Example.org",
            "password1": "Maple-Cloud-7304",
            "password2": "Maple-Cloud-7304",
        }

    def test_registration_creates_account_and_returns_to_login(self):
        response = self.client.post(reverse("games:register"), self.data, follow=True)
        self.assertRedirects(response, reverse("games:login"))
        self.assertContains(response, "Account created")
        self.assertEqual(response.context["form"]["username"].value(), "ArcPlayer")
        player = Player.objects.get()
        self.assertEqual(player.email, "arc@example.org")
        self.assertTrue(player.check_password(self.data["password1"]))
        self.assertNotEqual(player.password, self.data["password1"])
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_usernames_and_emails_are_unique_without_regard_to_case(self):
        self.client.post(reverse("games:register"), self.data)
        for field, value in (("username", "aRCpLAYER"), ("email", "ARC@EXAMPLE.ORG")):
            with self.subTest(field=field):
                data = {
                    **self.data,
                    "username": "DifferentName",
                    "email": "other@example.org",
                    field: value,
                }
                response = self.client.post(reverse("games:register"), data)
                self.assertIn(field, response.context["form"].errors)
        self.assertEqual(Player.objects.count(), 1)

    def test_password_strength_and_confirmation(self):
        for first, second in (
            ("abc", "abc"),
            (self.data["password1"], "Different-password"),
        ):
            response = self.client.post(
                reverse("games:register"),
                {**self.data, "password1": first, "password2": second},
            )
            self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(Player.objects.exists())

    def test_successful_login_and_logout_use_the_login_page(self):
        self.client.post(reverse("games:register"), self.data)
        for remember in (False, True):
            with self.subTest(remember=remember):
                payload = {"username": "arcplayer", "password": self.data["password1"]}
                if remember:
                    payload["remember_me"] = "on"
                response = self.client.post(
                    reverse("games:login"), payload, follow=True
                )
                self.assertRedirects(response, reverse("games:login"))
                self.assertContains(response, "You're logged in.")
                self.assertContains(response, "Welcome, ArcPlayer.")
                self.assertEqual(
                    self.client.session.get_expire_at_browser_close(), not remember
                )
                self.assertIn("no-store", response.headers["Cache-Control"])
                self.assertRedirects(
                    self.client.get(reverse("games:register")), reverse("games:login")
                )
                self.assertEqual(
                    self.client.get(reverse("games:logout")).status_code, 405
                )
                response = self.client.post(reverse("games:logout"), follow=True)
                self.assertRedirects(response, reverse("games:login"))
                self.assertContains(response, "Welcome back.")
                self.assertNotContains(response, "You're logged in.")
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_wrong_password_and_inactive_account_cannot_sign_in(self):
        self.client.post(reverse("games:register"), self.data)
        payload = {"username": "ArcPlayer", "password": "wrong"}
        response = self.client.post(reverse("games:login"), payload)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertNotIn("_auth_user_id", self.client.session)
        Player.objects.update(is_active=False)
        response = self.client.post(
            reverse("games:login"), {**payload, "password": self.data["password1"]}
        )
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_removed_routes_and_account_navigation(self):
        self.assertRedirects(
            self.client.get(reverse("games:home")), reverse("games:login")
        )
        for url in (
            "/games/add/",
            "/my-lobby/",
            "/posts/1/",
            "/admin/",
            "/password/reset/",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
        for name in ("login", "register"):
            html = self.client.get(reverse("games:" + name)).content.decode()
            self.assertIn('href="/games/', html)
            self.assertNotIn('href="/my-lobby/', html)
            self.assertNotIn('href="/password/', html)

    def test_login_ignores_redirects_to_removed_pages_and_other_sites(self):
        self.client.post(reverse("games:register"), self.data)
        for target in ("/games/", "https://external.example/done"):
            self.client.logout()
            response = self.client.post(
                reverse("games:login"),
                {
                    "username": "ArcPlayer",
                    "password": self.data["password1"],
                    "next": target,
                },
            )
            self.assertRedirects(response, reverse("games:login"))

    def test_registration_and_login_require_a_valid_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post(reverse("games:register"), self.data).status_code, 403
        )
        client.get(reverse("games:register"))
        token = client.cookies["csrftoken"].value
        response = client.post(
            reverse("games:register"), {**self.data, "csrfmiddlewaretoken": token}
        )
        self.assertRedirects(response, reverse("games:login"))
        credentials = {"username": "ArcPlayer", "password": self.data["password1"]}
        self.assertEqual(
            client.post(reverse("games:login"), credentials).status_code, 403
        )
        client.get(reverse("games:login"))
        token = client.cookies["csrftoken"].value
        self.assertRedirects(
            client.post(
                reverse("games:login"), {**credentials, "csrfmiddlewaretoken": token}
            ),
            reverse("games:login"),
        )
