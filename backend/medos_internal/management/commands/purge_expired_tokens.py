"""Management command to purge expired auth tokens.

Deletes tokens from ``authtoken_token`` whose ``created`` timestamp
is older than ``settings.TOKEN_EXPIRY_DAYS`` (default 7).

Run nightly via cron or Celery Beat:
    python manage.py purge_expired_tokens
"""
from django.conf import settings
from django.utils import timezone
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = 'Purge expired tokens from the authtoken_token table.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='Override TOKEN_EXPIRY_DAYS from settings.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print counts without deleting.',
        )

    def handle(self, **options):
        expiry_days = options['days'] or getattr(settings, 'TOKEN_EXPIRY_DAYS', 7)
        cutoff = timezone.now() - timezone.timedelta(days=expiry_days)

        qs = Token.objects.filter(created__lt=cutoff)
        count = qs.count()

        if options['dry_run']:
            self.stdout.write(
                f'{count} expired tokens (older than {expiry_days} days) would be purged.'
            )
        else:
            qs.delete()
            self.stdout.write(f'Purged {count} expired tokens.')
