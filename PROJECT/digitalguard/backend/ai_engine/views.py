"""
AI Engine Django app — proxy views between the browser/extension and the local AI service.

The actual AI inference runs in a separate FastAPI process (ai-engine/main.py).
This Django app provides authenticated REST endpoints that:
1. Accept text/URL from the browser extension (via device token)
2. Forward to the local AI engine (localhost:8765)
3. Return the classification result
4. Store the AIAnalysis record (hash-based, no raw content)
5. Create ActivityLog/ThreatEvent as needed

PRIVACY NOTE: Raw text is sent to the local AI engine only.
Raw text is NEVER stored in the database — only the SHA-256 hash and classification.
"""

import hashlib
import logging
import httpx
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from accounts.permissions import IsDeviceAuthenticated, IsParentOrDevice
from api.utils import success_response, error_response
from monitoring.models import ActivityLog, ThreatEvent, AIAnalysis
from alerts.utils import create_alert_if_needed

logger = logging.getLogger('digitalguard.ai_engine')

AI_ENGINE_URL = getattr(settings, 'LOCAL_AI_ENDPOINT', 'http://127.0.0.1:8765')
AI_ENGINE_TIMEOUT = 10.0  # seconds


def _hash_content(text: str) -> str:
    """SHA-256 hash of content for deduplication without storing raw text."""
    return hashlib.sha256(text.encode('utf-8', errors='replace')).hexdigest()


def _call_ai_engine(endpoint: str, payload: dict) -> dict:
    """
    Call the local AI engine. Returns the JSON response or raises an exception.
    The AI engine binds to 127.0.0.1 only — never exposed externally.
    """
    url = f'{AI_ENGINE_URL}{endpoint}'
    try:
        with httpx.Client(timeout=AI_ENGINE_TIMEOUT) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise RuntimeError('AI engine is not running. Start it with: cd ai-engine && python main.py')
    except httpx.TimeoutException:
        raise RuntimeError('AI engine timed out.')
    except Exception as e:
        raise RuntimeError(f'AI engine error: {str(e)}')


@api_view(['POST'])
@permission_classes([IsDeviceAuthenticated])
def analyze_text(request):
    """
    POST /api/ai/analyze/
    Analyzes text content from the browser extension.
    Authenticated via device token.

    Body: {"text": "...", "context": "webpage|chat|comment"}
    Returns: {"category": "...", "risk_score": 0.0, "confidence": 0.0, "recommended_action": "ALLOW"}

    PRIVACY: The text is forwarded to the local AI engine only.
    Only the SHA-256 hash is stored in the database, never the raw text.
    """
    device = request.auth
    text = request.data.get('text', '').strip()
    context = request.data.get('context', 'webpage')

    if not text:
        return Response(error_response('text field is required.'), status=status.HTTP_400_BAD_REQUEST)

    # Truncate to reasonable limit before sending to AI engine
    if len(text) > 10000:
        text = text[:10000]
        logger.debug('Text truncated to 10000 chars for AI analysis.')

    content_hash = _hash_content(text)

    # Check if we've recently analyzed identical content (5-minute cache)
    from django.utils import timezone
    from datetime import timedelta
    cached = AIAnalysis.objects.filter(
        device=device,
        content_hash=content_hash,
        created_at__gte=timezone.now() - timedelta(minutes=5)
    ).first()

    if cached:
        logger.debug('AI analysis cache hit for hash %s', content_hash[:16])
        return Response(success_response({
            'category': cached.category,
            'risk_score': cached.risk_score,
            'confidence': cached.confidence,
            'recommended_action': cached.recommended_action,
            'inference_mode': cached.inference_mode,
            'cached': True,
        }))

    # Call the local AI engine
    try:
        result = _call_ai_engine('/analyze/text', {
            'text': text,
            'context': context,
        })
    except RuntimeError as e:
        logger.error('AI engine unavailable: %s', str(e))
        # Fail gracefully — return safe default, log the failure
        _log_ai_failure(device, 'TEXT', content_hash, str(e))
        return Response(success_response({
            'category': 'unknown',
            'risk_score': 0.0,
            'confidence': 0.0,
            'recommended_action': 'ALLOW',
            'inference_mode': 'FALLBACK',
            'error': 'AI engine unavailable. Defaulting to ALLOW.',
        }))

    # Store analysis result (hash only, no raw text)
    analysis = AIAnalysis.objects.create(
        device=device,
        input_type=AIAnalysis.INPUT_TEXT,
        content_hash=content_hash,
        category=result.get('category', 'unknown'),
        risk_score=result.get('risk_score', 0.0),
        confidence=result.get('confidence', 0.0),
        recommended_action=result.get('recommended_action', 'ALLOW'),
        inference_mode=result.get('inference_mode', 'MOCK'),
    )

    # Create threat event if risk is significant
    if result.get('risk_score', 0.0) >= 0.6:
        _create_threat_from_analysis(device, result, context)

    return Response(success_response({
        'category': analysis.category,
        'risk_score': analysis.risk_score,
        'confidence': analysis.confidence,
        'recommended_action': analysis.recommended_action,
        'inference_mode': analysis.inference_mode,
        'cached': False,
    }))


