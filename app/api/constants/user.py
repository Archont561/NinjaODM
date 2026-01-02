from django.contrib.auth.models import AnonymousUser


class ServiceUser(AnonymousUser):
    """
    A lightweight, stateless user object with no DB representation.
    """
    def __init__(self, user_id: int, scopes: list[str]):
        self.pk = user_id
        self.id = user_id
        self.scopes = scopes
        self.is_active = True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True
