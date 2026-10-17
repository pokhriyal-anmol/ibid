"""Slice 8 ticket 01: `ibid headings list` reads margin headings without touching the index or any pin."""
import contextlib
import hashlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid.cli import main
from ibid.headings import parse_layout
from ibid.parse import PARSER_VERSION
from pdfs import BNS_PDF, IPC_PDF

ROOT = Path(__file__).resolve().parent.parent
GUARDED = ("results", "gold", "concordance")
WIDTH = 78


def right(body: str, note: str = "") -> str:
    return body.ljust(WIDTH) + note if note else body


def left(note: str, body: str) -> str:
    return note.ljust(18) + body


# Invented pages shaped like the gazette: a margin on the right of the body, then one on the left.
PAGES = [
    "\n".join([
        right("      1. Whoever does a thing shall be punished with fine which may", "Short title,"),
        right("extend to ten rupees, and with such further punishment as the Court", "commencement"),
        right("may order, and the body runs on past the end of the heading.", "and application."),
        right("      (2) A sub-provision has no heading of its own."),
        right("      2. Nothing is an offence which is done by accident or", "Accident."),
        right("misfortune, and the body of this section wraps well past its heading,"),
        right("over a third line, and a fourth."),
        right("                         CHAPTER II"),
        right("                       OF THINGS DONE"),
        right("      3. Whoever does a third thing shall be punished with fine.", "Third thing,"),
        right("", "wrapped twice,"),
        right("section 4. The sentence is body text.", "and so on."),
    ]),
    "\n".join([
        left("", "                 body of section 3 carries over to this page."),
        left("Fourth", "     4. Whoever does a fourth thing shall be punished."),
        left("thing and its", "                 the body wraps here."),
        left("punishment.", ""),
        left("", "                         CHAPTER III"),
        left("Fifth, headed", ""),
        left("on the line above", ""),
        left("its number.", "     5. A section whose heading starts above its number row."),
        left("", "                 body of five."),
        left("Sixth.", "     6. Whoever does a sixth thing."),
        left("", "                 (2) A sub-provision of six."),
    ]),
    "\n".join([
        right("      7. A section with no printed margin heading at all, shall be punished."),
        right("      8. Last one in the fixture shall be punished with fine.", "Eighth."),
    ]),
]
LAYOUT = "\f".join(PAGES)

EXPECTED = [
    "BNS 1\tShort title, commencement and application.",
    "BNS 2\tAccident.",
    "BNS 3\tThird thing, wrapped twice, and so on.",
    "BNS 4\tFourth thing and its punishment.",
    "BNS 5\tFifth, headed on the line above its number.",
    "BNS 6\tSixth.",
    "BNS 7\t",
    "BNS 8\tEighth.",
    "with heading: 7",
    "without heading: 1",
    "BNS 7",
]


def run(*args: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(["headings", "list", *args])
    return code, out.getvalue()


def snapshot() -> dict[str, str]:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for d in GUARDED for p in sorted((ROOT / d).rglob("*")) if p.is_file()}


class HeadingsFixtureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def lines(self, text: str = LAYOUT) -> list[str]:
        path = self.tmp / "layout.txt"
        path.write_text(text)
        code, out = run("--act", "bns", "--layout", str(path))
        self.assertEqual(code, 0)
        return out.splitlines()

    def test_whole_listing(self):
        self.assertEqual(self.lines(), EXPECTED)

    def test_each_heading_belongs_to_its_own_section(self):
        got = dict(ln.split("\t") for ln in self.lines() if "\t" in ln)
        self.assertEqual((got["BNS 2"], got["BNS 3"]), ("Accident.", "Third thing, wrapped twice, and so on."))

    def test_a_wrapped_heading_is_joined_not_cut_after_its_first_line(self):
        self.assertIn("BNS 1\tShort title, commencement and application.", self.lines())

    def test_a_chapter_title_is_never_a_heading(self):
        text = "\n".join(self.lines())
        self.assertNotIn("CHAPTER", text)
        self.assertNotIn("OF THINGS", text)

    def test_a_left_note_one_space_from_the_body_is_not_lost(self):
        page = "\n".join([left("Using as", "     1. Whoever uses a thing as genuine, shall be punished"),
                          "genuine, forged other persons, and so the body goes on.",
                          "misappropriation of property, ends here."])
        self.assertEqual(parse_layout(page), [("BNS 1", "Using as genuine, forged misappropriation of")])

    def test_no_sub_provision_is_listed(self):
        self.assertFalse([ln for ln in self.lines() if ln.startswith("BNS ") and "(" in ln.split("\t")[0]])


class HeadingsRealPdfTest(unittest.TestCase):
    def test_bns(self):
        before = snapshot()
        code, out = run("--act", "bns", "--bns", BNS_PDF)
        self.assertEqual(code, 0)
        lines = out.splitlines()
        n = lines.index(next(ln for ln in lines if ln.startswith("with heading: ")))
        rows, missing = lines[:n], lines[n + 2:]
        self.assertEqual(len(rows), 358)
        with_n, without_n = int(lines[n].split(": ")[1]), int(lines[n + 1].split(": ")[1])
        self.assertGreaterEqual(with_n, 350)
        self.assertEqual((with_n + without_n, len(missing)), (358, without_n))
        self.assertEqual(sorted(missing), sorted(r.split("\t")[0] for r in rows if r.endswith("\t")))
        got = dict(r.split("\t") for r in rows)
        self.assertEqual([got[f"BNS {n}"] for n in (83, 85, 86, 87)], [
            "Marriage ceremony fraudulently gone through without lawful marriage.",
            "Husband or relative of husband of a woman subjecting her to cruelty.",
            "Cruelty defined.",
            "Kidnapping, abducting or inducing woman to compel her marriage, etc."])
        self.assertFalse([r for r in rows if "(" in r.split("\t")[0]])
        self.assertEqual(PARSER_VERSION, "4")
        self.assertEqual(before, snapshot())

    def test_ipc(self):
        code, out = run("--act", "ipc", "--ipc", IPC_PDF)
        self.assertEqual(code, 0)
        lines = out.splitlines()
        n = lines.index(next(ln for ln in lines if ln.startswith("with heading: ")))
        rows = lines[:n]
        self.assertEqual(len(rows), 575)
        self.assertEqual(rows[0], "IPC 1\tTitle and extent of operation of the Code.")
        self.assertFalse([r for r in rows if "(" in r.split("\t")[0]])
        self.assertEqual(int(lines[n].split(": ")[1]) + int(lines[n + 1].split(": ")[1]), 575)


if __name__ == "__main__":
    unittest.main()
