from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from joblane.drawers import DrawerManager


class DrawerManagerTest(unittest.TestCase):
    def test_drawers_are_declared_outside_lane_source(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            manager = DrawerManager(Path(tmp), lanes_root=repo / "lanes")
            refs = manager.refs()
            self.assertTrue(refs)
            self.assertTrue(all(not ref.exists for ref in refs))

            ensured = manager.ensure()
            self.assertTrue(all(ref.exists for ref in ensured))
            self.assertTrue((Path(tmp) / "lanes" / "reflection" / "work").is_dir())
            self.assertFalse((repo / "lanes" / "reflection" / "work").exists())

    def test_drawers_cli(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            result = json.loads(
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "joblane.cli",
                        "drawers",
                        "--ensure",
                        "--lanes-root",
                        str(repo / "lanes"),
                        "--root",
                        tmp,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
            self.assertTrue(any(row["lane_id"] == "fitness" for row in result))
            self.assertTrue(all(row["exists"] for row in result))


if __name__ == "__main__":
    unittest.main()

