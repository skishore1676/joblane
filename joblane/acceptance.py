from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AcceptanceResult:
    ok: bool
    evidence: tuple[str, ...]
    gaps: tuple[str, ...]


def evaluate_job_artifacts(job: str, artifact_rows: list[dict[str, Any]]) -> AcceptanceResult:
    evidence: list[str] = []
    gaps: list[str] = []
    contents = [_content(row) for row in artifact_rows]
    if job == "A":
        _check_public_presence(contents, evidence, gaps)
    elif job == "B":
        _check_fitness(contents, evidence, gaps)
    elif job == "C":
        _check_trading(contents, evidence, gaps)
    elif job == "D":
        _check_chief_of_staff(contents, evidence, gaps)
    elif job == "E":
        _check_reflection(contents, evidence, gaps)
    elif job == "F":
        _check_experiment(contents, evidence, gaps)
    else:
        gaps.append(f"unknown Job {job}")
    return AcceptanceResult(ok=not gaps, evidence=tuple(evidence), gaps=tuple(gaps))


def _content(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("content_json")
    value = json.loads(raw) if isinstance(raw, str) else raw
    return value if isinstance(value, dict) else {}


def _nonempty_list(value: Any, *, min_len: int = 1) -> bool:
    return isinstance(value, list) and len(value) >= min_len and all(str(item).strip() for item in value)


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_one(contents: list[dict[str, Any]], predicate) -> dict[str, Any] | None:
    for content in contents:
        if predicate(content):
            return content
    return None


def _check_public_presence(contents: list[dict[str, Any]], evidence: list[str], gaps: list[str]) -> None:
    packet = _has_one(
        contents,
        lambda c: _nonempty_text(c.get("headline"))
        and _nonempty_list(c.get("x_posts"), min_len=2)
        and c.get("publish_mode") == "draft_only"
        and _nonempty_list(c.get("review_questions"), min_len=2)
        and c.get("live_publish_allowed") is False,
    )
    if packet:
        evidence.append("draft-only public packet has headline, multiple X posts, review questions, and no live publish")
    else:
        gaps.append("public packet lacks draft/live boundary or reviewable content")


def _check_fitness(contents: list[dict[str, Any]], evidence: list[str], gaps: list[str]) -> None:
    session = _has_one(
        contents,
        lambda c: _nonempty_text(c.get("today"))
        and _nonempty_list(c.get("main_lifts"), min_len=3)
        and _nonempty_text(c.get("parsed_log_candidate"))
        and _nonempty_list(c.get("structured_log"), min_len=1)
        and _nonempty_text(c.get("candidate_id"))
        and isinstance(c.get("progression_checks"), list)
        and c.get("durable_write_requires_gate") is True,
    )
    if session:
        evidence.append("fitness session has plan, log candidate, progression checks, and gated durable write")
    else:
        gaps.append("fitness artifact lacks in-gym plan/log/progression/gated-memory signal")


def _check_trading(contents: list[dict[str, Any]], evidence: list[str], gaps: list[str]) -> None:
    report = _has_one(
        contents,
        lambda c: c.get("mode") == "read_only"
        and _nonempty_list(c.get("anomalies"), min_len=1)
        and _nonempty_list(c.get("evidence_refs"), min_len=2)
        and {"submit_order", "cancel_order", "transfer_cash"}.issubset(set(c.get("forbidden") or []))
        and c.get("trade_authority") is False,
    )
    if report:
        evidence.append("trading synthesis is read-only, evidence-backed, and has no trade authority")
    else:
        gaps.append("trading artifact lacks read-only/evidence/no-authority proof")


def _check_chief_of_staff(contents: list[dict[str, Any]], evidence: list[str], gaps: list[str]) -> None:
    plan = _has_one(
        contents,
        lambda c: c.get("shape") == "morning plan"
        and _nonempty_list(c.get("time_blocks"), min_len=1)
        and _nonempty_list(c.get("delegate"), min_len=1)
        and _nonempty_list(c.get("push"), min_len=1)
        and _nonempty_list(c.get("decline"), min_len=1)
        and _nonempty_list(c.get("commitments"), min_len=2)
        and _nonempty_text(c.get("rationale"))
        and isinstance(c.get("recall"), dict)
    )
    if plan:
        evidence.append("chief-of-staff plan has delegate/push/decline, commitments, and recall context")
    else:
        gaps.append("chief-of-staff artifact lacks usable plan structure")


def _check_reflection(contents: list[dict[str, Any]], evidence: list[str], gaps: list[str]) -> None:
    takeaway = _has_one(
        contents,
        lambda c: _nonempty_text(c.get("candidate_id"))
        and _nonempty_text(c.get("prompt"))
        and _nonempty_list(c.get("themes"), min_len=1)
        and isinstance(c.get("recall"), dict)
        and c.get("durable_write_requires_gate") is True,
    )
    if takeaway:
        evidence.append("reflection artifact recalls context and proposes gated durable takeaway")
    else:
        gaps.append("reflection artifact lacks recall plus gated durable takeaway")


def _check_experiment(contents: list[dict[str, Any]], evidence: list[str], gaps: list[str]) -> None:
    packet = _has_one(
        contents,
        lambda c: _nonempty_text(c.get("experiment"))
        and c.get("status") in {"ready", "failed"}
        and isinstance(c.get("failure_alert"), bool)
        and c.get("allowed_decisions") == ["approve", "skip"]
        and c.get("platform_weight") == "minimal",
    )
    if packet:
        evidence.append("experiment packet is approve/skip, minimal, and failure-aware")
    else:
        gaps.append("experiment artifact lacks minimal approve/skip failure-aware shape")
