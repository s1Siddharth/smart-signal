"""
sim/vehicle_sim.py — Top-view 2D virtual traffic simulation.

Maintains virtual vehicle objects per road that:
- Queue behind the stop line when signal is RED
- Advance toward the intersection when GREEN
- Slow/stop when YELLOW (approaching vehicles)
- Maintain following distance
- Cross the intersection and leave

This is a REPRESENTATION layer. Its vehicle count is driven by
the real detection counts from the camera pipeline.

Road layout (top-view, normalized 0–1 space):
  A = North arm  (vehicles approach from top)
  B = East  arm  (vehicles approach from right)
  C = South arm  (vehicles approach from bottom)
  D = West  arm  (vehicles approach from left)
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


# ── Constants ──────────────────────────────────────────────────

ROAD_ARMS = ["A", "B", "C", "D"]

# How many virtual vehicles to maintain per real vehicle
VEHICLE_SCALE: float = 1.0  # 1:1 mapping

# Vehicle physics (normalized units per second)
MAX_SPEED: float = 0.08
ACCEL: float = 0.12
DECEL: float = 0.25
FOLLOW_GAP: float = 0.07   # min gap between vehicles
VEHICLE_LENGTH: float = 0.05

# Stop line distance from intersection center (normalized)
STOP_LINE_DIST: float = 0.32

# How far vehicle travels after crossing before it's removed
EXIT_DIST: float = 0.30

# Yellow slow-down threshold (if within this of stop line when yellow starts)
YELLOW_COMMIT_DIST: float = 0.15


class VehicleState(str, Enum):
    APPROACHING = "approaching"   # moving toward intersection
    STOPPED     = "stopped"       # queued at red
    CROSSING    = "crossing"      # in the intersection box
    EXITING     = "exiting"       # left intersection, fading out


@dataclass
class VirtualVehicle:
    vid: int
    road: str
    # dist = distance from intersection center (positive = approaching)
    # 0 = at center; >0 = queued; negative = past center / exiting
    dist: float
    speed: float = 0.0
    state: VehicleState = VehicleState.APPROACHING
    color: str = "#3DD6F5"

    @property
    def past_stop_line(self) -> bool:
        return self.dist <= STOP_LINE_DIST - 0.02

    @property
    def in_intersection(self) -> bool:
        return self.dist <= 0.10

    @property
    def exited(self) -> bool:
        return self.dist <= -EXIT_DIST


# ── Road arm simulator ──────────────────────────────────────────

class RoadArm:
    """Manages the queue of virtual vehicles for one road arm."""

    def __init__(self, road: str) -> None:
        self.road = road
        self._vehicles: list[VirtualVehicle] = []
        self._next_id = 0
        self._spawn_counter = 0.0

    # ── Public API ─────────────────────────────────────────────

    def sync_count(self, real_count: int) -> None:
        """Add or remove vehicles so count matches real_count."""
        current = len(self._vehicles)
        diff = real_count - current

        if diff > 0:
            for _ in range(diff):
                self._spawn_vehicle()
        elif diff < 0:
            # Remove the furthest-back (highest dist) vehicles first
            removable = sorted(
                [v for v in self._vehicles if v.state in
                 (VehicleState.APPROACHING, VehicleState.STOPPED)],
                key=lambda v: v.dist,
                reverse=True,
            )
            for v in removable[:abs(diff)]:
                self._vehicles.remove(v)

    def tick(
        self,
        dt: float,
        signal: Literal["GREEN", "YELLOW", "RED"],
    ) -> None:
        """Advance physics for all vehicles."""
        # Sort so front vehicles are processed first (lowest dist)
        self._vehicles.sort(key=lambda v: v.dist)

        for i, veh in enumerate(self._vehicles):
            if veh.state == VehicleState.EXITING:
                veh.dist -= MAX_SPEED * dt
                continue

            # Determine the gap limit (next vehicle or stop line)
            if i == 0:
                # Front vehicle
                leader_dist = None
            else:
                leader_dist = self._vehicles[i - 1].dist

            self._advance(veh, dt, signal, leader_dist)

        # Remove vehicles that have fully exited
        self._vehicles = [v for v in self._vehicles if not v.exited]

    def snapshot(self) -> list[dict]:
        """Return serialisable list of vehicle positions for frontend."""
        return [
            {
                "vid": v.vid,
                "road": v.road,
                "dist": round(v.dist, 4),
                "speed": round(v.speed, 4),
                "state": v.state.value,
                "color": v.color,
            }
            for v in self._vehicles
        ]

    @property
    def count(self) -> int:
        return len(self._vehicles)

    # ── Internal ───────────────────────────────────────────────

    def _spawn_vehicle(self) -> None:
        # Spawn behind the last vehicle in the queue (or at max queue depth)
        if self._vehicles:
            back_dist = max(v.dist for v in self._vehicles)
            spawn_dist = back_dist + VEHICLE_LENGTH + FOLLOW_GAP + 0.02
        else:
            spawn_dist = STOP_LINE_DIST + VEHICLE_LENGTH * 0.5

        spawn_dist = min(spawn_dist, STOP_LINE_DIST + 0.40)

        colors = ["#3DD6F5", "#FFB020", "#2EE59D", "#FF4D5E", "#A78BFA",
                  "#FB923C", "#F472B6", "#34D399"]
        color = colors[self._next_id % len(colors)]

        self._vehicles.append(VirtualVehicle(
            vid=self._next_id,
            road=self.road,
            dist=spawn_dist,
            speed=0.0,
            state=VehicleState.STOPPED,
            color=color,
        ))
        self._next_id += 1

    def _advance(
        self,
        veh: VirtualVehicle,
        dt: float,
        signal: str,
        leader_dist: float | None,
    ) -> None:
        """Update one vehicle's speed and position."""

        # Compute safe following distance
        if leader_dist is not None:
            gap_to_leader = veh.dist - leader_dist - VEHICLE_LENGTH
            safe_ahead = max(gap_to_leader - FOLLOW_GAP, 0.0)
        else:
            safe_ahead = 1.0  # no vehicle ahead

        # Compute distance to stop line
        gap_to_stop = veh.dist - STOP_LINE_DIST

        must_stop_at_line = False
        if signal == "RED":
            must_stop_at_line = gap_to_stop > 0  # haven't crossed yet
        elif signal == "YELLOW":
            # Commit if already past the commit point
            if gap_to_stop > 0 and veh.dist > STOP_LINE_DIST + YELLOW_COMMIT_DIST:
                must_stop_at_line = True
            # If already committed (close to stop line), continue through

        # Choose target speed
        if must_stop_at_line:
            # Decelerate toward stop line
            if gap_to_stop > 0:
                braking_dist = veh.speed ** 2 / (2 * DECEL)
                if braking_dist >= gap_to_stop or gap_to_stop < 0.02:
                    target_speed = 0.0
                    veh.state = VehicleState.STOPPED
                else:
                    target_speed = min(MAX_SPEED, math.sqrt(2 * DECEL * max(gap_to_stop, 0)))
                    veh.state = VehicleState.APPROACHING
            else:
                target_speed = 0.0
                veh.state = VehicleState.STOPPED
        else:
            # Move forward — constrained by gap to leader
            target_speed = min(MAX_SPEED, safe_ahead / dt if dt > 0 else MAX_SPEED)
            if veh.state == VehicleState.STOPPED:
                veh.state = VehicleState.APPROACHING

        # Apply acceleration / deceleration
        if target_speed > veh.speed:
            veh.speed = min(veh.speed + ACCEL * dt, target_speed)
        else:
            veh.speed = max(veh.speed - DECEL * dt, target_speed)

        veh.speed = max(0.0, veh.speed)

        # Move vehicle
        veh.dist -= veh.speed * dt

        # State transitions
        if veh.dist <= 0.0 and veh.state not in (VehicleState.CROSSING, VehicleState.EXITING):
            veh.state = VehicleState.CROSSING
        if veh.dist <= -0.05:
            veh.state = VehicleState.EXITING


# ── Main simulator ─────────────────────────────────────────────

class TrafficSimulator:
    """
    Top-level virtual traffic simulator.
    Drives per-road RoadArm instances from real camera counts.
    """

    def __init__(self) -> None:
        self._arms: dict[str, RoadArm] = {r: RoadArm(r) for r in ROAD_ARMS}
        self._last_tick = time.monotonic()

    def update(
        self,
        counts: dict[str, int],
        lights: dict[str, str],
        demo_speed: float = 1.0,
    ) -> None:
        """Call every backend tick with live counts and signal states."""
        now = time.monotonic()
        dt = (now - self._last_tick) * demo_speed
        self._last_tick = now

        dt = min(dt, 0.25)  # cap max dt to prevent tunnelling

        for road, arm in self._arms.items():
            real_count = counts.get(road, 0)
            arm.sync_count(real_count)
            signal = lights.get(road, "RED")
            arm.tick(dt, signal)  # type: ignore[arg-type]

    def snapshot(self) -> dict:
        """Return full simulation state for broadcast."""
        return {
            road: arm.snapshot()
            for road, arm in self._arms.items()
        }
