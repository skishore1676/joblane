from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .frontdoor import ingest_frontdoor_packet

if TYPE_CHECKING:
    from .runtime import JobLaneRuntime


class SurfaceInboxError(ValueError):
    pass


@dataclass(frozen=True)
class SurfaceInboxResult:
    packet_id: str
    surface: str
    external_id: str
    intent: str
    status: str
    result: dict[str, Any]
    duplicate: bool = False


def ingest_surface_packet(runtime: JobLaneRuntime, packet: dict[str, Any]) -> SurfaceInboxResult:
    """Record and route an external-surface packet.

    Surfaces are replaceable input/output adapters. The inbox preserves the
    provenance and idempotency key before routing to a lane, companion session,
    or front-door memory packet.
    """
    surface = _required_text(packet, "surface")
    external_id = str(packet.get("external_id") or uuid.uuid4().hex)
    intent = _required_text(packet, "intent")
    payload = packet.get("payload") or {}
    if not isinstance(payload, dict):
        raise SurfaceInboxError("payload must be an object")
    lane_id = packet.get("lane_id") or payload.get("lane_id")
    if lane_id is not None:
        lane_id = str(lane_id)

    existing = runtime.ledger.get_surface_packet(surface=surface, external_id=external_id)
    if existing is not None:
        return SurfaceInboxResult(
            packet_id=str(existing["packet_id"]),
            surface=surface,
            external_id=external_id,
            intent=str(existing["intent"]),
            status=str(existing["status"]),
            result=json.loads(existing["result_json"]),
            duplicate=True,
        )

    packet_id = f"surface:{uuid.uuid4().hex[:12]}"
    runtime.ledger.put_surface_packet(
        packet_id=packet_id,
        surface=surface,
        external_id=external_id,
        lane_id=lane_id,
        intent=intent,
        payload=payload,
    )
    try:
        result = _route(runtime, surface=surface, intent=intent, lane_id=lane_id, payload=payload)
    except Exception as exc:
        failure = {"error": str(exc), "live_effect": False}
        runtime.ledger.update_surface_packet(
            packet_id=packet_id,
            status="rejected",
            result=failure,
        )
        raise
    runtime.ledger.update_surface_packet(
        packet_id=packet_id,
        status="accepted",
        result=result,
    )
    return SurfaceInboxResult(
        packet_id=packet_id,
        surface=surface,
        external_id=external_id,
        intent=intent,
        status="accepted",
        result=result,
    )


def _route(
    runtime: JobLaneRuntime,
    *,
    surface: str,
    intent: str,
    lane_id: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if intent == "companion_turn":
        session_id = _required_text(payload, "session_id")
        message = _required_text(payload, "message")
        speaker = str(payload.get("speaker") or f"surface:{surface}")
        turn = runtime.companion_turn(session_id=session_id, message=message, speaker=speaker)
        return {**turn.__dict__, "live_effect": False}
    if intent == "frontdoor_packet":
        frontdoor_packet = dict(payload)
        if lane_id and "lane_id" not in frontdoor_packet:
            frontdoor_packet["lane_id"] = lane_id
        frontdoor_packet.setdefault("requested_by", f"surface:{surface}")
        result = ingest_frontdoor_packet(
            runtime.ledger,
            frontdoor_packet,
            lanes_root=runtime.lanes_root,
        )
        return {**result.__dict__, "live_effect": False}
    if intent == "lane_run":
        if not lane_id:
            raise SurfaceInboxError("lane_id is required for lane_run")
        run_id = runtime.run_lane(lane_id, inputs=dict(payload.get("inputs") or {}))
        return {"run_id": run_id, "lane_id": lane_id, "live_effect": False}
    raise SurfaceInboxError(f"unsupported surface intent: {intent}")


def _required_text(packet: dict[str, Any], key: str) -> str:
    value = str(packet.get(key) or "").strip()
    if not value:
        raise SurfaceInboxError(f"{key} is required")
    return value
