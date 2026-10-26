"""With the real assoc-nb v3 model present, learned top-5 over MCP equals the committed predictions."""
import json
import unittest

from mcp_harness import ROOT, Client, command
from pdfs import _main_checkout

PRED = ROOT / "results/layers/assoc-nb-v3-multicharge-v2-predictions.json"
GOLD = ROOT / "gold/multicharge/v2.json"
MODEL = next((p for p in (ROOT / "data/assoc-nb-v3.json", _main_checkout() / "data/assoc-nb-v3.json") if p.exists()), None)


@unittest.skipUnless(MODEL, "data/assoc-nb-v3.json is absent: produce it with `ibid assoc fit --source union` (needs the gated training data)")
class RealModelTest(unittest.TestCase):
    def check(self, swap: bool = False) -> None:
        pred = json.loads(PRED.read_text())
        items = json.loads(GOLD.read_text())["items"][:3]
        c = Client(command() + ["--assoc-model", str(MODEL)])
        try:
            for it in items:
                out = c.call("search", {"query": it["query"], "mode": "learned"})["result"]
                self.assertFalse(out["isError"], it["id"])
                sc = out["structuredContent"]
                self.assertEqual(sc["model_sha256"], pred["inputs"]["model"])
                want = list(pred["items"][it["id"]]["ipc"])
                if swap:
                    want[0], want[1] = want[1], want[0]
                self.assertEqual([h["citation"] for h in sc["results"]], want, it["id"])
        finally:
            c.close()

    def test_top5_matches_committed_predictions(self):
        self.check()

    def test_swapped_expectation_fails(self):
        with self.assertRaises(AssertionError):
            self.check(swap=True)


if __name__ == "__main__":
    unittest.main()
