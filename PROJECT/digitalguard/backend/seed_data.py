"""
DigitalGuard — Demo Database Seed Script

Populates realistic parent, children, devices, policies, screen time usage,
activity logs, threat events, alerts, and weekly reports for testing and demonstration.
"""

import os
import sys
import uuid
import datetime
from django.utils import timezone

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import ParentProfile, ChildProfile, Device
from policies.models import WebsitePolicy, ApplicationPolicy, ScreenTimePolicy
from monitoring.models import ActivityLog, ThreatEvent, AIAnalysis, ScreenTimeUsage
from alerts.models import Alert
from reports.models import Report

User = get_user_model()


def seed():
    print("==================================================")
    print("Seeding DigitalGuard Demo Database")
    print("==================================================")

    # 1. Parent User
    parent_email = "parent@digitalguard.local"
    user, created = User.objects.get_or_create(
        email=parent_email,
        defaults={
            "username": "sarah_connor",
            "role": User.ROLE_PARENT,
            "is_staff": True,
            "is_superuser": True,
            "is_verified": True,
        }
    )
    user.set_password("Password123!")
    user.save()
    print(f"[✓] Parent User: {parent_email} (Password: Password123!)")

    # Parent Profile
    parent_profile, _ = ParentProfile.objects.get_or_create(
        user=user,
        defaults={
            "display_name": "Sarah Connor",
            "notification_email": "sarah.connor@example.com",
            "alert_preferences": {
                "phishing": {"enabled": True, "min_severity": "MEDIUM"},
                "cyberbullying": {"enabled": True, "min_severity": "LOW"},
                "grooming": {"enabled": True, "min_severity": "LOW"},
                "harmful_content": {"enabled": True, "min_severity": "HIGH"},
                "screen_time": {"enabled": True, "min_severity": "LOW"},
                "app_blocked": {"enabled": True, "min_severity": "LOW"},
            }
        }
    )

    # 2. Children
    alex, _ = ChildProfile.objects.get_or_create(
        parent=parent_profile,
        name="Alex Connor",
        defaults={"age": 12, "avatar": "👦", "is_active": True}
    )

    emma, _ = ChildProfile.objects.get_or_create(
        parent=parent_profile,
        name="Emma Connor",
        defaults={"age": 8, "avatar": "👧", "is_active": True}
    )
    print(f"[✓] Children: {alex.name}, {emma.name}")

    # 3. Devices
    alex_pc_token = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    alex_pc, _ = Device.objects.get_or_create(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        defaults={
            "child": alex,
            "name": "Alex's Windows Gaming PC",
            "device_type": Device.DEVICE_DESKTOP,
            "os": "Windows",
            "os_version": "11 Pro",
            "device_token": alex_pc_token,
            "last_seen": timezone.now(),
            "is_active": True,
        }
    )
    if alex_pc.device_token != alex_pc_token:
        alex_pc.device_token = alex_pc_token
        alex_pc.save()

    alex_laptop, _ = Device.objects.get_or_create(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        defaults={
            "child": alex,
            "name": "Alex's School Laptop",
            "device_type": Device.DEVICE_LAPTOP,
            "os": "Windows",
            "os_version": "11 Home",
            "device_token": uuid.uuid4(),
            "last_seen": timezone.now() - datetime.timedelta(hours=2),
            "is_active": True,
        }
    )

    emma_tablet, _ = Device.objects.get_or_create(
        id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        defaults={
            "child": emma,
            "name": "Emma's Family Tablet",
            "device_type": Device.DEVICE_TABLET,
            "os": "Android",
            "os_version": "14",
            "device_token": uuid.uuid4(),
            "last_seen": timezone.now() - datetime.timedelta(minutes=45),
            "is_active": True,
        }
    )
    print(f"[✓] Registered Devices with primary token: {alex_pc_token}")

    # 4. Website Policies
    web_rules = [
        {"domain": "darknet-market.cc", "rule_type": "BLOCK", "category": "malware", "reason": "Known illicit marketplace"},
        {"domain": "phishing-bank-login.xyz", "rule_type": "BLOCK", "category": "phishing", "reason": "Credential harvesting decoy"},
        {"domain": "adult-xxx-stream.net", "rule_type": "BLOCK", "category": "adult", "reason": "Explicit adult content"},
        {"domain": "free-game-cheats-download.biz", "rule_type": "BLOCK", "category": "malware", "reason": "Trojan/adware distribution vector"},
        {"domain": "reddit.com", "rule_type": "WARN", "category": "social_media", "reason": "Unmoderated social platform"},
        {"domain": "tiktok.com", "rule_type": "WARN", "category": "social_media", "reason": "Screen time sink"},
        {"domain": "khanacademy.org", "rule_type": "ALLOW", "category": "education", "reason": "Approved educational resource"},
        {"domain": "wikipedia.org", "rule_type": "ALLOW", "category": "education", "reason": "General reference"},
        {"domain": "scratch.mit.edu", "rule_type": "ALLOW", "category": "education", "reason": "Child programming environment"},
    ]

    for rule in web_rules:
        WebsitePolicy.objects.get_or_create(
            parent=parent_profile,
            child=alex,
            domain=rule["domain"],
            defaults={
                "rule_type": rule["rule_type"],
                "category": rule["category"],
                "reason": rule["reason"],
            }
        )
    print(f"[✓] Seeded {len(web_rules)} Website Policies")

    # 5. Application Policies
    app_rules = [
        {"app_name": "cheatengine.exe", "policy": "BLOCK", "daily_limit_minutes": 0},
        {"app_name": "utorrent.exe", "policy": "BLOCK", "daily_limit_minutes": 0},
        {"app_name": "roblox.exe", "policy": "LIMITED", "daily_limit_minutes": 60},
        {"app_name": "discord.exe", "policy": "LIMITED", "daily_limit_minutes": 45},
        {"app_name": "steam.exe", "policy": "LIMITED", "daily_limit_minutes": 90},
        {"app_name": "chrome.exe", "policy": "ALLOW", "daily_limit_minutes": 0},
        {"app_name": "code.exe", "policy": "ALLOW", "daily_limit_minutes": 0},
    ]

    for rule in app_rules:
        ApplicationPolicy.objects.get_or_create(
            parent=parent_profile,
            child=alex,
            app_name=rule["app_name"],
            defaults={
                "policy": rule["policy"],
                "daily_limit_minutes": rule["daily_limit_minutes"],
            }
        )
    print(f"[✓] Seeded {len(app_rules)} Application Policies")

    # 6. Screen Time Policies
    ScreenTimePolicy.objects.get_or_create(
        child=alex,
        defaults={
            "daily_limit_minutes": 180,
            "allowed_start": datetime.time(8, 0),
            "allowed_end": datetime.time(21, 0),
            "weekend_limit_minutes": 240,
        }
    )

    ScreenTimePolicy.objects.get_or_create(
        child=emma,
        defaults={
            "daily_limit_minutes": 90,
            "allowed_start": datetime.time(9, 0),
            "allowed_end": datetime.time(19, 30),
            "weekend_limit_minutes": 120,
        }
    )

    # 7. Screen Time Usage History (Last 7 days)
    today = datetime.date.today()
    for i in range(7):
        d = today - datetime.timedelta(days=i)
        mins = 110 + (i * 12) % 75
        ScreenTimeUsage.objects.get_or_create(
            device=alex_pc,
            date=d,
            defaults={
                "total_minutes": mins,
                "app_breakdown": {
                    "chrome.exe": int(mins * 0.45),
                    "roblox.exe": int(mins * 0.35),
                    "code.exe": int(mins * 0.20),
                }
            }
        )
    print("[✓] Seeded 7 days of Screen Time Usage history")

    # 8. Activity Logs & Threat Events
    now = timezone.now()

    # Activity 1: Blocked Phishing Site
    log1, _ = ActivityLog.objects.get_or_create(
        id=uuid.UUID("a1111111-1111-1111-1111-111111111111"),
        defaults={
            "device": alex_pc,
            "event_type": ActivityLog.PHISHING_DETECTED,
            "timestamp": now - datetime.timedelta(minutes=15),
            "severity": ActivityLog.SEV_CRITICAL,
            "category": "phishing",
            "domain": "phishing-bank-login.xyz",
            "url_path": "/secure/login.php",
            "action_taken": ActivityLog.ACTION_BLOCK,
            "metadata": {"risk_score": 0.96, "heuristics": ["entropy_high", "typosquat_target"]},
        }
    )

    ThreatEvent.objects.get_or_create(
        activity_log=log1,
        defaults={
            "threat_type": "phishing",
            "risk_score": 0.96,
            "confidence": 0.92,
            "ai_category": "credential_theft",
            "indicators": ["entropy > 4.5", "target brand mismatch"],
            "inference_mode": "MOCK",
        }
    )

    # Activity 2: Cyberbullying Flagged in chat
    log2, _ = ActivityLog.objects.get_or_create(
        id=uuid.UUID("a2222222-2222-2222-2222-222222222222"),
        defaults={
            "device": alex_pc,
            "event_type": ActivityLog.CYBERBULLYING_DETECTED,
            "timestamp": now - datetime.timedelta(hours=1, minutes=10),
            "severity": ActivityLog.SEV_HIGH,
            "category": "cyberbullying",
            "domain": "web.discord.com",
            "url_path": "/channels/general",
            "action_taken": ActivityLog.ACTION_BLUR,
            "metadata": {"risk_score": 0.88, "context": "chat"},
        }
    )

    ThreatEvent.objects.get_or_create(
        activity_log=log2,
        defaults={
            "threat_type": "cyberbullying",
            "risk_score": 0.88,
            "confidence": 0.85,
            "ai_category": "harassment",
            "indicators": ["aggressive_language_pattern", "targeted_toxicity"],
            "inference_mode": "MOCK",
        }
    )

    # Activity 3: Application Blocked (Cheat Engine)
    log3, _ = ActivityLog.objects.get_or_create(
        id=uuid.UUID("a3333333-3333-3333-3333-333333333333"),
        defaults={
            "device": alex_pc,
            "event_type": ActivityLog.APPLICATION_BLOCKED,
            "timestamp": now - datetime.timedelta(hours=3),
            "severity": ActivityLog.SEV_HIGH,
            "category": "application",
            "app_name": "cheatengine.exe",
            "action_taken": ActivityLog.ACTION_BLOCK,
            "metadata": {"pid": 7820, "window_title": "Cheat Engine 7.5"},
        }
    )

    # Activity 4: Safe Educational Visit
    ActivityLog.objects.get_or_create(
        id=uuid.UUID("a4444444-4444-4444-4444-444444444444"),
        defaults={
            "device": alex_pc,
            "event_type": ActivityLog.WEBSITE_VISITED,
            "timestamp": now - datetime.timedelta(hours=4),
            "severity": ActivityLog.SEV_LOW,
            "category": "education",
            "domain": "khanacademy.org",
            "url_path": "/math/algebra",
            "action_taken": ActivityLog.ACTION_ALLOW,
            "metadata": {"title": "Linear Equations | Khan Academy"},
        }
    )
    print("[✓] Seeded Sample Activity Logs & Threat Events")

    # 9. Alerts
    Alert.objects.get_or_create(
        id=uuid.UUID("b1111111-1111-1111-1111-111111111111"),
        defaults={
            "parent": parent_profile,
            "child": alex,
            "activity_log": log1,
            "alert_type": "phishing",
            "severity": Alert.SEV_CRITICAL,
            "title": "Critical: Phishing Site Intercepted",
            "message": "Alex attempted to visit 'phishing-bank-login.xyz'. Access was blocked immediately by DigitalGuard Shield.",
            "is_read": False,
        }
    )

    Alert.objects.get_or_create(
        id=uuid.UUID("b2222222-2222-2222-2222-222222222222"),
        defaults={
            "parent": parent_profile,
            "child": alex,
            "activity_log": log2,
            "alert_type": "cyberbullying",
            "severity": Alert.SEV_HIGH,
            "title": "Toxic Language Detected on Discord",
            "message": "AI content analysis detected aggressive/harassing language on Discord. The message content was blurred.",
            "is_read": False,
        }
    )

    Alert.objects.get_or_create(
        id=uuid.UUID("b3333333-3333-3333-3333-333333333333"),
        defaults={
            "parent": parent_profile,
            "child": alex,
            "activity_log": log3,
            "alert_type": "app_blocked",
            "severity": Alert.SEV_MEDIUM,
            "title": "Restricted Application Launched",
            "message": "Alex attempted to execute 'cheatengine.exe'. The application was minimized and access denied.",
            "is_read": True,
        }
    )
    print("[✓] Seeded 3 Parent Alerts")

    # 10. Reports
    Report.objects.get_or_create(
        id=uuid.UUID("c1111111-1111-1111-1111-111111111111"),
        defaults={
            "parent": parent_profile,
            "child": alex,
            "report_type": Report.TYPE_WEEKLY,
            "period_start": today - datetime.timedelta(days=7),
            "period_end": today,
            "data": {
                "total_screen_time_hours": 14.5,
                "threats_blocked": 4,
                "flagged_chats": 2,
                "top_categories": [
                    {"category": "education", "percent": 42},
                    {"category": "gaming", "percent": 35},
                    {"category": "social", "percent": 15},
                    {"category": "other", "percent": 8},
                ],
                "safety_score": 94,
            }
        }
    )
    print("[✓] Seeded Weekly Parent Summary Report")

    print("\n[SUCCESS] Database populated with full demonstration dataset.")
    print("Log in at the Parental Dashboard with:")
    print("Email:    parent@digitalguard.local")
    print("Password: Password123!")


if __name__ == "__main__":
    seed()
