import csv
from datetime import datetime, timedelta

from django.db.models import Count, Q
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rbac.permissions import CanReadAuditLogs, CanExportAuditLogs, CanViewReports
from .filters import AccessLogFilter
from .models import AccessLog
from .serializers import AccessLogSerializer


class AccessLogListView(generics.ListAPIView):
    """
    List audit logs with filtering. Restricted to Admin and Auditor.
    GET /api/audit/logs/
    Filters: user_email, user_id, action, result, http_method, path, ip_address, date_from, date_to, resource
    """
    serializer_class = AccessLogSerializer
    permission_classes = [IsAuthenticated, CanReadAuditLogs]
    filterset_class = AccessLogFilter
    search_fields = ['user_email', 'action', 'path', 'resource', 'details']
    ordering_fields = ['timestamp', 'action', 'result', 'user_email']
    ordering = ['-timestamp']

    def get_queryset(self):
        return AccessLog.objects.select_related('user').all()


class _Echo:
    """Minimal write-capable object used for streaming CSV."""
    def write(self, value):
        return value


class AccessLogExportView(APIView):
    """
    Stream all filtered audit logs as CSV.
    GET /api/audit/logs/export/
    """
    permission_classes = [IsAuthenticated, CanExportAuditLogs]

    def get(self, request):
        filterset = AccessLogFilter(request.GET, queryset=AccessLog.objects.select_related('user').all())
        qs = filterset.qs.order_by('-timestamp')

        columns = [
            'id', 'timestamp', 'user_email', 'ip_address',
            'http_method', 'path', 'action', 'resource', 'result', 'status_code', 'details',
        ]

        def row_gen(queryset):
            writer = csv.writer(_Echo())
            yield writer.writerow(columns)
            for log in queryset.iterator(chunk_size=500):
                yield writer.writerow([
                    log.id,
                    log.timestamp.isoformat() if log.timestamp else '',
                    log.user_email,
                    log.ip_address or '',
                    log.http_method,
                    log.path,
                    log.action,
                    log.resource,
                    log.result,
                    log.status_code or '',
                    log.details,
                ])

        filename = f'audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response = StreamingHttpResponse(row_gen(qs), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class AuditSummaryReportView(APIView):
    """
    Summary statistics report.
    GET /api/audit/reports/summary/
    Optional query params: days (default 30)
    """
    permission_classes = [IsAuthenticated, CanViewReports]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        qs = AccessLog.objects.filter(timestamp__gte=since)

        total = qs.count()
        by_result = dict(qs.values_list('result').annotate(count=Count('id')).values_list('result', 'count'))
        by_action = list(
            qs.values('action').annotate(count=Count('id')).order_by('-count')[:10]
        )
        denied_by_user = list(
            qs.filter(result=AccessLog.RESULT_DENIED)
            .values('user_email').annotate(count=Count('id')).order_by('-count')[:10]
        )
        login_failures_by_day = list(
            qs.filter(action='login', result=AccessLog.RESULT_FAILURE)
            .extra(select={'day': "date(timestamp)"})
            .values('day').annotate(count=Count('id')).order_by('day')
        )
        top_ips = list(
            qs.filter(result__in=[AccessLog.RESULT_FAILURE, AccessLog.RESULT_DENIED])
            .values('ip_address').annotate(count=Count('id')).order_by('-count')[:10]
        )

        return Response({
            'period_days': days,
            'since': since.isoformat(),
            'total_events': total,
            'by_result': by_result,
            'top_actions': by_action,
            'denied_access_by_user': denied_by_user,
            'login_failures_by_day': login_failures_by_day,
            'top_suspicious_ips': top_ips,
        })


class LoginFailuresReportView(APIView):
    """
    Detailed login failure report.
    GET /api/audit/reports/login-failures/
    """
    permission_classes = [IsAuthenticated, CanViewReports]

    def get(self, request):
        days = int(request.query_params.get('days', 7))
        since = timezone.now() - timedelta(days=days)

        failures = (
            AccessLog.objects
            .filter(action='login', result__in=['failure', 'locked'], timestamp__gte=since)
            .order_by('-timestamp')[:200]
        )
        serializer = AccessLogSerializer(failures, many=True)

        summary = (
            AccessLog.objects
            .filter(action='login', result__in=['failure', 'locked'], timestamp__gte=since)
            .values('user_email').annotate(count=Count('id')).order_by('-count')[:20]
        )

        return Response({
            'period_days': days,
            'since': since.isoformat(),
            'recent_failures': serializer.data,
            'failures_by_user': list(summary),
        })
