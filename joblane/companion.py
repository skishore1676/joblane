from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from .contracts import Decision, JobArea, Orchestrator, Sensitivity
from .gates import make_artifact, make_gate
from .lanes import LANES
from .ledger import Ledger
from .memory import MemoryStore


COMPANION_LANES = {
    "fitness": ("gym", "workout_preference"),
    "chief_of_staff": ("intentions", "operating_preference"),
    "reflection": ("weekly", "operating_principle"),
}


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
) -> dict[str, Any]:
    if lane_id not in COMPANION_LANES:
        raise CompanionError(f"lane does not support companion sessions: {lane_id}")
    if max_turns < 1:
        raise CompanionError("max_turns must be positive")
    job = LANES[lane_id].job
    session_id = f"session:{uuid.uuid4().hex[:12]}"
    run_id = f"companion:{lane_id}:{uuid.uuid4().hex[:12]}"
    ledger.start_run(run_id, lane_id, job.value, Orchestrator.JOBLANE.value)
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
        "job": job.value,
        "status": "active",
        "max_turns": max_turns,
    }


def companion_turn(
    ledger: Ledger,
    *,
    session_id: str,
    message: str,
    speaker: str = "human",
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
    namespace, candidate_kind = COMPANION_LANES[lane_id]
    memory = MemoryStore(ledger, lane_id)
    memory.write_fast(
        namespace=namespace,
        key=f"companion-turn-{turn_index}",
        value={"session_id": session_id, "speaker": speaker, "message": clean_message},
        sensitivity=Sensitivity.PRIVATE,
    )
    recall = memory.recall(namespace=namespace, limit=5)
    reply = _reply_for(lane_id=lane_id, message=clean_message, recall=recall)
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
            sensitivity=Sensitivity.PRIVATE if lane_id in {"fitness", "chief_of_staff"} else Sensitivity.INTERNAL,
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


def _reply_for(*, lane_id: str, message: str, recall: dict[str, Any]) -> str:
    slow_count = len(recall["slow"])
    fast_count = len(recall["fast"])
    if lane_id == "fitness":
        if "pain" in message.lower() and "no pain" not in message.lower():
            return "Captured. Treating pain as a stop signal until a human confirms the next training step."
        return f"Captured the training note with {fast_count} recent fast record(s) and {slow_count} durable record(s) in view."
    if lane_id == "chief_of_staff":
        return f"Captured the operating context; the lane now has {fast_count} recent intention record(s) available for planning."
    if lane_id == "reflection":
        return f"Captured the reflection turn; durable lessons still require a gate before entering slow memory."
    raise CompanionError(f"unsupported companion lane: {lane_id}")

