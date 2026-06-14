from django.conf import settings
from django.db import models


class Permission(models.Model):
    """Granular permission: resource.action (e.g. users.create).

    Permissions are either *managed* (auto-generated from a Django model by the
    discovery engine in ``permission_sync``) or *custom* (hand-defined, e.g. the
    RBAC management permissions such as ``users.create`` or ``audit.export``).
    """
    codename = models.CharField(max_length=150, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    resource = models.CharField(max_length=120, db_index=True)
    action = models.CharField(max_length=50, db_index=True)
    # Auto-generated from a model by the discovery engine. Only managed
    # permissions are ever pruned; custom ones are left untouched.
    managed = models.BooleanField(default=False, db_index=True)
    # The model this permission was generated from (null for custom permissions).
    content_type = models.ForeignKey(
        'contenttypes.ContentType',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='rbac_permissions',
    )

    class Meta:
        db_table = 'rbac_permission'
        ordering = ['resource', 'action']
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'

    def __str__(self):
        return f'{self.codename} — {self.name}'


class Role(models.Model):
    """Named role with a set of permissions."""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        Permission,
        through='RolePermission',
        related_name='roles',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rbac_role'
        ordering = ['name']
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """Through table: Role ↔ Permission."""
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions', db_index=True)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_permissions', db_index=True)
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rbac_role_permission'
        unique_together = [('role', 'permission')]
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'

    def __str__(self):
        return f'{self.role.name} → {self.permission.codename}'


class UserRole(models.Model):
    """Through table: User ↔ Role."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_roles',
        db_index=True,
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles', db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='role_assignments_made',
    )

    class Meta:
        db_table = 'rbac_user_role'
        unique_together = [('user', 'role')]
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'

    def __str__(self):
        return f'{self.user} → {self.role.name}'
