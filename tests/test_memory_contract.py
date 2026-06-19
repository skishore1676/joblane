from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from joblane.contracts import Sensitivity
from joblane.ledger import Ledger
from joblane.memory import MemoryStore, publishable


class MemoryContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = Ledger(Path(self.tmp.name) / "ledger.sqlite3")
        self.memory = MemoryStore(self.ledger, "reflection")

    def tearDown(self) -> None:
        self.ledger.close()
        self.tmp.cleanup()

    def test_fast_memory_round_trips(self) -> None:
        self.memory.write_fast(namespace="weekly", key="k", value={"v": 1})
        packet = self.memory.recall(namespace="weekly")
        self.assertEqual(packet["fast"][0]["value"], {"v": 1})
        self.assertEqual(packet["slow"], [])

    def test_slow_memory_promotes_only_after_decide(self) -> None:
        candidate = self.memory.propose(
            namespace="weekly",
            kind="principle",
            memory={"text": "one orchestrator"},
        )
        self.assertEqual(self.memory.recall(namespace="weekly")["slow"], [])
        record = self.memory.decide(candidate_id=candidate.candidate_id, decision="approve")
        self.assertIsNotNone(record)
        packet = self.memory.recall(namespace="weekly")
        self.assertEqual(packet["slow"][0]["value"], {"text": "one orchestrator"})

    def test_private_and_unknown_are_not_publishable(self) -> None:
        self.assertTrue(publishable(Sensitivity.PUBLIC))
        self.assertTrue(publishable(Sensitivity.INTERNAL))
        self.assertFalse(publishable(Sensitivity.PRIVATE))
        self.assertFalse(publishable(Sensitivity.UNKNOWN))
        self.assertFalse(publishable("surprise"))


if __name__ == "__main__":
    unittest.main()

