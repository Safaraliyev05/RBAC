from django.apps import AppConfig


class RbacConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.rbac'
    label = 'rbac'
    verbose_name = 'RBAC'

    def ready(self):
        # Regenerate permissions from the project's models after every migrate,
        # so adding a new model automatically yields its permissions.
        from django.db.models.signals import post_migrate
        post_migrate.connect(_sync_permissions_on_migrate, sender=self)


def _sync_permissions_on_migrate(sender, **kwargs):
    from django.conf import settings
    if not getattr(settings, 'RBAC_AUTO_DISCOVER', True):
        return
    from .permission_sync import sync_permissions
    try:
        stats = sync_permissions()
    except Exception as exc:  # never let discovery break a migration
        print(f'[RBAC] permission sync skipped: {exc}')
        return
    print(
        f"[RBAC] synced {stats['total']} permissions "
        f"({stats['created']} new, {stats['updated']} updated, {stats['pruned']} pruned, "
        f"{stats['granted']} granted to admin)"
    )
