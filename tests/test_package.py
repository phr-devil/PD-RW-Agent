import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_zip_contains_one_skill_and_no_local_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "out.zip"
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "package_skill.py"),
                 "--output", str(destination)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(destination) as package:
                names = package.namelist()
                self.assertIn("pd-rw-research/SKILL.md", names)
                self.assertIn("pd-rw-research/scripts/bridge.py", names)
                self.assertTrue(all(name.startswith("pd-rw-research/") for name in names))
                self.assertFalse(any("project-map.local" in name for name in names))


if __name__ == "__main__":
    unittest.main()
