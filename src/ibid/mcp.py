"""`ibid mcp`: a stdio MCP server (newline-delimited JSON-RPC 2.0) over the deterministic lookups. No model (ADR 0001)."""
import json
from datetime import datetime, timezone
import sqlite3
import sys
import tempfile
from pathlib import Path

from ibid import assoc, concordance, headings, index
from ibid.ipc import IPC_TOTAL, parse_ipc
from ibid.parse import BNS_TOTAL, parse_bns
from ibid.xref import extract

PROTOCOL_VERSION = "2024-11-05"
ACTS = {"ipc": "IPC", "bns": "BNS", "crpc": "CrPC", "bnss": "BNSS"}  # act argument to Citation prefix
DIRECTIONS = ("ipc_to_bns", "bns_to_ipc", "crpc_to_bnss", "bnss_to_crpc")
MODES = ("keyword", "learned")
# Figures are read-checked against results/layer-comparison.md by tests/test_mcp_limits.py.
KEYWORD_LIMITS = ("Keyword search finds 3.1 to 5.1 percent of IPC charges on set v1 and 4.8 to 6.0 percent on set v2 "
                  "(story-style queries, measured per set).")
CAVEAT = ("Learned mode was fitted on court-judgment text and layperson forum posts, covers 140 IPC sections, "
          "finds 58.3 percent of IPC charges on layperson posts (set v2) and 42.9 percent on judgment text (set v1), "
          "was measured on labels that are incomplete, and is not legal advice.")
_CITATION = {"type": "object", "properties": {"citation": {"type": "string"}}, "required": ["citation"]}
TOOLS = {
    "get_provision": ("Verbatim text and child Citations of one Provision, by exact Citation.", _CITATION),
    "search": (f"Search the Acts by the raw query. mode keyword (default): {KEYWORD_LIMITS} mode learned: {CAVEAT}",
               {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"},
                                                      "adjacent": {"type": "boolean"},
                                                      "act": {"type": "string", "enum": list(ACTS)},
                                                      "mode": {"type": "string", "enum": list(MODES)}}, "required": ["query"]}),
    "cross_references": ("Resolved and unresolved Cross-references of one Provision.", _CITATION),
    "concordance": ("Verified Concordance entries for a Citation.",
                    {"type": "object", "properties": {"citation": {"type": "string"},
                                                      "direction": {"type": "string", "enum": list(DIRECTIONS)}},
                     "required": ["citation"]}),
}


class RpcError(Exception):
    def __init__(self, code: int, message: str):
        self.code, self.message = code, message


def _tool_result(payload: dict | str, is_error: bool = False) -> dict:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    out = {"content": [{"type": "text", "text": text}], "isError": is_error}
    if isinstance(payload, dict):
        out["structuredContent"] = payload
    return out


class LazyModel:
    """The assoc-nb v3 model file, read on the first learned call and never at startup."""

    def __init__(self, path: str):
        self.path, self.model = path, None

    def get(self) -> assoc.Model:
        if self.model is None:
            try:
                model = assoc.Model(self.path)
                found = (model.header.get("layer"), model.header.get("layer_version"))
            except (OSError, ValueError, KeyError, TypeError, AttributeError, ZeroDivisionError) as e:
                raise ValueError(f"cannot read the learned model {self.path} ({e}); fit it with `ibid assoc fit --source union`") from None
            if found != (assoc.LAYER, "v3"):
                raise ValueError(f"model {self.path} is {found[0]} {found[1]}, expected {assoc.LAYER} v3")
            self.model = model
        return self.model


def _learned(db, entries: list[dict], heads: dict, lazy: LazyModel, args: dict) -> dict:
    limit = args.get("limit", assoc.TOP_K)
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise RpcError(-32602, "limit must be an integer of at least 1")
    try:
        model = lazy.get()
    except ValueError as e:
        return _tool_result(str(e), True)
    notes = []
    if limit > assoc.TOP_K:
        notes.append(f"limit clamped to {assoc.TOP_K}")
    if args.get("adjacent"):
        notes.append("adjacent is not supported in learned mode and was ignored")
    results = [{"citation": c, "heading": heads.get(c), "text": index.lookup(db, c)[0], "rank": r,
                "bns": list(dict.fromkeys(b for h in entries if h["verified"] and c in h["ipc"] for b in h["bns"]))}
               for r, c in enumerate(model.predict(args["query"])[:limit], 1)]
    out = {"results": results, "layer": assoc.LAYER, "layer_version": model.header["layer_version"],
           "model_sha256": model.sha256, "caveat": CAVEAT}
    return _tool_result({**out, "notes": notes} if notes else out)


