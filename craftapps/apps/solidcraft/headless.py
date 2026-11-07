"""A headless SolidCraft session for batch work: `solidcraft-cli mcp --headless` over stdio, one reply per step,
with a time limit on each call (the kernel can spin on one command, and there is no cancel).

    import sys; sys.path.insert(0, "<skill>/apps/solidcraft"); from headless import Session, Hang
    s = Session()                                  # Session(timeout=60, allow_any_path=True)
    s.run("sketch.create", plane="XY")             # a command's reply, or {"error": text}
    s.tool("inspect_design")                       # MCP tools: execute batch measure inspect_design undo save open export new_design
    s.close()

A call over the limit kills the session and raises Hang: start a new Session and rebuild (or reopen a saved design).
Standard library only."""
import json
import queue
import subprocess
import threading
import time


class Hang(Exception):
    """A call did not answer in time (the session has been killed), or the session ended."""


class Session:
    def __init__(self, timeout=60, allow_any_path=True, cli="solidcraft-cli"):
        args = [cli, "mcp", "--headless"] + (["--allow-any-path"] if allow_any_path else [])
        self.p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  text=True, bufsize=1)
        self.timeout, self.n, self.lines = timeout, 0, queue.Queue()
        threading.Thread(target=lambda: [self.lines.put(l) for l in self.p.stdout] + [self.lines.put("")], daemon=True).start()
        self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "craftapps", "version": "1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, msg):
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()

    def rpc(self, method, params, timeout=None):
        self.n += 1
        self._send({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})
        end = time.time() + (timeout or self.timeout)
        while True:
            try:
                line = self.lines.get(timeout=max(0.05, end - time.time()))
            except queue.Empty:
                self.kill()
                raise Hang(f"no answer in {timeout or self.timeout} s: {json.dumps(params)[:300]}") from None
            if not line:
                raise Hang("the session ended")
            r = json.loads(line)
            if r.get("id") == self.n:
                return r

    def tool(self, name, timeout=None, **args):
        """The tool's JSON reply, or {"error": text}."""
        r = self.rpc("tools/call", {"name": name, "arguments": args}, timeout)
        if "error" in r:
            return {"error": str(r["error"])}
        res = r["result"]
        text = [c["text"] for c in res.get("content", []) if c.get("type") == "text"]
        if res.get("isError"):
            return {"error": " ".join(text)}
        try:
            return json.loads(text[-1])
        except (ValueError, IndexError):
            return {"text": text}

    def run(self, command, timeout=None, **params):
        """One command (`craft.py solidcraft params COMMAND` documents it)."""
        return self.tool("execute", timeout=timeout, command=command, params=params, verbose=False)

    def kill(self):
        self.p.kill()
        self.p.wait()

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            self.kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
