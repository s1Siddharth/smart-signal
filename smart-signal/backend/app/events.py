"""
events.py — Event bus + commuter notification messages.

Generates human-readable, rate-limited notifications for the Commuter page.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock

_RATE_LIMIT_S = 15.0  # Minimum seconds between same-type messages for same road
_MAX_QUEUE = 50


@dataclass
class Notification:
    id: int
    level: str           # "info" | "warning" | "alert"
    text: str
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """Generates and stores notifications, deduplicates similar events."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._queue: deque[Notification] = deque(maxlen=_MAX_QUEUE)
        self._counter = 0
        self._last_sent: dict[str, float] = {}  # key → timestamp

    # ── Public ──────────────────────────────────────────────────

    def recent(self, n: int = 20) -> list[Notification]:
        with self._lock:
            return list(self._queue)[-n:]

    def on_switch(self, from_road: str, to_road: str, reason: str, saved_s: float) -> None:
        if reason == "EMPTY_EARLY":
            self._emit(
                f"road-{from_road}-empty",
                "info",
                f"Road {from_road} cleared early → Road {to_road} now green."
                + (f" Saved ~{int(saved_s)} s." if saved_s > 0 else ""),
            )
        elif reason == "MAX_REACHED":
            self._emit(f"road-{to_road}-green", "info", f"Road {to_road}: green now (max time reached).")
        elif reason == "FAIRNESS":
            self._emit(f"road-{to_road}-fairness", "warning", f"Road {to_road}: granted green (fairness rule).")
        elif reason == "HIGHER_DEMAND":
            self._emit(f"road-{to_road}-demand", "info", f"Road {to_road}: high demand, switching early.")

    def on_ambulance(self, road: str) -> None:
        self._emit(f"ambu-{road}", "alert", f"🚨 Ambulance on Road {road}. Priority green active.")

    def on_ambulance_clear(self, road: str) -> None:
        self._emit(f"ambu-clear-{road}", "info", f"Ambulance cleared Road {road}. Normal cycle resumed.")

    def on_eta(self, road: str, eta_s: float) -> None:
        self._emit(f"eta-{road}", "info", f"Road {road}: turns green in ~{int(eta_s)} s.", rate_s=30)

    def on_heavy_traffic(self, road: str) -> None:
        self._emit(f"heavy-{road}", "warning", f"Heavy traffic on Road {road}.", rate_s=60)

    # ── Internal ────────────────────────────────────────────────

    def _emit(self, key: str, level: str, text: str, rate_s: float = _RATE_LIMIT_S) -> None:
        now = time.monotonic()
        last = self._last_sent.get(key, 0.0)
        if now - last < rate_s:
            return
        with self._lock:
            self._counter += 1
            n = Notification(id=self._counter, level=level, text=text)
            self._queue.append(n)
            self._last_sent[key] = now
