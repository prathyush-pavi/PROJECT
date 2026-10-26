from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'parent', 'child', 'period_start', 'period_end', 'created_at')
    list_filter = ('report_type',)
    readonly_fields = ('id', 'data', 'created_at')
