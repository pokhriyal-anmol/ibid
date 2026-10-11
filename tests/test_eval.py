"""Tests go through the one seam: `ibid eval`. Needs IBID_BNS_PDF and IBID_IPC_PDF (the gitignored source PDFs)."""
import hashlib
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
IPC_PDF = os.environ["IBID_IPC_PDF"]
FIX = Path(__file__).parent / "fixtures"
CGOLD, CONC = str(FIX / "concordance-gold.json"), str(FIX / "concordance.json")


class EvalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_eval(self, name="r", gold=GOLD, pdf=PDF, ipc=IPC_PDF, conc=None, mode="draft"):
        out, idx = self.tmp / f"{name}.json", self.tmp / f"{name}.sqlite"
        extra = ["--concordance", conc] if conc else []
        code = main(["eval", "--gold", gold, "--bns", pdf, "--ipc", ipc, "--index", str(idx), "--out", str(out), "--mode", mode, *extra])
        return code, out, idx

    def test_all_section_lookups_pass_and_results_carry_provenance(self):
        code, out, _ = self.run_eval()
        self.assertEqual(code, 0)
        r = json.loads(out.read_text())
        self.assertEqual(r["categories"]["section_lookup"], {"passed": 6, "total": 6})
        self.assertEqual(r["sections"]["BNS"], {"recovered": 358, "expected": 358})
        self.assertEqual(r["sections"]["IPC"], {"recovered": 575, "expected": 575})
        self.assertRegex(r["gold_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(r["parser_version"])
        self.assertEqual(r["categories"]["subprovision_lookup"], {"passed": 8, "total": 8})
        self.assertEqual(len(r["outcomes"]), 21)
        self.assertEqual(r["categories"]["keyword"], {"passed": 3, "total": 3})

    def test_wrong_expected_text_fails_and_lowers_the_score(self):
        gold = json.loads(Path(GOLD).read_text())
        gold[0]["expected_text"] = gold[0]["expected_text"].replace("death", "life", 1)
        bad = self.tmp / "bad-gold.json"
        bad.write_text(json.dumps(gold))
        _, out, _ = self.run_eval(gold=str(bad))
        r = json.loads(out.read_text())
        self.assertEqual(r["categories"]["section_lookup"], {"passed": 5, "total": 6})
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

    def test_ipc_citations_return_verbatim_text_and_do_not_collide_with_bns(self):
        # known-bad: the IPC 103 text expected under the BNS 103 citation (and the reverse) must fail
        def edit(g):
            g["ipc-lookup-103"]["expected_text"] = g["lookup-103"]["expected_text"]
            g["lookup-102"]["query"] = "IPC 102"
        passed = self.run_bad_gold(edit)
        self.assertFalse(passed["ipc-lookup-103"])
        self.assertFalse(passed["lookup-102"])
        self.assertTrue(passed["lookup-103"] and passed["ipc-lookup-302"])
        self.assertTrue(passed["sub-ipc-304B-2"] and passed["exception-ipc-300-1"])

    def test_missing_ipc_section_drops_the_count_and_exits_nonzero(self):
        pages = self.tmp / "ipc-pages"
        pages.mkdir()
        subprocess.run(["pdfseparate", IPC_PDF, str(pages / "%d.pdf")], check=True)
        files = [str(pages / f"{i}.pdf") for i in range(1, 120) if i != 75]  # page 75 holds 304A to 308
        short = self.tmp / "short-ipc.pdf"
        subprocess.run(["pdfunite", *files, str(short)], check=True)
        code, out, _ = self.run_eval(ipc=str(short))
        self.assertNotEqual(code, 0)
        self.assertFalse(out.exists())

    def test_keyword_ties_break_by_citation(self):
        # BNS 351(4) and BNS 94 tie on score; parse order puts 94 first, citation order puts 351(4) first.
        # Keyword items are scored as sets, so the order is asserted on the returned packet.
        _, out, _ = self.run_eval()
        packet = next(o for o in json.loads(out.read_text())["outcomes"] if o["id"] == "keyword-conceal")["packet"]
        cites = [c for c, _ in packet]
        self.assertLess(cites.index("BNS 351(4)"), cites.index("BNS 94"))

    def test_keyword_query_is_not_expanded_or_stemmed(self):
        def edit(g):
            g["keyword-conceal"]["query"] = "concealed"
        self.assertFalse(self.run_bad_gold(edit)["keyword-conceal"])

    def test_keyword_results_carry_verbatim_text_and_are_byte_identical_across_rebuilds(self):
        _, a, _ = self.run_eval("a")
        _, b, _ = self.run_eval("b")
        self.assertEqual(a.read_bytes(), b.read_bytes())
        packet = next(o for o in json.loads(a.read_text())["outcomes"] if o["id"] == "keyword-dowry")["packet"]
        self.assertTrue(packet[3][1].startswith("80. "))

    def test_chain_returns_provision_and_resolved_targets_in_fixed_order(self):
        _, out, _ = self.run_eval()
        r = json.loads(out.read_text())
        self.assertEqual(r["categories"]["cross_reference_chain"], {"passed": 4, "total": 4})
        packet = next(o for o in r["outcomes"] if o["id"] == "xref-bns-353-3")["packet"]
        self.assertEqual([c for c, _ in packet], ["BNS 353(2)", "BNS 353"])  # sub-section (2), then "this section"
        self.assertTrue(packet[0][1].startswith("(2) Whoever makes, publishes"))

    def test_chain_with_a_wrong_target_order_or_missing_target_is_a_miss(self):
        # known-bad: a deliberately wrong target, a swapped order, and a dropped target must each fail
        def edit(g):
            g["xref-bns-117-3"]["expected_refs"] = ["BNS 117(2)"]
            g["xref-bns-353-3"]["expected_refs"].reverse()
            g["xref-bns-66"]["expected_refs"].pop()
        passed = self.run_bad_gold(edit)
        self.assertFalse(passed["xref-bns-117-3"] or passed["xref-bns-353-3"] or passed["xref-bns-66"])
        self.assertTrue(passed["xref-bns-117-2"])

    def test_unresolved_references_are_listed_with_reason_and_counted_per_act(self):
        _, out, _ = self.run_eval()
        r = json.loads(out.read_text())
        self.assertEqual(r["xref"], {"BNS": {"resolved": 315, "unresolved": 16}, "IPC": {"resolved": 271, "unresolved": 13}})
        self.assertEqual(len(r["unresolved_xref"]), 29)
        self.assertIn({"source": "BNS 5", "matched": "section 474", "reason": "other Act: of the Bharatiya Nagarik Suraksha Sanhita"}, r["unresolved_xref"])
        self.assertIn({"source": "BNS 209", "matched": "sub-section (4)", "reason": "names an earlier section: of that section"}, r["unresolved_xref"])

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
        # Explicit exception to the eval-seam rule: parser invariants read the index schema directly.
        _, _, idx = self.run_eval()
        rows = sqlite3.connect(idx).execute("SELECT citation, text FROM provision").fetchall()
        self.assertEqual(len({c for c, _ in rows}), len(rows))
        self.assertEqual(len([c for c, _ in rows if re.fullmatch(r"BNS [1-9][0-9]*", c)]), 358)
        self.assertEqual(len([c for c, _ in rows if re.fullmatch(r"IPC [1-9][0-9]*[A-Z]{0,2}", c)]), 575)
        for citation, text in rows:
            self.assertRegex(citation, r"^(BNS [1-9][0-9]*|IPC [1-9][0-9]*[A-Z]{0,2})(\([0-9A-Z]+\))?(\([a-z]+\))*( (proviso|explanation|exception|illustration) [1-9][0-9]*)*(\([a-z]+\))*$")
            self.assertIsNone(re.search("[^\x20-\x7e—–‘’“”]", text), citation)
            # page headers, chapter titles and group headings are not part of any section
            self.assertIsNone(re.search(r"GAZETTE|EXTRAORDINARY|Sec\. \d|CHAPTER|(?:^|\. )Of [a-z]", text), citation)
            # amendment marks (brackets, *** for omitted words) are not part of the provision text
            self.assertNotRegex(text, r"[\[\]]|\*\*\*", citation)

    def test_every_child_address_exists_and_names_its_parent(self):
        # Explicit exception to the eval-seam rule: reads the index schema directly.
        _, _, idx = self.run_eval()
        db = sqlite3.connect(idx)
        parent = dict(db.execute("SELECT citation, parent FROM provision"))
        for citation, children in db.execute("SELECT citation, children FROM provision"):
            for child in json.loads(children):
                self.assertEqual(parent[child], citation)

    def run_conc(self, entries=None, edit=None, name="c"):
        gold = json.loads(Path(CGOLD).read_text())
        if edit:
            edit({g["id"]: g for g in gold})
        (self.tmp / name).mkdir(exist_ok=True)
        g = self.tmp / name / "gold.json"  # same stem every run: gold_version is in the results
        g.write_text(json.dumps(gold))
        conc = CONC
        if entries is not None:
            conc = str(self.tmp / f"{name}-conc.json")
            Path(conc).write_text(json.dumps(entries))
        code, out, _ = self.run_eval(name, gold=str(g), conc=conc)
        return code, out

    def test_concordance_serves_both_directions_with_every_mapping_type(self):
        code, out = self.run_conc()
        self.assertEqual(code, 0)
        r = json.loads(out.read_text())
        self.assertTrue(all(o["pass"] for o in r["outcomes"]), r["outcomes"])
        self.assertEqual(r["categories"]["ipc_to_bns"], {"passed": 6, "total": 6})
        self.assertEqual(r["categories"]["bns_to_ipc"], {"passed": 5, "total": 5})
        got = {o["id"]: o["packet"] for o in r["outcomes"]}
        self.assertEqual(got["c-removed"][0]["type"], "removed")
        self.assertEqual(got["c-unverified"], "no verified concordance")

    def test_concordance_expectations_that_are_wrong_fail(self):
        # known-bad: a wrong target, a wrong type, and a served unverified entry must each miss
        def edit(g):
            g["c-one"]["expected"][0]["citations"] = ["BNS 104"]
            g["c-split"]["expected"][0]["type"] = "one-to-one"
            g["c-unverified"]["expected"] = [{"type": "one-to-one", "citations": ["BNS 80"]}]
        _, out = self.run_conc(edit=edit)
        passed = {o["id"]: o["pass"] for o in json.loads(out.read_text())["outcomes"]}
        self.assertFalse(passed["c-one"] or passed["c-split"] or passed["c-unverified"])
        self.assertTrue(passed["c-rev"] and passed["c-none"])

    def test_verified_flag_decides_what_is_served(self):
        # known-bad: flipping the unverified fixture entry to verified must make it served
        entries = json.loads(Path(CONC).read_text())
        entries[-1]["verified"] = True
        _, out = self.run_conc(entries=entries)
        passed = {o["id"]: o["pass"] for o in json.loads(out.read_text())["outcomes"]}
        self.assertFalse(passed["c-unverified"])

    def test_entry_naming_a_citation_absent_from_the_index_fails_the_run(self):
        entries = json.loads(Path(CONC).read_text())
        entries.append({"ipc": ["IPC 9999"], "bns": ["BNS 1"], "type": "one-to-one", "verified": False})
        code, out = self.run_conc(entries=entries)
        self.assertNotEqual(code, 0)
        self.assertFalse(out.exists())

    def test_entries_must_fit_their_type_and_cite_the_right_act_on_each_side(self):
        base = json.loads(Path(CONC).read_text())[0]
        ipc, bns = base["ipc"], base["bns"]
        bad = [{**base, "type": "removed"}, {**base, "type": "new"}, {**base, "ipc": bns, "bns": ipc}]
        for entry in bad:
            code, out = self.run_conc(entries=[entry])
            self.assertNotEqual(code, 0, entry)
            self.assertFalse(out.exists())

    def test_results_name_the_concordance_that_produced_the_score(self):
        _, out = self.run_conc()
        got = json.loads(out.read_text())["concordance"]
        self.assertEqual(got["sha256"], hashlib.sha256(Path(CONC).read_bytes()).hexdigest())

    def test_concordance_results_are_byte_identical_across_runs(self):
        _, a = self.run_conc(name="a")
        _, b = self.run_conc(name="b")
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def pinned_gold(self, name, mutate=None):
        """Copy the draft gold set to <name>.json beside its pin; optionally change the file after pinning."""
        path = self.tmp / f"{name}.json"
        path.write_bytes(Path(GOLD).read_bytes())
        path.with_suffix(".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest() + "\n")
        if mutate:
            path.write_bytes(mutate(path.read_bytes()))
        return str(path)

    def test_scored_mode_runs_pinned_gold_and_records_mode_version_and_hash(self):
        gold = self.pinned_gold("v1")
        code, a, _ = self.run_eval("a", gold=gold, mode="scored")
        _, b, _ = self.run_eval("b", gold=gold, mode="scored")
        self.assertEqual(code, 0)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        r = json.loads(a.read_text())
        self.assertEqual((r["mode"], r["gold_version"]), ("scored", "v1"))
        self.assertEqual(r["gold_sha256"], hashlib.sha256(Path(gold).read_bytes()).hexdigest())

    def test_scored_mode_refuses_one_changed_byte_and_an_unpinned_file(self):
        # known-bad: one appended byte after pinning must refuse; an unpinned file must refuse
        code, out, _ = self.run_eval(gold=self.pinned_gold("v1", lambda b: b + b" "), mode="scored")
        self.assertNotEqual(code, 0)
        self.assertFalse(out.exists())
        code, out, _ = self.run_eval("u", gold=GOLD, mode="scored")
        self.assertNotEqual(code, 0)
        self.assertFalse(out.exists())

    def test_draft_mode_runs_without_a_pin_and_says_so(self):
        code, a, _ = self.run_eval("a")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(a.read_text())["mode"], "draft")

    def test_a_new_version_sits_beside_the_old_one_without_touching_it(self):
        v1 = self.pinned_gold("v1")
        v2 = self.pinned_gold("v2")
        Path(v2).write_text(json.dumps(json.loads(Path(v2).read_text())[:3]))
        Path(v2).with_suffix(".sha256").write_text(hashlib.sha256(Path(v2).read_bytes()).hexdigest())
        self.assertEqual(Path(v1).read_bytes(), Path(GOLD).read_bytes())
        for name, path in (("v1", v1), ("v2", v2)):
            code, out, _ = self.run_eval(name, gold=path, mode="scored")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.read_text())["gold_version"], name)

    def test_source_texts_are_not_tracked_by_git(self):
        for path in ("data/raw/bns-prs.pdf", "data/raw/ipc-wipo.pdf"):
            ignored = subprocess.run(["git", "check-ignore", "-q", path])
            self.assertEqual(ignored.returncode, 0, path)


if __name__ == "__main__":
    unittest.main()
