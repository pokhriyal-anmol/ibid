"""`ibid mcp`: a stdio MCP server (newline-delimited JSON-RPC 2.0) over the deterministic lookups. No model (ADR 0001)."""
import json
import sys
import tempfile
from pathlib import Path

from ibid import concordance, index
from ibid.ipc import IPC_TOTAL, parse_ipc
from ibid.parse import BNS_TOTAL, parse_bns
from ibid.xref import extract

PROTOCOL_VERSION = "2024-11-05"
_CITATION = {"type": "object", "properties": {"citation": {"type": "string"}}, "required": ["citation"]}
TOOLS = {
    "get_provision": ("Verbatim text and child Citations of one Provision, by exact Citation.", _CITATION),
    "search": ("Keyword search over the raw query.",
               {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]}),
    "cross_references": ("Resolved and unresolved Cross-references of one Provision.", _CITATION),
    "concordance": ("Verified Concordance entries for a Citation.",
                    {"type": "object", "properties": {"citation": {"type": "string"},
                                                      "direction": {"type": "string", "enum": ["ipc_to_bns", "bns_to_ipc"]}},
                     "required": ["citation", "direction"]}),
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


def call_tool(db, name: str, args: object) -> dict:
    if name not in TOOLS:
        raise RpcError(-32602, f"unknown tool: {name}")
    if not isinstance(args, dict):
        raise RpcError(-32602, "arguments must be an object")
    for key in TOOLS[name][1]["required"]:
        if not isinstance(args.get(key), str):
            raise RpcError(-32602, f"missing or non-string argument: {key}")
    if name == "search":
        limit = args.get("limit", 10)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise RpcError(-32602, "limit must be an integer of at least 1")
        hits = index.search(db, args["query"], limit)
        return _tool_result({"results": [{"citation": c, "text": t} for c, t in hits]})
    if name != "get_provision":
        return _tool_result("not implemented", True)
    got = index.lookup(db, args["citation"])
    if got is None:
        return _tool_result(f"Citation not in the index: {args['citation']}", True)
    return _tool_result({"citation": args["citation"], "text": got[0], "children": got[1]})


def handle(db, msg: object) -> dict | None:
    if not isinstance(msg, dict) or not isinstance(msg.get("method"), str):
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
            result = call_tool(db, params["name"], params.get("arguments", {}))
        elif "id" not in msg:
            return None  # notifications, including notifications/initialized
        else:
            raise RpcError(-32601, f"method not found: {method}")
    except RpcError as e:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": e.code, "message": e.message}}
    return None if "id" not in msg else {"jsonrpc": "2.0", "id": mid, "result": result}


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def serve(bns_pdf: str, ipc_pdf: str, concordance_path: str) -> int:
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
            concordance.load(concordance_path, db)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                _emit({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
                continue
            if (reply := handle(db, msg)) is not None:
                _emit(reply)
    return 0
