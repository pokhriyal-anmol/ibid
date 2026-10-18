"""Slice 9 ticket 1: ADR 0008 exists and carries the decision rule's links and thresholds."""
import unittest
from pathlib import Path

ADR = Path(__file__).resolve().parents[1] / "docs/adr/0008-association-layer-fitted-on-both-kinds-of-text.md"
NEEDED = ["0005-learned-association-layer", "0006-association-layer-fitted", "D-002", "D-003",
          "15.3", "16.3", "49.8", "59.2", "33.4", "Q-005"]


class Adr0008(unittest.TestCase):
    def test_links_and_thresholds(self) -> None:
        text = ADR.read_text()
        self.assertEqual([n for n in NEEDED if n not in text], [])


if __name__ == "__main__":
    unittest.main()
