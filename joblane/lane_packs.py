from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .contracts import JobArea, Orchestrator, RiskClass


@dataclass(frozen=True)
class LanePack:
    lane_id: str
    job: JobArea
    title: str
    mode: str
    orchestrator: Orchestrator
    risk_class: RiskClass
    live_effects: bool
    description: str
    path: Path


class LanePackError(ValueError):
    pass


def load_lane_pack(path: Path) -> LanePack:
    meta_path = path / "lane.json"
    if not meta_path.exists():
        raise LanePackError(f"missing lane.json: {path}")
    raw = json.loads(meta_path.read_text(encoding="utf-8"))
    required = {
        "id",
        "job",
        "title",
        "mode",
        "orchestrator",
        "risk_class",
        "live_effects",
        "description",
    }
    missing = sorted(required - raw.keys())
    if missing:
        raise LanePackError(f"{meta_path} missing required fields: {', '.join(missing)}")
    lane_id = str(raw["id"])
    if lane_id != path.name:
        raise LanePackError(f"{meta_path} id {lane_id!r} must match folder {path.name!r}")
    try:
        job = JobArea(str(raw["job"]))
        orchestrator = Orchestrator(str(raw["orchestrator"]))
        risk_class = RiskClass(str(raw["risk_class"]))
    except ValueError as exc:
        raise LanePackError(f"{meta_path} has invalid enum: {exc}") from exc
    if orchestrator == Orchestrator.OPENCLAW:
        raise LanePackError(
            f"{meta_path} delegates orchestration to OpenClaw; add an explicit "
            "no-competing-scheduler proof before enabling."
        )
    return LanePack(
        lane_id=lane_id,
        job=job,
        title=str(raw["title"]),
        mode=str(raw["mode"]),
        orchestrator=orchestrator,
        risk_class=risk_class,
        live_effects=bool(raw["live_effects"]),
        description=str(raw["description"]),
        path=path,
    )


def load_lane_packs(root: Path | str = "lanes") -> dict[str, LanePack]:
    root = Path(root)
    packs = {}
    for path in sorted(p for p in root.iterdir() if p.is_dir()):
        pack = load_lane_pack(path)
        packs[pack.lane_id] = pack
    return packs

