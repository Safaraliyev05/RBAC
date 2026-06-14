from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.audit.utils import log_auth_event
from .serializers import (
    RegisterSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
)
from .throttles import LoginRateThrottle, RegisterRateThrottle

User = get_user_model()


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Assign default 'User' role on registration
        try:
            from apps.rbac.models import Role, UserRole
            user_role = Role.objects.filter(name='User').first()
            if user_role:
                UserRole.objects.get_or_create(user=user, role=user_role)
        except Exception:
            pass

        log_auth_event(
            request=request,
            user=user,
            action='register',
            result='success',
            details=f'New user registered: {user.email}',
        )

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').lower().strip()
        ip = _get_client_ip(request)

        # Pre-check: does user exist and is locked out?
        try:
            user = User.objects.get(email=email)
            if user.is_locked_out():
                log_auth_event(
                    request=request,
                    user=user,
                    action='login',
                    result='locked',
                    details=f'Login blocked — account locked until {user.lockout_until}',
                )
                return Response(
                    {'detail': f'Account locked due to too many failed attempts. Try again after {user.lockout_until}.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
        except User.DoesNotExist:
            user = None

        # Mutate request data to ensure email is lowercase
        data = request.data.copy()
        data['email'] = email

        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            # Record failed login
            if user:
                max_attempts = settings.ACCOUNT_LOCKOUT_ATTEMPTS
                lockout_duration = settings.ACCOUNT_LOCKOUT_DURATION_MINUTES
                user.record_failed_login(max_attempts, lockout_duration)
                locked_msg = ''
                if user.lockout_until:
                    locked_msg = f' Account locked until {user.lockout_until}.'
                log_auth_event(
                    request=request,
                    user=user,
                    action='login',
                    result='failure',
                    details=f'Invalid credentials. Attempt {user.failed_login_count}/{max_attempts}.{locked_msg}',
                )
            else:
                log_auth_event(
                    request=request,
                    user=None,
                    action='login',
                    result='failure',
                    details=f'Login attempt for unknown email: {email}',
                    ip_override=ip,
                )
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        validated_user = serializer.user
        validated_user.record_successful_login(ip_address=ip)

        log_auth_event(
            request=request,
            user=validated_user,
            action='login',
            result='success',
            details=f'Login successful from {ip}',
        )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            log_auth_event(
                request=request,
                user=request.user,
                action='logout',
                result='success',
                details='User logged out, refresh token blacklisted.',
            )
        except TokenError:
            return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UserProfileUpdateSerializer
        return UserProfileSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'old_password': 'Incorrect current password.'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        log_auth_event(
            request=request,
            user=user,
            action='password_change',
            result='success',
            details='Password changed successfully.',
        )
        return Response({'detail': 'Password changed successfully.'}, status=status.HTTP_200_OK)
