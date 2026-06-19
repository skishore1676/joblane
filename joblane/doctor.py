from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .contracts import JobArea
from .lane_packs import load_lane_packs
from .ledger import Ledger
from .paths import DEFAULT_LANES_ROOT


@dataclass(frozen=True)
class DoctorReport:
    ok: bool
    issues: tuple[str, ...]
    summary: dict


class Doctor:
    def __init__(self, ledger: Ledger, lanes_root: Path | str = DEFAULT_LANES_ROOT) -> None:
        self.ledger = ledger
        self.lanes_root = Path(lanes_root)

    def run(self) -> DoctorReport:
        issues: list[str] = []
        packs = load_lane_packs(self.lanes_root)
        covered = {pack.job for pack in packs.values() if pack.job != JobArea.INFRA}
        expected = {
            JobArea.PUBLIC_PRESENCE,
            JobArea.FITNESS,
            JobArea.TRADING_INTEL,
            JobArea.CHIEF_OF_STAFF,
            JobArea.REFLECTION,
            JobArea.EXPERIMENT,
        }
        missing_jobs = sorted(job.value for job in expected - covered)
        if missing_jobs:
            issues.append(f"missing Job coverage: {', '.join(missing_jobs)}")
        for pack in packs.values():
            if pack.live_effects:
                issues.append(f"{pack.lane_id} declares live_effects=true in default pack")
        for row in self.ledger.rows("receipts"):
            data = json.loads(row["data_json"])
            if data.get("live_effect") is True or data.get("live_send") is True:
                issues.append(f"receipt {row['receipt_id']} recorded a live effect")
        status = self.ledger.status()
        summary = {
            "lane_packs": len(packs),
            "covered_jobs": sorted(job.value for job in covered),
            "waiting_gates": len(status["waiting_gates"]),
            "runs": len(status["runs"]),
        }
        return DoctorReport(ok=not issues, issues=tuple(issues), summary=summary)
