from django.core.management.base import BaseCommand
from app.api.models.service import AuthorizedService


class Command(BaseCommand):
    help = "Create a new AuthorizedService and show its API key and secret"

    def add_arguments(self, parser):
        parser.add_argument(
            "name", type=str, help="Name of the authorized service"
        )
        parser.add_argument(
            "--scopes",
            nargs="*",
            default=[],
            help="Optional list of allowed scopes (space-separated)",
        )

    def handle(self, *args, **options):
        name = options["name"]
        scopes = options["scopes"]

        service = AuthorizedService.objects.create(
            name=name,
            allowed_scopes=scopes
        )

        self.stdout.write(self.style.SUCCESS(f"Service '{service.name}' created!"))
        self.stdout.write(f"API Key: {service.api_key}")
        self.stdout.write(f"API Secret: {service.api_secret}")
