"""
main.py — FastAPI application.

Lifespan starts the vision engine in a background thread.
WebSocket /ws/state — authenticated, full state ~5 Hz
WebSocket /ws/public — public, lights + ETA + notifications only
REST endpoints: /api/state, /api/config, /api/demo/ambulance/{road},
                /api/source, /api/history, /api/stats, /api/health,
                /api/roi  (GET/POST calibration),
                /api/upload (with secure validation)
"""
from __future__ import annotations

import asyncio
import base64
import json
import threading
import time
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any

import cv2
import numpy as np
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from slowapi import _rate_limit_exceeded_handler  # type: ignore
from slowapi.errors import RateLimitExceeded  # type: ignore

import app.config as cfg
from app.control.controller import PhaseSnapshot, SignalController, TransitionEvent
from app.control.emergency import EmergencyCoordinator
from app.control.predictor import ClearancePredictor
from app.events import EventBus
from app.security.auth import require_user, verify_token
from app.security.headers import SecurityHeadersMiddleware
from app.security.ratelimit import limiter
from app.sim.fixed_vs_adaptive import FixedVsAdaptive
from app.sim.vehicle_sim import TrafficSimulator
from app.store import get_history, init_db, log_transition
from app.vision.ambulance import AmbulanceDetector
from app.vision.detector import VehicleDetector
from app.vision.roi import ROIManager
from app.vision.sources import VideoSource

# ── Engine state (shared between vision thread and FastAPI) ────
_source: VideoSource | None = None
_roi = ROIManager()
_detector: VehicleDetector | None = None
_ambu_detector: AmbulanceDetector | None = None
_controller: SignalController | None = None
_predictor: ClearancePredictor | None = None
_emergency: EmergencyCoordinator | None = None
_simulator: FixedVsAdaptive | None = None
_vehicle_sim: TrafficSimulator | None = None
_event_bus = EventBus()
_latest_state: dict[str, Any] = {}
_latest_frame_jpg: bytes | None = None
_state_lock = threading.Lock()
_ws_clients: set[WebSocket] = set()
_ws_public_clients: set[WebSocket] = set()
_ws_lock = asyncio.Lock()
_engine_running = False


def _build_config() -> dict:
    return {
        "MAX_GREEN_S": cfg.MAX_GREEN_S,
        "EMPTY_CUTOFF_S": cfg.EMPTY_CUTOFF_S,
        "MIN_GREEN_S": cfg.MIN_GREEN_S,
        "YELLOW_S": cfg.YELLOW_S,
        "ALL_RED_S": cfg.ALL_RED_S,
        "EMPTY_CONFIRM_S": cfg.EMPTY_CONFIRM_S,
        "STARVATION_WAIT_S": cfg.STARVATION_WAIT_S,
        "DEMO_SPEED": cfg.DEMO_SPEED,
        "AMBU_HOLD_S": cfg.AMBU_HOLD_S,
        "AMBU_CLEAR_S": cfg.AMBU_CLEAR_S,
    }


def _on_transition(ev: TransitionEvent) -> None:
    log_transition(
        from_state=ev.from_state,
        to_state=ev.to_state,
        from_phase=ev.from_phase,
        to_phase=ev.to_phase,
        reason=ev.reason,
        green_duration_s=ev.green_duration,
        counts=ev.counts_snapshot,
    )
    # Emit notifications
    if ev.reason in ("EMPTY_EARLY", "MAX_REACHED", "FAIRNESS", "HIGHER_DEMAND"):
        _event_bus.on_switch(
            from_road=ev.from_phase,
            to_road=ev.to_phase,
            reason=ev.reason,
            saved_s=_simulator.stats.saved_green_s if _simulator else 0,
        )
    elif ev.reason == "EMERGENCY_START":
        road = _controller._emergency_road if _controller else "?"
        _event_bus.on_ambulance(road or "?")
    elif ev.reason in ("EMERGENCY_CLEAR", "EMERGENCY_TIMEOUT"):
        _event_bus.on_ambulance_clear(ev.from_phase)


