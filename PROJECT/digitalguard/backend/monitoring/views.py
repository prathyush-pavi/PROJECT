"""
Monitoring views — activity logs, screen time, dashboard summary.
"""

import logging
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Count, Q, Sum
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from accounts.models import Device, ChildProfile
from accounts.permissions import IsParent, IsDeviceAuthenticated, IsParentOrDevice
from alerts.utils import create_alert_if_needed
from api.utils import success_response, error_response
from .models import ActivityLog, ScreenTimeUsage
from .serializers import (
    ActivityLogSerializer, ActivityLogIngestSerializer,
    ScreenTimeUsageSerializer, ScreenTimeIngestSerializer,
    DashboardSummarySerializer,
)
from .filters import ActivityLogFilter

logger = logging.getLogger('digitalguard.monitoring')


class ActivityLogListView(generics.ListAPIView):
    """
    GET /api/activity/
    List activity logs for all children of the authenticated parent.
    Supports filtering by date, event_type, severity, domain, app_name.
    """
    permission_classes = [IsParent]
    serializer_class = ActivityLogSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ActivityLogFilter
    search_fields = ['domain', 'app_name', 'category']
    ordering_fields = ['timestamp', 'severity', 'event_type']
    ordering = ['-timestamp']

    def get_queryset(self):
        parent = self.request.user.parent_profile
        child_id = self.request.query_params.get('child_id')
        device_id = self.request.query_params.get('device_id')

        qs = ActivityLog.objects.filter(
            device__child__parent=parent
        ).select_related('device__child', 'threat_event').order_by('-timestamp')

        if child_id:
            qs = qs.filter(device__child_id=child_id)
        if device_id:
            qs = qs.filter(device_id=device_id)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated = self.get_paginated_response(serializer.data)
            return Response(success_response(paginated.data))
        serializer = self.get_serializer(qs, many=True)
        return Response(success_response(serializer.data))


class ActivityLogDetailView(generics.RetrieveAPIView):
    """GET /api/activity/<id>/"""
    permission_classes = [IsParent]
    serializer_class = ActivityLogSerializer

    def get_queryset(self):
        return ActivityLog.objects.filter(
            device__child__parent=self.request.user.parent_profile
        ).select_related('device__child', 'threat_event')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(success_response(serializer.data))


class ActivityIngestView(generics.CreateAPIView):
    """
    POST /api/activity/ingest/
    Used by the desktop agent and browser extension to report events.
    Authenticated via DeviceToken.
    """
    permission_classes = [IsDeviceAuthenticated]
    serializer_class = ActivityLogIngestSerializer

    def create(self, request, *args, **kwargs):
        device = request.auth  # Set by DeviceTokenAuthentication
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

        # Create the activity log
        log = serializer.save(device=device)

        # Update device last_seen
        device.last_seen = timezone.now()
        device.save(update_fields=['last_seen', 'updated_at'])

        # Trigger alert creation if the event warrants it
        try:
            create_alert_if_needed(log)
        except Exception as e:
            logger.error('Alert creation failed for log %s: %s', log.id, str(e))

        logger.debug('Activity ingested: %s from device %s', log.event_type, device.name)
        return Response(
            success_response({'id': str(log.id)}, 'Event logged.'),
            status=status.HTTP_201_CREATED
        )


class ScreenTimeUsageListView(generics.ListAPIView):
    """
    GET /api/screentime/usage/?child_id=&start_date=&end_date=
    Screen time usage for the authenticated parent's children.
    """
    permission_classes = [IsParent]
    serializer_class = ScreenTimeUsageSerializer

    def get_queryset(self):
        parent = self.request.user.parent_profile
        child_id = self.request.query_params.get('child_id')
        start = self.request.query_params.get('start_date', str(date.today() - timedelta(days=7)))
        end = self.request.query_params.get('end_date', str(date.today()))

        qs = ScreenTimeUsage.objects.filter(
            device__child__parent=parent,
            date__gte=start,
            date__lte=end,
        ).select_related('device__child').order_by('-date')

        if child_id:
            qs = qs.filter(device__child_id=child_id)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response(success_response(serializer.data))


