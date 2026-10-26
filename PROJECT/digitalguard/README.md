# DigitalGuard 🛡️
### *A Hybrid System-Level Parental Control and Browser Security Suite (Windows Native)*

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Django 4.2](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-teal.svg)](https://fastapi.tiangolo.com/)
[![Windows Native](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6.svg)](https://www.microsoft.com/windows)
[![Privacy First](https://img.shields.io/badge/Privacy-On--Device%20AI-purple.svg)](#privacy-architecture)

DigitalGuard is a privacy-first hybrid parental control and cybersecurity platform designed to protect children on the modern internet. It couples system-level Windows desktop monitoring with browser security extensions and local on-device AI inference.

---

## 🌟 Key Highlights

- **🔒 Zero Content Leakage**: Raw webpage content, search queries, and chat messages **never leave the child's machine**. All semantic text analysis runs on the local device via an isolated AI microservice (`127.0.0.1:8765`).
- **🪟 Windows Native Desktop Agent**: Deep process and foreground window monitoring via Windows APIs (`user32.dll`), idle detection, screen-time quota enforcement, and executable blocking.
- **🌐 Chromium Browser Extension (MV3)**: Real-time URL threat classification, intelligent text blurring for cyberbullying, download screening for malicious binaries, and custom blocked pages.
- **📊 Modern Parental Dashboard**: Glassmorphic dark-mode web console featuring 10 dedicated management modules, Chart.js telemetry, and an instant interactive Demo Mode.
- **📱 Flutter Mobile Companion**: Scaffolded mobile client for real-time push alerts and remote policy adjustment on the go.

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────┐
│               CHILD'S WINDOWS COMPUTER                 │
│                                                        │
│  [ Chrome / Edge ] ──(MV3)──► [ Native Messaging Host ]│
│         ▲                               │              │
│         │ Overlay & Blur                │ JSON / stdio │
│         │                               ▼              │
│  [ Windows Desktop Agent ] ──► [ Local AI Engine ]     │
│   (App Monitor, Limits)        (FastAPI:8765 Loopback) │
└─────────────────────────────────────────┬──────────────┘
                                          │ Metadata Only
                                          ▼
┌────────────────────────────────────────────────────────┐
│               PARENT CONTROL & CLOUD                   │
│                                                        │
│       [ Django REST API & PostgreSQL / SQLite ]        │
│              ▲                         ▲               │
│              │                         │               │
│   [ Glassmorphic Web UI ]     [ Flutter Mobile App ]   │
└────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
digitalguard/
├── backend/                  # Django REST API service
│   ├── accounts/             # Parents, children, devices, credentials
│   ├── monitoring/           # Activity logs, threat events, screentime
│   ├── policies/             # Website and Windows application policies
│   ├── alerts/               # Parental notifications
│   ├── reports/              # Summary audits
│   ├── seed_data.py          # Demo dataset generator
│   └── manage.py
├── desktop-agent/            # Windows Native Desktop Agent
│   ├── monitoring/           # user32.dll foreground & idle detection
│   ├── enforcement/          # App blocking & bedtime screen-time quotas
│   ├── ipc/                  # Chrome/Edge Native Messaging & Local Bridge
│   ├── register_host.py      # Windows Registry installer
│   ├── install_host_windows.bat
│   └── main.py               # Main agent service loop
├── ai-engine/                # On-Device AI Content Analyzer
│   ├── models/               # Heuristic URL analyzer, Mock & ONNX models
│   ├── analyzer.py           # Unified safety pipeline
│   └── main.py               # FastAPI server (127.0.0.1:8765)
├── browser-extension/        # Manifest V3 Chrome / Edge Extension
│   ├── background/           # Service worker (navigation & download guards)
│   ├── content/              # DOM extraction, text blurring, blocked pages
│   ├── popup/                # Extension status popup
│   ├── options/              # Settings & device token configuration
│   └── assets/icons/         # Extension shield icons
├── dashboard/                # Parental Web Dashboard
│   ├── index.html            # 10-module single-page interface
│   ├── css/main.css          # Glassmorphic dark design system
│   └── js/                   # API integration & reactive controller
├── mobile/                   # Flutter Mobile Companion
│   └── digitalguard_mobile/  # Flutter app scaffold
├── tests/                    # Automated Test Suite
│   ├── backend/              # Django models & endpoint tests
│   ├── ai_engine/            # AI pipeline unit tests
│   └── desktop_agent/        # Windows monitor & policy tests
└── docs/                     # Technical Documentation
```

---

## 🚀 Quickstart Guide

### 1. Requirements & Setup
Ensure you have Python 3.10+ installed. Install dependencies:
```cmd
pip install -r requirements.txt
```

### 2. Initialize Database & Seed Demo Data
```cmd
cd backend
python manage.py migrate
python seed_data.py
```
*Pre-configured Demo Credentials:*
- **Email**: `parent@digitalguard.local`
- **Password**: `Password123!`
- **Device Token**: `550e8400-e29b-41d4-a716-446655440000`

### 3. Launch Services

#### A. Run Django Backend:
```cmd
cd backend
python manage.py runserver 127.0.0.1:8000
```

#### B. Run Local AI Engine:
```cmd
cd ai-engine
python -m uvicorn main:app --host 127.0.0.1 --port 8765
```

#### C. Run Windows Desktop Agent:
```cmd
cd desktop-agent
install_host_windows.bat    :: Registers Native Messaging Host in Windows Registry
python main.py
```

#### D. Open Parental Dashboard:
Open `dashboard/index.html` in any modern web browser or serve it locally. Click **"🎭 Load Demo Data"** for an instant hands-on preview!

#### E. Load Browser Extension:
1. Open `chrome://extensions` (or `edge://extensions`).
2. Enable **Developer mode**.
3. Click **Load unpacked** and select the `browser-extension/` directory.

---

## 🧪 Testing

Run test suites using pytest:
```cmd
pytest tests/backend/ -v
pytest tests/ai_engine/ -v
pytest tests/desktop_agent/ -v
```

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for details.
