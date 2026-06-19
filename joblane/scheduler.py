from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .ledger import Ledger
from .lane_packs import load_lane_packs
from .paths import DEFAULT_LANES_ROOT
from .schedules import due_status, parse_now


class Scheduler:
    def __init__(self, ledger: Ledger, *, lanes_root: Path | str = DEFAULT_LANES_ROOT) -> None:
        self.ledger = ledger
        self.lanes_root = lanes_root

    def due(self, *, now: datetime | str | None = None) -> list[dict]:
        instant = parse_now(now) if isinstance(now, str) or now is None else now
        packs = load_lane_packs(self.lanes_root)
        return [
            due_status(
                schedule=pack.schedule,
                lane_id=pack.lane_id,
                now=instant,
                last_run_at=self._last_run_at(pack.lane_id),
            )
            for pack in packs.values()
        ]

    def due_lanes(self, *, now: datetime | str | None = None) -> list[str]:
        return [row["lane_id"] for row in self.due(now=now) if row["due"]]

    def _last_run_at(self, lane_id: str) -> datetime | None:
        row = self.ledger.conn.execute(
            """
            SELECT created_at FROM runs
            WHERE lane_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            (lane_id,),
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(str(row["created_at"]))
