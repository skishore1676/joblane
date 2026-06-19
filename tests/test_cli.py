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


if __name__ == "__main__":
    unittest.main()
