# Testing Suite & Verification Guide

DigitalGuard includes automated tests covering backend API logic, AI pipelines, and Windows agent policy enforcement.

## Running Tests

### 1. Backend Unit & API Tests
```cmd
pytest tests/backend/ -v
```
Validates:
- User & device registration
- Device token authentication & rotation
- Activity log ingestion
- Threat detection linkage

### 2. Local AI Engine Tests
```cmd
pytest tests/ai_engine/ -v
```
Validates:
- Pipeline startup & fallback modes
- Safe text classification
- Harmful content keyword heuristics
- Phishing URL detection

### 3. Windows Desktop Agent Tests
```cmd
pytest tests/desktop_agent/ -v
```
Validates:
- Active window time accumulation
- Idle period subtraction
- Windows application policy enforcement (BLOCK vs LIMITED)
- Screen-time quota alerts
