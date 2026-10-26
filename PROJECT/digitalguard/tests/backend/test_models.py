"""
Backend Unit Tests — Models & Business Logic
"""

import os
import sys
import uuid
import datetime
from pathlib import Path
import pytest

# Configure Django settings
backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import ParentProfile, ChildProfile, Device
from policies.models import WebsitePolicy, ApplicationPolicy, ScreenTimePolicy
from monitoring.models import ActivityLog, ThreatEvent

User = get_user_model()


@pytest.mark.django_db
def test_user_creation():
    user = User.objects.create_user(
        email="testparent@digitalguard.local",
        username="testparent",
        password="TestPassword123!",
        role=User.ROLE_PARENT,
    )
    assert user.is_parent
    assert user.email == "testparent@digitalguard.local"


@pytest.mark.django_db
def test_device_token_rotation():
    user = User.objects.create_user(
        email="deviceparent@digitalguard.local",
        username="deviceparent",
        password="TestPassword123!",
    )
    parent = ParentProfile.objects.create(user=user, display_name="Test Parent")
    child = ChildProfile.objects.create(parent=parent, name="Timmy")
    device = Device.objects.create(
        child=child,
        name="Timmy's Windows PC",
        os="Windows",
    )

    old_token = device.device_token
    new_token = device.rotate_token()
    assert old_token != new_token
    assert device.device_token == new_token


@pytest.mark.django_db
def test_activity_log_creation():
    user = User.objects.create_user(
        email="actparent@digitalguard.local",
        username="actparent",
        password="TestPassword123!",
    )
    parent = ParentProfile.objects.create(user=user, display_name="Parent")
    child = ChildProfile.objects.create(parent=parent, name="Child")
    device = Device.objects.create(child=child, name="PC", os="Windows")

    log = ActivityLog.objects.create(
        device=device,
        event_type=ActivityLog.PHISHING_DETECTED,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        severity=ActivityLog.SEV_CRITICAL,
        category="phishing",
        domain="fake-bank.xyz",
        action_taken=ActivityLog.ACTION_BLOCK,
    )
    assert log.id is not None
    assert log.action_taken == "BLOCK"
