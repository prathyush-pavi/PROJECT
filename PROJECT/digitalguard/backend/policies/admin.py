from django.contrib import admin
from .models import WebsitePolicy, ApplicationPolicy, ScreenTimePolicy


@admin.register(WebsitePolicy)
class WebsitePolicyAdmin(admin.ModelAdmin):
    list_display = ('rule_type', 'domain', 'category', 'parent', 'child', 'is_active', 'created_at')
    list_filter = ('rule_type', 'is_active', 'category')
    search_fields = ('domain', 'parent__display_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ApplicationPolicy)
class ApplicationPolicyAdmin(admin.ModelAdmin):
    list_display = ('app_name', 'policy', 'daily_limit_minutes', 'parent', 'is_active')
    list_filter = ('policy', 'is_active')
    search_fields = ('app_name', 'parent__display_name')


@admin.register(ScreenTimePolicy)
class ScreenTimePolicyAdmin(admin.ModelAdmin):
    list_display = ('child', 'daily_limit_minutes', 'weekend_limit_minutes', 'allowed_start', 'allowed_end', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('child__name',)
