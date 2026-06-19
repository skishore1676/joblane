from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.paths import STARTER_LANES_ROOT
from joblane.runtime import JobLaneRuntime


class InputFixturesTest(unittest.TestCase):
    def test_run_accepts_input_file(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "state"
            run_id = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "joblane.cli",
                    "run",
                    "fitness",
                    "--input",
                    str(STARTER_LANES_ROOT / "fitness" / "fixtures" / "sample.json"),
                    "--root",
                    str(root),
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            rt = JobLaneRuntime(root)
            try:
                artifact = dict(rt.ledger.rows("artifacts")[0])
                content = json.loads(artifact["content_json"])
                self.assertEqual(artifact["run_id"], run_id)
                self.assertGreaterEqual(len(content["structured_log"]), 3)
                self.assertIn("progression_checks", content)
            finally:
                rt.close()

    def test_run_all_uses_lane_fixtures(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "state"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "joblane.cli",
                    "run-all",
                    "--fixtures-dir",
                    str(STARTER_LANES_ROOT),
                    "--root",
                    str(root),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            rt = JobLaneRuntime(root)
            try:
                artifacts = [json.loads(row["content_json"]) for row in rt.ledger.rows("artifacts")]
                chief = next(item for item in artifacts if item.get("shape") == "morning plan")
                reflection = next(item for item in artifacts if item.get("prompt"))
                self.assertGreaterEqual(len(chief["time_blocks"]), 3)
                self.assertIn("proof-bearing", " ".join(reflection["themes"]))
            finally:
                rt.close()


if __name__ == "__main__":
    unittest.main()
