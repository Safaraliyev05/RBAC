from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if not extra_fields.get('is_staff'):
            raise ValueError('Superuser must have is_staff=True.')
        if not extra_fields.get('is_superuser'):
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # Account lockout fields
    failed_login_count = models.PositiveIntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True, db_index=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'accounts_user'
        ordering = ['-date_joined']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email

    def is_locked_out(self):
        if self.lockout_until and timezone.now() < self.lockout_until:
            return True
        if self.lockout_until and timezone.now() >= self.lockout_until:
            # Auto-unlock when lockout expires
            self.lockout_until = None
            self.failed_login_count = 0
            self.save(update_fields=['lockout_until', 'failed_login_count'])
        return False

    def record_failed_login(self, max_attempts: int, lockout_duration_minutes: int):
        from datetime import timedelta
        self.failed_login_count += 1
        if self.failed_login_count >= max_attempts:
            self.lockout_until = timezone.now() + timedelta(minutes=lockout_duration_minutes)
        self.save(update_fields=['failed_login_count', 'lockout_until'])

    def record_successful_login(self, ip_address: str = None):
        self.failed_login_count = 0
        self.lockout_until = None
        if ip_address:
            self.last_login_ip = ip_address
        self.save(update_fields=['failed_login_count', 'lockout_until', 'last_login_ip'])

    def get_all_permissions_codenames(self):
        """Return a set of all permission codenames from all assigned roles."""
        from apps.rbac.models import UserRole
        role_ids = UserRole.objects.filter(user_id=self.pk).values_list('role_id', flat=True)
        from apps.rbac.models import RolePermission, Permission
        perm_ids = RolePermission.objects.filter(role_id__in=role_ids).values_list('permission_id', flat=True)
        return set(Permission.objects.filter(id__in=perm_ids).values_list('codename', flat=True))

    def has_rbac_permission(self, codename: str) -> bool:
        if self.is_superuser:
            return True
        return codename in self.get_all_permissions_codenames()
