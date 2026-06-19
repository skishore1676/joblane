from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.paths import STARTER_LANES_ROOT
from joblane.runtime import JobLaneRuntime
from joblane.scorecard import Scorecard


class ScorecardTest(unittest.TestCase):
    def test_scorecard_reports_job_distance_from_target(self) -> None:
        repo = Path(__file__).resolve().parents[1]
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
                card = Scorecard(rt.ledger, lanes_root=STARTER_LANES_ROOT).to_dict()
                self.assertEqual(set(card), {"A", "B", "C", "D", "E", "F"})
                self.assertTrue(all(row["score"] >= 100 for row in card.values()))
                self.assertEqual(card["C"]["status"], "useful-tracer")
                self.assertIn("read-only", " ".join(card["C"]["evidence"]))
            finally:
                rt.close()


if __name__ == "__main__":
    unittest.main()
