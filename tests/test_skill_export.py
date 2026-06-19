from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.paths import STARTER_LANES_ROOT
from joblane.skill_export import export_openclaw_skills, install_openclaw_skills


class SkillExportTest(unittest.TestCase):
    def test_exports_openclaw_frontdoor_skills(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            paths = export_openclaw_skills(
                lanes_root=STARTER_LANES_ROOT,
                out_dir=Path(tmp) / "skills",
            )
            self.assertEqual(len(paths), 6)
            text = (Path(tmp) / "skills" / "chief_of_staff" / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Orchestrator of record: `joblane`", text)
            self.assertIn("proposed_memories", text)

    def test_installs_openclaw_skills_to_target_dir(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            paths = install_openclaw_skills(
                lanes_root=STARTER_LANES_ROOT,
                target_dir=Path(tmp) / "openclaw" / "skills",
            )
            self.assertEqual(len(paths), 6)
            self.assertTrue((Path(tmp) / "openclaw" / "skills" / "joblane-reflection" / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
