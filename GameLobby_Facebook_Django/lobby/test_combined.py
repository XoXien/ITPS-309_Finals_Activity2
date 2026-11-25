from django.test import TestCase
from django.urls import reverse

from profiles.models import Profile

from .models import Player


class CombinedProjectTests(TestCase):
    def registration(self):
        return {
            "username": "SharedPlayer",
            "email": "shared@example.org",
            "password1": "Maple-Cloud-7304!",
            "password2": "Maple-Cloud-7304!",
        }

    def test_both_sections_keep_their_own_templates_and_navigation(self):
        games = self.client.get(reverse("games:login"))
        facebook = self.client.get(reverse("facebook:login"))
        self.assertContains(games, "/static/lobby/site.css")
        self.assertNotContains(games, "/static/profiles/site.css")
        self.assertNotContains(games, "/facebook/")
        self.assertNotContains(games, "Facebook")
        self.assertContains(facebook, "/static/profiles/site.css")
        self.assertNotContains(facebook, "/static/lobby/site.css")
        self.assertNotContains(facebook, "/games/")
        self.assertNotContains(facebook, "GameLobby")
        game_registration = self.client.get(reverse("games:register"))
        self.assertNotContains(game_registration, "/facebook/")
        self.assertNotContains(game_registration, "Facebook")
        game_error = self.client.get("/games/missing-page/")
        self.assertEqual(game_error.status_code, 404)
        self.assertContains(game_error, "/static/lobby/site.css", status_code=404)
        self.assertNotContains(game_error, "Facebook", status_code=404)
        facebook_error = self.client.get("/facebook/missing-page/")
        self.assertEqual(facebook_error.status_code, 404)
        self.assertContains(
            facebook_error, "/static/profiles/site.css", status_code=404
        )

    def test_gamelobby_account_can_open_and_edit_its_facebook_profile(self):
        credentials = self.registration()
        self.client.post(reverse("games:register"), credentials)
        self.client.post(
            reverse("games:login"),
            {"username": credentials["username"], "password": credentials["password1"]},
        )
        page = self.client.get(reverse("facebook:home"), follow=True)
        game_page = self.client.get(reverse("games:login"))
        self.assertNotContains(game_page, "/facebook/")
        self.assertNotContains(game_page, "Facebook")
        profile = Profile.objects.get()
        self.assertEqual(profile.user, Player.objects.get())
        self.assertEqual(profile.name, "SharedPlayer")
        self.assertContains(page, 'data-open="edit-dialog"')
        self.assertTrue(profile.get_absolute_url().startswith("/facebook/profile/"))
        self.assertContains(page, reverse("facebook:logout"))

    def test_account_created_from_facebook_can_log_in_through_games(self):
        credentials = self.registration()
        self.client.post(
            reverse("facebook:register"), {**credentials, "full_name": "Alex Rivera"}
        )
        self.assertContains(
            self.client.get(reverse("games:login")), "You're logged in."
        )
        profile_id = Profile.objects.get().pk
        self.client.post(reverse("facebook:logout"))
        response = self.client.post(
            reverse("games:login"),
            {"username": "sharedplayer", "password": credentials["password1"]},
            follow=True,
        )
        self.assertContains(response, "You're logged in.")
        self.client.get(reverse("facebook:home"))
        self.assertEqual(Profile.objects.get().pk, profile_id)

    def test_logout_from_either_section_signs_out_of_both(self):
        player = Player.objects.create_user(
            username="logoutplayer", email="logout@example.org"
        )
        for logout in ("games:logout", "facebook:logout"):
            with self.subTest(logout=logout):
                self.client.force_login(player)
                self.client.get(reverse("facebook:home"))
                self.client.post(reverse(logout))
                self.assertNotIn("_auth_user_id", self.client.session)
                self.assertContains(
                    self.client.get(reverse("games:login")), "Welcome back."
                )
                response = self.client.get(reverse("facebook:home"))
                self.assertTrue(response.url.startswith(reverse("facebook:login")))

    def test_accounts_cannot_be_duplicated_through_the_other_registration_form(self):
        data = self.registration()
        self.client.post(reverse("games:register"), data)
        form = self.client.post(
            reverse("facebook:register"),
            {**data, "full_name": "Alex Rivera", "username": "SHAREDPLAYER"},
        ).context["form"]
        self.assertIn("username", form.errors)
        self.assertIn("email", form.errors)
        self.assertEqual(Player.objects.count(), 1)

    def test_old_bookmarks_redirect_into_the_new_paths(self):
        self.assertRedirects(
            self.client.get("/"), reverse("games:home"), fetch_redirect_response=False
        )
        self.assertRedirects(self.client.get("/login/"), reverse("games:login"))
        self.assertRedirects(self.client.get("/register/"), reverse("games:register"))
        profile = Profile.objects.create(name="Public profile")
        self.assertRedirects(
            self.client.get(f"/profile/{profile.public_id}/"),
            profile.get_absolute_url(),
        )
