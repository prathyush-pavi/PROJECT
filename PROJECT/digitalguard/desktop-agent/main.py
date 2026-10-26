"""
DigitalGuard Desktop Agent — Main Service Loop (Windows)

Runs in the background on the child's Windows machine.
Coordinates window monitoring, idle detection, screen time aggregation,
local policy enforcement, and periodic telemetry sync to the Django backend.
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime

from config import config
from monitoring import WindowsAppMonitor, ScreenTimeTracker
from enforcement import WindowsPolicyEngine
from ipc import LocalBridge

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.log_file_path, encoding="utf-8", mode="a"),
    ],
)
logger = logging.getLogger("digitalguard.desktop.main")


class DigitalGuardAgent:
    def __init__(self):
        self.running = True
        self.bridge = LocalBridge(
            backend_url=config.backend_url,
            device_token=config.device_token,
            ai_engine_url=config.ai_engine_url,
        )
        self.monitor = WindowsAppMonitor(idle_threshold_seconds=config.idle_threshold_seconds)
        self.screentime = ScreenTimeTracker()
        self.enforcement = WindowsPolicyEngine(
            kill_blocked_apps=config.kill_blocked_apps,
            show_dialogs=config.show_toast_notifications,
        )

        self.last_sync_time = time.time()
        self.last_policy_fetch = 0.0
        self.last_heartbeat = 0.0

    def start(self):
        logger.info("==================================================")
        logger.info("Starting DigitalGuard Windows Desktop Agent v1.0")
        logger.info("Backend URL: %s", config.backend_url)
        logger.info("AI Engine URL: %s", config.ai_engine_url)
        logger.info("Device Token: %s...", config.device_token[:8])
        logger.info("==================================================")

        # Check AI Engine status
        if self.bridge.check_ai_health():
            logger.info("Local AI Engine is ONLINE.")
        else:
            logger.warning("Local AI Engine not reachable at %s. (Is it running?)", config.ai_engine_url)

        # Initial policy fetch
        self._refresh_policies()

        while self.running:
            try:
                now = time.time()

                # 1. Poll Foreground Application & Window
                event = self.monitor.poll()
                if event:
                    # Accumulate screen time (discounts idle)
                    self.screentime.record_activity(event.app_name, is_idle=event.is_idle)

                    if not event.is_idle and event.app_name:
                        # 2. Check Application Policy Enforcement
                        summary = self.screentime.get_summary()
                        app_usage = summary["app_breakdown"].get(event.app_name, 0)
                        violation = self.enforcement.check_application(
                            event.app_name, event.pid, app_usage
                        )

                        if violation:
                            # Log violation to backend
                            self.bridge.ingest_activity({
                                "event_type": "APPLICATION_BLOCKED",
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "severity": "HIGH",
                                "category": "application",
                                "app_name": event.app_name,
                                "action_taken": "BLOCK",
                                "metadata": {
                                    "window_title": event.window_title,
                                    "reason": violation.get("reason"),
                                    "pid": event.pid,
                                },
                            })

                        # 3. Check Screen Time & Curfew Policy
                        st_violation = self.enforcement.check_screen_time(summary["total_minutes"])
                        if st_violation:
                            self.bridge.ingest_activity({
                                "event_type": "SCREEN_TIME_LIMIT",
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "severity": "MEDIUM",
                                "category": "screen_time",
                                "action_taken": "WARN",
                                "metadata": st_violation,
                            })

                # 4. Periodic Screen Time Sync
                if now - self.last_sync_time >= config.screentime_sync_interval:
                    self._sync_screentime()
                    self.last_sync_time = now

                # 5. Periodic Policy Refresh
                if now - self.last_policy_fetch >= config.policy_refresh_interval:
                    self._refresh_policies()
                    self.last_policy_fetch = now

                # 6. Periodic Heartbeat
                if now - self.last_heartbeat >= config.heartbeat_interval:
                    self._send_heartbeat()
                    self.last_heartbeat = now

                time.sleep(config.app_poll_interval)

            except KeyboardInterrupt:
                logger.info("Agent shutdown requested by user.")
                break
            except Exception as e:
                logger.error("Error in agent loop: %s", e, exc_info=True)
                time.sleep(5)

        logger.info("DigitalGuard Desktop Agent stopped.")

    def _sync_screentime(self):
        summary = self.screentime.get_summary()
        logger.debug("Syncing screen time: %d mins today", summary["total_minutes"])
        self.bridge.ingest_screentime(summary)

    def _refresh_policies(self):
        logger.debug("Fetching updated policies from backend...")
        data = self.bridge.fetch_policies()
        if data and isinstance(data, dict):
            app_rules = data.get("data", {}).get("results", []) if "data" in data else data.get("results", [])
            self.enforcement.update_policies(app_rules)

    def _send_heartbeat(self):
        self.bridge.ingest_activity({
            "event_type": "DEVICE_HEARTBEAT",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": "LOW",
            "category": "system",
            "action_taken": "ALLOW",
            "metadata": {
                "os": "Windows",
                "status": "online",
            },
        })


def main():
    agent = DigitalGuardAgent()

    def sig_handler(signum, frame):
        agent.running = False

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    agent.start()


if __name__ == "__main__":
    main()
