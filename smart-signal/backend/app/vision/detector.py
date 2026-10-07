"""
vision/detector.py — Vehicle detector.

Supports two modes (config DETECTOR):
  "yolo"   — Ultralytics YOLOv8n on COCO classes
  "motion" — OpenCV MOG2 background subtraction + contour filter

Output per road: RoadCounts dataclass.
Counts are smoothed with a rolling median over SMOOTHING_WINDOW_S seconds.
"""
from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from app.config import (
    DETECTOR,
    PROCESS_EVERY_N_FRAMES,
    SMOOTHING_WINDOW_S,
    VEHICLE_WEIGHTS,
    YOLO_CONF,
    YOLO_IMGSZ,
    YOLO_MODEL,
)
from app.vision.roi import ROIManager

# COCO class IDs for vehicles
_YOLO_VEHICLE_IDS: dict[int, str] = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

_MOTION_MIN_AREA = 800  # pixels²


@dataclass
class Detection:
    bbox: tuple[int, int, int, int]  # x1,y1,x2,y2
    cls: str
    conf: float


@dataclass
class RoadCounts:
    road: str
    count: int = 0
    weighted_density: float = 0.0
    vehicles: list[Detection] = field(default_factory=list)


class VehicleDetector:
    """Runs detection on each frame and returns per-road counts."""

    def __init__(self, roi: ROIManager, mode: str = DETECTOR) -> None:
        self._roi = roi
        self._mode = mode
        self._frame_idx = 0
        self._last_result: dict[str, RoadCounts] = {}

        # Smoothing buffers: road → deque of (timestamp, count)
        self._smooth: dict[str, collections.deque[tuple[float, int]]] = {
            r: collections.deque() for r in roi.roads()
        }

        # YOLO model (lazy load)
        self._yolo: Any | None = None

        # MOG2 background subtractor (motion mode)
        self._mog2: Any | None = None
        if mode == "motion":
            self._mog2 = cv2.createBackgroundSubtractorMOG2(
                history=200, varThreshold=50, detectShadows=False
            )

    # ── Public ──────────────────────────────────────────────────

    def process(self, frame: np.ndarray) -> dict[str, RoadCounts]:
        """Process a frame. Returns per-road RoadCounts (smoothed)."""
        self._roi.auto_scale(frame.shape[1], frame.shape[0])
        
        self._frame_idx += 1
        if self._frame_idx % PROCESS_EVERY_N_FRAMES != 0:
            return self._last_result

        if self._mode == "yolo":
            raw = self._detect_yolo(frame)
        else:
            raw = self._detect_motion(frame)

        self._last_raw = raw

        now = time.monotonic()
        result: dict[str, RoadCounts] = {}
        for road in self._roi.roads():
            road_dets = [d for d in raw if self._roi.center_in_roi(road, d.bbox)]
            raw_count = len(road_dets)

            # Push to smoothing buffer
            buf = self._smooth[road]
            buf.append((now, raw_count))
            # Drop old entries outside the window
            while buf and (now - buf[0][0]) > SMOOTHING_WINDOW_S:
                buf.popleft()

            # Smoothed count = median of recent counts
            counts_in_window = [c for _, c in buf]
            smoothed = int(np.median(counts_in_window)) if counts_in_window else 0

            weighted = sum(
                VEHICLE_WEIGHTS.get(d.cls, 1.0) for d in road_dets
            )

            result[road] = RoadCounts(
                road=road,
                count=smoothed,
                weighted_density=round(weighted, 2),
                vehicles=road_dets,
            )

        self._last_result = result
        return result

    def annotate(self, frame: np.ndarray, counts: dict[str, RoadCounts]) -> np.ndarray:
        """Draw bounding boxes and road counts on the frame."""
        out = self._roi.draw(frame)
        
        # 1. Draw all raw detections lightly (so user knows YOLO is working outside ROIs)
        if hasattr(self, '_last_raw'):
            for d in getattr(self, '_last_raw', []):
                x1, y1, x2, y2 = d.bbox
                cv2.rectangle(out, (x1, y1), (x2, y2), (0, 140, 255), 1) # Orange

        # 2. Draw vehicles inside ROIs boldly, and add Count/Density text
        for road, rc in counts.items():
            for d in rc.vehicles:
                x1, y1, x2, y2 = d.bbox
                cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2) # Green
                cv2.putText(out, f"{d.cls} {d.conf:.2f}", (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
            
            if road in self._roi._rois:
                poly = self._roi._rois[road]
                px = min(p[0] for p in poly)
                py = min(p[1] for p in poly)
                cv2.putText(out, f"Count: {rc.count}", (px + 10, py + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.putText(out, f"Density: {rc.weighted_density}", (px + 10, py + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
        return out

    # ── YOLO ────────────────────────────────────────────────────

    def _detect_yolo(self, frame: np.ndarray) -> list[Detection]:
        if self._yolo is None:
            from ultralytics import YOLO  # type: ignore
            self._yolo = YOLO(YOLO_MODEL)

        results = self._yolo(frame, imgsz=YOLO_IMGSZ, conf=YOLO_CONF, verbose=False)
        dets: list[Detection] = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls_id = int(box.cls[0])
                if cls_id not in _YOLO_VEHICLE_IDS:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                dets.append(Detection(
                    bbox=(x1, y1, x2, y2),
                    cls=_YOLO_VEHICLE_IDS[cls_id],
                    conf=float(box.conf[0]),
                ))
        return dets

    # ── Motion (MOG2) ───────────────────────────────────────────

    def _detect_motion(self, frame: np.ndarray) -> list[Detection]:
        assert self._mog2 is not None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mask = self._mog2.apply(gray)
        _, thresh = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        dets: list[Detection] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < _MOTION_MIN_AREA:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            dets.append(Detection(bbox=(x, y, x + w, y + h), cls="car", conf=1.0))
        return dets
