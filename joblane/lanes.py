from __future__ import annotations

import re
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
    source_notes = list(inputs.get("source_notes") or [])
    x_posts = list(inputs.get("x_posts") or [])
    packet = {
        "headline": inputs.get("headline") or "Three useful notes from this week",
        "source_notes": source_notes
        or [
            "Demand is Jobs-to-be-Done; lanes are fulfillment.",
            "Surfaces are projections; the ledger owns truth.",
        ],
        "x_posts": x_posts
        or [
            "A good agent system separates demand, fulfillment, and proof.",
            "A workflow has one orchestrator of record.",
        ],
        "review_questions": list(inputs.get("review_questions") or [])
        or [
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
    parsed_log = _parse_workout_log(str(inputs.get("today_log") or inputs.get("log") or "squat 3x5 @ easy; no pain"))
    last_session = inputs.get("last_session") if isinstance(inputs.get("last_session"), dict) else {}
    available_minutes = int(inputs.get("available_minutes") or 45)
    main_lifts = _next_lifts(last_session, available_minutes=available_minutes)
    pain_flags = parsed_log["pain_flags"]
    session = {
        "today": f"{inputs.get('goal') or 'full-body strength'}, {available_minutes} minutes",
        "main_lifts": main_lifts,
        "structured_log": parsed_log["sets"],
        "pain_flags": pain_flags,
        "progression_checks": [
            "hold load if pain appears" if pain_flags else "no pain reported; normal progression allowed",
            "add one rep or 5 lb next time if all sets feel RIR2+",
        ],
        "recall": recall,
        "parsed_log_candidate": parsed_log["summary"],
        "durable_write_requires_gate": True,
    }
    candidate = memory.propose(
        namespace="gym",
        kind="workout_log",
        memory={
            "summary": session["parsed_log_candidate"],
            "sets": parsed_log["sets"],
            "pain_flags": pain_flags,
            "next_lifts": main_lifts,
        },
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
    checks = [item for item in inputs.get("checks", []) if isinstance(item, dict)]
    stale = [item for item in checks if item.get("status") not in {"ok", "green"}]
    evidence_refs = [str(item.get("evidence")) for item in checks if item.get("evidence")]
    report = {
        "mode": "read_only",
        "health": inputs.get("health") or ("yellow" if stale else "green"),
        "anomalies": [f"{item.get('name', 'check')} is {item.get('status')}" for item in stale]
        or ["no anomalies in fixture"],
        "evidence_refs": evidence_refs or ["fixture://broker-cache", "fixture://strategy-ledger"],
        "checks": checks,
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
    for index, intention in enumerate(inputs.get("intentions") or []):
        memory.write_fast(
            namespace="intentions",
            key=f"input-intention-{index}",
            value={"text": str(intention)},
            sensitivity=Sensitivity.PRIVATE,
        )
    recall = memory.recall(namespace="intentions")
    calendar = [item for item in inputs.get("calendar", []) if isinstance(item, dict)]
    inbox = [str(item) for item in inputs.get("inbox", [])]
    time_blocks = _time_blocks(calendar)
    plan = {
        "shape": "morning plan",
        "time_blocks": time_blocks,
        "delegate": [item for item in inbox if "review" in item.lower() or "follow" in item.lower()]
        or ["delegate routine follow-up"],
        "push": [block["title"] for block in time_blocks[:1]]
        or ["finish one durable proof slice"],
        "decline": [item for item in inbox if "wait" in item.lower() or "low-priority" in item.lower()]
        or ["skip low-value new work"],
        "commitments": [
            "finish the highest-energy block before opening new work",
            "review waiting gates before adding more lanes",
        ],
        "rationale": "Ranked high-energy blocks before coordination and parked low-priority work.",
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
    observations = [str(item) for item in inputs.get("observations") or []] or [
        "operator wants fewer systems and more proof"
    ]
    prior_patterns = [str(item) for item in inputs.get("prior_patterns") or []]
    for index, pattern in enumerate(prior_patterns):
        memory.write_fast(
            namespace="weekly",
            key=f"prior-pattern-{index}",
            value={"pattern": pattern},
            sensitivity=Sensitivity.INTERNAL,
        )
    memory.write_fast(
        namespace="weekly",
        key="current_session",
        value={"observations": observations},
        sensitivity=Sensitivity.PRIVATE,
    )
    themes = _reflection_themes(observations + prior_patterns)
    candidate = memory.propose(
        namespace="weekly",
        kind="operating_principle",
        memory={
            "principle": themes[0] if themes else "one workflow has one orchestrator of record",
            "themes": themes,
        },
        sensitivity=Sensitivity.INTERNAL,
    )
    artifact = make_artifact(
        "reflection:takeaway",
        "memory_takeaway",
        {
            "candidate_id": candidate.candidate_id,
            "prompt": inputs.get("session_prompt") or "What decision should persist beyond this session?",
            "themes": themes,
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
        "experiment": inputs.get("experiment") or "daily small creative output",
        "status": inputs.get("status", "ready"),
        "failure_alert": inputs.get("status") == "failed",
        "failure_reason": inputs.get("failure_reason"),
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


def _parse_workout_log(raw: str) -> dict[str, Any]:
    sets = []
    pain_flags = []
    for chunk in re.split(r"[;\n]+", raw):
        text = chunk.strip()
        if not text:
            continue
        if "pain" in text.lower() and "no pain" not in text.lower():
            pain_flags.append(text)
        match = re.search(
            r"(?P<exercise>[A-Za-z][A-Za-z _-]*)\s+(?P<load>\d+)?x?(?P<reps>\d+)(?:\s*RIR(?P<rir>\d+))?",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            sets.append(
                {
                    "exercise": match.group("exercise").strip().lower(),
                    "load": int(match.group("load")) if match.group("load") else None,
                    "reps": int(match.group("reps")),
                    "rir": int(match.group("rir")) if match.group("rir") else None,
                }
            )
    return {
        "summary": raw.strip(),
        "sets": sets,
        "pain_flags": pain_flags,
    }


def _next_lifts(last_session: dict[str, Any], *, available_minutes: int) -> list[str]:
    sets = [item for item in last_session.get("sets", []) if isinstance(item, dict)]
    if not sets:
        return ["squat 3x5 RIR2", "press 3x5 RIR2", "row 3x8 RIR2"]
    out = []
    for item in sets[:3 if available_minutes >= 40 else 2]:
        exercise = str(item.get("exercise") or "lift")
        load = item.get("load")
        reps = item.get("reps") or 5
        rir = item.get("rir")
        next_load = int(load) + 5 if isinstance(load, int) and (rir is None or int(rir) >= 2) else load
        load_text = f"{next_load} lb " if next_load else ""
        out.append(f"{exercise} {load_text}x{reps} RIR2".strip())
    return out


def _time_blocks(calendar: list[dict[str, Any]]) -> list[dict[str, str]]:
    blocks = []
    for item in calendar:
        blocks.append(
            {
                "time": str(item.get("time") or ""),
                "title": str(item.get("title") or "work block"),
                "energy": str(item.get("energy") or "medium"),
            }
        )
    return blocks or [{"time": "09:00", "title": "focus block", "energy": "high"}]


def _reflection_themes(texts: list[str]) -> list[str]:
    joined = " ".join(texts).lower()
    themes = []
    if "orchestrator" in joined:
        themes.append("Keep one orchestrator of record per workflow.")
    if "proof" in joined or "scorecard" in joined:
        themes.append("Prefer proof-bearing artifacts over existence checks.")
    if "burden" in joined or "scheduler" in joined:
        themes.append("Automation should remove operator scheduling burden.")
    if not themes:
        themes.append("Promote only durable, reusable operating lessons.")
    return themes
