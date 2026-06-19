from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from joblane.contracts import ProviderResult
from joblane.control import ControlIntentError, ControlTower
from joblane.providers import DeterministicProvider, FailoverProvider, OpenClawProvider, ProviderRequest
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

    def test_failover_cascades_infra_failure(self) -> None:
        result = FailoverProvider([_FailingProvider(), DeterministicProvider()]).run(
            ProviderRequest(role="reviewer", prompt="judge", context={}, allowed_outcomes=("ok",))
        )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.data["provider_layer"], 1)
        self.assertEqual(result.data["failover_chain"], ("failing", "deterministic"))
        self.assertEqual(len(result.data["failover_failures"]), 1)

    def test_failover_does_not_reroll_valid_negative_outcome(self) -> None:
        result = FailoverProvider([_NegativeProvider(), DeterministicProvider()]).run(
            ProviderRequest(
                role="reviewer",
                prompt="judge",
                context={},
                allowed_outcomes=("revise", "approve"),
            )
        )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.outcome, "revise")
        self.assertEqual(result.data["provider_layer"], 0)
        self.assertEqual(result.data["failover_failures"], [])

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

    def test_control_tower_records_allowed_intent_only(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            rt = JobLaneRuntime(Path(tmp))
            try:
                run_id = rt.run_lane("experiment")
                tower = ControlTower(rt.ledger, lanes_root=repo / "lanes")
                actions = tower.lane_actions()
                self.assertTrue(any(row["lane_id"] == "experiment" for row in actions))

                intent = tower.submit_intent(
                    lane_id="experiment",
                    action="park",
                    run_id=run_id,
                    note="operator wants to pause this packet",
                )
                self.assertEqual(intent["status"], "pending")
                self.assertEqual(rt.status()["counts"]["control_intents"], 1)
                self.assertEqual(rt.status()["pending_control_intents"][0]["action"], "park")

                with self.assertRaises(ControlIntentError):
                    tower.submit_intent(lane_id="experiment", action="publish_live")

                other_run = rt.run_lane("trading_intel")
                with self.assertRaises(ControlIntentError):
                    tower.submit_intent(lane_id="experiment", action="park", run_id=other_run)
            finally:
                rt.close()


class _FailingProvider:
    provider_id = "failing"

    def run(self, request: ProviderRequest) -> ProviderResult:
        return ProviderResult(
            status="failed",
            output_text="",
            failure_summary="simulated infra outage",
            data={"provider": self.provider_id},
        )


class _NegativeProvider:
    provider_id = "negative"

    def run(self, request: ProviderRequest) -> ProviderResult:
        return ProviderResult(
            status="succeeded",
            outcome="revise",
            output_text="valid negative verdict",
            data={"provider": self.provider_id, "live_effect": False},
        )


if __name__ == "__main__":
    unittest.main()
