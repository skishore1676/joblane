from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from joblane.runtime import JobLaneRuntime
from joblane.surfaces import MarkdownSurface, TelegramSandboxSurface


class SurfaceProjectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rt = JobLaneRuntime(self.root)

    def tearDown(self) -> None:
        self.rt.close()
        self.tmp.cleanup()

    def test_markdown_surface_can_be_deleted_and_rerendered(self) -> None:
        self.rt.run_lane("chief_of_staff")
        surface = MarkdownSurface(self.root / "vault", self.rt.ledger)
        first = surface.render_waiting_gates()
        self.assertEqual(len(first), 1)
        first_text = first[0].read_text(encoding="utf-8")
        first[0].unlink()
        second = surface.render_waiting_gates()
        self.assertEqual(second[0].read_text(encoding="utf-8"), first_text)
        self.assertEqual(self.rt.status()["counts"]["gates"], 1)

    def test_telegram_sandbox_records_no_live_send(self) -> None:
        run_id = self.rt.run_lane("trading_intel")
        outbox = self.root / "outbox" / "telegram.jsonl"
        TelegramSandboxSurface(outbox, self.rt.ledger).send(run_id=run_id, text="hello")
        self.assertIn('"live_send": false', outbox.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

