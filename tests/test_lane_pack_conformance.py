from __future__ import annotations

import unittest
from pathlib import Path

from tests.paths import STARTER_LANES_ROOT
from joblane.contracts import JobArea, Orchestrator
from joblane.lane_packs import load_lane_packs


class LanePackConformanceTest(unittest.TestCase):
    def test_default_lane_packs_cover_jobs_a_to_f(self) -> None:
        packs = load_lane_packs(STARTER_LANES_ROOT)
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
        self.assertTrue(all(pack.workflow.stages for pack in packs.values()))
        self.assertTrue(all(pack.workflow.orchestrator == pack.orchestrator for pack in packs.values()))
        self.assertTrue(all(pack.schedule.kind for pack in packs.values()))
        self.assertTrue(all(pack.providers.actors for pack in packs.values()))
        self.assertTrue(all(pack.allowed_control_actions for pack in packs.values()))
        self.assertTrue(all(pack.drawers == ("inbox", "work", "products", "archive") for pack in packs.values()))

    def test_gated_workflows_declare_content_bound_gates(self) -> None:
        packs = load_lane_packs(STARTER_LANES_ROOT)
        gated = [pack for pack in packs.values() if pack.workflow.gates]
        self.assertGreaterEqual(len(gated), 5)
        self.assertTrue(all(pack.workflow.gates for pack in gated))


if __name__ == "__main__":
    unittest.main()
