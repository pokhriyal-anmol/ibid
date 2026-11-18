"""IB35: rules the seventh audit showed CI does not guard, checked without the source PDFs.
Exception to AGENTS.md rule 5: calls cli, concordance, crpc, index and mcp functions directly, because `ibid eval` needs both PDFs."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import test_gaps_without_pdfs as gaps  # noqa: E402
from ibid import cli, concordance, crpc, headings, index, mcp  # noqa: E402
from ibid.parse import Provision  # noqa: E402


def quiet(*argv: str) -> tuple[int, str]:
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        return cli.main(list(argv)), err.getvalue()


class ConcordanceSidesTest(unittest.TestCase):
    def load(self, entry: dict, provisions: list[Provision], old: str = "ipc", new: str = "bns"):
        with tempfile.TemporaryDirectory() as tmp:
            db = index.build(f"{tmp}/i.sqlite", provisions, [])
            Path(f"{tmp}/c.json").write_text(json.dumps([{"verified": True, **entry}]))
            try:
                return concordance.load(f"{tmp}/c.json", db, old, new)
            finally:
                db.close()

    def test_a_bnss_citation_is_not_accepted_on_the_bns_side(self):
        provs = [Provision("IPC 2", "2. x.", None, ()), Provision("BNSS 1", "1. y.", None, ())]
        with self.assertRaisesRegex(ValueError, "wrong side"):
            self.load({"type": "one-to-one", "ipc": ["IPC 2"], "bns": ["BNSS 1"]}, provs)

    def test_a_crpc_citation_is_not_accepted_on_the_bnss_side(self):
        provs = [Provision("CrPC 1", "1. x.", None, ()), Provision("CrPC 2", "2. y.", None, ())]
        with self.assertRaisesRegex(ValueError, "wrong side"):
            self.load({"type": "one-to-one", "crpc": ["CrPC 1"], "bnss": ["CrPC 2"]}, provs, "crpc", "bnss")

    def test_one_to_one_split_and_merged_need_both_sides(self):
        provs = [Provision("IPC 2", "2. x.", None, ()), Provision("BNS 3", "3. y.", None, ())]
        for kind in ("one-to-one", "split", "merged"):
            for entry in ({"ipc": ["IPC 2"], "bns": []}, {"ipc": [], "bns": ["BNS 3"]}):
                with self.assertRaisesRegex(ValueError, "needs both", msg=f"{kind} {entry}"):
                    self.load({"type": kind, **entry}, provs)


class LearnedLimitAndActTest(gaps.Base):
    def learned(self, **extra) -> dict:
        lazy = gaps.LearnedModeTest.Lazy(["IPC 2", "IPC 20", "IPC 2", "IPC 20"])
        return self.call("search", {"query": "x", "mode": "learned", **extra}, [gaps.ENTRY], lazy=lazy)[0]

    def test_learned_mode_returns_exactly_limit_results(self):
        for limit in (1, 2, 3):
            got = self.learned(limit=limit)["result"]["structuredContent"]["results"]
            self.assertEqual([r["rank"] for r in got], list(range(1, limit + 1)))

    def test_learned_mode_accepts_ipc_and_refuses_any_other_act(self):
        self.assertFalse(self.learned(act="ipc")["result"]["isError"])
        self.assertFalse(self.learned()["result"]["isError"])
        for act in ("bns", "crpc", "bnss"):
            self.assertTrue(self.learned(act=act)["result"]["isError"], act)


class HeadingsAndNeighboursTest(gaps.Base):
    def test_a_section_hit_carries_its_heading_and_a_sub_provision_hit_does_not(self):
        provs = [Provision("IPC 2", "2. Whoever commits murder.", None, ("IPC 2(1)",)),
                 Provision("IPC 2(1)", "(1) Whoever commits murder twice.", "IPC 2", ())]
        with tempfile.TemporaryDirectory() as tmp:
            db = index.build(f"{tmp}/h.sqlite", provs, [])
            msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search", "arguments": {"query": "twice"}}}
            reply = mcp.handle(db, [], msg, {"IPC 2": "Murder"}, mcp.LazyModel("unused"))
            msg["params"]["arguments"]["query"] = "commits"
            both = mcp.handle(db, [], msg, {"IPC 2": "Murder"}, mcp.LazyModel("unused"))
            db.close()
        self.assertEqual([r["heading"] for r in reply["result"]["structuredContent"]["results"]], [None])
        self.assertEqual({r["citation"]: r["heading"] for r in both["result"]["structuredContent"]["results"]}, {"IPC 2": "Murder", "IPC 2(1)": None})

    def test_the_neighbour_heading_is_the_first_line_cut_at_the_dash_and_at_100_characters(self):
        provs = [Provision("IPC 1", "1. Title.—Rest of the section.\nmore", None, ()), Provision("IPC 2", "2. " + "a" * 150, None, ()),
                 Provision("IPC 3", "3. Last.\nmore detail", None, ())]
        with tempfile.TemporaryDirectory() as tmp:
            db = index.build(f"{tmp}/n.sqlite", provs, [])
            prev, nxt = index.neighbours(db, "IPC 2")
            self.assertEqual(prev, ("IPC 1", "1. Title."))
            self.assertEqual(nxt, ("IPC 3", "3. Last."))
            self.assertEqual(index.neighbours(db, "IPC 3")[0], ("IPC 2", ("2. " + "a" * 150)[:100]))
            db.close()


class FootnoteNumeralTest(unittest.TestCase):
    def test_a_footnote_numeral_before_a_bracket_is_dropped_and_a_digit_run_after_text_is_not(self):
        self.assertEqual(crpc._clean("12[(1) The arrest] is made"), "(1) The arrest is made")
        self.assertEqual(crpc._clean("section 154 applies"), "section 154 applies")
        self.assertEqual(crpc._clean("fine 3*** only"), "fine only")


class CommandsTest(unittest.TestCase):
    def test_conform_exits_1_with_a_report_and_0_without(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("g", "b", "i"):
                Path(tmp, name).write_text("")
            args = ["conform", "--gold", f"{tmp}/g", "--bns", f"{tmp}/b", "--ipc", f"{tmp}/i"]
            with mock.patch("ibid.conform.conform", return_value=["x: not conformed"]):
                self.assertEqual(quiet(*args)[0], 1)
            with mock.patch("ibid.conform.conform", return_value=[]):
                self.assertEqual(quiet(*args)[0], 0)

    def test_links_list_refuses_a_concordance_that_does_not_match_its_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            index.build(f"{tmp}/i.sqlite", [Provision("IPC 2", "2. x.", None, ())], []).close()
            Path(f"{tmp}/c.json").write_text("[]")
            Path(f"{tmp}/c.sha256").write_text("0" * 64 + "\n")
            code, err = quiet("links", "list", "--index", f"{tmp}/i.sqlite", "--concordance", f"{tmp}/c.json")
        self.assertEqual(code, 1)
        self.assertIn("does not match its pin", err)

    def test_headings_with_a_layout_file_reads_the_layout_not_the_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(f"{tmp}/layout.txt").write_text("LAYOUT TEXT")
            with mock.patch.object(headings, "parse_layout", return_value=[("BNS 1", "Short title")]) as layout, \
                    mock.patch.object(headings, "bns_headings") as pdf:
                code, _ = quiet("headings", "list", "--act", "bns", "--layout", f"{tmp}/layout.txt")
        self.assertEqual(code, 0)
        layout.assert_called_once_with("LAYOUT TEXT")
        pdf.assert_not_called()


if __name__ == "__main__":
    unittest.main()