def call_tool(db, entries: list[dict], name: str, args: object, heads: dict[str, str | None], lazy: LazyModel, procedure: tuple | None = None) -> dict:
    # section Citation to heading; a sub-provision is absent, so its heading is null
    if name not in TOOLS:
        raise RpcError(-32602, f"unknown tool: {name}")
    if not isinstance(args, dict):
        raise RpcError(-32602, "arguments must be an object")
    for key in TOOLS[name][1]["required"]:
        if not isinstance(args.get(key), str):
            raise RpcError(-32602, f"missing or non-string argument: {key}")
    if name == "search":
        if args.get("mode", "keyword") not in MODES:
            return _tool_result("mode must be " + " or ".join(MODES), True)
        if args.get("mode") == "learned":
            if args.get("act", "ipc") != "ipc":
                return _tool_result("learned mode covers IPC sections only; leave act out or pass ipc", True)
            return _learned(db, entries, heads, lazy, args)
        limit = args.get("limit", 10)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise RpcError(-32602, "limit must be an integer of at least 1")
        if not isinstance(args.get("adjacent", False), bool):
            raise RpcError(-32602, "adjacent must be a boolean")
        act = args.get("act")
        if "act" in args and (not isinstance(act, str) or act not in ACTS):
            raise RpcError(-32602, "act must be one of " + ", ".join(ACTS))
        if act in ("crpc", "bnss"):  # the second index
            if not procedure:
                return _tool_result("The second index is not built, so CrPC and BNSS are not searchable.", True)
            db, heads = procedure[:2]
        hits, extra = index.search_explained(db, args["query"], limit, ACTS.get(act))
        results = [{"citation": c, "text": t, "heading": heads.get(c)} for c, t in hits]
        if args.get("adjacent"):
            for r in results:
                prev, nxt = index.neighbours(db, r["citation"])
                r["previous"], r["next"] = [None if n is None else {"citation": n[0], "heading": heads.get(n[0]) or n[1]} for n in (prev, nxt)]
        return _tool_result({"results": results, **extra})
    if name == "concordance":
        prefix = args["citation"].split(" ")[0].lower()
        inferred = {d.split("_to_")[0]: d for d in DIRECTIONS}.get(prefix)
        direction = args.get("direction", inferred)
        if direction not in DIRECTIONS:
            raise RpcError(-32602, "direction must be " + " or ".join(DIRECTIONS))
        if inferred and direction != inferred:
            return _tool_result(f"direction {direction} contradicts the Citation prefix {prefix.upper()} (expects {inferred})", True)
        src, dst = direction.split("_to_")
        if src in ("crpc", "bnss"):
            entries = procedure[2] if procedure else []
        got = concordance.lookup(entries, args["citation"], src, dst)
        section = args["citation"].split("(")[0].strip()
        if isinstance(got, str) and section != args["citation"]:  # sub-provision: retry its section
            got = concordance.lookup(entries, section, src, dst)
            if not isinstance(got, str):
                return _tool_result({"result": got, "via": section})
        return _tool_result(got if isinstance(got, str) else {"result": got})
    if procedure and args["citation"].split(" ")[0] in ("CrPC", "BNSS"):  # the second index holds the procedure Acts
        db, heads = procedure[:2]
    got = index.lookup(db, args["citation"])
    if got is None:
        return _tool_result(f"Citation not in the index: {args['citation']}. Covered Acts: IPC, BNS, CrPC, BNSS.", True)
    if name == "cross_references":
        miss = [{"matched": u["matched"], "reason": u["reason"]} for u in index.unresolved(db) if u["source"] == args["citation"]]
        return _tool_result({"citation": args["citation"], "resolved": got[2], "unresolved": miss})
    return _tool_result({"citation": args["citation"], "heading": heads.get(args["citation"]), "text": got[0], "children": got[1]})


