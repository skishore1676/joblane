from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from joblane.doctor import Doctor
from joblane.runtime import JobLaneRuntime


class DoctorTest(unittest.TestCase):
    def test_doctor_reports_green_for_default_sandbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rt = JobLaneRuntime(Path(tmp))
            try:
                for lane_id in (
                    "public_presence",
                    "fitness",
                    "trading_intel",
                    "chief_of_staff",
                    "reflection",
                    "experiment",
                ):
                    rt.run_lane(lane_id)
                report = Doctor(
                    rt.ledger,
                    lanes_root=Path(__file__).resolve().parents[1] / "lanes",
                ).run()
                self.assertTrue(report.ok, report.issues)
                self.assertEqual(report.summary["covered_jobs"], ["A", "B", "C", "D", "E", "F"])
            finally:
                rt.close()


if __name__ == "__main__":
    unittest.main()

