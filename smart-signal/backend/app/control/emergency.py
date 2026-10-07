"""
control/emergency.py — Emergency preemption coordination.

Bridges the ambulance detector output and the signal controller.
"""
from __future__ import annotations

from app.control.controller import SignalController


class EmergencyCoordinator:
    """Calls controller.trigger_emergency when an ambulance is detected."""

    def __init__(self, controller: SignalController) -> None:
        self._ctrl = controller
        self._last_emergency: dict[str, bool] = {}

    def update(self, ambulance: dict[str, bool]) -> None:
        """Call every tick with the latest ambulance flags per road."""
        for road, present in ambulance.items():
            was_present = self._last_emergency.get(road, False)
            if present and not was_present:
                # Rising edge — trigger preemption
                self._ctrl.trigger_emergency(road)
            self._last_emergency[road] = present
