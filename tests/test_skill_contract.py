import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "pd-rw-research"
ENTRY = SKILL / "SKILL.md"


class SkillContractTests(unittest.TestCase):
    def test_workbuddy_frontmatter_and_short_entry(self):
        text = ENTRY.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        front = text.split("---", 2)[1]
        for key in ("name", "description", "display_name", "display_name_en",
                    "description_zh", "description_en", "version", "author"):
            self.assertRegex(front, rf"(?m)^{re.escape(key)}:")
        self.assertIn("name: pd-rw-research", front)
        self.assertLess(len(text.splitlines()), 160)

    def test_references_are_real_and_opt_in(self):
        text = ENTRY.read_text(encoding="utf-8")
        refs = re.findall(r"\[references/([^\]]+)\]\(references/([^\)]+)\)", text)
        self.assertEqual(len(refs), 3)
        for label, target in refs:
            self.assertEqual(label, target)
            self.assertTrue((SKILL / "references" / target).is_file())

    def test_example_mapping_is_structured_but_not_real(self):
        item = json.loads((ROOT / "config" / "project-map.example.json").read_text("utf-8"))
        self.assertEqual(item["schema_version"], 1)
        self.assertIn("example-project", item["projects"])
        self.assertIn("example", item["projects"]["example-project"]["root"])


if __name__ == "__main__":
    unittest.main()
