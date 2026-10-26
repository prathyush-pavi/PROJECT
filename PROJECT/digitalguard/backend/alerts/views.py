"""Alerts views."""

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsParent
from api.utils import success_response, error_response
from .models import Alert
from .serializers import AlertSerializer


class AlertListView(generics.ListAPIView):
    """GET /api/alerts/ — list all alerts for the authenticated parent."""
    permission_classes = [IsParent]
    serializer_class = AlertSerializer

    def get_queryset(self):
        qs = Alert.objects.filter(parent=self.request.user.parent_profile)
        unread_only = self.request.query_params.get('unread_only', 'false').lower() == 'true'
        severity = self.request.query_params.get('severity')
        alert_type = self.request.query_params.get('alert_type')
        if unread_only:
            qs = qs.filter(is_read=False)
        if severity:
            qs = qs.filter(severity=severity.upper())
        if alert_type:
            qs = qs.filter(alert_type=alert_type.upper())
        return qs.select_related('child')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return Response(success_response(self.get_paginated_response(serializer.data).data))
        serializer = self.get_serializer(qs, many=True)
        return Response(success_response(serializer.data))


class AlertDetailView(generics.RetrieveAPIView):
    """GET /api/alerts/<id>/"""
    permission_classes = [IsParent]
    serializer_class = AlertSerializer

    def get_queryset(self):
        return Alert.objects.filter(parent=self.request.user.parent_profile)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(success_response(serializer.data))


class AlertMarkReadView(generics.UpdateAPIView):
    """PATCH /api/alerts/<id>/mark-read/"""
    permission_classes = [IsParent]

    def get_queryset(self):
        return Alert.objects.filter(parent=self.request.user.parent_profile)

    def patch(self, request, *args, **kwargs):
        alert = self.get_object()
        alert.is_read = True
        alert.save(update_fields=['is_read'])
        return Response(success_response({'id': str(alert.id), 'is_read': True}, 'Alert marked as read.'))


@api_view(['POST'])
@permission_classes([IsParent])
def mark_all_alerts_read(request):
    """POST /api/alerts/mark-all-read/"""
    count = Alert.objects.filter(
        parent=request.user.parent_profile, is_read=False
    ).update(is_read=True)
    return Response(success_response({'marked_read': count}, f'{count} alerts marked as read.'))


class AlertDeleteView(generics.DestroyAPIView):
    """DELETE /api/alerts/<id>/"""
    permission_classes = [IsParent]

    def get_queryset(self):
        return Alert.objects.filter(parent=self.request.user.parent_profile)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(success_response({}, 'Alert deleted.'))
