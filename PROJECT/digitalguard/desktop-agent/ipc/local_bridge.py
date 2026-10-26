"""
DigitalGuard Desktop Agent — Local Bridge (Backend & AI Engine IPC)
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

logger = logging.getLogger("digitalguard.desktop.bridge")


class LocalBridge:
    """
    HTTP communication bridge for the desktop agent to talk to:
    1. DigitalGuard Backend (API)
    2. DigitalGuard Local AI Engine
    Uses standard library urllib for zero external runtime dependencies.
    """

    def __init__(self, backend_url: str, device_token: str, ai_engine_url: str):
        self.backend_url = backend_url.rstrip("/")
        self.device_token = device_token
        self.ai_engine_url = ai_engine_url.rstrip("/")

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 5,
    ) -> Optional[Dict[str, Any]]:
        if headers is None:
            headers = {}

        headers["Content-Type"] = "application/json"
        headers["User-Agent"] = "DigitalGuard-DesktopAgent-Windows/1.0"

        data_bytes = None
        if payload is not None:
            data_bytes = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                if raw:
                    return json.loads(raw)
                return {}
        except urllib.error.HTTPError as e:
            try:
                err_content = e.read().decode("utf-8")
                logger.warning("HTTP %d from %s: %s", e.code, url, err_content[:200])
            except Exception:
                logger.warning("HTTP %d from %s", e.code, url)
            return None
        except Exception as e:
            logger.debug("Request failed for %s: %s", url, e)
            return None

    # Backend API methods
    def ingest_activity(self, activity_data: Dict[str, Any]) -> bool:
        url = f"{self.backend_url}/api/activity/ingest/"
        headers = {"Authorization": f"DeviceToken {self.device_token}"}
        res = self._make_request(url, method="POST", payload=activity_data, headers=headers)
        return res is not None

    def ingest_screentime(self, screentime_data: Dict[str, Any]) -> bool:
        url = f"{self.backend_url}/api/screentime/ingest/"
        headers = {"Authorization": f"DeviceToken {self.device_token}"}
        res = self._make_request(url, method="POST", payload=screentime_data, headers=headers)
        return res is not None

    def fetch_policies(self) -> Optional[Dict[str, Any]]:
        """
        Fetches website and application rules from backend.
        """
        url = f"{self.backend_url}/api/policies/applications/"
        headers = {"Authorization": f"DeviceToken {self.device_token}"}
        return self._make_request(url, method="GET", headers=headers)

    # Local AI Engine methods
    def analyze_url(self, url_to_check: str) -> Optional[Dict[str, Any]]:
        url = f"{self.ai_engine_url}/analyze/url"
        return self._make_request(url, method="POST", payload={"url": url_to_check}, timeout=3)

    def analyze_text(self, text_to_check: str, context: str = "webpage") -> Optional[Dict[str, Any]]:
        url = f"{self.ai_engine_url}/analyze/text"
        return self._make_request(
            url,
            method="POST",
            payload={"text": text_to_check, "context": context},
            timeout=3,
        )

    def check_ai_health(self) -> bool:
        url = f"{self.ai_engine_url}/health"
        res = self._make_request(url, method="GET", timeout=2)
        return res is not None and res.get("status") == "ok"
