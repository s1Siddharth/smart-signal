"""
control/controller.py — Signal state machine.

Pure logic module: NO vision imports. Fully unit-testable with fake counts.

Roads: A, B, C, D
Phases: P1 = {A, C}  (opposite pair)
        P2 = {B, D}

States: GREEN(phase) → YELLOW → ALL_RED → GREEN(next)
        EMERGENCY(road) can interrupt from any state (after yellow safety)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable


class SignalState(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ALL_RED = "ALL_RED"
    EMERGENCY = "EMERGENCY"


@dataclass
class PhaseSnapshot:
    """Input to the controller tick — what the vision layer reports."""
    counts: dict[str, int]           # road → smoothed vehicle count
    densities: dict[str, float]      # road → weighted density
    ambulance: dict[str, bool]       # road → ambulance present?


@dataclass
class TransitionEvent:
    timestamp: float
    from_state: str
    to_state: str
    from_phase: str
    to_phase: str
    reason: str
    green_duration: float
    counts_snapshot: dict[str, int]


class SignalController:
    """
    State machine for adaptive signal control.

    Args:
        phases: mapping phase_id → list of road IDs
        config: dict of tunable params (mirrors config.py defaults)
        clock:  callable returning monotonic seconds (injectable for tests)
        on_transition: callback called with TransitionEvent on every state change
    """

    def __init__(
        self,
        phases: dict[str, list[str]],
        config: dict,
        clock: Callable[[], float] | None = None,
        on_transition: Callable[[TransitionEvent], None] | None = None,
    ) -> None:
        self._phases = phases
        self._cfg = config
        self._clock = clock or time.monotonic
        self._on_transition = on_transition

        # Ordered list of phase IDs for round-robin
        self._phase_order = list(phases.keys())

        # Current state
        self._state: SignalState = SignalState.GREEN
        self._current_phase_idx: int = 0
        self._state_entered_at: float = self._clock()
        self._phase_entered_at: float = self._clock()

        # Emergency
        self._emergency_road: str | None = None

        # Per-road waiting time tracker
        self._road_last_green_at: dict[str, float] = {
            r: self._clock()
            for roads in phases.values()
            for r in roads
        }

        # Empty-road continuous timer
        self._empty_since: dict[str, float | None] = {
            r: None for roads in phases.values() for r in roads
        }

        # Transition log
        self._log: list[TransitionEvent] = []

    # ── Public API ──────────────────────────────────────────────

    @property
    def state(self) -> SignalState:
        return self._state

    @property
    def current_phase(self) -> str:
        return self._phase_order[self._current_phase_idx]

    @property
    def current_roads(self) -> list[str]:
        return self._phases[self.current_phase]

    @property
    def elapsed_s(self) -> float:
        """Seconds since the current GREEN phase started (scaled by DEMO_SPEED)."""
        raw = self._clock() - self._phase_entered_at
        return raw * self._cfg.get("DEMO_SPEED", 1)

    @property
    def lights(self) -> dict[str, str]:
        """Current light color per road."""
        green_roads = set(self._phases.get(self.current_phase, []))
        result: dict[str, str] = {}
        all_roads = [r for roads in self._phases.values() for r in roads]
        for road in all_roads:
            if self._state == SignalState.EMERGENCY:
                if road == self._emergency_road:
                    result[road] = "GREEN"
                else:
                    result[road] = "RED"
            elif self._state == SignalState.YELLOW:
                result[road] = "YELLOW" if road in green_roads else "RED"
            elif self._state == SignalState.ALL_RED:
                result[road] = "RED"
            else:  # GREEN
                result[road] = "GREEN" if road in green_roads else "RED"
        return result

    @property
    def transition_log(self) -> list[TransitionEvent]:
        return list(self._log[-50:])  # last 50 entries

    def trigger_emergency(self, road: str) -> None:
        """External call to trigger ambulance preemption."""
        self._emergency_road = road
        # Will be handled on next tick

    def waiting_s(self, road: str) -> float:
        """Seconds since this road last had green (approx)."""
        return self._clock() - self._road_last_green_at.get(road, self._clock())

    # ── Main tick ───────────────────────────────────────────────

    def tick(self, snapshot: PhaseSnapshot) -> None:
        """Call ~5 Hz. Updates state machine based on current counts."""
        now = self._clock()
        speed = self._cfg.get("DEMO_SPEED", 1)
        elapsed = (now - self._phase_entered_at) * speed
        state_elapsed = (now - self._state_entered_at) * speed

        # Update empty-road timers
        for road, count in snapshot.counts.items():
            if count == 0:
                if self._empty_since[road] is None:
                    self._empty_since[road] = now
            else:
                self._empty_since[road] = None

        if self._state == SignalState.GREEN:
            self._tick_green(snapshot, elapsed, now)
        elif self._state == SignalState.YELLOW:
            if state_elapsed >= self._cfg["YELLOW_S"]:
                self._transition(SignalState.ALL_RED, "YELLOW_DONE", snapshot.counts)
        elif self._state == SignalState.ALL_RED:
            if state_elapsed >= self._cfg["ALL_RED_S"]:
                # Advance to next phase
                self._advance_phase()
                self._transition(SignalState.GREEN, "ALL_RED_DONE", snapshot.counts)
        elif self._state == SignalState.EMERGENCY:
            self._tick_emergency(snapshot, state_elapsed, now)

    # ── Internal ────────────────────────────────────────────────

    def _tick_green(self, snap: PhaseSnapshot, elapsed: float, now: float) -> None:
        cfg = self._cfg
        current_roads = self.current_roads
        other_phase = self._other_phase()
        other_roads = self._phases[other_phase]

        current_density = sum(snap.densities.get(r, 0) for r in current_roads)
        other_density = sum(snap.densities.get(r, 0) for r in other_roads)
        current_count = sum(snap.counts.get(r, 0) for r in current_roads)
        other_count = sum(snap.counts.get(r, 0) for r in other_roads)

        # 1. Emergency check (other phase)
        for road in other_roads:
            if snap.ambulance.get(road, False):
                self._emergency_road = road
                self._transition(SignalState.YELLOW, "EMERGENCY_START", snap.counts)
                return

        # 2. Emergency on current phase — stay green, hold timer
        for road in current_roads:
            if snap.ambulance.get(road, False):
                self._emergency_road = road
                self._state = SignalState.EMERGENCY
                self._state_entered_at = now
                return

        # 3. Max green reached
        if elapsed >= cfg["MAX_GREEN_S"]:
            self._transition(SignalState.YELLOW, "MAX_REACHED", snap.counts)
            return

        # 4. Early switch rules (only after MIN_GREEN_S)
        if elapsed >= cfg["MIN_GREEN_S"] and other_count > 0:
            # EMPTY_EARLY: current phase empty for EMPTY_CONFIRM_S
            current_empty = all(
                self._empty_since.get(r) is not None and
                (now - (self._empty_since[r] or now)) * cfg.get("DEMO_SPEED", 1)
                >= cfg["EMPTY_CONFIRM_S"]
                for r in current_roads
            )
            if current_empty and current_count == 0:
                self._transition(SignalState.YELLOW, "EMPTY_EARLY", snap.counts)
                return

            # HIGHER_DEMAND: other phase density ≥ 2× current and current not empty
            if elapsed >= cfg.get("EMPTY_CUTOFF_S", 35):
                if other_density >= 2 * max(current_density, 0.1) and current_count > 0:
                    self._transition(SignalState.YELLOW, "HIGHER_DEMAND", snap.counts)
                    return

        # 5. Fairness / anti-starvation
        for road in other_roads:
            wait = (now - self._road_last_green_at.get(road, now)) * cfg.get("DEMO_SPEED", 1)
            if wait >= cfg["STARVATION_WAIT_S"]:
                self._transition(SignalState.YELLOW, "FAIRNESS", snap.counts)
                return

        # 6. Both phases empty → stay green (no pointless switch)

    def _tick_emergency(self, snap: PhaseSnapshot, state_elapsed: float, now: float) -> None:
        cfg = self._cfg
        road = self._emergency_road
        if road is None:
            self._transition(SignalState.YELLOW, "EMERGENCY_CLEAR", snap.counts)
            return

        # Check if ambulance has left the ROI for AMBU_CLEAR_S
        ambu_present = snap.ambulance.get(road, False)
        if not ambu_present:
            if self._empty_since.get(road) is not None:
                clear_duration = (now - (self._empty_since[road] or now)) * cfg.get("DEMO_SPEED", 1)
                if clear_duration >= cfg.get("AMBU_CLEAR_S", 3):
                    self._emergency_road = None
                    self._transition(SignalState.YELLOW, "EMERGENCY_CLEAR", snap.counts)
                    return

        # Timeout
        if state_elapsed >= cfg.get("AMBU_HOLD_S", 30):
            self._emergency_road = None
            self._transition(SignalState.YELLOW, "EMERGENCY_TIMEOUT", snap.counts)

    def _other_phase(self) -> str:
        other_idx = (self._current_phase_idx + 1) % len(self._phase_order)
        return self._phase_order[other_idx]

    def _advance_phase(self) -> None:
        if self._emergency_road is not None:
            # Find which phase contains the emergency road
            for i, (pid, roads) in enumerate(self._phases.items()):
                if self._emergency_road in roads:
                    self._current_phase_idx = i
                    self._emergency_road = None
                    return
        self._current_phase_idx = (self._current_phase_idx + 1) % len(self._phase_order)

    def _transition(self, new_state: SignalState, reason: str, counts: dict[str, int]) -> None:
        now = self._clock()
        ev = TransitionEvent(
            timestamp=now,
            from_state=self._state.value,
            to_state=new_state.value,
            from_phase=self.current_phase,
            to_phase=self._other_phase() if new_state == SignalState.YELLOW else self.current_phase,
            reason=reason,
            green_duration=self.elapsed_s,
            counts_snapshot=dict(counts),
        )
        self._log.append(ev)
        if self._on_transition:
            self._on_transition(ev)

        # Update last-green timestamps when leaving green
        if self._state == SignalState.GREEN and new_state == SignalState.YELLOW:
            for road in self.current_roads:
                self._road_last_green_at[road] = now

        self._state = new_state
        self._state_entered_at = now
        if new_state == SignalState.GREEN:
            self._phase_entered_at = now
