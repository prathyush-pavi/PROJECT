from django.urls import path
from . import views

urlpatterns = [
    path('reports/', views.ReportListCreateView.as_view(), name='report-list'),
]
