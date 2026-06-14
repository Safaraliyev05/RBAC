import django_filters
from .models import AccessLog


class AccessLogFilter(django_filters.FilterSet):
    user_email = django_filters.CharFilter(field_name='user_email', lookup_expr='icontains')
    user_id = django_filters.NumberFilter(field_name='user__id')
    action = django_filters.CharFilter(lookup_expr='icontains')
    result = django_filters.ChoiceFilter(choices=AccessLog.RESULT_CHOICES)
    http_method = django_filters.CharFilter(lookup_expr='iexact')
    path = django_filters.CharFilter(lookup_expr='icontains')
    ip_address = django_filters.CharFilter(lookup_expr='icontains')
    date_from = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')
    resource = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = AccessLog
        fields = [
            'user_email', 'user_id', 'action', 'result',
            'http_method', 'path', 'ip_address', 'date_from', 'date_to', 'resource',
        ]
