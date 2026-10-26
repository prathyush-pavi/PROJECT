from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/summary/', views.dashboard_summary, name='dashboard-summary'),

    # Activity logs
    path('activity/', views.ActivityLogListView.as_view(), name='activity-list'),
    path('activity/<uuid:pk>/', views.ActivityLogDetailView.as_view(), name='activity-detail'),
    path('activity/ingest/', views.ActivityIngestView.as_view(), name='activity-ingest'),

    # Screen time
    path('screentime/usage/', views.ScreenTimeUsageListView.as_view(), name='screentime-usage'),
    path('screentime/ingest/', views.ScreenTimeIngestView.as_view(), name='screentime-ingest'),
]
