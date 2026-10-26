"""
Backend API Integration Tests
"""

import os
import sys
from pathlib import Path
import pytest
from rest_framework.test import APIClient

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import ParentProfile, ChildProfile, Device

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


def test_api_health_root(api_client):
    response = api_client.get("/api/")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "DigitalGuard API" in response.json()["data"]["service"]


@pytest.mark.django_db
def test_parent_registration_and_login(api_client):
    reg_data = {
        "email": "sarah.registered@digitalguard.local",
        "username": "sarah_registered",
        "password": "SecurePassword123!",
        "display_name": "Sarah Registered",
    }
    reg_resp = api_client.post("/api/auth/register/", data=reg_data, format="json")
    assert reg_resp.status_code in [200, 201]

    login_resp = api_client.post("/api/auth/login/", data={
        "email": reg_data["email"],
        "password": reg_data["password"],
    }, format="json")
    assert login_resp.status_code == 200
    tokens = login_resp.json()["data"]["tokens"]
    assert "access" in tokens
