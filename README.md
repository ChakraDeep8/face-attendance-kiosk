# Verity Face Attendance

A privacy-focused face registration and attendance kiosk built with React, TypeScript, Express, and the Human face-analysis library.

## Features

- Guided employee enrollment with center, left, right, up, and down head poses
- 468-point facial mesh and six-template identity profiles
- Continuous 24×7 camera monitoring with automatic matching
- Visual and audible security alerts for unknown faces
- Multi-frame live recognition with screen wake-lock support
- Liveness and anti-spoofing signals
- Duplicate check-in protection
- Persistent local roster, attendance events, and audit history
- Responsive administrator dashboard and kiosk interface

## Run locally

```bash
npm install
npm run dev
```

Open `http://localhost:5173`. The local API runs on `http://127.0.0.1:8791`.

This experiment currently uses the browser webcam. The camera provider is
isolated so a later edge deployment can replace it with an RTSP-to-WebRTC
gateway without changing enrollment, recognition, alerts, or attendance logic.

```text
Current: Webcam → browser video → face model → local attendance API
Future:  RTSP camera → edge gateway/WebRTC → face model → edge attendance API
```

## Production build

```bash
npm run build
```

## Data and privacy

Local registrations and attendance records are written under `data/`, which is excluded from Git. Do not use this prototype as a legally certified biometric identity system without a privacy, security, retention, and accessibility review.
