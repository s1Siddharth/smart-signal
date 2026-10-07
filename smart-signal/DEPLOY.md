# Deployment Guide

A cloud server cannot access the webcam on your laptop directly. Therefore, we recommend two modes:

### Mode A: Cloud Demo
Deploy the app to the cloud using a recorded sample traffic video.
1. Place a sample video in the `samples/` directory (e.g., `samples/traffic.mp4`).
2. Deploy the Backend Docker container to Render or Railway.
3. Deploy the Frontend to Vercel.
4. Open the Vercel URL during your presentation.

### Mode B: Live Model Demo (Cloudflare Tunnel)
Deploy the frontend to Vercel, but run the backend on your laptop with the live webcam.
1. Run the backend locally: `uvicorn app.main:app --port 8000`
2. Expose it via Cloudflare Tunnel: `cloudflared tunnel --url http://localhost:8000`
3. Copy the generated HTTPS URL from Cloudflare.
4. Set the `VITE_API_URL` in your Vercel frontend environment variables to this Cloudflare URL.
5. The deployed Vercel site will now talk to your laptop's backend, viewing the live camera.

## Step-by-Step Deployment (Mode A)

### Backend (Render / Railway)
1. Create a new GitHub repository and push your code.
2. Sign up for [Render](https://render.com) or [Railway](https://railway.app).
3. Create a new "Web Service" connected to your GitHub repo.
4. Select the `backend/Dockerfile`.
5. Environment Variables:
   - `CORS_ORIGINS`: `https://your-frontend-url.vercel.app`
   - `FIREBASE_SERVICE_ACCOUNT_JSON`: The raw JSON string of your Firebase admin credentials.
   - `ALLOWED_EMAILS`: Comma-separated list of allowed user emails.
6. Deploy and note the public URL.

### Frontend (Vercel)
1. Sign up for [Vercel](https://vercel.com).
2. Create a new Project connected to your GitHub repo.
3. Set the Framework Preset to `Vite`.
4. Set the Root Directory to `frontend`.
5. Environment Variables:
   - `VITE_API_URL`: The URL of your backend (from Render/Railway).
   - All `VITE_FIREBASE_*` variables from your local `.env.local` file.
6. Deploy!

### Post-Deploy Smoke Test Checklist
- [ ] Backend `/api/health` returns `{"status": "ok", "engine": true}`
- [ ] Unauthenticated GET to `/api/state` returns a `401 Unauthorized` error.
- [ ] Email and Google login both work, and unauthorized emails are blocked.
- [ ] The Dashboard successfully connects to the WebSocket over `wss://` and receives live data.
- [ ] The Commuter page (`/commuter`) opens on a phone, requires no login, and displays no video.
- [ ] Clicking "Simulate Ambulance" correctly preempts the signal and sends an alert.
