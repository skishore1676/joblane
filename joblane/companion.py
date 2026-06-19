from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import Decision, Orchestrator, Sensitivity
from .gates import make_artifact, make_gate
from .lane_packs import LanePack, LanePackError, load_lane_pack
from .ledger import Ledger
from .memory import MemoryStore


class CompanionError(ValueError):
    pass


@dataclass(frozen=True)
class CompanionTurnResult:
    session_id: str
    run_id: str
    turn_index: int
    lane_id: str
    reply: str
    proposed_candidate_id: str | None = None
    gate_id: str | None = None


def start_companion_session(
    ledger: Ledger,
    *,
    lane_id: str,
    opened_by: str = "human",
    max_turns: int = 8,
    lanes_root: Path | str = "lanes",
) -> dict[str, Any]:
    pack = _load_companion_pack(lane_id, lanes_root=lanes_root)
    if max_turns < 1:
        raise CompanionError("max_turns must be positive")
    session_id = f"session:{uuid.uuid4().hex[:12]}"
    run_id = f"companion:{lane_id}:{uuid.uuid4().hex[:12]}"
    ledger.start_run(run_id, lane_id, pack.job.value, Orchestrator.JOBLANE.value)
    ledger.create_companion_session(
        session_id=session_id,
        run_id=run_id,
        lane_id=lane_id,
        opened_by=opened_by,
        max_turns=max_turns,
    )
    return {
        "session_id": session_id,
        "run_id": run_id,
        "lane_id": lane_id,
        "job": pack.job.value,
        "status": "active",
        "max_turns": max_turns,
    }


def companion_turn(
    ledger: Ledger,
    *,
    session_id: str,
    message: str,
    speaker: str = "human",
    lanes_root: Path | str = "lanes",
) -> CompanionTurnResult:
    session = ledger.get_companion_session(session_id)
    if session is None:
        raise CompanionError("unknown companion session")
    if session["status"] != "active":
        raise CompanionError("companion session is not active")
    clean_message = message.strip()
    if not clean_message:
        raise CompanionError("message must not be empty")
    turn_index = ledger.companion_turn_count(session_id) + 1
    if turn_index > int(session["max_turns"]):
        raise CompanionError("companion session turn limit reached")

    lane_id = str(session["lane_id"])
    run_id = str(session["run_id"])
    pack = _load_companion_pack(lane_id, lanes_root=lanes_root)
    companion = _companion_config(pack)
    namespace = str(companion["namespace"])
    candidate_kind = str(companion["candidate_kind"])
    memory = MemoryStore(ledger, lane_id)
    memory.write_fast(
        namespace=namespace,
        key=f"companion-turn-{turn_index}",
        value={"session_id": session_id, "speaker": speaker, "message": clean_message},
        sensitivity=Sensitivity.PRIVATE,
    )
    recall = memory.recall(namespace=namespace, limit=5)
    reply = _reply_for(pack=pack, message=clean_message, recall=recall)
    proposed_candidate_id = None
    gate_id = None
    if _should_propose_memory(clean_message):
        candidate = memory.propose(
            namespace=namespace,
            kind=candidate_kind,
            memory={
                "source": "companion_session",
                "session_id": session_id,
                "turn_index": turn_index,
                "text": _durable_text(clean_message),
                "lane_id": lane_id,
            },
            sensitivity=_companion_sensitivity(companion),
        )
        proposed_candidate_id = candidate.candidate_id
        gate_id = f"companion_memory_gate_{turn_index}"
        artifact = make_artifact(
            f"{run_id}:companion-memory:{turn_index}",
            "companion_memory_candidate",
            {
                "lane_id": lane_id,
                "session_id": session_id,
                "turn_index": turn_index,
                "candidate_id": candidate.candidate_id,
                "memory": candidate.memory,
                "durable_write_requires_gate": True,
            },
            sensitivity=Sensitivity.PRIVATE,
        )
        gate = make_gate(
            gate_id=gate_id,
            run_id=run_id,
            prompt="Promote this companion-session memory to the durable tier?",
            allowed_decisions=(Decision.APPROVE.value, Decision.REJECT.value, Decision.REVISE.value),
            action="promote_companion_memory",
            target=lane_id,
            artifact=artifact,
        )
        ledger.put_artifact(run_id, artifact)
        ledger.put_gate(gate)
        reply = f"{reply} I staged one durable-memory candidate behind `{gate_id}`."

    response = {
        "reply": reply,
        "lane_id": lane_id,
        "run_id": run_id,
        "proposed_candidate_id": proposed_candidate_id,
        "gate_id": gate_id,
    }
    ledger.put_companion_turn(
        turn_id=f"turn:{session_id}:{turn_index}",
        session_id=session_id,
        turn_index=turn_index,
        speaker=speaker,
        message=clean_message,
        response=response,
    )
    return CompanionTurnResult(
        session_id=session_id,
        run_id=run_id,
        turn_index=turn_index,
        lane_id=lane_id,
        reply=reply,
        proposed_candidate_id=proposed_candidate_id,
        gate_id=gate_id,
    )


def close_companion_session(ledger: Ledger, *, session_id: str) -> dict[str, Any]:
    session = ledger.get_companion_session(session_id)
    if session is None:
        raise CompanionError("unknown companion session")
    ledger.close_companion_session(session_id)
    ledger.finish_run(str(session["run_id"]), "done")
    return {
        "session_id": session_id,
        "run_id": str(session["run_id"]),
        "status": "closed",
        "turns": ledger.companion_turn_count(session_id),
    }


def _should_propose_memory(message: str) -> bool:
    lowered = message.lower()
    return any(token in lowered for token in ("remember", "always", "principle", "baseline", "preference"))


def _durable_text(message: str) -> str:
    lowered = message.lower()
    for prefix in ("remember that", "remember", "always"):
        if lowered.startswith(prefix):
            return message[len(prefix) :].strip(" :.-") or message
    return message


def _load_companion_pack(lane_id: str, *, lanes_root: Path | str) -> LanePack:
    try:
        pack = load_lane_pack(Path(lanes_root) / lane_id)
    except LanePackError as exc:
        raise CompanionError(f"unknown lane: {lane_id}") from exc
    if pack.mode != "companion":
        raise CompanionError(f"lane does not support companion sessions: {lane_id}")
    _companion_config(pack)
    return pack


def _companion_config(pack: LanePack) -> dict[str, Any]:
    companion = pack.workflow.execution.get("companion")
    if not isinstance(companion, dict):
        raise CompanionError(f"companion lane lacks execution.companion config: {pack.lane_id}")
    if not companion.get("namespace") or not companion.get("candidate_kind"):
        raise CompanionError(f"companion config incomplete: {pack.lane_id}")
    return companion


def _companion_sensitivity(companion: dict[str, Any]) -> Sensitivity:
    try:
        return Sensitivity(str(companion.get("candidate_sensitivity") or Sensitivity.PRIVATE.value))
    except ValueError:
        return Sensitivity.UNKNOWN


def _reply_for(*, pack: LanePack, message: str, recall: dict[str, Any]) -> str:
    slow_count = len(recall["slow"])
    fast_count = len(recall["fast"])
    if "pain" in message.lower() and "no pain" not in message.lower():
        return "Captured. Treating pain as a stop signal until a human confirms the next step."
    return (
        f"Captured for {pack.title}; {fast_count} recent fast record(s) and "
        f"{slow_count} durable record(s) are in view."
    )
