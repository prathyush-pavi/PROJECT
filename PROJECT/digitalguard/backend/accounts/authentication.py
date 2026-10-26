"""
Device Token Authentication

Allows the desktop agent and browser extension to authenticate API calls
using a per-device UUID token stored in the Device model.

Usage:
    Include the device token in the Authorization header:
    Authorization: DeviceToken <uuid>

Security:
    - Tokens are UUIDs (128-bit random) stored hashed in production
    - Tokens can be rotated via the parent dashboard
    - Compromised tokens must be rotated immediately
"""

import logging
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Device

logger = logging.getLogger('digitalguard.accounts.auth')


class DeviceTokenAuthentication(BaseAuthentication):
    """
    Custom DRF authentication for device-to-server communication.
    The desktop agent and browser extension use this to POST activity events.
    """
    KEYWORD = 'DeviceToken'

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith(self.KEYWORD + ' '):
            return None  # Not a device token — let other authenticators handle it

        token_value = auth_header[len(self.KEYWORD) + 1:].strip()
        if not token_value:
            raise AuthenticationFailed('Device token is missing.')

        try:
            device = Device.objects.select_related(
                'child__parent__user'
            ).get(device_token=token_value, is_active=True)
        except (Device.DoesNotExist, Exception):
            # Log at WARNING level — repeated failures may indicate a brute-force attempt
            logger.warning('Failed device token auth attempt, token_prefix=%s', token_value[:8])
            raise AuthenticationFailed('Invalid or inactive device token.')

        # Return (user, device) — DRF will set request.user and request.auth
        return (device.child.parent.user, device)

    def authenticate_header(self, request):
        return self.KEYWORD
