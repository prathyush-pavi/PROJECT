"""
Accounts permissions — custom DRF permission classes.
"""

from rest_framework.permissions import BasePermission
from .models import ChildProfile, Device


class IsParent(BasePermission):
    """Allow access only to authenticated parent users."""
    message = 'Only parent accounts can access this resource.'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ('PARENT', 'ADMIN')
        )


class IsDeviceAuthenticated(BasePermission):
    """Allow access only to requests authenticated via DeviceToken."""
    message = 'Device token authentication required.'

    def has_permission(self, request, view):
        # request.auth is set to the Device instance by DeviceTokenAuthentication
        return request.auth is not None and isinstance(request.auth, Device)


class IsParentOrDevice(BasePermission):
    """Allow access to parent users OR device token authenticated requests."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Parent/admin user
        if request.user.role in ('PARENT', 'ADMIN'):
            return True
        # Device token auth
        if isinstance(request.auth, Device):
            return True
        return False


class OwnChildrenOnly(BasePermission):
    """
    Object-level permission: parents can only access their own children's data.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'ADMIN':
            return True
        parent_profile = getattr(request.user, 'parent_profile', None)
        if not parent_profile:
            return False
        # Determine ownership based on obj type
        if isinstance(obj, ChildProfile):
            return obj.parent == parent_profile
        if isinstance(obj, Device):
            return obj.child.parent == parent_profile
        # For other objects with a child FK
        if hasattr(obj, 'child'):
            return obj.child.parent == parent_profile
        if hasattr(obj, 'parent'):
            return obj.parent == parent_profile
        return False
