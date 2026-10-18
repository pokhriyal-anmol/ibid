"""Slice 9 ticket 1: ADR 0008 exists, links its parents, and carries each threshold in its own rule row."""
import re
import unittest
from pathlib import Path

ADR = Path(__file__).resolve().parents[1] / "docs/adr/0008-association-layer-fitted-on-both-kinds-of-text.md"
LINKS = ["0005-learned-association-layer", "0006-association-layer-fitted", "D-002", "D-003", "Q-005"]
ROWS = {1: "15.3", 2: "16.3", 3: "49.8", 4: "59.2", 5: "33.4"}  # comparison number -> threshold in its row


class Adr0008(unittest.TestCase):
    def test_links_and_thresholds(self) -> None:
        text = ADR.read_text()
        self.assertEqual([n for n in LINKS if n not in text], [])
        rows = dict(re.findall(r"^\| (\d) \|.*\| (.*) \|$", text, re.M))
        self.assertEqual({int(n): re.search(r"\d+\.\d", r)[0] for n, r in rows.items()}, ROWS)


if __name__ == "__main__":
    unittest.main()
