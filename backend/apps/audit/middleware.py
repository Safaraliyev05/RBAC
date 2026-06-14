"""
AuditMiddleware: records every authenticated API request to AccessLog.
Auth events (login/logout/register) are logged explicitly in views.
This middleware focuses on logging resource access and authz denials.
"""
import json
from .models import AccessLog


AUTH_PATHS = {'/api/auth/login/', '/api/auth/logout/', '/api/auth/register/', '/api/auth/token/refresh/'}
SKIP_PATHS = {'/admin/', '/api/auth/'}


def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _should_skip(path: str) -> bool:
    """Skip logging for auth endpoints (handled by views) and admin."""
    for skip in SKIP_PATHS:
        if path.startswith(skip):
            return True
    return False


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only log authenticated API requests to non-auth paths
        if not request.path.startswith('/api/'):
            return response
        if _should_skip(request.path):
            return response

        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            result = AccessLog.RESULT_SUCCESS
            if response.status_code == 403:
                result = AccessLog.RESULT_DENIED
            elif response.status_code >= 400:
                result = AccessLog.RESULT_FAILURE

            # Extract action and resource from path
            action, resource = _extract_action_resource(request.method, request.path)

            try:
                AccessLog.objects.create(
                    user=user,
                    user_email=user.email,
                    ip_address=_get_ip(request),
                    http_method=request.method,
                    path=request.path,
                    action=action,
                    resource=resource,
                    result=result,
                    status_code=response.status_code,
                    details='',
                )
            except Exception:
                pass  # Never let audit logging break the response

        return response


def _extract_action_resource(method: str, path: str) -> tuple[str, str]:
    """Infer action and resource from HTTP method and URL path."""
    parts = [p for p in path.strip('/').split('/') if p]
    # e.g. ['api', 'rbac', 'users', '42', 'assign-roles']
    method_action_map = {
        'GET': 'read',
        'POST': 'create',
        'PUT': 'update',
        'PATCH': 'update',
        'DELETE': 'delete',
    }
    action_suffix = method_action_map.get(method, method.lower())

    if len(parts) >= 3:
        resource_type = parts[2]  # e.g. 'users', 'roles'
        if len(parts) >= 4:
            resource_id = parts[3]
            # Check for sub-action
            if len(parts) >= 5:
                sub_action = parts[4]
                return f'{resource_type}.{sub_action}', f'{resource_type[:-1]}:{resource_id}'
            return f'{resource_type}.{action_suffix}', f'{resource_type[:-1]}:{resource_id}'
        return f'{resource_type}.{action_suffix}', resource_type
    return f'api.{action_suffix}', path