def _log(event: str, msg: object, **fields: object) -> None:
    """One JSON line on stderr per failed request, for whoever runs the server (stdout carries only JSON-RPC)."""
    msg = msg if isinstance(msg, dict) else {}
    params = msg.get("params")
    tool = params.get("name") if isinstance(params, dict) and isinstance(params.get("name"), str) else None
    print(json.dumps({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": event, "id": msg.get("id"),
                      "method": msg.get("method") if isinstance(msg.get("method"), str) else None, "tool": tool, **fields}), file=sys.stderr, flush=True)


def handle(db, entries: list[dict], msg: object, heads: dict[str, str | None], lazy: LazyModel, procedure: tuple | None = None) -> dict | None:
    if not isinstance(msg, dict) or not isinstance(msg.get("method"), str):
        _log("rejected", msg, code=-32600, message="invalid request")
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}}
    mid, method, params = msg.get("id"), msg["method"], msg.get("params") or {}
    try:
        if method == "initialize":
            result = {"protocolVersion": PROTOCOL_VERSION, "serverInfo": {"name": "ibid", "version": "0.1"},
                      "capabilities": {"tools": {}}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [{"name": n, "description": d, "inputSchema": s} for n, (d, s) in TOOLS.items()]}
        elif method == "tools/call":
            if not isinstance(params, dict) or not isinstance(params.get("name"), str):
                raise RpcError(-32602, "params.name is required")
            result = call_tool(db, entries, params["name"], params.get("arguments", {}), heads, lazy, procedure)
        elif "id" not in msg:
            return None  # notifications, including notifications/initialized
        else:
            raise RpcError(-32601, f"method not found: {method}")
    except RpcError as e:
        _log("rejected", msg, code=e.code, message=e.message)
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": e.code, "message": e.message}}
    except Exception as e:  # a bug or an input nobody validated must not end the session; the client gets no stack trace
        _log("internal_error", msg, error_type=type(e).__name__, message=str(e))
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": "internal error"}}
    return None if "id" not in msg else {"jsonrpc": "2.0", "id": mid, "result": result}


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def serve(bns_pdf: str, ipc_pdf: str, concordance_path: str, assoc_model: str, procedure_index: str | None = None, procedure_concordance: str | None = None) -> int:
    for path in (bns_pdf, ipc_pdf, concordance_path):
        if not Path(path).is_file():
            print(f"error: no such file: {path}", file=sys.stderr)
            return 1
    provisions = []
    for act, parse, total, pdf in (("BNS", parse_bns, BNS_TOTAL, bns_pdf), ("IPC", parse_ipc, IPC_TOTAL, ipc_pdf)):
        parsed = parse(pdf)
        if sum(p.parent is None for p in parsed) != total:
            print(f"error: {act} section count does not match the known total", file=sys.stderr)
            return 1
        provisions += parsed
    with tempfile.TemporaryDirectory() as tmp:
        db = index.build(str(Path(tmp) / "ibid.sqlite"), provisions, extract(provisions))
        try:
            entries = concordance.load(concordance_path, db)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        heads = dict(headings.bns_headings(bns_pdf) + headings.ipc_headings(ipc_pdf))
        lazy = LazyModel(assoc_model)
        procedure = None
        if procedure_index and Path(procedure_index).is_file():
            pdb = sqlite3.connect(f"file:{procedure_index}?mode=ro", uri=True)
            try:
                pentries = concordance.load(procedure_concordance, pdb, "crpc", "bnss") if procedure_concordance and Path(procedure_concordance).is_file() else []
            except ValueError as e:
                print(f"error: {e}", file=sys.stderr)
                return 1
            procedure = (pdb, dict(pdb.execute("SELECT citation, heading FROM heading")), pentries)
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                _log("rejected", None, code=-32700, message="parse error")
                _emit({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
                continue
            if (reply := handle(db, entries, msg, heads, lazy, procedure)) is not None:
                _emit(reply)
    return 0
