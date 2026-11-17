"""IB18: a pinned fingerprint of the whole BNS parse, so a parser or cross-reference change that moves provisions,
text, edges or chains fails CI even though no gold item looks at them. CI fetches the BNS PDF, so this runs there.

The fingerprint holds hashes and counts only, never the Act's text. When a change to parsing is intended, bump
PARSER_VERSION in src/ibid/parse.py and regenerate it:

    uv run python tests/test_bns_fingerprint.py --write
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ibid.parse import PARSER_VERSION, parse_bns  # noqa: E402
from ibid.xref import chains, extract  # noqa: E402
from pdfs import BNS_PDF  # noqa: E402

PIN = Path(__file__).parent / "fixtures" / "bns-parse-fingerprint.json"


def _hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def fingerprint() -> dict:
    provisions = parse_bns(BNS_PDF)
    edges = extract(provisions)
    return {
        "parser_version": PARSER_VERSION,
        "provisions": len(provisions),
        "edges": len(edges),
        "parse_sha256": _hash([(p.citation, p.text, p.parent, list(p.children)) for p in provisions]),
        "edges_sha256": _hash([(e.source, e.matched, e.target, e.reason) for e in edges]),
        "chains_sha256": _hash(chains(provisions, edges)),
    }


class BnsParseFingerprintTest(unittest.TestCase):
    def test_the_bns_parse_matches_its_pinned_fingerprint(self):
        want, got = json.loads(PIN.read_text()), fingerprint()
        moved = [k for k in want if want[k] != got[k]]
        self.assertEqual(moved, [], f"BNS parse changed in {moved}: pinned {want}, got {got}. If intended, bump PARSER_VERSION and run --write")


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        PIN.write_text(json.dumps(fingerprint(), indent=1, sort_keys=True) + "\n")
        print(f"wrote {PIN}")
    else:
        unittest.main()
