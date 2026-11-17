"""Slice 15 ticket 02: the CrPC in a second index, checked against its Arrangement, served by `ibid mcp`.
Seam: `ibid procedure build` and JSON-RPC over stdio, on an invented mini-CrPC in the shape of the real layout text."""
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mcp_harness import ENV, ROOT, Client, command
from pdfs import BNSS_PDF, CRPC_PDF
from pdfs import needs_ipc

MINI = ROOT / "tests" / "fixtures" / "crpc-mini.txt"
BNSS_MINI = ROOT / "tests" / "fixtures" / "bnss-mini.txt"
HEAD_41A = "Notice of appearance before police officer."


def build(src: str, index_path: str, bnss: str = str(BNSS_MINI)) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "ibid.cli", "procedure", "build", "--crpc", src, "--bnss", bnss, "--index", index_path],
                          cwd=ROOT, env=ENV, capture_output=True, text=True)


def snapshot() -> dict[str, str]:
    """SHA-256 of the first index, every pinned file and all of results/ (decision 10)."""
    paths = [ROOT / "data/index/ibid.sqlite", *(ROOT / "gold").glob("v2.*"), *(ROOT / "concordance").glob("v[23].*"),
             *(p for p in (ROOT / "results").rglob("*") if p.is_file())]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


@needs_ipc
class MiniCrpcTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.index = str(Path(cls.tmp.name) / "procedure.sqlite")
        cls.built = build(str(MINI), cls.index)
        cls.c = Client(command() + ["--procedure-index", cls.index, "--procedure-concordance", "absent.json"])

    @classmethod
    def tearDownClass(cls):
        cls.c.close()
        cls.tmp.cleanup()

    def get(self, citation: str) -> dict:
        return self.c.call("get_provision", {"citation": citation})["result"]

    def test_build_passes_and_prints_the_counts(self):
        self.assertEqual(self.built.returncode, 0, self.built.stderr)
        self.assertIn("CrPC sections: 7/7", self.built.stdout)
        self.assertIn("CrPC heading match: 100.00%", self.built.stdout)

    def test_the_index_records_its_own_parser_version(self):
        self.assertEqual(sqlite3.connect(self.index).execute("SELECT value FROM meta WHERE key = 'crpc_parser_version'").fetchone(), ("1",))

    def test_lettered_section_returns_text_arrangement_heading_and_children(self):
        got = self.get("CrPC 41A")
        self.assertFalse(got["isError"])
        sc = got["structuredContent"]
        self.assertEqual(sc["heading"], HEAD_41A)
        self.assertEqual(sc["children"], ["CrPC 41A(1)", "CrPC 41A(2)"])
        self.assertEqual(sc["text"], f"41A. {HEAD_41A}—(1) The police officer shall issue a notice directing the person to appear before him. "
                         "(2) Where such person complies with the notice, he shall not be arrested. "
                         "Provided that the officer may arrest him for reasons to be recorded. Illustration. "
                         "A is summoned by notice under sub-section (1). A appears. A is not arrested.")

    def test_sub_provision_text_starts_at_its_own_label_and_proviso_and_illustration_hang_off_it(self):
        one = self.get("CrPC 41A(1)")["structuredContent"]
        self.assertEqual(one["text"], "(1) The police officer shall issue a notice directing the person to appear before him.")
        self.assertIsNone(one["heading"])
        two = self.get("CrPC 41A(2)")["structuredContent"]
        self.assertEqual(two["children"], ["CrPC 41A(2) proviso 1", "CrPC 41A(2) illustration 1"])
        self.assertTrue(two["text"].startswith("(2) Where such person"))

    def test_clauses_amendment_marks_footnotes_and_chapter_headings_stay_out_of_the_text(self):
        self.assertEqual(self.get("CrPC 2")["structuredContent"]["children"], ["CrPC 2(a)", "CrPC 2(b)"])
        self.assertEqual(self.get("CrPC 1(2)")["structuredContent"]["text"],
                         "(2) It extends to the whole of India: Provided that nothing in this Code applies to the tribal areas.")
        for cite in ("CrPC 1", "CrPC 1(2)", "CrPC 3", "CrPC 41A"):
            text = self.get(cite)["structuredContent"]["text"]
            for junk in ("****", "[", "except the State of Jammu", "CHAPTER", "ARREST OF PERSONS", "Ins. by Act"):
                self.assertNotIn(junk, text, f"{cite}: {junk}")

    def test_repealed_section_is_counted_and_served(self):
        sc = self.get("CrPC 42")["structuredContent"]
        self.assertEqual((sc["heading"], sc["text"]), ("[Repealed.]", "42. Repealed."))

    def test_the_wrapped_arrangement_heading_is_joined(self):
        self.assertEqual(self.get("CrPC 3")["structuredContent"]["heading"], "Bail where the offence is not serious.")

    def test_a_citation_of_another_act_is_still_served_from_the_first_index(self):
        self.assertFalse(self.c.call("get_provision", {"citation": "IPC 420"})["result"]["isError"])

    def test_without_a_procedure_index_a_crpc_citation_is_not_in_the_index(self):
        c = Client(command() + ["--procedure-index", str(Path(self.tmp.name) / "absent.sqlite")])
        self.addCleanup(c.close)
        self.assertFalse(c.call("get_provision", {"citation": "IPC 420"})["result"]["isError"])
        got = c.call("get_provision", {"citation": "CrPC 41A"})["result"]
        self.assertTrue(got["isError"])
        self.assertIn("not in the index", got["content"][0]["text"])


class CheckFailsOnBadInputTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_bad(self, old: str, new: str) -> tuple[subprocess.CompletedProcess, Path]:
        src = MINI.read_text()
        self.assertIn(old, src)  # the mutation must apply, or this proves nothing
        bad = Path(self.tmp.name) / "bad.txt"
        bad.write_text(src.replace(old, new))
        index = Path(self.tmp.name) / "p.sqlite"
        return build(str(bad), str(index)), index

    def test_a_section_dropped_from_the_parse_fails_on_the_count_and_writes_nothing(self):
        done, index = self.run_bad("    43. Saving.—Nothing in this Code affects any other law.\n", "")
        self.assertEqual(done.returncode, 1)
        self.assertIn("CrPC sections: 6/7", done.stdout)
        self.assertIn("CrPC 43: arrangement 'Saving.', body None", done.stdout)
        self.assertFalse(index.exists())

    def test_a_changed_heading_is_printed_and_the_rate_falls_below_the_floor(self):
        done, index = self.run_bad("43. Saving.—Nothing", "43. Savings of rights.—Nothing")
        self.assertEqual(done.returncode, 1)
        self.assertIn("CrPC sections: 7/7", done.stdout)
        self.assertIn("CrPC heading match: 85.71%", done.stdout)
        self.assertIn("CrPC 43: arrangement 'Saving.', body 'Savings of rights.'", done.stdout)
        self.assertFalse(index.exists())


@needs_ipc
class FirstIndexUntouchedTest(unittest.TestCase):
    def test_the_build_leaves_the_first_index_the_pins_and_results_byte_identical(self):
        first = ROOT / "data/index/ibid.sqlite"
        if not first.is_file():  # a fresh worktree has none; `ibid eval` writes it, and its results go elsewhere
            from pdfs import BNS_PDF, IPC_PDF
            with tempfile.TemporaryDirectory() as out:
                subprocess.run([sys.executable, "-m", "ibid.cli", "eval", "--gold", "gold/v2.json", "--concordance", "concordance/v2.json",
                                "--bns", BNS_PDF, "--ipc", IPC_PDF, "--out", str(Path(out) / "r.json")], cwd=ROOT, env=ENV, check=True, capture_output=True)
        before = snapshot()
        self.assertIn(str(first), before)
        self.assertIn(str(ROOT / "results/baseline-v2.json"), before)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(build(str(MINI), str(Path(tmp) / "p.sqlite")).returncode, 0)
        self.assertEqual(snapshot(), before)

    def test_the_snapshot_notices_a_changed_file(self):
        before = snapshot()
        victim = ROOT / "concordance/v3.json"
        original = victim.read_bytes()
        self.addCleanup(victim.write_bytes, original)
        victim.write_bytes(original + b" ")
        self.assertNotEqual(snapshot(), before)


@needs_ipc
class RealCrpcTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.index = str(Path(cls.tmp.name) / "procedure.sqlite")
        cls.built = build(CRPC_PDF, cls.index, BNSS_PDF)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_count_matches_the_arrangement_and_headings_match_at_least_98_percent(self):
        print("\n" + self.built.stdout)  # the rate and every mismatch
        self.assertEqual(self.built.returncode, 0, self.built.stderr)
        got, want = map(int, re.search(r"CrPC sections: (\d+)/(\d+)", self.built.stdout).groups())
        self.assertEqual(got, want)
        self.assertGreaterEqual(float(re.search(r"heading match: ([\d.]+)%", self.built.stdout)[1]), 98.0)

    def test_section_438_and_a_lettered_section_are_served_through_mcp(self):
        c = Client(command() + ["--procedure-index", self.index, "--procedure-concordance", "absent.json"])
        self.addCleanup(c.close)
        sc = c.call("get_provision", {"citation": "CrPC 438"})["result"]["structuredContent"]
        self.assertEqual(sc["heading"], "Direction for grant of bail to person apprehending arrest.")
        self.assertTrue(sc["text"].startswith("438. Direction for grant of bail to person apprehending arrest.—"))
        self.assertIn("CrPC 438(1)", sc["children"])
        sub = c.call("get_provision", {"citation": "CrPC 438(1)"})["result"]["structuredContent"]
        self.assertTrue(sub["text"].startswith("(1) When any person has reason to believe"))
        self.assertFalse(c.call("get_provision", {"citation": "CrPC 41A"})["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
