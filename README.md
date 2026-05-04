

# 🛡️ EdgeGuard

**Edge IoT Security Monitor — Local-First, Privacy-Focused**

Real-time camera monitoring, motion detection, and alerting  
designed for local deployments with optional remote notifications.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Why EdgeGuard?

Most security systems require cloud subscriptions, send your footage to third-party servers, and introduce latency. EdgeGuard runs **entirely on your hardware** — your camera feed never leaves your machine unless you explicitly configure remote alerts.

- **No cloud dependency** — processes everything locally at the edge
- **Low latency** — motion detection and streaming happen on-device
- **Modular** — swap out components without rewriting the pipeline
- **Lightweight** — minimal dependencies, works on modest hardware

---

## Features

| Feature | Details |
|---|---|
| 📹 Live Streaming | MJPEG stream + WebRTC with audio |
| 🧠 Motion Detection | Configurable sensitivity, automatic event recording |
| 🔐 Local Auth | Tkinter-based authentication prompt before access |
| 📲 Telegram Alerts | Snapshots and video clips sent on motion events |
| 🌐 Web Dashboard | Browser-based monitoring and system control |
| 📁 Media Storage | Auto-organized snapshots and video recordings |

---

## Architecture

```
[ Camera ]
     │
     ▼
[ Camera Thread ]          ← Shared frame buffer
     │
     ▼
[ Motion Detection ]  ───► [ images/ ]  [ videos/ ]
     │
     ▼
[ FastAPI Server ]
  ├── GET  /          → Dashboard UI
  ├── GET  /video     → MJPEG stream
  ├── POST /offer     → WebRTC signaling
  ├── GET  /status    → System status
  ├── GET  /on|/off   → Enable/disable detection
  ├── GET  /api/images|/api/videos
  ├── GET  /logs
  └── WS   /ws        → Heartbeat
     │
     ▼
[ Browser Dashboard ]
     │
     ▼ (on motion)
[ Telegram Bot ]
```

---

## Project Structure

```
edgeguard/
├── server.py                 # FastAPI backend — APIs and streaming
├── webrtc.py                 # WebRTC audio/video track (aiortc)
├── dashboard.html            # Frontend UI
│
├── camera/
│   ├── camera_thread.py      # Shared camera reader (frame buffer)
│   ├── motion_detection.py   # Motion pipeline, alerts, recording
│   └── auth_ui.py            # Tkinter local auth prompt
│
├── images/                   # Motion event snapshots
├── videos/                   # Recorded motion clips
├── logs/activity.txt         # Event log
└── alarm.mp3                 # Alert sound
```

---

## Requirements

- Python 3.9+
- A webcam (default device index: `0`)
- macOS, Linux, or Windows

---

## Installation

```bash
git clone <repo-url>
cd edgeguard

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

---

## Running EdgeGuard

EdgeGuard has two independent processes. Open two terminal tabs and run them in parallel.

**1. Start the backend server**

```bash
python -m uvicorn server:app --host 0.0.0.0 --port 9090
```

**2. Start the motion detection engine**

```bash
python camera/motion_detection.py
```

**3. Open the dashboard**

Navigate to [http://127.0.0.1:9090](http://127.0.0.1:9090) in your browser.

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Dashboard UI |
| `GET` | `/video` | MJPEG live stream |
| `POST` | `/offer` | WebRTC signaling |
| `GET` | `/status` | System status |
| `GET` | `/on` | Enable motion detection |
| `GET` | `/off` | Disable motion detection |

### Media

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/images` | List captured snapshots |
| `GET` | `/api/videos` | List recorded clips |
| `GET` | `/image/{name}` | Fetch a snapshot |
| `GET` | `/video_file/{name}` | Fetch a recording |

### Logs & Realtime

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/logs` | Activity log |
| `WS` | `/ws` | WebSocket heartbeat |

---

## Configuration

### Telegram Alerts

Store credentials in environment variables — never hardcode them.

```bash
export TELEGRAM_TOKEN=your_bot_token_here
export TELEGRAM_CHAT_ID=your_chat_id_here
```

### WebRTC Audio (macOS)

```bash
AUDIO_SOURCE=default
AUDIO_FORMAT=avfoundation
AUDIO_DEVICE=optional
```

### Storage Paths

| Path | Contents |
|---|---|
| `images/` | Motion event snapshots |
| `videos/` | Recorded motion clips |
| `logs/activity.txt` | Event log |

---

## Security

> ⚠️ EdgeGuard is designed for local network use. Before exposing it to the internet, apply the following hardening steps.

- **Secrets** — Move all tokens and credentials to environment variables (see Configuration above)
- **HTTPS** — Put EdgeGuard behind a reverse proxy (e.g., Nginx) with a TLS certificate
- **API Auth** — Add JWT-based authentication to protect API endpoints
- **Media Encryption** — Optionally encrypt stored snapshots and videos at rest

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Camera not opening | Try device index `1`, `2`, etc. instead of `0` |
| No stream at `/video` | Confirm the FastAPI server is running on port 9090 |
| WebRTC not connecting | Check browser console for ICE errors; verify your network config |
| No Telegram alerts | Validate `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`; check network access |

---

## Known Issues

The following bugs are tracked for the next release:

- **Missing endpoints** — `/camera/acquire/{priority}/{name}` and `/camera/release/{priority}/{name}` are not yet implemented
- **Priority response mismatch** — `/camera/priority` response is missing the `can_motion_run` field
- **Duplicate method** — `stop_capture()` is defined twice in `camera_thread.py`

---

## Roadmap

- [ ] Camera lease system with priority locking
- [ ] State machine for the motion detection pipeline
- [ ] Rate limiting and authentication for all API routes
- [ ] Docker support (multi-stage build)
- [ ] System service integration (systemd / launchd)
- [ ] Multi-camera support
- [ ] Event timeline UI
- [ ] Face recognition module
- [ ] Optional cloud sync mode
- [ ] Mobile app integration

---

## Design Philosophy

EdgeGuard is built around three principles: **local-first** (your data stays on your hardware), **low latency** (edge processing means no round-trips to the cloud), and **modularity** (each component of the pipeline can be extended or replaced independently).

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

---


Made with ☕ for edge deployments that respect your privacy.
