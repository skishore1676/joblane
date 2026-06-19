from __future__ import annotations

import json
import unittest

from joblane.acceptance import evaluate_job_artifacts


def row(content: dict) -> dict:
    return {"content_json": json.dumps(content)}


class AcceptanceTest(unittest.TestCase):
    def test_rejects_thin_public_presence_packet(self) -> None:
        result = evaluate_job_artifacts("A", [row({"headline": "hi", "x_posts": ["one"]})])
        self.assertFalse(result.ok)
        self.assertIn("public packet", result.gaps[0])

    def test_accepts_trading_read_only_synthesis(self) -> None:
        result = evaluate_job_artifacts(
            "C",
            [
                row(
                    {
                        "mode": "read_only",
                        "anomalies": ["stale cache"],
                        "evidence_refs": ["a", "b"],
                        "forbidden": ["submit_order", "cancel_order", "transfer_cash"],
                        "trade_authority": False,
                    }
                )
            ],
        )
        self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
