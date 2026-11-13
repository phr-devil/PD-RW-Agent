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
        self.assertIn("version: 0.6.0", front)

    def test_registered_project_requires_real_mcp_preflight_when_available(self):
        text = ENTRY.read_text(encoding="utf-8")
        self.assertIn("MCP-first for a registered, permitted project", text)
        self.assertIn("actually call `get_project_context(project_id)` once", text)
        self.assertIn("compare", text.casefold())
        self.assertIn("MCP_NOT_USED", text)
        self.assertIn("audit_project_state(project_id)", text)
        self.assertIn("independent proof of project identity", text)
        self.assertIn("independent permitted read-only evidence review", text)
        self.assertIn("actual MCP tool names and statuses", text)

    def test_references_are_real_and_opt_in(self):
        text = ENTRY.read_text(encoding="utf-8")
        refs = re.findall(r"\[references/([^\]]+)\]\(references/([^\)]+)\)", text)
        self.assertEqual({target for _, target in refs},
                         {"integration.md", "execution.md", "troubleshooting.md", "INDEX.json"})
        for label, target in refs:
            self.assertEqual(label, target)
            self.assertTrue((SKILL / "references" / target).is_file())

    def test_reference_index_is_optional_metadata_with_existing_targets(self):
        index = json.loads((SKILL / "references" / "INDEX.json").read_text("utf-8"))
        self.assertEqual(index["schema_version"], 1)
        names = {item["file"] for item in index["references"]}
        self.assertEqual(names, {"integration.md", "execution.md", "troubleshooting.md"})
        for item in index["references"]:
            self.assertTrue((SKILL / "references" / item["file"]).is_file())
            self.assertEqual(item["authority"], "ADAPTER_GUIDANCE_ONLY")
            self.assertTrue(item["triggers"])

    def test_example_mapping_is_structured_but_not_real(self):
        item = json.loads((ROOT / "config" / "project-map.example.json").read_text("utf-8"))
        self.assertEqual(item["schema_version"], 1)
        self.assertIn("example-project", item["projects"])
        self.assertIn("example", item["projects"]["example-project"]["root"])


if __name__ == "__main__":
    unittest.main()
