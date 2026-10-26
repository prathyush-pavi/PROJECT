"""
Policies serializers.
"""

from rest_framework import serializers
from .models import WebsitePolicy, ApplicationPolicy, ScreenTimePolicy


class WebsitePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsitePolicy
        fields = (
            'id', 'child', 'domain', 'category', 'rule_type',
            'reason', 'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, attrs):
        domain = attrs.get('domain', '')
        category = attrs.get('category', '')
        if not domain and not category:
            raise serializers.ValidationError('Either domain or category must be specified.')
        if domain and category:
            raise serializers.ValidationError('Specify either domain OR category, not both.')
        return attrs

    def validate_child(self, value):
        """Ensure parent can only create policies for their own children."""
        request = self.context.get('request')
        if value and request and hasattr(request.user, 'parent_profile'):
            if value.parent != request.user.parent_profile:
                raise serializers.ValidationError('You can only create policies for your own children.')
        return value


class ApplicationPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationPolicy
        fields = (
            'id', 'child', 'app_name', 'policy', 'daily_limit_minutes',
            'reason', 'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, attrs):
        policy = attrs.get('policy')
        limit = attrs.get('daily_limit_minutes')
        if policy == 'LIMITED' and not limit:
            raise serializers.ValidationError(
                'daily_limit_minutes is required when policy is LIMITED.'
            )
        return attrs


class ScreenTimePolicySerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source='child.name', read_only=True)

    class Meta:
        model = ScreenTimePolicy
        fields = (
            'id', 'child', 'child_name', 'daily_limit_minutes', 'weekend_limit_minutes',
            'allowed_start', 'allowed_end', 'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'child_name', 'created_at', 'updated_at')

    def validate_child(self, value):
        request = self.context.get('request')
        if request and hasattr(request.user, 'parent_profile'):
            if value.parent != request.user.parent_profile:
                raise serializers.ValidationError('You can only set policies for your own children.')
        return value
