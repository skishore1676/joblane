from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ProviderPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderBinding:
    provider: str
    options: dict[str, Any] = field(default_factory=dict)
    fallback: tuple["ProviderBinding", ...] = ()
    source: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "options": self.options,
            "fallback": [item.to_dict() for item in self.fallback],
            "source": self.source,
        }

    def chain(self) -> tuple["ProviderBinding", ...]:
        return (self, *self.fallback)


@dataclass(frozen=True)
class LaneProviderSpec:
    actors: dict[str, ProviderBinding] = field(default_factory=dict)
    default: ProviderBinding | None = None


@dataclass(frozen=True)
class DeploymentProviderPolicy:
    default: ProviderBinding | None = None
    lanes: dict[str, LaneProviderSpec] = field(default_factory=dict)


BUILT_IN_DEFAULT = ProviderBinding(provider="deterministic", source="built_in")


def load_lane_provider_spec(path: Path | str) -> LaneProviderSpec:
    path = Path(path)
    if not path.exists():
        return LaneProviderSpec()
    raw = _read_object(path)
    if raw.get("schema") != "joblane.providers.v1":
        raise ProviderPolicyError(f"{path} schema must be joblane.providers.v1")
    return _lane_spec_from_raw(raw, source=f"lane:{path.parent.name}")


def load_deployment_policy(path: Path | str | None) -> DeploymentProviderPolicy:
    if path is None:
        return DeploymentProviderPolicy()
    path = Path(path)
    if not path.exists():
        raise ProviderPolicyError(f"provider policy not found: {path}")
    raw = _read_object(path)
    if raw.get("schema") != "joblane.provider_policy.v1":
        raise ProviderPolicyError(f"{path} schema must be joblane.provider_policy.v1")
    default = _binding(raw.get("default"), source="deployment:default") if raw.get("default") else None
    lanes: dict[str, LaneProviderSpec] = {}
    for lane_id, lane_raw in (raw.get("lanes") or {}).items():
        if not isinstance(lane_raw, dict):
            raise ProviderPolicyError(f"{path} lanes.{lane_id} must be an object")
        lanes[str(lane_id)] = _lane_spec_from_raw(
            lane_raw,
            source=f"deployment:{lane_id}",
        )
    return DeploymentProviderPolicy(default=default, lanes=lanes)


def resolve_provider_binding(
    *,
    lane_id: str,
    actor: str,
    lane_spec: LaneProviderSpec,
    deployment: DeploymentProviderPolicy | None = None,
) -> ProviderBinding:
    deployment = deployment or DeploymentProviderPolicy()
    deployment_lane = deployment.lanes.get(lane_id)
    if deployment_lane:
        actor_binding = deployment_lane.actors.get(actor)
        if actor_binding:
            return actor_binding
        if deployment_lane.default:
            return deployment_lane.default
    if deployment.default:
        return deployment.default
    lane_actor = lane_spec.actors.get(actor)
    if lane_actor:
        return lane_actor
    if lane_spec.default:
        return lane_spec.default
    return BUILT_IN_DEFAULT


def resolved_provider_report(
    *,
    lanes_root: Path | str = "lanes",
    policy_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    from .lane_packs import load_lane_packs

    deployment = load_deployment_policy(policy_path)
    rows = []
    for pack in load_lane_packs(lanes_root).values():
        actors = sorted(pack.providers.actors) or ["default"]
        for actor in actors:
            binding = resolve_provider_binding(
                lane_id=pack.lane_id,
                actor=actor,
                lane_spec=pack.providers,
                deployment=deployment,
            )
            rows.append(
                {
                    "lane_id": pack.lane_id,
                    "actor": actor,
                    "provider": binding.provider,
                    "options": binding.options,
                    "source": binding.source,
                    "failover_chain": [item.provider for item in binding.chain()],
                }
            )
    return rows


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProviderPolicyError(f"{path} must contain a JSON object")
    return value


def _lane_spec_from_raw(raw: dict[str, Any], *, source: str) -> LaneProviderSpec:
    default = _binding(raw.get("default"), source=f"{source}:default") if raw.get("default") else None
    actors: dict[str, ProviderBinding] = {}
    for actor, actor_raw in (raw.get("actors") or {}).items():
        actors[str(actor)] = _binding(actor_raw, source=f"{source}:actor:{actor}")
    return LaneProviderSpec(actors=actors, default=default)


def _binding(raw: Any, *, source: str) -> ProviderBinding:
    if not isinstance(raw, dict):
        raise ProviderPolicyError(f"{source} binding must be an object")
    provider = str(raw.get("provider") or "").strip()
    if not provider:
        raise ProviderPolicyError(f"{source} binding requires provider")
    options = raw.get("options") or {}
    if not isinstance(options, dict):
        raise ProviderPolicyError(f"{source} options must be an object")
    fallback = tuple(_binding(item, source=f"{source}:fallback:{index}") for index, item in enumerate(raw.get("fallback") or []))
    return ProviderBinding(
        provider=provider,
        options=dict(options),
        fallback=fallback,
        source=source,
    )

