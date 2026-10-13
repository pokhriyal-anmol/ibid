"""Slice 3 ticket 13: `ibid concordance from-table`. An invented table of the same shape as the real one."""
import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ibid import concordance, index
from ibid.cli import main
from ibid.parse import Provision

TABLE = """\
CORRESPONDENCE TABLE of an INVENTED SANHITA to an INVENTED CODE
 BNS         Subject                               IPC      Summary of comparison
 Sections/                                         Sections
 Subsecti
 ons
 1(1)        Short title and extent.               1       Included as a subsection.
 1(2)        Commencement.                         New     Power to appoint the date.
 1(3)        Punishment of offences within         2       No change.
             the territory.
 2(8)        "Document".                           29 and  Words are added.
                                                   29A
 303         Theft.                                378     No change.
                                                     © Invented Author, Director
\f 101        Murder.                               300     Split by punishment.
 102         Murder punishment.                    300     Split by punishment.
 7           Weights and measures.                 120     Table says so.
 9           Organised crime.                      New     Added.
 500         Ghost provision.                      999     Cited but absent.
"""

TEXT = {
    "IPC 1": "Title and extent of operation of the Code.",
    "IPC 2": "Punishment of offences committed within the territory of India.",
    "BNS 1": "Short title commencement. Offences within the territory of India under this Sanhita.",
    "IPC 29": "The word document denotes any matter expressed upon a substance.",
    "IPC 29A": "The words electronic record have the meaning given.",
    "BNS 2": "Definitions. Document includes any electronic record.",
    "IPC 378": "Whoever intends dishonestly to take movable property commits theft.",
    "BNS 303": "Whoever intends dishonestly to take movable property commits theft.",
    "IPC 300": "Culpable homicide is murder when the act is done with the intention of causing death.",
    "BNS 101": "Culpable homicide is murder when the act is done with intention of causing death.",
    "BNS 102": "Whoever commits murder shall be punished with death or imprisonment for life.",
    "IPC 120": "Concealing design to commit an offence punishable with imprisonment.",
    "BNS 7": "Falsified weights and measures sold in the market.",
    "BNS 9": "Organised crime by a syndicate.",
}
FILLER = [Provision(f"IPC {i}", "Whoever does this shall be punished with imprisonment or fine.", None, ()) for i in range(600, 640)]
PROVS = [Provision(c, t, None, ()) for c, t in TEXT.items()] + FILLER


class FromTableTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        index.build(str(self.tmp / "i.sqlite"), PROVS, []).close()
        self.run_table(TABLE)

    def run_table(self, text: str) -> None:
        (self.tmp / "t.txt").write_text(text)
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["concordance", "from-table", "--table", str(self.tmp / "t.txt"),
                         "--index", str(self.tmp / "i.sqlite"), "--out", str(self.tmp / "c.json")])
        self.assertEqual(code, 0)
        self.out = json.loads((self.tmp / "c.json").read_text())

    def served(self) -> dict[tuple, str]:
        return {(tuple(e["ipc"]), tuple(e["bns"])): e["type"] for e in self.out["entries"]}

    def test_parser_reproduces_the_fixture_rows(self):
        rows = {r["bns"]: r for r in self.out["rows"]}
        self.assertEqual(list(rows), ["1(1)", "1(2)", "1(3)", "2(8)", "303", "101", "102", "7", "9", "500"])
        self.assertEqual(rows["1(2)"]["ipc"], "New")
        self.assertEqual(rows["1(3)"]["subject"], "Punishment of offences within the territory.")
        self.assertEqual(rows["2(8)"]["ipc"], "29 and 29A")
        self.assertEqual((rows["303"]["page"], rows["101"]["page"]), (1, 2))

    def test_real_table_shapes_a_spaced_subclause_and_a_cell_one_space_from_its_note(self):
        # seen in the CAPT table: "318 (4)" with a space, and "376(1) & Word ..." / "not 304 amounting" with one space
        self.run_table(TABLE + (
            " 318 (4)     Cheating and delivery.                 29      Included as a sub-section.\n"
            " 64          Punishment for rape.                   300 & Word replaced with army.\n"
            " 105         Culpable homicide not 120 amounting.   1       Minimum added.\n"))
        rows = {r["bns"]: r for r in self.out["rows"]}
        self.assertEqual(rows["318 (4)"]["ipc"], "29")
        self.assertEqual((rows["64"]["ipc"], rows["64"]["note"]), ("300 &", "Word replaced with army."))
        self.assertEqual((rows["105"]["ipc"], rows["105"]["subject"]), ("1", "Culpable homicide not 120 amounting."))
        # a wrapped word in the IPC column that is not a section number goes to the note (BNS 86 "Explanat ion")
        self.run_table(TABLE + (" 85          Cruelty.                               378     No change.\n"
                                " 86          Cruelty defined.                       378     Split in two.\n"
                                "                                                    Explanat   Sections 85 and 86 ok.\n"))
        self.assertEqual({r["bns"]: r["ipc"] for r in self.out["rows"]}["86"], "378")
        self.run_table(TABLE + " 21          Act of a child above seven under 29    No change.\n")
        self.assertEqual({r["bns"]: r["ipc"] for r in self.out["rows"]}["21"], "29")  # off the page's column

    def test_entries_are_typed_from_the_counts_and_aggregated_to_section_level(self):
        self.assertEqual(self.served(), {
            (("IPC 1", "IPC 2"), ("BNS 1",)): "merged",   # sub-sections 1(1) to 1(3), the New sub-row adds no IPC side
            (("IPC 29", "IPC 29A"), ("BNS 2",)): "merged",
            (("IPC 378",), ("BNS 303",)): "one-to-one",
            (("IPC 300",), ("BNS 101", "BNS 102")): "split",
            ((), ("BNS 9",)): "new",
        })
        e = self.out["entries"][0]
        self.assertTrue(e["verified"])
        self.assertEqual(e["basis"], "source-table-checked")
        self.assertIn("not an official MHA publication", e["evidence"])
        self.assertIn("1(1) (p.1)", e["evidence"])

    def test_known_bad_pair_with_no_shared_distinctive_word_is_not_served(self):
        self.assertNotIn((("IPC 120",), ("BNS 7",)), self.served())
        self.assertIn({"bns": ["BNS 7"], "ipc": ["IPC 120"], "type": "one-to-one", "reason": "no shared distinctive word",
                       "rows": ["7 (p.2)"]}, self.out["refused"])

    def test_a_cited_provision_missing_from_the_index_is_refused(self):
        self.assertEqual({r["reason"] for r in self.out["refused"] if r["bns"] == ["BNS 500"]}, {"cited provision not in the index"})

    def test_report_counts(self):
        self.assertEqual(self.out["report"], {
            "source": self.out["report"]["source"], "rows_parsed": 10,
            "entries_produced": {"merged": 2, "new": 1, "one-to-one": 3, "split": 1},
            "entries_served": 5, "entries_refused": 2,
            "refused_reasons": {"cited provision not in the index": 1, "no shared distinctive word": 1}})
        self.assertIn("not an official MHA publication", self.out["report"]["source"])

    def test_loader_accepts_the_new_basis_and_refuses_an_unknown_one(self):
        db = index.build(str(self.tmp / "i.sqlite"), PROVS, [])
        (self.tmp / "ok.json").write_text(json.dumps(self.out["entries"]))
        self.assertEqual(len(concordance.load(str(self.tmp / "ok.json"), db)), 5)
        bad = [{**self.out["entries"][0], "basis": "vibes"}]
        (self.tmp / "bad.json").write_text(json.dumps(bad))
        with self.assertRaises(ValueError):
            concordance.load(str(self.tmp / "bad.json"), db)

    def test_freeze_keeps_a_table_checked_entry_served(self):
        (self.tmp / "s.md").write_text("")
        (self.tmp / "g.json").write_text("[]")
        (self.tmp / "dc.json").write_text(json.dumps(self.out["entries"]))
        for n in ("b.pdf", "i.pdf"):
            (self.tmp / n).write_bytes(n.encode())
        from ibid import freeze
        marks = {f"ipc_to_bns-{i}": "pass" for i in range(12)}
        # the sheet-count rule is exercised in test_freeze; here the draft entries are passed through directly
        orig = freeze.parse_sheet
        freeze.parse_sheet = lambda _t: marks
        self.addCleanup(setattr, freeze, "parse_sheet", orig)
        gold = [{"id": i, "category": "ipc_to_bns", "query": "IPC 1", "expected_citations": ["BNS 1"], "expected_type": "one-to-one"} for i in marks]
        (self.tmp / "g.json").write_text(json.dumps(gold))
        self.assertEqual(freeze.freeze(str(self.tmp / "s.md"), str(self.tmp / "g.json"), str(self.tmp / "dc.json"),
                                       str(self.tmp / "og.json"), str(self.tmp / "oc.json")), 0)
        out = json.loads((self.tmp / "oc.json").read_text())
        self.assertTrue(all(e["verified"] and e["basis"] == "source-table-checked" for e in out))

    def test_v2_and_its_pin_are_untouched(self):
        root = Path(__file__).resolve().parent.parent / "concordance"
        self.assertEqual(hashlib.sha256((root / "v2.json").read_bytes()).hexdigest(), (root / "v2.sha256").read_text().strip())


if __name__ == "__main__":
    unittest.main()
