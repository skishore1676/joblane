from __future__ import annotations

import json
import uuid
from typing import Any

from .contracts import MemoryCandidate, MemoryRecord, Provenance, Sensitivity
from .ledger import Ledger


def publishable(sensitivity: Sensitivity | str) -> bool:
    try:
        value = Sensitivity(sensitivity)
    except Exception:
        return False
    return value in {Sensitivity.PUBLIC, Sensitivity.INTERNAL}


class MemoryStore:
    def __init__(self, ledger: Ledger, lane_id: str) -> None:
        self.ledger = ledger
        self.lane_id = lane_id

    def write_fast(
        self,
        *,
        namespace: str,
        key: str,
        value: dict[str, Any],
        provenance: Provenance = Provenance.OBSERVED,
        sensitivity: Sensitivity = Sensitivity.INTERNAL,
    ) -> MemoryRecord:
        record_id = f"fast:{uuid.uuid4().hex}"
        self.ledger.conn.execute(
            """
            INSERT INTO memory_fast
            (record_id, lane_id, namespace, key, value_json, provenance, sensitivity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                self.lane_id,
                namespace,
                key,
                json.dumps(value, sort_keys=True),
                provenance.value,
                sensitivity.value,
            ),
        )
        self.ledger.conn.commit()
        return MemoryRecord(
            record_id=record_id,
            lane_id=self.lane_id,
            namespace=namespace,
            key=key,
            value=value,
            tier="fast",
            provenance=provenance,
            sensitivity=sensitivity,
        )

    def recall(self, *, namespace: str, limit: int = 20) -> dict[str, Any]:
        fast = [
            {
                "record_id": row["record_id"],
                "key": row["key"],
                "value": json.loads(row["value_json"]),
                "provenance": row["provenance"],
                "sensitivity": row["sensitivity"],
            }
            for row in self.ledger.conn.execute(
                """
                SELECT * FROM memory_fast
                WHERE lane_id = ? AND namespace = ?
                ORDER BY rowid DESC LIMIT ?
                """,
                (self.lane_id, namespace, limit),
            )
        ]
        slow = [
            {
                "record_id": row["record_id"],
                "key": row["key"],
                "value": json.loads(row["value_json"]),
                "provenance": row["provenance"],
                "sensitivity": row["sensitivity"],
            }
            for row in self.ledger.conn.execute(
                """
                SELECT * FROM memory_slow
                WHERE lane_id = ? AND namespace = ? AND status = 'active'
                ORDER BY rowid DESC LIMIT ?
                """,
                (self.lane_id, namespace, limit),
            )
        ]
        return {
            "lane_id": self.lane_id,
            "namespace": namespace,
            "fast": fast,
            "slow": slow,
            "slow_tier_available": True,
        }

    def propose(
        self,
        *,
        namespace: str,
        kind: str,
        memory: dict[str, Any],
        sensitivity: Sensitivity = Sensitivity.INTERNAL,
    ) -> MemoryCandidate:
        candidate_id = f"candidate:{uuid.uuid4().hex}"
        self.ledger.conn.execute(
            """
            INSERT INTO memory_candidates
            (candidate_id, lane_id, namespace, kind, memory_json, sensitivity, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                self.lane_id,
                namespace,
                kind,
                json.dumps(memory, sort_keys=True),
                sensitivity.value,
                "pending",
            ),
        )
        self.ledger.conn.commit()
        return MemoryCandidate(
            candidate_id=candidate_id,
            lane_id=self.lane_id,
            namespace=namespace,
            kind=kind,
            memory=memory,
            sensitivity=sensitivity,
        )

    def decide(self, *, candidate_id: str, decision: str, note: str = "") -> MemoryRecord | None:
        row = self.ledger.conn.execute(
            "SELECT * FROM memory_candidates WHERE candidate_id = ? AND lane_id = ?",
            (candidate_id, self.lane_id),
        ).fetchone()
        if row is None:
            raise ValueError("unknown memory candidate")
        if row["status"] != "pending":
            raise ValueError("memory candidate already decided")
        normalized = decision.lower().strip()
        if normalized not in {"approve", "reject"}:
            raise ValueError("memory decision must be approve or reject")
        if normalized == "reject":
            self.ledger.conn.execute(
                "UPDATE memory_candidates SET status = ?, decision_note = ? WHERE candidate_id = ?",
                ("rejected", note, candidate_id),
            )
            self.ledger.conn.commit()
            return None
        record_id = f"slow:{uuid.uuid4().hex}"
        memory = json.loads(row["memory_json"])
        self.ledger.conn.execute(
            "UPDATE memory_candidates SET status = ?, decision_note = ? WHERE candidate_id = ?",
            ("approved", note, candidate_id),
        )
        self.ledger.conn.execute(
            """
            INSERT INTO memory_slow
            (record_id, candidate_id, lane_id, namespace, key, value_json,
             provenance, sensitivity, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                candidate_id,
                self.lane_id,
                row["namespace"],
                row["kind"],
                json.dumps(memory, sort_keys=True),
                Provenance.INFERRED.value,
                row["sensitivity"],
                "active",
            ),
        )
        self.ledger.conn.commit()
        return MemoryRecord(
            record_id=record_id,
            lane_id=self.lane_id,
            namespace=row["namespace"],
            key=row["kind"],
            value=memory,
            tier="slow",
            provenance=Provenance.INFERRED,
            sensitivity=Sensitivity(row["sensitivity"]),
        )

