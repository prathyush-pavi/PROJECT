"""
DigitalGuard AI Analysis Pipeline

Orchestrates multiple analyzers to produce a unified risk assessment.

Model Loading Priority:
1. Try to load real ONNX model from ../models/text/*.onnx
2. Fall back to mock model if ONNX model not found
3. ALWAYS clearly label the inference_mode in responses

The mock model uses keyword heuristics — it is NOT a trained ML model.
It exists solely to demonstrate the interface and data flow.
Never present mock results as actual AI performance.
"""

import logging
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger('digitalguard.ai_engine.analyzer')

MODELS_DIR = Path(__file__).parent.parent / 'models' / 'text'


@dataclass
class AnalysisResult:
    """Unified result from the analysis pipeline."""
    category: str
    risk_score: float
    confidence: float
    recommended_action: str
    inference_mode: str
    indicators: list = field(default_factory=list)
    sub_scores: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            'category': self.category,
            'risk_score': round(self.risk_score, 4),
            'confidence': round(self.confidence, 4),
            'recommended_action': self.recommended_action,
            'inference_mode': self.inference_mode,
            'indicators': self.indicators,
            'sub_scores': self.sub_scores,
        }


class AnalysisPipeline:
    """
    Central pipeline that runs all analyzers and aggregates results.
    """

    def __init__(self):
        self.model_loaded = False
        self.inference_mode = 'MOCK'
        self._model = None
        self._load_model()

        # Initialize sub-analyzers
        from models.url_analyzer import URLAnalyzer
        from models.mock_model import MockTextModel
        from models.image_analyzer import ImageAnalyzer
        self._url_analyzer = URLAnalyzer()
        self._text_model = self._model or MockTextModel()
        self._image_analyzer = ImageAnalyzer()

    def _load_model(self):
        """Attempt to load the ONNX model. Fall back to mock if not found."""
        onnx_files = list(MODELS_DIR.glob('*.onnx')) if MODELS_DIR.exists() else []
        if onnx_files:
            try:
                from models.onnx_model import ONNXTextModel
                self._model = ONNXTextModel(str(onnx_files[0]))
                self.model_loaded = True
                self.inference_mode = 'REAL'
                logger.info('ONNX model loaded: %s', onnx_files[0].name)
            except Exception as e:
                logger.error('Failed to load ONNX model: %s — falling back to MOCK', str(e))
                self._model = None
                self.model_loaded = False
                self.inference_mode = 'MOCK'
        else:
            logger.warning(
                'No ONNX model found in %s. Using MOCK inference. '
                'See docs/ai-engine.md for model setup instructions.', MODELS_DIR
            )
            self.inference_mode = 'MOCK'

    def analyze_text(self, text: str, context: str = 'webpage') -> dict:
        """
        Run full text analysis pipeline:
        - Cyberbullying detection
        - Grooming risk detection
        - Harmful content detection
        Returns the highest-risk result.
        """
        result = self._text_model.analyze_text(text, context=context)
        return result.to_dict()

    def analyze_url(self, url: str) -> dict:
        """
        Classify a URL using heuristic URL analysis.
        (URL classification is always heuristic-based, not deep learning.)
        """
        result = self._url_analyzer.analyze(url)
        return result.to_dict()

    def analyze_image(self, image_url: str = None, image_b64: str = None) -> dict:
        """
        Classify an image for inappropriate content.

        Args:
            image_url: HTTP/HTTPS URL of the image to analyse.
            image_b64: Base64-encoded raw image data (alternative to URL).

        Processing tiers:
          1. URL keyword patterns (instant)
          2. Pillow pixel skin-tone heuristic (local, no model needed)
          3. ONNX vision model if available in models/vision/*.onnx

        Returns dict matching AnalysisResult.to_dict() format.
        """
        result = self._image_analyzer.analyze(
            image_url=image_url,
            image_b64=image_b64,
        )
        return result.to_dict()
