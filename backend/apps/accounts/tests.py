"""Tests for the accounts app: registration, JWT authentication, account
lockout, profile access and logout/blacklist."""
from django.conf import settings as dj_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

# Disable DRF rate-limiting during tests so functional assertions are
# deterministic (account-lockout is a separate mechanism and is tested directly).
_NO_THROTTLE = {
    **dj_settings.REST_FRAMEWORK,
    'DEFAULT_THROTTLE_RATES': {'anon': None, 'user': None, 'auth': None, 'login': None},
}

STRONG_PW = 'Testpass123!'


@override_settings(REST_FRAMEWORK=_NO_THROTTLE)
class AuthenticationFlowTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_register_creates_user_and_returns_tokens(self):
        resp = self.client.post('/api/auth/register/', {
            'email': 'newuser@example.com', 'first_name': 'New', 'last_name': 'User',
            'password': STRONG_PW, 'password_confirm': STRONG_PW,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', resp.data)
        self.assertIn('access', resp.data['tokens'])
        self.assertIn('refresh', resp.data['tokens'])

    def test_password_is_argon2_hashed(self):
        self.client.post('/api/auth/register/', {
            'email': 'argon@example.com', 'first_name': 'A', 'last_name': 'B',
            'password': STRONG_PW, 'password_confirm': STRONG_PW,
        }, format='json')
        user = User.objects.get(email='argon@example.com')
        # Argon2 is the preferred hasher (OWASP A02) — verify it was used.
        self.assertTrue(user.password.startswith('argon2'))
        self.assertTrue(user.check_password(STRONG_PW))

    def test_register_rejects_password_mismatch(self):
        resp = self.client.post('/api/auth/register/', {
            'email': 'mismatch@example.com', 'first_name': 'M', 'last_name': 'M',
            'password': STRONG_PW, 'password_confirm': 'Different123!',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(email='dupe@example.com', password=STRONG_PW,
                                 first_name='D', last_name='U')
        resp = self.client.post('/api/auth/register/', {
            'email': 'dupe@example.com', 'first_name': 'D', 'last_name': 'U',
            'password': STRONG_PW, 'password_confirm': STRONG_PW,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_issues_jwt(self):
        User.objects.create_user(email='login@example.com', password=STRONG_PW,
                                 first_name='L', last_name='I')
        resp = self.client.post('/api/auth/login/',
                                {'email': 'login@example.com', 'password': STRONG_PW},
                                format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_login_wrong_password_increments_failure_counter(self):
        user = User.objects.create_user(email='wrong@example.com', password=STRONG_PW,
                                        first_name='W', last_name='P')
        resp = self.client.post('/api/auth/login/',
                                {'email': 'wrong@example.com', 'password': 'BadPass123!'},
                                format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        user.refresh_from_db()
        self.assertEqual(user.failed_login_count, 1)

    def test_account_locks_after_five_failed_attempts(self):
        user = User.objects.create_user(email='lock@example.com', password=STRONG_PW,
                                        first_name='L', last_name='K')
        for _ in range(5):
            self.client.post('/api/auth/login/',
                             {'email': 'lock@example.com', 'password': 'BadPass123!'},
                             format='json')
        user.refresh_from_db()
        self.assertEqual(user.failed_login_count, 5)
        self.assertIsNotNone(user.lockout_until)
        self.assertTrue(user.is_locked_out())
        # A further attempt — even with the correct password — is blocked (HTTP 429).
        resp = self.client.post('/api/auth/login/',
                                {'email': 'lock@example.com', 'password': STRONG_PW},
                                format='json')
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_profile_requires_authentication(self):
        resp = self.client.get('/api/auth/profile/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_read_profile(self):
        resp = self.client.post('/api/auth/register/', {
            'email': 'me@example.com', 'first_name': 'Me', 'last_name': 'You',
            'password': STRONG_PW, 'password_confirm': STRONG_PW,
        }, format='json')
        access = resp.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        prof = self.client.get('/api/auth/profile/')
        self.assertEqual(prof.status_code, status.HTTP_200_OK)
        self.assertEqual(prof.data['email'], 'me@example.com')

    def test_logout_blacklists_refresh_token(self):
        resp = self.client.post('/api/auth/register/', {
            'email': 'out@example.com', 'first_name': 'O', 'last_name': 'U',
            'password': STRONG_PW, 'password_confirm': STRONG_PW,
        }, format='json')
        access = resp.data['tokens']['access']
        refresh = resp.data['tokens']['refresh']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        logout = self.client.post('/api/auth/logout/', {'refresh': refresh}, format='json')
        self.assertEqual(logout.status_code, status.HTTP_200_OK)
        # The blacklisted refresh token can no longer be used.
        self.client.credentials()
        refreshed = self.client.post('/api/auth/token/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(refreshed.status_code, status.HTTP_401_UNAUTHORIZED)
