from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import JobArea, LaneResult, Receipt, Sensitivity
from .gates import make_artifact, make_gate
from .lane_packs import LanePack
from .ledger import Ledger
from .memory import MemoryStore


class LaneExecutionError(ValueError):
    pass


class LanePackExecutor:
    def __init__(self, ledger: Ledger, *, root: Path | str = "state/local") -> None:
        self.ledger = ledger
        self.root = Path(root)

    def run(self, *, pack: LanePack, run_id: str, inputs: dict[str, Any]) -> LaneResult:
        execution = getattr(pack.workflow, "execution", None)
        if not isinstance(execution, dict):
            raise LaneExecutionError(f"{pack.lane_id} workflow lacks execution block")
        merged_inputs = _load_default_inputs(pack.path) | inputs

        artifacts = []
        gates = []
        receipts = []
        artifact = None

        for item in execution.get("memory_fast", []):
            MemoryStore(self.ledger, pack.lane_id).write_fast(
                namespace=_required(item, "namespace"),
                key=str(_resolve(item.get("key"), merged_inputs, run_id=run_id)),
                value=_object_from(item, "value", merged_inputs, run_id=run_id),
                sensitivity=_sensitivity(item.get("sensitivity"), default=Sensitivity.INTERNAL),
            )

        candidate_id = None
        candidate_spec = execution.get("memory_candidate")
        if isinstance(candidate_spec, dict):
            candidate = MemoryStore(self.ledger, pack.lane_id).propose(
                namespace=_required(candidate_spec, "namespace"),
                kind=_required(candidate_spec, "kind"),
                memory=_object_from(candidate_spec, "memory", merged_inputs, run_id=run_id),
                sensitivity=_sensitivity(candidate_spec.get("sensitivity"), default=Sensitivity.INTERNAL),
            )
            candidate_id = candidate.candidate_id

        artifact_spec = execution.get("artifact")
        if isinstance(artifact_spec, dict):
            content = _object_from(artifact_spec, "content", merged_inputs, run_id=run_id)
            if candidate_id and artifact_spec.get("candidate_field"):
                content[str(artifact_spec["candidate_field"])] = candidate_id
            artifact = make_artifact(
                str(artifact_spec.get("id") or f"{run_id}:artifact").format(run_id=run_id),
                _required(artifact_spec, "kind"),
                content,
                sensitivity=_sensitivity(artifact_spec.get("sensitivity"), default=Sensitivity.INTERNAL),
            )
            self.ledger.put_artifact(run_id, artifact)
            artifacts.append(artifact)

        gate_spec = execution.get("gate")
        if isinstance(gate_spec, dict):
            if artifact is None:
                raise LaneExecutionError(f"{pack.lane_id} gate requires an artifact")
            gate = make_gate(
                gate_id=_required(gate_spec, "id"),
                run_id=run_id,
                prompt=_required(gate_spec, "prompt"),
                allowed_decisions=tuple(str(item) for item in gate_spec.get("allowed_decisions", [])),
                action=_required(gate_spec, "action"),
                target=str(gate_spec.get("target") or pack.lane_id),
                artifact=artifact,
            )
            self.ledger.put_gate(gate)
            gates.append(gate)

        for item in execution.get("receipts", []):
            receipt = Receipt(
                receipt_id=str(item.get("id") or f"receipt:{run_id}:{_required(item, 'kind')}").format(
                    run_id=run_id
                ),
                run_id=run_id,
                kind=_required(item, "kind"),
                status=str(item.get("status") or "ok"),
                summary=str(_resolve(item.get("summary", ""), merged_inputs, run_id=run_id)),
                data=_object_from(item, "data", merged_inputs, run_id=run_id),
            )
            self.ledger.put_receipt(receipt)
            receipts.append(receipt)

        status = str(execution.get("status") or ("waiting" if gates else "done"))
        return LaneResult(
            run_id=run_id,
            lane_id=pack.lane_id,
            job=JobArea(pack.job.value),
            status=status,
            artifacts=tuple(artifacts),
            gates=tuple(gates),
            receipts=tuple(receipts),
        )


def _load_default_inputs(path: Path) -> dict[str, Any]:
    fixture = path / "fixtures" / "sample.json"
    if not fixture.exists():
        return {}
    value = json.loads(fixture.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise LaneExecutionError(f"fixture must be a JSON object: {fixture}")
    return value


def _object_from(spec: dict[str, Any], key: str, inputs: dict[str, Any], *, run_id: str) -> dict[str, Any]:
    if f"{key}_from" in spec:
        value = _get_path(inputs, str(spec[f"{key}_from"]))
    else:
        value = spec.get(key, {})
    resolved = _resolve(value, inputs, run_id=run_id)
    if not isinstance(resolved, dict):
        raise LaneExecutionError(f"{key} must resolve to an object")
    return resolved


def _resolve(value: Any, inputs: dict[str, Any], *, run_id: str) -> Any:
    if isinstance(value, dict):
        if "$input" in value:
            return _get_path(inputs, str(value["$input"]), value.get("default"))
        if "$run_id" in value:
            return run_id
        return {key: _resolve(item, inputs, run_id=run_id) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve(item, inputs, run_id=run_id) for item in value]
    if isinstance(value, str):
        return value.format(run_id=run_id)
    return value


def _get_path(value: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def _required(spec: dict[str, Any], key: str) -> str:
    value = str(spec.get(key) or "").strip()
    if not value:
        raise LaneExecutionError(f"missing required execution field: {key}")
    return value


def _sensitivity(value: Any, *, default: Sensitivity) -> Sensitivity:
    if value is None:
        return default
    try:
        return Sensitivity(str(value))
    except ValueError as exc:
        raise LaneExecutionError(f"invalid sensitivity: {value}") from exc

