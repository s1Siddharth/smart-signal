# Smart Adaptive Traffic Signal

An adaptive traffic signal control system built for an OE Design Thinking project.

This project upgrades a baseline traffic signal system into a comprehensive dynamic, AI-based adaptive traffic signal system that takes input from a physical 4-road model (via a top-down camera) and drives both a live operator dashboard and a 2D virtual simulation.

## Project Structure
- `backend/`: FastAPI + OpenCV + YOLO/MOG2 state machine, signal controller, and 2D physics simulation.
- `frontend/`: React + Vite + Tailwind frontend dashboard (Transit Control Room theme), including a live 2D Canvas-based simulation.
- `docs/`: Technical documentation and product requirements (PRD).
- `config/`: Centralized JSON schema configuration reference.
- `tools/`: Utility scripts (e.g., ROI calibration).
- `backend/samples/`: Drop traffic video MP4 files here for fallback/demo mode.

## Core Features
1. **Adaptive Signal Logic**: Green time dynamically scales based on live vehicle density and counts.
2. **2D Virtual Simulation**: A live top-down interactive canvas in the frontend that mirrors the physical model's vehicle counts with realistic queuing and physics.
3. **Emergency Preemption**: Detects ambulances (via red hue masking) and immediately overrides the state machine to grant green.
4. **Fairness / Anti-Starvation**: Enforces wait time limits to ensure no road is starved.
5. **Secure Configuration & Uploads**: Secure video upload endpoint for testing and a centralized config schema (`traffic_config.json`).
6. **ROI Calibration API**: Allows dynamic updating of Regions of Interest (ROI) via API.

## 5-Minute Quick Start

### 1. Requirements
- Python 3.11+
- Node.js 20 LTS

### 2. Configure Environment
1. Copy `backend/.env.example` to `backend/.env`.
2. (Optional) Configure Firebase: Go to Firebase Console, create a new project, enable Email/Password & Google sign-in. Set up a Web App and add the config to `frontend/.env.local`. Generate a private key for the backend and set it in `backend/.env` as `FIREBASE_SERVICE_ACCOUNT_JSON`. If omitted, the backend runs in DEV MODE and accepts mock tokens for local testing.

### 3. Start Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate   # (Windows)
# source venv/bin/activate # (Mac/Linux)
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Start Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

## Using the Physical Model Input

To run the system with your physical 4-road model:
1. Mount a webcam directly above the intersection pointing downwards.
2. In `backend/.env`, set `SOURCE_DEFAULT=0` (or the correct camera index for your webcam).
3. The system will detect vehicles using YOLOv8 or motion tracking (configured via `DETECTOR=yolo` or `DETECTOR=motion`).
4. Watch the vehicles move in the physical model and see the virtual 2D simulation in the dashboard reflect the live state.

## Sample Video Fallback

For reliable demos without hardware, place a sample traffic video in the `samples/` directory:
1. Place your video (e.g., `traffic.mp4`) in `backend/samples/`.
2. The system will automatically use this as a fallback when no webcam is available, or you can switch to it from the Dashboard.

## Modes

- **Mode A (Cloud Demo)**: A cloud-deployed version running with a sample traffic video.
- **Mode B (Live Hardware Demo)**: Running on your laptop with a webcam pointing at a physical cardboard model.

## Privacy Note
This system processes video streams in real-time. No video frames or video files are saved to the database or written to disk. The public Commuter page explicitly hides all video feeds and only transmits traffic light status and ETAs.