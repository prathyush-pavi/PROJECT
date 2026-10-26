"""
DigitalGuard Monitoring Models

ActivityLog, ThreatEvent, AIAnalysis, ScreenTimeUsage.

Privacy principle:
- Store metadata and classifications, NOT raw page content.
- content_hash is a SHA-256 of the analyzed content — allows deduplication
  without storing raw text.
"""

import uuid
import logging
from django.db import models

logger = logging.getLogger('digitalguard.monitoring')


class ActivityLog(models.Model):
    """
    Central log of all monitored events on a child's device.
    Every significant event (website visit, block, threat, app usage) creates a log entry.
    """
    # ── Event Types ──────────────────────────────────────────────────────────
    WEBSITE_VISITED = 'WEBSITE_VISITED'
    WEBSITE_BLOCKED = 'WEBSITE_BLOCKED'
    WEBSITE_WARNING = 'WEBSITE_WARNING'
    PHISHING_DETECTED = 'PHISHING_DETECTED'
    CONTENT_FLAGGED = 'CONTENT_FLAGGED'
    CYBERBULLYING_DETECTED = 'CYBERBULLYING_DETECTED'
    GROOMING_RISK_DETECTED = 'GROOMING_RISK_DETECTED'
    APPLICATION_STARTED = 'APPLICATION_STARTED'
    APPLICATION_BLOCKED = 'APPLICATION_BLOCKED'
    APPLICATION_LIMITED = 'APPLICATION_LIMITED'
    DOWNLOAD_ATTEMPTED = 'DOWNLOAD_ATTEMPTED'
    DOWNLOAD_BLOCKED = 'DOWNLOAD_BLOCKED'
    SCREEN_TIME_WARNING = 'SCREEN_TIME_WARNING'
    SCREEN_TIME_LIMIT_REACHED = 'SCREEN_TIME_LIMIT_REACHED'
    POLICY_CHANGED = 'POLICY_CHANGED'
    AI_ANALYSIS_FAILED = 'AI_ANALYSIS_FAILED'

    EVENT_TYPE_CHOICES = [
        (WEBSITE_VISITED, 'Website Visited'),
        (WEBSITE_BLOCKED, 'Website Blocked'),
        (WEBSITE_WARNING, 'Website Warning'),
        (PHISHING_DETECTED, 'Phishing Detected'),
        (CONTENT_FLAGGED, 'Content Flagged'),
        (CYBERBULLYING_DETECTED, 'Cyberbullying Detected'),
        (GROOMING_RISK_DETECTED, 'Grooming Risk Detected'),
        (APPLICATION_STARTED, 'Application Started'),
        (APPLICATION_BLOCKED, 'Application Blocked'),
        (APPLICATION_LIMITED, 'Application Usage Limited'),
        (DOWNLOAD_ATTEMPTED, 'Download Attempted'),
        (DOWNLOAD_BLOCKED, 'Download Blocked'),
        (SCREEN_TIME_WARNING, 'Screen Time Warning'),
        (SCREEN_TIME_LIMIT_REACHED, 'Screen Time Limit Reached'),
        (POLICY_CHANGED, 'Policy Changed'),
        (AI_ANALYSIS_FAILED, 'AI Analysis Failed'),
    ]

    # ── Severity Levels ───────────────────────────────────────────────────────
    SEV_LOW = 'LOW'
    SEV_MEDIUM = 'MEDIUM'
    SEV_HIGH = 'HIGH'
    SEV_CRITICAL = 'CRITICAL'
    SEVERITY_CHOICES = [
        (SEV_LOW, 'Low'),
        (SEV_MEDIUM, 'Medium'),
        (SEV_HIGH, 'High'),
        (SEV_CRITICAL, 'Critical'),
    ]

    # ── Actions ────────────────────────────────────────────────────────────────
    ACTION_ALLOW = 'ALLOW'
    ACTION_WARN = 'WARN'
    ACTION_BLUR = 'BLUR'
    ACTION_BLOCK = 'BLOCK'
    ACTION_LOG = 'LOG'
    ACTION_CHOICES = [
        (ACTION_ALLOW, 'Allow'),
        (ACTION_WARN, 'Warn'),
        (ACTION_BLUR, 'Blur'),
        (ACTION_BLOCK, 'Block'),
        (ACTION_LOG, 'Log Only'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(
        'accounts.Device', on_delete=models.CASCADE, related_name='activity_logs'
    )
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    severity = models.CharField(
        max_length=10, choices=SEVERITY_CHOICES, default=SEV_LOW, db_index=True
    )
    category = models.CharField(max_length=50, blank=True, db_index=True)
    # domain stored separately from full URL for privacy and indexing
    domain = models.CharField(max_length=255, blank=True, db_index=True)
    url_path = models.CharField(
        max_length=512, blank=True,
        help_text='URL path without query string — avoids capturing sensitive query params.'
    )
    app_name = models.CharField(max_length=100, blank=True)
    action_taken = models.CharField(max_length=10, choices=ACTION_CHOICES)
    # metadata stores minimal context: browser name, file extension (for downloads), etc.
    # Never store full page content or form data here.
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['severity', 'timestamp']),
            models.Index(fields=['domain']),
        ]

    def __str__(self):
        return f'{self.event_type} | {self.device} | {self.timestamp}'


