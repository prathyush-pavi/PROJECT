"""
Mock Text Model — Development Heuristic Classifier

⚠️  WARNING: THIS IS NOT A TRAINED ML MODEL ⚠️
This classifier uses simple keyword matching for development and testing ONLY.
It is designed to:
1. Demonstrate the model interface
2. Exercise the full data pipeline
3. Be trivially replaceable with a real ONNX model

All results are labeled inference_mode='MOCK'.
Never present mock results as actual AI performance or accuracy.

To replace with a real model:
1. Train or download a DistilBERT toxicity ONNX model
2. Place the .onnx file in models/text/
3. The pipeline will automatically detect and load it
4. See docs/ai-engine.md for details
"""

import re
import logging
from analyzer import AnalysisResult

logger = logging.getLogger('digitalguard.ai_engine.mock_model')


# ──────────────────────────────────────────────────────────────────────────────
# Keyword sets — deliberately simple for demo purposes
# A real model would not use these patterns
# ──────────────────────────────────────────────────────────────────────────────

CYBERBULLYING_PATTERNS = [
    r'\bkill\s+your?self\b', r'\bgo\s+die\b', r'\byou\s+are\s+(ugly|fat|stupid|worthless|pathetic)\b',
    r'\bno\s*one\s+likes\s+you\b', r'\bloser\b', r'\bidiot\b', r'\bmoron\b',
    r'\byou\s+suck\b', r'\bstfu\b', r'\bshut\s+up\b.*\btard\b',
]

GROOMING_PATTERNS = [
    r'\bdon\'?t\s+tell\s+(your\s+)?(parents?|mum|mom|dad)\b',
    r'\bkeep\s+(it|this)\s+(secret|between\s+us)\b',
    r'\bsend\s+me\s+(a\s+)?(photo|pic|picture)\b',
    r'\bhow\s+old\s+are\s+you\b',
    r'\bwhere\s+do\s+you\s+live\b',
    r'\bare\s+you\s+(home\s+)?alone\b',
    r'\bmeet\s+up\b.*\bsecret\b',
    r'\byou\s+are\s+(so\s+)?(mature|special)\s+for\s+your\s+age\b',
    r'\blet\'?s\s+move\s+to\s+(whatsapp|telegram|snapchat|discord)\b',
]

PHISHING_PATTERNS = [
    r'\bverify\s+your\s+account\b', r'\bclick\s+here\s+immediately\b',
    r'\byour\s+account\s+(has\s+been\s+)?(suspended|locked|compromised)\b',
    r'\benter\s+your\s+password\b', r'\bconfirm\s+your\s+(credit\s+card|bank|ssn)\b',
    r'\bact\s+now\b.*\bexpire\b', r'\bwon\s+a\s+(prize|lottery|gift\s+card)\b',
]

HARMFUL_CONTENT_PATTERNS = [
    r'\blow\s*cal(orie)?\s*diet.*\bfast(ing)?\b', r'\bhow\s+to\s+(make|build)\s+a\s+(bomb|weapon)\b',
    r'\bself.harm\b', r'\bcutting\s+yourself\b',
]

ADULT_CONTENT_PATTERNS = [
    r'\bporn(ography)?\b', r'\bxxx\b', r'\bnude(s)?\b', r'\bsexual\s+content\b',
    r'\berotic\b', r'\bhentai\b',
]


class MockTextModel:
    """
    Development-only keyword-based text classifier.
    Implements the same interface as ONNXTextModel.
    """
    INFERENCE_MODE = 'MOCK'

    def __init__(self):
        logger.warning(
            '[MOCK MODEL] Using keyword heuristics for text classification. '
            'NOT suitable for production. See docs/ai-engine.md.'
        )
        self._patterns = {
            'cyberbullying': (CYBERBULLYING_PATTERNS, 0.85),
            'grooming': (GROOMING_PATTERNS, 0.90),
            'phishing': (PHISHING_PATTERNS, 0.80),
            'harmful_content': (HARMFUL_CONTENT_PATTERNS, 0.75),
            'adult': (ADULT_CONTENT_PATTERNS, 0.90),
        }

    def analyze_text(self, text: str, context: str = 'webpage') -> AnalysisResult:
        """
        Classify text using keyword pattern matching.
        Returns AnalysisResult with MOCK inference_mode.
        """
        text_lower = text.lower()
        best_category = 'safe'
        best_score = 0.0
        best_confidence = 0.9
        matched_indicators = []

        for category, (patterns, base_confidence) in self._patterns.items():
            hits = []
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    hits.append(pattern)

            if hits:
                # Score based on number of pattern matches (capped at 1.0)
                score = min(0.5 + (len(hits) * 0.15), 0.95)
                if score > best_score:
                    best_score = score
                    best_category = category
                    best_confidence = base_confidence
                    matched_indicators = [f'Pattern match: {p}' for p in hits[:3]]

        action = self._score_to_action(best_score, best_category)

        return AnalysisResult(
            category=best_category,
            risk_score=best_score,
            confidence=best_confidence if best_score > 0 else 0.5,
            recommended_action=action,
            inference_mode=self.INFERENCE_MODE,
            indicators=matched_indicators,
            sub_scores={cat: 0.0 for cat in self._patterns},
        )

    def _score_to_action(self, score: float, category: str) -> str:
        """Convert risk score to enforcement action."""
        if score == 0.0:
            return 'ALLOW'
        if score < 0.4:
            return 'ALLOW'
        if score < 0.6:
            return 'WARN'
        if score < 0.8:
            return 'BLUR' if category in ('adult', 'harmful_content') else 'WARN'
        return 'BLOCK'
