#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""VectorCraft extras.

  tools.py arrow X0 Y0 X1 Y1 [--tip to|latex|stealth] [--width 1] [--color #000] [--bend 30] [--both]
      a TikZ-style arrow (PGF's tip geometry), drawn as paths and grouped
  tools.py svgunits FILE.svg [mm|pt|in]
      give an exported SVG's root size physical units (VectorCraft writes it unitless, 1 unit = 1 pt)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from craft import Craft, CraftError, _flag, _pop  # noqa: E402


def get_data(vc: "Craft", oid: int) -> dict:
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
    raise CraftError(f"unknown tip {kind!r} (to, latex, stealth)")


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


def tikz_arrow(vc: "Craft", start, end, tip: str = "to", width: float = 1.0, color: str = "#000000",
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
        raise CraftError(f"{path}: no <svg> element")
    head = m.group(0)

    def conv(attr, h):
        mm = re.search(rf'\b{attr}="([0-9.]+)(pt|px)?"', h)
        if not mm:
            return h
        return h[: mm.start()] + f'{attr}="{float(mm.group(1)) * k:.4f}{unit}"' + h[mm.end():]

    new = conv("height", conv("width", head))
    p.write_text(s[: m.start()] + new + s[m.end():], encoding="utf-8")
    return new


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]
    if cmd == "svgunits":
        print(svg_units(args[0], args[1] if len(args) > 1 else "mm"))
    elif cmd == "arrow":
        tip = _flag(args, "--tip", "to")
        width = _flag(args, "--width", 1.0, float)
        color = _flag(args, "--color", "#000000")
        bend = _flag(args, "--bend", 0.0, float)
        both = _pop(args, "--both")
        x0, y0, x1, y1 = (float(a) for a in args)
        print(json.dumps({"id": tikz_arrow(Craft("vectorcraft"), (x0, y0), (x1, y1), tip, width, color, bend, both)}))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except CraftError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
