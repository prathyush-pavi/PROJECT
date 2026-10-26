"""
Unit tests for DigitalGuard Desktop Agent (Windows)
"""

import sys
import time
from pathlib import Path

agent_dir = Path(__file__).resolve().parent.parent.parent / "desktop-agent"
sys.path.insert(0, str(agent_dir))

try:
    from monitoring.screen_time import ScreenTimeTracker
except (ImportError, ModuleNotFoundError, AttributeError):
    import importlib.util
    spec = importlib.util.spec_from_file_location("desktop_agent_screentime", agent_dir / "monitoring" / "screen_time.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ScreenTimeTracker = mod.ScreenTimeTracker

try:
    from enforcement.policy_engine import WindowsPolicyEngine
except (ImportError, ModuleNotFoundError, AttributeError):
    import importlib.util
    spec = importlib.util.spec_from_file_location("desktop_agent_enforcement", agent_dir / "enforcement" / "policy_engine.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    WindowsPolicyEngine = mod.WindowsPolicyEngine


def test_screentime_tracker_accumulation():
    tracker = ScreenTimeTracker()
    tracker.last_tick_time = time.time() - 5.0
    tracker.record_activity("chrome.exe", is_idle=False)

    summary = tracker.get_summary()
    assert summary["current_app"] == "chrome.exe"
    assert "date" in summary
    assert isinstance(summary["total_minutes"], int)


def test_screentime_tracker_idle_discount():
    tracker = ScreenTimeTracker()
    initial_total = tracker.total_active_seconds

    tracker.last_tick_time = time.time() - 10.0
    tracker.record_activity("chrome.exe", is_idle=True)

    # When idle, elapsed time should not be accumulated
    assert tracker.total_active_seconds == initial_total


def test_policy_engine_application_block():
    engine = WindowsPolicyEngine(kill_blocked_apps=False, show_dialogs=False)
    engine.update_policies([
        {"app_name": "cheatengine.exe", "policy": "BLOCK", "daily_limit_minutes": 0},
        {"app_name": "roblox.exe", "policy": "LIMITED", "daily_limit_minutes": 30},
    ])

    # Check blocked app
    violation = engine.check_application("cheatengine.exe", pid=1234, current_usage_minutes=5)
    assert violation is not None
    assert violation["type"] == "APPLICATION_BLOCKED"
    assert violation["app_name"] == "cheatengine.exe"

    # Check limited app under limit
    no_violation = engine.check_application("roblox.exe", pid=5678, current_usage_minutes=20)
    assert no_violation is None

    # Check limited app over limit
    limit_violation = engine.check_application("roblox.exe", pid=5678, current_usage_minutes=35)
    assert limit_violation is not None
    assert limit_violation["type"] == "APPLICATION_BLOCKED"


def test_policy_engine_screentime_limit():
    engine = WindowsPolicyEngine(show_dialogs=False)
    engine.update_policies([], screentime_policy={"daily_limit_minutes": 120, "weekend_limit_minutes": 180})

    # Under limit
    assert engine.check_screen_time(total_minutes_today=60) is None

    # Over limit (exceeds both weekday 120m and weekend 180m limits)
    res = engine.check_screen_time(total_minutes_today=200)
    assert res is not None
    assert res["type"] == "SCREENTIME_LIMIT_REACHED"
