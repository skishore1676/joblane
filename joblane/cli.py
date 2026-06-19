from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .doctor import Doctor
from .frontdoor import ingest_frontdoor_packet
from .runtime import JobLaneRuntime
from .scorecard import Scorecard
from .skill_export import export_openclaw_skills
from .surfaces import MarkdownSurface


def main() -> int:
    parser = argparse.ArgumentParser(prog="joblane")
    parser.add_argument("--root", default="state/local")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run")
    run.add_argument("lane_id")
    run.add_argument("--root", dest="root_override")

    run_all = sub.add_parser("run-all")
    run_all.add_argument("--root", dest="root_override")

    status = sub.add_parser("status")
    status.add_argument("--root", dest="root_override")

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

    args = parser.parse_args()
    root = getattr(args, "root_override", None) or args.root
    rt = JobLaneRuntime(root)
    try:
        if args.cmd == "run":
            run_id = rt.run_lane(args.lane_id)
            print(run_id)
        elif args.cmd == "run-all":
            from .lanes import LANES

            run_ids = {lane_id: rt.run_lane(lane_id) for lane_id in LANES}
            print(json.dumps(run_ids, indent=2, sort_keys=True))
        elif args.cmd == "status":
            print(json.dumps(rt.status(), indent=2, sort_keys=True))
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
        return 0
    finally:
        rt.close()


if __name__ == "__main__":
    raise SystemExit(main())
