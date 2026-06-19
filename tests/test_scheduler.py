from __future__ import annotations

from datetime import UTC, datetime
import tempfile
import unittest
from pathlib import Path

from joblane.lane_packs import load_lane_packs
from joblane.runtime import JobLaneRuntime
from joblane.scheduler import Scheduler
from joblane.schedules import due_status, parse_schedule


class SchedulerTest(unittest.TestCase):
    def test_lane_packs_declare_portable_schedules(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        packs = load_lane_packs(repo / "lanes")

        self.assertEqual(packs["fitness"].schedule.kind, "manual")
        self.assertEqual(packs["chief_of_staff"].schedule.kind, "daily")
        self.assertEqual(packs["reflection"].schedule.days, ("fri",))

    def test_due_status_respects_time_and_same_day_run(self) -> None:
        schedule = parse_schedule({"kind": "daily", "time": "08:30"})
        now = datetime.fromisoformat("2026-06-19T09:00:00")

        self.assertTrue(
            due_status(
                schedule=schedule,
                lane_id="chief_of_staff",
                now=now,
                last_run_at=None,
            )["due"]
        )
        self.assertFalse(
            due_status(
                schedule=schedule,
                lane_id="chief_of_staff",
                now=now,
                last_run_at=datetime.fromisoformat("2026-06-19T08:45:00"),
            )["due"]
        )
        not_reached = due_status(
            schedule=schedule,
            lane_id="chief_of_staff",
            now=datetime.fromisoformat("2026-06-19T08:00:00"),
            last_run_at=None,
        )
        self.assertFalse(not_reached["due"])
        self.assertEqual(not_reached["reason"], "daily time not reached")

    def test_scheduler_reads_due_lanes_from_ledger_and_lane_packs(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            rt = JobLaneRuntime(Path(tmp))
            try:
                due_before = Scheduler(rt.ledger, lanes_root=repo / "lanes").due_lanes(
                    now="2026-06-19T17:00:00"
                )
                self.assertIn("chief_of_staff", due_before)
                self.assertIn("reflection", due_before)

                rt.run_lane("chief_of_staff")
                due_after = Scheduler(rt.ledger, lanes_root=repo / "lanes").due_lanes(
                    now=datetime.now(UTC).replace(tzinfo=None)
                )
                self.assertNotIn("chief_of_staff", due_after)
            finally:
                rt.close()


if __name__ == "__main__":
    unittest.main()
