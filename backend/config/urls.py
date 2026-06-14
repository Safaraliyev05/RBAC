from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include


def health(_request):
    """Liveness/readiness probe endpoint (unauthenticated)."""
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health, name='health'),
    # Prometheus metrics at /metrics (scraped by the ServiceMonitor).
    path('', include('django_prometheus.urls')),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/rbac/', include('apps.rbac.urls')),
    path('api/audit/', include('apps.audit.urls')),
]
