from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class JobArea(StrEnum):
    PUBLIC_PRESENCE = "A"
    FITNESS = "B"
    TRADING_INTEL = "C"
    CHIEF_OF_STAFF = "D"
    REFLECTION = "E"
    EXPERIMENT = "F"
    INFRA = "infra"


class RiskClass(StrEnum):
    REVERSIBLE = "reversible"
    EXTERNAL_REVERSIBLE = "external_reversible"
    EXTERNAL_IRREVERSIBLE = "external_irreversible"
    READ_ONLY = "read_only"


class Decision(StrEnum):
    APPROVE = "approve"
    REVISE = "revise"
    PARK = "park"
    REJECT = "reject"
    SKIP = "skip"


class Sensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    UNKNOWN = "unknown"


class Provenance(StrEnum):
    OBSERVED = "observed"
    SELF_DESCRIBED = "self_described"
    INFERRED = "inferred"


class Orchestrator(StrEnum):
    JOBLANE = "joblane"
    OPENCLAW = "openclaw"


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    kind: str
    content: Any
    content_hash: str
    sensitivity: Sensitivity = Sensitivity.INTERNAL


@dataclass(frozen=True)
class GateRequest:
    gate_id: str
    run_id: str
    prompt: str
    allowed_decisions: tuple[str, ...]
    action: str
    action_fingerprint: str
    artifact: Artifact | None = None
    requires_artifact_hash: bool = True
    risk_class: RiskClass = RiskClass.REVERSIBLE


@dataclass(frozen=True)
class GateDecision:
    gate_id: str
    decision: str
    action_fingerprint: str
    approved_artifact_hash: str | None
    decided_by: str = "human"
    note: str = ""


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    run_id: str
    kind: str
    status: str
    summary: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LaneResult:
    run_id: str
    lane_id: str
    job: JobArea
    status: str
    artifacts: tuple[Artifact, ...] = ()
    gates: tuple[GateRequest, ...] = ()
    receipts: tuple[Receipt, ...] = ()


@dataclass(frozen=True)
class MemoryRecord:
    record_id: str
    lane_id: str
    namespace: str
    key: str
    value: dict[str, Any]
    tier: str
    provenance: Provenance
    sensitivity: Sensitivity
    status: str = "active"

    def publishable(self) -> bool:
        return self.sensitivity in {Sensitivity.PUBLIC, Sensitivity.INTERNAL}


@dataclass(frozen=True)
class MemoryCandidate:
    candidate_id: str
    lane_id: str
    namespace: str
    kind: str
    memory: dict[str, Any]
    sensitivity: Sensitivity
    status: str = "pending"


@dataclass(frozen=True)
class ProviderResult:
    status: str
    output_text: str
    outcome: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    failure_summary: str | None = None

