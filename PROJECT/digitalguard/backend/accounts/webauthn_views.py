"""
DigitalGuard WebAuthn / FIDO2 Views

Implements the complete passkey registration and authentication ceremonies
using the py-webauthn library (https://github.com/duo-labs/py-webauthn).

Ceremonies:
  Registration (two steps):
    1. POST /api/auth/webauthn/register-options/
       Returns PublicKeyCredentialCreationOptions for navigator.credentials.create()
       Stores challenge in the server session (expires in 5 minutes).

    2. POST /api/auth/webauthn/register-verify/
       Verifies the credential from the authenticator and stores it in
       AuthenticationCredential. Requires JWT authentication.

  Authentication (two steps):
    1. POST /api/auth/webauthn/auth-options/
       Takes user email, returns PublicKeyCredentialRequestOptions for
       navigator.credentials.get(). Stores challenge in session.
       Public endpoint — no auth required.

    2. POST /api/auth/webauthn/auth-verify/
       Verifies the assertion response, updates sign_count,
       and issues JWT tokens (same format as password login).
       Public endpoint — no prior auth required.

Security notes:
  - Challenges are single-use and session-scoped (5-minute TTL via SESSION_COOKIE_AGE).
  - sign_count is checked to detect credential cloning.
  - Raw biometric data never reaches the server — only the cryptographic credential.
  - Credentials can be listed and deleted from /api/auth/passkeys/.
"""

import logging
from django.conf import settings
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from api.utils import success_response, error_response
from .models import User, AuthenticationCredential

logger = logging.getLogger('digitalguard.accounts.webauthn')


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_webauthn():
    """Import py-webauthn — raises ImportError with helpful message if not installed."""
    try:
        import webauthn
        return webauthn
    except ImportError:
        raise ImportError(
            'py-webauthn is required for passkey support. '
            'Install it: pip install py-webauthn>=2.0'
        )


def _rp_config():
    return {
        'rp_id': getattr(settings, 'WEBAUTHN_RP_ID', 'localhost'),
        'rp_name': getattr(settings, 'WEBAUTHN_RP_NAME', 'DigitalGuard'),
        'origin': getattr(settings, 'WEBAUTHN_ORIGIN', 'http://localhost:8000'),
    }


def _issue_jwt_for_user(user):
    """Issue JWT access + refresh tokens for a user. Same format as password login."""
    refresh = RefreshToken.for_user(user)
    display_name = (
        user.parent_profile.display_name
        if hasattr(user, 'parent_profile') else user.username
    )
    return {
        'tokens': {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        },
        'user': {
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'display_name': display_name,
        },
    }


