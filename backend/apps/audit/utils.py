"""Utility functions for creating audit log entries."""
from .models import AccessLog


def _get_ip(request, ip_override=None):
    if ip_override:
        return ip_override
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def log_auth_event(request, user, action: str, result: str, details: str = '', ip_override=None):
    """Log authentication-related events (login, logout, register, lockout)."""
    email = ''
    if user:
        email = user.email
    elif hasattr(request, 'data'):
        email = request.data.get('email', '')

    AccessLog.objects.create(
        user=user,
        user_email=email,
        ip_address=_get_ip(request, ip_override),
        http_method=request.method,
        path=request.path,
        action=action,
        resource='auth',
        result=result,
        status_code=None,
        details=details,
    )


def log_authz_event(request, action: str, resource: str, result: str, details: str = ''):
    """Log authorization/resource-access events."""
    user = request.user if request.user.is_authenticated else None
    email = user.email if user else ''
    AccessLog.objects.create(
        user=user,
        user_email=email,
        ip_address=_get_ip(request),
        http_method=request.method,
        path=request.path,
        action=action,
        resource=resource,
        result=result,
        status_code=None,
        details=details,
    )
