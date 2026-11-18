"""Slice 15 ticket 06: the CrPC to BNSS concordance from the correspondence table, served by `ibid mcp`.
Seam: `ibid concordance from-table --acts crpc-bnss` and JSON-RPC over stdio, on an invented index and table."""
import collections
import contextlib
import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ibid import bnss, crpc, index
from ibid.cli import main
from ibid.parse import Provision
from mcp_harness import ROOT, Client, command
from pdfs import BNSS_PDF, CRPC_PDF
from test_crpc import build
from pdfs import needs_ipc

TABLE = """\
BNSS       Subject                          CrPC       Summary of Comparison
Sections                                    Sections

20         Summons to appear.               10         No change.
40         Search warrant.                  30         Split in two.
41         Seizure of property.             30         Split in two.
                                                     © Invented Author, Director
\f60         Appearance through pleader.      50 and 51  Merged.
70         Audio video electronic means.    -          Newly added.
90         Forfeiture of property.          91         Table says so.
"""

# (citation, heading, text); the text of a BNSS section carries no heading, as in the real index
SECTIONS = [
    ("CrPC 10", "Summons to appear", "A court may summon a witness to appear."),
    ("BNSS 20", "Summons to appear", "A court may summon a witness to appear."),
    ("CrPC 30", "Search and seizure", "A magistrate may issue a warrant of search and order seizure."),
    ("BNSS 40", "Search warrant", "A magistrate may issue a warrant of search."),
    ("BNSS 41", "Seizure of property", "A police officer may effect seizure of property found."),
    ("CrPC 50", "Appearance by pleader", "The accused may appear by a pleader."),
    ("CrPC 51", "Appearance of accused", "Attendance of the accused is dispensed with when a pleader is engaged."),
    ("BNSS 60", "Appearance through pleader", "The accused may appear through a pleader and attendance is dispensed with."),
    ("BNSS 70", "Audio video electronic means", "Proceedings may be held by audio video electronic means."),
    ("CrPC 80", "Obsolete power", "An obsolete power that the new Sanhita dropped."),
    ("CrPC 91", "Bail bonds", "A person released on bail executes a bond with sureties."),
    ("BNSS 90", "Forfeiture of property", "The proceeds of crime are forfeited to the State."),
] + [(f"BNSS {600 + i}", f"Filler {i}", "Whoever does this shall be punished with imprisonment or fine.") for i in range(40)]


def make_index(path: str) -> None:
    db = index.build(path, [Provision(c, t, None, ()) for c, _, t in SECTIONS], [])
    db.execute("CREATE TABLE heading (citation TEXT PRIMARY KEY, heading TEXT)")
    db.executemany("INSERT INTO heading VALUES (?, ?)", [(c, h) for c, h, _ in SECTIONS])
    db.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")  # what `ibid procedure build` records, which serve checks
    db.executemany("INSERT INTO meta VALUES (?, ?)", [("crpc_parser_version", crpc.CRPC_PARSER_VERSION), ("bnss_parser_version", bnss.BNSS_PARSER_VERSION)])
    db.commit()
    db.close()


def from_table(table: str, idx: str, out: str) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(["concordance", "from-table", "--acts", "crpc-bnss", "--table", table, "--index", idx, "--out", out])
    return code, buf.getvalue()


class CrpcBnssFromTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.idx, cls.out = str(cls.tmp / "p.sqlite"), str(cls.tmp / "crpc-bnss.json")
        make_index(cls.idx)
        (cls.tmp / "t.txt").write_text(TABLE)
        cls.code, cls.printed = from_table(str(cls.tmp / "t.txt"), cls.idx, cls.out)
        cls.entries = json.loads(Path(cls.out).read_text()) if cls.code == 0 else []

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_entries_are_counted_by_type_and_by_verified(self):
        self.assertEqual(self.code, 0, self.printed)
        counts = collections.Counter((e["type"], e["verified"]) for e in self.entries)
        self.assertEqual(counts, {("one-to-one", True): 1, ("one-to-one", False): 1, ("split", True): 1,
                                  ("merged", True): 1, ("new", True): 1, ("removed", False): 1})
        self.assertIn("one-to-one", self.printed)

    def test_the_row_whose_headings_disagree_is_unverified_and_each_type_is_found(self):
        by = {tuple(e["crpc"]) + tuple(e["bnss"]): e for e in self.entries}
        self.assertFalse(by[("CrPC 91", "BNSS 90")]["verified"])
        self.assertEqual(by[("CrPC 80",)]["type"], "removed")
        self.assertEqual(by[("CrPC 30", "BNSS 40", "BNSS 41")]["type"], "split")
        self.assertEqual(by[("CrPC 50", "CrPC 51", "BNSS 60")]["type"], "merged")
        self.assertEqual(by[("BNSS 70",)]["type"], "new")

    def test_only_section_numbers_and_row_references_are_stored(self):
        text = Path(self.out).read_text()
        for table_text in ("Summons to appear", "Newly added", "Merged.", "Invented Author"):
            self.assertNotIn(table_text, text)
        self.assertIn("p.2", text)

    def test_the_pin_is_written_next_to_the_file(self):
        pin = Path(self.out).with_suffix(".sha256").read_text().strip()
        self.assertEqual(pin, hashlib.sha256(Path(self.out).read_bytes()).hexdigest())

    def test_the_tripwire_rate_is_printed_on_a_good_run(self):
        self.assertIn("100.0%", self.printed)

    def test_the_tripwire_fails_on_a_shifted_table_parse_and_prints_every_mismatch(self):
        rows = TABLE.splitlines()
        pat = re.compile(r"^(\d+\s+)(.+?)(\s{2,}(?:\d|-).*)$")
        subjects = [m[2] for ln in rows if (m := pat.match(ln))]
        n = iter(range(1, len(subjects) + 1))
        shifted = "\n".join(pat.sub(lambda m: m[1] + subjects[next(n) % len(subjects)] + m[3], ln) for ln in rows)
        (self.tmp / "shifted.txt").write_text(shifted)
        code, printed = from_table(str(self.tmp / "shifted.txt"), self.idx, str(self.tmp / "shifted.json"))
        self.assertEqual(code, 1)
        self.assertFalse((self.tmp / "shifted.json").exists())
        self.assertIn("tripwire", printed)
        self.assertIn("BNSS 20", printed)


