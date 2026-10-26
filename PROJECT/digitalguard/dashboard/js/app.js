/**
 * DigitalGuard Parental Control Dashboard — Main Application Logic
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
  let activePage = 'overview';
  let screentimeChart = null;
  let appBreakdownChart = null;
  let pollInterval = null;

  // DOM Elements
  const loginScreen = document.getElementById('login-screen');
  const registerScreen = document.getElementById('register-screen');
  const appScreen = document.getElementById('app-screen');
  const sidebar = document.getElementById('sidebar');
  const navItems = document.querySelectorAll('.nav-item');
  const pages = document.querySelectorAll('.page');
  const topbarTitle = document.getElementById('topbar-title');
  const childFilter = document.getElementById('child-filter');

  // Format Date
  const todayDateEl = document.getElementById('today-date');
  if (todayDateEl) {
    todayDateEl.textContent = new Date().toLocaleDateString('en-US', {
      weekday: 'long', month: 'short', day: 'numeric', year: 'numeric'
    });
  }

  // Toast Helper
  function showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
  }

  // Navigation Logic
  function showScreen(screen) {
    [loginScreen, registerScreen, appScreen].forEach(s => s?.classList.remove('active'));
    screen.classList.add('active');
  }

  function navigateTo(pageId) {
    activePage = pageId;
    navItems.forEach(n => {
      n.classList.toggle('active', n.dataset.page === pageId);
    });
    pages.forEach(p => {
      p.classList.toggle('active', p.id === `page-${pageId}`);
    });

    if (topbarTitle) {
      const activeNav = document.querySelector(`.nav-item[data-page="${pageId}"] .nav-label`);
      topbarTitle.textContent = activeNav ? activeNav.textContent : 'Dashboard';
    }

    loadPageData(pageId);
  }

  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const pageId = item.dataset.page;
      if (pageId) navigateTo(pageId);
      if (window.innerWidth <= 900) sidebar.classList.remove('open');
    });
  });

  // Mobile sidebar toggle
  document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });

  // Screen Switchers
  document.getElementById('show-register')?.addEventListener('click', (e) => {
    e.preventDefault();
    showScreen(registerScreen);
  });
  document.getElementById('show-login')?.addEventListener('click', (e) => {
    e.preventDefault();
    showScreen(loginScreen);
  });

  // Demo Button
  document.getElementById('demo-btn')?.addEventListener('click', () => {
    API.setDemoMode(true);
    document.getElementById('user-name').textContent = "Sarah Connor";
    showScreen(appScreen);
    navigateTo('overview');
    showToast('🎭 Loaded in Interactive Demo Mode with complete mock dataset', 'success');
  });

  // Login Form
  document.getElementById('login-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const btn = document.getElementById('login-btn');
    const errEl = document.getElementById('login-error');

    if (errEl) errEl.style.display = 'none';
    if (btn) btn.disabled = true;

    try {
      const resp = await API.login(email, password);
      const userName = resp?.data?.user?.display_name || email;
      document.getElementById('user-name').textContent = userName;
      showScreen(appScreen);
      navigateTo('overview');
      startPolling();
    } catch (err) {
      if (errEl) {
        errEl.textContent = err.message || 'Login failed. Please verify credentials.';
        errEl.style.display = 'block';
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  // Logout
  document.getElementById('logout-btn')?.addEventListener('click', () => {
    API.logout();
    stopPolling();
    showScreen(loginScreen);
    showToast('Signed out successfully');
  });

  // Child filter selector
  childFilter?.addEventListener('change', () => {
    loadPageData(activePage);
  });

  // Refresh button
  document.getElementById('refresh-btn')?.addEventListener('click', () => {
    loadPageData(activePage);
    showToast('Dashboard refreshed');
  });

  // ─── Data Loaders ─────────────────────────────────────────

  async function loadPageData(pageId) {
    const selectedChild = childFilter?.value || null;

    if (pageId === 'overview') {
      await loadOverview(selectedChild);
    } else if (pageId === 'activity') {
      await loadActivities();
    } else if (pageId === 'alerts') {
      await loadAlerts();
    } else if (pageId === 'screentime') {
      await loadScreenTime();
    } else if (pageId === 'websites') {
      await loadWebsites();
    } else if (pageId === 'applications') {
      await loadApplications();
    } else if (pageId === 'reports') {
      await loadReports();
    } else if (pageId === 'devices') {
      await loadDevices();
    } else if (pageId === 'children') {
      await loadChildrenList();
    } else if (pageId === 'settings') {
      await loadSettings();
    }
  }

  // 1. Overview Page
  async function loadOverview(childId) {
    const [summary, children, activities] = await Promise.all([
      API.getSummary(childId),
      API.getChildren(),
      API.getActivities()
    ]);

    // Populate stats cards
    document.getElementById('stat-total').textContent = summary.total_events || 0;
    document.getElementById('stat-visited-dash').textContent = summary.sites_visited || 0;
    document.getElementById('stat-blocked-dash').textContent = summary.sites_blocked || 0;
    document.getElementById('stat-threats').textContent = summary.threats_detected || 0;
    document.getElementById('stat-screentime').textContent = `${Math.round((summary.screen_time_mins || 0) / 60)}h ${(summary.screen_time_mins || 0) % 60}m`;
    document.getElementById('stat-unread-alerts').textContent = summary.unread_alerts || 0;

    // Populate children cards
    const childrenGrid = document.getElementById('children-grid');
    if (childrenGrid && children) {
      childrenGrid.innerHTML = children.map(c => `
        <div class="child-card ${c.id === childId ? 'selected' : ''}" onclick="selectChild('${c.id}')">
          <div class="child-avatar-lg">${c.avatar || '🧒'}</div>
          <div class="child-details">
            <h4>${c.name}</h4>
            <p>Age: ${c.age || 'N/A'} &bull; ${c.device_count || 1} Registered Devices</p>
            <span class="child-status-badge">● Active Protection</span>
          </div>
        </div>
      `).join('');
    }

    // Populate recent events
    const recentList = document.getElementById('recent-events');
    if (recentList && activities) {
      recentList.innerHTML = activities.slice(0, 5).map(renderEventRow).join('');
    }
  }

  // 2. Activity Page
  async function loadActivities() {
    const eventType = document.getElementById('filter-event-type')?.value || '';
    const severity = document.getElementById('filter-severity')?.value || '';

    const list = await API.getActivities({ event_type: eventType, severity });
    const tbody = document.getElementById('activity-tbody');
    if (tbody) {
      tbody.innerHTML = list.map(a => `
        <tr>
          <td>${a.timestamp}</td>
          <td><strong>${formatEventType(a.event_type)}</strong></td>
          <td><code>${a.domain || a.app_name || '-'}</code></td>
          <td>${a.category || '-'}</td>
          <td><span class="badge ${getSeverityBadge(a.severity)}">${a.severity}</span></td>
          <td><span class="badge ${getActionBadge(a.action || a.action_taken)}">${a.action || a.action_taken}</span></td>
        </tr>
      `).join('') || '<tr><td colspan="6" style="text-align:center;">No activity records match filters.</td></tr>';
    }
  }

  document.getElementById('apply-filters')?.addEventListener('click', loadActivities);
  document.getElementById('clear-filters')?.addEventListener('click', () => {
    document.getElementById('filter-event-type').value = '';
    document.getElementById('filter-severity').value = '';
    loadActivities();
  });

  // 3. Alerts Page
  async function loadAlerts() {
    const alerts = await API.getAlerts();
    const container = document.getElementById('alerts-list');
    if (container) {
      container.innerHTML = alerts.map(al => `
        <div class="event-item" style="${al.is_read ? 'opacity: 0.6;' : 'border-left: 3px solid #ef4444;'}">
          <div class="event-badge">${getAlertIcon(al.alert_type)}</div>
          <div class="event-content">
            <div class="event-title">${al.title}</div>
            <div class="event-meta" style="margin-top: 4px;">${al.message}</div>
            <div class="event-meta" style="font-size: 11px; margin-top: 6px;">${al.created_at}</div>
          </div>
          <div>
            ${!al.is_read ? `<button class="btn btn-secondary btn-sm" onclick="markAlertAsRead('${al.id}')">Mark Read</button>` : '<span class="badge badge-grey">Read</span>'}
          </div>
        </div>
      `).join('') || '<div class="loading-placeholder">No alerts recorded. All safe!</div>';
    }
  }

  window.markAlertAsRead = async function(id) {
    await API.markAlertRead(id);
    loadAlerts();
    showToast('Alert marked as resolved');
  };

  document.getElementById('mark-all-read-btn')?.addEventListener('click', async () => {
    const alerts = await API.getAlerts();
    for (const al of alerts) {
      if (!al.is_read) await API.markAlertRead(al.id);
    }
    loadAlerts();
    showToast('All alerts marked as read');
  });

  // 4. Screen Time Page
  async function loadScreenTime() {
    const data = await API.getScreenTimeData();
    const ctx = document.getElementById('screentime-chart');
    if (ctx && window.Chart) {
      if (screentimeChart) screentimeChart.destroy();
      screentimeChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: data.labels,
          datasets: data.datasets.map((ds, idx) => ({
            label: ds.label,
            data: ds.data,
            backgroundColor: idx === 0 ? 'rgba(79, 70, 229, 0.85)' : 'rgba(56, 189, 248, 0.85)',
            borderRadius: 6
          }))
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { labels: { color: '#cbd5e1' } } },
          scales: {
            x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
            y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
          }
        }
      });
    }

    const appCtx = document.getElementById('app-breakdown-chart');
    if (appCtx && window.Chart) {
      if (appBreakdownChart) appBreakdownChart.destroy();
      appBreakdownChart = new Chart(appCtx, {
        type: 'doughnut',
        data: {
          labels: ['Web Browsing', 'Games (Roblox)', 'Productivity & Code', 'Discord/Chat'],
          datasets: [{
            data: [45, 30, 15, 10],
            backgroundColor: ['#38bdf8', '#ef4444', '#10b981', '#a855f7'],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { labels: { color: '#cbd5e1' } } }
        }
      });
    }
  }

  // 5. Websites Policy Page
  async function loadWebsites() {
    const list = await API.getWebsites();
    const tbody = document.getElementById('websites-tbody');
    if (tbody) {
      tbody.innerHTML = list.map(w => `
        <tr>
          <td><code>${w.domain}</code></td>
          <td><span class="badge ${getActionBadge(w.rule_type)}">${w.rule_type}</span></td>
          <td>All Children</td>
          <td>${w.reason || '-'}</td>
          <td>
            <button class="btn btn-danger btn-sm" onclick="removeWebsiteRule('${w.id}')">Delete</button>
          </td>
        </tr>
      `).join('') || '<tr><td colspan="5" style="text-align:center;">No custom website policies configured.</td></tr>';
    }
  }

  window.removeWebsiteRule = async function(id) {
    await API.deleteWebsite(id);
    loadWebsites();
    showToast('Website policy rule removed');
  };

  document.getElementById('add-website-btn')?.addEventListener('click', () => {
    openModal('Add Website Policy Rule', `
      <form id="add-web-form">
        <div class="form-group" style="margin-bottom: 14px;">
          <label style="display:block; font-size: 13px; margin-bottom: 6px;">Domain Name</label>
          <input type="text" id="web-domain" placeholder="example.com" required style="width: 100%; padding: 10px; background: #0c101e; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #fff;">
        </div>
        <div class="form-group" style="margin-bottom: 14px;">
          <label style="display:block; font-size: 13px; margin-bottom: 6px;">Rule Action</label>
          <select id="web-action" class="select-input" style="width: 100%;">
            <option value="BLOCK">BLOCK (Restricted)</option>
            <option value="WARN">WARN (Warning Overlay)</option>
            <option value="ALLOW">ALLOW (Always Safe)</option>
          </select>
        </div>
        <div class="form-group" style="margin-bottom: 20px;">
          <label style="display:block; font-size: 13px; margin-bottom: 6px;">Reason / Category</label>
          <input type="text" id="web-reason" placeholder="e.g. Inappropriate content" style="width: 100%; padding: 10px; background: #0c101e; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #fff;">
        </div>
        <button type="submit" class="btn btn-primary btn-full">Save Policy Rule</button>
      </form>
    `);

    document.getElementById('add-web-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const domain = document.getElementById('web-domain').value.trim();
      const rule_type = document.getElementById('web-action').value;
      const reason = document.getElementById('web-reason').value.trim();
      await API.addWebsite({ domain, rule_type, reason, category: 'custom' });
      closeModal();
      loadWebsites();
      showToast(`Rule saved for ${domain}`);
    });
  });

  // 6. Applications Policy Page
  async function loadApplications() {
    const list = await API.getApplications();
    const tbody = document.getElementById('apps-tbody');
    if (tbody) {
      tbody.innerHTML = list.map(a => `
        <tr>
          <td><code>${a.app_name}</code></td>
          <td><span class="badge ${getActionBadge(a.policy)}">${a.policy}</span></td>
          <td>${a.daily_limit_minutes ? a.daily_limit_minutes + ' mins' : 'Unlimited'}</td>
          <td>All Children</td>
          <td>
            <button class="btn btn-danger btn-sm" onclick="removeAppRule('${a.id}')">Delete</button>
          </td>
        </tr>
      `).join('') || '<tr><td colspan="5" style="text-align:center;">No application restrictions configured.</td></tr>';
    }
  }

  window.removeAppRule = async function(id) {
    await API.deleteApplication(id);
    loadApplications();
    showToast('Application policy deleted');
  };

  document.getElementById('add-app-btn')?.addEventListener('click', () => {
    openModal('Restrict Application on Windows', `
      <form id="add-app-form">
        <div class="form-group" style="margin-bottom: 14px;">
          <label style="display:block; font-size: 13px; margin-bottom: 6px;">Process Executable Name</label>
          <input type="text" id="app-name-input" placeholder="e.g. discord.exe or roblox.exe" required style="width: 100%; padding: 10px; background: #0c101e; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #fff;">
        </div>
        <div class="form-group" style="margin-bottom: 14px;">
          <label style="display:block; font-size: 13px; margin-bottom: 6px;">Policy Type</label>
          <select id="app-policy-input" class="select-input" style="width: 100%;">
            <option value="BLOCK">BLOCK (Halt Execution)</option>
            <option value="LIMITED">LIMITED (Daily Time Limit)</option>
            <option value="ALLOW">ALLOW</option>
          </select>
        </div>
        <div class="form-group" id="limit-mins-group" style="margin-bottom: 20px;">
          <label style="display:block; font-size: 13px; margin-bottom: 6px;">Daily Limit (Minutes)</label>
          <input type="number" id="app-limit-mins" value="60" min="5" max="720" style="width: 100%; padding: 10px; background: #0c101e; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #fff;">
        </div>
        <button type="submit" class="btn btn-primary btn-full">Enforce Application Rule</button>
      </form>
    `);

    document.getElementById('add-app-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const app_name = document.getElementById('app-name-input').value.trim();
      const policy = document.getElementById('app-policy-input').value;
      const daily_limit_minutes = parseInt(document.getElementById('app-limit-mins').value) || 0;
      await API.addApplication({ app_name, policy, daily_limit_minutes });
      closeModal();
      loadApplications();
      showToast(`Policy configured for ${app_name}`);
    });
  });

  // 7. Devices Page
  async function loadDevices() {
    const devices = await API.getDevices();
    const container = document.getElementById('devices-grid');
    if (container) {
      container.innerHTML = devices.map(d => `
        <div class="child-card" style="cursor: default;">
          <div class="child-avatar-lg">${d.type === 'DESKTOP' ? '🖥️' : (d.type === 'TABLET' ? '📱' : '💻')}</div>
          <div class="child-details" style="flex:1;">
            <h4>${d.name}</h4>
            <p>Assigned to: ${d.child_name || 'Child'} &bull; OS: ${d.os || 'Windows'}</p>
            <span class="child-status-badge" style="margin-top: 6px;">● Last Seen: ${d.last_seen || 'Active'}</span>
          </div>
        </div>
      `).join('');
    }
  }

  // 8. Children Page
  async function loadChildrenList() {
    const children = await API.getChildren();
    const container = document.getElementById('children-manage-grid');
    if (container) {
      container.innerHTML = children.map(c => `
        <div class="child-card" style="cursor: default;">
          <div class="child-avatar-lg">${c.avatar || '🧒'}</div>
          <div class="child-details" style="flex:1;">
            <h4>${c.name}</h4>
            <p>Age: ${c.age || 'N/A'} &bull; ${c.device_count || 1} Connected Devices</p>
            <span class="child-status-badge" style="margin-top: 6px;">● Protection Active</span>
          </div>
        </div>
      `).join('');
    }
  }

  // 9. Reports Page
  async function loadReports() {
    const container = document.getElementById('reports-list');
    if (container) {
      container.innerHTML = `
        <div class="table-card" style="padding: 24px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <h4>Weekly Family Safety Audit &bull; Alex & Emma</h4>
            <span class="badge badge-allow">Score: 94/100 Safe</span>
          </div>
          <p style="color: var(--text-muted); font-size: 13px; line-height: 1.6;">
            Over the past 7 days, DigitalGuard intercepted 4 malicious / phishing attempts and blurred 2 flagged chat messages.
            Alex spent 14.5 hours online (42% Educational, 35% Gaming, 15% Social).
          </p>
          <div style="margin-top: 20px; display:flex; gap:10px;">
            <button class="btn btn-secondary btn-sm" onclick="alert('Exporting PDF audit summary...')">📥 Download PDF Report</button>
          </div>
        </div>
      `;
    }
  }

  // 10. Settings Page
  async function loadSettings() {
    const aiHealth = await API.checkAIHealth();
    const statusBadge = document.getElementById('ai-status-badge');
    const modeBadge = document.getElementById('ai-mode-badge');

    if (statusBadge) {
      statusBadge.textContent = aiHealth.status === 'ok' ? 'ONLINE (127.0.0.1:8765)' : 'OFFLINE';
      statusBadge.className = aiHealth.status === 'ok' ? 'badge badge-allow' : 'badge badge-block';
    }
    if (modeBadge) {
      modeBadge.textContent = aiHealth.inference_mode || 'MOCK';
      modeBadge.className = aiHealth.inference_mode === 'REAL' ? 'badge badge-allow' : 'badge badge-warn';
    }

    loadPasskeys();
  }

  async function loadPasskeys() {
    const listEl = document.getElementById('passkeys-list');
    if (!listEl) return;
    try {
      const passkeys = await API.getPasskeys();
      if (!passkeys.length) {
        listEl.innerHTML = '<div class="empty-state-sm">No passkeys registered yet. Click "+ Register Passkey" to add one.</div>';
        return;
      }
      listEl.innerHTML = passkeys.map(pk => `
        <div class="setting-info-row flex-between" style="padding: 8px 0; border-bottom: 1px solid var(--color-border,#334155)">
          <div>
            <strong>🔑 ${pk.display_name || 'Passkey'}</strong>
            <div style="font-size: 0.8rem; color: var(--color-text-muted,#94a3b8)">Added: ${new Date(pk.created_at).toLocaleDateString()}</div>
          </div>
          <button class="btn btn-secondary btn-sm delete-passkey-btn" data-id="${pk.id}">Delete</button>
        </div>
      `).join('');

      listEl.querySelectorAll('.delete-passkey-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
          if (confirm('Are you sure you want to remove this passkey?')) {
            await API.deletePasskey(btn.dataset.id);
            showToast('Passkey deleted');
            loadPasskeys();
          }
        });
      });
    } catch {
      listEl.innerHTML = '<div class="empty-state-sm">Failed to load passkeys.</div>';
    }
  }

  // ── WebAuthn / Passkey Helpers ─────────────────────────────────────
  function bufferToBase64URL(buffer) {
    const bytes = new Uint8Array(buffer);
    let string = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      string += String.fromCharCode(bytes[i]);
    }
    return btoa(string).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  }

  function base64URLToBuffer(base64url) {
    let base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    while (base64.length % 4) base64 += '=';
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes.buffer;
  }

  // Passkey Login Handler
  document.getElementById('passkey-login-btn')?.addEventListener('click', async () => {
    const emailInput = document.getElementById('login-email');
    const email = (emailInput?.value || '').trim();
    if (!email) {
      showToast('Please enter your email address first.', 'warn');
      emailInput?.focus();
      return;
    }

    if (!window.PublicKeyCredential) {
      showToast('WebAuthn / Passkeys are not supported in this browser.', 'error');
      return;
    }

    try {
      showToast('Requesting passkey challenge...');
      const optRes = await API.webauthnAuthOptions(email);
      const optionsJSON = JSON.parse(optRes.data);

      optionsJSON.challenge = base64URLToBuffer(optionsJSON.challenge);
      if (optionsJSON.allowCredentials) {
        optionsJSON.allowCredentials = optionsJSON.allowCredentials.map(c => ({
          ...c,
          id: base64URLToBuffer(c.id)
        }));
      }

      showToast('Touch sensor or insert security key...');
      const credential = await navigator.credentials.get({ publicKey: optionsJSON });

      const credentialJSON = {
        id: credential.id,
        rawId: bufferToBase64URL(credential.rawId),
        type: credential.type,
        response: {
          authenticatorData: bufferToBase64URL(credential.response.authenticatorData),
          clientDataJSON: bufferToBase64URL(credential.response.clientDataJSON),
          signature: bufferToBase64URL(credential.response.signature),
          userHandle: credential.response.userHandle ? bufferToBase64URL(credential.response.userHandle) : null,
        }
      };

      const verifyRes = await API.webauthnAuthVerify(credentialJSON);
      const user = verifyRes.data.user;
      document.getElementById('user-name').textContent = user.display_name || user.email;
      showScreen(appScreen);
      navigateTo('overview');
      startPolling();
      showToast(`Welcome back, ${user.display_name || user.email}! Signed in via Passkey.`, 'success');
    } catch (e) {
      console.error('[WebAuthn Auth Error]', e);
      showToast(`Passkey login failed: ${e.message}`, 'error');
    }
  });

  // Passkey Register Handler
  document.getElementById('register-passkey-btn')?.addEventListener('click', async () => {
    if (!window.PublicKeyCredential) {
      showToast('WebAuthn / Passkeys are not supported in this browser.', 'error');
      return;
    }

    const passkeyName = prompt('Enter a label for this passkey (e.g., MacBook Touch ID, YubiKey):', 'My Security Key');
    if (!passkeyName) return;

    try {
      showToast('Generating passkey registration challenge...');
      const optRes = await API.webauthnRegisterOptions();
      const optionsJSON = JSON.parse(optRes.data);

      optionsJSON.challenge = base64URLToBuffer(optionsJSON.challenge);
      optionsJSON.user.id = base64URLToBuffer(optionsJSON.user.id);
      if (optionsJSON.excludeCredentials) {
        optionsJSON.excludeCredentials = optionsJSON.excludeCredentials.map(c => ({
          ...c,
          id: base64URLToBuffer(c.id)
        }));
      }

      showToast('Follow browser prompt to register passkey...');
      const credential = await navigator.credentials.create({ publicKey: optionsJSON });

      const credentialJSON = {
        id: credential.id,
        rawId: bufferToBase64URL(credential.rawId),
        type: credential.type,
        credential_name: passkeyName,
        response: {
          attestationObject: bufferToBase64URL(credential.response.attestationObject),
          clientDataJSON: bufferToBase64URL(credential.response.clientDataJSON),
          transports: credential.response.getTransports ? credential.response.getTransports() : []
        }
      };

      await API.webauthnRegisterVerify(credentialJSON);
      showToast('Passkey registered successfully!', 'success');
      loadPasskeys();
    } catch (e) {
      console.error('[WebAuthn Register Error]', e);
      showToast(`Passkey registration failed: ${e.message}`, 'error');
    }
  });

  document.getElementById('save-account-btn')?.addEventListener('click', () => {
    showToast('Account details updated');
  });
  document.getElementById('save-prefs-btn')?.addEventListener('click', () => {
    showToast('Notification preferences saved');
  });

  // Modal helpers
  function openModal(title, htmlBody) {
    const overlay = document.getElementById('modal-overlay');
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = htmlBody;
    overlay.style.display = 'flex';
  }

  function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
  }

  document.getElementById('modal-close')?.addEventListener('click', closeModal);

  // Render Helpers
  function renderEventRow(a) {
    return `
      <div class="event-item">
        <div class="event-badge">${getEventIcon(a.event_type)}</div>
        <div class="event-content">
          <div class="event-title">${formatEventType(a.event_type)} &mdash; <code>${a.domain || a.app_name || ''}</code></div>
          <div class="event-meta">Action: <strong>${a.action || a.action_taken}</strong> &bull; ${a.timestamp}</div>
        </div>
        <div>
          <span class="badge ${getSeverityBadge(a.severity)}">${a.severity}</span>
        </div>
      </div>
    `;
  }

  function getEventIcon(type) {
    if (type?.includes('PHISH')) return '🎣';
    if (type?.includes('BULLY')) return '💬';
    if (type?.includes('APP')) return '📱';
    if (type?.includes('BLOCK')) return '🚫';
    if (type?.includes('WARN')) return '⚠️';
    return '🌐';
  }

  function getAlertIcon(type) {
    if (type === 'phishing') return '🎣';
    if (type === 'cyberbullying') return '💬';
    if (type === 'app_blocked') return '📱';
    return '🔔';
  }

  function formatEventType(type) {
    return (type || '').replace(/_/g, ' ');
  }

  function getSeverityBadge(sev) {
    if (sev === 'CRITICAL') return 'badge-critical';
    if (sev === 'HIGH') return 'badge-block';
    if (sev === 'MEDIUM') return 'badge-warn';
    return 'badge-allow';
  }

  function getActionBadge(act) {
    if (act === 'BLOCK') return 'badge-block';
    if (act === 'WARN') return 'badge-warn';
    if (act === 'LIMITED') return 'badge-warn';
    return 'badge-allow';
  }

  // Polling loop
  function startPolling() {
    stopPolling();
    pollInterval = setInterval(() => {
      if (appScreen.classList.contains('active')) {
        loadPageData(activePage);
      }
    }, 5000);
  }

  function stopPolling() {
    if (pollInterval) clearInterval(pollInterval);
  }

  // Child selection helper
  window.selectChild = function(childId) {
    if (childFilter) {
      childFilter.value = childId;
      loadOverview(childId);
    }
  };

  // Auto-load if in demo mode
  if (API.isDemoMode()) {
    showScreen(appScreen);
    navigateTo('overview');
  }
});
