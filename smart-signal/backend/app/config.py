"""
config.py — All tuneable parameters for Smart Adaptive Traffic Signal.
Edit here or override via environment variables.
"""
import os

# ── Signal timing ──────────────────────────────────────────────
MAX_GREEN_S: float = float(os.getenv("MAX_GREEN_S", 120))
EMPTY_CUTOFF_S: float = float(os.getenv("EMPTY_CUTOFF_S", 35))
MIN_GREEN_S: float = float(os.getenv("MIN_GREEN_S", 10))
YELLOW_S: float = float(os.getenv("YELLOW_S", 3))
ALL_RED_S: float = float(os.getenv("ALL_RED_S", 1))
EMPTY_CONFIRM_S: float = float(os.getenv("EMPTY_CONFIRM_S", 3))
STARVATION_WAIT_S: float = float(os.getenv("STARVATION_WAIT_S", 150))

# ── Demo ───────────────────────────────────────────────────────
DEMO_SPEED: float = float(os.getenv("DEMO_SPEED", 1))  # 1 = real-time; 10 = 10×

# ── Predictor ──────────────────────────────────────────────────
SECONDS_PER_VEHICLE: float = float(os.getenv("SECONDS_PER_VEHICLE", 2.0))
STARTUP_LOST_S: float = float(os.getenv("STARTUP_LOST_S", 2.0))
VEHICLE_WEIGHTS: dict[str, float] = {
    "motorcycle": 0.5,
    "car": 1.0,
    "bus": 2.5,
    "truck": 2.5,
}

# ── Vision ─────────────────────────────────────────────────────
DETECTOR: str = os.getenv("DETECTOR", "yolo")          # "yolo" | "motion"
PROCESS_EVERY_N_FRAMES: int = int(os.getenv("PROCESS_EVERY_N_FRAMES", 1))
YOLO_MODEL: str = os.getenv("YOLO_MODEL", "yolov8s.pt")
YOLO_IMGSZ: int = int(os.getenv("YOLO_IMGSZ", 1024))
YOLO_CONF: float = float(os.getenv("YOLO_CONF", 0.15))
SMOOTHING_WINDOW_S: float = float(os.getenv("SMOOTHING_WINDOW_S", 1.5))

# ── Ambulance detection ────────────────────────────────────────
# HSV range for the toy ambulance (white body, red marking)
AMBU_HSV_LOWER: list[int] = [0, 100, 100]    # red lower
AMBU_HSV_UPPER: list[int] = [10, 255, 255]   # red upper
AMBU_MIN_AREA: int = int(os.getenv("AMBU_MIN_AREA", 500))
AMBU_HOLD_S: float = float(os.getenv("AMBU_HOLD_S", 30))  # timeout after detected
AMBU_CLEAR_S: float = float(os.getenv("AMBU_CLEAR_S", 3))  # clear of ROI for this long

# ── Source ─────────────────────────────────────────────────────
SOURCE_DEFAULT: str = os.getenv("SOURCE_DEFAULT", "0")
CAMERA_INDEX: int = int(os.getenv("CAMERA_INDEX", 0))

# ── WebSocket ──────────────────────────────────────────────────
WS_BROADCAST_HZ: float = float(os.getenv("WS_BROADCAST_HZ", 5))
WS_AUTH_TIMEOUT_S: float = float(os.getenv("WS_AUTH_TIMEOUT_S", 5))

# ── Security ───────────────────────────────────────────────────
ALLOWED_EMAILS: list[str] = [
    e.strip() for e in os.getenv("ALLOWED_EMAILS", "").split(",") if e.strip()
]
CORS_ORIGINS: list[str] = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()
]

# ── Database ───────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "smart_signal.db")

# ── Roads and phases ───────────────────────────────────────────
ROADS: list[str] = ["A", "B", "C", "D"]
PHASES: dict[str, list[str]] = {
    "P1": ["A"],
    "P2": ["B"],
    "P3": ["C"],
    "P4": ["D"],
}
