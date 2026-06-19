from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .contracts import Orchestrator


class WorkflowError(ValueError):
    pass


@dataclass(frozen=True)
class WorkflowSpec:
    workflow_id: str
    version: str
    orchestrator: Orchestrator
    stages: tuple[str, ...]
    gates: tuple[str, ...]
    live_effects: bool
    path: Path


def load_workflow(path: Path) -> WorkflowSpec:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != "joblane.workflow.v1":
        raise WorkflowError(f"{path} has unsupported schema")
    required = {"id", "version", "orchestrator", "stages", "gates", "live_effects"}
    missing = sorted(required - raw.keys())
    if missing:
        raise WorkflowError(f"{path} missing required fields: {', '.join(missing)}")
    try:
        orchestrator = Orchestrator(str(raw["orchestrator"]))
    except ValueError as exc:
        raise WorkflowError(f"{path} has invalid orchestrator: {raw['orchestrator']!r}") from exc
    stages = raw["stages"]
    gates = raw["gates"]
    if not isinstance(stages, list) or not stages:
        raise WorkflowError(f"{path} must declare at least one stage")
    stage_ids = []
    for stage in stages:
        if not isinstance(stage, dict) or not stage.get("id") or not stage.get("kind"):
            raise WorkflowError(f"{path} has invalid stage: {stage!r}")
        stage_ids.append(str(stage["id"]))
    gate_ids = []
    if not isinstance(gates, list):
        raise WorkflowError(f"{path} gates must be a list")
    for gate in gates:
        if not isinstance(gate, dict) or not gate.get("id"):
            raise WorkflowError(f"{path} has invalid gate: {gate!r}")
        gate_id = str(gate["id"])
        if gate_id not in stage_ids:
            raise WorkflowError(f"{path} gate {gate_id!r} is not a stage")
        if not gate.get("content_bound"):
            raise WorkflowError(f"{path} gate {gate_id!r} must be content_bound")
        if not gate.get("allowed_decisions"):
            raise WorkflowError(f"{path} gate {gate_id!r} has no allowed decisions")
        gate_ids.append(gate_id)
    if bool(raw["live_effects"]):
        raise WorkflowError(f"{path} default workflow may not enable live_effects")
    return WorkflowSpec(
        workflow_id=str(raw["id"]),
        version=str(raw["version"]),
        orchestrator=orchestrator,
        stages=tuple(stage_ids),
        gates=tuple(gate_ids),
        live_effects=bool(raw["live_effects"]),
        path=path,
    )

