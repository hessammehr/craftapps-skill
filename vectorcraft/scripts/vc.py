#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Client for VectorCraft's JSON control channel (one JSON request per line over TCP).

CLI usage (run with `uv run vc.py ...`):

  vc.py ping                                  app + document summary
  vc.py call METHOD [JSON]                    raw control method (ui.inspect, document.inspect, ui.render, ...)
  vc.py run COMMAND [JSON]                    engine.execute one command, e.g. run shape.rectangle '{"x":0,...}'
  vc.py batch FILE|-  [--label L]             command.batch: [{"command":..,"params":..}, ...] as ONE undo step
  vc.py seq FILE|- [--label L]                like batch, but params may say "$N.id" (step N's result); one undo step
  vc.py find QUERY [--params] [--all]       search the command catalogue (id, label, menu path, shortcut)
  vc.py params COMMAND                        full parameter doc of one command
  vc.py how COMMAND|QUERY                     how a person does it by hand: menu path, shortcut, tool, panel
  vc.py tools                                 the toolbar: tool ids, labels, shortcuts, flyout groups
  vc.py tree [--depth N]                      compact outline of the active document's layers and objects
  vc.py node ID                               one object in full (document.node)
  vc.py docs                                  open documents (index, title, dirty) and the active one
  vc.py open PATH                             open a file (svg, pdf, ai, vectorcraft, ...) → its document index
  vc.py activate INDEX                        switch document tab
  vc.py render OUT.png [--artboard N] [--scale S]   headless render of an artboard (no UI chrome)
  vc.py shot OUT.png                          window screenshot (UI included)
  vc.py export PATH [JSON]                    document.export (format from the extension)
  vc.py save PATH [JSON]                      document.save (gives the document that path)
  vc.py arrow X0 Y0 X1 Y1 [--tip to|latex|stealth] [--width 1] [--color #000] [--bend 30] [--both]
                                              TikZ-style arrow (PGF tip geometry), grouped; see tikz_arrow
  vc.py svgunits FILE.svg [pt|mm|in]         give an exported SVG's root size physical units (see svg_units)
  vc.py note [--prompt] TEXT | --result PNG [caption]   narration / prompt marker / outcome image → $VC_LOG (demo videos)
  vc.py undo [N] / redo [N]

Environment: VECTORCRAFT_PORT (default 12345), VECTORCRAFT_HOST (default 127.0.0.1),
VC_LOG (optional: log every call to this JSON-lines file, for demo recordings).

Library usage:  sys.path.insert(0, "<skill>/scripts"); from vc import VC; vc = VC(); vc.run("select.all")
"""
from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

HOST = os.environ.get("VECTORCRAFT_HOST", "127.0.0.1")
PORT = int(os.environ.get("VECTORCRAFT_PORT", "12345"))
CACHE = Path(os.environ.get("TMPDIR", "/tmp")) / "vectorcraft-catalogue.json"


class VCError(RuntimeError):
    pass


def log_event(ev: dict):
    """Append a timestamped event to $VC_LOG (JSON lines), if set. Used by demo recordings for captions."""
    path = os.environ.get("VC_LOG")
    if not path:
        return
    import time

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.time(), **ev}, ensure_ascii=False) + "\n")


class VC:
    """One persistent connection; reconnects when the app drops it (idle > 5 min, error replies)."""

    def __init__(self, host: str = HOST, port: int = PORT, timeout: float = 90):
        self.host, self.port, self.timeout = host, port, timeout
        self._sock = None
        self._file = None
        self._id = 0

    # -- transport ---------------------------------------------------------
    def _connect(self):
        try:
            self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        except OSError as e:
            raise VCError(
                f"can't reach VectorCraft on {self.host}:{self.port} ({e}). Is it running with "
                f"--control {self.port}?"
            ) from None
        self._file = self._sock.makefile("rb")

    def close(self):
        if self._sock:
            self._sock.close()
        self._sock = self._file = None

    def call(self, method: str, params: dict | None = None, check: bool = True):
        """Send one request; return `result` (raise VCError on ok:false when check)."""
        if os.environ.get("VC_LOG"):
            p = params or {}
            log_event({"type": "call", "method": method, "command": p.get("command") if method == "engine.execute" else None})
        self._id += 1
        line = json.dumps({"id": self._id, "method": method, "params": params or {}}) + "\n"
        for attempt in (0, 1):
            if self._sock is None:
                self._connect()
            try:
                self._sock.sendall(line.encode())
                raw = self._file.readline()
                if not raw:
                    raise ConnectionError("connection closed")
                break
            except (ConnectionError, BrokenPipeError, socket.timeout, OSError):
                self.close()
                if attempt:
                    raise
        reply = json.loads(raw)
        if not reply.get("ok"):
            # The server closes the connection after some errors; start fresh next time.
            self.close()
            if check:
                raise VCError(f"{method}: {reply.get('error')}")
            return reply
        return reply.get("result")

    # -- conveniences --------------------------------------------------------
    def run(self, command: str, params: dict | None = None, check: bool = True):
        """engine.execute: any engine/UI command from `engine.commands`."""
        return self.call("engine.execute", {"command": command, "params": params or {}}, check)

    def batch(self, steps: list, label: str | None = None):
        """Several commands as ONE undo step; rolls everything back on the first error.
        steps: [{"command": id, "params": {...}}] or [(id, params)]."""
        cmds = [s if isinstance(s, dict) else {"command": s[0], "params": s[1] if len(s) > 1 else {}} for s in steps]
        p = {"commands": cmds}
        if label:
            p["label"] = label
        return self.run("command.batch", p)

    def seq(self, steps: list, label: str = "Script"):
        """Like batch, but a step's params may use "$N.key.0" strings for values from step N's result
        (e.g. {"id": "$0.id"}, {"ids": ["$3.id", "$4.id"]}). Runs one request per step inside an
        undo group (one undo step); on the first error the group is undone and the error re-raised.
        Returns the list of results."""
        import re

        ref = re.compile(r"^\$(\d+)((?:\.[^.]+)*)$")
        results = []

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

        depth0 = len(self.call("document.inspect", {"depth": 0}).get("history") or [])
        self.run("edit.undoGroup.begin", {"label": label})
        try:
            for i, s in enumerate(steps):
                cmd, params = (s["command"], s.get("params", {})) if isinstance(s, dict) else (s[0], s[1] if len(s) > 1 else {})
                try:
                    p = resolve(params)
                except (KeyError, IndexError, TypeError, ValueError) as e:
                    raise VCError(f"step {i} ({cmd}): bad reference {e!r}; earlier results: {results}") from None
                try:
                    results.append(self.run(cmd, p))
                except VCError as e:
                    raise VCError(f"step {i}: {e}") from None
        except Exception:
            self.run("edit.undoGroup.end")
            if len(self.call("document.inspect", {"depth": 0}).get("history") or []) > depth0:
                self.run("edit.undo")  # roll back what the earlier steps did (never an older user step)
            raise
        self.run("edit.undoGroup.end")
        return results

    def inspect(self, **kw):
        return self.call("document.inspect", kw)

    def ui(self):
        return self.call("ui.inspect")

    def render(self, path: str, artboard: int = 0, scale: float | None = None):
        p = {"path": str(Path(path).resolve()), "artboard": artboard}
        if scale:
            p["scale"] = scale
        return self.call("ui.render", p)

    def open(self, path: str):
        return self.call("app.open", {"path": str(Path(path).expanduser().resolve())})

    def rect(self, x, y, w, h, fill=None, stroke=None, weight=None, **kw):
        r = self.run("shape.rectangle", {"x": x, "y": y, "width": w, "height": h, **kw})
        self.style(r["id"], fill, stroke, weight)
        return r["id"]

    def ellipse(self, x, y, w, h, fill=None, stroke=None, weight=None):
        r = self.run("shape.ellipse", {"x": x, "y": y, "width": w, "height": h})
        self.style(r["id"], fill, stroke, weight)
        return r["id"]

    def path(self, d: str, fill=None, stroke=None, weight=None, **kw):
        r = self.run("path.create", {"d": d, **kw})
        self.style(r["id"], fill, stroke, weight)
        return r["id"]

    def text(self, x, y, s, size=None, font=None, color=None, **kw):
        p = {"x": x, "y": y, "text": s, **kw}
        if size:
            p["size"] = size
        if font:
            p["font"] = font
        if color:
            p["color"] = color
        return self.run("text.create", p)["id"]

    def style(self, oid, fill=None, stroke=None, weight=None):
        if fill is not None:
            self.run("paint.setFill", {"ids": [oid], **({"none": True} if fill == "none" else {"color": fill})})
        if stroke is not None:
            self.run("paint.setStroke", {"ids": [oid], **({"none": True} if stroke == "none" else {"color": stroke})})
        if weight is not None:
            self.run("stroke.set", {"ids": [oid], "weight": weight})


# -- catalogue (commands + menus + tools), cached for a day (--refresh after an app update) --
def catalogue(vc: VC, refresh: bool = False) -> dict:
    import time

    if CACHE.exists() and not refresh and time.time() - CACHE.stat().st_mtime < 86400:
        try:
            return json.loads(CACHE.read_text())
        except ValueError:
            pass
    cat = {
        "commands": vc.call("engine.commands"),
        "menus": vc.call("ui.menu.list"),
        "tools": vc.call("ui.tool.list"),
    }
    CACHE.write_text(json.dumps(cat))
    return cat


def _menu_index(cat):
    idx = {}
    for m in cat["menus"]:
        if m.get("command"):
            idx.setdefault(m["command"], []).append(m)
    return idx


def find(cat, query: str, show_params=False, include_all=False):
    q = query.lower().split()
    menus = _menu_index(cat)
    out = []
    for c in cat["commands"]:
        hay = " ".join([c["id"], c.get("label") or "", " ".join(c.get("menu") or []), c.get("params") or ""]).lower()
        hay_short = " ".join([c["id"], c.get("label") or "", " ".join(c.get("menu") or [])]).lower()
        if all(w in (hay if include_all else hay_short) for w in q):
            out.append(c)
    for c in out[:80]:
        mm = menus.get(c["id"], [])
        where = "; ".join(" > ".join(m["path"] + [m["label"]]) for m in mm[:2]) or " > ".join(c.get("menu") or []) or "-"
        sc = c.get("shortcut") or (mm[0].get("shortcut") if mm else "") or ""
        print(f"{c['id']:<40} {c.get('label') or '':<34} {where}  {sc}")
        if show_params:
            print("    ", c.get("params"))
    if len(out) > 80:
        print(f"... {len(out) - 80} more; narrow the query")
    if not out:
        print("no match; try --all to search parameter docs too")


def how(cat, query: str):
    """Manual instructions for a command id (or the best label match)."""
    cmds = {c["id"]: c for c in cat["commands"]}
    menus = _menu_index(cat)
    ql = query.lower()
    dynamic = (("Type", "Font"), ("Type", "Recent Fonts"), ("File", "Open Recent Files"))
    # 1. menu items whose own label matches: report the item itself (path, shortcut, what it runs)
    items = [m for m in cat["menus"] if ql in m["label"].lower() and tuple(m["path"][:2]) not in dynamic]
    # 2. commands whose id or label matches (and that no matched menu item already covers)
    hits = [query] if query in cmds else []
    if not hits:
        covered = {m["command"] for m in items}
        hits = [c["id"] for c in cat["commands"]
                if (ql in (c.get("label") or "").lower() or ql in c["id"].lower()) and c["id"] not in covered]
    tools = [t for grp in cat["tools"] for t in grp]
    thits = [t for t in tools if ql in t["id"].lower() or ql in t["label"].lower()]
    if not hits and not thits and not items:
        print("nothing matches; try `find`")
        return
    for m in items[:8]:
        par = f"   [runs {m['command']} {json.dumps(m['params'])}]" if m.get("params") else f"   [runs {m['command']}]"
        print(f"MENU  {' > '.join(m['path'] + [m['label']])}" + (f"   ({m['shortcut']})" if m.get("shortcut") else "") + par)
    for t in thits[:5]:
        grp = next(g for g in cat["tools"] if t in g)
        flyout = f" (in the flyout under {grp[0]['label']}: press and hold that button)" if grp[0] is not t else ""
        print(f"TOOL  {t['label']} [{t['id']}]  shortcut: {t.get('shortcut') or 'none'}{flyout}")
    for cid in hits[:8]:
        c = cmds.get(cid, {"id": cid})
        mm = menus.get(cid, [])
        print(f"\n{cid}  — {c.get('label') or (mm[0]['label'] if mm else '')}")
        for m in mm[:3]:
            print(f"  menu:     {' > '.join(m['path'] + [m['label']])}" + (f"   ({m['shortcut']})" if m.get("shortcut") else "")
                  + (f"   [runs with {json.dumps(m['params'])}]" if m.get("params") else ""))
        if len(mm) > 3:
            print(f"  … {len(mm) - 3} more menu items run {cid} with other params; search them with `find` or menus.md")
        if not mm and c.get("menu"):
            print(f"  menu:     {' > '.join(c['menu'])} > {c.get('label')}")
        if c.get("shortcut") and not any(m.get("shortcut") for m in mm):
            print(f"  shortcut: {c['shortcut']}")
        if not mm and not c.get("menu"):
            print("  (no menu item: done with a tool, a panel or a dialog; see the params below)")
        if c.get("params"):
            print(f"  params:   {c['params'][:600]}")


# -- tree view -----------------------------------------------------------------
def _fmt_bounds(b):
    return f"{b['x']:.1f},{b['y']:.1f} {b['width']:.1f}x{b['height']:.1f}" if b else "-"


def tree(doc: dict, max_depth: int = 99):
    for i, a in enumerate(doc.get("artboards", [])):
        print(f"artboard {i} '{a.get('name')}' at {a['x']:.1f},{a['y']:.1f} size {a['width']:.1f}x{a['height']:.1f} pt")
    sel = set(doc.get("selection") or [])

    def walk(n, d):
        if d > max_depth:
            return
        kind = n.get("kind", "Layer")
        bits = [f"#{n.get('id')}", kind, repr(n.get("name"))]
        if n.get("text") is not None:
            t = n["text"].replace("\n", "⏎")
            bits.append(repr(t[:60]))
        for k in ("fill", "stroke"):
            if n.get(k) not in (None, "None"):
                bits.append(f"{k}={n[k]}")
        if n.get("strokeWidth"):
            bits.append(f"sw={n['strokeWidth']:g}")
        if n.get("opacity", 1) < 1:
            bits.append(f"op={n['opacity']:.2f}")
        if n.get("bounds"):
            bits.append("@" + _fmt_bounds(n["bounds"]))
        if not n.get("visible", True):
            bits.append("HIDDEN")
        if n.get("locked"):
            bits.append("LOCKED")
        if n.get("id") in sel:
            bits.append("*sel*")
        kids = n.get("children") or []
        if kids and d == max_depth:
            bits.append(f"[{len(kids)} children]")
        print("  " * d + " ".join(str(b) for b in bits))
        for k in kids:
            walk(k, d + 1)

    for layer in doc.get("layers", []):
        walk(layer, 0)


def get_data(vc: "VC", oid: int) -> dict:
    """An object's own data (object.setProps data / SVG data-*), as a dict."""
    d = (vc.run("document.node", {"id": oid}).get("attrs") or {}).get("data") or {}
    return dict(d) if isinstance(d, list) else d


# -- TikZ-style arrows ----------------------------------------------------------------
# Tip geometry copied from PGF's classic arrow definitions (pgfcorearrows.code.tex: `to`, `latex`,
# `stealth`); `to` is what TikZ's `->` draws. Sizes scale with the line width lw exactly as in PGF:
# a = 0.28pt + 0.3*lw. Local tip coordinates: u along the direction of travel, v across; the shaft is
# shortened by the tip's right-extend so the tip's foremost point lands on the end point.
def _tip(kind: str, lw: float):
    a = 0.28 + 0.3 * lw
    if kind == "to":  # open, two curved barbs, stroked at 0.8 lw with round caps/joins
        segs = [("M", (-3 * a, 4 * a)), ("C", (-2.75 * a, 2.5 * a), (0, 0.25 * a), (0.75 * a, 0)),
                ("C", (0, -0.25 * a), (-2.75 * a, -2.5 * a), (-3 * a, -4 * a))]
        return segs, 0.21 + 0.625 * lw, "stroke"
    if kind == "latex":  # filled, curved sides
        segs = [("M", (9 * a, 0)), ("C", (6.3333 * a, 0.5 * a), (2 * a, 2 * a), (-a, 3.75 * a)),
                ("L", (-a, -3.75 * a)), ("C", (2 * a, -2 * a), (6.3333 * a, -0.5 * a), (9 * a, 0)), ("Z",)]
        return segs, 9 * a, "fill"
    if kind == "stealth":  # filled, swept-back kite
        segs = [("M", (5 * a, 0)), ("L", (-3 * a, 4 * a)), ("L", (0, 0)), ("L", (-3 * a, -4 * a)), ("Z",)]
        return segs, 5 * a, "fill"
    raise VCError(f"unknown tip {kind!r} (to, latex, stealth)")


def _tip_d(kind, lw, end, direction):
    import math

    segs, ext, mode = _tip(kind, lw)
    ux, uy = direction
    n = math.hypot(ux, uy)
    ux, uy = ux / n, uy / n
    ox, oy = end[0] - ext * ux, end[1] - ext * uy  # tip origin = shortened shaft end
    tr = lambda p: f"{ox + p[0] * ux - p[1] * uy:.3f} {oy + p[0] * uy + p[1] * ux:.3f}"
    d = " ".join(s[0] + (" " + " ".join(tr(p) for p in s[1:]) if len(s) > 1 else "") for s in segs)
    return d, (ox, oy), mode


def tikz_arrow(vc: "VC", start, end, tip: str = "to", width: float = 1.0, color: str = "#000000",
               bend: float = 0.0, both: bool = False, name: str | None = None) -> int:
    """Draw a TikZ-style arrow from `start` to `end` (pt, y down) and return the group id.
    tip: to (TikZ `->`), latex (`-latex`), stealth (`-stealth`). width: line width in pt (TikZ default
    0.4). bend: degrees, like TikZ `bend left=θ` (negative = bend right). both: tips at both ends (`<->`).
    The parameters are stored on the group (`data-tikz`) so it can be found and redrawn later."""
    import math

    (x0, y0), (x3, y3) = start, end
    L = math.hypot(x3 - x0, y3 - y0)
    th = math.atan2(y3 - y0, x3 - x0)
    # TikZ `bend left` turns the start direction by -θ in screen space (y down); control distance 0.3915 L
    b = math.radians(-bend)
    c1 = (x0 + 0.3915 * L * math.cos(th + b), y0 + 0.3915 * L * math.sin(th + b))
    c2 = (x3 - 0.3915 * L * math.cos(th - b), y3 - 0.3915 * L * math.sin(th - b))
    d_end = (x3 - c2[0], y3 - c2[1]) if bend else (x3 - x0, y3 - y0)
    d_start = (x0 - c1[0], y0 - c1[1]) if bend else (x0 - x3, y0 - y3)
    head, (sx3, sy3), mode = _tip_d(tip, width, end, d_end)
    ids = []
    if both:
        tail, (sx0, sy0), _ = _tip_d(tip, width, start, d_start)
    else:
        sx0, sy0 = x0, y0
    # shorten the shaft: move the end point (and its control point) by the same offset
    if bend:
        dx3, dy3 = sx3 - x3, sy3 - y3
        dx0, dy0 = sx0 - x0, sy0 - y0
        shaft = (f"M{sx0:.3f} {sy0:.3f} C{c1[0] + dx0:.3f} {c1[1] + dy0:.3f} "
                 f"{c2[0] + dx3:.3f} {c2[1] + dy3:.3f} {sx3:.3f} {sy3:.3f}")
    else:
        shaft = f"M{sx0:.3f} {sy0:.3f} L{sx3:.3f} {sy3:.3f}"
    steps = [("path.create", {"d": shaft}), ("paint.setFill", {"none": True}),
             ("paint.setStroke", {"color": color}), ("stroke.set", {"weight": width, "cap": "butt"})]
    heads = [head] + ([tail] if both else [])
    for hd in heads:
        steps.append(("path.create", {"d": hd}))
        if mode == "stroke":
            steps += [("paint.setFill", {"none": True}), ("paint.setStroke", {"color": color}),
                      ("stroke.set", {"weight": 0.8 * width, "cap": "round", "join": "round"})]
        else:
            steps += [("paint.setFill", {"color": color}), ("paint.setStroke", {"none": True})]
    res = vc.seq(steps, label=f"TikZ arrow ({tip})")
    ids = [r["id"] for r in res if isinstance(r, dict) and "id" in r and len(r) == 1]
    spec = {"start": list(start), "end": list(end), "tip": tip, "width": width, "color": color,
            "bend": bend, "both": both}
    g = vc.run("object.group", {"ids": ids})["id"]
    vc.run("object.setProps", {"id": g, "name": name or f"arrow ({'<' if both else ''}-{tip})",
                               "data": {"tikz": json.dumps(spec)}})
    return g


# -- SVG physical size -------------------------------------------------------------
def svg_units(path: str, unit: str = "pt") -> str:
    """VectorCraft writes the root width/height unitless with 1 unit = 1 pt (as Illustrator does).
    Browsers and Inkscape read unitless as px (1/96 in), so the figure comes out at 75 % size.
    Rewrite the root size in `unit` (pt, mm, in) so its physical size survives; the viewBox is kept."""
    import re

    k = {"pt": 1.0, "mm": 25.4 / 72, "in": 1 / 72}[unit]
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    m = re.search(r"<svg\b[^>]*>", s)
    if not m:
        raise VCError(f"{path}: no <svg> element")
    head = m.group(0)

    def conv(attr, h):
        mm = re.search(rf'\b{attr}="([0-9.]+)(pt|px)?"', h)
        if not mm:
            return h
        return h[: mm.start()] + f'{attr}="{float(mm.group(1)) * k:.4f}{unit}"' + h[mm.end():]

    new = conv("height", conv("width", head))
    p.write_text(s[: m.start()] + new + s[m.end():], encoding="utf-8")
    return new


# -- CLI -------------------------------------------------------------------------
def _json_arg(args, i, default=None):
    if len(args) > i:
        a = args[i]
        if a == "-":
            return json.load(sys.stdin)
        if a.startswith("@"):
            return json.loads(Path(a[1:]).read_text())
        return json.loads(a)
    return default if default is not None else {}


def _flag(args, name, default=None, cast=str):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i : i + 2]
        return cast(v)
    return default


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return
    vc = VC()
    cmd, args = argv[0], argv[1:]
    pr = lambda r: print(json.dumps(r, indent=1, ensure_ascii=False))
    if cmd == "ping":
        u = vc.ui()
        print("tool:", u["tool"], "| active document:", u["activeDocument"])
        for i, d in enumerate(u["documents"]):
            print(f"  [{i}] {d['title']}{' (unsaved changes)' if d['dirty'] else ''}")
    elif cmd == "call":
        pr(vc.call(args[0], _json_arg(args, 1)))
    elif cmd == "run":
        pr(vc.run(args[0], _json_arg(args, 1)))
    elif cmd == "batch":
        label = _flag(args, "--label")
        steps = _json_arg(args, 0)
        pr(vc.batch(steps, label))
    elif cmd == "seq":
        label = _flag(args, "--label", "Script")
        pr(vc.seq(_json_arg(args, 0), label))
    elif cmd in ("find", "params", "how", "tools"):
        refresh = "--refresh" in args
        args = [a for a in args if a != "--refresh"]
        cat = catalogue(vc, refresh)
        if cmd == "find":
            sp, al = "--params" in args, "--all" in args
            find(cat, " ".join(a for a in args if not a.startswith("--")), sp, al)
        elif cmd == "params":
            c = next((c for c in cat["commands"] if c["id"] == args[0]), None)
            print(c["params"] if c else f"no command {args[0]}; try `find`")
        elif cmd == "how":
            how(cat, " ".join(args))
        else:
            for grp in cat["tools"]:
                head, rest = grp[0], grp[1:]
                print(f"{head['id']:<22} {head['label']:<30} {head.get('shortcut') or ''}")
                for t in rest:
                    print(f"   └ {t['id']:<18} {t['label']:<30} {t.get('shortcut') or ''}")
    elif cmd == "tree":
        depth = _flag(args, "--depth", 99, int)
        tree(vc.inspect(), depth)
    elif cmd == "node":
        pr(vc.run("document.node", {"id": int(args[0])}))
    elif cmd == "docs":
        u = vc.ui()
        for i, d in enumerate(u["documents"]):
            print(f"{'*' if i == u['activeDocument'] else ' '}[{i}] {d['title']}{' (unsaved)' if d['dirty'] else ''}")
    elif cmd == "open":
        pr(vc.open(args[0]))
    elif cmd == "activate":
        pr(vc.run("document.activate", {"index": int(args[0])}))
    elif cmd == "render":
        ab = _flag(args, "--artboard", 0, int)
        sc = _flag(args, "--scale", None, float)
        pr(vc.render(args[0], ab, sc))
    elif cmd == "shot":
        pr(vc.call("ui.screenshot", {"path": str(Path(args[0]).resolve())}))
    elif cmd == "export":
        pr(vc.run("document.export", {"path": str(Path(args[0]).resolve()), **_json_arg(args, 1)}))
    elif cmd == "save":
        pr(vc.run("document.save", {"path": str(Path(args[0]).resolve()), **_json_arg(args, 1)}))
    elif cmd == "arrow":
        tip = _flag(args, "--tip", "to")
        width = _flag(args, "--width", 1.0, float)
        color = _flag(args, "--color", "#000000")
        bend = _flag(args, "--bend", 0.0, float)
        both = "--both" in args
        x0, y0, x1, y1 = (float(a) for a in args if a != "--both")
        print(json.dumps({"id": tikz_arrow(vc, (x0, y0), (x1, y1), tip, width, color, bend, both)}))
    elif cmd == "svgunits":
        print(svg_units(args[0], args[1] if len(args) > 1 else "pt"))
    elif cmd == "note":
        if "--result" in args:  # vc.py note --result PATH [caption…]: an image to show as the outcome
            rest = [a for a in args if a != "--result"]
            log_event({"type": "result", "path": str(Path(rest[0]).resolve()), "caption": " ".join(rest[1:])})
        else:
            kind = "prompt" if "--prompt" in args else "note"
            log_event({"type": kind, "text": " ".join(a for a in args if a != "--prompt")})
    elif cmd in ("undo", "redo"):
        for _ in range(int(args[0]) if args else 1):
            vc.run(f"edit.{cmd}")
        print("ok")
    else:
        print(f"unknown subcommand {cmd}\n{__doc__}")
        sys.exit(2)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except VCError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
