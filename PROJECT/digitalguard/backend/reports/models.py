"""
Reports models.
"""

import uuid
from django.db import models


class Report(models.Model):
    """
    Generated activity/threat reports for a date range.
    Report data is stored as JSON — computed at generation time.
    """
    REPORT_WEEKLY = 'WEEKLY'
    REPORT_MONTHLY = 'MONTHLY'
    REPORT_CUSTOM = 'CUSTOM'
    TYPE_WEEKLY = REPORT_WEEKLY
    TYPE_MONTHLY = REPORT_MONTHLY
    TYPE_CUSTOM = REPORT_CUSTOM
    REPORT_TYPE_CHOICES = [
        (REPORT_WEEKLY, 'Weekly Summary'),
        (REPORT_MONTHLY, 'Monthly Summary'),
        (REPORT_CUSTOM, 'Custom Date Range'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(
        'accounts.ParentProfile', on_delete=models.CASCADE, related_name='reports'
    )
    child = models.ForeignKey(
        'accounts.ChildProfile', on_delete=models.CASCADE,
        related_name='reports', null=True, blank=True
    )
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    # Pre-computed summary data
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.report_type} {self.period_start}–{self.period_end}'
