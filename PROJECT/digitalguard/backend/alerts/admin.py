from django.contrib import admin
from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'alert_type', 'severity', 'child', 'is_read', 'created_at')
    list_filter = ('alert_type', 'severity', 'is_read')
    search_fields = ('title', 'message', 'child__name')
    readonly_fields = ('id', 'created_at')
