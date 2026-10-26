"""
DigitalGuard Desktop Agent — Windows Policy Enforcement Engine

Evaluates running processes and screen time usage against active parental policies.
Enforces restrictions via Windows API (ShowWindow, MessageBoxW) or process termination.
"""

import sys
import time
import datetime
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("digitalguard.desktop.enforcement")

if sys.platform == "win32":
    import ctypes
    user32 = ctypes.windll.user32
    SW_MINIMIZE = 6
    MB_OK = 0x00000000
    MB_ICONWARNING = 0x00000030
    MB_SYSTEMMODAL = 0x00001000
else:
    user32 = None
    SW_MINIMIZE = 6
    MB_OK = 0
    MB_ICONWARNING = 0
    MB_SYSTEMMODAL = 0

try:
    import psutil
except ImportError:
    psutil = None


class WindowsPolicyEngine:
    """
    Evaluates application policies, bedtime schedules, and screen-time quotas.
    """

    def __init__(self, kill_blocked_apps: bool = False, show_dialogs: bool = True):
        self.kill_blocked_apps = kill_blocked_apps
        self.show_dialogs = show_dialogs
        self.app_policies: Dict[str, Dict[str, Any]] = {}
        self.screentime_policy: Dict[str, Any] = {
            "daily_limit_minutes": 180,
            "allowed_start": "08:00",
            "allowed_end": "21:00",
            "weekend_limit_minutes": 240,
        }
        self._last_alert_times: Dict[str, float] = {}

    def update_policies(self, app_policies: List[Dict[str, Any]], screentime_policy: Optional[Dict[str, Any]] = None):
        """Update active policies from backend."""
        self.app_policies.clear()
        for p in app_policies:
            app_name = p.get("app_name", "").lower()
            if app_name:
                self.app_policies[app_name] = p

        if screentime_policy:
            self.screentime_policy.update(screentime_policy)
        logger.info("Policy cache refreshed: %d app policies loaded.", len(self.app_policies))

    def _should_suppress_alert(self, key: str, cooldown_seconds: int = 60) -> bool:
        """Avoid spamming dialogs / alerts for the same event repeatedly."""
        now = time.time()
        last = self._last_alert_times.get(key, 0.0)
        if now - last < cooldown_seconds:
            return True
        self._last_alert_times[key] = now
        return False

    def check_application(self, app_name: str, pid: int, current_usage_minutes: int) -> Optional[Dict[str, Any]]:
        """
        Checks if the currently running app is blocked or has exceeded limits.
        Returns enforcement action dict if a violation occurred, else None.
        """
        clean_name = app_name.lower().strip()
        policy = self.app_policies.get(clean_name)
        if not policy:
            # Check without .exe extension or partial match
            clean_base = clean_name.replace(".exe", "")
            policy = self.app_policies.get(clean_base)

        if not policy:
            return None

        rule = policy.get("policy", "ALLOW").upper()

        if rule == "BLOCK":
            return self._enforce_blocked_app(app_name, pid, "Prohibited by parent policy")

        if rule == "LIMITED":
            daily_limit = policy.get("daily_limit_minutes", 60)
            if current_usage_minutes >= daily_limit:
                return self._enforce_blocked_app(
                    app_name,
                    pid,
                    f"Daily time limit of {daily_limit} minutes reached",
                )

        return None

    def check_screen_time(self, total_minutes_today: int) -> Optional[Dict[str, Any]]:
        """
        Evaluates daily screen time limit and bedtime schedule.
        """
        now = datetime.datetime.now()
        is_weekend = now.weekday() >= 5
        limit = (
            self.screentime_policy.get("weekend_limit_minutes", 240)
            if is_weekend
            else self.screentime_policy.get("daily_limit_minutes", 180)
        )

        # 1. Check total duration
        if total_minutes_today >= limit:
            if self.show_dialogs and not self._should_suppress_alert("screentime_limit", cooldown_seconds=300):
                self._show_warning_dialog(
                    "DigitalGuard Screen Time Alert",
                    f"Your daily screen time limit of {limit} minutes has been reached for today.",
                )
            return {
                "type": "SCREENTIME_LIMIT_REACHED",
                "total_minutes": total_minutes_today,
                "limit": limit,
            }

        # 2. Check bedtime curfew
        start_str = self.screentime_policy.get("allowed_start", "08:00")
        end_str = self.screentime_policy.get("allowed_end", "21:00")
        try:
            cur_time = now.time()
            start_time = datetime.datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.datetime.strptime(end_str, "%H:%M").time()

            in_curfew = False
            if start_time < end_time:
                in_curfew = cur_time < start_time or cur_time > end_time
            else:  # spans midnight
                in_curfew = end_time < cur_time < start_time

            if in_curfew:
                if self.show_dialogs and not self._should_suppress_alert("curfew_alert", cooldown_seconds=300):
                    self._show_warning_dialog(
                        "DigitalGuard Bedtime Curfew",
                        f"Device usage is restricted outside allowable hours ({start_str} - {end_str}).",
                    )
                return {
                    "type": "BEDTIME_CURFEW_ACTIVE",
                    "allowed_window": f"{start_str} - {end_str}",
                }
        except Exception as e:
            logger.debug("Curfew time parse error: %s", e)

        return None

    def _enforce_blocked_app(self, app_name: str, pid: int, reason: str) -> Dict[str, Any]:
        """Perform Windows enforcement: minimize, alert, or terminate."""
        suppressed = self._should_suppress_alert(f"block_{app_name}", cooldown_seconds=30)

        # 1. Minimize foreground window or terminate
        if sys.platform == "win32" and user32:
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                user32.ShowWindow(hwnd, SW_MINIMIZE)

        if self.kill_blocked_apps and psutil and pid > 0:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                logger.warning("Terminated disallowed process %s (PID %d)", app_name, pid)
            except Exception as e:
                logger.error("Failed to terminate process %d: %s", pid, e)

        # 2. Show Windows message dialog
        if not suppressed and self.show_dialogs:
            self._show_warning_dialog(
                "DigitalGuard Application Blocked",
                f"{app_name} is restricted by your family safety settings.\n\nReason: {reason}",
            )

        return {
            "type": "APPLICATION_BLOCKED",
            "app_name": app_name,
            "pid": pid,
            "reason": reason,
        }

    def _show_warning_dialog(self, title: str, message: str):
        """Displays a native Windows message box modal."""
        if sys.platform == "win32" and user32:
            try:
                user32.MessageBoxW(0, message, title, MB_OK | MB_ICONWARNING | MB_SYSTEMMODAL)
            except Exception as e:
                logger.debug("MessageBoxW error: %s", e)
        else:
            print(f"[{title}] {message}")
