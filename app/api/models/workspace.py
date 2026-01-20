from django.db import models
import random

from app.api.models.mixins import UUIDPrimaryKeyModelMixin, TimeStampedModelMixin


ADJECTIVES = [
    "focused",
    "brave",
    "calm",
    "eager",
    "frosty",
    "happy",
    "keen",
    "mighty",
    "quiet",
    "swift",
]

NOUNS = [
    "turing",
    "hopper",
    "lovelace",
    "einstein",
    "curie",
    "tesla",
    "newton",
    "galileo",
    "darwin",
    "morse",
]


def generate_workspace_name():
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    number = random.randint(1, 999)
    return f"{adjective}_{noun}_{number}"


class Workspace(UUIDPrimaryKeyModelMixin, TimeStampedModelMixin, models.Model):
    user_id = models.CharField(max_length=100)
    name = models.CharField(
        max_length=50,
        default=generate_workspace_name,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name
