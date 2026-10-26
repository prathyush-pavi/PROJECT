"""
Accounts views — authentication, parent profiles, children, devices.
All endpoints require authentication unless explicitly marked public.
"""

import logging
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from api.utils import success_response, error_response
from .models import ParentProfile, ChildProfile, Device
from .serializers import (
    RegisterSerializer, CustomTokenObtainPairSerializer,
    ParentProfileSerializer, ChildProfileSerializer,
    DeviceSerializer, DeviceTokenSerializer,
)
from .permissions import IsParent, OwnChildrenOnly

logger = logging.getLogger('digitalguard.accounts')


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Register a new parent account. Public endpoint.
    """
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        logger.info('New parent registered: %s', user.email)
        return Response(
            success_response({'email': user.email}, 'Registration successful. You can now log in.'),
            status=status.HTTP_201_CREATED
        )


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Returns JWT access + refresh tokens. Public endpoint.
    """
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            logger.info('Login successful for: %s', request.data.get('email', 'unknown'))
            return Response(success_response(response.data, 'Login successful.'))
        return Response(error_response('Invalid credentials.', code='AUTH_FAILED'), status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(generics.GenericAPIView):
    """
    POST /api/auth/logout/
    Blacklists the refresh token, invalidating the session.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                error_response('Refresh token is required.', code='MISSING_TOKEN'),
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info('User logged out: %s', request.user.email)
            return Response(success_response({}, 'Logged out successfully.'))
        except Exception as e:
            logger.warning('Logout error for %s: %s', request.user.email, str(e))
            return Response(error_response('Invalid or already blacklisted token.'), status=status.HTTP_400_BAD_REQUEST)


class ParentProfileView(generics.RetrieveUpdateAPIView):
    """
    GET/PUT/PATCH /api/auth/profile/
    View and update the authenticated parent's profile.
    """
    permission_classes = [IsParent]
    serializer_class = ParentProfileSerializer

    def get_object(self):
        return self.request.user.parent_profile


class ChildViewSet(viewsets.ModelViewSet):
    """
    /api/children/
    CRUD for child profiles belonging to the authenticated parent.
    """
    permission_classes = [IsParent, OwnChildrenOnly]
    serializer_class = ChildProfileSerializer

    def get_queryset(self):
        return ChildProfile.objects.filter(
            parent=self.request.user.parent_profile
        ).order_by('name')

    def perform_create(self, serializer):
        serializer.save(parent=self.request.user.parent_profile)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response(success_response(serializer.data))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(success_response(serializer.data))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(success_response(serializer.data, 'Child profile created.'), status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        return Response(success_response(serializer.data, 'Child profile updated.'))


class DeviceViewSet(viewsets.ModelViewSet):
    """
    /api/devices/
    CRUD for devices belonging to the authenticated parent's children.
    """
    permission_classes = [IsParent, OwnChildrenOnly]
    serializer_class = DeviceSerializer

    def get_queryset(self):
        parent = self.request.user.parent_profile
        return Device.objects.filter(
            child__parent=parent
        ).select_related('child').order_by('-last_seen')

    def perform_create(self, serializer):
        device = serializer.save()
        logger.info('New device registered: %s for child %s', device.name, device.child.name)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        # Return the token on creation (only time it's shown in full)
        token_serializer = DeviceTokenSerializer(serializer.instance)
        return Response(
            success_response(
                token_serializer.data,
                'Device registered. Save the device_token — it will not be shown again in full.'
            ),
            status=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response(success_response(serializer.data))

    @action(detail=True, methods=['post'], url_path='rotate-token')
    def rotate_token(self, request, pk=None):
        """
        POST /api/devices/<id>/rotate-token/
        Generate a new device token, invalidating the old one.
        Use this if a token is suspected to be compromised.
        """
        device = self.get_object()
        new_token = device.rotate_token()
        logger.warning('Device token rotated by parent %s for device %s', request.user.email, device.id)
        return Response(success_response(
            {'device_id': str(device.id), 'device_token': str(new_token)},
            'Token rotated. Update the desktop agent configuration with the new token.'
        ))

    @action(detail=True, methods=['get'], url_path='heartbeat')
    def heartbeat(self, request, pk=None):
        """
        GET /api/devices/<id>/heartbeat/
        Returns last-seen time and active status for a device.
        """
        device = self.get_object()
        return Response(success_response({
            'device_id': str(device.id),
            'last_seen': device.last_seen,
            'is_active': device.is_active,
        }))
