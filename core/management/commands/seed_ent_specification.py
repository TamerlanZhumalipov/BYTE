from importlib import import_module

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Create ENT-2026 catalogue; optionally add missing initial root mappings."

    def add_arguments(self, parser):
        parser.add_argument("--map-existing", action="store_true", help="Add initial mappings to existing topics (never deletes custom mappings).")

    @transaction.atomic
    def handle(self, *args, **options):
        module = import_module("core.migrations.0005_seed_ent_2026")
        from types import SimpleNamespace
        module.seed(apps, SimpleNamespace(connection=connection), map_existing=options["map_existing"])
        self.stdout.write(self.style.SUCCESS("ENT-2026 ready. Review coverage in admin."))
