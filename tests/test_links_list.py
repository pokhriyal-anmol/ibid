"""Slice 7 ticket 02: `ibid links list`, IPC definition-punishment links from headings."""
import contextlib
import hashlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid import index
from ibid.cli import main
from ibid.ipc import parse_ipc
from ibid.parse import Provision
from pdfs import IPC_PDF

ROOT = Path(__file__).resolve().parent.parent
GUARDED = ("results", "gold", "concordance")

MINI = [
    ("IPC 10", "10. Theft.—Whoever steals."),
    ("IPC 11", "11. Punishment for theft.—Shall be punished."),
    ("IPC 12", "12. Punishment for arson.—Shall be punished."),  # no section headed Arson
    ("IPC 13", "13. Punishment for fraud.—Shall be punished."),
    ("IPC 14", "14. Fraud by a public servant.—Contains the term but is not headed by it."),
    ("IPC 15", "15. Fraud.—  Defined."),
    ("IPC 9A", "9A. Punishment for Robbery. —Upper case and a space before the dash."),
    ("IPC 9", "9. ROBBERY.—Upper case."),
    ("IPC 11(1)", "11(1) Theft."),  # a sub-provision never counts
]


def run(*args: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(list(args))
    return code, out.getvalue()


def snapshot() -> dict[str, str]:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for d in GUARDED for p in sorted((ROOT / d).rglob("*")) if p.is_file()}


class LinksListTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def build(self, rows, name="i.sqlite") -> str:
        path = str(self.tmp / name)
        provs = [Provision(c, t, c.split("(")[0] if "(" in c else None, ()) for c, t in rows]
        index.build(path, provs, []).close()
        return path

    def test_exact_matches_only_both_ways_in_numeric_order(self):
        code, out = run("links", "list", "--index", self.build(MINI))
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["IPC 9 <-> IPC 9A", "IPC 10 <-> IPC 11", "IPC 13 <-> IPC 15", "IPC pairs: 3"])

    def test_two_runs_are_byte_identical(self):
        path = self.build(MINI)
        self.assertEqual(run("links", "list", "--index", path), run("links", "list", "--index", path))

    def test_real_index(self):
        before = snapshot()
        path = str(self.tmp / "real.sqlite")
        index.build(path, parse_ipc(IPC_PDF), []).close()
        _, out = run("links", "list", "--index", path)
        lines = out.splitlines()
        for pair in ("IPC 300 <-> IPC 302", "IPC 375 <-> IPC 376", "IPC 378 <-> IPC 379"):
            self.assertIn(pair, lines)
        self.assertEqual(lines[-1], f"IPC pairs: {len(lines) - 1}")
        self.assertEqual(lines[-1], "IPC pairs: 23")  # the spec's expectation, measured on this index
        self.assertEqual(before, snapshot())


if __name__ == "__main__":
    unittest.main()
