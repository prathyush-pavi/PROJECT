"""
Unit tests for DigitalGuard Local AI Engine
"""

import sys
from pathlib import Path

# Add ai-engine to sys.path
ai_engine_dir = Path(__file__).resolve().parent.parent.parent / "ai-engine"
sys.path.insert(0, str(ai_engine_dir))

import pytest
from analyzer import AnalysisPipeline


def test_ai_pipeline_initialization():
    pipeline = AnalysisPipeline()
    assert pipeline.inference_mode in ["REAL", "MOCK"]
    assert pipeline._text_model is not None
    assert pipeline._url_analyzer is not None


def test_text_analysis_safe_content():
    pipeline = AnalysisPipeline()
    res = pipeline.analyze_text("Hello, let's work on our science project together.")
    assert "category" in res
    assert "risk_score" in res
    assert "recommended_action" in res
    assert res["recommended_action"] in ["ALLOW", "WARN", "BLUR", "BLOCK"]
    assert res["risk_score"] < 0.5


def test_text_analysis_harmful_keyword_mock():
    pipeline = AnalysisPipeline()
    # Test keyword triggering in mock mode
    res = pipeline.analyze_text("You are so stupid and ugly, go die and kill yourself")
    assert res["risk_score"] >= 0.6
    assert res["recommended_action"] in ["WARN", "BLUR", "BLOCK"]
    assert res["category"] in ["cyberbullying", "harassment", "toxic"]


def test_url_analysis_phishing_heuristic():
    pipeline = AnalysisPipeline()
    res = pipeline.analyze_url("http://paypal-security-update-verify-login.xyz/account")
    assert res["risk_score"] > 0.5
    assert res["category"] == "phishing"
    assert res["recommended_action"] in ["WARN", "BLOCK"]


def test_url_analysis_safe():
    pipeline = AnalysisPipeline()
    res = pipeline.analyze_url("https://en.wikipedia.org/wiki/Main_Page")
    assert res["risk_score"] < 0.3
    assert res["recommended_action"] == "ALLOW"