def _vision_loop() -> None:
    """Background thread: reads frames, runs detection, ticks controller, updates virtual sim."""
    global _latest_state, _latest_frame_jpg, _engine_running
    assert _source and _detector and _ambu_detector and _controller
    assert _predictor and _emergency and _simulator and _vehicle_sim

    tick_interval = 1.0 / cfg.WS_BROADCAST_HZ
    last_tick = time.monotonic()

    for frame in _frame_gen():
        if not _engine_running:
            break

        now = time.monotonic()
        counts_map = _detector.process(frame)
        ambu_map = _ambu_detector.process(frame)

        counts = {r: rc.count for r, rc in counts_map.items()}
        densities = {r: rc.weighted_density for r, rc in counts_map.items()}

        snap = PhaseSnapshot(counts=counts, densities=densities, ambulance=ambu_map)

        if now - last_tick >= tick_interval:
            _controller.tick(snap)
            _emergency.update(ambu_map)
            _simulator.tick(counts, _controller.current_roads, cfg.DEMO_SPEED)

            # Update virtual 2D vehicle simulation
            _vehicle_sim.update(
                counts=counts,
                lights=_controller.lights,
                demo_speed=cfg.DEMO_SPEED,
            )

            for road, rc in counts_map.items():
                _predictor.update_discharge(road, rc.count)

            prediction = _predictor.predict(
                _controller.current_roads, counts, densities, _controller.elapsed_s
            )
            log_items = [
                {
                    "t": time.strftime("%H:%M:%S", time.localtime(ev.timestamp)),
                    "text": f"Road {ev.from_phase} → {ev.to_phase} ({ev.reason}, {ev.green_duration:.1f}s)",
                }
                for ev in _controller.transition_log[-5:]
            ]

            # Compute adaptive green time per road (for dashboard display)
            total_density = sum(densities.get(r, 0.0) for r in cfg.ROADS)
            adaptive_green_times = {}
            for r in cfg.ROADS:
                d = densities.get(r, 0.0)
                norm_density = d / max(total_density, 1.0)
                adaptive_green_times[r] = round(
                    max(
                        cfg.MIN_GREEN_S,
                        min(
                            cfg.MAX_GREEN_S,
                            cfg.MIN_GREEN_S + norm_density * (cfg.MAX_GREEN_S - cfg.MIN_GREEN_S),
                        )
                    ),
                    1,
                )

            state = {
                "ts": time.time(),
                "phase": _controller.current_phase,
                "state": _controller.state.value,
                "elapsed_s": round(_controller.elapsed_s, 1),
                "max_s": cfg.MAX_GREEN_S,
                "reason_last": (_controller.transition_log[-1].reason if _controller.transition_log else ""),
                "lights": _controller.lights,
                "roads": {
                    r: {
                        "count": counts.get(r, 0),
                        "density": densities.get(r, 0.0),
                        "waiting_s": round(_controller.waiting_s(r), 1),
                        "adaptive_green_s": adaptive_green_times.get(r, cfg.MIN_GREEN_S),
                    }
                    for r in cfg.ROADS
                },
                "predict": {
                    "clear_s": prediction.clear_s,
                    "confidence": prediction.confidence,
                },
                "emergency": {
                    "active": _controller.state.value == "EMERGENCY",
                    "road": _controller._emergency_road,
                },
                "stats": {
                    "saved_green_s": round(_simulator.stats.saved_green_s, 1),
                    "fixed_wasted_s": round(_simulator.stats.fixed_wasted_green_s, 1),
                    "adaptive_wasted_s": round(_simulator.stats.adaptive_wasted_green_s, 1),
                    "fixed_wait_vehicle_s": round(_simulator.stats.fixed_wait_vehicle_s, 1),
                    "adaptive_wait_vehicle_s": round(_simulator.stats.adaptive_wait_vehicle_s, 1),
                },
                "notifications": [
                    {"id": n.id, "level": n.level, "text": n.text}
                    for n in _event_bus.recent(10)
                ],
                "decision_log": log_items,
                # Virtual 2D simulation state
                "simulation": _vehicle_sim.snapshot(),
            }

            # Annotated frame → JPEG → base64
            annotated = _detector.annotate(frame, counts_map)
            _, jpg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 60])
            frame_b64 = base64.b64encode(jpg.tobytes()).decode()
            state["frame_b64"] = frame_b64

            with _state_lock:
                _latest_state = state
                _latest_frame_jpg = jpg.tobytes()

            last_tick = now


def _frame_gen():
    assert _source
    while _engine_running:
        frame = _source.read()
        if frame is not None:
            yield frame
        else:
            time.sleep(0.01)


