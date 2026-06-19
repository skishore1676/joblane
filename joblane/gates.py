from __future__ import annotations

import hashlib
import json
from typing import Any

from .contracts import Artifact, GateDecision, GateRequest, Receipt


class GateValidationError(ValueError):
    """Raised when a human decision fails the gate contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def content_hash(value: Any) -> str:
    payload = value if isinstance(value, str) else canonical_json(value)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_artifact(artifact_id: str, kind: str, content: Any, **kwargs: Any) -> Artifact:
    return Artifact(
        artifact_id=artifact_id,
        kind=kind,
        content=content,
        content_hash=content_hash(content),
        **kwargs,
    )


def action_fingerprint(*, action: str, target: str, artifact_hash: str | None = None) -> str:
    return content_hash(
        {
            "action": action,
            "target": target,
            "artifact_hash": artifact_hash,
        }
    )


def make_gate(
    *,
    gate_id: str,
    run_id: str,
    prompt: str,
    allowed_decisions: tuple[str, ...],
    action: str,
    target: str,
    artifact: Artifact | None,
    requires_artifact_hash: bool = True,
) -> GateRequest:
    return GateRequest(
        gate_id=gate_id,
        run_id=run_id,
        prompt=prompt,
        allowed_decisions=allowed_decisions,
        action=action,
        action_fingerprint=action_fingerprint(
            action=action,
            target=target,
            artifact_hash=artifact.content_hash if artifact else None,
        ),
        artifact=artifact,
        requires_artifact_hash=requires_artifact_hash,
    )


def validate_decision(gate: GateRequest, decision: GateDecision) -> Receipt:
    if decision.gate_id != gate.gate_id:
        raise GateValidationError("decision addresses the wrong gate")
    if decision.action_fingerprint != gate.action_fingerprint:
        raise GateValidationError("decision action fingerprint mismatch")
    if decision.decision not in gate.allowed_decisions:
        raise GateValidationError("decision is not allowed for this gate")
    if gate.requires_artifact_hash:
        expected = gate.artifact.content_hash if gate.artifact else None
        if not expected:
            raise GateValidationError("gate requires an artifact hash but has no artifact")
        if decision.approved_artifact_hash != expected:
            raise GateValidationError("approved artifact hash mismatch")
    return Receipt(
        receipt_id=f"receipt:{gate.run_id}:{gate.gate_id}:{decision.decision}",
        run_id=gate.run_id,
        kind="gate_decision",
        status="ok",
        summary=f"{gate.gate_id} accepted {decision.decision}",
        data={
            "gate_id": gate.gate_id,
            "decision": decision.decision,
            "artifact_hash": decision.approved_artifact_hash,
        },
    )

