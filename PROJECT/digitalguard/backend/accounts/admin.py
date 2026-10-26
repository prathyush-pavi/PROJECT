from django.contrib import admin
from .models import User, ParentProfile, ChildProfile, Device, AuthenticationCredential


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'role', 'is_active', 'is_verified', 'created_at')
    list_filter = ('role', 'is_active', 'is_verified')
    search_fields = ('email', 'username')
    readonly_fields = ('created_at',)


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user', 'notification_email', 'created_at')
    search_fields = ('display_name', 'user__email')
    readonly_fields = ('created_at',)


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'age', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'parent__display_name')
    readonly_fields = ('created_at',)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'child', 'device_type', 'os', 'is_active', 'last_seen')
    list_filter = ('device_type', 'is_active', 'os')
    search_fields = ('name', 'child__name')
    readonly_fields = ('id', 'device_token', 'last_seen', 'created_at')


@admin.register(AuthenticationCredential)
class AuthenticationCredentialAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user', 'aaguid', 'sign_count', 'created_at', 'last_used')
    search_fields = ('user__email', 'display_name')
    readonly_fields = ('credential_id', 'public_key', 'created_at')