class ScreenTimeIngestView(generics.GenericAPIView):
    """
    POST /api/screentime/ingest/
    Desktop agent reports screen time updates.
    """
    permission_classes = [IsDeviceAuthenticated]
    serializer_class = ScreenTimeIngestSerializer

    def post(self, request):
        device = request.auth
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        usage, created = ScreenTimeUsage.objects.update_or_create(
            device=device,
            date=data['date'],
            defaults={
                'total_minutes': data['total_minutes'],
                'app_breakdown': data['app_breakdown'],
            }
        )

        # Check screen time policy
        _check_screen_time_policy(device, usage)

        return Response(success_response(
            {'total_minutes': usage.total_minutes, 'date': str(usage.date)},
            'Screen time updated.'
        ))


def _check_screen_time_policy(device, usage):
    """Check if screen time limit has been reached and create an alert."""
    try:
        from policies.models import ScreenTimePolicy
        policy = ScreenTimePolicy.objects.filter(child=device.child).first()
        if not policy:
            return

        limit = policy.daily_limit_minutes
        if limit and usage.total_minutes >= limit:
            # Create a SCREEN_TIME_LIMIT_REACHED activity log if not already created today
            existing = ActivityLog.objects.filter(
                device=device,
                event_type=ActivityLog.SCREEN_TIME_LIMIT_REACHED,
                timestamp__date=usage.date
            ).exists()
            if not existing:
                log = ActivityLog.objects.create(
                    device=device,
                    event_type=ActivityLog.SCREEN_TIME_LIMIT_REACHED,
                    timestamp=timezone.now(),
                    severity=ActivityLog.SEV_MEDIUM,
                    category='screen_time',
                    action_taken=ActivityLog.ACTION_WARN,
                    metadata={'daily_limit': limit, 'current_usage': usage.total_minutes},
                )
                create_alert_if_needed(log)
    except Exception as e:
        logger.error('Screen time policy check failed: %s', str(e))


@api_view(['GET'])
@permission_classes([IsParent])
def dashboard_summary(request):
    """
    GET /api/dashboard/summary/
    Returns aggregated stats for the dashboard home page.
    """
    parent = request.user.parent_profile
    today = date.today()

    # All activity logs for today across all of this parent's children
    today_logs = ActivityLog.objects.filter(
        device__child__parent=parent,
        timestamp__date=today
    )

    total_events = today_logs.count()
    websites_visited = today_logs.filter(event_type=ActivityLog.WEBSITE_VISITED).count()
    websites_blocked = today_logs.filter(event_type=ActivityLog.WEBSITE_BLOCKED).count()
    threats = today_logs.filter(
        event_type__in=[
            ActivityLog.PHISHING_DETECTED,
            ActivityLog.CYBERBULLYING_DETECTED,
            ActivityLog.GROOMING_RISK_DETECTED,
            ActivityLog.CONTENT_FLAGGED,
        ]
    ).count()

    # Screen time today
    screen_time = ScreenTimeUsage.objects.filter(
        device__child__parent=parent, date=today
    ).aggregate(total=Sum('total_minutes'))['total'] or 0

    # Unread alerts
    from alerts.models import Alert
    unread_alerts = Alert.objects.filter(parent=parent, is_read=False).count()

    # Children summary
    children = []
    for child in ChildProfile.objects.filter(parent=parent, is_active=True):
        child_logs_today = today_logs.filter(device__child=child)
        child_screen_time = ScreenTimeUsage.objects.filter(
            device__child=child, date=today
        ).aggregate(total=Sum('total_minutes'))['total'] or 0
        children.append({
            'id': child.id,
            'name': child.name,
            'avatar': child.avatar,
            'events_today': child_logs_today.count(),
            'threats_today': child_logs_today.filter(
                severity__in=[ActivityLog.SEV_HIGH, ActivityLog.SEV_CRITICAL]
            ).count(),
            'screen_time_today': child_screen_time,
        })

    # Recent events
    recent = today_logs.select_related('device__child', 'threat_event').order_by('-timestamp')[:10]
    recent_serialized = ActivityLogSerializer(recent, many=True).data

    return Response(success_response({
        'total_events_today': total_events,
        'websites_visited_today': websites_visited,
        'websites_blocked_today': websites_blocked,
        'threats_detected_today': threats,
        'screen_time_today_minutes': screen_time,
        'unread_alerts': unread_alerts,
        'children': children,
        'recent_events': recent_serialized,
    }))
