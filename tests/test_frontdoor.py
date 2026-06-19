from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from joblane.frontdoor import FrontDoorPacketError, ingest_frontdoor_packet
from joblane.ledger import Ledger
from joblane.memory import MemoryStore


class FrontDoorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = Ledger(Path(self.tmp.name) / "ledger.sqlite3")

    def tearDown(self) -> None:
        self.ledger.close()
        self.tmp.cleanup()

    def test_frontdoor_can_propose_but_not_promote_memory(self) -> None:
        result = ingest_frontdoor_packet(
            self.ledger,
            {
                "lane_id": "reflection",
                "requested_by": "openclaw",
                "namespace": "weekly",
                "observations": [
                    {"key": "o1", "value": {"text": "session happened"}, "sensitivity": "private"}
                ],
                "proposed_memories": [
                    {
                        "kind": "principle",
                        "memory": {"text": "one workflow has one orchestrator"},
                        "sensitivity": "internal",
                    }
                ],
            },
        )
        self.assertEqual(len(result.fast_records), 1)
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.gate_id, "frontdoor_memory_gate")
        packet = MemoryStore(self.ledger, "reflection").recall(namespace="weekly")
        self.assertEqual(len(packet["fast"]), 1)
        self.assertEqual(packet["slow"], [])
        self.assertEqual(self.ledger.status()["waiting_gates"][0]["gate_id"], "frontdoor_memory_gate")

    def test_frontdoor_requires_known_lane_and_requester(self) -> None:
        with self.assertRaises(FrontDoorPacketError):
            ingest_frontdoor_packet(self.ledger, {"lane_id": "missing", "requested_by": "x"})
        with self.assertRaises(FrontDoorPacketError):
            ingest_frontdoor_packet(self.ledger, {"lane_id": "reflection"})


if __name__ == "__main__":
    unittest.main()

