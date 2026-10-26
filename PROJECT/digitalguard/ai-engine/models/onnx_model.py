"""
ONNX Text Model — Real Inference

Loads a DistilBERT-based toxicity classification model from an ONNX file.
This replaces the MockTextModel when a real model is available.

Expected ONNX model inputs:
- input_ids: (batch, seq_len) int64
- attention_mask: (batch, seq_len) int64

Expected ONNX model outputs:
- logits: (batch, num_classes) float32

Label mapping must match the model's training labels.
See docs/ai-engine.md for model download/training instructions.
"""

import logging
import numpy as np
from analyzer import AnalysisResult

logger = logging.getLogger('digitalguard.ai_engine.onnx_model')

# Label mapping — must match the model's training labels
# Update this if you use a different model
LABEL_MAP = {
    0: 'safe',
    1: 'cyberbullying',
    2: 'adult',
    3: 'phishing',
    4: 'grooming',
    5: 'violence',
    6: 'harmful_content',
}

ACTION_MAP = {
    'safe': 'ALLOW',
    'cyberbullying': 'BLOCK',
    'adult': 'BLUR',
    'phishing': 'BLOCK',
    'grooming': 'BLOCK',
    'violence': 'WARN',
    'harmful_content': 'BLUR',
}

MAX_SEQ_LEN = 512


class ONNXTextModel:
    """
    ONNX Runtime text classifier.
    Uses a tokenizer to convert text to input IDs, then runs inference.
    """
    INFERENCE_MODE = 'REAL'

    def __init__(self, model_path: str):
        # Import here to avoid hard dependency when model isn't present
        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer
        except ImportError:
            raise ImportError(
                'onnxruntime and transformers are required for ONNX inference. '
                'Install with: pip install onnxruntime transformers'
            )

        logger.info('Loading ONNX model from: %s', model_path)
        self._session = ort.InferenceSession(
            model_path,
            providers=['CPUExecutionProvider']  # CPU only — keeps inference local
        )
        # Tokenizer: distilbert-base-uncased (or match your model's tokenizer)
        # This only downloads the tokenizer config (< 1MB), not model weights
        self._tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')
        logger.info('ONNX model loaded. Input names: %s', [i.name for i in self._session.get_inputs()])

    def analyze_text(self, text: str, context: str = 'webpage') -> AnalysisResult:
        """Run ONNX inference on the given text."""
        # Tokenize
        encoding = self._tokenizer(
            text,
            max_length=MAX_SEQ_LEN,
            truncation=True,
            padding='max_length',
            return_tensors='np',
        )

        input_ids = encoding['input_ids'].astype(np.int64)
        attention_mask = encoding['attention_mask'].astype(np.int64)

        # Run inference
        outputs = self._session.run(
            None,
            {
                'input_ids': input_ids,
                'attention_mask': attention_mask,
            }
        )

        logits = outputs[0][0]  # (num_classes,)

        # Softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()

        best_class_idx = int(np.argmax(probs))
        best_score = float(probs[best_class_idx])
        category = LABEL_MAP.get(best_class_idx, 'unknown')

        # Use class probabilities as sub_scores
        sub_scores = {LABEL_MAP.get(i, str(i)): float(p) for i, p in enumerate(probs)}

        # Risk score = probability of the non-safe class (1 - P(safe))
        risk_score = 1.0 - float(probs[0]) if len(probs) > 0 else best_score

        action = ACTION_MAP.get(category, 'WARN')

        return AnalysisResult(
            category=category,
            risk_score=min(risk_score, 1.0),
            confidence=best_score,
            recommended_action=action,
            inference_mode=self.INFERENCE_MODE,
            indicators=[f'ONNX class={category}, confidence={best_score:.2f}'],
            sub_scores=sub_scores,
        )
