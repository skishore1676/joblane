from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .contracts import Decision, JobArea, LaneResult, Orchestrator, Receipt, Sensitivity
from .gates import make_artifact, make_gate
from .ledger import Ledger
from .memory import MemoryStore


@dataclass(frozen=True)
class LaneSpec:
    lane_id: str
    job: JobArea
    handler: Callable[[Ledger, str, dict[str, Any]], LaneResult]


def _record(ledger: Ledger, run_id: str, artifact, gate=None) -> None:
    ledger.put_artifact(run_id, artifact)
    if gate is not None:
        ledger.put_gate(gate)


def public_presence(ledger: Ledger, run_id: str, inputs: dict[str, Any]) -> LaneResult:
    packet = {
        "headline": "Three useful notes from this week",
        "x_posts": [
            "A good agent system separates demand, fulfillment, and proof.",
            "A workflow has one orchestrator of record.",
        ],
        "review_questions": [
            "Is the claim sharp enough to publish?",
            "Does anything private or operational leak?",
        ],
        "publish_mode": "draft_only",
        "live_publish_allowed": False,
    }
    artifact = make_artifact("public_presence:packet", "publish_packet", packet)
    gate = make_gate(
        gate_id="taste_gate",
        run_id=run_id,
        prompt="Approve, revise, park, or reject this draft packet.",
        allowed_decisions=(
            Decision.APPROVE.value,
            Decision.REVISE.value,
            Decision.PARK.value,
            Decision.REJECT.value,
        ),
        action="stage_public_draft",
        target="public_presence",
        artifact=artifact,
    )
    _record(ledger, run_id, artifact, gate)
    return LaneResult(run_id, "public_presence", JobArea.PUBLIC_PRESENCE, "waiting", (artifact,), (gate,))


def fitness(ledger: Ledger, run_id: str, inputs: dict[str, Any]) -> LaneResult:
    memory = MemoryStore(ledger, "fitness")
    recall = memory.recall(namespace="gym")
    session = {
        "today": "full-body strength, conservative re-entry",
        "main_lifts": ["squat 3x5 RIR2", "press 3x5 RIR2", "row 3x8"],
        "progression_checks": [
            "hold load if pain appears",
            "add one rep next time if all sets feel RIR2+",
        ],
        "recall": recall,
        "parsed_log_candidate": inputs.get("log", "squat 3x5 @ easy; no pain"),
        "durable_write_requires_gate": True,
    }
    candidate = memory.propose(
        namespace="gym",
        kind="workout_log",
        memory={"summary": session["parsed_log_candidate"]},
        sensitivity=Sensitivity.PRIVATE,
    )
    artifact = make_artifact("fitness:session", "gym_session", {**session, "candidate_id": candidate.candidate_id})
    gate = make_gate(
        gate_id="log_gate",
        run_id=run_id,
        prompt="Confirm the parsed workout log before it becomes durable body memory.",
        allowed_decisions=(Decision.APPROVE.value, Decision.REVISE.value, Decision.SKIP.value),
        action="promote_gym_memory",
        target="fitness",
        artifact=artifact,
    )
    _record(ledger, run_id, artifact, gate)
    return LaneResult(run_id, "fitness", JobArea.FITNESS, "waiting", (artifact,), (gate,))


def trading_intel(ledger: Ledger, run_id: str, inputs: dict[str, Any]) -> LaneResult:
    report = {
        "mode": "read_only",
        "health": "yellow",
        "anomalies": ["one data cache is stale in fixture"],
        "evidence_refs": ["fixture://broker-cache", "fixture://strategy-ledger"],
        "forbidden": ["submit_order", "cancel_order", "transfer_cash"],
        "trade_authority": False,
        "next_question": "Did the stale cache affect today's synthesis?",
    }
    artifact = make_artifact(
        "trading_intel:report",
        "read_only_synthesis",
        report,
        sensitivity=Sensitivity.PRIVATE,
    )
    ledger.put_artifact(run_id, artifact)
    receipt = Receipt(
        f"receipt:{run_id}:read_only",
        run_id,
        "read_only_guard",
        "ok",
        "Trading lane produced read-only synthesis with no trade authority.",
        {"live_effect": False, "read_only": True},
    )
    ledger.put_receipt(receipt)
    return LaneResult(run_id, "trading_intel", JobArea.TRADING_INTEL, "done", (artifact,), (), (receipt,))


