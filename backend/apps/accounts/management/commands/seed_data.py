"""
Management command: seed_data
Creates all default permissions, roles, and an admin superuser.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.rbac.models import Permission, Role, RolePermission, UserRole
from apps.rbac.permission_sync import sync_permissions

User = get_user_model()

# Role → permission codenames. 'Admin' is special-cased to receive *every*
# permission (including auto-discovered model permissions). Auditor and User get
# explicit curated subsets.
ROLE_PERMISSIONS = {
    'Auditor': [
        'users.read',
        'roles.read',
        'permissions.read',
        'audit.read',
        'audit.export',
        'reports.view',
        'profile.read',
        'profile.update',
    ],
    'User': [
        'profile.read',
        'profile.update',
    ],
}


class Command(BaseCommand):
    help = 'Seed default permissions, roles, and admin user'

    def add_arguments(self, parser):
        parser.add_argument('--admin-email', default='admin@example.com')
        parser.add_argument('--admin-password', default='Admin@1234!')
        parser.add_argument('--admin-first-name', default='System')
        parser.add_argument('--admin-last-name', default='Admin')

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== Seeding RBAC data ==='))

        # 1. Discover & create all permissions (custom + model-generated).
        self.stdout.write('  Syncing permissions from models...')
        stats = sync_permissions()
        self.stdout.write(
            f"    [SYNCED] {stats['total']} permissions "
            f"({stats['created']} new, {stats['updated']} updated)"
        )
        perm_objects = {p.codename: p for p in Permission.objects.all()}

        # 2. Create Roles and assign permissions. Admin gets everything.
        self.stdout.write('  Creating roles...')
        role_permissions = dict(ROLE_PERMISSIONS)
        role_permissions['Admin'] = list(perm_objects.keys())
        for role_name in ('Admin', 'Auditor', 'User'):
            perm_codenames = role_permissions[role_name]
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={'description': f'Default {role_name} role'}
            )
            status = 'CREATED' if created else 'EXISTS'
            self.stdout.write(f'    [{status}] Role: {role_name} ({len(perm_codenames)} perms)')

            for codename in perm_codenames:
                perm = perm_objects.get(codename)
                if perm:
                    RolePermission.objects.get_or_create(role=role, permission=perm)

        # 3. Create Admin superuser
        self.stdout.write('  Creating admin user...')
        email = options['admin_email']
        password = options['admin_password']
        first_name = options['admin_first_name']
        last_name = options['admin_last_name']

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(f'    [CREATED] Admin: {email}')
        else:
            self.stdout.write(f'    [EXISTS]  Admin: {email}')

        # Assign Admin role to admin user
        admin_role = Role.objects.get(name='Admin')
        UserRole.objects.get_or_create(user=user, role=admin_role)

        self.stdout.write(self.style.SUCCESS('=== Seeding complete ==='))
        self.stdout.write(self.style.WARNING(
            f'\n  Admin credentials:\n'
            f'    Email:    {email}\n'
            f'    Password: {password}\n'
            f'  CHANGE THESE IN PRODUCTION!'
        ))
