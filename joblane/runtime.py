from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .contracts import GateDecision, Orchestrator
from .gates import validate_decision
from .lanes import LANES
from .ledger import Ledger


class JobLaneRuntime:
    def __init__(self, root: Path | str = "state/local") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger = Ledger(self.root / "ledger.sqlite3")

    def close(self) -> None:
        self.ledger.close()

    def run_lane(self, lane_id: str, inputs: dict[str, Any] | None = None) -> str:
        if lane_id not in LANES:
            raise ValueError(f"unknown lane: {lane_id}")
        spec = LANES[lane_id]
        run_id = f"{lane_id}:{uuid.uuid4().hex[:12]}"
        self.ledger.start_run(run_id, lane_id, spec.job.value, Orchestrator.JOBLANE.value)
        result = spec.handler(self.ledger, run_id, inputs or {})
        self.ledger.finish_run(run_id, result.status)
        for receipt in result.receipts:
            self.ledger.put_receipt(receipt)
        return run_id

    def status(self) -> dict[str, Any]:
        return self.ledger.status()

    def decide_gate(self, *, run_id: str, gate_id: str, decision: str, note: str = "") -> None:
        row = self.ledger.conn.execute(
            """
            SELECT g.*, a.content_hash
            FROM gates g
            LEFT JOIN artifacts a ON a.artifact_id = g.artifact_id
            WHERE g.run_id = ? AND g.gate_id = ?
            """,
            (run_id, gate_id),
        ).fetchone()
        if row is None:
            raise ValueError("unknown gate")
        from .contracts import Artifact, GateRequest
        import json

        artifact = None
        if row["artifact_id"]:
            arow = self.ledger.conn.execute(
                "SELECT * FROM artifacts WHERE artifact_id = ?", (row["artifact_id"],)
            ).fetchone()
            artifact = Artifact(
                artifact_id=arow["artifact_id"],
                kind=arow["kind"],
                content=json.loads(arow["content_json"]),
                content_hash=arow["content_hash"],
            )
        gate = GateRequest(
            gate_id=row["gate_id"],
            run_id=row["run_id"],
            prompt=row["prompt"],
            allowed_decisions=tuple(json.loads(row["allowed_json"])),
            action=row["action"],
            action_fingerprint=row["action_fingerprint"],
            artifact=artifact,
        )
        gate_decision = GateDecision(
            gate_id=gate_id,
            decision=decision,
            action_fingerprint=gate.action_fingerprint,
            approved_artifact_hash=artifact.content_hash if artifact else None,
            note=note,
        )
        receipt = validate_decision(gate, gate_decision)
        self.ledger.record_decision(
            f"decision:{run_id}:{gate_id}:{decision}", run_id, gate_decision
        )
        self.ledger.put_receipt(receipt)
        terminal = "done" if decision == "approve" else "cancelled"
        self.ledger.finish_run(run_id, terminal)

