from typing import List

class ServiceUser:
    """
    Lightweight, stateless user compatible with Django auth.
    """

    def __init__(self, user_id: int, scopes: List[str]):
        self.id = user_id
        self.pk = user_id
        self.scopes = scopes
        self.is_active = True
        self.is_staff = False
        self.is_superuser = False
        self.username = ""

    @property
    def is_anonymous(self) -> bool:
        return False

    @property
    def is_authenticated(self) -> bool:
        return True

    def get_username(self) -> str:
        return self.username
