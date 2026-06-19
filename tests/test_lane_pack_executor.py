from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from joblane.runtime import JobLaneRuntime


class LanePackExecutorTest(unittest.TestCase):
    def test_runtime_executes_new_lane_pack_without_engine_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lanes_root = root / "lane-packs"
            lane = lanes_root / "personal_admin"
            (lane / "fixtures").mkdir(parents=True)
            _write_json(
                lane / "lane.json",
                {
                    "id": "personal_admin",
                    "job": "D",
                    "title": "Personal Admin",
                    "mode": "workflow",
                    "orchestrator": "joblane",
                    "risk_class": "reversible",
                    "live_effects": False,
                    "schedule": {"kind": "manual"},
                    "allowed_control_actions": ["run_now", "park"],
                    "drawers": ["inbox", "work", "products", "archive"],
                    "description": "A temporary user-defined job pack.",
                },
            )
            _write_json(
                lane / "providers.json",
                {
                    "schema": "joblane.providers.v1",
                    "actors": {"runner": {"provider": "deterministic"}},
                },
            )
            _write_json(
                lane / "workflow.json",
                {
                    "schema": "joblane.workflow.v1",
                    "id": "personal_admin",
                    "version": "0.1.0",
                    "orchestrator": "joblane",
                    "stages": [
                        {"id": "prepare", "kind": "fixture_or_provider"},
                        {"id": "review_gate", "kind": "human_gate"},
                    ],
                    "gates": [
                        {
                            "id": "review_gate",
                            "allowed_decisions": ["approve", "park"],
                            "content_bound": True,
                        }
                    ],
                    "live_effects": False,
                    "execution": {
                        "artifact": {
                            "id": "{run_id}:packet",
                            "kind": "admin_packet",
                            "content_from": "artifact",
                        },
                        "gate": {
                            "id": "review_gate",
                            "prompt": "Approve or park this packet.",
                            "allowed_decisions": ["approve", "park"],
                            "action": "stage_admin_packet",
                        },
                        "status": "waiting",
                    },
                },
            )
            _write_json(
                lane / "fixtures" / "sample.json",
                {"artifact": {"task": "renew document", "live_effect": False}},
            )

            rt = JobLaneRuntime(root / "state", lanes_root=lanes_root)
            try:
                run_id = rt.run_lane("personal_admin")
                status = rt.status()
                self.assertEqual(status["counts"]["runs"], 1)
                self.assertEqual(status["waiting_gates"][0]["gate_id"], "review_gate")
                artifact = rt.ledger.conn.execute(
                    "SELECT * FROM artifacts WHERE run_id = ?", (run_id,)
                ).fetchone()
                self.assertEqual(artifact["kind"], "admin_packet")
            finally:
                rt.close()


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