# ── Step 1: Registration Options ───────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def webauthn_register_options(request):
    """
    POST /api/auth/webauthn/register-options/
    Requires: JWT authentication.

    Generates PublicKeyCredentialCreationOptions for navigator.credentials.create().
    The challenge is stored in the server session (5-minute TTL).

    Response body is base64url-safe JSON suitable for passing directly to
    the WebAuthn browser API (after minimal client-side transformation).
    """
    try:
        webauthn = _get_webauthn()
    except ImportError as e:
        return Response(error_response(str(e)), status=status.HTTP_503_SERVICE_UNAVAILABLE)

    user = request.user
    rp = _rp_config()

    # Collect existing credential IDs so they can be excluded (avoid re-registering same device)
    existing_credentials = AuthenticationCredential.objects.filter(user=user)
    exclude_credentials = [
        webauthn.PublicKeyCredentialDescriptor(id=bytes(cred.credential_id))
        for cred in existing_credentials
    ]

    try:
        options = webauthn.generate_registration_options(
            rp_id=rp['rp_id'],
            rp_name=rp['rp_name'],
            user_id=str(user.id).encode(),
            user_name=user.email,
            user_display_name=(
                user.parent_profile.display_name
                if hasattr(user, 'parent_profile') else user.username
            ),
            exclude_credentials=exclude_credentials,
            authenticator_selection=webauthn.AuthenticatorSelectionCriteria(
                authenticator_attachment=webauthn.AuthenticatorAttachment.PLATFORM,
                resident_key=webauthn.ResidentKeyRequirement.PREFERRED,
                user_verification=webauthn.UserVerificationRequirement.PREFERRED,
            ),
        )
    except Exception as e:
        logger.error('WebAuthn registration options error: %s', str(e))
        return Response(error_response(f'Failed to generate registration options: {str(e)}'), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Store challenge in session (will expire in SESSION_COOKIE_AGE seconds)
    request.session['webauthn_registration_challenge'] = webauthn.base64url_to_bytes(
        webauthn.options_to_json(options)['challenge']
    ).hex()
    request.session.modified = True

    return Response(success_response(
        webauthn.options_to_json(options),
        'Registration options generated. Complete the passkey prompt.'
    ))


# ── Step 2: Registration Verify ────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def webauthn_register_verify(request):
    """
    POST /api/auth/webauthn/register-verify/
    Requires: JWT authentication.

    Body: The full attestation response from navigator.credentials.create()
    as a JSON object with fields: id, rawId, response, type, clientExtensionResults.

    Verifies the attestation, then creates an AuthenticationCredential record.
    """
    try:
        webauthn = _get_webauthn()
    except ImportError as e:
        return Response(error_response(str(e)), status=status.HTTP_503_SERVICE_UNAVAILABLE)

    challenge_hex = request.session.get('webauthn_registration_challenge')
    if not challenge_hex:
        return Response(
            error_response('No registration challenge found. Please restart the registration process.', code='CHALLENGE_MISSING'),
            status=status.HTTP_400_BAD_REQUEST
        )

    rp = _rp_config()
    user = request.user

    try:
        expected_challenge = bytes.fromhex(challenge_hex)

        credential = webauthn.parse_registration_credential_json(request.data)

        verification = webauthn.verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp['rp_id'],
            expected_origin=rp['origin'],
            require_user_verification=False,
        )
    except Exception as e:
        logger.warning('WebAuthn registration verification failed for %s: %s', user.email, str(e))
        return Response(
            error_response(f'Passkey registration failed: {str(e)}', code='VERIFICATION_FAILED'),
            status=status.HTTP_400_BAD_REQUEST
        )

    # Clear the challenge from session (single-use)
    del request.session['webauthn_registration_challenge']
    request.session.modified = True

    # Extract optional transports
    transports = []
    if hasattr(credential, 'response') and hasattr(credential.response, 'transports'):
        transports = [t.value for t in (credential.response.transports or [])]

    # Save the credential
    display_name = request.data.get('credential_name', 'Passkey')
    auth_cred = AuthenticationCredential.objects.create(
        user=user,
        credential_id=verification.credential_id,
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count,
        aaguid=str(verification.aaguid) if verification.aaguid else '',
        transports=transports,
        last_used=timezone.now(),
        display_name=display_name[:100],
    )

    logger.info('Passkey registered for user %s (cred_id=%s)', user.email, verification.credential_id.hex()[:16])

    return Response(success_response({
        'credential_id': verification.credential_id.hex(),
        'display_name': auth_cred.display_name,
        'created_at': auth_cred.created_at.isoformat(),
    }, 'Passkey registered successfully.'), status=status.HTTP_201_CREATED)


