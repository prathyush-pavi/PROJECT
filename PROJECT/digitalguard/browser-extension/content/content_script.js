/**
 * DigitalGuard — Content Script
 *
 * Runs in the context of every web page.
 *
 * Responsibilities:
 * - Receive protection verdicts from the service worker
 * - Apply blur/warn overlays based on verdict
 * - Extract visible text for AI analysis (no passwords, no form data)
 * - Communicate with the background service worker
 *
 * PRIVACY: This script NEVER reads password fields, payment info,
 * or other sensitive form inputs. Only visible body text is extracted.
 */

'use strict';

(function () {
  // ─── State ─────────────────────────────────────────────────────────────────
  let warningOverlayShown = false;
  let blurApplied = false;

  // ─── Safe text extraction ───────────────────────────────────────────────────
  /**
   * Extract visible text from the page body.
   * Explicitly avoids: input fields, textareas, password fields, forms.
   * Returns up to 5000 characters.
   */
  function extractVisibleText() {
    const EXCLUDED_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'INPUT', 'TEXTAREA', 'SELECT', 'FORM']);
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: (node) => {
          // Skip excluded tag types
          let parent = node.parentElement;
          while (parent) {
            if (EXCLUDED_TAGS.has(parent.tagName)) return NodeFilter.FILTER_REJECT;
            if (parent.getAttribute('type') === 'password') return NodeFilter.FILTER_REJECT;
            parent = parent.parentElement;
          }
          // Skip invisible nodes
          const style = window.getComputedStyle(node.parentElement || document.body);
          if (style.display === 'none' || style.visibility === 'hidden') return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      }
    );

    const textParts = [];
    let totalLength = 0;
    let node;

    while ((node = walker.nextNode()) && totalLength < 5000) {
      const text = node.textContent.trim();
      if (text.length > 3) {
        textParts.push(text);
        totalLength += text.length;
      }
    }

    return textParts.join(' ').substring(0, 5000);
  }

  // ─── Overlay/enforcement UI ─────────────────────────────────────────────────
  /**
   * Show a warning banner at the top of the page.
   * Does not block navigation — parent is informed via activity log.
   */
  function showWarningBanner(category, riskScore, inferenceMode) {
    if (warningOverlayShown) return;
    warningOverlayShown = true;

    const banner = document.createElement('div');
    banner.id = 'dg-warning-banner';
    banner.innerHTML = `
      <div style="
        position: fixed; top: 0; left: 0; right: 0; z-index: 2147483647;
        background: linear-gradient(135deg, #ff6b35, #f7c948);
        color: #1a1a2e; padding: 12px 20px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 14px; font-weight: 600;
        display: flex; align-items: center; justify-content: space-between;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      ">
        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 20px;">⚠️</span>
          <div>
            <strong>DigitalGuard Warning</strong><br>
            <span style="font-weight: 400; font-size: 12px;">
              This page has been flagged as <strong>${category}</strong>
              ${inferenceMode === 'MOCK' ? ' (Development mode — not real AI)' : ''}.
              Risk score: ${Math.round(riskScore * 100)}%
            </span>
          </div>
        </div>
        <button onclick="this.parentElement.parentElement.remove()" style="
          background: rgba(0,0,0,0.2); border: none; color: #1a1a2e;
          padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 13px;
        ">✕ Dismiss</button>
      </div>
    `;
    document.body.prepend(banner);

    // Auto-dismiss after 10 seconds
    setTimeout(() => {
      if (banner.parentElement) banner.remove();
    }, 10000);
  }

  /**
   * Apply a blur filter to the page content.
   * Used for adult/explicit content warnings.
   */
  function applyBlurFilter(category) {
    if (blurApplied) return;
    blurApplied = true;

    // Blur the main content area
    document.body.style.filter = 'blur(8px)';
    document.body.style.pointerEvents = 'none';

    // Show an unblur overlay
    const overlay = document.createElement('div');
    overlay.id = 'dg-blur-overlay';
    overlay.innerHTML = `
      <div style="
        position: fixed; inset: 0; z-index: 2147483647;
        background: rgba(15, 15, 40, 0.9);
        display: flex; align-items: center; justify-content: center;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      ">
        <div style="
          background: linear-gradient(135deg, #1a1a3e, #2d1b69);
          border: 2px solid rgba(255,107,53,0.5);
          border-radius: 20px; padding: 40px; max-width: 420px;
          text-align: center; color: #fff;
          box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        ">
          <div style="font-size: 48px; margin-bottom: 16px;">🛡️</div>
          <h2 style="margin: 0 0 12px; font-size: 22px;">Content Blocked</h2>
          <p style="color: rgba(255,255,255,0.7); font-size: 14px; line-height: 1.6; margin: 0 0 20px;">
            DigitalGuard has detected <strong>${category}</strong> content on this page.
            This content has been hidden for your protection.
          </p>
          <p style="color: rgba(255,255,255,0.5); font-size: 12px;">
            Your parent has been notified. This activity has been logged.
          </p>
        </div>
      </div>
    `;
    document.body.style.overflow = 'hidden';
    document.documentElement.appendChild(overlay);
  }

  // ─── Message handling ────────────────────────────────────────────────────────
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'PROTECTION_VERDICT') {
      const { action, category, riskScore, inferenceMode } = message;

      if (action === 'WARN') {
        showWarningBanner(category, riskScore, inferenceMode);
      } else if (action === 'BLUR') {
        showWarningBanner(category, riskScore, inferenceMode);
        applyBlurFilter(category);
      }
      // BLOCK is handled at navigation level by service worker (redirect to block page)
      // ALLOW requires no action
    }
  });

  // ─── Text analysis trigger ────────────────────────────────────────────────────
  /**
   * Send extracted page text to the background for AI analysis.
   * Only triggered on pages that haven't already been blocked.
   * Throttled — only runs once per page load.
   */
  let textAnalysisTriggered = false;

  function triggerTextAnalysis() {
    if (textAnalysisTriggered) return;
    textAnalysisTriggered = true;

    const text = extractVisibleText();
    if (!text || text.length < 50) return;  // Not enough text to analyze

    chrome.runtime.sendMessage(
      {
        type: 'CONTENT_ANALYSIS_REQUEST',
        text,
        context: 'webpage',
      },
      (result) => {
        if (chrome.runtime.lastError) return;
        if (!result) return;

        const action = result.recommended_action || result.action || 'ALLOW';
        const category = result.category || 'unknown';
        const riskScore = result.risk_score || 0.0;
        const inferenceMode = result.inference_mode || 'UNKNOWN';

        if (action === 'WARN') {
          showWarningBanner(category, riskScore, inferenceMode);
        } else if (action === 'BLUR') {
          applyBlurFilter(category);
        }
        // BLOCK: handled by service worker after receiving content analysis result
      }
    );
  }

  // Trigger text analysis after page has loaded
  if (document.readyState === 'complete') {
    setTimeout(triggerTextAnalysis, 1500);
  } else {
    window.addEventListener('load', () => setTimeout(triggerTextAnalysis, 1500));
  }

  // ─── Image scanning ──────────────────────────────────────────────────────────
  /**
   * Collect significant images on the page and send to background for
   * AI content classification.
   *
   * Only processes images >= 80x80px (skips icons, avatars, tracking pixels).
   * Applies individual blur to flagged images without hiding the whole page.
   *
   * PRIVACY: Only the image SRC URL is sent — no pixel data is extracted here.
   */
  let imageScanTriggered = false;

  // Track which image URLs we've already checked to avoid duplicate requests
  const checkedImageUrls = new Set();

  function applyImageBlur(imgElement, category, riskScore) {
    if (imgElement.dataset.dgBlurred) return;
    imgElement.dataset.dgBlurred = 'true';

    const wrapper = document.createElement('div');
    wrapper.style.cssText = `
      position: relative; display: inline-block;
      width: ${imgElement.width}px; height: ${imgElement.height}px;
    `;

    const overlay = document.createElement('div');
    overlay.style.cssText = `
      position: absolute; inset: 0; z-index: 9999;
      background: rgba(15,15,40,0.85);
      display: flex; align-items: center; justify-content: center;
      border-radius: 4px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    `;
    overlay.innerHTML = `
      <div style="text-align:center; color:#fff; padding:8px;">
        <div style="font-size:22px;">🛡️</div>
        <div style="font-size:11px; margin-top:4px; opacity:0.85;">
          Content hidden<br><span style="opacity:0.6">${category}</span>
        </div>
      </div>
    `;

    imgElement.style.filter = 'blur(16px)';
    imgElement.style.pointerEvents = 'none';

    imgElement.parentNode.insertBefore(wrapper, imgElement);
    wrapper.appendChild(imgElement);
    wrapper.appendChild(overlay);
  }

  function scanPageImages() {
    if (imageScanTriggered) return;
    imageScanTriggered = true;

    const images = Array.from(document.querySelectorAll('img[src]'))
      .filter(img => {
        const src = img.src;
        // Skip data URIs (too large), extension resources, and tiny images
        if (!src || src.startsWith('data:') || src.startsWith('chrome-extension://')) return false;
        if (img.naturalWidth < 80 || img.naturalHeight < 80) return false;
        if (img.width < 80 || img.height < 80) return false;
        if (checkedImageUrls.has(src)) return false;
        return true;
      });

    if (images.length === 0) return;
    console.debug(`[DigitalGuard] Image scan: ${images.length} significant image(s) found.`);

    // Process in batches to avoid flooding the background with too many requests
    const BATCH_SIZE = 5;
    let index = 0;

    function processBatch() {
      const batch = images.slice(index, index + BATCH_SIZE);
      index += BATCH_SIZE;

      batch.forEach(img => {
        const imageUrl = img.src;
        checkedImageUrls.add(imageUrl);

        chrome.runtime.sendMessage(
          {
            type: 'CONTENT_IMAGE_SCAN_REQUEST',
            imageUrl,
          },
          (result) => {
            if (chrome.runtime.lastError || !result) return;

            const action = result.recommended_action || result.action || 'ALLOW';
            const category = result.category || 'unknown';
            const riskScore = result.risk_score || 0.0;

            if (action === 'BLUR' || action === 'BLOCK') {
              // Re-query the DOM to find the image element (it may have been reused/moved)
              const liveImg = document.querySelector(`img[src="${CSS.escape(imageUrl)}"]`);
              if (liveImg) {
                applyImageBlur(liveImg, category, riskScore);
              }
              console.warn(`[DigitalGuard] Image flagged as ${category} (score=${riskScore.toFixed(2)}, action=${action})`);
            }
          }
        );
      });

      // Schedule next batch if there are more images
      if (index < images.length) {
        setTimeout(processBatch, 1000);
      }
    }

    processBatch();
  }

  // Trigger image scan 3.5 seconds after load (after text analysis has run)
  if (document.readyState === 'complete') {
    setTimeout(scanPageImages, 3500);
  } else {
    window.addEventListener('load', () => setTimeout(scanPageImages, 3500));
  }

})();
