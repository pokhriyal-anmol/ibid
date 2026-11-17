"""Slice 15 ticket 03: the BNSS in the second index, checked, and kept apart from the BNS.
Seam: `ibid procedure build` and JSON-RPC over stdio, on an invented mini-BNSS in the shape of the Gazette layout text."""
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mcp_harness import ENV, ROOT, Client, command
from pdfs import BNSS_PDF, CRPC_PDF
from test_crpc import BNSS_MINI, MINI, build
from pdfs import needs_ipc

COVERED = ("IPC", "BNS", "CrPC", "BNSS")


@needs_ipc
class MiniBnssTest(unittest.TestCase):
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

    def test_build_prints_the_bnss_counts(self):
        self.assertEqual(self.built.returncode, 0, self.built.stderr)
        self.assertIn("BNSS sections: 4/4", self.built.stdout)
        self.assertIn("BNSS heading match: 100.00%", self.built.stdout)

    def test_section_text_heading_and_children(self):
        sc = self.get("BNSS 3")["structuredContent"]
        self.assertEqual(sc["heading"], "Bail where the offence is not serious.")
        self.assertEqual(sc["children"], ["BNSS 3(1)", "BNSS 3(2)"])
        self.assertEqual(sc["text"], "3. (1) A person accused of a minor offence shall be released on bail: "
                         "Provided that the Court may refuse bail for reasons to be recorded. "
                         "(2) The Court may impose conditions on the bail. Illustration. A is accused of a minor offence. A is released on bail.")

    def test_sub_provision_text_starts_at_its_own_label(self):
        one = self.get("BNSS 3(1)")["structuredContent"]
        self.assertEqual(one["text"], "(1) A person accused of a minor offence shall be released on bail: Provided that the Court may refuse bail for reasons to be recorded.")
        self.assertEqual(one["children"], ["BNSS 3(1) proviso 1"])
        self.assertIsNone(one["heading"])

    def test_clauses_hang_off_their_sub_section_and_the_chapter_heading_stays_out(self):
        self.assertEqual(self.get("BNSS 2(1)")["structuredContent"]["children"], ["BNSS 2(1)(a)", "BNSS 2(1)(b)"])
        for cite in ("BNSS 2", "BNSS 2(2)"):
            text = self.get(cite)["structuredContent"]["text"]
            self.assertNotIn("CHAPTER", text)
            self.assertNotIn("BAIL AND BONDS", text)

    def test_a_bnss_citation_never_resolves_to_the_bns_section_of_the_same_number(self):
        bnss, bns = self.get("BNSS 3"), self.get("BNS 3")
        self.assertFalse(bns["isError"])
        self.assertNotEqual(bnss["structuredContent"]["text"], bns["structuredContent"]["text"])
        self.assertIn("minor offence", bnss["structuredContent"]["text"])
        self.assertNotIn("minor offence", bns["structuredContent"]["text"])

    def test_a_citation_in_neither_index_is_a_tool_error_naming_the_four_acts(self):
        for cite in ("CrPC 9999", "BNSS 9999"):
            got = self.get(cite)
            self.assertTrue(got["isError"], cite)
            for act in COVERED:
                self.assertIn(act, got["content"][0]["text"])

    def test_the_index_records_the_bnss_parser_version(self):
        row = sqlite3.connect(self.index).execute("SELECT value FROM meta WHERE key = 'bnss_parser_version'").fetchone()
        self.assertEqual(row, ("1",))


class CheckFailsOnBadInputTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_bad(self, old: str, new: str):
        src = BNSS_MINI.read_text()
        self.assertIn(old, src)  # the mutation must apply, or this proves nothing
        bad = Path(self.tmp.name) / "bad.txt"
        bad.write_text(src.replace(old, new))
        index = Path(self.tmp.name) / "p.sqlite"
        return build(str(MINI), str(index), str(bad)), index

    def test_a_section_dropped_from_the_parse_fails_on_the_count_and_writes_nothing(self):
        done, index = self.run_bad("law.                  4. Nothing in this Sanhita affects any other law.\n", "")
        self.assertEqual(done.returncode, 1)
        self.assertIn("BNSS sections: 3/4", done.stdout)
        self.assertIn("BNSS 4: arrangement 'Saving of other law.', body None", done.stdout)
        self.assertFalse(index.exists())

    def test_a_changed_heading_is_printed_and_the_rate_falls_below_the_floor(self):
        done, index = self.run_bad("Saving of other\nlaw.   ", "Saving of other\nrights.")
        self.assertEqual(done.returncode, 1)
        self.assertIn("BNSS sections: 4/4", done.stdout)
        self.assertIn("BNSS heading match: 75.00%", done.stdout)
        self.assertIn("BNSS 4: arrangement 'Saving of other law.', body 'Saving of other rights.'", done.stdout)
        self.assertFalse(index.exists())