@api_view(['POST'])
@permission_classes([IsDeviceAuthenticated])
def check_url(request):
    """
    POST /api/browser/check-url/
    Classify a URL for safety. Used by the browser extension on every navigation.

    Body: {"url": "https://...", "child_id": 1}
    Returns: {"category": "...", "risk_score": 0.0, "recommended_action": "ALLOW|WARN|BLOCK"}
    """
    device = request.auth
    url = request.data.get('url', '').strip()

    if not url:
        return Response(error_response('url field is required.'), status=status.HTTP_400_BAD_REQUEST)

    # Extract domain for policy check
    try:
        import tldextract
        extracted = tldextract.extract(url)
        domain = f'{extracted.domain}.{extracted.suffix}' if extracted.suffix else extracted.domain
    except Exception:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()

    # Check parent website policy first (policy takes precedence over AI)
    policy_action = _check_website_policy(device, domain)
    if policy_action:
        return Response(success_response({
            'url': url,
            'domain': domain,
            'category': 'policy',
            'risk_score': 1.0 if policy_action == 'BLOCK' else 0.3,
            'confidence': 1.0,
            'recommended_action': policy_action,
            'source': 'parent_policy',
            'inference_mode': 'POLICY',
        }))

    # Call the local AI engine for URL classification
    content_hash = _hash_content(url)
    try:
        result = _call_ai_engine('/analyze/url', {'url': url})
    except RuntimeError as e:
        logger.error('AI engine unavailable for URL check: %s', str(e))
        return Response(success_response({
            'url': url,
            'domain': domain,
            'category': 'unknown',
            'risk_score': 0.0,
            'confidence': 0.0,
            'recommended_action': 'ALLOW',
            'source': 'fallback',
            'inference_mode': 'FALLBACK',
        }))

    result['url'] = url
    result['domain'] = domain
    result['source'] = 'ai_engine'
    return Response(success_response(result))


@api_view(['POST'])
@permission_classes([IsDeviceAuthenticated])
def analyze_image(request):
    """
    POST /api/ai/analyze-image/
    Classify an image for inappropriate (adult/explicit) content.
    Called by the browser extension content script for each significant image on a page.

    Body: {"image_url": "https://..."}
    Returns: {"category": "...", "risk_score": 0.0, "recommended_action": "ALLOW|WARN|BLUR|BLOCK"}

    PRIVACY: The image URL is forwarded to the local AI engine only.
    The URL is hashed (SHA-256) for deduplication; the raw URL is never stored in DB.
    Image pixel data is processed locally — never sent externally.
    """
    device = request.auth
    image_url = request.data.get('image_url', '').strip()
    image_b64 = request.data.get('image_b64', '').strip()

    if not image_url and not image_b64:
        return Response(error_response('image_url or image_b64 is required.'), status=status.HTTP_400_BAD_REQUEST)

    # Truncate URL to reasonable length
    if image_url and len(image_url) > 2048:
        image_url = image_url[:2048]

    content_hash = _hash_content(image_url or image_b64)

    # Cache check — avoid re-analysing the same image multiple times in 10 minutes
    from datetime import timedelta
    cached = AIAnalysis.objects.filter(
        device=device,
        input_type=AIAnalysis.INPUT_IMAGE,
        content_hash=content_hash,
        created_at__gte=timezone.now() - timedelta(minutes=10)
    ).first()

    if cached:
        logger.debug('Image analysis cache hit for hash %s', content_hash[:16])
        return Response(success_response({
            'category': cached.category,
            'risk_score': cached.risk_score,
            'confidence': cached.confidence,
            'recommended_action': cached.recommended_action,
            'inference_mode': cached.inference_mode,
            'cached': True,
        }))

    # Build payload for AI engine
    payload = {}
    if image_url:
        payload['image_url'] = image_url
    if image_b64:
        payload['image_b64'] = image_b64

    # Call the local AI engine
    try:
        result = _call_ai_engine('/analyze/image', payload)
    except RuntimeError as e:
        logger.error('AI engine unavailable for image analysis: %s', str(e))
        _log_ai_failure(device, 'IMAGE', content_hash, str(e))
        return Response(success_response({
            'category': 'unknown',
            'risk_score': 0.0,
            'confidence': 0.0,
            'recommended_action': 'ALLOW',
            'inference_mode': 'FALLBACK',
            'error': 'AI engine unavailable. Defaulting to ALLOW.',
        }))

    # Store analysis result (hash only — raw URL/image data never stored)
    analysis = AIAnalysis.objects.create(
        device=device,
        input_type=AIAnalysis.INPUT_IMAGE,
        content_hash=content_hash,
        category=result.get('category', 'unknown'),
        risk_score=result.get('risk_score', 0.0),
        confidence=result.get('confidence', 0.0),
        recommended_action=result.get('recommended_action', 'ALLOW'),
        inference_mode=result.get('inference_mode', 'MOCK_VISION'),
    )

    # Create threat event for high-risk images
    if result.get('risk_score', 0.0) >= 0.55:
        _create_threat_from_analysis(
            device,
            result,
            context=f'image:{image_url[:100] if image_url else "b64"}',
        )

    return Response(success_response({
        'category': analysis.category,
        'risk_score': analysis.risk_score,
        'confidence': analysis.confidence,
        'recommended_action': analysis.recommended_action,
        'inference_mode': analysis.inference_mode,
        'cached': False,
    }))



