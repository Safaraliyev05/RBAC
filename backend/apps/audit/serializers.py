from rest_framework import serializers
from .models import AccessLog


class AccessLogSerializer(serializers.ModelSerializer):
    user_display = serializers.SerializerMethodField()

    class Meta:
        model = AccessLog
        fields = [
            'id', 'user', 'user_display', 'user_email', 'timestamp',
            'ip_address', 'http_method', 'path', 'action', 'resource',
            'result', 'status_code', 'details',
        ]
        read_only_fields = fields

    def get_user_display(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return obj.user_email or 'Anonymous'
