from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import Receipt
from .runtime import JobLaneRuntime
from .scheduler import Scheduler
from .surfaces import MarkdownSurface


@dataclass(frozen=True)
class RunnerTickResult:
    now: str | None
    dry_run: bool
    due: tuple[dict[str, Any], ...]
    run_ids: dict[str, str]
    rendered_gate_paths: tuple[str, ...]
    board_path: str | None
    receipt_id: str | None
    live_effect: bool = False


class DeploymentRunner:
    """One-shot sandbox runner for due lane packs.

    This is intentionally not a resident daemon. A deployment scheduler can call
    it repeatedly, but this class only evaluates due lanes, runs them once, and
    writes local proof.
    """

    def __init__(
        self,
        runtime: JobLaneRuntime,
        *,
        lanes_root: Path | str = "lanes",
        fixtures_dir: Path | str = "lanes",
    ) -> None:
        self.runtime = runtime
        self.lanes_root = Path(lanes_root)
        self.fixtures_dir = Path(fixtures_dir)

    def tick(self, *, now: str | None = None, dry_run: bool = False, render: bool = True) -> RunnerTickResult:
        due = tuple(Scheduler(self.runtime.ledger, lanes_root=self.lanes_root).due(now=now))
        due_lane_ids = [row["lane_id"] for row in due if row["due"]]
        run_ids: dict[str, str] = {}
        rendered_gate_paths: tuple[str, ...] = ()
        board_path: str | None = None
        receipt_id: str | None = None
        if not dry_run:
            for lane_id in due_lane_ids:
                run_ids[lane_id] = self.runtime.run_lane(
                    lane_id,
                    inputs=_fixture_inputs(self.fixtures_dir, lane_id),
                )
            if render:
                surface = MarkdownSurface(self.runtime.root / "surfaces" / "markdown", self.runtime.ledger)
                rendered_gate_paths = tuple(str(path) for path in surface.render_waiting_gates())
                board_path = str(surface.render_board(lanes_root=self.lanes_root))
            receipt_id = f"receipt:runner_tick:{uuid.uuid4().hex[:12]}"
            self.runtime.ledger.put_receipt(
                Receipt(
                    receipt_id=receipt_id,
                    run_id="system",
                    kind="runner_tick",
                    status="ok",
                    summary=f"runner tick evaluated {len(due)} lane(s), ran {len(run_ids)} due lane(s)",
                    data={
                        "due_lane_ids": due_lane_ids,
                        "run_ids": run_ids,
                        "rendered_gate_paths": list(rendered_gate_paths),
                        "board_path": board_path,
                        "dry_run": dry_run,
                        "live_effect": False,
                    },
                )
            )
        return RunnerTickResult(
            now=now,
            dry_run=dry_run,
            due=due,
            run_ids=run_ids,
            rendered_gate_paths=rendered_gate_paths,
            board_path=board_path,
            receipt_id=receipt_id,
        )


def _fixture_inputs(fixtures_dir: Path, lane_id: str) -> dict[str, Any]:
    path = fixtures_dir / lane_id / "fixtures" / "sample.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"fixture must be a JSON object: {path}")
    return value

