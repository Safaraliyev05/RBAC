from django.urls import path
from .views import (
    AccessLogListView,
    AccessLogExportView,
    AuditSummaryReportView,
    LoginFailuresReportView,
)

urlpatterns = [
    path('logs/', AccessLogListView.as_view(), name='audit-logs'),
    path('logs/export/', AccessLogExportView.as_view(), name='audit-logs-export'),
    path('reports/summary/', AuditSummaryReportView.as_view(), name='audit-report-summary'),
    path('reports/login-failures/', LoginFailuresReportView.as_view(), name='audit-report-login-failures'),
]
