from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTest(unittest.TestCase):
    def test_run_render_decide_status_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = subprocess.run(
                [sys.executable, "-m", "joblane.cli", "run", "public_presence", "--root", str(root)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            rendered = subprocess.run(
                [sys.executable, "-m", "joblane.cli", "render", "--root", str(root)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("taste_gate", rendered)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "joblane.cli",
                    "decide",
                    run,
                    "taste_gate",
                    "approve",
                    "--root",
                    str(root),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            status = json.loads(
                subprocess.run(
                    [sys.executable, "-m", "joblane.cli", "status", "--root", str(root)],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
            self.assertEqual(status["waiting_gates"], [])
            self.assertEqual(status["counts"]["decisions"], 1)

    def test_companion_cli_round_trip(self) -> None:
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
                        "--max-turns",
                        "2",
                        "--root",
                        str(root),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
            turn = json.loads(
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "joblane.cli",
                        "companion-turn",
                        started["session_id"],
                        "--message",
                        "Remember that one orchestrator owns workflow truth.",
                        "--root",
                        str(root),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
            self.assertEqual(turn["gate_id"], "companion_memory_gate_1")
            status = json.loads(
                subprocess.run(
                    [sys.executable, "-m", "joblane.cli", "status", "--root", str(root)],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
            self.assertEqual(status["counts"]["companion_turns"], 1)
            self.assertEqual(status["waiting_gates"][0]["gate_id"], "companion_memory_gate_1")


if __name__ == "__main__":
    unittest.main()
