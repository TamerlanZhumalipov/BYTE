import os
import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create a consistent SQLite backup outside the repository (mode 0600).'

    def add_arguments(self, parser):
        parser.add_argument('--output', required=True)

    def handle(self, *args, **options):
        config=settings.DATABASES['default']
        if config['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError('Use the database vendor backup utility for non-SQLite databases.')
        source=Path(config['NAME']).resolve()
        target=Path(options['output']).resolve()
        if not source.is_file():
            raise CommandError('Database does not exist.')
        if target.is_relative_to(settings.BASE_DIR.resolve()):
            raise CommandError('Keep backups outside the repository and static directories.')
        try:
            descriptor=os.open(str(target),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            os.close(descriptor)
            with sqlite3.connect('file:'+source.as_posix()+'?mode=ro',uri=True) as db,sqlite3.connect(str(target)) as backup:
                db.backup(backup)
                if backup.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise CommandError('Backup integrity check failed.')
        except (OSError,sqlite3.Error) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write('Consistent backup created; integrity check passed.')