def _start_engine(source_str: str | None = None) -> None:
    global _source, _detector, _ambu_detector, _controller, _predictor
    global _emergency, _simulator, _vehicle_sim, _engine_running

    _source = VideoSource(source_str)
    _source.start()

    _roi.load()
    _detector = VehicleDetector(_roi, mode=cfg.DETECTOR)
    _ambu_detector = AmbulanceDetector(_roi)
    _controller = SignalController(
        phases=cfg.PHASES,
        config=_build_config(),
        on_transition=_on_transition,
    )
    _predictor = ClearancePredictor()
    _emergency = EmergencyCoordinator(_controller)
    _simulator = FixedVsAdaptive(phases=cfg.PHASES, fixed_green_s=cfg.MAX_GREEN_S)
    _vehicle_sim = TrafficSimulator()

    _engine_running = True
    t = threading.Thread(target=_vision_loop, daemon=True)
    t.start()


def _stop_engine() -> None:
    global _engine_running
    _engine_running = False
    if _source:
        _source.stop()


# ── Lifespan ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    _start_engine()
    yield
    _stop_engine()


# ── App factory ─────────────────────────────────────────────────

app = FastAPI(title="Smart Adaptive Traffic Signal API", lifespan=lifespan)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)


# ── REST endpoints ──────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "engine": _engine_running}


@app.get("/api/state", dependencies=[Depends(require_user)])
def get_state():
    with _state_lock:
        return _latest_state


@app.get("/api/public/state")
def get_public_state():
    """Public read-only: lights + ETA only. No vehicle counts, no video."""
    with _state_lock:
        s = _latest_state
        return {
            "ts": s.get("ts"),
            "lights": s.get("lights", {}),
            "predict": s.get("predict", {}),
            "emergency": s.get("emergency", {}),
            "notifications": s.get("notifications", []),
        }


class ConfigUpdate(BaseModel):
    MAX_GREEN_S: float | None = None
    EMPTY_CUTOFF_S: float | None = None
    MIN_GREEN_S: float | None = None
    YELLOW_S: float | None = None
    ALL_RED_S: float | None = None
    STARVATION_WAIT_S: float | None = None
    DEMO_SPEED: float | None = None
    DETECTOR: str | None = None

    @validator("MAX_GREEN_S")
    def clamp_max_green(cls, v):
        if v is not None:
            return max(10.0, min(300.0, v))
        return v

    @validator("DEMO_SPEED")
    def clamp_speed(cls, v):
        if v is not None:
            return max(0.1, min(100.0, v))
        return v


@app.post("/api/config", dependencies=[Depends(require_user)])
def update_config(update: ConfigUpdate):
    if update.MAX_GREEN_S is not None:
        cfg.MAX_GREEN_S = update.MAX_GREEN_S
    if update.EMPTY_CUTOFF_S is not None:
        cfg.EMPTY_CUTOFF_S = update.EMPTY_CUTOFF_S
    if update.MIN_GREEN_S is not None:
        cfg.MIN_GREEN_S = update.MIN_GREEN_S
    if update.YELLOW_S is not None:
        cfg.YELLOW_S = update.YELLOW_S
    if update.ALL_RED_S is not None:
        cfg.ALL_RED_S = update.ALL_RED_S
    if update.STARVATION_WAIT_S is not None:
        cfg.STARVATION_WAIT_S = update.STARVATION_WAIT_S
    if update.DEMO_SPEED is not None:
        cfg.DEMO_SPEED = update.DEMO_SPEED
    if update.DETECTOR is not None and update.DETECTOR in ("yolo", "motion"):
        cfg.DETECTOR = update.DETECTOR
    if _controller:
        _controller._cfg.update(_build_config())
    return {"status": "updated"}


@app.post("/api/demo/ambulance/{road}", dependencies=[Depends(require_user)])
def simulate_ambulance(road: str):
    road = road.upper()
    if road not in cfg.ROADS:
        raise HTTPException(status_code=400, detail=f"Unknown road: {road}")
    if _ambu_detector:
        _ambu_detector.simulate(road)
    return {"status": "simulated", "road": road}


class SourceUpdate(BaseModel):
    source: str


@app.post("/api/source", dependencies=[Depends(require_user)])
def switch_source(body: SourceUpdate):
    if _source:
        _source.switch(body.source)
    return {"status": "switched", "source": body.source}


# Allowed video MIME types for upload security
_ALLOWED_VIDEO_TYPES = {
    "video/mp4", "video/x-m4v", "video/quicktime",
    "video/x-msvideo", "video/avi", "video/webm",
    "video/mpeg", "video/ogg",
}
_MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB
_ALLOWED_EXTENSIONS = {'.mp4', '.m4v', '.mov', '.avi', '.webm', '.mpg', '.mpeg', '.ogv'}


