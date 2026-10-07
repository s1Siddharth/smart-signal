"""
tests/test_controller.py — Unit tests for the signal controller.
All tests use a fake monotonic clock for full determinism.
"""
from __future__ import annotations

import pytest
from app.control.controller import PhaseSnapshot, SignalController, SignalState

PHASES = {"P1": ["A", "C"], "P2": ["B", "D"]}

DEFAULT_CFG = {
    "MAX_GREEN_S": 120,
    "EMPTY_CUTOFF_S": 35,
    "MIN_GREEN_S": 10,
    "YELLOW_S": 3,
    "ALL_RED_S": 1,
    "EMPTY_CONFIRM_S": 3,
    "STARVATION_WAIT_S": 150,
    "DEMO_SPEED": 1,
    "AMBU_HOLD_S": 30,
    "AMBU_CLEAR_S": 3,
}


class FakeClock:
    def __init__(self, t: float = 0.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def make_ctrl(cfg: dict | None = None, clock: FakeClock | None = None) -> tuple[SignalController, FakeClock]:
    clk = clock or FakeClock()
    ctrl = SignalController(phases=PHASES, config=cfg or dict(DEFAULT_CFG), clock=clk)
    return ctrl, clk


def snap(
    counts: dict | None = None,
    densities: dict | None = None,
    ambulance: dict | None = None,
) -> PhaseSnapshot:
    counts = counts or {"A": 0, "B": 0, "C": 0, "D": 0}
    densities = densities or {r: float(v) for r, v in counts.items()}
    ambulance = ambulance or {"A": False, "B": False, "C": False, "D": False}
    return PhaseSnapshot(counts=counts, densities=densities, ambulance=ambulance)


def tick_to(ctrl: SignalController, clk: FakeClock, target_s: float, step: float = 1.0):
    """Advance clock and tick controller to reach target_s elapsed."""
    while clk.t < target_s:
        clk.advance(step)
        ctrl.tick(snap())


# ── Test 1: EMPTY_EARLY switch ──────────────────────────────────

def test_empty_early_switch():
    """Green road empty for EMPTY_CONFIRM_S at t>=EMPTY_CUTOFF_S → EMPTY_EARLY switch."""
    ctrl, clk = make_ctrl()
    assert ctrl.current_phase == "P1"

    # At t=36, current phase (P1: A,C) has 0 vehicles, P2 has 5
    clk.advance(36)
    s = snap(counts={"A": 0, "B": 5, "C": 0, "D": 0},
             densities={"A": 0, "B": 5, "C": 0, "D": 0})
    # Seed empty-since for A and C
    ctrl._empty_since["A"] = clk.t - 4  # 4 s ago
    ctrl._empty_since["C"] = clk.t - 4
    ctrl.tick(s)

    assert ctrl.state == SignalState.YELLOW, f"Expected YELLOW, got {ctrl.state}"
    assert ctrl.transition_log[-1].reason == "EMPTY_EARLY"


# ── Test 2: No switch before EMPTY_CUTOFF_S ─────────────────────

def test_no_early_switch_before_cutoff():
    """Green road empty at t=20 (< EMPTY_CUTOFF_S=35) → should NOT switch."""
    ctrl, clk = make_ctrl()
    clk.advance(20)
    ctrl._empty_since["A"] = clk.t - 5
    ctrl._empty_since["C"] = clk.t - 5
    s = snap(counts={"A": 0, "B": 3, "C": 0, "D": 0},
             densities={"A": 0, "B": 3, "C": 0, "D": 0})
    ctrl.tick(s)
    assert ctrl.state == SignalState.GREEN


# ── Test 3: MAX_REACHED ─────────────────────────────────────────

def test_max_reached():
    """Busy road stays green until 120 s, then MAX_REACHED."""
    ctrl, clk = make_ctrl()
    # Advance to just before max
    clk.t = 119
    s = snap(counts={"A": 5, "B": 2, "C": 3, "D": 1},
             densities={"A": 5, "B": 2, "C": 3, "D": 1})
    ctrl.tick(s)
    assert ctrl.state == SignalState.GREEN  # not yet

    clk.advance(2)  # now at 121 s
    ctrl.tick(s)
    assert ctrl.state == SignalState.YELLOW
    assert ctrl.transition_log[-1].reason == "MAX_REACHED"


# ── Test 4: Both roads empty → no switch ───────────────────────

def test_both_empty_no_switch():
    """Both phases empty → stay green, no pointless switching."""
    ctrl, clk = make_ctrl()
    clk.advance(40)
    ctrl._empty_since["A"] = clk.t - 10
    ctrl._empty_since["C"] = clk.t - 10
    s = snap()  # all zeros
    ctrl.tick(s)
    assert ctrl.state == SignalState.GREEN


# ── Test 5: FAIRNESS ────────────────────────────────────────────

def test_fairness_switch():
    """Waiting road exceeds STARVATION_WAIT_S → forced FAIRNESS switch."""
    ctrl, clk = make_ctrl()
    # Force road B/D waiting time beyond threshold
    ctrl._road_last_green_at["B"] = clk.t - 160
    ctrl._road_last_green_at["D"] = clk.t - 160
    clk.advance(1)
    s = snap(counts={"A": 3, "B": 1, "C": 2, "D": 1},
             densities={"A": 3, "B": 1, "C": 2, "D": 1})
    ctrl.tick(s)
    assert ctrl.state == SignalState.YELLOW
    assert ctrl.transition_log[-1].reason == "FAIRNESS"


# ── Test 6: Ambulance on red road → EMERGENCY ──────────────────

def test_ambulance_red_road():
    """Ambulance on Road D (red) → YELLOW → ALL_RED → GREEN → EMERGENCY."""
    ctrl, clk = make_ctrl()
    assert ctrl.current_phase == "P1"  # A,C green

    s = snap(ambulance={"A": False, "B": False, "C": False, "D": True})
    ctrl.tick(s)
    assert ctrl.state == SignalState.YELLOW

    # Advance through yellow
    clk.advance(4)
    ctrl.tick(s)
    assert ctrl.state == SignalState.ALL_RED

    clk.advance(2)
    ctrl.tick(s)
    assert ctrl.state == SignalState.GREEN
    
    # Tick again so the green phase registers the ambulance and triggers EMERGENCY
    ctrl.tick(s)
    assert ctrl.state == SignalState.EMERGENCY

    # Emergency road (D) should be green now, others red
    lights = ctrl.lights
    assert lights["D"] == "GREEN"
    assert lights["A"] == "RED"
    assert lights["B"] == "RED"


# ── Test 7: Ambulance on green road → stay green, hold ─────────

def test_ambulance_on_green_road():
    """Ambulance on Road A (already green) → stays GREEN, enters EMERGENCY."""
    ctrl, clk = make_ctrl()
    s = snap(ambulance={"A": True, "B": False, "C": False, "D": False})
    ctrl.tick(s)
    assert ctrl.state == SignalState.EMERGENCY


# ── Test 8: Count flicker does not cause switch ─────────────────

def test_count_flicker_no_switch():
    """Flickering count 0,3,0,3 on green phase: should not trigger EMPTY_EARLY."""
    ctrl, clk = make_ctrl()
    clk.advance(36)
    # Flicker — never sustained 3 s empty
    for _ in range(10):
        ctrl._empty_since["A"] = None
        ctrl._empty_since["C"] = None
        ctrl.tick(snap(counts={"A": 3, "B": 2, "C": 2, "D": 1}))
        ctrl.tick(snap(counts={"A": 0, "B": 2, "C": 0, "D": 1}))
        clk.advance(0.2)
    assert ctrl.state == SignalState.GREEN


# ── Test 9: Predictor never exceeds remaining cap ──────────────

def test_predictor_cap():
    from app.control.predictor import ClearancePredictor
    pred = ClearancePredictor()
    # 10 vehicles, 2 s/vehicle = 20 s raw. Elapsed = 110 → remaining = 10
    result = pred.predict(["A", "C"], {"A": 5, "C": 5}, {"A": 5.0, "C": 5.0}, elapsed_s=110)
    assert result.clear_s <= 10.0


# ── Test 10: Demo speed scales timers ──────────────────────────

def test_demo_speed():
    cfg = dict(DEFAULT_CFG)
    cfg["DEMO_SPEED"] = 10
    ctrl, clk = make_ctrl(cfg=cfg)
    # At real 12 s with 10× speed → effective 120 s → MAX_REACHED
    clk.advance(12)
    s = snap(counts={"A": 5, "B": 2, "C": 3, "D": 1},
             densities={"A": 5, "B": 2, "C": 3, "D": 1})
    ctrl.tick(s)
    assert ctrl.state == SignalState.YELLOW
    assert ctrl.transition_log[-1].reason == "MAX_REACHED"
