from rest_framework import serializers
from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source='child.name', read_only=True)
    activity_log_id = serializers.UUIDField(source='activity_log.id', read_only=True, allow_null=True)

    class Meta:
        model = Alert
        fields = (
            'id', 'child', 'child_name', 'activity_log_id', 'alert_type',
            'severity', 'title', 'message', 'is_read', 'created_at'
        )
        read_only_fields = ('id', 'child_name', 'activity_log_id', 'created_at')
