"""
vision/ambulance.py — Ambulance detection.

Three-tier approach (in order of reliability):
  (a) Color + shape heuristic (HSV red mask inside ROI)
  (b) Demo simulate button — sets a flag via API endpoint
  (c) Optional: YOLO fine-tune (future)

The simulate flag is always shipped so the demo never fails.
"""
from __future__ import annotations

import threading
import time

import cv2
import numpy as np

from app.config import (
    AMBU_CLEAR_S,
    AMBU_HOLD_S,
    AMBU_HSV_LOWER,
    AMBU_HSV_UPPER,
    AMBU_MIN_AREA,
)
from app.vision.roi import ROIManager


class AmbulanceDetector:
    """Detects ambulance presence per road using HSV color heuristic + simulate API."""

    def __init__(self, roi: ROIManager) -> None:
        self._roi = roi
        self._lock = threading.Lock()
        # Per-road state
        self._detected: dict[str, bool] = {r: False for r in roi.roads()}
        self._simulate_until: dict[str, float] = {r: 0.0 for r in roi.roads()}
        self._clear_since: dict[str, float | None] = {r: None for r in roi.roads()}

    # ── Public ──────────────────────────────────────────────────

    def process(self, frame: np.ndarray) -> dict[str, bool]:
        """Return per-road ambulance flag (True = ambulance present)."""
        now = time.monotonic()
        result: dict[str, bool] = {}
        for road in self._roi.roads():
            color_hit = self._color_detect(frame, road)
            sim_hit = now < self._simulate_until.get(road, 0.0)
            detected = color_hit or sim_hit

            with self._lock:
                if not detected:
                    # Start clear timer
                    if self._clear_since[road] is None:
                        self._clear_since[road] = now
                    elif (now - self._clear_since[road]) >= AMBU_CLEAR_S:  # type: ignore
                        self._detected[road] = False
                else:
                    self._clear_since[road] = None
                    self._detected[road] = True

                result[road] = self._detected[road]

        return result

    def simulate(self, road: str, duration_s: float = AMBU_HOLD_S) -> None:
        """Trigger ambulance simulation on a road (from the API/demo button)."""
        with self._lock:
            self._simulate_until[road] = time.monotonic() + duration_s
            self._detected[road] = True
            self._clear_since[road] = None

    def clear_simulation(self, road: str) -> None:
        """Manually clear the simulate flag for a road."""
        with self._lock:
            self._simulate_until[road] = 0.0

    # ── Internal ────────────────────────────────────────────────

    def _color_detect(self, frame: np.ndarray, road: str) -> bool:
        """True if a red region (ambulance marking) appears inside the road's ROI."""
        poly = self._roi.polygon(road)
        mask_roi = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(mask_roi, [poly], 255)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower = np.array(AMBU_HSV_LOWER, dtype=np.uint8)
        upper = np.array(AMBU_HSV_UPPER, dtype=np.uint8)
        red_mask = cv2.inRange(hsv, lower, upper)

        # Also cover the wrap-around red (170–180)
        lower2 = np.array([170, 100, 100], dtype=np.uint8)
        upper2 = np.array([180, 255, 255], dtype=np.uint8)
        red_mask2 = cv2.inRange(hsv, lower2, upper2)
        combined = cv2.bitwise_or(red_mask, red_mask2)

        masked = cv2.bitwise_and(combined, combined, mask=mask_roi)
        return int(masked.sum()) // 255 >= AMBU_MIN_AREA
