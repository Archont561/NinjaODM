import random
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from django.core.files.base import ContentFile
from django.db import transaction

from app.api.models.workspace import Workspace
from app.api.models.task import ODMTask
from app.api.models.result import ODMTaskResult
from app.api.models.image import Image
from app.api.models.gcp import GroundControlPoint
from app.api.constants.odm import (
    ODMTaskStatus,
    ODMProcessingStage,
    ODMTaskResultType,
)

class Command(BaseCommand):
    help = "Seed database with demo ODM data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--workspaces",
            type=int,
            default=3,
            help="Number of workspaces to create",
        )
        parser.add_argument(
            "--tasks",
            type=int,
            default=5,
            help="Tasks per workspace",
        )
        parser.add_argument(
            "--images",
            type=int,
            default=10,
            help="Images per workspace",
        )
        parser.add_argument(
            "--user-id",
            type=str,
            help="Seed data for a specific user_id",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding (scoped to user if --user-id is set)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        workspaces_count = options["workspaces"]
        tasks_per_workspace = options["tasks"]
        images_per_workspace = options["images"]
        user_id = options.get("user_id")
        clear = options["clear"]

        # -----------------------
        # Clear existing data
        # -----------------------
        if clear:
            self._clear_data(user_id)
            self.stdout.write(self.style.WARNING("🧹 Existing data cleared"))
            return

        self.stdout.write(self.style.NOTICE("🌱 Seeding database..."))

        # -----------------------
        # Create workspaces
        # -----------------------
        for w in range(workspaces_count):
            workspace = Workspace.objects.create(
                user_id=user_id or f"user_{w}",
                name=f"Workspace {w + 1}",
            )

            self.stdout.write(f"Created workspace: {workspace.name}")

            # ---- Tasks ----
            tasks = [
                ODMTask.objects.create(
                    workspace=workspace,
                    name=f"Task {i + 1}",
                    status=random.choice(
                        [s.value for s in ODMTaskStatus]
                    ),
                    step=random.choice(
                        [s.value for s in ODMProcessingStage]
                    ),
                    options={"resolution": "high", "orthophoto": True},
                )
                for i in range(tasks_per_workspace)
            ]

            # ---- Task Results ----
            for task in tasks:
                ODMTaskResult.objects.create(
                    workspace=workspace,
                    result_type=random.choice(
                        [r.value for r in ODMTaskResultType]
                    ),
                    file=self._fake_file(
                        f"result_{task.uuid}.txt",
                        "Demo result content",
                    ),
                )

            # ---- Images ----
            images = []
            for i in range(images_per_workspace):
                image = Image.objects.create(
                    workspace=workspace,
                    name=f"image_{i + 1}.jpg",
                    image_file=self._fake_image(f"image_{i + 1}.jpg"),
                    is_thumbnail=False,
                )
                images.append(image)

                Image.objects.create(
                    workspace=workspace,
                    name=f"image_{i + 1}.jpg",
                    image_file=self._fake_image(f"thumb_{i + 1}.jpg"),
                    is_thumbnail=True,
                )

            # ---- Ground Control Points ----
            for image in images:
                for g in range(random.randint(3, 8)):
                    GroundControlPoint.objects.create(
                        image=image,
                        label=f"GCP_{g + 1}",
                        point=Point(
                            random.uniform(-180, 180),
                            random.uniform(-90, 90),
                            random.uniform(0, 1000),
                            srid=4326,
                        ),
                        imgx=random.uniform(0, 4000),
                        imgy=random.uniform(0, 3000),
                    )

        self.stdout.write(self.style.SUCCESS("✅ Database seeded successfully"))

    # -----------------------
    # Helpers
    # -----------------------

    def _clear_data(self, user_id=None):
        workspaces = Workspace.objects.all()
        if user_id:
            workspaces = workspaces.filter(user_id=user_id)

        # cascade-safe deletes
        GroundControlPoint.objects.filter(
            image__workspace__in=workspaces
        ).delete()
        Image.objects.filter(workspace__in=workspaces).delete()
        ODMTaskResult.objects.filter(workspace__in=workspaces).delete()
        ODMTask.objects.filter(workspace__in=workspaces).delete()
        workspaces.delete()

    def _fake_file(self, name, content):
        return ContentFile(content.encode("utf-8"), name=name)

    def _fake_image(self, name):
        return ContentFile(b"fake image content", name=name)
