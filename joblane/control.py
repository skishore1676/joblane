from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .lane_packs import load_lane_packs
from .ledger import Ledger
from .paths import DEFAULT_LANES_ROOT


class ControlIntentError(ValueError):
    pass


class ControlTower:
    def __init__(self, ledger: Ledger, *, lanes_root: Path | str = DEFAULT_LANES_ROOT) -> None:
        self.ledger = ledger
        self.lanes_root = lanes_root

    def needs_attention(self) -> list[dict]:
        return self.ledger.status()["waiting_gates"]

    def lane_actions(self) -> list[dict[str, Any]]:
        return [
            {
                "lane_id": pack.lane_id,
                "risk_class": pack.risk_class.value,
                "allowed_control_actions": list(pack.allowed_control_actions),
            }
            for pack in load_lane_packs(self.lanes_root).values()
        ]

    def submit_intent(
        self,
        *,
        lane_id: str,
        action: str,
        run_id: str | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        packs = load_lane_packs(self.lanes_root)
        if lane_id not in packs:
            raise ControlIntentError(f"unknown lane: {lane_id}")
        pack = packs[lane_id]
        if action not in pack.allowed_control_actions:
            raise ControlIntentError(f"{action!r} is not allowed for lane {lane_id!r}")
        if run_id:
            row = self.ledger.conn.execute(
                "SELECT lane_id FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                raise ControlIntentError(f"unknown run: {run_id}")
            if row["lane_id"] != lane_id:
                raise ControlIntentError("run does not belong to lane")
        intent_id = f"control:{uuid.uuid4().hex[:12]}"
        result = {
            "lane_id": lane_id,
            "action": action,
            "run_id": run_id,
            "risk_class": pack.risk_class.value,
            "live_effect": False,
        }
        self.ledger.put_control_intent(
            intent_id=intent_id,
            lane_id=lane_id,
            action=action,
            run_id=run_id,
            note=note,
            result=result,
        )
        return {"intent_id": intent_id, "status": "pending", **result}

    def summary(self) -> dict:
        status = self.ledger.status()
        return {
            "runs": len(status["runs"]),
            "waiting": len(status["waiting_gates"]),
            "pending_control": len(status["pending_control_intents"]),
            "counts": status["counts"],
        }
