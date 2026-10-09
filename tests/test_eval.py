"""Tests go through the one seam: `ibid eval`. Needs IBID_BNS_PDF (the gitignored gazette PDF)."""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from ibid.cli import main

GOLD = str(Path(__file__).parent.parent / "gold" / "draft.json")
PDF = os.environ["IBID_BNS_PDF"]


class EvalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_eval(self, name="r", gold=GOLD, pdf=PDF):
        out, idx = self.tmp / f"{name}.json", self.tmp / f"{name}.sqlite"
        code = main(["eval", "--gold", gold, "--bns", pdf, "--index", str(idx), "--out", str(out)])
        return code, out, idx

    def test_all_section_lookups_pass_and_results_carry_provenance(self):
        code, out, _ = self.run_eval()
        self.assertEqual(code, 0)
        r = json.loads(out.read_text())
        self.assertEqual(r["categories"]["section_lookup"], {"passed": 4, "total": 4})
        self.assertEqual(r["sections"]["BNS"], {"recovered": 358, "expected": 358})
        self.assertRegex(r["gold_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(r["parser_version"])
        self.assertEqual(r["categories"]["subprovision_lookup"], {"passed": 6, "total": 6})
        self.assertEqual(len(r["outcomes"]), 13)
        self.assertEqual(r["categories"]["keyword"], {"passed": 3, "total": 3})

    def test_wrong_expected_text_fails_and_lowers_the_score(self):
        gold = json.loads(Path(GOLD).read_text())
        gold[0]["expected_text"] = gold[0]["expected_text"].replace("death", "life", 1)
        bad = self.tmp / "bad-gold.json"
        bad.write_text(json.dumps(gold))
        _, out, _ = self.run_eval(gold=str(bad))
        r = json.loads(out.read_text())
        self.assertEqual(r["categories"]["section_lookup"], {"passed": 3, "total": 4})
        self.assertFalse(r["outcomes"][0]["pass"])

    def run_bad_gold(self, edit):
        gold = json.loads(Path(GOLD).read_text())
        edit({g["id"]: g for g in gold})
        bad = self.tmp / "bad-gold.json"
        bad.write_text(json.dumps(gold))
        _, out, _ = self.run_eval(gold=str(bad))
        return {o["id"]: o["pass"] for o in json.loads(out.read_text())["outcomes"]}

    def test_subsection_lookup_returns_only_that_subsection(self):
        # known-bad: expecting the whole section's text for a subsection citation must fail
        def edit(g):
            g["sub-103-1"]["expected_text"] = g["lookup-103"]["expected_text"]
        passed = self.run_bad_gold(edit)
        self.assertFalse(passed["sub-103-1"])
        self.assertTrue(passed["lookup-103"])

    def test_section_lookup_must_return_its_child_addresses(self):
        def edit(g):
            g["lookup-103"]["expected_children"] = ["BNS 103(1)"]
        self.assertFalse(self.run_bad_gold(edit)["lookup-103"])

    def test_keyword_ties_break_by_citation(self):
        # BNS 351(4) and BNS 94 tie on score; parse order puts 94 first, citation order puts 351(4) first
        def edit(g):
            c = g["keyword-conceal"]["expected_citations"]
            c[1], c[2] = c[2], c[1]
        self.assertFalse(self.run_bad_gold(edit)["keyword-conceal"])

    def test_keyword_query_is_not_expanded_or_stemmed(self):
        def edit(g):
            g["keyword-conceal"]["query"] = "concealed"
        self.assertFalse(self.run_bad_gold(edit)["keyword-conceal"])

    def test_keyword_results_carry_verbatim_text_and_are_byte_identical_across_rebuilds(self):
        _, a, _ = self.run_eval("a")
        _, b, _ = self.run_eval("b")
        self.assertEqual(a.read_bytes(), b.read_bytes())
        packet = next(o for o in json.loads(a.read_text())["outcomes"] if o["id"] == "keyword-dowry")["packet"]
        self.assertTrue(packet[1][1].startswith("80. "))

    def test_truncated_source_drops_the_count_and_exits_nonzero(self):
        pages = self.tmp / "pages"
        pages.mkdir()
        subprocess.run(["pdfseparate", "-f", "1", "-l", "60", PDF, str(pages / "%d.pdf")], check=True)
        short = self.tmp / "short.pdf"
        files = [str(pages / f"{i}.pdf") for i in range(1, 61)]
        subprocess.run(["pdfunite", *files, str(short)], check=True)
        code, out, _ = self.run_eval(pdf=str(short))
        self.assertNotEqual(code, 0)
        self.assertFalse(out.exists())

    def test_two_runs_are_byte_identical(self):
        _, a, _ = self.run_eval("a")
        _, b, _ = self.run_eval("b")
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_indexed_text_is_english_only_and_citations_are_unique(self):
        _, _, idx = self.run_eval()
        rows = sqlite3.connect(idx).execute("SELECT citation, text FROM provision").fetchall()
        self.assertEqual(len({c for c, _ in rows}), len(rows))
        self.assertEqual(len([c for c, _ in rows if re.fullmatch(r"BNS [1-9][0-9]*", c)]), 358)
        for citation, text in rows:
            self.assertRegex(citation, r"^BNS [1-9][0-9]*(\([0-9A-Z]+\))?(\([a-z]+\))*( (proviso|explanation|exception|illustration) [1-9][0-9]*)*(\([a-z]+\))*$")
            self.assertIsNone(re.search("[^\x20-\x7e—–‘’“”]", text), citation)
            # page headers, chapter titles and group headings are not part of any section
            self.assertIsNone(re.search(r"GAZETTE|EXTRAORDINARY|Sec\. \d|CHAPTER|(?:^|\. )Of [a-z]", text), citation)

    def test_every_child_address_exists_and_names_its_parent(self):
        _, _, idx = self.run_eval()
        db = sqlite3.connect(idx)
        parent = dict(db.execute("SELECT citation, parent FROM provision"))
        for citation, children in db.execute("SELECT citation, children FROM provision"):
            for child in json.loads(children):
                self.assertEqual(parent[child], citation)

    def test_source_texts_are_not_tracked_by_git(self):
        for path in ("data/raw/bns-prs.pdf", "data/raw/ipc-wipo.pdf"):
            ignored = subprocess.run(["git", "check-ignore", "-q", path])
            self.assertEqual(ignored.returncode, 0, path)


if __name__ == "__main__":
    unittest.main()
