# DigitalGuard System Architecture

DigitalGuard is a hybrid, privacy-first parental control and browser security suite engineered for modern desktop (Windows) and multi-device households.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CHILD'S WINDOWS DEVICE                            │
│                                                                             │
│  ┌───────────────────────┐             ┌─────────────────────────────────┐  │
│  │   Browser Extension   │             │       Windows Desktop Agent     │  │
│  │     (Chrome / Edge)   │             │   (Foreground, Idle, Limits)    │  │
│  └───────────┬───────────┘             └────────────────┬────────────────┘  │
│              │ Native Messaging (stdio)                 │                   │
│              ▼                                          │                   │
│  ┌───────────────────────┐                              │                   │
│  │  NativeMessagingHost  │◄─────────────────────────────┘                   │
│  └───────────┬───────────┘                                                  │
│              │ HTTP (Loopback 127.0.0.1:8765)                               │
│              ▼                                                              │
│  ┌───────────────────────────────────────────────────────┐                  │
│  │              Local On-Device AI Engine                │                  │
│  │          (FastAPI, ONNX / Mock Heuristics)            │                  │
│  │       Raw child content NEVER leaves device!          │                  │
│  └───────────────────────────┬───────────────────────────┘                  │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               │
                               │ Telemetry & Metadata Only (Device Token Auth)
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PARENT SERVER & CLOUD                              │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                       Django REST Backend API                         │  │
│  │            Auth, Policies, Activity Logs, Alerts, Reports             │  │
│  └───────────┬───────────────────────────────────────────┬───────────────┘  │
│              │                                           │                  │
│              ▼                                           ▼                  │
│  ┌───────────────────────┐                   ┌───────────────────────────┐  │
│  │   Parent Web Portal   │                   │   Flutter Companion App   │  │
│  │ (Glassmorphic UI/UX)  │                   │  (iOS / Android Alerts)   │  │
│  └───────────────────────┘                   └───────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Privacy Invariant
1. **Zero Content Leaks**: Web page bodies, chat messages, and search queries are processed locally by the on-device AI Engine.
2. **Metadata-Only Egress**: The backend receives strictly:
   - Event classifications (e.g. `PHISHING_DETECTED`, `CYBERBULLYING_DETECTED`)
   - Severity level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
   - Domain or application name (`discord.exe`, `bank-fake.xyz`)
   - Anonymized SHA-256 content hashes for deduplication
   - Timestamp and device ID

## Component Summary
- **Desktop Agent (Windows)**: Background service monitoring foreground applications, window titles, user idle time (`user32.dll`), enforcing process termination or window minimization, and accumulating screen time quotas.
- **Browser Extension (MV3)**: Content scripts that blur abusive language or render block overlays, service worker checking navigation against backend policies and dispatching text to the AI engine.
- **AI Engine (FastAPI)**: Standalone microservice running on `127.0.0.1:8765` evaluating phishing URLs, cyberbullying, grooming risk, and toxicity.
- **Django Backend**: Central persistence, parent JWT authentication, device token validation, policy enforcement rules, and reporting.
- **Parent Dashboard**: Glassmorphic web console featuring 10 operational sections, Chart.js telemetry, real-time alerts, and policy management.