@app.post("/api/upload", dependencies=[Depends(require_user)])
def upload_video(file: UploadFile = File(...)):
    # Validate file extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only video files are accepted.",
        )
    # Validate MIME type
    if file.content_type and file.content_type not in _ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content type.",
        )
    # Validate size (stream read with limit)
    samples_dir = Path("samples")
    samples_dir.mkdir(exist_ok=True)
    safe_name = f"{int(time.time())}_{Path(file.filename or 'upload').name}"
    file_path = samples_dir / safe_name
    total_bytes = 0
    try:
        with open(file_path, "wb") as buffer:
            while chunk := file.file.read(65536):
                total_bytes += len(chunk)
                if total_bytes > _MAX_UPLOAD_BYTES:
                    buffer.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File exceeds 200 MB limit.",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Upload failed.") from exc

    if _source:
        _source.switch(str(file_path))
    return {"status": "uploaded", "filename": safe_name}


@app.get("/api/history", dependencies=[Depends(require_user)])
def get_history_endpoint(limit: int = 100):
    return get_history(min(limit, 500))


# ── ROI calibration endpoints ───────────────────────────────────

@app.get("/api/roi", dependencies=[Depends(require_user)])
def get_roi():
    """Return current ROI polygons (road → list of [x,y] points)."""
    return {road: _roi.polygon(road).tolist() for road in _roi.roads()}


class RoiUpdate(BaseModel):
    rois: dict[str, list[list[int]]]


@app.post("/api/roi", dependencies=[Depends(require_user)])
def set_roi(body: RoiUpdate):
    """Update ROI polygons. Each road must have ≥ 3 points."""
    for road, pts in body.rois.items():
        if road not in cfg.ROADS:
            raise HTTPException(status_code=400, detail=f"Unknown road: {road}")
        if len(pts) < 3:
            raise HTTPException(status_code=400, detail=f"Road {road} needs ≥ 3 points.")
        for pt in pts:
            if len(pt) != 2 or not all(isinstance(v, int) for v in pt):
                raise HTTPException(status_code=400, detail="Each point must be [x, y] integers.")
        _roi.set_roi(road, pts)
    _roi.save()
    # Recreate detector with updated ROIs
    if _detector:
        _detector._roi = _roi
        _detector._smooth = {r: _detector._smooth.get(r, __import__('collections').deque())
                             for r in _roi.roads()}
    return {"status": "saved", "roads": list(body.rois.keys())}


@app.get("/api/stats", dependencies=[Depends(require_user)])
def get_stats():
    if _simulator is None:
        return {}
    return {
        "fixed_wasted_green_s": _simulator.stats.fixed_wasted_green_s,
        "adaptive_wasted_green_s": _simulator.stats.adaptive_wasted_green_s,
        "saved_green_s": _simulator.stats.saved_green_s,
        "fixed_wait_vehicle_s": _simulator.stats.fixed_wait_vehicle_s,
        "adaptive_wait_vehicle_s": _simulator.stats.adaptive_wait_vehicle_s,
    }


# ── WebSocket ───────────────────────────────────────────────────

async def _ws_auth(ws: WebSocket) -> bool:
    """Receive first message (token) within WS_AUTH_TIMEOUT_S or close."""
    try:
        msg = await asyncio.wait_for(ws.receive_text(), timeout=cfg.WS_AUTH_TIMEOUT_S)
        data = json.loads(msg)
        token = data.get("token", "")
        verify_token(token)
        return True
    except Exception:
        await ws.close(code=4001)
        return False


@app.websocket("/ws/state")
async def ws_state(ws: WebSocket):
    await ws.accept()
    if not await _ws_auth(ws):
        return
    async with _ws_lock:
        _ws_clients.add(ws)
    try:
        while True:
            with _state_lock:
                state = dict(_latest_state)
            await ws.send_text(json.dumps(state))
            await asyncio.sleep(1.0 / cfg.WS_BROADCAST_HZ)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        async with _ws_lock:
            _ws_clients.discard(ws)


@app.websocket("/ws/public")
async def ws_public(ws: WebSocket):
    await ws.accept()
    async with _ws_lock:
        _ws_public_clients.add(ws)
    try:
        while True:
            with _state_lock:
                s = _latest_state
                payload = {
                    "ts": s.get("ts"),
                    "lights": s.get("lights", {}),
                    "predict": s.get("predict", {}),
                    "emergency": s.get("emergency", {}),
                    "notifications": s.get("notifications", []),
                }
            await ws.send_text(json.dumps(payload))
            await asyncio.sleep(1.0 / cfg.WS_BROADCAST_HZ)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        async with _ws_lock:
            _ws_public_clients.discard(ws)
