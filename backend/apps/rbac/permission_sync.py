"""
Model-driven permission discovery.

This is what makes the RBAC app *universal*: drop it into any Django project,
add your own models, and a `create/read/update/delete/list/export` permission is
generated for every discovered model automatically. Generated ("managed")
permissions follow the ``app_label.model.action`` codename convention, e.g.::

    blog.post.create
    blog.post.read
    accounts.user.update

Custom, non-model permissions (the RBAC management permissions like
``users.create`` or ``audit.export``) live in ``RBAC_CUSTOM_PERMISSIONS`` and are
created alongside the managed ones but never pruned.

Configuration (all overridable in settings.py):
    RBAC_AUTO_DISCOVER       bool  run automatically on post_migrate
    RBAC_AUTO_PRUNE          bool  delete managed perms whose model is gone
    RBAC_PERMISSION_ACTIONS  list  actions generated per model
    RBAC_EXCLUDED_APPS       list  app_labels to skip entirely
    RBAC_EXCLUDED_MODELS     list  'app_label.model' entries to skip
    RBAC_CUSTOM_PERMISSIONS  list  (codename, name, resource, action) tuples
"""
from django.apps import apps as django_apps
from django.conf import settings
from django.db import transaction

# Actions generated for every discovered model.
DEFAULT_ACTIONS = ['create', 'read', 'update', 'delete', 'list', 'export']

# Framework / internal apps that should never get auto CRUD permissions.
DEFAULT_EXCLUDED_APPS = [
    'admin',
    'auth',
    'contenttypes',
    'sessions',
    'token_blacklist',
]

# RBAC's own plumbing tables — managing the manager is meaningless.
DEFAULT_EXCLUDED_MODELS = [
    'rbac.permission',
    'rbac.rolepermission',
    'rbac.userrole',
]

# Hand-defined permissions that don't map 1:1 to a model. These govern the RBAC
# admin surface itself and are referenced by the default seeded roles.
DEFAULT_CUSTOM_PERMISSIONS = [
    # (codename, name, resource, action)
    ('users.create',       'Create users',                'users',       'create'),
    ('users.read',         'View users',                  'users',       'read'),
    ('users.update',       'Update users',                'users',       'update'),
    ('users.delete',       'Delete users',                'users',       'delete'),
    ('roles.create',       'Create roles',                'roles',       'create'),
    ('roles.read',         'View roles',                  'roles',       'read'),
    ('roles.update',       'Update roles',                'roles',       'update'),
    ('roles.delete',       'Delete roles',                'roles',       'delete'),
    ('permissions.read',   'View permissions',            'permissions', 'read'),
    ('permissions.assign', 'Assign permissions to roles', 'permissions', 'assign'),
    ('permissions.sync',   'Sync permissions from models','permissions', 'sync'),
    ('audit.read',         'View audit logs',             'audit',       'read'),
    ('audit.export',       'Export audit logs',           'audit',       'export'),
    ('reports.view',       'View reports',                'reports',     'view'),
    ('profile.read',       'View own profile',            'profile',     'read'),
    ('profile.update',     'Update own profile',          'profile',     'update'),
]


def _cfg(name, default):
    return getattr(settings, name, default)


def discoverable_models():
    """Yield model classes that should receive auto-generated permissions."""
    excluded_apps = set(_cfg('RBAC_EXCLUDED_APPS', DEFAULT_EXCLUDED_APPS))
    excluded_models = {m.lower() for m in _cfg('RBAC_EXCLUDED_MODELS', DEFAULT_EXCLUDED_MODELS)}

    for model in django_apps.get_models():
        meta = model._meta
        if meta.app_label in excluded_apps:
            continue
        if f'{meta.app_label}.{meta.model_name}' in excluded_models:
            continue
        # Skip auto-created M2M through tables — they're implementation detail.
        if getattr(meta, 'auto_created', False):
            continue
        yield model


@transaction.atomic
def sync_permissions(prune=None):
    """Create/update permissions for every discovered model and custom entry.

    Returns a stats dict: {created, updated, pruned, total}.
    """
    from .models import Permission

    if prune is None:
        prune = bool(_cfg('RBAC_AUTO_PRUNE', False))

    actions = list(_cfg('RBAC_PERMISSION_ACTIONS', DEFAULT_ACTIONS))
    custom = list(_cfg('RBAC_CUSTOM_PERMISSIONS', DEFAULT_CUSTOM_PERMISSIONS))

    created = updated = 0
    managed_codenames = set()

    def upsert(codename, name, resource, action, *, managed, content_type=None):
        nonlocal created, updated
        _, was_created = Permission.objects.update_or_create(
            codename=codename,
            defaults={
                'name': name,
                'resource': resource,
                'action': action,
                'managed': managed,
                'content_type': content_type,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    # 1. Custom (non-model) permissions.
    for codename, name, resource, action in custom:
        upsert(codename, name, resource, action, managed=False)

    # 2. Auto-generated permissions, one set per discovered model.
    from django.contrib.contenttypes.models import ContentType
    for model in discoverable_models():
        meta = model._meta
        resource = f'{meta.app_label}.{meta.model_name}'
        ct = ContentType.objects.get_for_model(model)
        label = str(meta.verbose_name).strip().title()
        for action in actions:
            codename = f'{resource}.{action}'
            managed_codenames.add(codename)
            upsert(
                codename,
                f'{action.title()} {label}',
                resource,
                action,
                managed=True,
                content_type=ct,
            )

    # 3. Optionally remove managed permissions whose model/action disappeared.
    pruned = 0
    if prune:
        stale = Permission.objects.filter(managed=True).exclude(codename__in=managed_codenames)
        pruned = stale.count()
        stale.delete()

    # 4. Keep the superuser role holding every permission, so newly discovered
    #    permissions are usable immediately without re-seeding.
    granted = _grant_all_to_superuser_role()

    return {
        'created': created,
        'updated': updated,
        'pruned': pruned,
        'granted': granted,
        'total': Permission.objects.count(),
    }


def _grant_all_to_superuser_role():
    """Attach every permission to the configured superuser role. Returns the
    number of newly attached permissions (0 if the role/feature is disabled)."""
    from .models import Permission, Role, RolePermission

    role_name = _cfg('RBAC_SUPERUSER_ROLE', 'Admin')
    if not role_name:
        return 0
    try:
        role = Role.objects.get(name=role_name)
    except Role.DoesNotExist:
        return 0  # not seeded yet; seed_data will create and fill it

    held = set(
        RolePermission.objects.filter(role=role).values_list('permission_id', flat=True)
    )
    missing = Permission.objects.exclude(id__in=held).values_list('id', flat=True)
    new_links = [RolePermission(role=role, permission_id=pid) for pid in missing]
    RolePermission.objects.bulk_create(new_links, ignore_conflicts=True)
    return len(new_links)
