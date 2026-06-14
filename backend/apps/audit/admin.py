from django.contrib import admin
from .models import AccessLog


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user_email', 'action', 'result', 'http_method', 'path', 'ip_address', 'status_code']
    list_filter = ['result', 'action', 'http_method']
    search_fields = ['user_email', 'action', 'path', 'ip_address']
    date_hierarchy = 'timestamp'
    readonly_fields = [f.name for f in AccessLog._meta.get_fields() if hasattr(f, 'name')]
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
