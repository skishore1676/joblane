from __future__ import annotations

import unittest
from pathlib import Path

from joblane.contracts import JobArea, Orchestrator
from joblane.lane_packs import load_lane_packs


class LanePackConformanceTest(unittest.TestCase):
    def test_default_lane_packs_cover_jobs_a_to_f(self) -> None:
        packs = load_lane_packs(Path(__file__).resolve().parents[1] / "lanes")
        covered = {pack.job for pack in packs.values()}
        self.assertTrue(
            {
                JobArea.PUBLIC_PRESENCE,
                JobArea.FITNESS,
                JobArea.TRADING_INTEL,
                JobArea.CHIEF_OF_STAFF,
                JobArea.REFLECTION,
                JobArea.EXPERIMENT,
            }.issubset(covered)
        )
        self.assertTrue(all(pack.orchestrator == Orchestrator.JOBLANE for pack in packs.values()))
        self.assertTrue(all(not pack.live_effects for pack in packs.values()))


if __name__ == "__main__":
    unittest.main()