# ── Step 3: Authentication Options ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def webauthn_auth_options(request):
    """
    POST /api/auth/webauthn/auth-options/
    Public endpoint — no authentication required.

    Body: {"email": "parent@example.com"}

    Returns PublicKeyCredentialRequestOptions for navigator.credentials.get().
    Stores challenge in session.
    """
    try:
        webauthn = _get_webauthn()
    except ImportError as e:
        return Response(error_response(str(e)), status=status.HTTP_503_SERVICE_UNAVAILABLE)

    email = request.data.get('email', '').strip().lower()
    if not email:
        return Response(error_response('email is required.'), status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Don't reveal whether the email exists — return generic options
        # with no allow_credentials (browser will show all stored passkeys)
        logger.debug('WebAuthn auth options requested for unknown email: %s', email)
        user = None

    rp = _rp_config()
    allow_credentials = []

    if user:
        credentials = AuthenticationCredential.objects.filter(user=user)
        allow_credentials = [
            webauthn.PublicKeyCredentialDescriptor(
                id=bytes(cred.credential_id),
                transports=[webauthn.AuthenticatorTransport(t) for t in (cred.transports or []) if t],
            )
            for cred in credentials
        ]

    try:
        options = webauthn.generate_authentication_options(
            rp_id=rp['rp_id'],
            allow_credentials=allow_credentials,
            user_verification=webauthn.UserVerificationRequirement.PREFERRED,
        )
    except Exception as e:
        logger.error('WebAuthn auth options error: %s', str(e))
        return Response(error_response(f'Failed to generate authentication options: {str(e)}'), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Store challenge + email hint in session
    request.session['webauthn_auth_challenge'] = webauthn.base64url_to_bytes(
        webauthn.options_to_json(options)['challenge']
    ).hex()
    request.session['webauthn_auth_email'] = email
    request.session.modified = True

    return Response(success_response(
        webauthn.options_to_json(options),
        'Authentication options generated.'
    ))


# ── Step 4: Authentication Verify ──────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def webauthn_auth_verify(request):
    """
    POST /api/auth/webauthn/auth-verify/
    Public endpoint — no authentication required.

    Body: The full assertion response from navigator.credentials.get()
    as a JSON object, plus an optional "email" field if email was not
    supplied in auth-options.

    On success, returns the same JWT token structure as the password login endpoint.
    """
    try:
        webauthn = _get_webauthn()
    except ImportError as e:
        return Response(error_response(str(e)), status=status.HTTP_503_SERVICE_UNAVAILABLE)

    challenge_hex = request.session.get('webauthn_auth_challenge')
    if not challenge_hex:
        return Response(
            error_response('No authentication challenge found. Please restart the sign-in process.', code='CHALLENGE_MISSING'),
            status=status.HTTP_400_BAD_REQUEST
        )

    rp = _rp_config()

    try:
        credential = webauthn.parse_authentication_credential_json(request.data)
    except Exception as e:
        return Response(error_response(f'Invalid credential data: {str(e)}'), status=status.HTTP_400_BAD_REQUEST)

    # Look up the stored credential by credential_id
    credential_id_bytes = webauthn.base64url_to_bytes(credential.raw_id)
    try:
        stored_cred = AuthenticationCredential.objects.select_related('user').get(
            credential_id=credential_id_bytes
        )
    except AuthenticationCredential.DoesNotExist:
        logger.warning('WebAuthn: unknown credential_id presented')
        return Response(
            error_response('Passkey not recognised.', code='UNKNOWN_CREDENTIAL'),
            status=status.HTTP_401_UNAUTHORIZED
        )

    user = stored_cred.user
    expected_challenge = bytes.fromhex(challenge_hex)

    try:
        verification = webauthn.verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp['rp_id'],
            expected_origin=rp['origin'],
            credential_public_key=bytes(stored_cred.public_key),
            credential_current_sign_count=stored_cred.sign_count,
            require_user_verification=False,
        )
    except Exception as e:
        logger.warning('WebAuthn authentication verification failed for user %s: %s', user.email, str(e))
        return Response(
            error_response(f'Passkey authentication failed: {str(e)}', code='VERIFICATION_FAILED'),
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Clear challenge from session (single-use)
    del request.session['webauthn_auth_challenge']
    request.session.pop('webauthn_auth_email', None)
    request.session.modified = True

    # Update sign_count (detects credential cloning if count goes backward)
    stored_cred.sign_count = verification.new_sign_count
    stored_cred.last_used = timezone.now()
    stored_cred.save(update_fields=['sign_count', 'last_used'])

    logger.info('Passkey authentication successful for user %s', user.email)

    return Response(success_response(
        _issue_jwt_for_user(user),
        'Passkey authentication successful.'
    ))


# ── Credential Management ──────────────────────────────────────────────────────

@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def webauthn_passkeys(request, pk=None):
    """
    GET /api/auth/passkeys/
    List all passkeys registered for the current user.

    DELETE /api/auth/passkeys/<id>/
    Delete a registered passkey.
    """
    user = request.user

    if request.method == 'GET':
        credentials = AuthenticationCredential.objects.filter(user=user).order_by('-created_at')
        from .serializers import AuthenticationCredentialSerializer
        serializer = AuthenticationCredentialSerializer(credentials, many=True)
        return Response(success_response(serializer.data))

    elif request.method == 'DELETE':
        if not pk:
            return Response(error_response('Credential ID is required.'), status=status.HTTP_400_BAD_REQUEST)
        try:
            cred = AuthenticationCredential.objects.get(id=pk, user=user)
            cred.delete()
            logger.info('Passkey %s deleted by user %s', pk, user.email)
            return Response(success_response({}, 'Passkey deleted successfully.'))
        except AuthenticationCredential.DoesNotExist:
            return Response(error_response('Passkey not found.', code='NOT_FOUND'), status=status.HTTP_404_NOT_FOUND)
