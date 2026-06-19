from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .doctor import Doctor
from .frontdoor import ingest_frontdoor_packet
from .proof import build_proof_packet
from .runtime import JobLaneRuntime
from .scorecard import Scorecard
from .skill_export import export_openclaw_skills, install_openclaw_skills
from .surfaces import MarkdownSurface


def main() -> int:
    parser = argparse.ArgumentParser(prog="joblane")
    parser.add_argument("--root", default="state/local")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run")
    run.add_argument("lane_id")
    run.add_argument("--root", dest="root_override")
    run.add_argument("--input", help="JSON input file for the lane")

    run_all = sub.add_parser("run-all")
    run_all.add_argument("--root", dest="root_override")
    run_all.add_argument("--fixtures-dir", default="lanes", help="load lanes/<id>/fixtures/sample.json when present")

    status = sub.add_parser("status")
    status.add_argument("--root", dest="root_override")

    decide = sub.add_parser("decide")
    decide.add_argument("run_id")
    decide.add_argument("gate_id")
    decide.add_argument("decision")
    decide.add_argument("--note", default="")
    decide.add_argument("--root", dest="root_override")

    render = sub.add_parser("render")
    render.add_argument("--root", dest="root_override")

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--root", dest="root_override")
    doctor.add_argument("--lanes-root", default="lanes")

    scorecard = sub.add_parser("scorecard")
    scorecard.add_argument("--root", dest="root_override")
    scorecard.add_argument("--lanes-root", default="lanes")

    ingest = sub.add_parser("ingest-frontdoor")
    ingest.add_argument("--root", dest="root_override")
    ingest.add_argument("--file", help="JSON packet file; stdin when omitted")

    export = sub.add_parser("export-openclaw-skills")
    export.add_argument("--lanes-root", default="lanes")
    export.add_argument("--out-dir", default="out/openclaw-skills")

    install = sub.add_parser("install-openclaw-skills")
    install.add_argument("--lanes-root", default="lanes")
    install.add_argument("--target-dir", required=True)
    install.add_argument("--prefix", default="joblane-")

    proof = sub.add_parser("proof")
    proof.add_argument("--root", default="state/proof")
    proof.add_argument("--lanes-root", default="lanes")
    proof.add_argument("--output", default="out/proof/joblane-proof.json")

    args = parser.parse_args()
    root = getattr(args, "root_override", None) or args.root
    rt = JobLaneRuntime(root)
    try:
        if args.cmd == "proof":
            # Build proof in an isolated runtime owned by the proof helper.
            rt.close()
            path = build_proof_packet(
                root=args.root,
                lanes_root=args.lanes_root,
                output=args.output,
            )
            print(json.dumps({"proof": str(path)}, indent=2))
            return 0
        if args.cmd == "run":
            inputs = _read_json_file(args.input) if args.input else {}
            run_id = rt.run_lane(args.lane_id, inputs=inputs)
            print(run_id)
        elif args.cmd == "run-all":
            from .lanes import LANES

            run_ids = {
                lane_id: rt.run_lane(lane_id, inputs=_fixture_inputs(args.fixtures_dir, lane_id))
                for lane_id in LANES
            }
            print(json.dumps(run_ids, indent=2, sort_keys=True))
        elif args.cmd == "status":
            print(json.dumps(rt.status(), indent=2, sort_keys=True))
        elif args.cmd == "decide":
            rt.decide_gate(
                run_id=args.run_id,
                gate_id=args.gate_id,
                decision=args.decision,
                note=args.note,
            )
            print(json.dumps({"ok": True, "run_id": args.run_id, "gate_id": args.gate_id}, indent=2))
        elif args.cmd == "render":
            paths = MarkdownSurface(Path(root) / "surfaces" / "markdown", rt.ledger).render_waiting_gates()
            print(json.dumps([str(path) for path in paths], indent=2))
        elif args.cmd == "doctor":
            report = Doctor(rt.ledger, lanes_root=args.lanes_root).run()
            print(
                json.dumps(
                    {"ok": report.ok, "issues": report.issues, "summary": report.summary},
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0 if report.ok else 1
        elif args.cmd == "scorecard":
            print(
                json.dumps(
                    Scorecard(rt.ledger, lanes_root=args.lanes_root).to_dict(),
                    indent=2,
                    sort_keys=True,
                )
            )
        elif args.cmd == "ingest-frontdoor":
            raw = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
            result = ingest_frontdoor_packet(rt.ledger, json.loads(raw))
            print(json.dumps(result.__dict__, indent=2, sort_keys=True))
        elif args.cmd == "export-openclaw-skills":
            paths = export_openclaw_skills(lanes_root=args.lanes_root, out_dir=args.out_dir)
            print(json.dumps([str(path) for path in paths], indent=2))
        elif args.cmd == "install-openclaw-skills":
            rt.close()
            paths = install_openclaw_skills(
                lanes_root=args.lanes_root,
                target_dir=args.target_dir,
                prefix=args.prefix,
            )
            print(json.dumps([str(path) for path in paths], indent=2))
            return 0
        return 0
    finally:
        rt.close()


def _read_json_file(path: str | None) -> dict:
    if not path:
        return {}
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"joblane: input file must contain a JSON object: {path}")
    return value


def _fixture_inputs(fixtures_dir: str, lane_id: str) -> dict:
    path = Path(fixtures_dir) / lane_id / "fixtures" / "sample.json"
    return _read_json_file(str(path)) if path.exists() else {}


if __name__ == "__main__":
    raise SystemExit(main())
