"""
Monitoring serializers — activity logs, threat events, screen time.
"""

from rest_framework import serializers
from .models import ActivityLog, ThreatEvent, AIAnalysis, ScreenTimeUsage


class ThreatEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThreatEvent
        fields = (
            'id', 'threat_type', 'risk_score', 'confidence',
            'ai_category', 'indicators', 'inference_mode', 'created_at'
        )
        read_only_fields = fields


class ActivityLogSerializer(serializers.ModelSerializer):
    threat_event = ThreatEventSerializer(read_only=True)
    child_name = serializers.CharField(source='device.child.name', read_only=True)
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = ActivityLog
        fields = (
            'id', 'device', 'device_name', 'child_name', 'event_type', 'timestamp',
            'severity', 'category', 'domain', 'url_path', 'app_name',
            'action_taken', 'metadata', 'threat_event', 'created_at'
        )
        read_only_fields = (
            'id', 'child_name', 'device_name', 'threat_event', 'created_at'
        )


class ActivityLogIngestSerializer(serializers.ModelSerializer):
    """
    Serializer for device-to-server activity ingestion.
    Used by the desktop agent / browser extension.
    """
    class Meta:
        model = ActivityLog
        fields = (
            'event_type', 'timestamp', 'severity', 'category',
            'domain', 'url_path', 'app_name', 'action_taken', 'metadata'
        )

    def validate_event_type(self, value):
        valid = [et[0] for et in ActivityLog.EVENT_TYPE_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(f'Invalid event_type. Valid values: {valid}')
        return value


class ScreenTimeUsageSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    child_name = serializers.CharField(source='device.child.name', read_only=True)

    class Meta:
        model = ScreenTimeUsage
        fields = ('id', 'device', 'device_name', 'child_name', 'date', 'total_minutes', 'app_breakdown', 'updated_at')
        read_only_fields = ('id', 'device_name', 'child_name', 'updated_at')


class ScreenTimeIngestSerializer(serializers.Serializer):
    """Used by desktop agent to push screen time updates."""
    date = serializers.DateField()
    total_minutes = serializers.IntegerField(min_value=0, max_value=1440)
    app_breakdown = serializers.DictField(
        child=serializers.IntegerField(min_value=0),
        allow_empty=True
    )


class DashboardSummarySerializer(serializers.Serializer):
    """Aggregated stats for the dashboard home page."""
    total_events_today = serializers.IntegerField()
    websites_visited_today = serializers.IntegerField()
    websites_blocked_today = serializers.IntegerField()
    threats_detected_today = serializers.IntegerField()
    screen_time_today_minutes = serializers.IntegerField()
    unread_alerts = serializers.IntegerField()
    children = serializers.ListField()
    recent_events = ActivityLogSerializer(many=True)
