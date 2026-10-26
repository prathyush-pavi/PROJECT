"""
Accounts serializers — handles validation and transformation for
authentication, parent profiles, child profiles, and devices.
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, ParentProfile, ChildProfile, Device


class RegisterSerializer(serializers.ModelSerializer):
    """Parent user registration with password confirmation."""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=False, label='Confirm Password')
    display_name = serializers.CharField(required=True, max_length=100)

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'password2', 'display_name')

    def validate(self, attrs):
        if 'password2' in attrs and attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        display_name = validated_data.pop('display_name')
        validated_data.pop('password2', None)
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data.get('username', validated_data['email']),
            password=validated_data['password'],
            role=User.ROLE_PARENT,
        )
        # Auto-create parent profile
        ParentProfile.objects.create(
            user=user,
            display_name=display_name,
            notification_email=user.email,
            alert_preferences=ParentProfile().get_default_alert_preferences(),
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extended JWT token serializer — adds user info to token response."""
    def validate(self, attrs):
        data = super().validate(attrs)
        data['tokens'] = {
            'access': data.get('access'),
            'refresh': data.get('refresh'),
        }
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'role': self.user.role,
            'display_name': (
                self.user.parent_profile.display_name
                if hasattr(self.user, 'parent_profile') else self.user.username
            ),
        }
        return data


class ParentProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = ParentProfile
        fields = ('id', 'email', 'display_name', 'notification_email', 'alert_preferences', 'created_at')
        read_only_fields = ('id', 'email', 'created_at')


class ChildProfileSerializer(serializers.ModelSerializer):
    device_count = serializers.SerializerMethodField()

    class Meta:
        model = ChildProfile
        fields = ('id', 'name', 'age', 'avatar', 'is_active', 'device_count', 'created_at')
        read_only_fields = ('id', 'created_at', 'device_count')

    def get_device_count(self, obj):
        return obj.devices.filter(is_active=True).count()

    def validate_age(self, value):
        if value is not None and (value < 1 or value > 18):
            raise serializers.ValidationError('Age must be between 1 and 18.')
        return value


class DeviceSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source='child.name', read_only=True)
    # Never expose the full token in list views — only on creation/rotation
    device_token = serializers.UUIDField(read_only=True)

    class Meta:
        model = Device
        fields = (
            'id', 'child', 'child_name', 'name', 'device_type',
            'os', 'os_version', 'device_token', 'last_seen', 'is_active', 'created_at'
        )
        read_only_fields = ('id', 'device_token', 'last_seen', 'created_at', 'child_name')

    def validate_child(self, value):
        """Ensure parent can only add devices to their own children."""
        request = self.context.get('request')
        if request and hasattr(request.user, 'parent_profile'):
            if value.parent != request.user.parent_profile:
                raise serializers.ValidationError('You can only add devices to your own children.')
        return value


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Used when exposing the device token (creation + rotation only)."""
    class Meta:
        model = Device
        fields = ('id', 'name', 'device_token')
        read_only_fields = ('id', 'name', 'device_token')


class AuthenticationCredentialSerializer(serializers.ModelSerializer):
    """Serializer for listing/managing FIDO2 / WebAuthn passkeys."""
    credential_id_hex = serializers.SerializerMethodField()

    class Meta:
        from .models import AuthenticationCredential
        model = AuthenticationCredential
        fields = (
            'id', 'credential_id_hex', 'display_name',
            'aaguid', 'transports', 'created_at', 'last_used',
        )
        read_only_fields = fields

    def get_credential_id_hex(self, obj):
        """Return a truncated hex representation of the credential ID for display."""
        try:
            return bytes(obj.credential_id).hex()[:24] + '...'
        except Exception:
            return '(unknown)'
