from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from joblane.runtime import JobLaneRuntime
from joblane.surfaces import MarkdownSurface


class BoardSurfaceTest(unittest.TestCase):
    def test_board_projects_needs_attention_and_scorecard(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rt = JobLaneRuntime(root)
            try:
                rt.run_lane("public_presence")
                rt.run_lane("trading_intel")
                surface = MarkdownSurface(root / "vault", rt.ledger)
                path = surface.render_board(lanes_root=repo / "lanes")
                text = path.read_text(encoding="utf-8")
                self.assertIn("Needs Attention", text)
                self.assertIn("Schedule Due", text)
                self.assertIn("taste_gate", text)
                self.assertIn("| A |", text)
                path.unlink()
                rerendered = surface.render_board(lanes_root=repo / "lanes")
                self.assertIn("taste_gate", rerendered.read_text(encoding="utf-8"))
                self.assertEqual(rt.status()["counts"]["runs"], 2)
            finally:
                rt.close()


if __name__ == "__main__":
    unittest.main()
