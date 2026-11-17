"""IB22 and IB23: rules the fifth audit showed CI does not guard, checked without the source PDFs. Each test was written
against a planted bug that survived (see docs/readiness/ledger.md).
Exception to AGENTS.md rule 5: calls index, concordance, mcp and cli functions directly, because `ibid eval` needs both PDFs."""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ibid import cli, concordance, index, ipc, mcp  # noqa: E402
from ibid.parse import PARSER_VERSION, Provision  # noqa: E402
from ibid.xref import Edge  # noqa: E402

ROOT = Path(__file__).parent.parent
PROVS = [Provision("IPC 100", "100. Definitions of terms.", None, ()),
         Provision("IPC 302", "302. Whoever commits murder shall be punished with death.", None, ()),
         Provision("IPC 379", "379. Whoever commits theft shall be punished.", None, ()),
         Provision("IPC 500", "500. Whoever defames another shall be punished.", None, ()),
         Provision("BNS 103", "103. Whoever commits murder shall be punished.", None, ())]
EDGES = [Edge("IPC 302", "section 9", None, "not in this Act"), Edge("IPC 100", "section 7", None, "repealed"), Edge("IPC 379", "section 3", None, "a table")]
PROCEDURE = [Provision("CrPC 1", "1. Short title of the Code.", None, ()), Provision("BNSS 1", "1. Short title of the Sanhita.", None, ()),
             Provision("BNS 103", "103. A BNS citation placed in this index for the side check.", None, ())]


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = index.build(str(Path(cls.tmp.name) / "i.sqlite"), PROVS, EDGES)
        cls.pdb = index.build(str(Path(cls.tmp.name) / "p.sqlite"), PROCEDURE, [])

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.pdb.close()
        cls.tmp.cleanup()

    def handle(self, name: str, arguments: dict, entries: list[dict] | None = None, heads: dict | None = None, procedure: tuple | None = None) -> dict:
        msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
        with contextlib.redirect_stderr(io.StringIO()):
            return mcp.handle(self.db, entries or [], msg, heads or {}, mcp.LazyModel("unused"), procedure)


class IpcKeyTest(unittest.TestCase):
    def test_a_section_key_is_its_number_and_up_to_two_capital_letters(self):
        self.assertEqual(ipc._key("124AA. Waging war."), "124AA")
        self.assertEqual(ipc._key("5. Heading"), "5")
        self.assertEqual(ipc._key("[302. Murder"), "302")
        self.assertEqual(ipc._key("12A Heading"), "12A")
        self.assertIsNone(ipc._key("Heading without a number"))


class ConcordanceRulesTest(Base):
    def load(self, entry: dict, db, old: str, new: str) -> list[dict]:
        path = Path(self.tmp.name) / "c.json"
        path.write_text(json.dumps([entry]))
        return concordance.load(str(path), db, old, new)

    def test_the_procedure_sides_take_crpc_and_bnss_citations_only(self):
        good = {"type": "one-to-one", "crpc": ["CrPC 1"], "bnss": ["BNSS 1"], "verified": True}
        self.assertEqual(self.load(good, self.pdb, "crpc", "bnss"), [good])
        with self.assertRaisesRegex(ValueError, "wrong side"):
            self.load({**good, "bnss": ["BNS 103"]}, self.pdb, "crpc", "bnss")  # BNS 103 is in the index, but it is not a BNSS citation

    def test_lookup_returns_verified_entries_in_file_order(self):
        entries = [{"type": "split", "ipc": ["IPC 302"], "bns": [f"BNS {n}"], "verified": True} for n in (9, 3, 7)]
        got = concordance.lookup(entries, "IPC 302", "ipc", "bns")
        self.assertEqual([g["citations"] for g in got], [["BNS 9"], ["BNS 3"], ["BNS 7"]])


class McpRoutingTest(Base):
    def test_procedure_citations_are_read_from_the_second_index(self):
        procedure = (self.pdb, {"BNSS 1": "Short title.", "CrPC 1": "Short title of the Code."}, [])
        for citation, text in (("BNSS 1", "Sanhita"), ("CrPC 1", "Code")):
            res = self.handle("get_provision", {"citation": citation}, procedure=procedure)["result"]
            self.assertFalse(res["isError"], citation)
            self.assertIn(text, res["structuredContent"]["text"])
        self.assertTrue(self.handle("get_provision", {"citation": "BNSS 1"})["result"]["isError"])  # no second index: not found

    def test_a_sub_provision_concordance_falls_back_to_its_section_and_says_so(self):
        entries = [{"type": "one-to-one", "ipc": ["IPC 302"], "bns": ["BNS 103"], "verified": True}]
        sub = self.handle("concordance", {"citation": "IPC 302(1)"}, entries)["result"]["structuredContent"]
        self.assertEqual((sub["via"], sub["result"][0]["citations"]), ("IPC 302", ["BNS 103"]))
        self.assertNotIn("via", self.handle("concordance", {"citation": "IPC 302"}, entries)["result"]["structuredContent"])

    def test_adjacent_headings_come_from_the_heading_table_else_the_section_text(self):
        res = self.handle("search", {"query": "theft", "adjacent": True}, heads={"IPC 302": "Murder."})["result"]["structuredContent"]["results"]
        self.assertEqual(res[0]["citation"], "IPC 379")
        self.assertEqual(res[0]["previous"], {"citation": "IPC 302", "heading": "Murder."})
        self.assertEqual(res[0]["next"]["citation"], "IPC 500")
        self.assertTrue(res[0]["next"]["heading"].startswith("500. Whoever defames"))  # no table entry: the first line of the text


