from django.test import Client, TestCase
from django.urls import reverse

from lobby.models import Player

from .models import Post, Profile


class ProfilePostTests(TestCase):
    def setUp(self):
        self.user = Player.objects.create_user(
            username="alex", email="alex@example.org"
        )
        self.profile = Profile.objects.create(user=self.user, name="Alex Rivera")
        self.other = Player.objects.create_user(username="sam", email="sam@example.org")
        self.other_profile = Profile.objects.create(user=self.other, name="Sam Rivera")
        self.client.force_login(self.user)

    def post_url(self, action="create_post", post=None, profile=None):
        args = [(profile or self.profile).public_id]
        if post is not None:
            args.append(post.pk)
        return reverse(f"facebook:{action}", args=args)

    def test_create_persists_and_refresh_does_not_publish_twice(self):
        response = self.client.post(
            self.post_url(),
            {
                "body": "  My first update!\nLearning Django today.  ",
                "profile": self.other_profile.pk,
            },
        )
        self.assertRedirects(response, self.profile.get_absolute_url())
        saved = Post.objects.get()
        self.assertEqual(saved.profile, self.profile)
        self.assertEqual(saved.body, "My first update!\nLearning Django today.")
        for _ in range(2):
            page = self.client.get(self.profile.get_absolute_url())
            self.assertContains(page, "My first update!")
            self.assertContains(page, "Learning Django today.")
        self.assertEqual(Post.objects.count(), 1)
        self.assertContains(page, 'data-open="post-dialog"')

    def test_empty_and_oversized_posts_are_rejected_with_text_retained(self):
        for text in ("   \n ", "A" * 2001):
            with self.subTest(length=len(text)):
                response = self.client.post(self.post_url(), {"body": text})
                self.assertIn("body", response.context["form"].errors)
                self.assertContains(response, "Create post")
        self.assertFalse(Post.objects.exists())

    def test_edit_changes_only_own_content_and_keeps_creation_time(self):
        post = Post.objects.create(profile=self.profile, body="Original update")
        created_at = post.created_at
        page = self.client.get(self.post_url("edit_post", post))
        self.assertContains(page, "Original update")
        response = self.client.post(
            self.post_url("edit_post", post),
            {"body": "Updated text", "profile": self.other_profile.pk},
        )
        self.assertRedirects(response, self.profile.get_absolute_url())
        post.refresh_from_db()
        self.assertEqual(post.body, "Updated text")
        self.assertEqual(post.profile, self.profile)
        self.assertEqual(post.created_at, created_at)
        self.assertIsNotNone(post.updated_at)
        self.assertContains(self.client.get(self.profile.get_absolute_url()), "Edited")

    def test_delete_shows_confirmation_before_removing_the_post(self):
        post = Post.objects.create(profile=self.profile, body="A temporary update")
        url = self.post_url("delete_post", post)
        self.assertContains(self.client.get(url), "Delete this post?")
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())
        self.assertEqual(self.client.put(url).status_code, 405)
        self.assertRedirects(self.client.post(url), self.profile.get_absolute_url())
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_anonymous_visitors_can_read_but_cannot_publish_or_change_posts(self):
        post = Post.objects.create(profile=self.profile, body="A public update")
        visitor = Client()
        page = visitor.get(self.profile.get_absolute_url())
        self.assertContains(page, "A public update")
        self.assertNotContains(page, 'data-open="post-dialog"')
        self.assertNotContains(page, "Edit post")
        for action in ("create_post", "edit_post", "delete_post"):
            url = self.post_url(action, None if action == "create_post" else post)
            response = visitor.post(url, {"body": "Changed"})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(reverse("facebook:login")))
        post.refresh_from_db()
        self.assertEqual(post.body, "A public update")

    def test_other_accounts_and_staff_cannot_impersonate_the_profile_owner(self):
        post = Post.objects.create(profile=self.profile, body="My update")
        for staff in (False, True):
            self.other.is_staff = staff
            self.other.save(update_fields=["is_staff"])
            self.client.force_login(self.other)
            for action in ("create_post", "edit_post", "delete_post"):
                url = self.post_url(action, None if action == "create_post" else post)
                self.assertEqual(
                    self.client.post(url, {"body": "Changed"}).status_code, 403
                )
        self.assertEqual(Post.objects.get().body, "My update")

    def test_a_post_cannot_be_addressed_through_another_profiles_url(self):
        other_post = Post.objects.create(
            profile=self.other_profile, body="Sam's update"
        )
        for action in ("edit_post", "delete_post"):
            self.assertEqual(
                self.client.post(
                    self.post_url(action, other_post), {"body": "Changed"}
                ).status_code,
                404,
            )
        other_post.refresh_from_db()
        self.assertEqual(other_post.body, "Sam's update")

    def test_post_mutations_require_csrf_tokens(self):
        post = Post.objects.create(profile=self.profile, body="Original update")
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        for action in ("create_post", "edit_post", "delete_post"):
            url = self.post_url(action, None if action == "create_post" else post)
            self.assertEqual(client.post(url, {"body": "Changed"}).status_code, 403)
        client.get(self.profile.get_absolute_url())
        response = client.post(
            self.post_url(),
            {
                "body": "Valid update",
                "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Post.objects.count(), 2)

    def test_post_text_is_escaped_instead_of_executed(self):
        self.client.post(
            self.post_url(), {"body": "<script>alert('test')</script>\nA normal line"}
        )
        response = Client().get(self.profile.get_absolute_url())
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert")
        self.assertContains(response, "A normal line")

    def test_posts_are_paginated_newest_first_and_only_for_this_profile(self):
        Post.objects.bulk_create(
            [Post(profile=self.profile, body=f"Update {n}") for n in range(12)]
        )
        Post.objects.create(
            profile=self.other_profile, body="A different profile's post"
        )
        first = self.client.get(self.profile.get_absolute_url())
        self.assertEqual(len(first.context["posts"]), 10)
        self.assertEqual(first.context["posts"][0].body, "Update 11")
        self.assertContains(first, "Older posts")
        self.assertNotContains(first, "A different profile's post")
        second = self.client.get(self.profile.get_absolute_url(), {"page": 2})
        self.assertEqual(
            [post.body for post in second.context["posts"]], ["Update 1", "Update 0"]
        )
