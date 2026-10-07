"""
store.py — SQLite event/phase-change logging via SQLModel.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

from app.config import DB_PATH


class PhaseEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: float = Field(default_factory=time.time)
    from_state: str
    to_state: str
    from_phase: str
    to_phase: str
    reason: str
    green_duration_s: float
    counts_json: str  # JSON-encoded dict


_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def init_db() -> None:
    SQLModel.metadata.create_all(_engine)


def log_transition(
    from_state: str,
    to_state: str,
    from_phase: str,
    to_phase: str,
    reason: str,
    green_duration_s: float,
    counts: dict[str, int],
) -> None:
    ev = PhaseEvent(
        from_state=from_state,
        to_state=to_state,
        from_phase=from_phase,
        to_phase=to_phase,
        reason=reason,
        green_duration_s=green_duration_s,
        counts_json=json.dumps(counts),
    )
    with Session(_engine) as session:
        session.add(ev)
        session.commit()


def get_history(limit: int = 100) -> list[dict]:
    with Session(_engine) as session:
        events = session.exec(
            select(PhaseEvent).order_by(PhaseEvent.id.desc()).limit(limit)  # type: ignore
        ).all()
        return [
            {
                "id": e.id,
                "timestamp": e.timestamp,
                "from_state": e.from_state,
                "to_state": e.to_state,
                "from_phase": e.from_phase,
                "to_phase": e.to_phase,
                "reason": e.reason,
                "green_duration_s": e.green_duration_s,
                "counts": json.loads(e.counts_json),
            }
            for e in events
        ]
