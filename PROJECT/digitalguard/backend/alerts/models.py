"""
DigitalGuard Alerts Models + Alert Generation Utility

Alerts are generated automatically when high/critical severity events occur.
Parents can read and dismiss alerts from the dashboard.
"""

import uuid
import logging
from django.db import models

logger = logging.getLogger('digitalguard.alerts')


class Alert(models.Model):
    """
    Parent-facing alert generated when a significant threat is detected.
    """
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

    ALERT_PHISHING = 'PHISHING'
    ALERT_CYBERBULLYING = 'CYBERBULLYING'
    ALERT_GROOMING = 'GROOMING_RISK'
    ALERT_HARMFUL_CONTENT = 'HARMFUL_CONTENT'
    ALERT_DOWNLOAD = 'SUSPICIOUS_DOWNLOAD'
    ALERT_APP_BLOCKED = 'APP_BLOCKED'
    ALERT_SCREEN_TIME = 'SCREEN_TIME'
    ALERT_WEBSITE_BLOCKED = 'WEBSITE_BLOCKED'
    ALERT_SYSTEM = 'SYSTEM'
    ALERT_TYPE_CHOICES = [
        (ALERT_PHISHING, 'Phishing Detected'),
        (ALERT_CYBERBULLYING, 'Cyberbullying Detected'),
        (ALERT_GROOMING, 'Grooming Risk Detected'),
        (ALERT_HARMFUL_CONTENT, 'Harmful Content'),
        (ALERT_DOWNLOAD, 'Suspicious Download'),
        (ALERT_APP_BLOCKED, 'Application Blocked'),
        (ALERT_SCREEN_TIME, 'Screen Time Limit'),
        (ALERT_WEBSITE_BLOCKED, 'Website Blocked'),
        (ALERT_SYSTEM, 'System Alert'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(
        'accounts.ParentProfile', on_delete=models.CASCADE, related_name='alerts'
    )
    child = models.ForeignKey(
        'accounts.ChildProfile', on_delete=models.CASCADE,
        related_name='alerts', null=True, blank=True
    )
    # Link to the triggering activity log (optional — system alerts may not have one)
    activity_log = models.ForeignKey(
        'monitoring.ActivityLog', on_delete=models.SET_NULL,
        related_name='alerts', null=True, blank=True
    )
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES, db_index=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['parent', 'is_read', 'created_at']),
            models.Index(fields=['parent', 'alert_type']),
        ]

    def __str__(self):
        return f'[{self.severity}] {self.alert_type}: {self.title}'
