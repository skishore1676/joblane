from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from joblane.skill_export import export_openclaw_skills


class SkillExportTest(unittest.TestCase):
    def test_exports_openclaw_frontdoor_skills(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            paths = export_openclaw_skills(
                lanes_root=repo / "lanes",
                out_dir=Path(tmp) / "skills",
            )
            self.assertEqual(len(paths), 6)
            text = (Path(tmp) / "skills" / "chief_of_staff" / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Orchestrator of record: `joblane`", text)
            self.assertIn("proposed_memories", text)


if __name__ == "__main__":
    unittest.main()

