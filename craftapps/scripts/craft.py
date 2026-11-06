#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""One client for the Craft apps' JSON control channels. Each app is described by apps/<app>/app.json,
with optional app-specific logic in apps/<app>/adapter.py.

  craft.py apps                              every known app: installed? running? port?
  craft.py APP status                        document, dirty, tool, selection, dialog, busy: what the person sees now
  craft.py APP launch [--isolated] [--port P] [--roots DIR]... [FILE]   start the app with its control channel
  craft.py APP wait [--timeout S] [--on selection|document|dialog|tool|revision]
                                             block until the person changes something; prints what changed
  craft.py APP watch [--interval S]          print one line per state change until stopped
  craft.py APP run COMMAND [JSON] [--force]  run one command (refused while a dialog is open or the app is busy)
  craft.py APP batch FILE|-|JSON [--label L] [--force]   several commands, atomically where the app can
  craft.py APP seq FILE|-|JSON [--label L] [--force]     steps run one by one; params may say "$N.id" (step N's result)
  craft.py APP call METHOD [JSON]            any raw control method (no checks)
  craft.py APP find WORDS [--params] [--all] search the live command catalogue
  craft.py APP params COMMAND                full parameter doc of a command
  craft.py APP how WORDS                     how a person does it: menu path, ribbon location, tool, shortcut
  craft.py APP families                      commands per family, to see the app's whole surface
  craft.py APP tools                         the toolbar's tools, where the app lists them
  craft.py APP tree [--depth N]              compact outline of the active document
  craft.py APP open PATH | save PATH | export PATH [JSON]
  craft.py APP render OUT.png [--scale S] [--page N] | shot OUT.png | undo [N] | redo [N]
  craft.py APP dialog [set JSON | ok | cancel]   read or answer the open dialog, whichever way this app does it
  craft.py APP front                         bring its window forward (a covered window draws no frames, so GUI input waits)
  craft.py APP docs                          download the app's upstream docs; prints the local paths to grep
  craft.py note [--prompt] TEXT | --result PNG [caption]    add to $CRAFT_LOG (recordings and coverage)

Environment: <APP>_CONTROL_PORT overrides the port; CRAFT_LOG logs every call to a JSON-lines file.
Library use: sys.path.insert(0, "<skill>/scripts"); from craft import Craft; c = Craft("photocraft"); c.run("edit.undo")
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPS = ROOT / "apps"
CACHE = Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")).expanduser() / "craftapps"
PLATFORM = "win32" if sys.platform.startswith("win") else "darwin" if sys.platform == "darwin" else "linux"


class CraftError(RuntimeError):
    pass


def log_event(ev: dict):
    path = os.environ.get("CRAFT_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.time(), **ev}, ensure_ascii=False) + "\n")


def known_apps() -> list[str]:
    return sorted(p.parent.name for p in APPS.glob("*/app.json"))


def manifest(app: str) -> dict:
    p = APPS / app.lower() / "app.json"
    if not p.exists():
        raise CraftError(f"unknown app {app!r}; known: {', '.join(known_apps())} (see references/adding-an-app.md)")
    return json.loads(p.read_text())


def _path(s: str | None) -> str | None:
    return os.path.expandvars(os.path.expanduser(s)) if s else None


def _processes() -> list[tuple[int, str]]:
    try:
        if PLATFORM == "win32":
            out = subprocess.run(["powershell", "-NoProfile", "-c",
                                  "Get-CimInstance Win32_Process | ForEach-Object { \"$($_.ProcessId) $($_.CommandLine)\" }"],
                                 capture_output=True, text=True, timeout=20).stdout
        else:
            out = subprocess.run(["ps", "-axww", "-o", "pid=,args="], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    rows = []
    for line in out.splitlines():
        pid, _, args = line.strip().partition(" ")
        if pid.isdigit():
            rows.append((int(pid), args))
    return rows


def find_process(m: dict) -> dict | None:
    """The running app, with the port and token file on its command line, if any."""
    binary = _path(m["binary"].get(PLATFORM)) or m["id"]
    base = os.path.basename(binary).lower()
    for pid, args in _processes():
        a = args.replace("\\", "/")
        if a.startswith(binary.replace("\\", "/")) or a.lower().split(" ")[0].rsplit("/", 1)[-1] == base:
            port = re.search(r"--control[= ](\d+)", args)
            tok = re.search(r"--control-token-file[= ](\S+)", args)
            return {"pid": pid, "port": int(port.group(1)) if port else None, "token_file": tok.group(1) if tok else None}
    return None


def _listening(port: int, host="127.0.0.1") -> bool:
    try:
        socket.create_connection((host, port), timeout=1).close()
        return True
    except OSError:
        return False


class Craft:
    """One persistent connection; it re-authenticates and reconnects when the app drops it."""

    def __init__(self, app: str, port: int | None = None, host: str = "127.0.0.1", timeout: float = 120, token_file: str | None = None):
        self.m = manifest(app)
        self.app = self.m["id"]
        self.host, self.timeout, self._token_file = host, timeout, token_file
        self.port = port
        self._sock = self._file = None
        self._id = 0
        self._adapter = None

    # -- finding the app ---------------------------------------------------------
    def _resolve_port(self) -> int:
        env = os.environ.get(self.m["port"]["env"])
        proc = find_process(self.m)
        if proc and proc["token_file"]:
            self._token_file = self._token_file or proc["token_file"]
        if self.port or env:
            return self.port or int(env)
        if proc and proc["port"]:
            return proc["port"]
        auth = self.m.get("auth", {})
        if auth.get("port_file"):
            pf = Path(_path(auth["token_dir"][PLATFORM])) / auth["port_file"]
            if pf.exists() and pf.read_text().strip().isdigit():
                return int(pf.read_text().strip())
        return self.m["port"]["default"]

    def _token(self) -> str | None:
        auth = self.m.get("auth", {})
        if auth.get("kind") == "none":
            return None
        if auth.get("env") and os.environ.get(auth["env"]):
            return os.environ[auth["env"]]
        if auth["kind"] == "token_field":
            p = Path(_path(auth["token_dir"][PLATFORM])) / f"{self.port}.token"
        else:
            p = Path(self._token_file) if self._token_file else CACHE / f"{self.app}.token"
        if not p.exists():
            raise CraftError(f"{self.m['name']}: no control token at {p}. Start it with `craft.py {self.app} launch`.")
        return p.read_text().strip()

    def _connect(self):
        self.port = self._resolve_port()
        try:
            self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        except OSError as e:
            proc = find_process(self.m)
            hint = (f"It is running (pid {proc['pid']}) without a control port: ask the person to save their work, "
                    f"then quit it and run `craft.py {self.app} launch`." if proc else f"Start it with `craft.py {self.app} launch`.")
            raise CraftError(f"can't reach {self.m['name']} on port {self.port} ({e}). {hint}") from None
        self._file = self._sock.makefile("rb")
        self._authed = False
        if self.m.get("auth", {}).get("kind") == "auth_request":
            self._exchange({"id": "auth", "method": "auth", "params": {"token": self._token()}}, check=True)
            self._authed = True

    def close(self):
        if self._sock:
            self._sock.close()
        self._sock = self._file = None

    def _exchange(self, req: dict, check=False) -> dict:
        self._sock.sendall((json.dumps(req) + "\n").encode())
        while True:
            raw = self._file.readline()
            if not raw:
                raise ConnectionError("connection closed")
            reply = json.loads(raw)
            if "event" not in reply:  # subscribed event lines have no id
                break
        if check and not reply.get("ok"):
            raise CraftError(f"{req['method']}: {reply.get('error')}")
        return reply

    # -- calling -----------------------------------------------------------------------
    def call(self, method: str, params: dict | None = None, check: bool = True):
        """Send one control request and return its result (CraftError on ok:false when check)."""
        p = params or {}
        log_event({"type": "call", "app": self.app, "method": method,
                   "command": p.get("command") if method == "engine.execute" else None,
                   "commands": [s.get("command") if isinstance(s, dict) else s[0] for s in p.get(self.m.get("batch", {}).get("steps_key", "commands"), [])
                                ] if "batch" in method else None})
        self._id += 1
        for attempt in (0, 1):
            try:
                if self._sock is None:
                    self._connect()
                req = {"id": self._id, "method": method, "params": p}
                if self.m.get("auth", {}).get("kind") == "token_field" and not self._authed:
                    req["token"] = self._token()
                reply = self._exchange(req)
                self._authed = True
                break
            except (ConnectionError, BrokenPipeError, socket.timeout, OSError):
                self.close()
                if attempt:
                    raise CraftError(f"{self.m['name']} stopped answering during {method}") from None
        if not reply.get("ok"):
            err = str(reply.get("error"))
            if "closing the connection" in err:
                self.close()
            if check:
                raise CraftError(f"{method}: {err}")
            return reply
        return reply.get("result")

    def run(self, command: str, params: dict | None = None, check: bool = True):
        return self.call("engine.execute", {"command": command, "params": params or {}}, check)

    @property
    def adapter(self):
        if self._adapter is None:
            p = APPS / self.app / "adapter.py"
            spec = importlib.util.spec_from_file_location(f"craft_adapter_{self.app}", p)
            self._adapter = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self._adapter)
        return self._adapter

    def state(self) -> dict:
        """{document, dirty, documents, tool, selection, dialog, busy, revision} as the person sees them now."""
        return self.adapter.state(self)

    def inspect(self, **kw) -> dict:
        return self.adapter.inspect(self, **kw)

    def preflight(self, force=False):
        """Refuse to act under the person's hands: an open dialog, a running job, or a loading file."""
        if force:
            return
        s = self.state()
        if s.get("dialog"):
            raise CraftError(f"{self.m['name']} has a dialog open ({s['dialog']}): the person may be using it. "
                             "Check with them, or close it with ui.dialog.cancel; --force skips this check.")
        if s.get("busy"):
            raise CraftError(f"{self.m['name']} is busy ({s['busy']}): wait for it, or use --force.")

    @staticmethod
    def _steps(steps) -> list[tuple[str, dict]]:
        return [(s["command"], s.get("params") or {}) if isinstance(s, dict) else (s[0], s[1] if len(s) > 1 else {}) for s in steps]

    def batch(self, steps: list, label: str | None = None):
        """Several commands in one go, atomic and one undo step where the app supports it (see its APP.md)."""
        b = self.m.get("batch")
        norm = self._steps(steps)
        if not b:
            return self.seq(norm, label or "Script")
        body = {b["steps_key"]: [{"command": c, "params": p} for c, p in norm]}
        if label and b.get("label_key"):
            body[b["label_key"]] = label
        res = self.call(b["method"], body) if b.get("method") else self.run(b["command"], body)
        if isinstance(res, dict) and res.get("failed"):
            raise CraftError(f"batch failed: {json.dumps(res['failed'])[:500]}")
        return res

    @contextmanager
    def undo_group(self, label: str = "Script"):
        """Group edits into one undo step, where the app has undo groups; otherwise each edit is its own step."""
        g = self.m.get("undo_group")
        if g:
            self.run(g["begin"], {"label": label})
        try:
            yield self
        finally:
            if g:
                self.run(g["end"])

    def seq(self, steps: list, label: str = "Script") -> list:
        """Steps one by one; params may say "$N.key.0" for a value in step N's result. In an undo group where
        the app has one. On error, what this call did is undone where history can tell, and the error re-raised."""
        ref = re.compile(r"^\$(\d+)((?:\.[^.]+)*)$")
        results: list = []

        def resolve(v):
            if isinstance(v, str) and (m := ref.match(v)):
                cur = results[int(m.group(1))]
                for k in filter(None, m.group(2).split(".")):
                    cur = cur[int(k)] if isinstance(cur, list) else cur[k]
                return cur
            if isinstance(v, list):
                return [resolve(x) for x in v]
            if isinstance(v, dict):
                return {k: resolve(x) for k, x in v.items()}
            return v

        h0 = self.adapter.history_len(self)
        grouped = bool(self.m.get("undo_group"))
        try:
            with self.undo_group(label):
                for i, (cmd, params) in enumerate(self._steps(steps)):
                    try:
                        p = resolve(params)
                    except (KeyError, IndexError, TypeError, ValueError) as e:
                        raise CraftError(f"step {i} ({cmd}): bad reference {e!r}; earlier results: {results}") from None
                    try:
                        results.append(self.run(cmd, p))
                    except CraftError as e:
                        raise CraftError(f"step {i}: {e}") from None
        except Exception:
            done = self.adapter.history_len(self) - h0
            for _ in range(max(0, 1 if grouped and done > 0 else done)):
                self.run("edit.undo")
            raise
        return results

    # -- files, pictures -----------------------------------------------------------
    def open(self, path: str):
        return self.adapter.open(self, str(Path(path).expanduser().resolve()))

    def save(self, path: str, **kw):
        return self.adapter.save(self, str(Path(path).expanduser().resolve()), **kw)

    def export(self, path: str, **kw):
        return self.adapter.export(self, str(Path(path).expanduser().resolve()), **kw)

    def render(self, path: str, **kw):
        return self.adapter.render(self, str(Path(path).expanduser().resolve()), **kw)

    def shot(self, path: str):
        return self.call("ui.screenshot", {"path": str(Path(path).expanduser().resolve()), **self.m.get("screenshot_params", {})})


# -- the catalogue: read from the running app, cached per build ---------------------------------
def _flatten_menus(items, path=()):
    """Menus as a flat list of {path, label, command, params, shortcut}, whichever shape the app reports."""
    out = []
    for it in items or []:
        if isinstance(it, list):  # DesignCraft: ["File", ["cmd:file.close", ">Open Recent", …, "<", "-", …]]
            stack = [it[0]]
            for e in it[1]:
                if e == "<":
                    stack.pop()
                elif e.startswith(">"):
                    stack.append(e[1:])
                elif ":" in e:
                    out.append({"path": list(stack), "label": "", "command": e.split(":", 1)[1], "params": None, "shortcut": ""})
            continue
        label = it.get("label") or it.get("title") or it.get("name") or ""
        p = list(it.get("path") or path)
        cmd = it.get("command") or it.get("id")
        kids = it.get("items") or it.get("children") or it.get("submenu")
        if kids:
            out += _flatten_menus(kids, tuple(p) + (label,))
        elif cmd or label:
            out.append({"path": p, "label": label, "command": cmd, "params": it.get("params"), "shortcut": it.get("shortcut") or ""})
    return out


def catalogue(c: Craft, refresh=False) -> dict:
    binary = _path(c.m["binary"].get(PLATFORM)) or ""
    stamp = str(int(os.path.getmtime(binary))) if binary and os.path.exists(binary) else time.strftime("%Y%m%d")
    f = CACHE / f"{c.app}-{stamp}.json"
    if f.exists() and not refresh:
        return json.loads(f.read_text())
    cat = {"commands": c.call("engine.commands"), "menus": [], "tools": []}
    for key, method in (("menus", "ui.menu.list"), ("tools", "ui.tool.list")):
        r = c.call(method, check=False)
        if isinstance(r, list):
            cat[key] = _flatten_menus(r) if key == "menus" else r
    labels = {x["id"]: x for x in cat["commands"]}
    for m in cat["menus"]:  # menus that name only the command take its label and shortcut
        if not m["label"] and m["command"] in labels:
            m["label"], m["shortcut"] = labels[m["command"]].get("label") or "", labels[m["command"]].get("shortcut") or ""
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(cat))
    return cat


def _where(cmd: dict, menus: list) -> str:
    mm = [m for m in menus if m.get("command") == cmd["id"]]
    if mm:
        return " > ".join(mm[0]["path"] + [mm[0]["label"]]) + (f" (+{len(mm) - 1})" if len(mm) > 1 else "")
    if cmd.get("tab") or cmd.get("panel"):
        return "ribbon: " + " > ".join(x for x in (cmd.get("tab"), cmd.get("panel")) if x)
    return " > ".join(cmd.get("menu") or []) or "-"


def cmd_find(cat, words, show_params=False, everywhere=False):
    q = [w.lower() for w in words]
    hits = []
    for c in cat["commands"]:
        base = [c["id"], c.get("label") or "", " ".join(c.get("menu") or []), c.get("tab") or "", c.get("panel") or "", " ".join(c.get("keywords") or [])]
        hay = " ".join(base + ([c.get("params") or ""] if everywhere else [])).lower()
        if all(w in hay for w in q):
            hits.append(c)
    for c in hits[:80]:
        print(f"{c['id']:<40} {(c.get('label') or '')[:34]:<34} {_where(c, cat['menus'])}  {c.get('shortcut') or ''}")
        if show_params:
            print("    ", c.get("params"))
    if len(hits) > 80:
        print(f"... {len(hits) - 80} more; narrow the query")
    if not hits:
        print("no match; try --all to search parameter docs too")


def cmd_how(cat, query):
    ql = query.lower()
    cmds = {c["id"]: c for c in cat["commands"]}
    noisy = {"font", "recent fonts", "open recent files", "open recent"}
    items = [m for m in cat["menus"] if ql in (m["label"] or "").lower() and not (set(p.lower() for p in m["path"]) & noisy)]
    covered = {m["command"] for m in items}
    hits = [query] if query in cmds else [c["id"] for c in cat["commands"] if (ql in (c.get("label") or "").lower() or ql in c["id"].lower()) and c["id"] not in covered]
    tools = []
    for grp in cat["tools"]:
        for t in grp if isinstance(grp, list) else grp.get("tools", [grp]):
            if ql in str(t.get("id", "")).lower() or ql in str(t.get("label", "")).lower():
                tools.append((t, grp))
    if not (items or hits or tools):
        print("nothing matches; try `find`")
    for m in items[:8]:
        print(f"MENU  {' > '.join(m['path'] + [m['label']])}" + (f"   ({m['shortcut']})" if m.get("shortcut") else "")
              + f"   [runs {m['command']}" + (f" {json.dumps(m['params'])}" if m.get("params") else "") + "]")
    for t, grp in tools[:5]:
        first = grp[0] if isinstance(grp, list) else t
        fly = f" (in the flyout under {first.get('label')}: press and hold it)" if first is not t else ""
        print(f"TOOL  {t.get('label')} [{t.get('id')}]  shortcut: {t.get('shortcut') or 'none'}{fly}")
    for cid in hits[:8]:
        c = cmds.get(cid, {"id": cid})
        print(f"\n{cid}  — {c.get('label') or ''}")
        print(f"  where:    {_where(c, cat['menus'])}" + (f"   ({c['shortcut']})" if c.get("shortcut") else ""))
        if c.get("params"):
            print(f"  params:   {c['params'][:600]}")


def cmd_docs(c: Craft):
    import urllib.request

    d = CACHE / "docs" / c.app
    d.mkdir(parents=True, exist_ok=True)
    for url in c.m.get("docs", []):
        f = d / url.rsplit("/", 1)[1]
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                f.write_bytes(r.read())
        except OSError as e:
            print(f"could not fetch {url}: {e}" + (" (keeping the old copy)" if f.exists() else ""), file=sys.stderr)
        if f.exists():
            print(f)


# -- launching ---------------------------------------------------------------------------------
def launch(c: Craft, isolated=False, port=None, file=None, roots=None) -> dict:
    m = c.m
    proc = find_process(m)
    if proc and not isolated:
        port_now = proc["port"] or (c._resolve_port() if m.get("auth", {}).get("port_file") else None)
        if port_now and _listening(port_now):
            c.port = port_now
            return {"already_running": True, "pid": proc["pid"], "port": port_now}
        raise CraftError(f"{m['name']} is already running (pid {proc['pid']}) without a control port, and a running app "
                         "ignores new arguments. Ask the person to save their work and quit it, then launch again.")
    binary = _path(m["binary"].get(PLATFORM))
    if not binary:
        raise CraftError(f"no known path for {m['name']} on {PLATFORM}")
    port = port or m["port"]["default"]
    if isolated and port == m["port"]["default"]:
        port += 100
    args = [binary, "--control", str(port)]
    env = dict(os.environ)
    info: dict = {"port": port}
    if isolated:
        prof = tempfile.mkdtemp(prefix=f"craft-{m['id']}-profile-")
        env[m["profile_env"]] = prof
        info["profile"] = prof
    if m.get("auth", {}).get("token_file_flag"):
        CACHE.mkdir(parents=True, exist_ok=True)
        tf = Path(tempfile.mkdtemp(prefix="craft-token-")) / "control.token" if isolated else CACHE / f"{m['id']}.token"
        args += [m["auth"]["token_file_flag"], str(tf)]
        c._token_file = str(tf)
        info["token_file"] = str(tf)
    if m.get("roots"):  # the app refuses every path over the channel outside these folders
        chosen = roots or [str(Path.home())]
        for r in chosen:
            args += [m["roots"]["read_flag"], str(Path(r).expanduser().resolve()), m["roots"]["write_flag"], str(Path(r).expanduser().resolve())]
        info["roots"] = chosen
    if file:
        args.append(str(Path(file).expanduser().resolve()))
    CACHE.mkdir(parents=True, exist_ok=True)
    log = open(CACHE / f"{m['id']}-launch.log", "a")
    p = subprocess.Popen(args, env=env, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    info["pid"] = p.pid
    c.port = port
    for _ in range(120):
        if _listening(port):
            for _ in range(30):
                try:
                    c.call("ui.inspect")
                    return info
                except CraftError:
                    time.sleep(0.5)
        if p.poll() is not None:
            raise CraftError(f"{m['name']} exited at start (code {p.returncode}); see {log.name}")
        time.sleep(0.5)
    raise CraftError(f"{m['name']} didn't open port {port} within a minute; see {log.name}")


def bring_to_front(c: Craft):
    """A covered or minimised window draws no frames: screenshots fail and GUI input queues. Takes focus, so ask first."""
    if c.call("ui.focus", check=False) is None or PLATFORM != "darwin":
        pass
    if PLATFORM == "darwin":
        proc = find_process(c.m)
        if proc:
            subprocess.run(["osascript", "-e", f'tell application "System Events" to set frontmost of (first process whose unix id is {proc["pid"]}) to true'],
                           capture_output=True, timeout=10)
    return {"front": True}


# -- following the person ------------------------------------------------------------------------
def _diff(a: dict, b: dict, on=None) -> dict:
    keys = [on] if on else [k for k in b if k != "busy"]
    return {k: {"from": a.get(k), "to": b.get(k)} for k in keys if a.get(k) != b.get(k)}


def cmd_wait(c: Craft, timeout=300.0, on=None, interval=0.4):
    """Block until the state changes (the person acted, or a job ended)."""
    start = c.state()
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(interval)
        now = c.state()
        d = _diff(start, now, on)
        if d:
            print(json.dumps({"changed": d, "state": now}, ensure_ascii=False))
            return 0
    print(json.dumps({"changed": None, "timeout": timeout, "state": start}, ensure_ascii=False))
    return 3


def cmd_watch(c: Craft, interval=0.5):
    prev = c.state()
    print(json.dumps(prev, ensure_ascii=False), flush=True)
    while True:
        time.sleep(interval)
        now = c.state()
        d = _diff(prev, now)
        if d:
            print(time.strftime("%H:%M:%S"), json.dumps(d, ensure_ascii=False), flush=True)
            prev = now


# -- CLI ---------------------------------------------------------------------------------------------
def _json_arg(args, i, default=None):
    if len(args) > i:
        a = args[i]
        if a == "-":
            return json.load(sys.stdin)
        if a.startswith("@"):
            return json.loads(Path(a[1:]).read_text())
        if not a.lstrip().startswith(("{", "[")) and Path(a).exists():
            return json.loads(Path(a).read_text())
        return json.loads(a)
    return {} if default is None else default


def _flag(args, name, default=None, cast=str):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i: i + 2]
        return cast(v)
    return default


def _pop(args, name) -> bool:
    if name in args:
        args.remove(name)
        return True
    return False


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    pr = lambda r: print(json.dumps(r, indent=1, ensure_ascii=False))
    if argv[0] == "note":
        a = argv[1:]
        if _pop(a, "--result"):
            log_event({"type": "result", "path": str(Path(a[0]).resolve()), "caption": " ".join(a[1:])})
        else:
            log_event({"type": "prompt" if _pop(a, "--prompt") else "note", "text": " ".join(a)})
        return 0
    if argv[0] == "apps":
        for app in known_apps():
            m = manifest(app)
            b = _path(m["binary"].get(PLATFORM)) or ""
            proc = find_process(m)
            print(f"{m['name']:<14} {m['kind']:<40} installed={'yes' if os.path.exists(b) or not os.path.isabs(b) else 'no':<4}"
                  f" running={'pid ' + str(proc['pid']) if proc else 'no'} port={proc['port'] if proc else '-'}")
        return 0
    app, cmd, args = argv[0], (argv[1] if len(argv) > 1 else "status"), argv[2:]
    c = Craft(app, port=_flag(args, "--port", None, int))
    if cmd == "status":
        pr({"app": c.m["name"], "port": c._resolve_port(), **c.state()})
    elif cmd == "launch":
        iso, roots = _pop(args, "--isolated"), []
        while "--roots" in args:
            roots.append(_flag(args, "--roots"))
        pr(launch(c, iso, c.port, args[0] if args else None, roots or None))
    elif cmd == "wait":
        return cmd_wait(c, _flag(args, "--timeout", 300.0, float), _flag(args, "--on"))
    elif cmd == "watch":
        cmd_watch(c, _flag(args, "--interval", 0.5, float))
    elif cmd == "call":
        pr(c.call(args[0], _json_arg(args, 1)))
    elif cmd == "run":
        c.preflight(_pop(args, "--force"))
        pr(c.run(args[0], _json_arg(args, 1)))
    elif cmd in ("batch", "seq"):
        force, label = _pop(args, "--force"), _flag(args, "--label", "Script")
        c.preflight(force)
        pr(getattr(c, cmd)(_json_arg(args, 0), label))
    elif cmd in ("find", "params", "how", "families", "tools"):
        refresh, sp, al = _pop(args, "--refresh"), _pop(args, "--params"), _pop(args, "--all")
        cat = catalogue(c, refresh)
        if cmd == "find":
            cmd_find(cat, args, sp, al)
        elif cmd == "how":
            cmd_how(cat, " ".join(args))
        elif cmd == "params":
            hit = next((x for x in cat["commands"] if x["id"] == args[0]), None)
            print(hit["params"] if hit else f"no command {args[0]}; try `find`")
        elif cmd == "families":
            fam: dict = {}
            for x in cat["commands"]:
                fam.setdefault(x["id"].split(".")[0], []).append(x["id"])
            for k, v in sorted(fam.items(), key=lambda kv: -len(kv[1])):
                print(f"{len(v):>4}  {k}")
            print(f"{len(cat['commands']):>4}  total")
        else:
            pr(cat["tools"]) if cat["tools"] else print(f"{c.m['name']} has no tool list; see its APP.md")
    elif cmd == "tree":
        c.adapter.tree(c, _flag(args, "--depth", 99, int))
    elif cmd == "open":
        pr(c.open(args[0]))
    elif cmd in ("save", "export"):
        pr(getattr(c, cmd)(args[0], **_json_arg(args, 1)))
    elif cmd == "render":
        kw = {k: v for k, v in (("scale", _flag(args, "--scale", None, float)), ("page", _flag(args, "--page", None, int))) if v is not None}
        pr(c.render(args[0], **kw))
    elif cmd == "shot":
        pr(c.shot(args[0]))
    elif cmd in ("undo", "redo"):
        for _ in range(int(args[0]) if args else 1):
            c.run(f"edit.{cmd}")
        print("ok")
    elif cmd == "front":
        pr(bring_to_front(c))
    elif cmd == "dialog":
        sub = args[0] if args else "show"
        a = c.adapter
        pr({"show": lambda: a.dialog_info(c), "set": lambda: a.dialog_set(c, _json_arg(args, 1)),
            "ok": lambda: a.dialog_ok(c), "cancel": lambda: a.dialog_cancel(c)}[sub]())
    elif cmd == "docs":
        cmd_docs(c)
    else:
        print(f"unknown subcommand {cmd}\n{__doc__}")
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except CraftError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