class NoArrangementTest(unittest.TestCase):
    """The real Gazette prints no Arrangement, so the count comes from BNSS_TOTAL and headings are checked for presence only."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src = BNSS_MINI.read_text()
        self.body = self.src[self.src.index("                         THE MINI BHARATIYA", 10):]  # the Act without its Arrangement

    def run_with(self, text: str, total: str = "4"):
        bnss = Path(self.tmp.name) / "bnss.txt"
        bnss.write_text(text)
        index = Path(self.tmp.name) / "p.sqlite"
        done = subprocess.run([sys.executable, "-m", "ibid.cli", "procedure", "build", "--crpc", str(MINI), "--bnss", str(bnss), "--index", str(index)],
                              cwd=ROOT, env={**ENV, "IBID_BNSS_TOTAL": total}, capture_output=True, text=True)
        return done, index

    def test_the_good_file_passes_on_the_constant_alone(self):
        done, index = self.run_with(self.body)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("BNSS sections: 4/4", done.stdout)
        self.assertIn("BNSS has no Arrangement", done.stdout)
        self.assertTrue(index.exists())

    def test_a_section_dropped_fails_on_the_count_and_writes_nothing(self):
        gone = "Saving of other\nlaw.                  4. Nothing in this Sanhita affects any other law.\n"
        self.assertIn(gone, self.body)
        done, index = self.run_with(self.body.replace(gone, ""))
        self.assertEqual(done.returncode, 1)
        self.assertIn("BNSS sections: 3/4", done.stdout)
        self.assertIn("BNSS 4: no heading, body None", done.stdout)
        self.assertFalse(index.exists())

    def test_a_margin_heading_removed_is_printed_and_the_rate_falls_below_the_floor(self):
        gone = "Short title.          1."
        self.assertIn(gone, self.body)
        done, index = self.run_with(self.body.replace(gone, "                      1."))
        self.assertEqual(done.returncode, 1)
        self.assertIn("BNSS heading match: 75.00%", done.stdout)
        self.assertIn("BNSS 1: no heading, body None", done.stdout)
        self.assertFalse(index.exists())


@needs_ipc
class RealBnssTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.index = str(Path(cls.tmp.name) / "procedure.sqlite")
        cls.built = build(CRPC_PDF, cls.index, BNSS_PDF)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_count_is_531_and_every_section_has_a_heading(self):
        print("\n" + "\n".join(ln for ln in self.built.stdout.splitlines() if ln.startswith("BNSS")))  # the rate and every mismatch
        self.assertEqual(self.built.returncode, 0, self.built.stderr)
        self.assertIn("BNSS sections: 531/531", self.built.stdout)
        self.assertGreaterEqual(float(re.search(r"BNSS heading match: ([\d.]+)%", self.built.stdout)[1]), 98.0)

    def test_a_part_heading_and_a_wrapped_margin_note_stay_out_of_the_text(self):
        c = Client(command() + ["--procedure-index", self.index, "--procedure-concordance", "absent.json"])
        self.addCleanup(c.close)
        get = lambda cite: c.call("get_provision", {"citation": cite})["result"]["structuredContent"]
        for cite in ("BNSS 71", "BNSS 83", "BNSS 456", "BNSS 471"):
            self.assertNotRegex(get(cite)["text"][-60:], r"[A-Z]\.—", cite)
        self.assertEqual(get("BNSS 246")["heading"], "What persons may be charged jointly.")
        self.assertNotIn("What persons", get("BNSS 246")["text"])

    def test_section_482_and_its_first_sub_section_are_served_through_mcp(self):
        c = Client(command() + ["--procedure-index", self.index, "--procedure-concordance", "absent.json"])
        self.addCleanup(c.close)
        sc = c.call("get_provision", {"citation": "BNSS 482"})["result"]["structuredContent"]
        self.assertEqual(sc["heading"], "Direction for grant of bail to person apprehending arrest.")
        self.assertTrue(sc["text"].startswith("482. (1) When any person has reason to believe"))
        self.assertEqual(sc["children"][:2], ["BNSS 482(1)", "BNSS 482(2)"])
        sub = c.call("get_provision", {"citation": "BNSS 482(1)"})["result"]["structuredContent"]
        self.assertTrue(sub["text"].startswith("(1) When any person has reason to believe"))
        self.assertTrue(sub["text"].endswith("released on bail."))
        bns = c.call("get_provision", {"citation": "BNS 103"})["result"]["structuredContent"]["text"]
        self.assertNotEqual(c.call("get_provision", {"citation": "BNSS 103"})["result"]["structuredContent"]["text"], bns)


if __name__ == "__main__":
    unittest.main()
