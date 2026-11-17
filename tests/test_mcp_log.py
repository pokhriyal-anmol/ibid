"""IB3: one malformed argument must not kill the MCP server, and the owner must find the failure in stderr.
Exception to AGENTS.md rule 5: calls mcp.handle on a three-provision index so it runs without the source PDFs."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ibid import index, mcp  # noqa: E402
from ibid.parse import Provision  # noqa: E402

PROVS = [Provision("IPC 302", "Punishment for murder.", None, ())]


class McpLogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = index.build(str(Path(cls.tmp.name) / "i.sqlite"), PROVS, [])

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.tmp.cleanup()

    def call(self, msg: dict) -> tuple[dict | None, list[dict]]:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            reply = mcp.handle(self.db, [], msg, {}, mcp.LazyModel("unused"))
        return reply, [json.loads(line) for line in err.getvalue().splitlines()]

    def search(self, **arguments) -> dict:
        return {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "search", "arguments": {"query": "murder", **arguments}}}

    def test_an_unhashable_act_is_a_client_error_not_a_crash(self):
        reply, logs = self.call(self.search(act=[]))
        self.assertEqual(reply["error"]["code"], -32602)
        self.assertEqual([(r["event"], r["tool"], r["code"]) for r in logs], [("rejected", "search", -32602)])

    def test_an_unexpected_exception_is_an_internal_error_reply_and_a_log_line(self):
        original = mcp.call_tool
        mcp.call_tool = lambda *a, **k: 1 / 0
        try:
            reply, logs = self.call(self.search())
        finally:
            mcp.call_tool = original
        self.assertEqual(reply, {"jsonrpc": "2.0", "id": 7, "error": {"code": -32603, "message": "internal error"}})
        self.assertEqual([(r["event"], r["error_type"]) for r in logs], [("internal_error", "ZeroDivisionError")])

    def test_an_oversized_limit_is_a_client_error_not_an_internal_one(self):
        for limit in (2**63, 10**6):
            reply, logs = self.call(self.search(limit=limit))
            self.assertEqual(reply["error"]["code"], -32602, limit)
            self.assertEqual([r["event"] for r in logs], ["rejected"], limit)
        self.assertEqual(self.call(self.search(limit=10_000))[0]["result"]["isError"], False)

    def test_a_line_json_cannot_represent_is_refused_not_echoed(self):
        for bad in ('{"id":NaN}', '{"id":Infinity}', '{"id":1e400}', '{"id":-1e400}', '{"params":[1E999]}', "not json", "[" * 100000):
            with self.assertRaises((ValueError, RecursionError), msg=bad[:30]):
                mcp._decode(bad)
        self.assertEqual(mcp._decode('{"id":1.5,"x":1e300}'), {"id": 1.5, "x": 1e300})

    def test_an_invalid_request_is_logged(self):
        reply, logs = self.call({"jsonrpc": "2.0", "id": 3})
        self.assertEqual(reply["error"]["code"], -32600)
        self.assertEqual([(r["event"], r["code"]) for r in logs], [("rejected", -32600)])

    def test_a_good_call_logs_nothing(self):
        reply, logs = self.call(self.search())
        self.assertEqual(reply["result"]["structuredContent"]["results"][0]["citation"], "IPC 302")
        self.assertEqual(logs, [])


if __name__ == "__main__":
    unittest.main()