@needs_ipc
class CrpcBnssMcpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        idx, out = str(cls.tmp / "p.sqlite"), str(cls.tmp / "crpc-bnss.json")
        make_index(idx)
        (cls.tmp / "t.txt").write_text(TABLE)
        assert from_table(str(cls.tmp / "t.txt"), idx, out)[0] == 0
        cls.c = Client(command() + ["--procedure-index", idx, "--procedure-concordance", out])

    @classmethod
    def tearDownClass(cls):
        cls.c.close()
        shutil.rmtree(cls.tmp)

    def conc(self, citation: str, **kw) -> dict:
        return self.c.call("concordance", {"citation": citation, **kw})["result"]

    def test_a_crpc_citation_returns_its_bnss_successors_and_type(self):
        self.assertEqual(self.conc("CrPC 30")["structuredContent"],
                         {"result": [{"type": "split", "citations": ["BNSS 40", "BNSS 41"]}]})
        self.assertEqual(self.conc("CrPC 10", direction="crpc_to_bnss")["structuredContent"],
                         {"result": [{"type": "one-to-one", "citations": ["BNSS 20"]}]})

    def test_a_bnss_citation_returns_its_crpc_predecessors(self):
        self.assertEqual(self.conc("BNSS 60")["structuredContent"],
                         {"result": [{"type": "merged", "citations": ["CrPC 50", "CrPC 51"]}]})
        self.assertEqual(self.conc("BNSS 70")["structuredContent"], {"result": [{"type": "new", "citations": []}]})

    def test_an_unverified_entry_is_never_served(self):
        for cite in ("CrPC 91", "BNSS 90", "CrPC 80"):
            got = self.conc(cite)
            self.assertFalse(got["isError"], cite)
            self.assertEqual(got["content"][0]["text"], "no verified concordance", cite)

    def test_a_contradicting_direction_is_a_tool_error_and_ipc_bns_is_unchanged(self):
        self.assertTrue(self.conc("CrPC 30", direction="bnss_to_crpc")["isError"])
        self.assertTrue(self.conc("IPC 378", direction="crpc_to_bnss")["isError"])
        self.assertEqual(self.conc("IPC 378")["structuredContent"]["result"][0]["citations"], ["BNS 303"])


class CrpcBnssRealTableTest(unittest.TestCase):
    CONC = ROOT / "concordance" / "crpc-bnss-v1.json"
    TABLE = Path(CRPC_PDF).parent / "capt" / "comparison_summary_BNSS_to_CrPC.pdf"

    def test_the_committed_file_matches_its_pin(self):
        self.assertEqual(hashlib.sha256(self.CONC.read_bytes()).hexdigest(), self.CONC.with_suffix(".sha256").read_text().strip())

    def test_v2_and_v3_match_their_pins(self):
        for v in ("v2", "v3"):
            p = ROOT / "concordance" / v
            self.assertEqual(hashlib.sha256(p.with_suffix(".json").read_bytes()).hexdigest(), p.with_suffix(".sha256").read_text().strip())

    def test_regenerating_from_the_real_table_reproduces_the_file_and_prints_the_tripwire(self):
        if not (self.TABLE.is_file() and Path(CRPC_PDF).is_file() and Path(BNSS_PDF).is_file()):
            self.skipTest("source PDFs or the table are missing")
        with tempfile.TemporaryDirectory() as tmp:
            idx, txt, out = f"{tmp}/p.sqlite", f"{tmp}/t.txt", f"{tmp}/c.json"
            self.assertEqual(build(CRPC_PDF, idx, BNSS_PDF).returncode, 0)
            Path(txt).write_text(subprocess.run(["pdftotext", "-layout", str(self.TABLE), "-"], check=True, capture_output=True, text=True).stdout)
            code, printed = from_table(txt, idx, out)
            print("\n" + printed)
            self.assertEqual(code, 0, printed)
            self.assertEqual(Path(out).read_bytes(), self.CONC.read_bytes())
            self.assertIn("tripwire", printed)


if __name__ == "__main__":
    unittest.main()
