"""
vision/sources.py — Video source reader.
Supports webcam index, video file (loops for demo), and RTSP URL.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Generator

import cv2
import numpy as np

from app.config import CAMERA_INDEX, SOURCE_DEFAULT


class VideoSource:
    """Thread-safe frame provider that supports webcam, file, and RTSP."""

    def __init__(self, source: str | None = None) -> None:
        self._source_str: str = source or SOURCE_DEFAULT
        self._cap: cv2.VideoCapture | None = None
        self._lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._running = False
        self._thread: threading.Thread | None = None

    # ── Public API ──────────────────────────────────────────────

    def start(self) -> None:
        """Open the source and start the background reader thread."""
        self._open()
        self._running = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        if self._cap:
            try:
                self._cap.release()
            except Exception as e:
                print(f"WARNING: Error releasing video capture: {e}")
            self._cap = None

    def read(self) -> np.ndarray | None:
        """Return the most recent frame (BGR) or None if not available."""
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def switch(self, source: str) -> None:
        """Hot-swap the video source at runtime."""
        self.stop()
        self._source_str = source
        self.start()

    @property
    def source_str(self) -> str:
        return self._source_str

    # ── Internal ────────────────────────────────────────────────

    def _open(self) -> None:
        src = self._resolve_source(self._source_str)
        try:
            self._cap = cv2.VideoCapture(src)
            # Try DirectShow fallback if default MSMF fails on Windows
            if not self._cap.isOpened() and isinstance(src, int) and __import__("os").name == "nt":
                print(f"Default camera API failed for index {src}, trying DirectShow...")
                self._cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)

            if not self._cap.isOpened():
                print(f"WARNING: Cannot open video source: {self._source_str!r}. Running without video.")
                self._cap = None
                self._fps = 10.0
            else:
                self._fps = self._cap.get(cv2.CAP_PROP_FPS)
                if not self._fps or self._fps <= 0:
                    self._fps = 30.0
        except Exception as e:
            print(f"WARNING: Error opening video source {src}: {e}")
            self._cap = None
            self._fps = 10.0

    def _resolve_source(self, s: str) -> str | int:
        """Convert 'webcam' / integer string / file path / URL to the right type."""
        if s.lower() == "webcam":
            return CAMERA_INDEX
        try:
            idx = int(s)
            return idx
        except ValueError:
            pass
        return s  # file path or RTSP URL

    def _reader(self) -> None:
        """Background thread: continuously read frames and store the latest."""
        is_file = self._is_file_source()
        sleep_time = 1.0 / self._fps if hasattr(self, '_fps') and self._fps > 0 else 1.0 / 30.0
        
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, f"NO SOURCE: {self._source_str}", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                with self._lock:
                    self._latest_frame = frame
                time.sleep(0.1)
                continue

            try:
                ok, frame = self._cap.read()
            except Exception as e:
                print(f"WARNING: OpenCV read exception: {e}")
                ok, frame = False, None
                # Force reopen on next loop if it's a webcam, or just let it loop if it's a file
                if not is_file:
                    self._cap.release()
                    self._cap = None
                
            if not ok:
                if is_file:
                    # Loop video file for demo
                    try:
                        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    except Exception:
                        pass
                    time.sleep(0.1)
                    continue
                else:
                    time.sleep(0.1)
                    continue
            with self._lock:
                self._latest_frame = frame
                
            if is_file:
                time.sleep(sleep_time)

    def _is_file_source(self) -> bool:
        s = self._source_str
        if s.lower() == "webcam":
            return False
        try:
            int(s)
            return False
        except ValueError:
            pass
        return Path(s).exists()


def frames(source: VideoSource) -> Generator[np.ndarray, None, None]:
    """Yield frames from a running VideoSource, blocking until one is available."""
    while True:
        frame = source.read()
        if frame is not None:
            yield frame
        else:
            time.sleep(0.01)
