"""
sim/fixed_vs_adaptive.py — Shadow fixed-timer controller.

Runs in parallel with the adaptive controller, fed the same live counts.
Tracks:
  - seconds of green given to an empty road while the other had vehicles
  - cumulative waiting vehicle-seconds saved vs fixed timer
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ComparisonStats:
    fixed_wasted_green_s: float = 0.0     # green time wasted by fixed timer on empty roads
    adaptive_wasted_green_s: float = 0.0  # green time wasted by adaptive (should be ~0)
    fixed_wait_vehicle_s: float = 0.0     # cumulative waiting vehicle-seconds under fixed
    adaptive_wait_vehicle_s: float = 0.0  # cumulative waiting vehicle-seconds under adaptive
    saved_green_s: float = 0.0            # fixed_wasted - adaptive_wasted


class FixedVsAdaptive:
    """Shadow fixed-timer controller for comparison analytics."""

    def __init__(
        self,
        phases: dict[str, list[str]],
        fixed_green_s: float = 120.0,
        clock: None = None,
    ) -> None:
        self._phases = phases
        self._phase_order = list(phases.keys())
        self._fixed_green_s = fixed_green_s
        self._clock = clock or time.monotonic

        self._fixed_idx = 0
        self._fixed_phase_start = self._clock()
        self._stats = ComparisonStats()
        self._last_tick = self._clock()

    # ── Public ──────────────────────────────────────────────────

    @property
    def stats(self) -> ComparisonStats:
        return self._stats

    def tick(
        self,
        counts: dict[str, int],
        adaptive_green_roads: list[str],
        demo_speed: float = 1.0,
    ) -> None:
        """Call every tick with the current counts and adaptive green roads."""
        now = self._clock()
        dt = (now - self._last_tick) * demo_speed
        self._last_tick = now

        # Fixed controller phase
        fixed_elapsed = (now - self._fixed_phase_start) * demo_speed
        fixed_green_roads = self._phases[self._phase_order[self._fixed_idx]]
        fixed_red_roads = [
            r for phase_roads in self._phases.values()
            for r in phase_roads
            if r not in fixed_green_roads
        ]

        if fixed_elapsed >= self._fixed_green_s:
            self._fixed_idx = (self._fixed_idx + 1) % len(self._phase_order)
            self._fixed_phase_start = now

        # Wasted green: green to empty road while red road has vehicles
        for road in fixed_green_roads:
            if counts.get(road, 0) == 0:
                # Any red road with vehicles?
                any_red_busy = any(counts.get(r, 0) > 0 for r in fixed_red_roads)
                if any_red_busy:
                    self._stats.fixed_wasted_green_s += dt

        for road in adaptive_green_roads:
            all_other_roads = [
                r for phase_roads in self._phases.values()
                for r in phase_roads
                if r not in adaptive_green_roads
            ]
            if counts.get(road, 0) == 0:
                any_other_busy = any(counts.get(r, 0) > 0 for r in all_other_roads)
                if any_other_busy:
                    self._stats.adaptive_wasted_green_s += dt

        # Waiting vehicle-seconds
        for road in fixed_red_roads:
            self._stats.fixed_wait_vehicle_s += counts.get(road, 0) * dt

        adaptive_red_roads = [
            r for phase_roads in self._phases.values()
            for r in phase_roads
            if r not in adaptive_green_roads
        ]
        for road in adaptive_red_roads:
            self._stats.adaptive_wait_vehicle_s += counts.get(road, 0) * dt

        # Saved = wasted green time recovered
        self._stats.saved_green_s = max(
            0.0, self._stats.fixed_wasted_green_s - self._stats.adaptive_wasted_green_s
        )
