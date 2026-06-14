"""
Custom DRF permission classes that enforce RBAC based on aggregated role permissions.
"""
from rest_framework.permissions import BasePermission, IsAuthenticated


class HasRBACPermission(BasePermission):
    """
    Generic RBAC permission checker.
    Usage: set `required_permission = 'resource.action'` on the view.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        required = getattr(view, 'required_permission', None)
        if not required:
            return True  # No specific permission required
        return request.user.has_rbac_permission(required)


def rbac_permission(codename: str):
    """
    Factory that returns a DRF permission class requiring a specific codename.
    Usage: permission_classes = [rbac_permission('users.create')]
    """
    class _DynamicRBACPermission(BasePermission):
        _codename = codename

        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            return request.user.has_rbac_permission(self._codename)

        def has_object_permission(self, request, view, obj):
            return self.has_permission(request, view)

    _DynamicRBACPermission.__name__ = f'RBACPermission_{codename.replace(".", "_")}'
    return _DynamicRBACPermission


# Convenience permission classes for common endpoints
class CanCreateUsers(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_rbac_permission('users.create')


class CanReadUsers(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_rbac_permission('users.read')


class CanUpdateUsers(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_rbac_permission('users.update')


class CanDeleteUsers(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_rbac_permission('users.delete')


class CanManageRoles(BasePermission):
    def has_permission(self, request, view):
        from rest_framework.permissions import SAFE_METHODS
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return request.user.has_rbac_permission('roles.read')
        return request.user.has_rbac_permission('roles.create') or \
               request.user.has_rbac_permission('roles.update') or \
               request.user.has_rbac_permission('roles.delete')


class CanReadAuditLogs(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_rbac_permission('audit.read')


class CanExportAuditLogs(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_rbac_permission('audit.export')


class CanViewReports(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_rbac_permission('reports.view')
