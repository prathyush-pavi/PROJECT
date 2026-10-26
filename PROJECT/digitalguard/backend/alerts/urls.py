from django.urls import path
from . import views

urlpatterns = [
    path('alerts/', views.AlertListView.as_view(), name='alert-list'),
    path('alerts/mark-all-read/', views.mark_all_alerts_read, name='alert-mark-all-read'),
    path('alerts/<uuid:pk>/', views.AlertDetailView.as_view(), name='alert-detail'),
    path('alerts/<uuid:pk>/mark-read/', views.AlertMarkReadView.as_view(), name='alert-mark-read'),
    path('alerts/<uuid:pk>/delete/', views.AlertDeleteView.as_view(), name='alert-delete'),
]
