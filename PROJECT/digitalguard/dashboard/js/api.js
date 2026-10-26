/**
 * DigitalGuard Parental Dashboard — API Client Layer
 * Supports live Django backend integration with seamless fallback to built-in Demo Mode.
 */

'use strict';

const API = (() => {
  const BASE_URL = 'http://127.0.0.1:8000';
  let isDemoMode = false;

  // Mock State for Demo Mode
  const DEMO_STATE = {
    parent: {
      name: "Sarah Connor",
      email: "parent@digitalguard.local",
      role: "Parent"
    },
    children: [
      { id: "c1", name: "Alex Connor", age: 12, avatar: "👦", device_count: 2, status: "Active" },
      { id: "c2", name: "Emma Connor", age: 8, avatar: "👧", device_count: 1, status: "Active" }
    ],
    devices: [
      { id: "d1", name: "Alex's Windows Gaming PC", child_name: "Alex Connor", os: "Windows 11", type: "DESKTOP", last_seen: "Just now", status: "Online" },
      { id: "d2", name: "Alex's School Laptop", child_name: "Alex Connor", os: "Windows 11", type: "LAPTOP", last_seen: "2 hours ago", status: "Offline" },
      { id: "d3", name: "Emma's Family Tablet", child_name: "Emma Connor", os: "Android 14", type: "TABLET", last_seen: "45 mins ago", status: "Online" }
    ],
    summary: {
      total_events: 142,
      sites_visited: 86,
      sites_blocked: 8,
      threats_detected: 3,
      screen_time_mins: 165,
      unread_alerts: 2
    },
    activities: [
      { id: "a1", event_type: "PHISHING_DETECTED", domain: "phishing-bank-login.xyz", url_path: "/login", category: "phishing", action: "BLOCK", severity: "CRITICAL", timestamp: "15 mins ago" },
      { id: "a2", event_type: "CYBERBULLYING_DETECTED", domain: "web.discord.com", url_path: "/channels/general", category: "cyberbullying", action: "BLUR", severity: "HIGH", timestamp: "1 hour ago" },
      { id: "a3", event_type: "APPLICATION_BLOCKED", app_name: "cheatengine.exe", domain: "", url_path: "", category: "application", action: "BLOCK", severity: "HIGH", timestamp: "3 hours ago" },
      { id: "a4", event_type: "WEBSITE_VISITED", domain: "khanacademy.org", url_path: "/math/algebra", category: "education", action: "ALLOW", severity: "LOW", timestamp: "4 hours ago" },
      { id: "a5", event_type: "WEBSITE_VISITED", domain: "wikipedia.org", url_path: "/wiki/Apollo_11", category: "education", action: "ALLOW", severity: "LOW", timestamp: "5 hours ago" },
      { id: "a6", event_type: "WEBSITE_WARNING", domain: "reddit.com", url_path: "/r/gaming", category: "social_media", action: "WARN", severity: "MEDIUM", timestamp: "6 hours ago" }
    ],
    alerts: [
      { id: "al1", alert_type: "phishing", severity: "CRITICAL", title: "Critical: Phishing Intercepted", message: "Blocked connection to credential harvesting domain 'phishing-bank-login.xyz'.", is_read: false, created_at: "15 mins ago" },
      { id: "al2", alert_type: "cyberbullying", severity: "HIGH", title: "Harassment Detected on Discord", message: "AI detected aggressive bullying pattern. Content blurred on Alex's screen.", is_read: false, created_at: "1 hour ago" },
      { id: "al3", alert_type: "app_blocked", severity: "MEDIUM", title: "Restricted App Blocked", message: "Alex launched cheatengine.exe. The application was minimized and halted.", is_read: true, created_at: "3 hours ago" }
    ],
    websites: [
      { id: "w1", domain: "darknet-market.cc", rule_type: "BLOCK", category: "malware", reason: "Illicit domain" },
      { id: "w2", domain: "phishing-bank-login.xyz", rule_type: "BLOCK", category: "phishing", reason: "Known credential stealer" },
      { id: "w3", domain: "adult-xxx-stream.net", rule_type: "BLOCK", category: "adult", reason: "Adult content" },
      { id: "w4", domain: "reddit.com", rule_type: "WARN", category: "social_media", reason: "Social forum" },
      { id: "w5", domain: "khanacademy.org", rule_type: "ALLOW", category: "education", reason: "Learning platform" }
    ],
    applications: [
      { id: "ap1", app_name: "cheatengine.exe", policy: "BLOCK", daily_limit_minutes: 0 },
      { id: "ap2", app_name: "utorrent.exe", policy: "BLOCK", daily_limit_minutes: 0 },
      { id: "ap3", app_name: "roblox.exe", policy: "LIMITED", daily_limit_minutes: 60 },
      { id: "ap4", app_name: "discord.exe", policy: "LIMITED", daily_limit_minutes: 45 },
      { id: "ap5", app_name: "chrome.exe", policy: "ALLOW", daily_limit_minutes: 0 }
    ],
    screentime_chart: {
      labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      datasets: [
        { label: 'Alex (Hours)', data: [2.5, 3.1, 2.0, 2.8, 3.5, 4.2, 3.8] },
        { label: 'Emma (Hours)', data: [1.2, 1.0, 1.5, 1.1, 1.4, 2.0, 1.8] }
      ]
    }
  };

  function getToken() {
    return localStorage.getItem('dg_access_token');
  }

  function setToken(token) {
    localStorage.setItem('dg_access_token', token);
  }

  function clearToken() {
    localStorage.removeItem('dg_access_token');
    localStorage.removeItem('dg_refresh_token');
  }

  async function request(endpoint, options = {}) {
    if (isDemoMode) return null;

    options.headers = options.headers || {};
    options.headers['Content-Type'] = 'application/json';
    const token = getToken();
    if (token) {
      options.headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const res = await fetch(`${BASE_URL}${endpoint}`, options);
      if (res.status === 401) {
        clearToken();
        window.dispatchEvent(new CustomEvent('auth:expired'));
        throw new Error('Authentication expired');
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.message || `HTTP ${res.status}`);
      }
      return await res.json();
    } catch (e) {
      console.warn(`[API] ${endpoint} failed:`, e.message);
      throw e;
    }
  }

  return {
    setDemoMode(enabled) {
      isDemoMode = enabled;
      localStorage.setItem('dg_demo_mode', enabled ? '1' : '0');
    },
    isDemoMode() {
      return isDemoMode || localStorage.getItem('dg_demo_mode') === '1';
    },

    // Auth
    async login(email, password) {
      if (isDemoMode) {
        return { success: true, data: { user: DEMO_STATE.parent, tokens: { access: 'demo_token' } } };
      }
      const data = await request('/api/auth/login/', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      });
      if (data?.data?.tokens?.access) {
        setToken(data.data.tokens.access);
        if (data.data.tokens.refresh) {
          localStorage.setItem('dg_refresh_token', data.data.tokens.refresh);
        }
      }
      return data;
    },

    async register(name, email, username, password) {
      if (isDemoMode) return { success: true };
      return await request('/api/auth/register/', {
        method: 'POST',
        body: JSON.stringify({ display_name: name, email, username, password })
      });
    },

    logout() {
      clearToken();
      this.setDemoMode(false);
    },

    // Dashboard
    async getSummary(childId = null) {
      if (this.isDemoMode()) return DEMO_STATE.summary;
      try {
        const url = childId ? `/api/dashboard/summary/?child_id=${childId}` : '/api/dashboard/summary/';
        const res = await request(url);
        return res?.data || DEMO_STATE.summary;
      } catch {
        return DEMO_STATE.summary;
      }
    },

    async getChildren() {
      if (this.isDemoMode()) return DEMO_STATE.children;
      try {
        const res = await request('/api/children/');
        return res?.data?.results || res?.data || DEMO_STATE.children;
      } catch {
        return DEMO_STATE.children;
      }
    },

    async getDevices() {
      if (this.isDemoMode()) return DEMO_STATE.devices;
      try {
        const res = await request('/api/devices/');
        return res?.data?.results || res?.data || DEMO_STATE.devices;
      } catch {
        return DEMO_STATE.devices;
      }
    },

    async getActivities(params = {}) {
      if (this.isDemoMode()) {
        let list = [...DEMO_STATE.activities];
        if (params.event_type) list = list.filter(a => a.event_type === params.event_type);
        if (params.severity) list = list.filter(a => a.severity === params.severity);
        return list;
      }
      try {
        const query = new URLSearchParams(params).toString();
        const res = await request(`/api/activity/?${query}`);
        return res?.data?.results || res?.data || DEMO_STATE.activities;
      } catch {
        return DEMO_STATE.activities;
      }
    },

    async getAlerts() {
      if (this.isDemoMode()) return DEMO_STATE.alerts;
      try {
        const res = await request('/api/alerts/');
        return res?.data?.results || res?.data || DEMO_STATE.alerts;
      } catch {
        return DEMO_STATE.alerts;
      }
    },

    async markAlertRead(alertId) {
      if (this.isDemoMode()) {
        const al = DEMO_STATE.alerts.find(a => a.id === alertId);
        if (al) al.is_read = true;
        return { success: true };
      }
      return await request(`/api/alerts/${alertId}/mark-read/`, { method: 'PATCH' });
    },

    async getWebsites() {
      if (this.isDemoMode()) return DEMO_STATE.websites;
      try {
        const res = await request('/api/policies/websites/');
        return res?.data?.results || res?.data || DEMO_STATE.websites;
      } catch {
        return DEMO_STATE.websites;
      }
    },

    async addWebsite(rule) {
      if (this.isDemoMode()) {
        const newRule = { id: 'w_' + Date.now(), ...rule };
        DEMO_STATE.websites.unshift(newRule);
        return newRule;
      }
      return await request('/api/policies/websites/', { method: 'POST', body: JSON.stringify(rule) });
    },

    async deleteWebsite(id) {
      if (this.isDemoMode()) {
        DEMO_STATE.websites = DEMO_STATE.websites.filter(w => w.id !== id);
        return { success: true };
      }
      return await request(`/api/policies/websites/${id}/`, { method: 'DELETE' });
    },

    async getApplications() {
      if (this.isDemoMode()) return DEMO_STATE.applications;
      try {
        const res = await request('/api/policies/applications/');
        return res?.data?.results || res?.data || DEMO_STATE.applications;
      } catch {
        return DEMO_STATE.applications;
      }
    },

    async addApplication(rule) {
      if (this.isDemoMode()) {
        const newRule = { id: 'ap_' + Date.now(), ...rule };
        DEMO_STATE.applications.unshift(newRule);
        return newRule;
      }
      return await request('/api/policies/applications/', { method: 'POST', body: JSON.stringify(rule) });
    },

    async deleteApplication(id) {
      if (this.isDemoMode()) {
        DEMO_STATE.applications = DEMO_STATE.applications.filter(a => a.id !== id);
        return { success: true };
      }
      return await request(`/api/policies/applications/${id}/`, { method: 'DELETE' });
    },

    async getScreenTimeData() {
      if (this.isDemoMode()) return DEMO_STATE.screentime_chart;
      try {
        const res = await request('/api/screentime/usage/');
        return res?.data || DEMO_STATE.screentime_chart;
      } catch {
        return DEMO_STATE.screentime_chart;
      }
    },

    async checkAIHealth() {
      try {
        const res = await fetch('http://127.0.0.1:8765/health', { signal: AbortSignal.timeout(2000) });
        if (res.ok) return await res.json();
      } catch {
        return { status: 'offline', inference_mode: 'MOCK' };
      }
      return { status: 'offline', inference_mode: 'MOCK' };
    },

    // ── WebAuthn / Passkey ──────────────────────────────────────────
    async getPasskeys() {
      if (this.isDemoMode()) return [
        { id: 'pk1', display_name: 'MacBook Touch ID', created_at: '2026-08-10T10:00:00Z', last_used: '2 hours ago' }
      ];
      try {
        const res = await request('/api/auth/passkeys/');
        return res?.data?.results || res?.data || [];
      } catch {
        return [];
      }
    },

    async deletePasskey(id) {
      if (this.isDemoMode()) return { success: true };
      return await request(`/api/auth/passkeys/${id}/`, { method: 'DELETE' });
    },

    async webauthnRegisterOptions() {
      return await request('/api/auth/webauthn/register-options/', { method: 'POST' });
    },

    async webauthnRegisterVerify(credential) {
      return await request('/api/auth/webauthn/register-verify/', {
        method: 'POST',
        body: JSON.stringify(credential)
      });
    },

    async webauthnAuthOptions(email) {
      return await request('/api/auth/webauthn/auth-options/', {
        method: 'POST',
        body: JSON.stringify({ email })
      });
    },

    async webauthnAuthVerify(credential) {
      const data = await request('/api/auth/webauthn/auth-verify/', {
        method: 'POST',
        body: JSON.stringify(credential)
      });
      if (data?.data?.tokens?.access) {
        setToken(data.data.tokens.access);
        if (data.data.tokens.refresh) {
          localStorage.setItem('dg_refresh_token', data.data.tokens.refresh);
        }
      }
      return data;
    }
  };
})();
