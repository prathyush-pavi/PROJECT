"""
Image Analyzer — On-Device Image Content Classification

Classifies images for inappropriate content (adult/explicit material) using
a tiered approach:

  Tier 1 — URL pattern analysis (instant, no image download required)
            Checks image URL/path for known adult-content keywords.

  Tier 2 — Pixel heuristic (Pillow-based, runs locally)
            Downloads the image data and computes the ratio of skin-tone
            pixels using HSV colour ranges. High ratio = likely adult content.
            This is a statistical heuristic, NOT a trained model.

  Tier 3 — ONNX Vision model (if available in models/vision/*.onnx)
            Loads a MobileNet-based NSFW classifier and runs inference.

All processing is local. Images are never forwarded to external APIs.

inference_mode values:
  URL_HEURISTIC  — decision based on URL pattern only
  PIXEL_HEURISTIC — decision based on skin-tone pixel analysis
  MOCK_VISION    — no model found, pixel heuristic used as fallback
  REAL_VISION    — real ONNX vision model loaded and used
"""

import re
import io
import logging
from pathlib import Path
from urllib.parse import urlparse
from analyzer import AnalysisResult

logger = logging.getLogger('digitalguard.ai_engine.image_analyzer')

# ── URL keyword patterns for fast screening ────────────────────────────────────
ADULT_URL_PATTERNS = [
    r'/(?:nude|nudity|naked|nsfw|xxx|porn|sex|adult|erotic|hentai|lewd)',
    r'(?:porn|nude|xxx|nsfw|adult|hentai|lewd)\.',
    r'(?:onlyfans|brazzers|pornhub|xvideos|xnxx|redtube|youporn)',
]

ADULT_URL_COMPILED = [re.compile(p, re.IGNORECASE) for p in ADULT_URL_PATTERNS]

# ── Skin-tone HSV ranges (Hue, Saturation, Value) ─────────────────────────────
# These ranges approximate human skin tones in HSV colour space.
# Used with Pillow — no model weights required.
SKIN_TONE_RANGES = [
    # Lighter skin tones
    {'h': (0, 25), 's': (0.15, 0.85), 'v': (0.35, 1.0)},
    # Medium skin tones
    {'h': (350, 360), 's': (0.10, 0.70), 'v': (0.20, 0.90)},
    # Darker skin tones
    {'h': (10, 30), 's': (0.10, 0.80), 'v': (0.10, 0.75)},
]

# If the skin-pixel ratio exceeds this threshold, flag as suspicious adult content
SKIN_RATIO_WARN_THRESHOLD = 0.35    # 35%+ skin pixels → warn
SKIN_RATIO_BLOCK_THRESHOLD = 0.60   # 60%+ skin pixels → block

# Max image size to download for analysis (bytes) — prevents large downloads
MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2MB

# ── ONNX Vision model directory ───────────────────────────────────────────────
VISION_MODELS_DIR = Path(__file__).parent.parent.parent / 'models' / 'vision'


def _check_url_patterns(image_url: str) -> tuple[bool, list[str]]:
    """Check URL against adult content patterns. Returns (is_adult, indicators)."""
    indicators = []
    try:
        parsed = urlparse(image_url)
        url_path = (parsed.netloc + parsed.path).lower()
    except Exception:
        url_path = image_url.lower()

    for pattern in ADULT_URL_COMPILED:
        if pattern.search(url_path):
            indicators.append(f'Adult URL pattern matched: {pattern.pattern}')

    return len(indicators) > 0, indicators


def _is_skin_tone(h: float, s: float, v: float) -> bool:
    """Check if HSV values fall within any defined skin-tone range."""
    hue_deg = h * 360.0
    for skin_range in SKIN_TONE_RANGES:
        h_min, h_max = skin_range['h']
        s_min, s_max = skin_range['s']
        v_min, v_max = skin_range['v']
        if h_min <= hue_deg <= h_max and s_min <= s <= s_max and v_min <= v <= v_max:
            return True
    return False


