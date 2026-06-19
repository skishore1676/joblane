from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

from .contracts import ProviderResult


@dataclass(frozen=True)
class ProviderRequest:
    role: str
    prompt: str
    context: dict[str, Any]
    trusted_input: bool = False
    allowed_outcomes: tuple[str, ...] = ()


class DeterministicProvider:
    provider_id = "deterministic"

    def run(self, request: ProviderRequest) -> ProviderResult:
        outcome = request.allowed_outcomes[0] if request.allowed_outcomes else None
        return ProviderResult(
            status="succeeded",
            outcome=outcome,
            output_text=json.dumps(
                {
                    "role": request.role,
                    "outcome": outcome,
                    "summary": request.prompt[:120],
                },
                sort_keys=True,
            ),
            data={"provider": self.provider_id, "live_effect": False},
        )


class OpenClawProvider:
    provider_id = "openclaw"

    def __init__(self, *, binary: str = "openclaw", agent: str = "main") -> None:
        self.binary = binary
        self.agent = agent

    def run(self, request: ProviderRequest) -> ProviderResult:
        if not request.trusted_input:
            return ProviderResult(
                status="failed",
                output_text="",
                failure_summary=(
                    "OpenClaw provider refused untrusted input. Use a restricted "
                    "gateway agent or route through JobLane gates/memory tools."
                ),
                data={"provider": self.provider_id, "guard": "untrusted_input_refused"},
            )
        # This bridge is intentionally conservative: the first slice proves the
        # guardrail without requiring a live OpenClaw gateway on every dev box.
        try:
            completed = subprocess.run(
                [self.binary, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except Exception as exc:
            return ProviderResult(
                status="failed",
                output_text="",
                failure_summary=f"OpenClaw unavailable: {exc}",
                data={"provider": self.provider_id},
            )
        return ProviderResult(
            status="succeeded",
            output_text=completed.stdout.strip() or completed.stderr.strip(),
            data={"provider": self.provider_id, "agent": self.agent, "live_effect": False},
        )

