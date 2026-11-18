"""IB31: `mcp.serve` (the stdin to stdout loop) and `ibid eval` checked without the source PDFs, which CI cannot all fetch.
Exception to AGENTS.md rule 5: the PDF parsers are replaced by a tiny fixed corpus, so the real loop and the real command run on it."""
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
from ibid import cli, headings, mcp  # noqa: E402
from ibid.parse import Provision  # noqa: E402

BNS = [Provision("BNS 103", "103. Whoever commits murder.", None, ())]
IPC = [Provision("IPC 302", "302. Whoever commits murder.", None, ())]
CONCORDANCE = [{"type": "one-to-one", "ipc": ["IPC 302"], "bns": ["BNS 103"], "verified": True, "basis": "human-checked"}]


def tmp_files(tmp: str) -> tuple[str, str]:
    conc = Path(tmp) / "c.json"
    conc.write_text(json.dumps(CONCORDANCE))
    return str(conc), str(Path(tmp) / "pdf")


def serve(lines: list[str], tmp: str) -> tuple[int, list[dict], str]:
    conc, pdf = tmp_files(tmp)
    Path(pdf).write_bytes(b"")
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(mcp, "parse_bns", lambda _p: BNS), mock.patch.object(mcp, "parse_ipc", lambda _p: IPC), \
            mock.patch.object(mcp, "BNS_TOTAL", 1), mock.patch.object(mcp, "IPC_TOTAL", 1), \
            mock.patch.object(headings, "bns_headings", lambda _p: []), mock.patch.object(headings, "ipc_headings", lambda _p: []), \
            mock.patch.object(sys, "stdin", io.StringIO("\n".join(lines) + "\n")), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = mcp.serve(pdf, pdf, conc, "unused")
    return code, [json.loads(line) for line in out.getvalue().splitlines()], err.getvalue()


def call(i: int, name: str, **args) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args}})


class ServeLoopTest(unittest.TestCase):
    def test_a_deeply_nested_line_is_a_parse_error_and_the_session_survives(self):
        deep = '{"jsonrpc":"2.0","id":1,"method":"ping","params":' + "[" * 100000 + "]" * 100000 + "}"
        with tempfile.TemporaryDirectory() as tmp:
            code, replies, _ = serve([deep, '{"jsonrpc":"2.0","id":2,"method":"ping"}'], tmp)
        self.assertEqual(code, 0)
        self.assertEqual([r.get("error", {}).get("code") for r in replies], [-32700, None])
        self.assertEqual(replies[1]["result"], {})

    def test_every_line_gets_exactly_one_reply_and_a_notification_none(self):
        lines = ['{"jsonrpc":"2.0","id":1,"method":"ping"}', '{"jsonrpc":"2.0","method":"notifications/initialized"}',
                 '{"jsonrpc":"2.0","id":NaN,"method":"ping"}', "not json", "", call(5, "get_provision", citation="BNS 103")]
        with tempfile.TemporaryDirectory() as tmp:
            _, replies, _ = serve(lines, tmp)
        self.assertEqual(len(replies), 4)
        self.assertEqual([r["id"] for r in replies], [1, None, None, 5])
        self.assertIn("murder", json.dumps(replies[3]))

    def test_a_search_over_the_stub_corpus_finds_both_acts(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, replies, _ = serve([call(1, "search", query="murder")], tmp)
        found = [h["citation"] for h in replies[0]["result"]["structuredContent"]["results"]]
        self.assertEqual(sorted(found), ["BNS 103", "IPC 302"])

    def test_a_section_count_that_differs_from_the_known_total_stops_the_server_either_way(self):
        for total in (0, 2):  # one parsed: too many, then too few
            with tempfile.TemporaryDirectory() as tmp, mock.patch.object(mcp, "BNS_TOTAL", total):
                conc, pdf = tmp_files(tmp)
                Path(pdf).write_bytes(b"")
                err = io.StringIO()
                with mock.patch.object(mcp, "parse_bns", lambda _p: BNS), mock.patch.object(mcp, "parse_ipc", lambda _p: IPC), \
                        mock.patch.object(mcp, "IPC_TOTAL", 1), contextlib.redirect_stderr(err):
                    self.assertEqual(mcp.serve(pdf, pdf, conc, "unused"), 1, total)
            self.assertIn("section count", err.getvalue())


class EvalCommandTest(unittest.TestCase):
    def gold(self, tmp: str, pinned: bool = True) -> str:
        path = Path(tmp) / "g.json"
        path.write_text(json.dumps([{"id": "s1", "category": "section_lookup", "query": "BNS 103", "expected_text": BNS[0].text}]))
        if pinned:
            path.with_suffix(".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest() + "\n")
        return str(path)

    def run_eval(self, tmp: str, gold: str, *extra: str, bns_total: int = 1) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        Path(f"{tmp}/pdf").write_bytes(b"")  # exists, so the missing-PDF check passes; the parsers are replaced below
        with mock.patch.object(cli, "parse_bns", lambda _p: BNS), mock.patch.object(cli, "parse_ipc", lambda _p: IPC), \
                mock.patch.object(cli, "BNS_TOTAL", bns_total), mock.patch.object(cli, "IPC_TOTAL", 1), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["eval", "--gold", gold, "--bns", f"{tmp}/pdf", "--ipc", f"{tmp}/pdf", "--index", f"{tmp}/i.sqlite", "--out", f"{tmp}/r.json", *extra])
        return code, out.getvalue(), err.getvalue()

    def test_the_default_mode_is_scored_and_refuses_an_unpinned_gold_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = self.run_eval(tmp, self.gold(tmp, pinned=False))
        self.assertEqual(code, 1)
        self.assertIn("scored mode refused", err)

    def test_a_pinned_gold_file_is_scored_and_the_result_records_the_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = self.run_eval(tmp, self.gold(tmp))
            self.assertEqual(code, 0, err)
            result = json.loads((Path(tmp) / "r.json").read_text())
        self.assertEqual(result["mode"], "scored")
        self.assertEqual(result["sections"]["BNS"], {"recovered": 1, "expected": 1})
        self.assertEqual(result["categories"], {"section_lookup": {"passed": 1, "total": 1}})
        self.assertEqual(result["parser_version"], cli.PARSER_VERSION)

    def test_more_sections_than_the_known_total_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = self.run_eval(tmp, self.gold(tmp), bns_total=0)
        self.assertEqual(code, 1)
        self.assertIn("section count", err)
        self.assertFalse((Path(tmp) / "r.json").exists())


if __name__ == "__main__":
    unittest.main()
