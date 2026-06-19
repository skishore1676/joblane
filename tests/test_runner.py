from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from joblane.runtime import JobLaneRuntime
from joblane.runner import DeploymentRunner


class DeploymentRunnerTest(unittest.TestCase):
    def test_tick_runs_due_lanes_and_renders_surfaces(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            rt = JobLaneRuntime(Path(tmp))
            try:
                result = DeploymentRunner(
                    rt,
                    lanes_root=repo / "lanes",
                    fixtures_dir=repo / "lanes",
                ).tick(now="2026-06-19T17:00:00")

                self.assertEqual(set(result.run_ids), {"chief_of_staff", "reflection", "trading_intel"})
                self.assertTrue(result.rendered_gate_paths)
                self.assertIsNotNone(result.board_path)
                self.assertIsNotNone(result.receipt_id)
                status = rt.status()
                self.assertEqual(status["counts"]["runs"], 3)
                self.assertGreaterEqual(status["counts"]["surface_refs"], 1)
                receipt = rt.ledger.conn.execute(
                    "SELECT * FROM receipts WHERE receipt_id = ?",
                    (result.receipt_id,),
                ).fetchone()
                receipt_data = json.loads(receipt["data_json"])
                self.assertFalse(receipt_data["live_effect"])

                second = DeploymentRunner(
                    rt,
                    lanes_root=repo / "lanes",
                    fixtures_dir=repo / "lanes",
                ).tick(now="2026-06-19T17:30:00")
                self.assertEqual(second.run_ids, {})
            finally:
                rt.close()

    def test_dry_run_has_no_ledger_side_effects(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            rt = JobLaneRuntime(Path(tmp))
            try:
                result = DeploymentRunner(rt, lanes_root=repo / "lanes").tick(
                    now="2026-06-19T17:00:00",
                    dry_run=True,
                )
                self.assertTrue([row for row in result.due if row["due"]])
                self.assertEqual(result.run_ids, {})
                self.assertIsNone(result.receipt_id)
                self.assertEqual(rt.status()["counts"]["runs"], 0)
            finally:
                rt.close()

    def test_tick_cli(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            result = json.loads(
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "joblane.cli",
                        "tick",
                        "--now",
                        "2026-06-19T17:00:00",
                        "--lanes-root",
                        str(repo / "lanes"),
                        "--fixtures-dir",
                        str(repo / "lanes"),
                        "--root",
                        tmp,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
            self.assertIn("chief_of_staff", result["run_ids"])
            self.assertFalse(result["live_effect"])
            self.assertTrue(result["rendered_gate_paths"])


if __name__ == "__main__":
    unittest.main()

