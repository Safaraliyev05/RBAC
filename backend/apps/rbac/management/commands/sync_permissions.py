"""
Management command: sync_permissions

Discover all project models and (re)generate their RBAC permissions. Runs
automatically on migrate too; this command is for manual/CI use.

    python manage.py sync_permissions
    python manage.py sync_permissions --prune
"""
from django.core.management.base import BaseCommand

from apps.rbac.permission_sync import sync_permissions


class Command(BaseCommand):
    help = 'Discover models and synchronise RBAC permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--prune',
            action='store_true',
            help='Delete managed permissions whose model no longer exists.',
        )

    def handle(self, *args, **options):
        stats = sync_permissions(prune=options['prune'])
        self.stdout.write(self.style.SUCCESS(
            f"[RBAC] synced {stats['total']} permissions "
            f"({stats['created']} new, {stats['updated']} updated, {stats['pruned']} pruned, "
            f"{stats['granted']} granted to admin)"
        ))
