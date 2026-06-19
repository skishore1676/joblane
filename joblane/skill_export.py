from __future__ import annotations

from pathlib import Path

from .lane_packs import LanePack, load_lane_packs
from .paths import DEFAULT_LANES_ROOT


def export_openclaw_skills(
    *, lanes_root: Path | str = DEFAULT_LANES_ROOT, out_dir: Path | str = "out/openclaw-skills"
) -> list[Path]:
    """Generate thin OpenClaw skill docs for lane front-door usage.

    The skills instruct OpenClaw to hand JobLane packets to the front-door seam;
    they do not grant OpenClaw direct write/publish authority.
    """
    packs = load_lane_packs(lanes_root)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for pack in packs.values():
        skill_dir = out / pack.lane_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        path = skill_dir / "SKILL.md"
        path.write_text(_skill_text(pack), encoding="utf-8")
        paths.append(path)
    return paths


def install_openclaw_skills(
    *,
    lanes_root: Path | str = DEFAULT_LANES_ROOT,
    target_dir: Path | str,
    prefix: str = "joblane-",
) -> list[Path]:
    """Install thin JobLane front-door skills into an OpenClaw skills directory.

    This is a filesystem copy of source skill docs only. It does not restart
    OpenClaw, mutate runtime state, or edit agent routing. Operators can point
    it at `workspace-main/skills` when they want the source workspace to expose
    JobLane front-door skills.
    """
    packs = load_lane_packs(lanes_root)
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for pack in packs.values():
        skill_dir = target / f"{prefix}{pack.lane_id}"
        skill_dir.mkdir(parents=True, exist_ok=True)
        path = skill_dir / "SKILL.md"
        path.write_text(_skill_text(pack), encoding="utf-8")
        paths.append(path)
    return paths


def _skill_text(pack: LanePack) -> str:
    return f"""---
name: joblane-{pack.lane_id}
description: Front-door skill for the JobLane {pack.title} lane.
---

# {pack.title}

Use this skill when a conversation needs to hand work to the JobLane
`{pack.lane_id}` lane.

Job: `{pack.job.value}`
Mode: `{pack.mode}`
Orchestrator of record: `{pack.orchestrator.value}`

Do not directly publish, send, write durable memory, or mutate external systems.
Prepare a front-door packet and pass it to JobLane:

```json
{{
  "lane_id": "{pack.lane_id}",
  "requested_by": "openclaw",
  "namespace": "{pack.lane_id}",
  "summary": "short summary",
  "observations": [
    {{"key": "obs-1", "value": {{"text": "episodic fact"}}, "sensitivity": "internal"}}
  ],
  "proposed_memories": [
    {{"kind": "takeaway", "memory": {{"text": "durable candidate"}}, "sensitivity": "internal"}}
  ]
}}
```

JobLane will record fast memory immediately and route durable memory candidates
through a human gate. The surface is a projection; the ledger remains truth.
"""
