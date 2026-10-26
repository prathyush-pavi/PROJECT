// DigitalGuard Extension Options Logic
'use strict';

document.addEventListener('DOMContentLoaded', async () => {
  // Load saved preferences
  const config = await chrome.storage.local.get([
    'device_token',
    'api_base_url',
    'ai_engine_url',
    'protection_enabled',
    'auto_blur',
    'download_guard',
    'ai_sensitivity'
  ]);

  if (config.device_token) document.getElementById('deviceToken').value = config.device_token;
  if (config.api_base_url) document.getElementById('apiBaseUrl').value = config.api_base_url;
  if (config.ai_engine_url) document.getElementById('aiEngineUrl').value = config.ai_engine_url;
  
  document.getElementById('toggleProtection').checked = config.protection_enabled !== false;
  document.getElementById('toggleBlur').checked = config.auto_blur !== false;
  document.getElementById('toggleDownloads').checked = config.download_guard !== false;
  
  if (config.ai_sensitivity) {
    document.getElementById('aiSensitivity').value = config.ai_sensitivity;
    document.getElementById('sensitivityVal').textContent = Math.round(config.ai_sensitivity * 100) + '%';
  }

  // Update range slider label
  document.getElementById('aiSensitivity').addEventListener('input', (e) => {
    document.getElementById('sensitivityVal').textContent = Math.round(e.target.value * 100) + '%';
  });

  // Paste clipboard helper
  document.getElementById('btnPasteToken').addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      document.getElementById('deviceToken').value = text.trim();
    } catch (err) {
      console.warn('Clipboard read denied');
    }
  });

  // Test Connection
  document.getElementById('btnTestConnection').addEventListener('click', async () => {
    const banner = document.getElementById('connResult');
    const apiBase = document.getElementById('apiBaseUrl').value.trim() || 'http://127.0.0.1:8000';
    const token = document.getElementById('deviceToken').value.trim();

    banner.style.display = 'block';
    banner.className = 'conn-banner testing';
    banner.textContent = 'Connecting to backend and checking device token...';

    try {
      const resp = await fetch(`${apiBase}/api/`, { method: 'GET' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      let tokenMsg = '';
      if (token) {
        tokenMsg = ' & Device Token configured';
      } else {
        tokenMsg = ' (Warning: No Device Token set)';
      }

      banner.className = 'conn-banner success';
      banner.textContent = `✓ Connected to DigitalGuard Backend (v${data.data?.version || '1.0'})${tokenMsg}`;
    } catch (err) {
      banner.className = 'conn-banner error';
      banner.textContent = `✗ Connection failed: ${err.message}. Ensure Django server is running on ${apiBase}.`;
    }
  });

  // Save preferences
  document.getElementById('btnSaveConfig').addEventListener('click', async () => {
    const deviceToken = document.getElementById('deviceToken').value.trim();
    const apiBaseUrl = document.getElementById('apiBaseUrl').value.trim() || 'http://127.0.0.1:8000';
    const aiEngineUrl = document.getElementById('aiEngineUrl').value.trim() || 'http://127.0.0.1:8765';
    const protectionEnabled = document.getElementById('toggleProtection').checked;
    const autoBlur = document.getElementById('toggleBlur').checked;
    const downloadGuard = document.getElementById('toggleDownloads').checked;
    const aiSensitivity = parseFloat(document.getElementById('aiSensitivity').value);

    await chrome.storage.local.set({
      device_token: deviceToken,
      api_base_url: apiBaseUrl,
      ai_engine_url: aiEngineUrl,
      protection_enabled: protectionEnabled,
      auto_blur: autoBlur,
      download_guard: downloadGuard,
      ai_sensitivity: aiSensitivity
    });

    const statusText = document.getElementById('saveStatusText');
    statusText.textContent = '✓ Configuration saved successfully!';
    statusText.style.color = '#34d399';
    setTimeout(() => {
      statusText.textContent = 'All configurations synchronized';
      statusText.style.color = '#94a3b8';
    }, 2500);
  });
});
