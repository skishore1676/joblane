from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from joblane.memory import MemoryStore
from joblane.runtime import JobLaneRuntime


class EffectsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rt = JobLaneRuntime(self.root)

    def tearDown(self) -> None:
        self.rt.close()
        self.tmp.cleanup()

    def test_reflection_approval_promotes_slow_memory(self) -> None:
        run_id = self.rt.run_lane("reflection")
        self.assertEqual(MemoryStore(self.rt.ledger, "reflection").recall(namespace="weekly")["slow"], [])
        self.rt.decide_gate(run_id=run_id, gate_id="memory_gate", decision="approve")
        packet = MemoryStore(self.rt.ledger, "reflection").recall(namespace="weekly")
        self.assertEqual(len(packet["slow"]), 1)
        receipts = [dict(row) for row in self.rt.ledger.rows("receipts")]
        self.assertTrue(any(row["kind"] == "memory_promoted" for row in receipts))

    def test_reject_does_not_promote_memory(self) -> None:
        run_id = self.rt.run_lane("fitness")
        self.rt.decide_gate(run_id=run_id, gate_id="log_gate", decision="skip")
        packet = MemoryStore(self.rt.ledger, "fitness").recall(namespace="gym")
        self.assertEqual(packet["slow"], [])
        receipts = [dict(row) for row in self.rt.ledger.rows("receipts")]
        self.assertTrue(any(row["kind"] == "effect_skipped" for row in receipts))

    def test_public_presence_approval_stages_local_draft_only(self) -> None:
        run_id = self.rt.run_lane("public_presence")
        self.rt.decide_gate(run_id=run_id, gate_id="taste_gate", decision="approve")
        staged = list((self.root / "outbox" / "public_presence").glob("*.json"))
        self.assertEqual(len(staged), 1)
        self.assertIn("live_publish_allowed", staged[0].read_text(encoding="utf-8"))
        receipts = [dict(row) for row in self.rt.ledger.rows("receipts")]
        self.assertTrue(any(row["kind"] == "draft_staged" for row in receipts))


if __name__ == "__main__":
    unittest.main()
