import random
import uuid
import factory
from factory.django import DjangoModelFactory
from factory import fuzzy
from faker import Faker
from django.contrib.gis.geos import Point

from app.api.models.service import AuthorizedService
from app.api.models.workspace import Workspace
from app.api.models.image import Image
from app.api.models.gcp import GroundControlPoint
from app.api.models.task import ODMTask
from app.api.models.result import ODMTaskResult
from app.api.constants.odm import ODMTaskStatus, ODMProcessingStage, ODMTaskResultType

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
    user_id = faker.random_int(min=1, max=5000)


class ImageFactory(DjangoModelFactory):
    class Meta:
        model = Image

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.LazyAttribute(lambda _: f"{uuid.uuid4().hex}.png")
    is_thumbnail = False
    

class GroundControlPointFactory(DjangoModelFactory):
    class Meta:
        model = GroundControlPoint
        
    label = factory.LazyFunction(lambda: faker.pystr(min_chars=8, max_chars=12))
    image = factory.SubFactory(ImageFactory)

    imgx = factory.LazyFunction(lambda: faker.pyfloat(min_value=0, max_value=8000))
    imgy = factory.LazyFunction(lambda: faker.pyfloat(min_value=0, max_value=8000))

    @factory.lazy_attribute
    def point(self):
        # Generate random longitude [-180,180], latitude [-90,90], altitude [1,5000]
        lng = float(faker.longitude())
        lat = float(faker.latitude())
        alt = float(faker.random_int(min=1, max=5000))
        return Point(lng, lat, alt)


class ODMTaskFactory(DjangoModelFactory):
    class Meta:
        model = ODMTask

    workspace = factory.SubFactory(WorkspaceFactory)
    status = factory.LazyFunction(lambda: random.choice([s.value for s in ODMTaskStatus]))
    step = factory.LazyFunction(lambda: random.choice([s.value for s in ODMProcessingStage]))
    options = factory.LazyFunction(dict)
    

class ODMTaskResultFactory(DjangoModelFactory):
    class Meta:
        model = ODMTaskResult

    workspace = factory.SubFactory(WorkspaceFactory)
    result_type = factory.LazyFunction(lambda: random.choice([s.value for s in ODMTaskResultType]))