class ThreatEvent(models.Model):
    """
    Detailed threat information linked to an ActivityLog entry.
    Contains AI analysis results for threat-type events.

    IMPORTANT: inference_mode must always be checked.
    'MOCK' results are development-time heuristics only.
    """
    INFERENCE_REAL = 'REAL'
    INFERENCE_MOCK = 'MOCK'
    INFERENCE_MODE_CHOICES = [
        (INFERENCE_REAL, 'Real ONNX Inference'),
        (INFERENCE_MOCK, 'Mock/Development Heuristic'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity_log = models.OneToOneField(
        ActivityLog, on_delete=models.CASCADE, related_name='threat_event'
    )
    threat_type = models.CharField(max_length=50, db_index=True)
    risk_score = models.FloatField(help_text='0.0 (safe) to 1.0 (definite threat)')
    confidence = models.FloatField(help_text='Model confidence in the classification (0.0–1.0)')
    ai_category = models.CharField(max_length=100)
    # indicators: list of explainable features that contributed to the classification
    indicators = models.JSONField(
        default=list,
        help_text='Explainable indicators — e.g. ["contains_sexual_content", "suspicious_domain"]'
    )
    # ALWAYS store this — the UI should display MOCK warnings prominently
    inference_mode = models.CharField(
        max_length=10, choices=INFERENCE_MODE_CHOICES, default=INFERENCE_MOCK
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Threat Event'
        verbose_name_plural = 'Threat Events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['threat_type', 'created_at']),
        ]

    def __str__(self):
        return f'{self.threat_type} risk={self.risk_score:.2f} [{self.inference_mode}]'


class AIAnalysis(models.Model):
    """
    Record of AI analysis results.
    content_hash (SHA-256) allows deduplication without storing raw content.
    """
    INPUT_TEXT = 'TEXT'
    INPUT_URL = 'URL'
    INPUT_IMAGE = 'IMAGE'
    INPUT_TYPE_CHOICES = [
        (INPUT_TEXT, 'Text Content'),
        (INPUT_URL, 'URL'),
        (INPUT_IMAGE, 'Image'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(
        'accounts.Device', on_delete=models.CASCADE, related_name='ai_analyses'
    )
    input_type = models.CharField(max_length=10, choices=INPUT_TYPE_CHOICES)
    # SHA-256 of the raw input — used for caching/deduplication.
    # We store the hash, never the raw content.
    content_hash = models.CharField(max_length=64, db_index=True)
    category = models.CharField(max_length=100)
    risk_score = models.FloatField()
    confidence = models.FloatField()
    recommended_action = models.CharField(max_length=10)
    inference_mode = models.CharField(
        max_length=10,
        choices=[('REAL', 'Real'), ('MOCK', 'Mock')],
        default='MOCK'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'AI Analysis'
        verbose_name_plural = 'AI Analyses'
        ordering = ['-created_at']

    def __str__(self):
        return f'AIAnalysis({self.input_type}, {self.category}, risk={self.risk_score:.2f})'


class ScreenTimeUsage(models.Model):
    """
    Daily screen-time usage record for a device.
    Updated by the desktop agent periodically.
    app_breakdown: {app_name: minutes_used}
    """
    device = models.ForeignKey(
        'accounts.Device', on_delete=models.CASCADE, related_name='screen_time_usage'
    )
    date = models.DateField(db_index=True)
    total_minutes = models.IntegerField(default=0)
    # app_breakdown: {"firefox": 45, "youtube": 30, ...}
    app_breakdown = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Screen Time Usage'
        verbose_name_plural = 'Screen Time Usage Records'
        unique_together = [('device', 'date')]
        indexes = [
            models.Index(fields=['device', 'date']),
        ]

    def __str__(self):
        return f'{self.device.name} | {self.date} | {self.total_minutes}min'
