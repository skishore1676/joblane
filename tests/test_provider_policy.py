from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from joblane.provider_policy import (
    load_deployment_policy,
    load_lane_provider_spec,
    resolve_provider_binding,
    resolved_provider_report,
)


class ProviderPolicyTest(unittest.TestCase):
    def test_deployment_actor_override_beats_lane_default(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        lane_spec = load_lane_provider_spec(repo / "lanes" / "reflection" / "providers.json")
        deployment = load_deployment_policy(repo / "deployments" / "local.example" / "provider-policy.json")

        binding = resolve_provider_binding(
            lane_id="reflection",
            actor="companion",
            lane_spec=lane_spec,
            deployment=deployment,
        )

        self.assertEqual(binding.provider, "openclaw")
        self.assertEqual(binding.fallback[0].provider, "deterministic")
        self.assertIn("deployment:reflection", binding.source)

    def test_report_lists_failover_chain(self) -> None:
        repo = Path(__file__).resolve().parents[1]

        rows = resolved_provider_report(
            lanes_root=repo / "lanes",
            policy_path=repo / "deployments" / "local.example" / "provider-policy.json",
        )

        reflection = [
            row for row in rows if row["lane_id"] == "reflection" and row["actor"] == "companion"
        ][0]
        self.assertEqual(reflection["failover_chain"], ["openclaw", "deterministic"])

    def test_providers_cli(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            result = json.loads(
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "joblane.cli",
                        "providers",
                        "--lanes-root",
                        str(repo / "lanes"),
                        "--policy",
                        str(repo / "deployments" / "local.example" / "provider-policy.json"),
                        "--root",
                        tmp,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
        self.assertTrue(any(row["provider"] == "openclaw" for row in result))


if __name__ == "__main__":
    unittest.main()

