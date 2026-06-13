"""Management command to purge old activity and login logs.

Keeps ``UserLoginActivity`` rows for the last 90 days and
``SystemActivityLog`` rows for the last 180 days.

Run nightly via cron or Celery Beat:
    python manage.py purge_old_logs --days 90
    python manage.py purge_old_logs --days 180 --model SystemActivityLog
"""
from datetime import timedelta

from django.utils import timezone
from django.core.management.base import BaseCommand, CommandParser

from medos_internal.models import SystemActivityLog, UserLoginActivity


MODEL_MAP = {
    'UserLoginActivity': UserLoginActivity,
    'SystemActivityLog': SystemActivityLog,
}

DEFAULT_RETENTION = {
    'UserLoginActivity': 90,
    'SystemActivityLog': 180,
}


class Command(BaseCommand):
    help = 'Purge activity logs older than the retention period.'

    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            '--model',
            choices=list(MODEL_MAP.keys()),
            default=None,
            help='Specific model to purge (default: all).',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='Override retention days (default: per-model).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print counts without deleting.',
        )

    def handle(self, **options):
        models_to_purge = (
            [options['model']]
            if options['model']
            else list(MODEL_MAP.keys())
        )

        for name in models_to_purge:
            model = MODEL_MAP[name]
            days = options['days'] or DEFAULT_RETENTION[name]
            cutoff = timezone.now() - timedelta(days=days)

            # Determine the date field name
            date_field = (
                'login_timestamp' if name == 'UserLoginActivity'
                else 'timestamp'
            )

            qs = model.objects.filter(**{f'{date_field}__lt': cutoff})
            count = qs.count()

            if options['dry_run']:
                self.stdout.write(
                    f'{name}: {count} rows older than {days} days would be purged.'
                )
            else:
                qs.delete()
                self.stdout.write(
                    f'{name}: purged {count} rows older than {days} days.'
                )
