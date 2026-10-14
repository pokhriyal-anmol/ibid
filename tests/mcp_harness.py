"""Starts `ibid mcp` as a subprocess and talks newline-delimited JSON-RPC to it. Shared by the MCP tests."""
import json
import os
import subprocess
import sys
from pathlib import Path

from pdfs import BNS_PDF, IPC_PDF

ROOT = Path(__file__).parent.parent
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}


def command(bns: str = BNS_PDF, ipc: str = IPC_PDF, conc: str = "concordance/v3.json") -> list[str]:
    return [sys.executable, "-m", "ibid.cli", "mcp", "--bns", bns, "--ipc", ipc, "--concordance", conc]


class Client:
    def __init__(self, args: list[str] | None = None):
        self.proc = subprocess.Popen(args or command(), cwd=ROOT, env=ENV, text=True, bufsize=1,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.n = 0
        self.lines: list[str] = []

    def send_raw(self, line: str) -> dict:
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
        raw = self.proc.stdout.readline()
        self.lines.append(raw)
        try:
            return json.loads(raw)  # every stdout line must be a JSON message
        except json.JSONDecodeError:
            raise AssertionError(f"stdout line is not a JSON-RPC message: {raw!r}") from None

    def request(self, method: str, params: dict | None = None) -> dict:
        self.n += 1
        return self.send_raw(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}}))

    def call(self, name: str, arguments: dict | None = None) -> dict:
        return self.request("tools/call", {"name": name, "arguments": {} if arguments is None else arguments})

    def notify(self, method: str) -> None:
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.proc.stdin.flush()

    def close(self) -> None:
        self.proc.stdin.close()
        self.proc.wait(timeout=30)
        self.proc.stdout.close()
        self.proc.stderr.close()
