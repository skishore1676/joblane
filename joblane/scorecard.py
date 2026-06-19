from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .acceptance import evaluate_job_artifacts
from .contracts import JobArea
from .lane_packs import load_lane_packs
from .ledger import Ledger
from .paths import DEFAULT_LANES_ROOT


@dataclass(frozen=True)
class JobScore:
    job: str
    score: int
    status: str
    evidence: tuple[str, ...]
    gaps: tuple[str, ...]


class Scorecard:
    def __init__(self, ledger: Ledger, lanes_root: Path | str = DEFAULT_LANES_ROOT) -> None:
        self.ledger = ledger
        self.lanes_root = Path(lanes_root)

    def build(self) -> dict[str, JobScore]:
        packs = load_lane_packs(self.lanes_root)
        lanes_by_job = {}
        for pack in packs.values():
            lanes_by_job.setdefault(pack.job.value, []).append(pack.lane_id)
        runs = [dict(row) for row in self.ledger.rows("runs")]
        artifacts = [dict(row) for row in self.ledger.rows("artifacts")]
        gates = [dict(row) for row in self.ledger.rows("gates")]
        memory_fast = [dict(row) for row in self.ledger.rows("memory_fast")]
        memory_candidates = [dict(row) for row in self.ledger.rows("memory_candidates")]
        receipts = [dict(row) for row in self.ledger.rows("receipts")]

        out: dict[str, JobScore] = {}
        for job in ("A", "B", "C", "D", "E", "F"):
            evidence: list[str] = []
            gaps: list[str] = []
            score = 0
            lane_ids = lanes_by_job.get(job, [])
            if lane_ids:
                score += 20
                evidence.append(f"lane pack(s): {', '.join(sorted(lane_ids))}")
            else:
                gaps.append("no lane pack")
            job_runs = [run for run in runs if run["job"] == job]
            if job_runs:
                score += 20
                evidence.append(f"{len(job_runs)} run(s) recorded")
            else:
                gaps.append("no run proof")
            job_run_ids = {run["run_id"] for run in job_runs}
            if any(a["run_id"] in job_run_ids for a in artifacts):
                score += 20
                evidence.append("artifact recorded")
            else:
                gaps.append("no artifact proof")
            if self._job_specific_signal(job, job_run_ids, gates, memory_fast, memory_candidates, receipts):
                score += 20
                evidence.append("job-specific substrate signal present")
            else:
                gaps.append("missing job-specific substrate signal")
            job_artifacts = [artifact for artifact in artifacts if artifact["run_id"] in job_run_ids]
            acceptance = evaluate_job_artifacts(job, job_artifacts)
            if acceptance.ok:
                score += 20
                evidence.extend(acceptance.evidence)
            else:
                gaps.extend(acceptance.gaps)
            if score >= 80:
                status = "useful-tracer"
            elif score >= 60:
                status = "partial"
            elif score >= 40:
                status = "skeleton"
            else:
                status = "concept"
            if score < 80:
                gaps.append("needs richer real-world workflow before 70-80% target")
            elif score < 100:
                gaps.append("useful tracer only; still needs live-context integrations before production")
            out[job] = JobScore(job=job, score=score, status=status, evidence=tuple(evidence), gaps=tuple(gaps))
        return out

    def _job_specific_signal(
        self,
        job: str,
        run_ids: set[str],
        gates: list[dict],
        memory_fast: list[dict],
        memory_candidates: list[dict],
        receipts: list[dict],
    ) -> bool:
        if not run_ids:
            return False
        if job in {"A", "D", "F"}:
            return any(g["run_id"] in run_ids for g in gates)
        if job == "B":
            return any(row["lane_id"] == "fitness" for row in memory_candidates)
        if job == "C":
            return any(r["run_id"] in run_ids and r["kind"] == "read_only_guard" for r in receipts)
        if job == "E":
            return any(row["lane_id"] == "reflection" for row in memory_fast + memory_candidates)
        return False

    def to_dict(self) -> dict:
        return {
            job: {
                "score": score.score,
                "status": score.status,
                "evidence": score.evidence,
                "gaps": score.gaps,
            }
            for job, score in self.build().items()
        }
