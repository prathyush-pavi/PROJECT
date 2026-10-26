from django.contrib import admin
from .models import ActivityLog, ThreatEvent, AIAnalysis, ScreenTimeUsage


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'device', 'severity', 'domain', 'action_taken', 'timestamp')
    list_filter = ('event_type', 'severity', 'action_taken')
    search_fields = ('domain', 'app_name', 'device__name')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'timestamp'


@admin.register(ThreatEvent)
class ThreatEventAdmin(admin.ModelAdmin):
    list_display = ('threat_type', 'risk_score', 'confidence', 'inference_mode', 'created_at')
    list_filter = ('threat_type', 'inference_mode')
    readonly_fields = ('id', 'created_at')


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ('input_type', 'category', 'risk_score', 'inference_mode', 'created_at')
    list_filter = ('input_type', 'inference_mode')
    readonly_fields = ('id', 'content_hash', 'created_at')


@admin.register(ScreenTimeUsage)
class ScreenTimeUsageAdmin(admin.ModelAdmin):
    list_display = ('device', 'date', 'total_minutes', 'updated_at')
    list_filter = ('date',)
    search_fields = ('device__name', 'device__child__name')
