from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from joblane.runtime import JobLaneRuntime


class RuntimeJobsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.rt = JobLaneRuntime(Path(self.tmp.name))

    def tearDown(self) -> None:
        self.rt.close()
        self.tmp.cleanup()

    def test_all_jobs_have_tracer_bullets(self) -> None:
        lanes = [
            "public_presence",
            "fitness",
            "trading_intel",
            "chief_of_staff",
            "reflection",
            "experiment",
        ]
        for lane in lanes:
            with self.subTest(lane=lane):
                self.rt.run_lane(lane)
        status = self.rt.status()
        jobs = {row["job"] for row in status["runs"]}
        self.assertEqual(jobs, {"A", "B", "C", "D", "E", "F"})
        self.assertEqual(status["counts"]["artifacts"], 6)
        self.assertGreaterEqual(status["counts"]["gates"], 5)

    def test_decision_advances_waiting_gate(self) -> None:
        run_id = self.rt.run_lane("public_presence")
        self.assertEqual(len(self.rt.status()["waiting_gates"]), 1)
        self.rt.decide_gate(run_id=run_id, gate_id="taste_gate", decision="approve")
        status = self.rt.status()
        self.assertEqual(status["waiting_gates"], [])
        self.assertEqual(status["counts"]["decisions"], 1)


if __name__ == "__main__":
    unittest.main()

