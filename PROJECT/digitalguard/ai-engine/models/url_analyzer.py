"""
URL Analyzer — Heuristic-based URL classification.

This is a rule-based (non-ML) analyzer that evaluates URLs for:
- Known suspicious patterns
- Domain entropy (high entropy = random domain = suspicious)
- Suspicious TLDs
- IP address as hostname
- Excessive subdomains
- Known phishing patterns
- URL length anomalies

This runs entirely locally without any network calls.
"""

import re
import math
import logging
from urllib.parse import urlparse
from analyzer import AnalysisResult

logger = logging.getLogger('digitalguard.ai_engine.url_analyzer')


# ──────────────────────────────────────────────────────────────────────────────
# Known suspicious TLDs (commonly used in phishing/malware)
# ──────────────────────────────────────────────────────────────────────────────
SUSPICIOUS_TLDS = {
    '.tk', '.ml', '.ga', '.cf', '.gq', '.pw', '.top', '.xyz',
    '.club', '.work', '.click', '.link', '.download', '.loan',
}

# ──────────────────────────────────────────────────────────────────────────────
# Known adult/inappropriate domains (very small demo list — real list would be larger)
# ──────────────────────────────────────────────────────────────────────────────
ADULT_DOMAINS = {'pornhub.com', 'xvideos.com', 'xnxx.com', 'brazzers.com', 'onlyfans.com'}
GAMBLING_DOMAINS = {'bet365.com', 'pokerstars.com', 'draftkings.com', 'fanduel.com'}

# ──────────────────────────────────────────────────────────────────────────────
# Phishing keyword patterns in URLs
# ──────────────────────────────────────────────────────────────────────────────
PHISHING_URL_PATTERNS = [
    r'(paypa1|payp4l|paypai)',      # PayPal lookalike
    r'(g00gle|go0gle|gooogle)',      # Google lookalike
    r'(arnazon|amaz0n|amazom)',      # Amazon lookalike
    r'(micros0ft|micosoft)',         # Microsoft lookalike
    r'(faceb00k|facebok)',           # Facebook lookalike
    r'(paypal|apple|google|amazon|microsoft|netflix).*(security|update|verify|login|account)',
    r'secure.*login.*verify',
    r'security.*verify.*login',
    r'account.*suspend.*verify',
    r'confirm.*password.*account',
    r'bank.*login.*secure',
]

CATEGORY_ACTIONS = {
    'safe': 'ALLOW',
    'phishing': 'BLOCK',
    'adult': 'BLOCK',
    'gambling': 'BLOCK',
    'suspicious': 'WARN',
    'malware': 'BLOCK',
    'unknown': 'ALLOW',
}


def _shannon_entropy(s: str) -> float:
    """Calculate Shannon entropy of a string. High entropy = more random = suspicious."""
    if not s:
        return 0.0
    freq = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


class URLAnalyzer:
    """Heuristic URL classifier."""

    def analyze(self, url: str) -> AnalysisResult:
        """Analyze a URL and return risk classification."""
        indicators = []
        risk_score = 0.0
        category = 'unknown'

        try:
            parsed = urlparse(url if url.startswith('http') else f'http://{url}')
            hostname = parsed.hostname or ''
            path = parsed.path.lower()
            full_url_lower = url.lower()
        except Exception:
            return AnalysisResult(
                category='unknown',
                risk_score=0.1,
                confidence=0.5,
                recommended_action='ALLOW',
                inference_mode='HEURISTIC',
                indicators=['URL parsing failed'],
            )

        # ── 1. Check known domain lists ─────────────────────────────────────
        for domain in ADULT_DOMAINS:
            if domain in hostname:
                return AnalysisResult(
                    category='adult',
                    risk_score=0.95,
                    confidence=0.99,
                    recommended_action='BLOCK',
                    inference_mode='HEURISTIC',
                    indicators=[f'Known adult domain: {domain}'],
                )

        for domain in GAMBLING_DOMAINS:
            if domain in hostname:
                return AnalysisResult(
                    category='gambling',
                    risk_score=0.9,
                    confidence=0.99,
                    recommended_action='BLOCK',
                    inference_mode='HEURISTIC',
                    indicators=[f'Known gambling domain: {domain}'],
                )

        # ── 2. IP address as hostname ────────────────────────────────────────
        if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', hostname):
            indicators.append('IP address used as hostname (suspicious)')
            risk_score += 0.4
            category = 'suspicious'

        # ── 3. Suspicious TLD ────────────────────────────────────────────────
        for tld in SUSPICIOUS_TLDS:
            if hostname.endswith(tld):
                indicators.append(f'Suspicious TLD: {tld}')
                risk_score += 0.25
                category = 'suspicious'
                break

        # ── 4. Excessive subdomains ──────────────────────────────────────────
        subdomain_count = hostname.count('.')
        if subdomain_count > 4:
            indicators.append(f'Excessive subdomains ({subdomain_count})')
            risk_score += 0.2

        # ── 5. High domain entropy (random-looking domain) ───────────────────
        domain_part = hostname.split('.')[0] if '.' in hostname else hostname
        entropy = _shannon_entropy(domain_part)
        if entropy > 3.8 and len(domain_part) > 8:
            indicators.append(f'High domain entropy ({entropy:.2f}) — random-looking domain')
            risk_score += 0.15

        # ── 6. Phishing URL patterns ─────────────────────────────────────────
        for pattern in PHISHING_URL_PATTERNS:
            if re.search(pattern, full_url_lower):
                indicators.append(f'Phishing pattern match: {pattern}')
                risk_score += 0.4
                category = 'phishing'
                break

        # ── 7. URL length anomaly ────────────────────────────────────────────
        if len(url) > 200:
            indicators.append(f'Very long URL ({len(url)} chars)')
            risk_score += 0.1

        # ── 8. HTTPS check ──────────────────────────────────────────────────
        if parsed.scheme == 'http' and risk_score > 0.2:
            indicators.append('HTTP (not HTTPS) for a suspicious-looking URL')
            risk_score += 0.1

        # Cap risk score
        risk_score = min(risk_score, 1.0)

        # Determine final category
        if risk_score == 0.0:
            category = 'safe'
        elif risk_score < 0.3 and category == 'unknown':
            category = 'safe'
        elif category == 'unknown' and risk_score >= 0.3:
            category = 'suspicious'

        action = CATEGORY_ACTIONS.get(category, 'ALLOW')
        confidence = 0.7 if indicators else 0.9  # lower confidence when no indicators

        return AnalysisResult(
            category=category,
            risk_score=risk_score,
            confidence=confidence,
            recommended_action=action,
            inference_mode='HEURISTIC',
            indicators=indicators,
        )
