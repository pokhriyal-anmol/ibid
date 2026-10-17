"""Slice 7 ticket 02: `ibid links list`, IPC definition-punishment links from headings."""
import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid import index
from ibid.cli import main
from ibid.ipc import parse_ipc
from ibid.parse import Provision, parse_bns
from pdfs import BNS_PDF, IPC_PDF

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
] + [(f"BNS {n}", f"{n}. Text.") for n in range(1, 6)]


def entry(ipc, bns, verified=True):
    return {"ipc": ipc, "bns": bns, "type": "merged" if len(ipc) > 1 else "one-to-one", "verified": verified}


CONC = [
    entry(["IPC 10"], ["BNS 1"]), entry(["IPC 11"], ["BNS 2"]),   # carries 10 <-> 11 to BNS 1 <-> 2
    entry(["IPC 13"], ["BNS 3"], verified=False), entry(["IPC 15"], ["BNS 4"]),  # unverified: no link
    entry(["IPC 9", "IPC 9A"], ["BNS 5"]),  # both ends serve the same BNS section: no link
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

    def conc(self, entries=CONC, name="c.json", pin=None) -> str:
        path = self.tmp / name
        path.write_text(json.dumps(entries))
        path.with_suffix(".sha256").write_text(pin or hashlib.sha256(path.read_bytes()).hexdigest())
        return str(path)

    def test_exact_matches_only_both_ways_in_numeric_order(self):
        code, out = run("links", "list", "--index", self.build(MINI), "--concordance", self.conc())
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[:4], ["IPC 9 <-> IPC 9A", "IPC 10 <-> IPC 11", "IPC 13 <-> IPC 15", "IPC pairs: 3"])

    def test_bns_links_only_through_verified_entries_and_distinct_sections(self):
        _, out = run("links", "list", "--index", self.build(MINI), "--concordance", self.conc())
        self.assertEqual(out.splitlines()[4:], ["BNS 1 <-> BNS 2", "BNS pairs: 1"])

    def test_pin_mismatch_is_refused(self):
        code, out = run("links", "list", "--index", self.build(MINI), "--concordance", self.conc(pin="0" * 64))
        self.assertEqual((code, out), (1, ""))

    def test_two_runs_are_byte_identical(self):
        args = ("links", "list", "--index", self.build(MINI), "--concordance", self.conc())
        self.assertEqual(run(*args), run(*args))

    def test_real_index(self):
        before = snapshot()
        path = str(self.tmp / "real.sqlite")
        index.build(path, parse_bns(BNS_PDF) + parse_ipc(IPC_PDF), []).close()
        args = ("links", "list", "--index", path, "--concordance", "concordance/v3.json")
        _, out = run(*args)
        self.assertEqual(out, run(*args)[1])
        lines = out.splitlines()
        n = lines.index("IPC pairs: 23")
        self.assertEqual(lines[-1], f"BNS pairs: {len(lines) - n - 2}")
        self.assertEqual(lines[-1], "BNS pairs: 2")  # measured; 300/302 -> BNS 101/103 BNS 101-103 and 170-173; 378/379 share BNS 303
        lines = lines[:n + 1]
        for pair in ("IPC 300 <-> IPC 302", "IPC 375 <-> IPC 376", "IPC 378 <-> IPC 379"):
            self.assertIn(pair, lines)
        self.assertEqual(lines[-1], f"IPC pairs: {len(lines) - 1}")
        self.assertEqual(lines[-1], "IPC pairs: 23")  # the spec's expectation, measured on this index
        self.assertEqual(before, snapshot())


if __name__ == "__main__":
    unittest.main()
