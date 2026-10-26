"""
Policies views — website, application, and screen-time policy CRUD.
All mutations are logged for auditing purposes.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsParent
from api.utils import success_response, error_response
from .models import WebsitePolicy, ApplicationPolicy, ScreenTimePolicy
from .serializers import (
    WebsitePolicySerializer, ApplicationPolicySerializer, ScreenTimePolicySerializer
)

logger = logging.getLogger('digitalguard.policies')


class WebsitePolicyViewSet(viewsets.ModelViewSet):
    """
    /api/policies/websites/
    CRUD for website policies. Authenticated parents only.
    Changes are applied immediately (extension polls policy on each navigation).
    """
    permission_classes = [IsParent]
    serializer_class = WebsitePolicySerializer

    def get_queryset(self):
        parent = self.request.user.parent_profile
        qs = WebsitePolicy.objects.filter(parent=parent).order_by('-created_at')
        child_id = self.request.query_params.get('child_id')
        if child_id:
            qs = qs.filter(child_id=child_id)
        return qs

    def perform_create(self, serializer):
        policy = serializer.save(parent=self.request.user.parent_profile)
        logger.info('Website policy created: %s by %s', policy, self.request.user.email)

    def perform_update(self, serializer):
        policy = serializer.save()
        logger.info('Website policy updated: %s by %s', policy, self.request.user.email)

    def perform_destroy(self, instance):
        logger.info('Website policy deleted: %s by %s', instance, self.request.user.email)
        instance.delete()

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response(success_response(serializer.data))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(success_response(serializer.data, 'Policy created.'), status=status.HTTP_201_CREATED)


class ApplicationPolicyViewSet(viewsets.ModelViewSet):
    """
    /api/policies/applications/
    CRUD for application policies.
    """
    permission_classes = [IsParent]
    serializer_class = ApplicationPolicySerializer

    def get_queryset(self):
        parent = self.request.user.parent_profile
        return ApplicationPolicy.objects.filter(parent=parent).order_by('-created_at')

    def perform_create(self, serializer):
        policy = serializer.save(parent=self.request.user.parent_profile)
        logger.info('App policy created: %s by %s', policy, self.request.user.email)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(success_response(serializer.data))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(success_response(serializer.data, 'Application policy created.'), status=status.HTTP_201_CREATED)


class ScreenTimePolicyViewSet(viewsets.ModelViewSet):
    """
    /api/screentime/policies/
    CRUD for screen-time policies (one per child).
    """
    permission_classes = [IsParent]
    serializer_class = ScreenTimePolicySerializer

    def get_queryset(self):
        parent = self.request.user.parent_profile
        return ScreenTimePolicy.objects.filter(
            child__parent=parent
        ).select_related('child').order_by('child__name')

    def perform_create(self, serializer):
        policy = serializer.save()
        logger.info('Screen time policy created for child %s by %s', policy.child.name, self.request.user.email)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(success_response(serializer.data))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(error_response(serializer.errors), status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response(success_response(serializer.data, 'Screen time policy created.'), status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsParent])
def check_url_policy(request):
    """
    GET /api/policies/check-url/?domain=example.com&child_id=1
    Returns the effective policy for a given domain and child.
    Used by the browser extension to check policies.
    """
    domain = request.query_params.get('domain', '').lower().strip()
    child_id = request.query_params.get('child_id')

    if not domain:
        return Response(error_response('domain parameter is required.'), status=status.HTTP_400_BAD_REQUEST)

    parent = request.user.parent_profile

    # Priority: domain-specific > category-level
    # Allow rules take precedence over block rules for the same domain
    qs = WebsitePolicy.objects.filter(
        parent=parent,
        is_active=True,
    ).filter(
        models_Q(child_id=child_id) | models_Q(child__isnull=True)
    )

    # Exact domain match
    domain_policy = qs.filter(domain__iexact=domain).first()
    if domain_policy:
        return Response(success_response({
            'domain': domain,
            'rule_type': domain_policy.rule_type,
            'source': 'domain_rule',
            'policy_id': domain_policy.id,
        }))

    # No explicit domain rule — return default
    return Response(success_response({
        'domain': domain,
        'rule_type': 'ALLOW',
        'source': 'default',
        'policy_id': None,
    }))
