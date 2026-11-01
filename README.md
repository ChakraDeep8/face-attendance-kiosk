# Verity Face Attendance

A privacy-focused face registration and attendance kiosk built with React, TypeScript, Express, and the Human face-analysis library.

## Features

- Register people with a camera capture or uploaded image
- 468-point facial mesh and multi-sample face descriptors
- Five-frame live check-in matching
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

## Production build

```bash
npm run build
```

## Data and privacy

Local registrations and attendance records are written under `data/`, which is excluded from Git. Do not use this prototype as a legally certified biometric identity system without a privacy, security, retention, and accessibility review.
