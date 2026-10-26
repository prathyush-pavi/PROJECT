/**
 * DigitalGuard Extension Popup Script
 * Displays current tab status, protection toggle, and today's stats.
 */

'use strict';

const STATUS_CONFIG = {
  ALLOW: { icon: '✓', text: 'Safe', cls: 'safe', riskClass: 'risk-low' },
  WARN:  { icon: '⚠', text: 'Warning', cls: 'warning', riskClass: 'risk-med' },
  BLUR:  { icon: '🔵', text: 'Blurred', cls: 'warning', riskClass: 'risk-med' },
  BLOCK: { icon: '✕', text: 'Blocked', cls: 'blocked', riskClass: 'risk-high' },
  checking: { icon: '◌', text: 'Checking...', cls: 'checking', riskClass: 'risk-low' },
  not_configured: { icon: '!', text: 'Not Configured', cls: 'warning', riskClass: 'risk-low' },
};

async function getCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function getTabState(tabId) {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, { type: 'GET_TAB_STATUS' }, (resp) => {
      if (chrome.runtime.lastError) {
        resolve(null);
        return;
      }
      resolve(resp?.state || null);
    });
  });
}

async function updateUI() {
  const tab = await getCurrentTab();
  if (!tab) return;

  const url = tab.url || '';
  const urlEl = document.getElementById('current-url');

  // Show abbreviated URL
  try {
    const u = new URL(url);
    urlEl.textContent = u.hostname;
    urlEl.title = url;
  } catch {
    urlEl.textContent = url.substring(0, 50);
  }

  // Check if extension is configured
  const config = await chrome.storage.local.get(['device_token', 'protection_enabled']);
  const protectionEnabled = config.protection_enabled !== false;

  // Update toggle
  const toggle = document.getElementById('toggle-protection');
  const label = document.getElementById('protection-label');
  toggle.className = 'header-toggle' + (protectionEnabled ? ' on' : '');
  label.textContent = protectionEnabled ? 'Protection Active' : 'Protection Off';

  if (!config.device_token) {
    setStatus('not_configured', 0, 'UNKNOWN');
    return;
  }

  // Get tab status from background
  const state = await new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: 'GET_TAB_STATUS', tabId: tab.id }, (resp) => {
      resolve(resp?.state || null);
    });
  });

  if (state) {
    setStatus(state.status || 'ALLOW', state.riskScore || 0, state.inferenceMode);
  } else {
    setStatus('checking', 0, 'UNKNOWN');
  }

  // Load today's stats from storage
  loadTodayStats();
}

function setStatus(status, riskScore, inferenceMode) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG['checking'];
  const badge = document.getElementById('status-badge');
  const icon = document.getElementById('status-icon');
  const text = document.getElementById('status-text');
  const bar = document.getElementById('risk-bar-fill');
  const barContainer = document.getElementById('risk-bar-container');
  const riskLabel = document.getElementById('risk-score-label');
  const mockBadge = document.getElementById('inference-mode-badge');

  badge.className = `status-badge ${cfg.cls}`;
  icon.textContent = cfg.icon;
  text.textContent = cfg.text;

  const riskPct = Math.round((riskScore || 0) * 100);
  bar.style.width = `${riskPct}%`;
  riskLabel.textContent = `${riskPct}%`;
  barContainer.className = `risk-bar ${cfg.riskClass}`;

  // Show MOCK badge if inference is from mock model
  if (inferenceMode === 'MOCK' || inferenceMode === 'HEURISTIC') {
    mockBadge.style.display = 'inline-block';
  } else {
    mockBadge.style.display = 'none';
  }
}

function loadTodayStats() {
  chrome.storage.local.get(['today_visited', 'today_blocked'], (data) => {
    document.getElementById('stat-visited').textContent = data.today_visited || 0;
    document.getElementById('stat-blocked').textContent = data.today_blocked || 0;
  });
}

// ── Event listeners ──────────────────────────────────────────────────────────
document.getElementById('toggle-protection').addEventListener('click', async () => {
  const config = await chrome.storage.local.get(['protection_enabled']);
  const current = config.protection_enabled !== false;
  await chrome.storage.local.set({ protection_enabled: !current });
  updateUI();
});

document.getElementById('btn-settings').addEventListener('click', () => {
  chrome.runtime.openOptionsPage();
});

document.getElementById('btn-report').addEventListener('click', async () => {
  const tab = await getCurrentTab();
  const url = tab?.url || '';
  alert(`[DigitalGuard] Reporting this URL for review:\n${url}\n\n(In production, this would submit to the parent dashboard.)`);
});

// Initialize
updateUI();