def _analyse_image_pixels(image_data: bytes) -> tuple[float, str, list[str]]:
    """
    Compute skin-tone pixel ratio using Pillow.
    Returns (risk_score, category, indicators).
    """
    try:
        from PIL import Image
        import colorsys
    except ImportError:
        logger.warning('[ImageAnalyzer] Pillow not available for pixel analysis.')
        return 0.0, 'unknown', ['Pillow not installed — pixel analysis skipped']

    try:
        img = Image.open(io.BytesIO(image_data)).convert('RGB')

        # Downsample to a maximum of 200x200 for fast analysis
        img.thumbnail((200, 200), Image.LANCZOS)

        pixels = list(img.getdata())
        total = len(pixels)
        if total == 0:
            return 0.0, 'safe', []

        skin_count = 0
        for (r, g, b) in pixels:
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if _is_skin_tone(h, s, v):
                skin_count += 1

        ratio = skin_count / total
        logger.debug('[ImageAnalyzer] Skin-tone ratio: %.2f (%d/%d pixels)', ratio, skin_count, total)

        indicators = [f'Skin-tone pixel ratio: {ratio:.1%}']

        if ratio >= SKIN_RATIO_BLOCK_THRESHOLD:
            return min(0.4 + ratio * 0.6, 0.95), 'adult', indicators
        elif ratio >= SKIN_RATIO_WARN_THRESHOLD:
            return 0.35 + ratio * 0.5, 'suspicious', indicators
        else:
            return ratio * 0.3, 'safe', indicators

    except Exception as e:
        logger.warning('[ImageAnalyzer] Pixel analysis failed: %s', str(e))
        return 0.0, 'unknown', [f'Pixel analysis error: {str(e)}']


