from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .contracts import Artifact, GateDecision, GateRequest, Receipt


class Ledger:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                lane_id TEXT NOT NULL,
                job TEXT NOT NULL,
                status TEXT NOT NULL,
                orchestrator TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                artifact_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                sensitivity TEXT NOT NULL,
                content_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS gates (
                gate_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                prompt TEXT NOT NULL,
                allowed_json TEXT NOT NULL,
                action TEXT NOT NULL,
                action_fingerprint TEXT NOT NULL,
                artifact_id TEXT,
                status TEXT NOT NULL,
                PRIMARY KEY (run_id, gate_id)
            );
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                gate_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                action_fingerprint TEXT NOT NULL,
                approved_artifact_hash TEXT,
                decided_by TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS memory_fast (
                record_id TEXT PRIMARY KEY,
                lane_id TEXT NOT NULL,
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value_json TEXT NOT NULL,
                provenance TEXT NOT NULL,
                sensitivity TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS memory_candidates (
                candidate_id TEXT PRIMARY KEY,
                lane_id TEXT NOT NULL,
                namespace TEXT NOT NULL,
                kind TEXT NOT NULL,
                memory_json TEXT NOT NULL,
                sensitivity TEXT NOT NULL,
                status TEXT NOT NULL,
                decision_note TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS memory_slow (
                record_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                lane_id TEXT NOT NULL,
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value_json TEXT NOT NULL,
                provenance TEXT NOT NULL,
                sensitivity TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS surface_refs (
                surface_ref TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                surface TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS companion_sessions (
                session_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                lane_id TEXT NOT NULL,
                status TEXT NOT NULL,
                opened_by TEXT NOT NULL,
                max_turns INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS companion_turns (
                turn_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                speaker TEXT NOT NULL,
                message TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS surface_inbox (
                packet_id TEXT PRIMARY KEY,
                surface TEXT NOT NULL,
                external_id TEXT NOT NULL,
                lane_id TEXT,
                intent TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(surface, external_id)
            );
            """
        )
        self.conn.commit()

    def start_run(self, run_id: str, lane_id: str, job: str, orchestrator: str) -> None:
        self.conn.execute(
            "INSERT INTO runs(run_id, lane_id, job, status, orchestrator) VALUES (?, ?, ?, ?, ?)",
            (run_id, lane_id, job, "running", orchestrator),
        )
        self.conn.commit()

    def finish_run(self, run_id: str, status: str) -> None:
        self.conn.execute("UPDATE runs SET status = ? WHERE run_id = ?", (status, run_id))
        self.conn.commit()

    def put_artifact(self, run_id: str, artifact: Artifact) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO artifacts
            (artifact_id, run_id, kind, content_hash, sensitivity, content_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                artifact.artifact_id,
                run_id,
                artifact.kind,
                artifact.content_hash,
                artifact.sensitivity.value,
                json.dumps(artifact.content, sort_keys=True),
            ),
        )
        self.conn.commit()

    def put_gate(self, gate: GateRequest) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO gates
            (gate_id, run_id, prompt, allowed_json, action, action_fingerprint, artifact_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                gate.gate_id,
                gate.run_id,
                gate.prompt,
                json.dumps(gate.allowed_decisions),
                gate.action,
                gate.action_fingerprint,
                gate.artifact.artifact_id if gate.artifact else None,
                "waiting",
            ),
        )
        self.conn.commit()

    def record_decision(self, decision_id: str, run_id: str, decision: GateDecision) -> None:
        self.conn.execute(
            """
            INSERT INTO decisions
            (decision_id, run_id, gate_id, decision, action_fingerprint,
             approved_artifact_hash, decided_by, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                run_id,
                decision.gate_id,
                decision.decision,
                decision.action_fingerprint,
                decision.approved_artifact_hash,
                decision.decided_by,
                decision.note,
            ),
        )
        self.conn.execute(
            "UPDATE gates SET status = ? WHERE run_id = ? AND gate_id = ?",
            ("decided", run_id, decision.gate_id),
        )
        self.conn.commit()

    def put_receipt(self, receipt: Receipt) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO receipts(receipt_id, run_id, kind, status, summary, data_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                receipt.receipt_id,
                receipt.run_id,
                receipt.kind,
                receipt.status,
                receipt.summary,
                json.dumps(receipt.data, sort_keys=True),
            ),
        )
        self.conn.commit()

    def rows(self, table: str) -> list[sqlite3.Row]:
        if table not in {
            "runs",
            "artifacts",
            "gates",
            "decisions",
            "receipts",
            "memory_fast",
            "memory_candidates",
            "memory_slow",
            "surface_refs",
            "companion_sessions",
            "companion_turns",
            "surface_inbox",
        }:
            raise ValueError(f"unknown table: {table}")
        return list(self.conn.execute(f"SELECT * FROM {table} ORDER BY rowid"))

    def counts(self) -> dict[str, int]:
        tables = [
            "runs",
            "artifacts",
            "gates",
            "decisions",
            "receipts",
            "memory_fast",
            "memory_candidates",
            "memory_slow",
            "surface_refs",
            "companion_sessions",
            "companion_turns",
            "surface_inbox",
        ]
        return {
            table: int(self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }

    def status(self) -> dict[str, Any]:
        waiting = [
            dict(row)
            for row in self.conn.execute(
                "SELECT run_id, gate_id, prompt FROM gates WHERE status = 'waiting' ORDER BY rowid"
            )
        ]
        runs = [dict(row) for row in self.conn.execute("SELECT * FROM runs ORDER BY rowid")]
        sessions = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT * FROM companion_sessions
                WHERE status = 'active'
                ORDER BY rowid
                """
            )
        ]
        return {
            "runs": runs,
            "waiting_gates": waiting,
            "active_companion_sessions": sessions,
            "counts": self.counts(),
        }

    def record_surface_ref(
        self, *, surface_ref: str, run_id: str, surface: str, content_hash: str, path: str
    ) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO surface_refs(surface_ref, run_id, surface, content_hash, path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (surface_ref, run_id, surface, content_hash, path),
        )
        self.conn.commit()

    def iter_waiting_gates(self) -> Iterable[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT g.*, a.content_json, a.content_hash, a.kind, a.sensitivity
            FROM gates g
            LEFT JOIN artifacts a ON a.artifact_id = g.artifact_id
            WHERE g.status = 'waiting'
            ORDER BY g.rowid
            """
        )

    def create_companion_session(
        self,
        *,
        session_id: str,
        run_id: str,
        lane_id: str,
        opened_by: str,
        max_turns: int,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO companion_sessions
            (session_id, run_id, lane_id, status, opened_by, max_turns)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, run_id, lane_id, "active", opened_by, max_turns),
        )
        self.conn.commit()

    def get_companion_session(self, session_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM companion_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()

    def get_companion_session_by_run(self, run_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM companion_sessions WHERE run_id = ?",
            (run_id,),
        ).fetchone()

    def companion_turn_count(self, session_id: str) -> int:
        return int(
            self.conn.execute(
                "SELECT COUNT(*) FROM companion_turns WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
        )

    def put_companion_turn(
        self,
        *,
        turn_id: str,
        session_id: str,
        turn_index: int,
        speaker: str,
        message: str,
        response: dict[str, Any],
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO companion_turns
            (turn_id, session_id, turn_index, speaker, message, response_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                turn_id,
                session_id,
                turn_index,
                speaker,
                message,
                json.dumps(response, sort_keys=True),
            ),
        )
        self.conn.commit()

    def close_companion_session(self, session_id: str) -> None:
        self.conn.execute(
            """
            UPDATE companion_sessions
            SET status = 'closed', closed_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (session_id,),
        )
        self.conn.commit()

    def get_surface_packet(self, *, surface: str, external_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            """
            SELECT * FROM surface_inbox
            WHERE surface = ? AND external_id = ?
            """,
            (surface, external_id),
        ).fetchone()

    def put_surface_packet(
        self,
        *,
        packet_id: str,
        surface: str,
        external_id: str,
        lane_id: str | None,
        intent: str,
        payload: dict[str, Any],
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO surface_inbox
            (packet_id, surface, external_id, lane_id, intent, payload_json, status, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                packet_id,
                surface,
                external_id,
                lane_id,
                intent,
                json.dumps(payload, sort_keys=True),
                "received",
                "{}",
            ),
        )
        self.conn.commit()

    def update_surface_packet(
        self,
        *,
        packet_id: str,
        status: str,
        result: dict[str, Any],
    ) -> None:
        self.conn.execute(
            """
            UPDATE surface_inbox
            SET status = ?, result_json = ?
            WHERE packet_id = ?
            """,
            (status, json.dumps(result, sort_keys=True), packet_id),
        )
        self.conn.commit()
