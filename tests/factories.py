import io
import random
import uuid
import factory
from factory.django import DjangoModelFactory
from factory import fuzzy
from faker import Faker
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image as PILImage

from app.api.models.service import AuthorizedService
from app.api.models.workspace import Workspace
from app.api.models.image import Image

faker = Faker()


class AuthorizedServiceFactory(DjangoModelFactory):
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


class WorkspaceFactory(DjangoModelFactory):
    class Meta:
        model = Workspace

    name = factory.Sequence(lambda n: f"Workspace {n}")


class ImageFactory(DjangoModelFactory):
    class Meta:
        model = Image

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.LazyAttribute(lambda _: f"{uuid.uuid4().hex}.png")
    is_thumbnail = False

    @factory.lazy_attribute
    def image_file(self):
        """Create an in-memory image file."""
        buf = io.BytesIO()
        color = (random.randint(0,255), random.randint(0,255), random.randint(0,255))
        with PILImage.new("RGB", (512, 512), color=color) as im:
            im.save(buf, format="PNG")
        buf.seek(0)
        return SimpleUploadedFile(self.name, buf.getvalue(), content_type="image/png")
    