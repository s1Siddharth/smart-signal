# Smart Signal Deployment Guide

Since a cloud server cannot access your laptop's physical webcam directly, the system has two main deployment modes depending on your presentation needs:

## Mode A: Cloud Demo (Recommended for Public Links)
Deploy both the frontend and backend to the cloud. The backend will analyze a pre-recorded traffic video instead of a live webcam.

### 1. Backend (Render / Railway)
1. Ensure you have a sample traffic video in your repository at `backend/samples/traffic.mp4`.
2. Sign up for [Render](https://render.com) or [Railway](https://railway.app).
3. Create a new **Web Service** connected to your GitHub repo.
4. Choose the **Docker** environment (`backend/Dockerfile`).
5. **Set the following Environment Variables:**
   - `CORS_ORIGINS`: `https://your-frontend-url.vercel.app` *(Update this after deploying Vercel)*
   - `SOURCE_DEFAULT`: `samples/traffic.mp4` *(Critical: points the system to your video instead of a webcam)*
   - `DETECTOR`: `yolo`
   - `FIREBASE_SERVICE_ACCOUNT_JSON`: The raw JSON string of your Firebase admin credentials (optional, for auth).
   - `ALLOWED_EMAILS`: Comma-separated list of allowed user emails.
6. Deploy and note the public URL (e.g., `https://smart-signal-api.onrender.com`).

*Note: Free cloud tiers often use ephemeral storage. The `smart_signal.db` SQLite database will reset if the server restarts unless you attach a persistent disk.*

### 2. Frontend (Vercel)
1. Sign up for [Vercel](https://vercel.com).
2. Create a new Project connected to your GitHub repo.
3. Set the **Framework Preset** to `Vite`.
4. Set the **Root Directory** to `frontend`.
5. **Set the following Environment Variables:**
   - `VITE_API_URL`: The URL of your backend (from Render/Railway).
   - `VITE_FIREBASE_API_KEY`: *(From Firebase Console)*
   - `VITE_FIREBASE_AUTH_DOMAIN`: *(From Firebase Console)*
   - `VITE_FIREBASE_PROJECT_ID`: *(From Firebase Console)*
   - `VITE_FIREBASE_STORAGE_BUCKET`: *(From Firebase Console)*
   - `VITE_FIREBASE_MESSAGING_SENDER_ID`: *(From Firebase Console)*
   - `VITE_FIREBASE_APP_ID`: *(From Firebase Console)*
6. Deploy!

---

## Mode B: Live Model Demo (Cloudflare Tunnel)
Use this if you are doing an in-person presentation with a live physical cardboard model and a webcam connected to your laptop. The frontend is hosted in the cloud, but the backend runs on your laptop.

### 1. Run Backend Locally
1. Connect your webcam pointing at the model.
2. In `backend/.env`, set `SOURCE_DEFAULT=0` (or the correct camera index).
3. Start the backend: `uvicorn app.main:app --port 8000`

### 2. Expose via Cloudflare Tunnel
1. Install `cloudflared`.
2. Run: `cloudflared tunnel --url http://localhost:8000`
3. Copy the generated HTTPS URL (e.g., `https://random-words.trycloudflare.com`).

### 3. Deploy Frontend (Vercel)
1. Follow the Vercel steps from Mode A.
2. Set the `VITE_API_URL` environment variable in Vercel to your Cloudflare tunnel URL.
3. The deployed Vercel site will now talk to your laptop's backend, allowing you to view the live camera on the dashboard from anywhere.

---

## Post-Deploy Smoke Test Checklist
- [ ] Backend `/api/health` returns `{"status": "ok", "engine": true}`
- [ ] Unauthenticated GET to `/api/state` returns a `401 Unauthorized` error.
- [ ] Email and Google login both work, and unauthorized emails are blocked.
- [ ] The Dashboard successfully connects to the WebSocket over `wss://` and receives live data.
- [ ] The Commuter page (`/commuter`) opens on a phone, requires no login, and displays no video.
- [ ] Clicking "Simulate Ambulance" correctly preempts the signal and sends an alert.
