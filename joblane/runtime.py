from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .contracts import GateDecision, Orchestrator, Receipt
from .gates import validate_decision
from .lanes import LANES
from .ledger import Ledger
from .memory import MemoryStore


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
        from .contracts import Artifact, GateRequest, Sensitivity

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
                sensitivity=Sensitivity(arow["sensitivity"]),
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
        self._apply_decision_effects(run_id=run_id, gate_id=gate_id, decision=decision, artifact=artifact)
        terminal = "done" if decision == "approve" else "cancelled"
        self.ledger.finish_run(run_id, terminal)

    def _apply_decision_effects(self, *, run_id: str, gate_id: str, decision: str, artifact) -> None:
        if artifact is None:
            return
        if decision != "approve":
            self.ledger.put_receipt(
                Receipt(
                    receipt_id=f"receipt:{run_id}:{gate_id}:no_effect",
                    run_id=run_id,
                    kind="effect_skipped",
                    status="ok",
                    summary=f"{gate_id} decision {decision!r} produced no durable effect",
                    data={"decision": decision, "live_effect": False},
                )
            )
            return
        run = self.ledger.conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        lane_id = str(run["lane_id"]) if run else str(artifact.content.get("lane_id") or "")
        content = artifact.content if isinstance(artifact.content, dict) else {}
        if gate_id in {"log_gate", "memory_gate", "frontdoor_memory_gate"}:
            candidate_ids = []
            if content.get("candidate_id"):
                candidate_ids.append(str(content["candidate_id"]))
            candidate_ids.extend(str(c) for c in content.get("candidates", []) if c)
            promoted = []
            memory = MemoryStore(self.ledger, lane_id)
            for candidate_id in candidate_ids:
                try:
                    record = memory.decide(candidate_id=candidate_id, decision="approve")
                except ValueError as exc:
                    self.ledger.put_receipt(
                        Receipt(
                            receipt_id=f"receipt:{run_id}:{gate_id}:{candidate_id}:effect_failed",
                            run_id=run_id,
                            kind="effect_failed",
                            status="failed",
                            summary=f"memory promotion failed: {exc}",
                            data={"candidate_id": candidate_id, "live_effect": False},
                        )
                    )
                    continue
                if record:
                    promoted.append(record.record_id)
            self.ledger.put_receipt(
                Receipt(
                    receipt_id=f"receipt:{run_id}:{gate_id}:memory_promoted",
                    run_id=run_id,
                    kind="memory_promoted",
                    status="ok",
                    summary=f"promoted {len(promoted)} durable memory record(s)",
                    data={"promoted": promoted, "live_effect": False},
                )
            )
            return
        if gate_id == "taste_gate":
            out_dir = self.root / "outbox" / "public_presence"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"{_safe_run_id(run_id)}.json"
            path.write_text(json.dumps(content, indent=2, sort_keys=True), encoding="utf-8")
            self.ledger.put_receipt(
                Receipt(
                    receipt_id=f"receipt:{run_id}:{gate_id}:draft_staged",
                    run_id=run_id,
                    kind="draft_staged",
                    status="ok",
                    summary="public draft packet staged locally; no live publish",
                    data={"path": str(path), "live_effect": False},
                )
            )
            return
        if gate_id == "commitment_gate":
            self.ledger.put_receipt(
                Receipt(
                    receipt_id=f"receipt:{run_id}:{gate_id}:commitments_recorded",
                    run_id=run_id,
                    kind="commitments_recorded",
                    status="ok",
                    summary="day commitments recorded as approved local plan",
                    data={"commitments": content.get("commitments", []), "live_effect": False},
                )
            )
            return
        if gate_id == "approve_or_skip":
            self.ledger.put_receipt(
                Receipt(
                    receipt_id=f"receipt:{run_id}:{gate_id}:experiment_staged",
                    run_id=run_id,
                    kind="experiment_staged",
                    status="ok",
                    summary="experiment output staged locally; no live external action",
                    data={"status": content.get("status"), "live_effect": False},
                )
            )


def _safe_run_id(run_id: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in run_id)
