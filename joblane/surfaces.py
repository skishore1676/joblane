from __future__ import annotations

import json
from pathlib import Path

from .gates import content_hash
from .ledger import Ledger


class MarkdownSurface:
    surface_id = "markdown"

    def __init__(self, root: Path | str, ledger: Ledger) -> None:
        self.root = Path(root)
        self.ledger = ledger
        self.root.mkdir(parents=True, exist_ok=True)

    def render_waiting_gates(self) -> list[Path]:
        paths: list[Path] = []
        for row in self.ledger.iter_waiting_gates():
            path = self.root / f"{row['run_id']}__{row['gate_id']}.md"
            body = self._render_gate(row)
            path.write_text(body, encoding="utf-8")
            h = content_hash(body)
            self.ledger.record_surface_ref(
                surface_ref=f"markdown:{row['run_id']}:{row['gate_id']}",
                run_id=row["run_id"],
                surface=self.surface_id,
                content_hash=h,
                path=str(path),
            )
            paths.append(path)
        return paths

    def _render_gate(self, row) -> str:
        artifact = json.loads(row["content_json"]) if row["content_json"] else None
        allowed = json.loads(row["allowed_json"])
        choices = "\n".join(f"- [ ] `{choice}`" for choice in allowed)
        return (
            f"---\n"
            f"run_id: {row['run_id']}\n"
            f"gate_id: {row['gate_id']}\n"
            f"action_fingerprint: {row['action_fingerprint']}\n"
            f"artifact_hash: {row['content_hash'] or ''}\n"
            f"---\n\n"
            f"# Gate: {row['gate_id']}\n\n"
            f"{row['prompt']}\n\n"
            f"## Artifact\n\n"
            f"```json\n{json.dumps(artifact, indent=2, sort_keys=True)}\n```\n\n"
            f"## Decision\n\n"
            f"{choices}\n"
        )


class TelegramSandboxSurface:
    surface_id = "telegram_sandbox"

    def __init__(self, outbox: Path | str, ledger: Ledger) -> None:
        self.outbox = Path(outbox)
        self.ledger = ledger
        self.outbox.parent.mkdir(parents=True, exist_ok=True)

    def send(self, *, run_id: str, text: str) -> None:
        packet = {"run_id": run_id, "text": text, "live_send": False}
        with self.outbox.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(packet, sort_keys=True) + "\n")
        self.ledger.record_surface_ref(
            surface_ref=f"telegram_sandbox:{run_id}",
            run_id=run_id,
            surface=self.surface_id,
            content_hash=content_hash(packet),
            path=str(self.outbox),
        )

