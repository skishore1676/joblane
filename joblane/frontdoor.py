from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import Orchestrator, Sensitivity
from .gates import make_artifact, make_gate
from .lane_packs import LanePackError, load_lane_pack
from .ledger import Ledger
from .memory import MemoryStore


class FrontDoorPacketError(ValueError):
    pass


@dataclass(frozen=True)
class FrontDoorResult:
    run_id: str
    lane_id: str
    fast_records: tuple[str, ...]
    candidates: tuple[str, ...]
    gate_id: str | None


def ingest_frontdoor_packet(
    ledger: Ledger,
    packet: dict[str, Any],
    *,
    lanes_root: Path | str = "lanes",
) -> FrontDoorResult:
    """Ingest a packet from a conversational front door.

    This is the OpenClaw/Jarvis seam: the conversational agent can send observed
    context and proposed durable memories. It cannot approve, publish, or mutate
    slow memory directly.
    """
    lane_id = str(packet.get("lane_id") or "")
    try:
        pack = load_lane_pack(Path(lanes_root) / lane_id)
    except LanePackError as exc:
        raise FrontDoorPacketError(f"unknown lane_id: {lane_id!r}")
    requested_by = str(packet.get("requested_by") or "").strip()
    if not requested_by:
        raise FrontDoorPacketError("requested_by is required")
    observations = packet.get("observations") or []
    proposals = packet.get("proposed_memories") or []
    if not isinstance(observations, list) or not isinstance(proposals, list):
        raise FrontDoorPacketError("observations and proposed_memories must be lists")

    run_id = f"frontdoor:{lane_id}:{uuid.uuid4().hex[:12]}"
    ledger.start_run(run_id, lane_id, pack.job.value, Orchestrator.JOBLANE.value)
    memory = MemoryStore(ledger, lane_id)

    fast_ids: list[str] = []
    candidate_ids: list[str] = []
    namespace = str(packet.get("namespace") or lane_id)
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            raise FrontDoorPacketError("each observation must be an object")
        record = memory.write_fast(
            namespace=namespace,
            key=str(observation.get("key") or f"obs-{index}"),
            value=dict(observation.get("value") or observation),
            sensitivity=_sensitivity(observation.get("sensitivity")),
        )
        fast_ids.append(record.record_id)
    for proposal in proposals:
        if not isinstance(proposal, dict):
            raise FrontDoorPacketError("each proposed memory must be an object")
        candidate = memory.propose(
            namespace=namespace,
            kind=str(proposal.get("kind") or "takeaway"),
            memory=dict(proposal.get("memory") or proposal),
            sensitivity=_sensitivity(proposal.get("sensitivity")),
        )
        candidate_ids.append(candidate.candidate_id)

    artifact = make_artifact(
        f"{run_id}:frontdoor_packet",
        "frontdoor_packet",
        {
            "lane_id": lane_id,
            "requested_by": requested_by,
            "fast_records": fast_ids,
            "candidates": candidate_ids,
            "summary": packet.get("summary", ""),
        },
        sensitivity=Sensitivity.INTERNAL,
    )
    ledger.put_artifact(run_id, artifact)
    gate_id = None
    if candidate_ids:
        gate = make_gate(
            gate_id="frontdoor_memory_gate",
            run_id=run_id,
            prompt="Review proposed durable memory from the conversational front door.",
            allowed_decisions=("approve", "reject", "revise"),
            action="review_frontdoor_memory_candidates",
            target=lane_id,
            artifact=artifact,
        )
        ledger.put_gate(gate)
        gate_id = gate.gate_id
        ledger.finish_run(run_id, "waiting")
    else:
        ledger.finish_run(run_id, "done")
    return FrontDoorResult(
        run_id=run_id,
        lane_id=lane_id,
        fast_records=tuple(fast_ids),
        candidates=tuple(candidate_ids),
        gate_id=gate_id,
    )


def _sensitivity(value: Any) -> Sensitivity:
    try:
        return Sensitivity(str(value or Sensitivity.INTERNAL.value))
    except Exception:
        return Sensitivity.UNKNOWN
