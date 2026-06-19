from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from joblane.control import ControlTower
from joblane.providers import DeterministicProvider, OpenClawProvider, ProviderRequest
from joblane.runtime import JobLaneRuntime


class ProviderAndControlTest(unittest.TestCase):
    def test_deterministic_provider_is_safe_worker(self) -> None:
        result = DeterministicProvider().run(
            ProviderRequest(role="reviewer", prompt="judge", context={}, allowed_outcomes=("ok",))
        )
        self.assertEqual(result.status, "succeeded")
        self.assertFalse(result.data["live_effect"])

    def test_openclaw_refuses_untrusted_input_by_default(self) -> None:
        result = OpenClawProvider().run(
            ProviderRequest(role="writer", prompt="external bookmark text", context={})
        )
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.data["guard"], "untrusted_input_refused")

    def test_control_tower_reads_waiting_from_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rt = JobLaneRuntime(Path(tmp))
            try:
                rt.run_lane("experiment")
                tower = ControlTower(rt.ledger)
                self.assertEqual(tower.summary()["waiting"], 1)
                self.assertEqual(tower.needs_attention()[0]["gate_id"], "approve_or_skip")
            finally:
                rt.close()


if __name__ == "__main__":
    unittest.main()

