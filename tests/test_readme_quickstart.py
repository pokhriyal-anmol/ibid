"""The README Quickstart is the setup sequence, with no manual fetch, hash check or export step."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def quickstart() -> str:
    text = (ROOT / "README.md").read_text()
    return re.search(r"^## Quickstart\n(.*?)^## ", text, re.S | re.M).group(1)


class QuickstartTest(unittest.TestCase):
    def test_has_the_setup_sequence_in_order(self):
        q = quickstart()
        steps = ["uv sync", "uv run ibid setup --fetch bns", "uv run ibid setup --fetch ipc --url", "uv run ibid setup\n",
                 "uv run ibid eval", "unittest discover"]
        at = [q.find(s) for s in steps]
        self.assertNotIn(-1, at, dict(zip(steps, at)))
        self.assertEqual(at, sorted(at))

    def test_ipc_step_explains_expiring_link(self):
        q = quickstart()
        self.assertIn("expires", q)
        self.assertIn("data/SOURCES.md", q)

    def test_no_manual_fetch_hash_or_export(self):
        q = quickstart().lower()
        for bad in ("export ibid_", "check the hashes", "by hand", "into `data/raw/`"):
            self.assertNotIn(bad, q)

    def test_sources_md_points_at_manifest(self):
        self.assertIn("data/sources.json", (ROOT / "data" / "SOURCES.md").read_text())

    def test_agents_lists_setup(self):
        self.assertIn("ibid setup", (ROOT / "AGENTS.md").read_text())


if __name__ == "__main__":
    unittest.main()
