from __future__ import annotations

import json
from pathlib import Path

from .gates import content_hash
from .ledger import Ledger
from .paths import DEFAULT_LANES_ROOT
from .scheduler import Scheduler
from .scorecard import Scorecard


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

    def render_board(self, *, lanes_root: Path | str = DEFAULT_LANES_ROOT) -> Path:
        status = self.ledger.status()
        scorecard = Scorecard(self.ledger, lanes_root=lanes_root).to_dict()
        due = Scheduler(self.ledger, lanes_root=lanes_root).due()
        path = self.root / "BOARD.md"
        body = self._render_board(status=status, scorecard=scorecard, due=due)
        path.write_text(body, encoding="utf-8")
        self.ledger.record_surface_ref(
            surface_ref="markdown:board",
            run_id="system",
            surface=self.surface_id,
            content_hash=content_hash(body),
            path=str(path),
        )
        return path

    def _render_board(self, *, status: dict, scorecard: dict, due: list[dict]) -> str:
        lines = [
            "# JobLane Board",
            "",
            "This file is a projection of the ledger. Deleting it loses no state.",
            "",
            "## Needs Attention",
            "",
        ]
        waiting = status["waiting_gates"]
        if waiting:
            for item in waiting:
                lines.append(f"- `{item['run_id']}` at `{item['gate_id']}`: {item['prompt']}")
        else:
            lines.append("- Nothing waiting on a human decision.")
        lines.extend(["", "## Active Companion Sessions", ""])
        sessions = status.get("active_companion_sessions", [])
        if sessions:
            for item in sessions:
                lines.append(
                    f"- `{item['session_id']}` · lane `{item['lane_id']}` · run `{item['run_id']}`"
                )
        else:
            lines.append("- No active companion sessions.")
        lines.extend(["", "## Pending Control Intents", ""])
        intents = status.get("pending_control_intents", [])
        if intents:
            for item in intents:
                target = f" for `{item['run_id']}`" if item.get("run_id") else ""
                lines.append(f"- `{item['action']}` on `{item['lane_id']}`{target}: {item['note']}")
        else:
            lines.append("- No pending control intents.")
        lines.extend(["", "## Schedule Due", ""])
        due_rows = [item for item in due if item["due"]]
        if due_rows:
            for item in due_rows:
                lines.append(f"- `{item['lane_id']}`: {item['reason']}")
        else:
            lines.append("- No scheduled lanes are currently due.")
        lines.extend(["", "## Job Coverage", ""])
        lines.append("| Job | Score | Status |")
        lines.append("|---|---:|---|")
        for job in sorted(scorecard):
            row = scorecard[job]
            lines.append(f"| {job} | {row['score']} | {row['status']} |")
        lines.extend(["", "## Recent Runs", ""])
        for item in status["runs"][-10:]:
            lines.append(
                f"- `{item['run_id']}` · lane `{item['lane_id']}` · Job {item['job']} · `{item['status']}`"
            )
        lines.append("")
        return "\n".join(lines)

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
