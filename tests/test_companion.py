from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from joblane.companion import CompanionError
from joblane.memory import MemoryStore
from joblane.runtime import JobLaneRuntime


class CompanionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rt = JobLaneRuntime(self.root)

    def tearDown(self) -> None:
        self.rt.close()
        self.tmp.cleanup()

    def test_companion_turns_are_ledger_backed_fast_memory(self) -> None:
        session = self.rt.start_companion_session(lane_id="chief_of_staff", max_turns=3)
        result = self.rt.companion_turn(
            session_id=session["session_id"],
            message="Push the low value meeting and preserve the writing block.",
        )

        self.assertEqual(result.lane_id, "chief_of_staff")
        self.assertIsNone(result.gate_id)
        self.assertEqual(self.rt.status()["counts"]["companion_sessions"], 1)
        self.assertEqual(self.rt.status()["counts"]["companion_turns"], 1)
        recall = MemoryStore(self.rt.ledger, "chief_of_staff").recall(namespace="intentions")
        self.assertEqual(len(recall["fast"]), 1)
        self.assertEqual(recall["slow"], [])

    def test_durable_companion_memory_requires_gate(self) -> None:
        session = self.rt.start_companion_session(lane_id="reflection", max_turns=3)
        result = self.rt.companion_turn(
            session_id=session["session_id"],
            message="Remember that proof-bearing artifacts beat existence checks.",
        )

        self.assertEqual(result.gate_id, "companion_memory_gate_1")
        self.assertEqual(MemoryStore(self.rt.ledger, "reflection").recall(namespace="weekly")["slow"], [])
        self.rt.decide_gate(
            run_id=session["run_id"],
            gate_id="companion_memory_gate_1",
            decision="approve",
        )
        status = self.rt.status()
        self.assertEqual(status["active_companion_sessions"][0]["session_id"], session["session_id"])
        self.assertEqual(
            len(MemoryStore(self.rt.ledger, "reflection").recall(namespace="weekly")["slow"]),
            1,
        )

    def test_companion_turn_limit_and_close(self) -> None:
        session = self.rt.start_companion_session(lane_id="fitness", max_turns=1)
        self.rt.companion_turn(session_id=session["session_id"], message="squat felt good, no pain")

        with self.assertRaises(CompanionError):
            self.rt.companion_turn(session_id=session["session_id"], message="second turn")

        closed = self.rt.close_companion_session(session_id=session["session_id"])
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(self.rt.status()["active_companion_sessions"], [])
        run = self.rt.ledger.conn.execute(
            "SELECT status FROM runs WHERE run_id = ?",
            (session["run_id"],),
        ).fetchone()
        self.assertEqual(run["status"], "done")

    def test_only_memory_heavy_jobs_support_companion_sessions(self) -> None:
        with self.assertRaises(CompanionError):
            self.rt.start_companion_session(lane_id="trading_intel")


if __name__ == "__main__":
    unittest.main()

