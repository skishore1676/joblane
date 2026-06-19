from __future__ import annotations

import json
import platform
from pathlib import Path

from .doctor import Doctor
from .lane_packs import load_lane_packs
from .paths import DEFAULT_LANES_ROOT
from .runtime import JobLaneRuntime
from .scorecard import Scorecard


def build_proof_packet(
    *,
    root: Path | str = "state/proof",
    lanes_root: Path | str = DEFAULT_LANES_ROOT,
    output: Path | str = "out/proof/joblane-proof.json",
) -> Path:
    root = Path(root)
    lanes_root = Path(lanes_root)
    output = Path(output)
    if root.exists():
        # This function intentionally owns its proof root; callers should pass a
        # scratch root. Avoid destructive cleanup and let SQLite reuse the file.
        pass
    rt = JobLaneRuntime(root, lanes_root=lanes_root)
    try:
        for lane_id in load_lane_packs(lanes_root):
            existing = rt.ledger.conn.execute(
                "SELECT 1 FROM runs WHERE lane_id = ? LIMIT 1", (lane_id,)
            ).fetchone()
            if existing is None:
                rt.run_lane(lane_id, inputs=_fixture_inputs(lanes_root, lane_id))
        doctor = Doctor(rt.ledger, lanes_root=lanes_root).run()
        packet = {
            "schema": "joblane.proof.v1",
            "python": platform.python_version(),
            "root": str(root),
            "lanes_root": str(lanes_root),
            "doctor": {"ok": doctor.ok, "issues": doctor.issues, "summary": doctor.summary},
            "scorecard": Scorecard(rt.ledger, lanes_root=lanes_root).to_dict(),
            "status": rt.status(),
            "protected_gate_statement": {
                "live_send": False,
                "public_publish": False,
                "trading_mutation": False,
                "auth_secret_mutation": False,
                "runtime_cutover": False,
            },
        }
    finally:
        rt.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
    return output


def _fixture_inputs(lanes_root: Path, lane_id: str) -> dict:
    path = lanes_root / lane_id / "fixtures" / "sample.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"fixture must be a JSON object: {path}")
    return value
