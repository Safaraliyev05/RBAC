from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.utils import log_authz_event
from .models import Permission, Role, UserRole
from .permissions import (
    CanCreateUsers, CanReadUsers, CanUpdateUsers, CanDeleteUsers,
    CanManageRoles, rbac_permission,
)
from .serializers import (
    PermissionSerializer,
    RoleSerializer,
    AdminUserListSerializer,
    AdminUserCreateSerializer,
    AdminUserUpdateSerializer,
    AssignRolesSerializer,
    UserRoleSerializer,
)

User = get_user_model()


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve permissions (Admin and Auditor)."""
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, rbac_permission('permissions.read')]
    queryset = Permission.objects.all().order_by('resource', 'action')
    search_fields = ['codename', 'name', 'resource']
    ordering_fields = ['codename', 'resource', 'action']
    filterset_fields = ['resource', 'action', 'managed']

    @action(
        detail=False,
        methods=['post'],
        url_path='sync',
        permission_classes=[IsAuthenticated, rbac_permission('permissions.sync')],
    )
    def sync(self, request):
        """Discover models and (re)generate permissions. Admin only."""
        from .permission_sync import sync_permissions
        prune = bool(request.data.get('prune', False))
        stats = sync_permissions(prune=prune)
        log_authz_event(
            request, action='permissions.sync', resource='permissions',
            result='success', details=str(stats),
        )
        return Response(stats)


class RoleViewSet(viewsets.ModelViewSet):
    """CRUD for roles. List/retrieve: Admins and Auditors. Create/update/delete: Admin only."""
    serializer_class = RoleSerializer
    queryset = Role.objects.prefetch_related('permissions').all()
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), rbac_permission('roles.read')()]
        elif self.action == 'create':
            return [IsAuthenticated(), rbac_permission('roles.create')()]
        elif self.action in ('update', 'partial_update'):
            return [IsAuthenticated(), rbac_permission('roles.update')()]
        elif self.action == 'destroy':
            return [IsAuthenticated(), rbac_permission('roles.delete')()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        role = serializer.save()
        log_authz_event(self.request, action='roles.create', resource=f'role:{role.id}', result='success')

    def perform_update(self, serializer):
        role = serializer.save()
        log_authz_event(self.request, action='roles.update', resource=f'role:{role.id}', result='success')

    def perform_destroy(self, instance):
        role_id = instance.id
        instance.delete()
        log_authz_event(self.request, action='roles.delete', resource=f'role:{role_id}', result='success')


class AdminUserViewSet(viewsets.ModelViewSet):
    """Admin CRUD for users and role assignments."""
    queryset = User.objects.all().order_by('-date_joined')
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['email', 'date_joined', 'last_login']
    filterset_fields = ['is_active', 'is_staff']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated(), rbac_permission('users.read')()]
        elif self.action == 'create':
            return [IsAuthenticated(), rbac_permission('users.create')()]
        elif self.action in ('update', 'partial_update'):
            return [IsAuthenticated(), rbac_permission('users.update')()]
        elif self.action == 'destroy':
            return [IsAuthenticated(), rbac_permission('users.delete')()]
        elif self.action == 'assign_roles':
            return [IsAuthenticated(), rbac_permission('roles.update')()]
        elif self.action == 'user_roles':
            return [IsAuthenticated(), rbac_permission('users.read')()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminUserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return AdminUserUpdateSerializer
        if self.action == 'assign_roles':
            return AssignRolesSerializer
        if self.action == 'user_roles':
            return UserRoleSerializer
        return AdminUserListSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        log_authz_event(self.request, action='users.create', resource=f'user:{user.id}', result='success')

    def perform_update(self, serializer):
        user = serializer.save()
        log_authz_event(self.request, action='users.update', resource=f'user:{user.id}', result='success')

    def perform_destroy(self, instance):
        user_id = instance.id
        instance.delete()
        log_authz_event(self.request, action='users.delete', resource=f'user:{user_id}', result='success')

    @action(detail=True, methods=['post'], url_path='assign-roles')
    def assign_roles(self, request, pk=None):
        user = self.get_object()
        serializer = AssignRolesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        roles = serializer.validated_data['role_ids']
        replace = serializer.validated_data['replace']

        if replace:
            UserRole.objects.filter(user=user).delete()

        assigned = []
        for role in roles:
            obj, created = UserRole.objects.get_or_create(
                user=user, role=role,
                defaults={'assigned_by': request.user}
            )
            if created:
                assigned.append(role.name)

        log_authz_event(
            request, action='roles.assign',
            resource=f'user:{user.id}',
            result='success',
            details=f'Roles assigned: {assigned}',
        )
        return Response({'detail': 'Roles updated.', 'assigned': assigned})

    @action(detail=True, methods=['get'], url_path='roles')
    def user_roles(self, request, pk=None):
        user = self.get_object()
        qs = UserRole.objects.filter(user=user).select_related('role', 'assigned_by')
        serializer = UserRoleSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], url_path='roles/(?P<role_id>[^/.]+)/remove')
    def remove_role(self, request, pk=None, role_id=None):
        if not request.user.has_rbac_permission('roles.update'):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        deleted, _ = UserRole.objects.filter(user=user, role_id=role_id).delete()
        if not deleted:
            return Response({'detail': 'Role not assigned to user.'}, status=status.HTTP_404_NOT_FOUND)
        log_authz_event(request, action='roles.remove', resource=f'user:{user.id}', result='success',
                        details=f'Role {role_id} removed from user {user.id}')
        return Response({'detail': 'Role removed.'})
