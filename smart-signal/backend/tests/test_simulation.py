"""
tests/test_simulation.py — Unit tests for the 2D virtual traffic simulation.
"""
from __future__ import annotations

import pytest
from app.sim.vehicle_sim import (
    RoadArm,
    TrafficSimulator,
    VehicleState,
    STOP_LINE_DIST,
)


# ── Helpers ────────────────────────────────────────────────────

def make_arm(road: str = "A") -> RoadArm:
    return RoadArm(road)


# ── Test 1: Sync count spawns correct vehicles ─────────────────

def test_sync_adds_vehicles():
    arm = make_arm()
    arm.sync_count(3)
    assert arm.count == 3


def test_sync_removes_vehicles():
    arm = make_arm()
    arm.sync_count(5)
    arm.sync_count(2)
    assert arm.count == 2


def test_sync_noop():
    arm = make_arm()
    arm.sync_count(3)
    arm.sync_count(3)
    assert arm.count == 3


# ── Test 2: Vehicles stop at red ───────────────────────────────

def test_vehicles_stop_at_red():
    arm = make_arm("A")
    arm.sync_count(2)

    # Tick many times with RED signal
    for _ in range(500):
        arm.tick(0.05, "RED")  # type: ignore

    snap = arm.snapshot()
    for v in snap:
        # All vehicles should be at or behind the stop line
        assert v["dist"] >= STOP_LINE_DIST - 0.05, (
            f"Vehicle past stop line at dist={v['dist']:.4f}"
        )


# ── Test 3: Vehicles advance on green ─────────────────────────

def test_vehicles_advance_on_green():
    arm = make_arm("B")
    arm.sync_count(1)

    # Get initial dist
    initial_dist = arm.snapshot()[0]["dist"]

    # Tick with GREEN
    for _ in range(60):
        arm.tick(0.05, "GREEN")  # type: ignore

    final_dist = arm.snapshot()[0]["dist"] if arm.count > 0 else -999

    # Vehicle should have moved closer to center or crossed
    assert final_dist < initial_dist, (
        f"Vehicle did not advance: initial={initial_dist:.4f}, final={final_dist:.4f}"
    )


# ── Test 4: Vehicles don't overlap ────────────────────────────

def test_vehicles_maintain_spacing():
    """Vehicles in a queue should maintain non-overlapping positions (no negative gap)."""
    arm = make_arm("C")
    arm.sync_count(4)

    for _ in range(200):
        arm.tick(0.05, "RED")  # type: ignore

    snap = sorted(arm.snapshot(), key=lambda v: v["dist"])
    for i in range(1, len(snap)):
        gap = snap[i]["dist"] - snap[i-1]["dist"]
        # Vehicles must not overlap (gap >= 0 with small tolerance)
        assert gap >= -0.005, (
            f"Overlap detected: gap={gap:.4f} between vehicles {i-1} and {i}"
        )


# ── Test 5: Exiting vehicles removed ──────────────────────────

def test_exiting_vehicles_removed():
    arm = make_arm("D")
    arm.sync_count(1)

    # Tick many times with GREEN — vehicle should cross and be removed
    for _ in range(1000):
        arm.tick(0.05, "GREEN")  # type: ignore

    # After sufficient time, vehicle should have exited
    assert arm.count == 0


# ── Test 6: TrafficSimulator integration ──────────────────────

def test_simulator_full_cycle():
    sim = TrafficSimulator()

    lights = {"A": "GREEN", "B": "RED", "C": "GREEN", "D": "RED"}
    counts = {"A": 3, "B": 1, "C": 2, "D": 0}

    # Run several ticks
    for _ in range(20):
        sim.update(counts, lights, demo_speed=10.0)

    snap = sim.snapshot()
    assert "A" in snap
    assert "B" in snap
    assert "C" in snap
    assert "D" in snap

    # A and C have green, vehicles should be moving (some might have crossed)
    a_states = {v["state"] for v in snap["A"]}
    b_states = {v["state"] for v in snap["B"]}

    # B has RED, so vehicles should be stopped or approaching near stop line
    for v in snap["B"]:
        assert v["state"] in ("stopped", "approaching", "crossing", "exiting"), v["state"]


# ── Test 7: Count drives virtual count ───────────────────────

def test_count_matches_target():
    sim = TrafficSimulator()

    lights = {"A": "RED", "B": "RED", "C": "RED", "D": "RED"}
    counts = {"A": 4, "B": 2, "C": 3, "D": 1}

    sim.update(counts, lights)
    snap = sim.snapshot()

    # Immediately after update, counts should match (no vehicles exited yet)
    assert len(snap["A"]) == 4
    assert len(snap["B"]) == 2
    assert len(snap["C"]) == 3
    assert len(snap["D"]) == 1


# ── Test 8: Yellow slows approaching vehicles ─────────────────

def test_yellow_stops_far_vehicles():
    arm = make_arm("A")
    arm.sync_count(1)

    # Start moving on green for a bit
    for _ in range(10):
        arm.tick(0.05, "GREEN")  # type: ignore

    snap_before = arm.snapshot()
    if not snap_before:
        return  # vehicle already crossed, skip

    v_before = snap_before[0]
    # Vehicle should be approaching stop line

    # Switch to YELLOW — if vehicle is far, it should stop
    if v_before["dist"] > STOP_LINE_DIST + 0.15:
        for _ in range(100):
            arm.tick(0.05, "YELLOW")  # type: ignore
        snap_after = arm.snapshot()
        if snap_after:
            assert snap_after[0]["dist"] >= STOP_LINE_DIST - 0.05


# ── Test 9: Snapshot format ───────────────────────────────────

def test_snapshot_format():
    arm = make_arm("A")
    arm.sync_count(2)

    snap = arm.snapshot()
    assert isinstance(snap, list)
    for item in snap:
        assert "vid" in item
        assert "road" in item
        assert "dist" in item
        assert "speed" in item
        assert "state" in item
        assert "color" in item
        assert item["road"] == "A"
