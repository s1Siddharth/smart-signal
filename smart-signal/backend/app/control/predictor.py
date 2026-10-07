"""
control/predictor.py — Clearance-time estimator.

Formula:
  clear_time = STARTUP_LOST_S + Σ(weight_i) × SECONDS_PER_VEHICLE
  clear_time  = min(clear_time, MAX_GREEN_S - elapsed_s)

Improves over time using an exponential moving average of observed discharge rate.
"""
from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass

from app.config import (
    MAX_GREEN_S,
    SECONDS_PER_VEHICLE,
    STARTUP_LOST_S,
    VEHICLE_WEIGHTS,
)


@dataclass
class Prediction:
    clear_s: float       # estimated seconds to clear the current queue
    confidence: str      # "high" | "low"
    vehicle_count: int


class ClearancePredictor:
    """
    Predicts how long the current green phase queue will take to clear.
    """

    def __init__(self) -> None:
        # EMA of discharge rate (vehicles/second) per road
        self._ema_discharge: dict[str, float] = {}
        self._prev_counts: dict[str, int] = {}
        self._prev_ts: float = time.monotonic()
        # History of recent counts for confidence estimation
        self._count_history: dict[str, deque[int]] = {}

    def predict(
        self,
        phase_roads: list[str],
        counts: dict[str, int],
        densities: dict[str, float],
        elapsed_s: float,
    ) -> Prediction:
        """Predict clearance time for the active phase."""
        # Use sum of weighted densities across phase roads
        total_density = sum(densities.get(r, 0.0) for r in phase_roads)
        total_count = sum(counts.get(r, 0) for r in phase_roads)

        # Base formula
        spv = self._effective_spv(phase_roads)
        raw_clear = STARTUP_LOST_S + total_density * spv
        remaining_cap = max(0.0, MAX_GREEN_S - elapsed_s)
        clear_s = min(raw_clear, remaining_cap)

        # Confidence: low if count changed > 30% in recent history
        conf = self._confidence(phase_roads, counts)

        return Prediction(
            clear_s=round(clear_s, 1),
            confidence=conf,
            vehicle_count=total_count,
        )

    def update_discharge(self, road: str, count_now: int) -> None:
        """Call each frame to update the discharge-rate EMA."""
        now = time.monotonic()
        dt = now - self._prev_ts
        if dt <= 0:
            return
        prev = self._prev_counts.get(road, count_now)
        discharged = max(0, prev - count_now) / dt  # vehicles/second

        alpha = 0.1  # EMA smoothing factor
        prev_ema = self._ema_discharge.get(road, discharged)
        self._ema_discharge[road] = alpha * discharged + (1 - alpha) * prev_ema
        self._prev_counts[road] = count_now
        self._prev_ts = now

        # Track recent count history
        hist = self._count_history.setdefault(road, deque(maxlen=15))
        hist.append(count_now)

    # ── Internal ────────────────────────────────────────────────

    def _effective_spv(self, roads: list[str]) -> float:
        """Use EMA discharge rate if available, else config default."""
        rates = [
            1 / r for r in (self._ema_discharge.get(road) for road in roads)
            if r and r > 0
        ]
        if rates:
            return sum(rates) / len(rates)
        return SECONDS_PER_VEHICLE

    def _confidence(self, roads: list[str], current_counts: dict[str, int]) -> str:
        for road in roads:
            hist = self._count_history.get(road)
            if hist and len(hist) >= 3:
                recent = list(hist)[-3:]
                if max(recent) > 0:
                    variation = (max(recent) - min(recent)) / max(recent)
                    if variation > 0.30:
                        return "low"
        return "high"