class IndexRulesTest(Base):
    def test_unresolved_references_are_listed_in_the_order_they_were_found(self):
        self.assertEqual([u["source"] for u in index.unresolved(self.db)], ["IPC 302", "IPC 100", "IPC 379"])

    def test_a_neighbour_heading_is_cut_at_100_characters(self):
        provs = [Provision("IPC 1", "1. Short.", None, ()), Provision("IPC 2", "2. " + "x" * 200, None, ())]
        with tempfile.TemporaryDirectory() as tmp:
            db = index.build(str(Path(tmp) / "i.sqlite"), provs, [])
            self.assertEqual(len(index.neighbours(db, "IPC 1")[1][1]), 100)
            db.close()


class ResultsRecordTest(Base):
    def test_the_results_record_names_its_inputs_and_counts_both_acts_cross_references(self):
        conc = Path(self.tmp.name) / "conc.json"
        conc.write_text("[]")
        rec = cli.build_results(self.db, {"mode": "draft", "gold_path": "gold/v2.json", "gold_bytes": b"[]", "concordance_path": str(conc)},
                                {"BNS": {"recovered": 1, "expected": 1}}, {"keyword": {"passed": 1, "total": 1}}, [])
        self.assertEqual((rec["mode"], rec["gold_version"], rec["parser_version"]), ("draft", "v2", PARSER_VERSION))
        self.assertEqual(rec["gold_sha256"], hashlib.sha256(b"[]").hexdigest())
        self.assertEqual(rec["concordance"], {"file": "conc.json", "sha256": hashlib.sha256(b"[]").hexdigest()})
        self.assertEqual(set(rec["xref"]), {"BNS", "IPC"})
        self.assertEqual(rec["xref"]["IPC"], {"resolved": 0, "unresolved": 3})
        self.assertEqual([u["source"] for u in rec["unresolved_xref"]], ["IPC 302", "IPC 100", "IPC 379"])


class CliDefaultsTest(unittest.TestCase):
    def test_the_mcp_server_defaults_to_the_newest_pinned_concordance(self):
        newest = max((ROOT / "concordance").glob("v[0-9]*.json"), key=lambda p: int(p.stem[1:]))
        with mock.patch("ibid.mcp.serve", return_value=0) as serve:
            self.assertEqual(cli.main(["mcp", "--bns", __file__, "--ipc", __file__]), 0)
        self.assertEqual(Path(serve.call_args.args[2]), Path("concordance") / newest.name)
        self.assertIsNone(cli.pin_error(str(newest), newest.read_bytes()))


class ValidationTest(Base):
    def test_an_unknown_gold_category_is_refused_not_scored_as_a_lookup(self):
        with self.assertRaisesRegex(ValueError, "unknown category"):
            cli.score_item(self.db, [], {"id": "x", "category": "bogus", "query": "IPC 302", "expected_text": PROVS[1].text})
        item = {"id": "x", "category": "section_lookup", "query": "IPC 302", "expected_text": PROVS[1].text}
        self.assertTrue(cli.score_item(self.db, [], item)["pass"])

    def test_jsonrpc_must_be_2_0_and_the_id_a_string_number_or_null(self):
        def ask(**fields) -> dict:
            with contextlib.redirect_stderr(io.StringIO()):
                return mcp.handle(self.db, [], {"method": "ping", **fields}, {}, mcp.LazyModel("unused"))
        for bad in ({}, {"jsonrpc": "1.0", "id": 1}, {"jsonrpc": 2, "id": 1}, {"jsonrpc": "2.0", "id": {"a": 1}},
                    {"jsonrpc": "2.0", "id": [1]}, {"jsonrpc": "2.0", "id": True}):
            self.assertEqual(ask(**bad)["error"]["code"], -32600, bad)
            self.assertIsNone(ask(**bad)["id"], bad)
        for good in ("x", 7, 1.5, None):
            self.assertEqual(ask(jsonrpc="2.0", id=good)["result"], {}, good)


if __name__ == "__main__":
    unittest.main()
