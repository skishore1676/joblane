from __future__ import annotations

from .ledger import Ledger


class ControlTower:
    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger

    def needs_attention(self) -> list[dict]:
        return self.ledger.status()["waiting_gates"]

    def summary(self) -> dict:
        status = self.ledger.status()
        return {
            "runs": len(status["runs"]),
            "waiting": len(status["waiting_gates"]),
            "counts": status["counts"],
        }

