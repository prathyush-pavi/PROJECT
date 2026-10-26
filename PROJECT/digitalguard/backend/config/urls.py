from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def api_root(request):
    """API root — health check endpoint."""
    return JsonResponse({
        'success': True,
        'data': {'service': 'DigitalGuard API', 'version': '1.0.0'},
        'message': 'DigitalGuard API is running.'
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api_root, name='api-root'),

    # Authentication & Accounts
    path('api/', include('accounts.urls')),

    # Core resources
    path('api/', include('monitoring.urls')),
    path('api/', include('policies.urls')),
    path('api/', include('alerts.urls')),
    path('api/', include('reports.urls')),
    path('api/', include('ai_engine.urls')),
]
