"""
DigitalGuard Policies Models

Website policies, Application policies, Screen-time policies.
Parents configure these to control what their children can access.
"""

from django.db import models


class WebsitePolicy(models.Model):
    """
    Per-domain or per-category website policy.
    Domain rules take precedence over category rules.
    """
    RULE_BLOCK = 'BLOCK'
    RULE_ALLOW = 'ALLOW'
    RULE_WARN = 'WARN'
    RULE_TYPE_CHOICES = [
        (RULE_BLOCK, 'Block'),
        (RULE_ALLOW, 'Allow (whitelist override)'),
        (RULE_WARN, 'Warn (show warning, allow through)'),
    ]

    # Website risk categories — configurable here, not hard-coded in extension
    CATEGORY_SAFE = 'safe'
    CATEGORY_ADULT = 'adult'
    CATEGORY_GAMBLING = 'gambling'
    CATEGORY_VIOLENCE = 'violence'
    CATEGORY_PHISHING = 'phishing'
    CATEGORY_MALWARE = 'malware'
    CATEGORY_SOCIAL_MEDIA = 'social_media'
    CATEGORY_GAMING = 'gaming'
    CATEGORY_UNKNOWN = 'unknown'

    CATEGORY_CHOICES = [
        (CATEGORY_SAFE, 'Safe'),
        (CATEGORY_ADULT, 'Adult / Inappropriate'),
        (CATEGORY_GAMBLING, 'Gambling'),
        (CATEGORY_VIOLENCE, 'Violence'),
        (CATEGORY_PHISHING, 'Phishing'),
        (CATEGORY_MALWARE, 'Malware / Suspicious'),
        (CATEGORY_SOCIAL_MEDIA, 'Social Media'),
        (CATEGORY_GAMING, 'Gaming'),
        (CATEGORY_UNKNOWN, 'Unknown'),
    ]

    parent = models.ForeignKey(
        'accounts.ParentProfile', on_delete=models.CASCADE, related_name='website_policies'
    )
    # child=None means policy applies to ALL children of this parent
    child = models.ForeignKey(
        'accounts.ChildProfile', on_delete=models.CASCADE,
        related_name='website_policies', null=True, blank=True
    )
    # domain: exact domain match (e.g. "youtube.com")
    # Leave blank if this is a category-level rule
    domain = models.CharField(max_length=255, blank=True, db_index=True)
    # category: used when domain is blank
    category = models.CharField(max_length=30, blank=True, choices=CATEGORY_CHOICES)
    rule_type = models.CharField(max_length=10, choices=RULE_TYPE_CHOICES)
    reason = models.CharField(max_length=500, blank=True, help_text='Optional note for this rule.')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Website Policy'
        verbose_name_plural = 'Website Policies'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['parent', 'domain']),
            models.Index(fields=['parent', 'category']),
        ]

    def __str__(self):
        target = self.domain or f'[category: {self.category}]'
        return f'{self.rule_type} {target} (parent={self.parent.display_name})'

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.domain and not self.category:
            raise ValidationError('Either domain or category must be specified.')
        if self.domain and self.category:
            raise ValidationError('Specify either domain OR category, not both.')


class ApplicationPolicy(models.Model):
    """Policy for a specific application on the child's device."""
    POLICY_ALLOW = 'ALLOW'
    POLICY_BLOCK = 'BLOCK'
    POLICY_LIMITED = 'LIMITED'
    POLICY_CHOICES = [
        (POLICY_ALLOW, 'Allow'),
        (POLICY_BLOCK, 'Block'),
        (POLICY_LIMITED, 'Limited (time-based)'),
    ]

    parent = models.ForeignKey(
        'accounts.ParentProfile', on_delete=models.CASCADE, related_name='app_policies'
    )
    child = models.ForeignKey(
        'accounts.ChildProfile', on_delete=models.CASCADE,
        related_name='app_policies', null=True, blank=True
    )
    app_name = models.CharField(max_length=100, help_text='Application name (case-insensitive match)')
    policy = models.CharField(max_length=10, choices=POLICY_CHOICES, default=POLICY_ALLOW)
    daily_limit_minutes = models.IntegerField(
        null=True, blank=True,
        help_text='Used only when policy=LIMITED. Max minutes per day.'
    )
    reason = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Application Policy'
        verbose_name_plural = 'Application Policies'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.policy} {self.app_name}'


class ScreenTimePolicy(models.Model):
    """
    Screen-time limits and allowed usage hours for a child.
    One policy per child. Use update to change existing policy.
    """
    child = models.OneToOneField(
        'accounts.ChildProfile', on_delete=models.CASCADE, related_name='screen_time_policy'
    )
    daily_limit_minutes = models.IntegerField(
        null=True, blank=True, help_text='Max total screen time per day (minutes).'
    )
    weekend_limit_minutes = models.IntegerField(
        null=True, blank=True, help_text='Override limit for weekends (minutes).'
    )
    # Allowed usage window — e.g. only between 08:00 and 21:00
    allowed_start = models.TimeField(null=True, blank=True, help_text='Start of allowed usage window.')
    allowed_end = models.TimeField(null=True, blank=True, help_text='End of allowed usage window.')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Screen Time Policy'
        verbose_name_plural = 'Screen Time Policies'

    def __str__(self):
        return f'ScreenTimePolicy({self.child.name}, limit={self.daily_limit_minutes}min)'
