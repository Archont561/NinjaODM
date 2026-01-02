import factory
from factory import fuzzy
from faker import Faker

from app.api.models.service import AuthorizedService

faker = Faker()


class AuthorizedServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuthorizedService

    name = factory.Sequence(lambda n: f"gateway-{n}")
    allowed_scopes = fuzzy.FuzzyChoice(
        choices=[
            ["read:profile"],
            ["read:profile", "write:profile"],
            ["read:profile", "read:orders"],
            ["read:profile", "write:orders", "delete:orders"],
            ["read:profile", "read:payments", "write:payments"],
            ["openid", "profile", "email"],
            ["read:all", "write:all"],
            [],
        ]
    )
