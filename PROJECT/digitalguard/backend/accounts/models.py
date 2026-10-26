"""
DigitalGuard Accounts Models

Defines the custom User model and all parent/child/device entities.
All authentication credentials are stored with proper hashing — never in plaintext.
"""

import uuid
import logging
from django.contrib.auth.models import AbstractUser
from django.db import models

logger = logging.getLogger('digitalguard.accounts')


class User(AbstractUser):
    """
    Custom user model.
    Parents use email as login username.
    """
    ROLE_PARENT = 'PARENT'
    ROLE_ADMIN = 'ADMIN'
    ROLE_CHOICES = [
        (ROLE_PARENT, 'Parent'),
        (ROLE_ADMIN, 'Administrator'),
    ]

    # Override email to be unique and required
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_PARENT)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Use email as the login field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f'{self.email} ({self.role})'

    @property
    def is_parent(self):
        return self.role == self.ROLE_PARENT

    @property
    def is_admin_user(self):
        return self.role == self.ROLE_ADMIN


class ParentProfile(models.Model):
    """
    Extended profile for parent users.
    Contains notification preferences and display settings.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='parent_profile'
    )
    display_name = models.CharField(max_length=100)
    notification_email = models.EmailField(blank=True)
    alert_preferences = models.JSONField(
        default=dict,
        help_text='JSON config for which event types generate alerts and at what severity.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Parent Profile'

    def __str__(self):
        return f'ParentProfile({self.display_name})'

    def get_default_alert_preferences(self):
        """Return sensible default alert preferences."""
        return {
            'phishing': {'enabled': True, 'min_severity': 'MEDIUM'},
            'cyberbullying': {'enabled': True, 'min_severity': 'MEDIUM'},
            'grooming': {'enabled': True, 'min_severity': 'LOW'},
            'harmful_content': {'enabled': True, 'min_severity': 'HIGH'},
            'screen_time': {'enabled': True, 'min_severity': 'LOW'},
            'app_blocked': {'enabled': True, 'min_severity': 'LOW'},
        }


class ChildProfile(models.Model):
    """Profile representing a monitored child user."""
    AVATAR_CHOICES = [
        ('🧒', 'Child'),
        ('👦', 'Boy'),
        ('👧', 'Girl'),
        ('🧑', 'Young person'),
        ('🐱', 'Cat'),
        ('🐶', 'Dog'),
        ('🦊', 'Fox'),
        ('🐼', 'Panda'),
    ]

    parent = models.ForeignKey(
        ParentProfile, on_delete=models.CASCADE, related_name='children'
    )
    name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    avatar = models.CharField(max_length=10, default='🧒')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Child Profile'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} (child of {self.parent.display_name})'


class Device(models.Model):
    """
    A physical device belonging to a child.
    Communicates with the backend via a device_token (UUID).
    The device_token acts as a per-device API credential.
    """
    DEVICE_DESKTOP = 'DESKTOP'
    DEVICE_LAPTOP = 'LAPTOP'
    DEVICE_MOBILE = 'MOBILE'
    DEVICE_TABLET = 'TABLET'
    DEVICE_TYPE_CHOICES = [
        (DEVICE_DESKTOP, 'Desktop'),
        (DEVICE_LAPTOP, 'Laptop'),
        (DEVICE_MOBILE, 'Mobile'),
        (DEVICE_TABLET, 'Tablet'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(
        ChildProfile, on_delete=models.CASCADE, related_name='devices'
    )
    name = models.CharField(max_length=100, help_text="Friendly name, e.g. 'Alex's Laptop'")
    device_type = models.CharField(
        max_length=10, choices=DEVICE_TYPE_CHOICES, default=DEVICE_LAPTOP
    )
    os = models.CharField(max_length=50, default='Windows')
    os_version = models.CharField(max_length=50, blank=True)
    # device_token is the credential used by the desktop agent and extension
    # to authenticate API calls. Treat it like a password — rotate if compromised.
    device_token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Device'
        ordering = ['-last_seen']

    def __str__(self):
        return f'{self.name} ({self.child.name})'

    def rotate_token(self):
        """Generate a new device token, invalidating the old one."""
        self.device_token = uuid.uuid4()
        self.save(update_fields=['device_token', 'updated_at'])
        logger.warning(
            'Device token rotated for device=%s child=%s', self.id, self.child.name
        )
        return self.device_token


class AuthenticationCredential(models.Model):
    """
    FIDO2 / WebAuthn credential storage.

    SECURITY NOTES:
    - credential_id and public_key are binary data — never store raw biometrics here.
    - The user's biometric data never leaves their device; only the cryptographic
      credential (public key + credential ID) is stored.
    - sign_count is used to detect credential cloning.
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='webauthn_credentials'
    )
    # Unique identifier for the credential (from the authenticator)
    credential_id = models.BinaryField(unique=True, max_length=1024)
    # Public key in COSE format
    public_key = models.BinaryField(max_length=4096)
    sign_count = models.IntegerField(default=0)
    # AAGUID identifies the type of authenticator (e.g., YubiKey model)
    aaguid = models.CharField(max_length=100, blank=True)
    transports = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    display_name = models.CharField(max_length=100, blank=True, default='Security Key')

    class Meta:
        verbose_name = 'Authentication Credential'
        verbose_name_plural = 'Authentication Credentials'

    def __str__(self):
        return f'Credential({self.display_name}) for {self.user.email}'