def _check_website_policy(device, domain):
    """Check if there's an explicit parent policy for this domain."""
    try:
        from policies.models import WebsitePolicy
        policy = WebsitePolicy.objects.filter(
            parent=device.child.parent,
            domain__iexact=domain,
            is_active=True,
        ).filter(
            models_child=device.child.id
        ).first() or WebsitePolicy.objects.filter(
            parent=device.child.parent,
            domain__iexact=domain,
            is_active=True,
            child__isnull=True,
        ).first()
        if policy:
            return policy.rule_type
    except Exception as e:
        logger.error('Policy check error: %s', str(e))
    return None


def _create_threat_from_analysis(device, result, context):
    """Create ActivityLog + ThreatEvent for a high-risk AI analysis."""
    try:
        severity_map = {
            (0.6, 0.75): ActivityLog.SEV_MEDIUM,
            (0.75, 0.9): ActivityLog.SEV_HIGH,
            (0.9, 1.1): ActivityLog.SEV_CRITICAL,
        }
        risk = result.get('risk_score', 0.0)
        severity = ActivityLog.SEV_MEDIUM
        for (low, high), sev in severity_map.items():
            if low <= risk < high:
                severity = sev

        category = result.get('category', 'unknown')
        event_type_map = {
            'cyberbullying': ActivityLog.CYBERBULLYING_DETECTED,
            'grooming': ActivityLog.GROOMING_RISK_DETECTED,
            'phishing': ActivityLog.PHISHING_DETECTED,
            'adult': ActivityLog.CONTENT_FLAGGED,
            'violence': ActivityLog.CONTENT_FLAGGED,
        }
        event_type = event_type_map.get(category.lower(), ActivityLog.CONTENT_FLAGGED)

        log = ActivityLog.objects.create(
            device=device,
            event_type=event_type,
            timestamp=timezone.now(),
            severity=severity,
            category=category,
            action_taken=result.get('recommended_action', 'WARN'),
            metadata={'context': context, 'inference_mode': result.get('inference_mode', 'MOCK')},
        )

        ThreatEvent.objects.create(
            activity_log=log,
            threat_type=category,
            risk_score=result.get('risk_score', 0.0),
            confidence=result.get('confidence', 0.0),
            ai_category=category,
            indicators=result.get('indicators', []),
            inference_mode=result.get('inference_mode', 'MOCK'),
        )

        create_alert_if_needed(log)
    except Exception as e:
        logger.error('Failed to create threat event: %s', str(e))


def _log_ai_failure(device, input_type, content_hash, error_msg):
    """Log an AI engine failure as an activity log entry."""
    try:
        ActivityLog.objects.create(
            device=device,
            event_type=ActivityLog.AI_ANALYSIS_FAILED,
            timestamp=timezone.now(),
            severity=ActivityLog.SEV_LOW,
            category='system',
            action_taken=ActivityLog.ACTION_ALLOW,
            metadata={'error': error_msg, 'input_type': input_type},
        )
    except Exception:
        pass
