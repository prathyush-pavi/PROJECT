/**
 * DigitalGuard — Browser Extension Service Worker (MV3)
 *
 * Responsibilities:
 * - Monitor navigation events (URL changes)
 * - Check URLs against parent policies and AI classification
 * - Monitor downloads for suspicious file types
 * - Relay messages from content scripts
 * - Maintain a local policy cache (5-minute TTL)
 * - Communicate with the DigitalGuard backend API
 */

'use strict';

// ─── Configuration ─────────────────────────────────────────────────────────
const CONFIG = {
  API_BASE_URL: 'http://127.0.0.1:8000',
  POLICY_CACHE_TTL_MS: 5 * 60 * 1000,  // 5 minutes
  SUSPICIOUS_EXTENSIONS: [
    '.exe', '.msi', '.bat', '.cmd', '.vbs', '.js', '.jar',
    '.scr', '.pif', '.com', '.dll', '.ps1', '.sh'
  ],
  // Event types for activity logging
  EVENT_TYPES: {
    WEBSITE_VISITED: 'WEBSITE_VISITED',
    WEBSITE_BLOCKED: 'WEBSITE_BLOCKED',
    WEBSITE_WARNING: 'WEBSITE_WARNING',
    PHISHING_DETECTED: 'PHISHING_DETECTED',
    DOWNLOAD_ATTEMPTED: 'DOWNLOAD_ATTEMPTED',
    DOWNLOAD_BLOCKED: 'DOWNLOAD_BLOCKED',
    CONTENT_FLAGGED: 'CONTENT_FLAGGED',
  }
};

// ─── State ──────────────────────────────────────────────────────────────────
// In-memory policy cache: { domain: { result, timestamp } }
const policyCache = new Map();
// Per-tab state: { tabId: { url, status, lastCheck } }
const tabState = new Map();
// Image scan cache: { imageUrl: { result, timestamp } } — 10 min TTL
const imageScanCache = new Map();
const IMAGE_SCAN_CACHE_TTL_MS = 10 * 60 * 1000;

// ─── Storage helpers ────────────────────────────────────────────────────────
async function getStoredConfig() {
  return chrome.storage.local.get([
    'device_token', 'child_id', 'protection_enabled', 'api_base_url'
  ]);
}

async function isProtectionEnabled() {
  const config = await getStoredConfig();
  return config.protection_enabled !== false;  // Default: enabled
}

async function getDeviceToken() {
  const config = await getStoredConfig();
  return config.device_token || null;
}

// ─── API communication ──────────────────────────────────────────────────────
/**
 * Check a URL against the backend policy/AI classification.
 * Uses cache to avoid redundant API calls.
 */
async function checkUrl(url, tabId) {
  try {
    const urlObj = new URL(url);
    const domain = urlObj.hostname.replace(/^www\./, '');

    // Skip internal/system URLs
    if (shouldSkipUrl(url)) {
      return { recommended_action: 'ALLOW', category: 'safe', source: 'skipped' };
    }

    // Check cache
    const cached = policyCache.get(domain);
    if (cached && (Date.now() - cached.timestamp) < CONFIG.POLICY_CACHE_TTL_MS) {
      return cached.result;
    }

    const deviceToken = await getDeviceToken();
    if (!deviceToken) {
      // Extension not configured — allow by default
      return { recommended_action: 'ALLOW', category: 'unknown', source: 'not_configured' };
    }

    const apiBase = (await getStoredConfig()).api_base_url || CONFIG.API_BASE_URL;

    const response = await fetch(`${apiBase}/api/browser/check-url/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `DeviceToken ${deviceToken}`,
      },
      body: JSON.stringify({ url }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    const result = data.data || data;

    // Cache the result
    policyCache.set(domain, { result, timestamp: Date.now() });
    return result;

  } catch (error) {
    console.warn('[DigitalGuard] URL check failed:', error.message, '— defaulting to ALLOW');
    // Fail safe: allow on error, log locally
    return { recommended_action: 'ALLOW', category: 'unknown', source: 'error' };
  }
}

/**
 * Ingest an activity event to the backend.
 * Fire-and-forget — don't block navigation on this.
 */
async function ingestActivity(eventData) {
  try {
    const deviceToken = await getDeviceToken();
    if (!deviceToken) return;

    const apiBase = (await getStoredConfig()).api_base_url || CONFIG.API_BASE_URL;

    fetch(`${apiBase}/api/activity/ingest/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `DeviceToken ${deviceToken}`,
      },
      body: JSON.stringify({
        event_type: eventData.event_type,
        timestamp: new Date().toISOString(),
        severity: eventData.severity || 'LOW',
        category: eventData.category || '',
        domain: eventData.domain || '',
        url_path: eventData.url_path || '',
        app_name: '',
        action_taken: eventData.action || 'ALLOW',
        metadata: eventData.metadata || {},
      }),
    }).catch(err => console.warn('[DigitalGuard] Activity ingest failed:', err.message));
  } catch (error) {
    console.warn('[DigitalGuard] Ingest error:', error.message);
  }
}

