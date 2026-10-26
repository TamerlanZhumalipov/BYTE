from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.legal import LEAD_RETENTION_DAYS
from core.models import Lead


class Command(BaseCommand):
    help = "Delete leads older than the published retention period (dry-run by default)."

    def add_arguments(self, parser):
        parser.add_argument("--delete", action="store_true", help="Actually delete the expired leads.")

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=LEAD_RETENTION_DAYS)
        leads = Lead.objects.filter(created_at__lt=cutoff)
        count = leads.count()
        if options["delete"]:
            leads.delete()
        self.stdout.write(f"{'Deleted' if options['delete'] else 'Would delete'}: {count}")
