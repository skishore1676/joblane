from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from joblane.proof import build_proof_packet


class ProofTest(unittest.TestCase):
    def test_builds_machine_readable_proof_packet(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            out = build_proof_packet(
                root=Path(tmp) / "state",
                lanes_root=repo / "lanes",
                output=Path(tmp) / "proof.json",
            )
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(packet["schema"], "joblane.proof.v1")
            self.assertEqual(packet["lanes_root"], str(repo / "lanes"))
            self.assertTrue(packet["doctor"]["ok"])
            self.assertEqual(set(packet["scorecard"]), {"A", "B", "C", "D", "E", "F"})
            self.assertFalse(packet["protected_gate_statement"]["public_publish"])


if __name__ == "__main__":
    unittest.main()
