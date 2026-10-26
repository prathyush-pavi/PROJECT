"""
Alert generation utility.
Called whenever a significant activity event is created.
Checks parent's alert_preferences before creating an alert.
"""

import logging
from .models import Alert
from monitoring.models import ActivityLog

logger = logging.getLogger('digitalguard.alerts')

# Map from ActivityLog event_type to Alert alert_type
EVENT_TO_ALERT_TYPE = {
    ActivityLog.PHISHING_DETECTED: Alert.ALERT_PHISHING,
    ActivityLog.CYBERBULLYING_DETECTED: Alert.ALERT_CYBERBULLYING,
    ActivityLog.GROOMING_RISK_DETECTED: Alert.ALERT_GROOMING,
    ActivityLog.CONTENT_FLAGGED: Alert.ALERT_HARMFUL_CONTENT,
    ActivityLog.DOWNLOAD_BLOCKED: Alert.ALERT_DOWNLOAD,
    ActivityLog.APPLICATION_BLOCKED: Alert.ALERT_APP_BLOCKED,
    ActivityLog.SCREEN_TIME_LIMIT_REACHED: Alert.ALERT_SCREEN_TIME,
    ActivityLog.WEBSITE_BLOCKED: Alert.ALERT_WEBSITE_BLOCKED,
}

# Events that always generate alerts regardless of preferences
ALWAYS_ALERT_EVENTS = {
    ActivityLog.PHISHING_DETECTED,
    ActivityLog.CYBERBULLYING_DETECTED,
    ActivityLog.GROOMING_RISK_DETECTED,
}


def create_alert_if_needed(activity_log: ActivityLog):
    """
    Evaluate whether the given ActivityLog entry should generate a parent alert.
    Respects the parent's alert_preferences configuration.
    """
    alert_type = EVENT_TO_ALERT_TYPE.get(activity_log.event_type)
    if not alert_type:
        return  # This event type doesn't generate alerts

    device = activity_log.device
    child = device.child
    parent = child.parent

    # Check parent preferences (unless this is an always-alert event)
    if activity_log.event_type not in ALWAYS_ALERT_EVENTS:
        prefs = parent.alert_preferences or {}
        pref_key = _get_pref_key(activity_log.event_type)
        if pref_key and pref_key in prefs:
            pref = prefs[pref_key]
            if not pref.get('enabled', True):
                return  # Parent has disabled this alert type

    # Build alert title and message
    title, message = _build_alert_message(activity_log, child)

    alert = Alert.objects.create(
        parent=parent,
        child=child,
        activity_log=activity_log,
        alert_type=alert_type,
        severity=activity_log.severity,
        title=title,
        message=message,
        is_read=False,
    )
    logger.info(
        'Alert created: [%s] %s for parent=%s', alert.severity, alert.title, parent.display_name
    )
    return alert


def _get_pref_key(event_type):
    mapping = {
        ActivityLog.PHISHING_DETECTED: 'phishing',
        ActivityLog.CYBERBULLYING_DETECTED: 'cyberbullying',
        ActivityLog.GROOMING_RISK_DETECTED: 'grooming',
        ActivityLog.CONTENT_FLAGGED: 'harmful_content',
        ActivityLog.DOWNLOAD_BLOCKED: 'download',
        ActivityLog.APPLICATION_BLOCKED: 'app_blocked',
        ActivityLog.SCREEN_TIME_LIMIT_REACHED: 'screen_time',
        ActivityLog.WEBSITE_BLOCKED: 'website_blocked',
    }
    return mapping.get(event_type)


def _build_alert_message(log: ActivityLog, child):
    """Generate a human-readable alert title and message."""
    child_name = child.name
    domain = log.domain or 'unknown site'
    app = log.app_name or 'unknown app'

    messages = {
        ActivityLog.PHISHING_DETECTED: (
            f'⚠️ Phishing site detected for {child_name}',
            f'{child_name} attempted to visit a phishing site: {domain}. The page was blocked.'
        ),
        ActivityLog.CYBERBULLYING_DETECTED: (
            f'🚨 Cyberbullying content detected for {child_name}',
            f'DigitalGuard detected potential cyberbullying content on {domain}. '
            f'Content was {log.action_taken.lower()}ed.'
        ),
        ActivityLog.GROOMING_RISK_DETECTED: (
            f'🔴 Grooming risk detected for {child_name}',
            f'Suspicious language patterns associated with grooming risk were detected on {domain}. '
            f'This is a risk indicator — please review activity logs.'
        ),
        ActivityLog.CONTENT_FLAGGED: (
            f'⚠️ Harmful content flagged for {child_name}',
            f'Potentially harmful content was detected on {domain}. Action taken: {log.action_taken}.'
        ),
        ActivityLog.DOWNLOAD_BLOCKED: (
            f'🛡️ Suspicious download blocked for {child_name}',
            f'A potentially suspicious file download was blocked on {domain}.'
        ),
        ActivityLog.APPLICATION_BLOCKED: (
            f'🚫 Application blocked for {child_name}',
            f'{child_name} attempted to use {app}, which is blocked by policy.'
        ),
        ActivityLog.SCREEN_TIME_LIMIT_REACHED: (
            f'⏱️ Screen time limit reached for {child_name}',
            f'{child_name} has reached their daily screen time limit. '
            f'Total usage: {log.metadata.get("current_usage", "?")} minutes.'
        ),
        ActivityLog.WEBSITE_BLOCKED: (
            f'🚫 Website blocked for {child_name}',
            f'{child_name} attempted to visit {domain}, which is blocked by policy.'
        ),
    }

    return messages.get(
        log.event_type,
        (f'Alert for {child_name}', f'Event: {log.event_type} on {domain}')
    )