def chief_of_staff(ledger: Ledger, run_id: str, inputs: dict[str, Any]) -> LaneResult:
    memory = MemoryStore(ledger, "chief_of_staff")
    recall = memory.recall(namespace="intentions")
    plan = {
        "shape": "morning plan",
        "delegate": ["send routine follow-up to assistant"],
        "push": ["finish one JobLane proof slice before opening new research"],
        "decline": ["skip new trading experiments today"],
        "commitments": [
            "finish the current proof slice before starting new architecture work",
            "review waiting gates before adding more lanes",
        ],
        "recall": recall,
    }
    artifact = make_artifact("chief_of_staff:plan", "morning_plan", plan, sensitivity=Sensitivity.PRIVATE)
    gate = make_gate(
        gate_id="commitment_gate",
        run_id=run_id,
        prompt="Approve or revise the commitments this plan creates for today.",
        allowed_decisions=(Decision.APPROVE.value, Decision.REVISE.value, Decision.PARK.value),
        action="commit_day_plan",
        target="chief_of_staff",
        artifact=artifact,
    )
    _record(ledger, run_id, artifact, gate)
    return LaneResult(run_id, "chief_of_staff", JobArea.CHIEF_OF_STAFF, "waiting", (artifact,), (gate,))


def reflection(ledger: Ledger, run_id: str, inputs: dict[str, Any]) -> LaneResult:
    memory = MemoryStore(ledger, "reflection")
    memory.write_fast(
        namespace="weekly",
        key="current_session",
        value={"observation": "operator wants fewer systems and more proof"},
        sensitivity=Sensitivity.PRIVATE,
    )
    candidate = memory.propose(
        namespace="weekly",
        kind="operating_principle",
        memory={"principle": "one workflow has one orchestrator of record"},
        sensitivity=Sensitivity.INTERNAL,
    )
    artifact = make_artifact(
        "reflection:takeaway",
        "memory_takeaway",
        {
            "candidate_id": candidate.candidate_id,
            "prompt": "What decision should persist beyond this session?",
            "recall": memory.recall(namespace="weekly"),
            "durable_write_requires_gate": True,
        },
    )
    gate = make_gate(
        gate_id="memory_gate",
        run_id=run_id,
        prompt="Promote this reflection takeaway to durable memory?",
        allowed_decisions=(Decision.APPROVE.value, Decision.REJECT.value, Decision.REVISE.value),
        action="promote_reflection_memory",
        target="reflection",
        artifact=artifact,
    )
    _record(ledger, run_id, artifact, gate)
    return LaneResult(run_id, "reflection", JobArea.REFLECTION, "waiting", (artifact,), (gate,))


def experiment(ledger: Ledger, run_id: str, inputs: dict[str, Any]) -> LaneResult:
    packet = {
        "experiment": "daily small creative output",
        "status": inputs.get("status", "ready"),
        "failure_alert": inputs.get("status") == "failed",
        "allowed_decisions": ["approve", "skip"],
        "platform_weight": "minimal",
    }
    artifact = make_artifact("experiment:packet", "experiment_packet", packet)
    gate = make_gate(
        gate_id="approve_or_skip",
        run_id=run_id,
        prompt="Approve today's experiment output or skip it.",
        allowed_decisions=(Decision.APPROVE.value, Decision.SKIP.value),
        action="stage_experiment_output",
        target="experiment",
        artifact=artifact,
    )
    _record(ledger, run_id, artifact, gate)
    return LaneResult(run_id, "experiment", JobArea.EXPERIMENT, "waiting", (artifact,), (gate,))


LANES: dict[str, LaneSpec] = {
    "public_presence": LaneSpec("public_presence", JobArea.PUBLIC_PRESENCE, public_presence),
    "fitness": LaneSpec("fitness", JobArea.FITNESS, fitness),
    "trading_intel": LaneSpec("trading_intel", JobArea.TRADING_INTEL, trading_intel),
    "chief_of_staff": LaneSpec("chief_of_staff", JobArea.CHIEF_OF_STAFF, chief_of_staff),
    "reflection": LaneSpec("reflection", JobArea.REFLECTION, reflection),
    "experiment": LaneSpec("experiment", JobArea.EXPERIMENT, experiment),
}