class ImageAnalyzer:
    """
    On-device image content classifier.

    Implements the same AnalysisResult interface as text/URL analyzers.
    Used by the AI engine to classify images sent by the browser extension.
    """

    def __init__(self):
        self._onnx_model = None
        self._inference_mode = 'MOCK_VISION'
        self._try_load_onnx()

    def _try_load_onnx(self):
        """Attempt to load an ONNX vision model from models/vision/."""
        if not VISION_MODELS_DIR.exists():
            logger.info('[ImageAnalyzer] No vision models directory found — using pixel heuristic.')
            return

        onnx_files = list(VISION_MODELS_DIR.glob('*.onnx'))
        if not onnx_files:
            logger.info('[ImageAnalyzer] No ONNX vision model found — using pixel heuristic.')
            return

        try:
            import onnxruntime as ort
            self._onnx_session = ort.InferenceSession(
                str(onnx_files[0]),
                providers=['CPUExecutionProvider']
            )
            self._inference_mode = 'REAL_VISION'
            logger.info('[ImageAnalyzer] ONNX vision model loaded: %s', onnx_files[0].name)
        except Exception as e:
            logger.error('[ImageAnalyzer] Failed to load ONNX vision model: %s', str(e))

    def analyze(self, image_url: str = None, image_b64: str = None) -> AnalysisResult:
        """
        Classify an image for inappropriate content.

        Args:
            image_url: HTTP/HTTPS URL of the image. URL pattern check is
                       performed instantly. Pixel analysis requires fetching the image.
            image_b64: Base64-encoded image data (alternative to URL).

        Returns:
            AnalysisResult with category, risk_score, and recommended_action.
        """
        indicators = []
        risk_score = 0.0
        category = 'safe'
        inference_mode = self._inference_mode

        # ── Tier 1: URL pattern check ─────────────────────────────────────────
        if image_url:
            is_adult_url, url_indicators = _check_url_patterns(image_url)
            if is_adult_url:
                return AnalysisResult(
                    category='adult',
                    risk_score=0.90,
                    confidence=0.85,
                    recommended_action='BLUR',
                    inference_mode='URL_HEURISTIC',
                    indicators=url_indicators,
                )

        # ── Tier 2: Pixel heuristic / ONNX model ─────────────────────────────
        image_data = None

        if image_b64:
            try:
                import base64
                image_data = base64.b64decode(image_b64)
            except Exception as e:
                logger.warning('[ImageAnalyzer] Failed to decode base64 image: %s', str(e))

        elif image_url:
            try:
                import urllib.request
                req = urllib.request.Request(
                    image_url,
                    headers={'User-Agent': 'DigitalGuard/1.0 (safety-scanner)'},
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    content_type = response.headers.get('Content-Type', '')
                    if not content_type.startswith('image/'):
                        logger.debug('[ImageAnalyzer] Non-image Content-Type: %s', content_type)
                        return self._safe_result(inference_mode)
                    image_data = response.read(MAX_IMAGE_BYTES)
            except Exception as e:
                logger.debug('[ImageAnalyzer] Could not fetch image %s: %s', image_url, str(e))
                # Cannot fetch — skip pixel analysis, return safe default
                return self._safe_result(inference_mode)

        if image_data is None:
            return self._safe_result(inference_mode)

        # ── Use ONNX vision model if available ────────────────────────────────
        if self._inference_mode == 'REAL_VISION' and self._onnx_session:
            return self._run_onnx_inference(image_data)

        # ── Fallback: Pillow pixel heuristic ─────────────────────────────────
        risk_score, category, indicators = _analyse_image_pixels(image_data)
        action = self._score_to_action(risk_score, category)

        return AnalysisResult(
            category=category,
            risk_score=round(risk_score, 4),
            confidence=0.65,  # heuristic confidence is moderate
            recommended_action=action,
            inference_mode='PIXEL_HEURISTIC',
            indicators=indicators,
        )

    def _run_onnx_inference(self, image_data: bytes) -> AnalysisResult:
        """
        Run ONNX vision model inference.
        Expected model: MobileNet-based NSFW binary classifier.
        Input: (1, 3, 224, 224) float32 normalized image.
        Output: (1, 2) logits [safe_score, nsfw_score].
        """
        try:
            from PIL import Image
            import numpy as np

            img = Image.open(io.BytesIO(image_data)).convert('RGB').resize((224, 224))
            arr = np.array(img, dtype=np.float32) / 255.0
            # Normalize (ImageNet mean/std)
            mean = np.array([0.485, 0.456, 0.406])
            std = np.array([0.229, 0.224, 0.225])
            arr = (arr - mean) / std
            arr = arr.transpose(2, 0, 1)[np.newaxis, :]  # (1, 3, 224, 224)

            outputs = self._onnx_session.run(None, {'input': arr.astype(np.float32)})
            logits = outputs[0][0]
            exp = np.exp(logits - np.max(logits))
            probs = exp / exp.sum()

            nsfw_score = float(probs[1]) if len(probs) > 1 else 0.0
            category = 'adult' if nsfw_score >= 0.5 else 'safe'
            action = self._score_to_action(nsfw_score, category)

            return AnalysisResult(
                category=category,
                risk_score=round(nsfw_score, 4),
                confidence=round(float(np.max(probs)), 4),
                recommended_action=action,
                inference_mode='REAL_VISION',
                indicators=[f'ONNX vision: nsfw_score={nsfw_score:.2f}'],
            )
        except Exception as e:
            logger.error('[ImageAnalyzer] ONNX inference failed: %s — falling back to pixel heuristic', str(e))
            risk_score, category, indicators = _analyse_image_pixels(image_data)
            action = self._score_to_action(risk_score, category)
            return AnalysisResult(
                category=category,
                risk_score=round(risk_score, 4),
                confidence=0.55,
                recommended_action=action,
                inference_mode='PIXEL_HEURISTIC',
                indicators=indicators + [f'ONNX failed: {str(e)}'],
            )

    @staticmethod
    def _score_to_action(score: float, category: str) -> str:
        if score < 0.30:
            return 'ALLOW'
        if score < 0.55:
            return 'WARN'
        if score < 0.80:
            return 'BLUR'
        return 'BLOCK'

    @staticmethod
    def _safe_result(inference_mode: str) -> AnalysisResult:
        return AnalysisResult(
            category='safe',
            risk_score=0.0,
            confidence=0.5,
            recommended_action='ALLOW',
            inference_mode=inference_mode,
            indicators=['Image could not be fetched or analysed — defaulting to safe'],
        )
