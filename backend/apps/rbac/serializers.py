from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Permission, Role, RolePermission, UserRole

User = get_user_model()


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'resource', 'action', 'managed']
        read_only_fields = ['id', 'managed']


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='permissions',
    )
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions', 'permission_ids', 'user_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_user_count(self, obj):
        return obj.user_roles.count()

    def create(self, validated_data):
        permissions = validated_data.pop('permissions', [])
        role = Role.objects.create(**validated_data)
        for perm in permissions:
            RolePermission.objects.get_or_create(role=role, permission=perm)
        return role

    def update(self, instance, validated_data):
        permissions = validated_data.pop('permissions', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if permissions is not None:
            RolePermission.objects.filter(role=instance).delete()
            for perm in permissions:
                RolePermission.objects.get_or_create(role=instance, permission=perm)
        return instance


class UserRoleSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = UserRole
        fields = ['id', 'role', 'role_name', 'assigned_at', 'assigned_by']
        read_only_fields = ['id', 'assigned_at']


class AdminUserListSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'is_active', 'is_staff', 'date_joined', 'last_login',
            'failed_login_count', 'lockout_until', 'roles',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'failed_login_count', 'lockout_until']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_roles(self, obj):
        return list(
            UserRole.objects.filter(user=obj)
            .select_related('role')
            .values('role__id', 'role__name')
        )


class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role_ids = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), many=True, write_only=True, required=False
    )

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'password', 'role_ids']
        read_only_fields = ['id']

    def create(self, validated_data):
        role_ids = validated_data.pop('role_ids', [])
        user = User.objects.create_user(**validated_data)
        for role in role_ids:
            UserRole.objects.get_or_create(
                user=user, role=role,
                defaults={'assigned_by': self.context['request'].user}
            )
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'is_active', 'is_staff']


class AssignRolesSerializer(serializers.Serializer):
    role_ids = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), many=True
    )
    replace = serializers.BooleanField(default=False)
