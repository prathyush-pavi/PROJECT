from django.urls import path
from . import views

urlpatterns = [
    path('ai/analyze/', views.analyze_text, name='ai-analyze'),
    path('ai/analyze-image/', views.analyze_image, name='ai-analyze-image'),
    path('browser/check-url/', views.check_url, name='browser-check-url'),
]
