# Local AI Engine Guide

The DigitalGuard AI Engine is a local, privacy-preserving microservice running on `127.0.0.1:8765`. It processes raw text and URL tokens on-device without exposing children's private conversations or browsing histories to external LLM providers.

## Architecture
- **Web Framework**: FastAPI & Uvicorn, restricted strictly to loopback interface.
- **Inference Mode**:
  - **REAL**: When an ONNX model is detected in `models/text/*.onnx`, high-speed local inference executes via `onnxruntime`.
  - **MOCK**: If no model file exists, fallback heuristics execute keyword pattern-matching and clearly label responses with `"inference_mode": "MOCK"`.

## Endpoints
### 1. `POST /analyze/text`
- Payload: `{"text": "string", "context": "webpage|chat|comment"}`
- Response:
  ```json
  {
    "category": "cyberbullying",
    "risk_score": 0.88,
    "confidence": 0.85,
    "recommended_action": "BLUR",
    "inference_mode": "MOCK",
    "indicators": ["targeted_toxicity"]
  }
  ```

### 2. `POST /analyze/url`
- Payload: `{"url": "http://..."}`
- Response:
  ```json
  {
    "category": "phishing",
    "risk_score": 0.94,
    "confidence": 0.90,
    "recommended_action": "BLOCK",
    "inference_mode": "MOCK",
    "indicators": ["high_entropy_domain", "deceptive_brand_typo"]
  }
  ```

### 3. `GET /health`
- Returns engine status and active inference mode.

## Starting the AI Service
```cmd
cd ai-engine
python -m uvicorn main:app --host 127.0.0.1 --port 8765
```
