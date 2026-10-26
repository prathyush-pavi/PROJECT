from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('policies/websites', views.WebsitePolicyViewSet, basename='website-policies')
router.register('policies/applications', views.ApplicationPolicyViewSet, basename='app-policies')
router.register('screentime/policies', views.ScreenTimePolicyViewSet, basename='screentime-policies')

urlpatterns = [
    path('', include(router.urls)),
    path('policies/check-url/', views.check_url_policy, name='check-url-policy'),
]
