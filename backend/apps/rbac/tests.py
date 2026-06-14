"""Tests for the rbac app: model-driven permission discovery, role/permission
aggregation, the superuser short-circuit, and API-level access enforcement."""
from django.conf import settings as dj_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.rbac.models import Permission, Role, RolePermission, UserRole
from apps.rbac.permission_sync import sync_permissions
from apps.rbac.permissions import rbac_permission

User = get_user_model()

_NO_THROTTLE = {
    **dj_settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_RATES': {'anon': None, 'user': None, 'auth': None, 'login': None},
}
STRONG_PW = 'Testpass123!'
ACTIONS = ['create', 'read', 'update', 'delete', 'list', 'export']


class PermissionDiscoveryTests(TestCase):
    def test_sync_generates_full_action_set_per_model(self):
        sync_permissions()
        for action in ACTIONS:
            codename = f'accounts.user.{action}'
            self.assertTrue(Permission.objects.filter(codename=codename).exists(),
                            f'missing managed permission {codename}')

    def test_managed_permissions_flagged_and_linked_to_content_type(self):
        sync_permissions()
        perm = Permission.objects.get(codename='accounts.user.create')
        self.assertTrue(perm.managed)
        self.assertIsNotNone(perm.content_type)

    def test_custom_management_permissions_created(self):
        sync_permissions()
        for codename in ['users.create', 'roles.update', 'audit.export',
                         'reports.view', 'profile.read', 'permissions.sync']:
            self.assertTrue(Permission.objects.filter(codename=codename).exists(),
                            f'missing custom permission {codename}')

    def test_rbac_plumbing_tables_excluded(self):
        sync_permissions()
        self.assertFalse(Permission.objects.filter(codename='rbac.permission.create').exists())
        self.assertFalse(Permission.objects.filter(codename='rbac.userrole.read').exists())

    def test_prune_removes_stale_managed_permissions(self):
        sync_permissions()
        Permission.objects.create(codename='ghost.model.read', name='Ghost',
                                  resource='ghost.model', action='read', managed=True)
        sync_permissions(prune=True)
        self.assertFalse(Permission.objects.filter(codename='ghost.model.read').exists())


class PermissionAggregationTests(TestCase):
    def setUp(self):
        sync_permissions()

    def _user_with_perms(self, email, codenames):
        user = User.objects.create_user(email=email, password=STRONG_PW,
                                        first_name='T', last_name='U')
        role = Role.objects.create(name=f'role_{email}')
        for codename in codenames:
            RolePermission.objects.create(role=role,
                                          permission=Permission.objects.get(codename=codename))
        UserRole.objects.create(user=user, role=role)
        return user

    def test_has_rbac_permission_true_for_granted_false_otherwise(self):
        user = self._user_with_perms('agg@example.com', ['users.read'])
        self.assertTrue(user.has_rbac_permission('users.read'))
        self.assertFalse(user.has_rbac_permission('users.delete'))

    def test_permissions_aggregate_across_multiple_roles(self):
        user = User.objects.create_user(email='multi@example.com', password=STRONG_PW,
                                        first_name='M', last_name='R')
        r1 = Role.objects.create(name='r1')
        r2 = Role.objects.create(name='r2')
        RolePermission.objects.create(role=r1, permission=Permission.objects.get(codename='users.read'))
        RolePermission.objects.create(role=r2, permission=Permission.objects.get(codename='audit.read'))
        UserRole.objects.create(user=user, role=r1)
        UserRole.objects.create(user=user, role=r2)
        self.assertTrue(user.has_rbac_permission('users.read'))
        self.assertTrue(user.has_rbac_permission('audit.read'))

    def test_superuser_short_circuits_all_checks(self):
        su = User.objects.create_superuser(email='su@example.com', password=STRONG_PW)
        self.assertTrue(su.has_rbac_permission('anything.not.granted'))

    def test_rbac_permission_factory_names_class(self):
        cls = rbac_permission('users.create')
        self.assertEqual(cls.__name__, 'RBACPermission_users_create')


@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
class RBACEnforcementTests(APITestCase):
    def setUp(self):
        cache.clear()
        call_command('seed_data', verbosity=0)
        self.admin = User.objects.get(email='admin@example.com')
        self.auditor = self._role_user('auditor@example.com', 'Auditor')
        self.normal = self._role_user('enduser@example.com', 'User')

    def _role_user(self, email, role_name):
        user = User.objects.create_user(email=email, password=STRONG_PW,
                                        first_name='T', last_name='U')
        UserRole.objects.create(user=user, role=Role.objects.get(name=role_name))
        return user

    def test_admin_can_list_users(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/api/rbac/users/').status_code, status.HTTP_200_OK)

    def test_admin_can_create_user(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post('/api/rbac/users/', {
            'email': 'created@example.com', 'first_name': 'C', 'last_name': 'U',
            'password': STRONG_PW,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_auditor_can_read_but_not_create_users(self):
        self.client.force_authenticate(self.auditor)
        self.assertEqual(self.client.get('/api/rbac/users/').status_code, status.HTTP_200_OK)
        denied = self.client.post('/api/rbac/users/', {
            'email': 'nope@example.com', 'first_name': 'N', 'last_name': 'O',
            'password': STRONG_PW,
        }, format='json')
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_end_user_denied_admin_endpoints(self):
        self.client.force_authenticate(self.normal)
        self.assertEqual(self.client.get('/api/rbac/users/').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get('/api/rbac/roles/').status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_denied(self):
        self.assertEqual(self.client.get('/api/rbac/users/').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_seed_data_creates_default_roles(self):
        for name in ('Admin', 'Auditor', 'User'):
            self.assertTrue(Role.objects.filter(name=name).exists())
        # User role is least-privilege: own profile only.
        user_perms = set(
            RolePermission.objects.filter(role__name='User')
            .values_list('permission__codename', flat=True)
        )
        self.assertEqual(user_perms, {'profile.read', 'profile.update'})