// ─── URL filtering ──────────────────────────────────────────────────────────
function shouldSkipUrl(url) {
  if (!url) return true;
  if (url.startsWith('chrome://') || url.startsWith('chrome-extension://')) return true;
  if (url.startsWith('about:') || url.startsWith('moz-extension://')) return true;
  if (url.startsWith('edge://') || url.startsWith('brave://')) return true;
  if (url === 'about:blank' || url === 'about:newtab') return true;
  return false;
}

function extractDomain(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

function extractPath(url) {
  try {
    const u = new URL(url);
    // Return path only, strip query string for privacy
    return u.pathname;
  } catch {
    return '';
  }
}

function getSeverityForCategory(category, action) {
  if (action === 'BLOCK') {
    const highSeverity = ['phishing', 'malware', 'grooming', 'adult'];
    return highSeverity.includes(category) ? 'HIGH' : 'MEDIUM';
  }
  if (action === 'WARN') return 'MEDIUM';
  return 'LOW';
}

// ─── Navigation monitoring ──────────────────────────────────────────────────
/**
 * Main URL processing function.
 * Called on every committed navigation.
 */
async function processNavigation(tabId, url) {
  if (!await isProtectionEnabled()) return;
  if (shouldSkipUrl(url)) return;

  const domain = extractDomain(url);
  const urlPath = extractPath(url);

  tabState.set(tabId, { url, domain, status: 'checking', timestamp: Date.now() });

  const result = await checkUrl(url, tabId);
  const action = result.recommended_action || 'ALLOW';
  const category = result.category || 'unknown';
  const riskScore = result.risk_score || 0.0;

  // Update tab state
  tabState.set(tabId, { url, domain, status: action, category, riskScore, timestamp: Date.now() });

  // Notify content script of the verdict
  try {
    chrome.tabs.sendMessage(tabId, {
      type: 'PROTECTION_VERDICT',
      action,
      category,
      riskScore,
      domain,
      inferenceMode: result.inference_mode || 'UNKNOWN',
    });
  } catch (e) {
    // Content script may not be ready yet — that's OK
  }

  const severity = getSeverityForCategory(category, action);

  // Handle enforcement
  if (action === 'BLOCK') {
    // Redirect to block page
    chrome.tabs.update(tabId, {
      url: chrome.runtime.getURL('content/blocked.html') +
           `?domain=${encodeURIComponent(domain)}&category=${encodeURIComponent(category)}&reason=${encodeURIComponent(result.reason || '')}`
    });

    const isPhishing = category === 'phishing';
    await ingestActivity({
      event_type: isPhishing ? CONFIG.EVENT_TYPES.PHISHING_DETECTED : CONFIG.EVENT_TYPES.WEBSITE_BLOCKED,
      severity: isPhishing ? 'HIGH' : severity,
      category,
      domain,
      url_path: urlPath,
      action: 'BLOCK',
      metadata: { risk_score: riskScore, inference_mode: result.inference_mode, source: result.source },
    });

  } else if (action === 'WARN') {
    // Content script will show warning overlay
    await ingestActivity({
      event_type: CONFIG.EVENT_TYPES.WEBSITE_WARNING,
      severity,
      category,
      domain,
      url_path: urlPath,
      action: 'WARN',
      metadata: { risk_score: riskScore },
    });

  } else {
    // Allowed — log as website visited (fire-and-forget)
    ingestActivity({
      event_type: CONFIG.EVENT_TYPES.WEBSITE_VISITED,
      severity: 'LOW',
      category,
      domain,
      url_path: urlPath,
      action: 'ALLOW',
      metadata: { risk_score: riskScore },
    });
  }
}

// ─── Event listeners ─────────────────────────────────────────────────────────

// Monitor committed navigations (main frame only)
chrome.webNavigation.onCommitted.addListener(
  (details) => {
    if (details.frameId !== 0) return;  // main frame only
    processNavigation(details.tabId, details.url);
  },
  { url: [{ schemes: ['http', 'https'] }] }
);

// Monitor downloads
chrome.downloads.onCreated.addListener(async (downloadItem) => {
  if (!await isProtectionEnabled()) return;

  const filename = downloadItem.filename || downloadItem.url || '';
  const lowerFilename = filename.toLowerCase();
  const isSuspicious = CONFIG.SUSPICIOUS_EXTENSIONS.some(ext => lowerFilename.endsWith(ext));

  if (isSuspicious) {
    const ext = CONFIG.SUSPICIOUS_EXTENSIONS.find(ext => lowerFilename.endsWith(ext));
    console.warn('[DigitalGuard] Suspicious download detected:', filename);

    ingestActivity({
      event_type: CONFIG.EVENT_TYPES.DOWNLOAD_ATTEMPTED,
      severity: 'MEDIUM',
      category: 'suspicious_download',
      domain: extractDomain(downloadItem.url || ''),
      action: 'WARN',
      metadata: {
        filename: lowerFilename.split('/').pop(),  // filename only, not full path
        extension: ext,
        url: downloadItem.url?.split('?')[0] || '',  // URL without query params
      },
    });

    // Note: MV3 downloads API cannot cancel a download that has already started.
    // We warn the parent via activity log. Domain blocking via declarativeNetRequest
    // is the mechanism for blocking download sources proactively.
  }
});

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_TAB_STATUS') {
    const state = tabState.get(sender.tab?.id);
    sendResponse({ state: state || null });
    return true;
  }

  if (message.type === 'CONTENT_ANALYSIS_REQUEST') {
    // Content script is requesting text analysis
    handleContentAnalysis(message, sender.tab?.id).then(sendResponse);
    return true;  // Keep message channel open for async response
  }

  if (message.type === 'CONTENT_IMAGE_SCAN_REQUEST') {
    // Content script is requesting image analysis
    handleImageScan(message, sender.tab?.id).then(sendResponse);
    return true;  // Keep message channel open for async response
  }

  if (message.type === 'GET_CONFIG') {
    getStoredConfig().then(sendResponse);
    return true;
  }
});

