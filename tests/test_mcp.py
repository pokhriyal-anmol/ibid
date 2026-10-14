"""`ibid mcp` through the one seam: JSON-RPC over stdio. Expected values come from index.lookup on the test's own index."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from ibid import concordance, index
from ibid.ipc import parse_ipc
from ibid.parse import parse_bns
from ibid.xref import extract
from mcp_harness import ENV, ROOT, Client, command
from pdfs import BNS_PDF, IPC_PDF


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        provs = parse_bns(BNS_PDF) + parse_ipc(IPC_PDF)
        cls.db = index.build(str(Path(cls.tmp.name) / "i.sqlite"), provs, extract(provs))
        cls.sub = next(p.citation for p in provs if p.parent and p.citation.startswith("BNS"))
        cls.ipc = next(p.citation for p in provs if p.parent is None and p.citation.startswith("IPC"))
        cls.c = Client()

    @classmethod
    def tearDownClass(cls):
        cls.c.close()
        cls.tmp.cleanup()

    def test_initialize_and_tools_list(self):
        r = self.c.request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t"}})
        self.assertIn("tools", r["result"]["capabilities"])
        self.assertIn("protocolVersion", r["result"])
        self.assertIn("serverInfo", r["result"])
        tools = self.c.request("tools/list")["result"]["tools"]
        self.assertEqual(sorted(t["name"] for t in tools), ["concordance", "cross_references", "get_provision", "search"])
        for t in tools:
            self.assertEqual(t["inputSchema"]["type"], "object")
            self.assertTrue(t["inputSchema"]["required"])

    def test_get_provision_matches_lookup(self):
        for cit in ("BNS 103", self.ipc, self.sub):
            text, children, _ = index.lookup(self.db, cit)
            res = self.c.call("get_provision", {"citation": cit})["result"]
            self.assertFalse(res["isError"], cit)
            self.assertEqual(res["structuredContent"]["text"], text, cit)
            self.assertEqual(res["structuredContent"]["children"], children, cit)
            self.assertEqual(json.loads(res["content"][0]["text"])["text"], text, cit)

    def test_unknown_citation_is_a_tool_error_with_no_text(self):
        for cit in ("BNS 9999", "bns 103"):
            res = self.c.call("get_provision", {"citation": cit})["result"]
            self.assertTrue(res["isError"], cit)
            self.assertNotIn("structuredContent", res)
            self.assertIn("not in the index", res["content"][0]["text"])

    def test_protocol_errors_and_server_keeps_running(self):
        self.assertEqual(self.c.send_raw("{not json")["error"]["code"], -32700)
        self.assertEqual(self.c.request("no/such")["error"]["code"], -32601)
        self.assertEqual(self.c.call("no_such_tool", {})["error"]["code"], -32602)
        self.assertEqual(self.c.call("get_provision", {})["error"]["code"], -32602)
        self.assertEqual(self.c.call("get_provision", {"citation": 103})["error"]["code"], -32602)
        self.assertEqual(self.c.request("ping")["result"], {})

    def test_notification_gets_no_response(self):
        self.c.notify("notifications/initialized")
        # if a stray reply were written, it would be read here instead of the ping reply
        self.assertEqual(self.c.request("ping")["id"], self.c.n)

    def test_unbuilt_tools_return_not_implemented(self):
        res = self.c.call("search", {"query": "murder"})["result"]
        self.assertTrue(res["isError"])


class ConcordanceToolTest(unittest.TestCase):
    FIXTURE = "tests/fixtures/concordance.json"

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        provs = parse_bns(BNS_PDF) + parse_ipc(IPC_PDF)
        db = index.build(str(Path(cls.tmp.name) / "i.sqlite"), provs, extract(provs))
        cls.v3 = concordance.load(str(ROOT / "concordance/v3.json"), db)
        cls.fix = concordance.load(str(ROOT / cls.FIXTURE), db)
        cls.c = Client()
        cls.cf = Client(command(conc=cls.FIXTURE))

    @classmethod
    def tearDownClass(cls):
        cls.c.close()
        cls.cf.close()
        cls.tmp.cleanup()

    def check(self, client, entries, citation, src, dst):
        want = concordance.lookup(entries, citation, src, dst)
        res = client.call("concordance", {"citation": citation, "direction": f"{src}_to_{dst}"})["result"]
        self.assertFalse(res["isError"])
        if isinstance(want, str):
            self.assertEqual(res["content"][0]["text"], want)
        else:
            self.assertEqual(res["structuredContent"]["result"], want)
        return want

    def test_both_directions_match_lookup(self):
        for src, dst in (("ipc", "bns"), ("bns", "ipc")):
            cit = next(e[src][0] for e in self.v3 if e["verified"] and e[src] and e[dst])
            self.assertIsInstance(self.check(self.c, self.v3, cit, src, dst), list)

    def test_only_unverified_gives_none(self):
        self.assertEqual(self.check(self.cf, self.fix, "IPC 304B", "ipc", "bns"), concordance.NONE)
        self.assertEqual(self.check(self.cf, self.fix, "BNS 80", "bns", "ipc"), concordance.NONE)

    def test_bad_direction_is_an_error_and_server_survives(self):
        for args in ({"citation": "IPC 302"}, {"citation": "IPC 302", "direction": "sideways"}):
            self.assertEqual(self.c.call("concordance", args)["error"]["code"], -32602)
        self.assertEqual(self.c.request("ping")["result"], {})


class StartupFailureTest(unittest.TestCase):
    def run_bad(self, args):
        p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=120, env=ENV)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(p.stdout, "")
        self.assertEqual(len(p.stderr.strip().splitlines()), 1)

    def test_missing_pdf(self):
        self.run_bad(command(bns="/no/such.pdf"))

    def test_missing_concordance(self):
        self.run_bad(command(conc="/no/such.json"))


if __name__ == "__main__":
    unittest.main()
