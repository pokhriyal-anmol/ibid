"""IB29: a pinned fingerprint of the whole CrPC and BNSS parse, as test_bns_fingerprint.py does for the BNS, so a change to
either parser or to their cross-references fails CI. CI fetches both PDFs. The fingerprint holds hashes and counts only, never
the Acts' text. When a change is intended, bump CRPC_PARSER_VERSION or BNSS_PARSER_VERSION and regenerate it:

    uv run python tests/test_procedure_fingerprint.py --write
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ibid.bnss import BNSS_PARSER_VERSION, parse_bnss  # noqa: E402
from ibid.crpc import CRPC_PARSER_VERSION, parse_crpc  # noqa: E402
from ibid.xref import chains, extract  # noqa: E402
from pdfs import BNSS_PDF, CRPC_PDF  # noqa: E402

PIN = Path(__file__).parent / "fixtures" / "procedure-parse-fingerprint.json"


def _hash(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _parse(provisions: list) -> list:
    return [(p.citation, p.text, p.parent, list(p.children)) for p in provisions]


def fingerprint() -> dict:
    crpc, crpc_arr = parse_crpc(CRPC_PDF)
    bnss, bnss_heads, bnss_arr = parse_bnss(BNSS_PDF)
    both = crpc + bnss  # the second index is built over both, as `ibid procedure build` does
    edges = extract(both)
    return {
        "crpc": {"parser_version": CRPC_PARSER_VERSION, "provisions": len(crpc), "parse_sha256": _hash(_parse(crpc)), "arrangement_sha256": _hash(crpc_arr)},
        "bnss": {"parser_version": BNSS_PARSER_VERSION, "provisions": len(bnss), "parse_sha256": _hash(_parse(bnss)),
                 "headings_sha256": _hash(bnss_heads), "arrangement_sha256": _hash(bnss_arr)},
        "xref": {"edges": len(edges), "edges_sha256": _hash([(e.source, e.matched, e.target, e.reason) for e in edges]),
                 "chains_sha256": _hash(chains(both, edges))},
    }


def _moved(want: dict, got: dict, path: str = "") -> list[str]:
    return [p for k in want for p in (_moved(want[k], got[k], f"{path}{k}.") if isinstance(want[k], dict) else [f"{path}{k}"] if want[k] != got[k] else [])]


class ProcedureParseFingerprintTest(unittest.TestCase):
    def test_the_crpc_and_bnss_parse_matches_its_pinned_fingerprint(self):
        want, got = json.loads(PIN.read_text()), fingerprint()
        moved = _moved(want, got)
        self.assertEqual(moved, [], f"CrPC or BNSS parse changed in {moved}. If intended, bump the parser version and run --write")


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        PIN.write_text(json.dumps(fingerprint(), indent=1, sort_keys=True) + "\n")
        print(f"wrote {PIN}")
    else:
        unittest.main()
