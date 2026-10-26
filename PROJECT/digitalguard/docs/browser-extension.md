# Browser Extension Guide (Manifest V3)

The DigitalGuard Browser Extension operates in Chromium browsers (Google Chrome, Microsoft Edge, Brave) providing real-time URL classification, download inspection, and content protection.

## Core Features
1. **Navigation Monitor**:
   - `chrome.webNavigation.onCommitted` evaluates every HTTP/HTTPS URL against the local policy cache (5-minute TTL) and the backend `/api/browser/check-url/`.
   - If prohibited, the user is redirected to `content/blocked.html` with category and reason details.
   - If warnings apply, a non-intrusive warning header is injected.
2. **On-Page Content Analysis**:
   - `content/content_script.js` safely extracts visible body text (excluding password fields, forms, and inputs).
   - If harmful or abusive language is detected, an intelligent blur filter is applied to shield the child while alerting the parent.
3. **Download Guard**:
   - `chrome.downloads.onCreated` detects dangerous executable extensions (`.exe`, `.msi`, `.bat`, `.ps1`, `.vbs`) and alerts the parental dashboard.
4. **Popup & Settings UI**:
   - `popup/popup.html`: Real-time shield toggle and domain trust assessment.
   - `options/options.html`: Device pairing, sensitivity sliders, and connection tester.

## Loading the Extension in Developer Mode
1. Open `chrome://extensions` (or `edge://extensions`) in your browser.
2. Toggle **Developer mode** (top right).
3. Click **Load unpacked**.
4. Select the `browser-extension` folder inside this repository.
5. Click extension options to pair your child's device token.
