from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views, webauthn_views

router = DefaultRouter()
router.register('children', views.ChildViewSet, basename='children')
router.register('devices', views.DeviceViewSet, basename='devices')

urlpatterns = [
    # Authentication
    path('auth/register/', views.RegisterView.as_view(), name='auth-register'),
    path('auth/login/', views.LoginView.as_view(), name='auth-login'),
    path('auth/logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/profile/', views.ParentProfileView.as_view(), name='auth-profile'),

    # Passkey / WebAuthn / FIDO2
    path('auth/webauthn/register-options/', webauthn_views.webauthn_register_options, name='webauthn-register-options'),
    path('auth/webauthn/register-verify/', webauthn_views.webauthn_register_verify, name='webauthn-register-verify'),
    path('auth/webauthn/auth-options/', webauthn_views.webauthn_auth_options, name='webauthn-auth-options'),
    path('auth/webauthn/auth-verify/', webauthn_views.webauthn_auth_verify, name='webauthn-auth-verify'),
    path('auth/passkeys/', webauthn_views.webauthn_passkeys, name='passkey-list'),
    path('auth/passkeys/<uuid:pk>/', webauthn_views.webauthn_passkeys, name='passkey-detail'),

    # Children & Devices
    path('', include(router.urls)),
]

