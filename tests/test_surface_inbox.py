from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from joblane.memory import MemoryStore
from joblane.runtime import JobLaneRuntime
from joblane.surface_inbox import SurfaceInboxError, ingest_surface_packet


class SurfaceInboxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rt = JobLaneRuntime(self.root)

    def tearDown(self) -> None:
        self.rt.close()
        self.tmp.cleanup()

    def test_surface_packet_routes_to_companion_turn_and_dedupes(self) -> None:
        session = self.rt.start_companion_session(lane_id="reflection")
        packet = {
            "surface": "obsidian",
            "external_id": "note-1",
            "intent": "companion_turn",
            "payload": {
                "session_id": session["session_id"],
                "message": "Remember that adapter input should be provenance-backed.",
            },
        }

        result = ingest_surface_packet(self.rt, packet)
        duplicate = ingest_surface_packet(self.rt, packet)

        self.assertEqual(result.status, "accepted")
        self.assertFalse(result.duplicate)
        self.assertTrue(duplicate.duplicate)
        self.assertEqual(self.rt.status()["counts"]["surface_inbox"], 1)
        self.assertEqual(self.rt.status()["counts"]["companion_turns"], 1)
        self.assertEqual(result.result["gate_id"], "companion_memory_gate_1")

    def test_surface_packet_routes_frontdoor_without_direct_slow_memory(self) -> None:
        result = ingest_surface_packet(
            self.rt,
            {
                "surface": "telegram",
                "external_id": "msg-1",
                "lane_id": "reflection",
                "intent": "frontdoor_packet",
                "payload": {
                    "namespace": "weekly",
                    "observations": [{"key": "seen", "value": {"text": "operator said X"}}],
                    "proposed_memories": [
                        {
                            "kind": "principle",
                            "memory": {"text": "keep input adapters thin"},
                            "sensitivity": "internal",
                        }
                    ],
                },
            },
        )

        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.result["gate_id"], "frontdoor_memory_gate")
        recall = MemoryStore(self.rt.ledger, "reflection").recall(namespace="weekly")
        self.assertEqual(len(recall["fast"]), 1)
        self.assertEqual(recall["slow"], [])

    def test_rejected_packet_is_recorded(self) -> None:
        with self.assertRaises(SurfaceInboxError):
            ingest_surface_packet(
                self.rt,
                {
                    "surface": "apple_notes",
                    "external_id": "bad-1",
                    "intent": "unknown",
                    "payload": {},
                },
            )
        row = self.rt.ledger.get_surface_packet(surface="apple_notes", external_id="bad-1")
        self.assertEqual(row["status"], "rejected")

    def test_surface_inbox_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            started = json.loads(
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "joblane.cli",
                        "companion-start",
                        "reflection",
                        "--root",
                        str(root),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
            packet = Path(tmp) / "surface.json"
            packet.write_text(
                json.dumps(
                    {
                        "surface": "apple_messages",
                        "external_id": "thread-1",
                        "intent": "companion_turn",
                        "payload": {
                            "session_id": started["session_id"],
                            "message": "Capture this as fast context only.",
                        },
                    }
                ),
                encoding="utf-8",
            )
            result = json.loads(
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "joblane.cli",
                        "ingest-surface",
                        "--file",
                        str(packet),
                        "--root",
                        str(root),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
            self.assertEqual(result["surface"], "apple_messages")
            self.assertEqual(result["status"], "accepted")


if __name__ == "__main__":
    unittest.main()

