from django.contrib import admin
from .models import Permission, Role, RolePermission, UserRole


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['codename', 'name', 'resource', 'action']
    search_fields = ['codename', 'name']
    list_filter = ['resource']


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']
    inlines = [RolePermissionInline]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'assigned_at', 'assigned_by']
    search_fields = ['user__email', 'role__name']
    list_filter = ['role']
