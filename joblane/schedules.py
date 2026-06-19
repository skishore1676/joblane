from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


class ScheduleError(ValueError):
    pass


@dataclass(frozen=True)
class ScheduleSpec:
    kind: str
    time: str | None = None
    days: tuple[str, ...] = ()
    interval_hours: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "time": self.time,
            "days": list(self.days),
            "interval_hours": self.interval_hours,
        }


def parse_schedule(raw: Any) -> ScheduleSpec:
    if raw is None:
        return ScheduleSpec(kind="manual")
    if not isinstance(raw, dict):
        raise ScheduleError("schedule must be an object")
    kind = str(raw.get("kind") or "").strip()
    if kind not in {"manual", "daily", "weekly", "interval_hours"}:
        raise ScheduleError(f"unsupported schedule kind: {kind}")
    time = raw.get("time")
    if time is not None:
        time = _parse_time(str(time))
    days = tuple(str(day).lower() for day in raw.get("days", []) if str(day).strip())
    if kind == "weekly":
        if not days:
            raise ScheduleError("weekly schedule requires days")
        invalid = sorted(set(days) - set(WEEKDAYS))
        if invalid:
            raise ScheduleError(f"invalid weekly days: {', '.join(invalid)}")
    interval_hours = raw.get("interval_hours")
    if kind == "interval_hours":
        try:
            interval_hours = int(interval_hours)
        except Exception as exc:
            raise ScheduleError("interval_hours schedule requires interval_hours") from exc
        if interval_hours < 1:
            raise ScheduleError("interval_hours must be positive")
    else:
        interval_hours = None
    if kind in {"daily", "weekly"} and time is None:
        raise ScheduleError(f"{kind} schedule requires time")
    return ScheduleSpec(kind=kind, time=time, days=days, interval_hours=interval_hours)


def due_status(
    *,
    schedule: ScheduleSpec,
    lane_id: str,
    now: datetime,
    last_run_at: datetime | None,
) -> dict[str, Any]:
    if schedule.kind == "manual":
        return _status(lane_id, schedule, False, "manual")
    if schedule.kind == "daily":
        if _already_ran_today(last_run_at, now):
            return _status(lane_id, schedule, False, "already ran today", last_run_at)
        due = _time_reached(schedule, now)
        return _status(
            lane_id,
            schedule,
            due,
            "daily time reached" if due else "daily time not reached",
            last_run_at,
        )
    if schedule.kind == "weekly":
        if WEEKDAYS[now.weekday()] not in schedule.days:
            return _status(lane_id, schedule, False, "not scheduled today", last_run_at)
        if _already_ran_today(last_run_at, now):
            return _status(lane_id, schedule, False, "already ran today", last_run_at)
        due = _time_reached(schedule, now)
        return _status(
            schedule=schedule,
            lane_id=lane_id,
            due=due,
            reason="weekly time reached" if due else "weekly time not reached",
            last_run_at=last_run_at,
        )
    if schedule.kind == "interval_hours":
        if last_run_at is None:
            return _status(lane_id, schedule, True, "never run", last_run_at)
        due = now - last_run_at >= timedelta(hours=int(schedule.interval_hours or 0))
        return _status(lane_id, schedule, due, "interval elapsed" if due else "interval not elapsed", last_run_at)
    raise ScheduleError(f"unsupported schedule kind: {schedule.kind}")


def parse_now(value: str | None = None) -> datetime:
    if not value:
        return datetime.now(UTC).replace(tzinfo=None)
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _parse_time(value: str) -> str:
    parts = value.split(":")
    if len(parts) != 2:
        raise ScheduleError("time must be HH:MM")
    hour, minute = int(parts[0]), int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ScheduleError("time must be HH:MM")
    return f"{hour:02d}:{minute:02d}"


def _time_reached(schedule: ScheduleSpec, now: datetime) -> bool:
    if not schedule.time:
        return False
    hour, minute = (int(part) for part in schedule.time.split(":"))
    return (now.hour, now.minute) >= (hour, minute)


def _already_ran_today(last_run_at: datetime | None, now: datetime) -> bool:
    return bool(last_run_at and last_run_at.date() == now.date())


def _status(
    lane_id: str,
    schedule: ScheduleSpec,
    due: bool,
    reason: str,
    last_run_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "lane_id": lane_id,
        "due": due,
        "reason": reason,
        "schedule": schedule.to_dict(),
        "last_run_at": last_run_at.isoformat(timespec="seconds") if last_run_at else None,
    }
