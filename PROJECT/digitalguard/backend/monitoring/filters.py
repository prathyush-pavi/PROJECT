"""
Activity log filters for DRF filter backend.
"""

import django_filters
from .models import ActivityLog


class ActivityLogFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name='timestamp', lookup_expr='date__gte')
    end_date = django_filters.DateFilter(field_name='timestamp', lookup_expr='date__lte')
    event_type = django_filters.CharFilter(field_name='event_type', lookup_expr='exact')
    severity = django_filters.CharFilter(field_name='severity', lookup_expr='exact')
    domain = django_filters.CharFilter(field_name='domain', lookup_expr='icontains')
    app_name = django_filters.CharFilter(field_name='app_name', lookup_expr='icontains')
    category = django_filters.CharFilter(field_name='category', lookup_expr='icontains')
    action_taken = django_filters.CharFilter(field_name='action_taken', lookup_expr='exact')

    class Meta:
        model = ActivityLog
        fields = ['event_type', 'severity', 'domain', 'app_name', 'category', 'action_taken']
