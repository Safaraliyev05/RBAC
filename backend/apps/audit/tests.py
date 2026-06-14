"""Tests for the audit app: middleware logging, the log utilities, CSV export,
summary/login-failure reports and access enforcement on audit endpoints."""
from django.conf import settings as dj_settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.audit.models import AccessLog
from apps.audit.utils import log_auth_event
from apps.rbac.models import Permission, Role, RolePermission, UserRole
from apps.rbac.permission_sync import sync_permissions

User = get_user_model()

_NO_THROTTLE = {
    **dj_settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_RATES': {'anon': None, 'user': None, 'auth': None, 'login': None},
}
STRONG_PW = 'Testpass123!'


def make_user(email, codenames):
    user = User.objects.create_user(email=email, password=STRONG_PW,
                                    first_name='T', last_name='U')
    if codenames:
        role = Role.objects.create(name=f'role_{email}')
        for codename in codenames:
            RolePermission.objects.create(role=role,
                                          permission=Permission.objects.get(codename=codename))
        UserRole.objects.create(user=user, role=role)
    return user


def bearer(client, user):
    """Authenticate via a real JWT so the AuditMiddleware sees an authenticated
    request.user (mirrors production behaviour)."""
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {AccessToken.for_user(user)}')


class LogUtilityTests(TestCase):
    def setUp(self):
        sync_permissions()

    def test_log_auth_event_creates_record(self):
        user = User.objects.create_user(email='u@example.com', password=STRONG_PW,
                                        first_name='U', last_name='U')
        request = RequestFactory().post('/api/auth/login/')
        log_auth_event(request, user, action='login', result='success', details='ok')
        log = AccessLog.objects.latest('id')
        self.assertEqual(log.action, 'login')
        self.assertEqual(log.result, 'success')
        self.assertEqual(log.user_email, 'u@example.com')


@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
class AuditMiddlewareTests(APITestCase):
    def setUp(self):
        sync_permissions()

    def test_successful_request_is_logged(self):
        reader = make_user('reader@example.com', ['users.read'])
        bearer(self.client, reader)
        before = AccessLog.objects.count()
        resp = self.client.get('/api/rbac/users/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(AccessLog.objects.count(), before)
        log = AccessLog.objects.latest('id')
        self.assertEqual(log.result, AccessLog.RESULT_SUCCESS)
        self.assertEqual(log.user_email, 'reader@example.com')

    def test_denied_request_is_logged_as_denied(self):
        noperm = make_user('noperm@example.com', [])
        bearer(self.client, noperm)
        resp = self.client.get('/api/rbac/users/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            AccessLog.objects.filter(user_email='noperm@example.com',
                                     result=AccessLog.RESULT_DENIED).exists()
        )


@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
class AuditEndpointTests(APITestCase):
    def setUp(self):
        sync_permissions()
        AccessLog.objects.create(user=None, user_email='x@example.com', action='login',
                                 result='failure', http_method='POST', path='/api/auth/login/')

    def test_logs_endpoint_requires_audit_read(self):
        noperm = make_user('a@example.com', [])
        bearer(self.client, noperm)
        self.assertEqual(self.client.get('/api/audit/logs/').status_code,
                         status.HTTP_403_FORBIDDEN)

    def test_auditor_can_read_logs(self):
        reader = make_user('b@example.com', ['audit.read'])
        bearer(self.client, reader)
        self.assertEqual(self.client.get('/api/audit/logs/').status_code,
                         status.HTTP_200_OK)

    def test_csv_export_streams_with_audit_export(self):
        exporter = make_user('c@example.com', ['audit.read', 'audit.export'])
        bearer(self.client, exporter)
        resp = self.client.get('/api/audit/logs/export/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp['Content-Type'].startswith('text/csv'))
        body = b''.join(resp.streaming_content)
        self.assertIn(b'timestamp', body)

    def test_summary_report_requires_reports_view(self):
        viewer = make_user('d@example.com', ['reports.view'])
        bearer(self.client, viewer)
        resp = self.client.get('/api/audit/reports/summary/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('total_events', resp.data)
        self.assertIn('by_result', resp.data)

    def test_login_failures_report(self):
        viewer = make_user('e@example.com', ['reports.view'])
        bearer(self.client, viewer)
        resp = self.client.get('/api/audit/reports/login-failures/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('recent_failures', resp.data)
