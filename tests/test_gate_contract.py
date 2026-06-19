from __future__ import annotations

import unittest

from joblane.contracts import Decision, GateDecision
from joblane.gates import GateValidationError, make_artifact, make_gate, validate_decision


class GateContractTest(unittest.TestCase):
    def test_content_bound_approval_accepts_exact_artifact(self) -> None:
        artifact = make_artifact("a1", "packet", {"text": "ship this"})
        gate = make_gate(
            gate_id="g1",
            run_id="r1",
            prompt="approve?",
            allowed_decisions=(Decision.APPROVE.value,),
            action="publish",
            target="draft",
            artifact=artifact,
        )
        decision = GateDecision(
            gate_id="g1",
            decision="approve",
            action_fingerprint=gate.action_fingerprint,
            approved_artifact_hash=artifact.content_hash,
        )
        receipt = validate_decision(gate, decision)
        self.assertEqual(receipt.status, "ok")

    def test_approve_one_ship_another_is_rejected(self) -> None:
        artifact = make_artifact("a1", "packet", {"text": "ship this"})
        gate = make_gate(
            gate_id="g1",
            run_id="r1",
            prompt="approve?",
            allowed_decisions=(Decision.APPROVE.value,),
            action="publish",
            target="draft",
            artifact=artifact,
        )
        decision = GateDecision(
            gate_id="g1",
            decision="approve",
            action_fingerprint=gate.action_fingerprint,
            approved_artifact_hash="sha256:other",
        )
        with self.assertRaises(GateValidationError):
            validate_decision(gate, decision)

    def test_wrong_fingerprint_is_rejected(self) -> None:
        artifact = make_artifact("a1", "packet", {"text": "ship this"})
        gate = make_gate(
            gate_id="g1",
            run_id="r1",
            prompt="approve?",
            allowed_decisions=(Decision.APPROVE.value,),
            action="publish",
            target="draft",
            artifact=artifact,
        )
        decision = GateDecision(
            gate_id="g1",
            decision="approve",
            action_fingerprint="sha256:wrong",
            approved_artifact_hash=artifact.content_hash,
        )
        with self.assertRaises(GateValidationError):
            validate_decision(gate, decision)


if __name__ == "__main__":
    unittest.main()

