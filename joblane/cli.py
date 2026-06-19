from __future__ import annotations

import argparse
import json
from pathlib import Path

from .doctor import Doctor
from .runtime import JobLaneRuntime
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
        return 0
    finally:
        rt.close()


if __name__ == "__main__":
    raise SystemExit(main())
