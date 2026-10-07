"""
vision/roi.py — Per-road polygon region-of-interest manager.
ROIs are saved to / loaded from roi.json in the project root.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROI_FILE = Path("roi.json")

# Default ROIs — Perfect corner-to-corner triangles for a standard 1920x1080 frame.
# This ensures 100% screen coverage for any video (no empty corners!).
# A = Left, B = Top, C = Right, D = Bottom
_DEFAULT_ROIS: dict[str, list[list[int]]] = {
    "A": [[0, 0], [960, 540], [0, 1080]],              # Left Triangle
    "B": [[0, 0], [1920, 0], [960, 540]],              # Top Triangle
    "C": [[1920, 0], [1920, 1080], [960, 540]],        # Right Triangle
    "D": [[0, 1080], [960, 540], [1920, 1080]],        # Bottom Triangle
}


class ROIManager:
    """Holds one polygon (convex or not) per road."""

    def __init__(self) -> None:
        self._rois: dict[str, np.ndarray] = {}
        self.load()

    # ── Public ──────────────────────────────────────────────────

    def load(self, path: Path = ROI_FILE) -> None:
        if path.exists():
            raw: dict[str, Any] = json.loads(path.read_text())
        else:
            raw = _DEFAULT_ROIS
        self._rois = {
            road: np.array(pts, dtype=np.int32) for road, pts in raw.items()
        }

    def save(self, path: Path = ROI_FILE) -> None:
        data = {road: pts.tolist() for road, pts in self._rois.items()}
        path.write_text(json.dumps(data, indent=2))

    def set_roi(self, road: str, points: list[list[int]]) -> None:
        self._rois[road] = np.array(points, dtype=np.int32)

    def roads(self) -> list[str]:
        return list(self._rois.keys())

    def polygon(self, road: str) -> np.ndarray:
        return self._rois[road]

    def auto_scale(self, w: int, h: int) -> None:
        """Dynamically scale ROIs if the frame size changed (e.g. from webcam to 4K video)."""
        if not self._rois:
            return
        # Find the max X and Y across all ROIs
        max_x = max(int(np.max(pts[:, 0])) for pts in self._rois.values())
        max_y = max(int(np.max(pts[:, 1])) for pts in self._rois.values())
        
        # If the ROIs are significantly smaller than the frame (e.g. 640x480 ROIs on a 1920x1080 video)
        if max_x > 0 and max_y > 0 and (w / max_x > 1.2 or h / max_y > 1.2):
            scale_x = w / max_x
            scale_y = h / max_y
            for road in self._rois:
                pts = self._rois[road].astype(np.float32)
                pts[:, 0] *= scale_x
                pts[:, 1] *= scale_y
                self._rois[road] = pts.astype(np.int32)
        
        # Also scale down if the video is much smaller
        elif max_x > 0 and max_y > 0 and (max_x / w > 1.2 or max_y / h > 1.2):
            scale_x = w / max_x
            scale_y = h / max_y
            for road in self._rois:
                pts = self._rois[road].astype(np.float32)
                pts[:, 0] *= scale_x
                pts[:, 1] *= scale_y
                self._rois[road] = pts.astype(np.int32)

    def point_in_roi(self, road: str, x: float, y: float) -> bool:
        """True if (x, y) is inside the road's polygon."""
        poly = self._rois.get(road)
        if poly is None:
            return False
        return cv2.pointPolygonTest(poly, (float(x), float(y)), False) >= 0

    def center_in_roi(self, road: str, bbox: tuple[int, int, int, int]) -> bool:
        """True if the center of bbox (x1,y1,x2,y2) is inside the road ROI."""
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        return self.point_in_roi(road, cx, cy)

    def draw(self, frame: np.ndarray, color: tuple[int, int, int] = (0, 255, 0)) -> np.ndarray:
        """Draw all ROI polygons on the frame (in-place copy)."""
        out = frame.copy()
        for road, poly in self._rois.items():
            cv2.polylines(out, [poly], isClosed=True, color=color, thickness=2)
            # Label at centroid
            cx = int(poly[:, 0].mean())
            cy = int(poly[:, 1].mean())
            cv2.putText(out, f"Road {road}", (cx - 20, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return out
