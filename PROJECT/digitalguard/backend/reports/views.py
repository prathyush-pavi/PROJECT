"""
Reports views — generate and retrieve activity/threat reports.
"""

from datetime import date, timedelta
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework import serializers

from accounts.permissions import IsParent
from api.utils import success_response, error_response
from monitoring.models import ActivityLog, ScreenTimeUsage, ThreatEvent
from alerts.models import Alert
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ('id', 'child', 'report_type', 'period_start', 'period_end', 'data', 'created_at')
        read_only_fields = ('id', 'data', 'created_at')


class ReportListCreateView(generics.ListCreateAPIView):
    """
    GET /api/reports/ — list existing reports.
    POST /api/reports/ — generate a new report.
    """
    permission_classes = [IsParent]
    serializer_class = ReportSerializer

    def get_queryset(self):
        return Report.objects.filter(parent=self.request.user.parent_profile)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(success_response(serializer.data))

    def create(self, request, *args, **kwargs):
        parent = request.user.parent_profile
        report_type = request.data.get('report_type', 'WEEKLY')
        child_id = request.data.get('child_id')

        # Determine date range
        today = date.today()
        if report_type == 'WEEKLY':
            start = today - timedelta(days=7)
            end = today
        elif report_type == 'MONTHLY':
            start = today.replace(day=1)
            end = today
        else:
            start = date.fromisoformat(request.data.get('period_start', str(today - timedelta(days=7))))
            end = date.fromisoformat(request.data.get('period_end', str(today)))

        # Build the report data
        data = _generate_report_data(parent, child_id, start, end)

        report = Report.objects.create(
            parent=parent,
            child_id=child_id,
            report_type=report_type,
            period_start=start,
            period_end=end,
            data=data,
        )
        serializer = self.get_serializer(report)
        return Response(success_response(serializer.data, 'Report generated.'), status=status.HTTP_201_CREATED)


def _generate_report_data(parent, child_id, start, end):
    """Compute the report summary for a given date range."""
    base_qs = ActivityLog.objects.filter(
        device__child__parent=parent,
        timestamp__date__gte=start,
        timestamp__date__lte=end,
    )
    if child_id:
        base_qs = base_qs.filter(device__child_id=child_id)

    threat_types = [
        ActivityLog.PHISHING_DETECTED,
        ActivityLog.CYBERBULLYING_DETECTED,
        ActivityLog.GROOMING_RISK_DETECTED,
        ActivityLog.CONTENT_FLAGGED,
    ]

    return {
        'period': {'start': str(start), 'end': str(end)},
        'activity_summary': {
            'total_events': base_qs.count(),
            'websites_visited': base_qs.filter(event_type=ActivityLog.WEBSITE_VISITED).count(),
            'websites_blocked': base_qs.filter(event_type=ActivityLog.WEBSITE_BLOCKED).count(),
            'apps_blocked': base_qs.filter(event_type=ActivityLog.APPLICATION_BLOCKED).count(),
        },
        'threat_summary': {
            'total_threats': base_qs.filter(event_type__in=threat_types).count(),
            'phishing': base_qs.filter(event_type=ActivityLog.PHISHING_DETECTED).count(),
            'cyberbullying': base_qs.filter(event_type=ActivityLog.CYBERBULLYING_DETECTED).count(),
            'grooming_risk': base_qs.filter(event_type=ActivityLog.GROOMING_RISK_DETECTED).count(),
            'harmful_content': base_qs.filter(event_type=ActivityLog.CONTENT_FLAGGED).count(),
        },
        'screen_time': {
            'total_minutes': sum(
                u.total_minutes for u in ScreenTimeUsage.objects.filter(
                    device__child__parent=parent,
                    date__gte=start, date__lte=end
                )
            ),
        },
        'top_domains': list(
            base_qs.values('domain').annotate(
                count=__import__('django.db.models', fromlist=['Count']).Count('id')
            ).order_by('-count')[:10]
        ),
        'severity_breakdown': {
            'low': base_qs.filter(severity='LOW').count(),
            'medium': base_qs.filter(severity='MEDIUM').count(),
            'high': base_qs.filter(severity='HIGH').count(),
            'critical': base_qs.filter(severity='CRITICAL').count(),
        },
    }
