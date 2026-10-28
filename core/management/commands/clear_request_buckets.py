from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import RequestBucket


class Command(BaseCommand):
    help = 'Delete expired abuse counters (run daily).'

    def handle(self, *args, **kwargs):
        count, _ = RequestBucket.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(str(count))