// Handle content analysis requests from content script
async function handleContentAnalysis(message, tabId) {
  try {
    const deviceToken = await getDeviceToken();
    if (!deviceToken) return { action: 'ALLOW', category: 'unknown', error: 'not_configured' };

    const apiBase = (await getStoredConfig()).api_base_url || CONFIG.API_BASE_URL;

    const response = await fetch(`${apiBase}/api/ai/analyze/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `DeviceToken ${deviceToken}`,
      },
      body: JSON.stringify({
        text: message.text,
        context: message.context || 'webpage',
      }),
    });

    if (!response.ok) throw new Error(`API error: ${response.status}`);
    const data = await response.json();
    return data.data || data;
  } catch (error) {
    console.warn('[DigitalGuard] Content analysis failed:', error.message);
    return { action: 'ALLOW', category: 'unknown', error: error.message };
  }
}

// Clear old cache entries periodically
setInterval(() => {
  const now = Date.now();
  for (const [domain, entry] of policyCache.entries()) {
    if (now - entry.timestamp > CONFIG.POLICY_CACHE_TTL_MS) {
      policyCache.delete(domain);
    }
  }
  for (const [url, entry] of imageScanCache.entries()) {
    if (now - entry.timestamp > IMAGE_SCAN_CACHE_TTL_MS) {
      imageScanCache.delete(url);
    }
  }
}, 60 * 1000);

// Handle image scan requests from content script
async function handleImageScan(message, tabId) {
  const { imageUrl } = message;
  if (!imageUrl) return { recommended_action: 'ALLOW', category: 'unknown', error: 'no_url' };

  // Check in-memory cache first
  const cached = imageScanCache.get(imageUrl);
  if (cached && (Date.now() - cached.timestamp) < IMAGE_SCAN_CACHE_TTL_MS) {
    return cached.result;
  }

  try {
    const deviceToken = await getDeviceToken();
    if (!deviceToken) return { recommended_action: 'ALLOW', category: 'unknown', error: 'not_configured' };

    const apiBase = (await getStoredConfig()).api_base_url || CONFIG.API_BASE_URL;

    const response = await fetch(`${apiBase}/api/ai/analyze-image/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `DeviceToken ${deviceToken}`,
      },
      body: JSON.stringify({ image_url: imageUrl }),
    });

    if (!response.ok) throw new Error(`API error: ${response.status}`);
    const data = await response.json();
    const result = data.data || data;

    // Cache the verdict
    imageScanCache.set(imageUrl, { result, timestamp: Date.now() });

    // If image is flagged as adult/suspicious, log it
    const action = result.recommended_action || 'ALLOW';
    if (action !== 'ALLOW') {
      ingestActivity({
        event_type: CONFIG.EVENT_TYPES.CONTENT_FLAGGED,
        severity: action === 'BLOCK' ? 'HIGH' : 'MEDIUM',
        category: result.category || 'adult',
        domain: (() => { try { return new URL(imageUrl).hostname; } catch { return ''; } })(),
        action,
        metadata: {
          type: 'image',
          risk_score: result.risk_score,
          inference_mode: result.inference_mode,
          image_url: imageUrl.substring(0, 150),
        },
      });
    }

    return result;
  } catch (error) {
    console.warn('[DigitalGuard] Image scan failed:', error.message, imageUrl.substring(0, 80));
    return { recommended_action: 'ALLOW', category: 'unknown', error: error.message };
  }
}

console.log('[DigitalGuard] Service worker initialized.');
