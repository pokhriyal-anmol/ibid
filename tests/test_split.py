"""The section splitter on synthetic lines, so a parser regression fails CI without the source PDFs."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ibid.parse import _split  # noqa: E402


class SplitTest(unittest.TestCase):
    def test_subsections_start_at_their_own_label_and_the_root_lists_them(self) -> None:
        lines = [("5. Heading text.", False), ("(1) First sub text.", False),
                 ("more of first.", False), ("(2) Second sub text.", False)]
        by = {p.citation: p for p in _split("BNS", 5, lines)}
        self.assertEqual(sorted(by), ["BNS 5", "BNS 5(1)", "BNS 5(2)"])
        self.assertEqual(by["BNS 5(1)"].text, "(1) First sub text. more of first.")
        self.assertEqual(by["BNS 5(2)"].text, "(2) Second sub text.")
        self.assertEqual(by["BNS 5"].children, ("BNS 5(1)", "BNS 5(2)"))
        self.assertTrue(by["BNS 5"].text.startswith("5. Heading text. (1) First"))

    def test_runs_of_spaces_and_wrapped_lines_are_collapsed_to_single_spaces(self):
        lines = [("5. Heading   text.", False), ("(1) First   sub", False), ("   wrapped    line  here", False)]
        by = {p.citation: p for p in _split("BNS", 5, lines)}
        self.assertEqual(by["BNS 5(1)"].text, "(1) First sub wrapped line here")
        self.assertEqual(by["BNS 5"].text, "5. Heading text. (1) First sub wrapped line here")


if __name__ == "__main__":
    unittest.main()
