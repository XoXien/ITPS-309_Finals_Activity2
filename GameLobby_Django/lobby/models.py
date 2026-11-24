from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.functions import Lower


class PlayerManager(UserManager):
    def get_by_natural_key(self, username):
        return self.get(username__iexact=username)


class Player(AbstractUser):
    email = models.EmailField(unique=True)
    objects = PlayerManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(Lower("username"), name="player_username_folded"),
            models.UniqueConstraint(Lower("email"), name="player_email_folded"),
        ]

    def clean(self):
        super().clean()
        self.email = self.email.strip().lower()
