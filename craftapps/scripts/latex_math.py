#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Typeset LaTeX (math, chemistry, units, even small TikZ) and place it as vector art in VectorCraft or DesignCraft.

  latex_math.py 'E = mc^2' --x 40 --y 120 [--align left|center|right] [--size 12] [--font cm|sans|arial] [--color #000000] [--display]
               [--text] [--preamble '\\usepackage{mhchem}'] [--engine pdflatex|lualatex] [--name N]
  latex_math.py --replace ID 'E = mc^3'      re-typeset an object placed by this script, same spot and options
  latex_math.py --list                        objects placed by this script in the active document

Position is like text.create: (x, y) is the left end of the BASELINE, in pt (y down). The content is
math by default (wrapped in $…$; --display uses \\displaystyle); --text takes it as LaTeX text mode, so
you can pass '\\ce{H2O}', '\\SI{5}{\\micro\\litre}', or 'Rate $k_\\text{obs}$'. The size is the font
size in pt (as in the Character panel); --font sans gives Helvetica + sansmath (pairs with Arial labels);
--font arial typesets text in real Arial via lualatex (math symbols stay Latin Modern).
The result is one group of filled outlines (no font dependency), named "math: <source>", with its
source and options stored as data-latex for --replace. Needs a TeX install (pdflatex; lualatex for fontspec).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from craft import Craft, CraftError as VCError  # noqa: E402

FONTS = {
    "cm": r"\usepackage[T1]{fontenc}\usepackage{lmodern}",
    "sans": r"\usepackage[T1]{fontenc}\usepackage[scaled=1]{helvet}\renewcommand{\familydefault}{\sfdefault}"
            r"\usepackage{sansmath}\sansmath\PassOptionsToPackage{mode=text}{siunitx}",
    # real Arial for text (needs lualatex, chosen automatically); math keeps Latin Modern
    "arial": r"\usepackage{fontspec}\setmainfont{Arial}\PassOptionsToPackage{mode=text}{siunitx}",
}

TEMPLATE = r"""\documentclass[border=0pt]{standalone}
\usepackage{amsmath,amssymb,xcolor}
%(font)s
%(preamble)s
\newsavebox\vcbox
\begin{document}
\fontsize{%(size)sbp}{%(lead)sbp}\selectfont%(sansmath)s
\savebox\vcbox{\color[HTML]{%(color)s}%(body)s}%%
\typeout{VCDIM:\the\wd\vcbox,\the\ht\vcbox,\the\dp\vcbox}%%
\usebox\vcbox
\end{document}
"""


def typeset(src, size=12.0, font="cm", color="#000000", display=False, text=False, preamble="", engine="pdflatex"):
    """→ (pdf_path, width_pt, height_pt, depth_pt); pt here = PostScript points (1/72 in), as VectorCraft uses."""
    if font == "arial":
        engine = "lualatex"
    exe = shutil.which(engine)
    if not exe:
        raise VCError(f"{engine} not found: install a TeX distribution (ask the user first)")
    body = src if text else ("$\\displaystyle " + src + "$" if display else "$" + src + "$")
    tex = TEMPLATE % {
        "font": FONTS.get(font, font), "preamble": preamble, "size": size, "lead": round(size * 1.2, 2),
        "sansmath": r"\sansmath" if font == "sans" else "", "color": color.lstrip("#").upper(), "body": body,
    }
    work = Path(tempfile.mkdtemp(prefix="vc-latex-"))
    (work / "m.tex").write_text(tex)
    r = subprocess.run([exe, "-interaction=nonstopmode", "-halt-on-error", "m.tex"], cwd=work,
                       capture_output=True, text=True, timeout=120)
    log = (work / "m.log").read_text(errors="replace") if (work / "m.log").exists() else r.stdout
    m = re.search(r"VCDIM:([\d.]+)pt,([\d.]+)pt,([\d.]+)pt", log)
    if r.returncode or not m or not (work / "m.pdf").exists():
        errs = [ln for ln in log.splitlines() if ln.startswith("!") or ln.startswith("l.")]
        raise VCError("LaTeX failed:\n  " + "\n  ".join(errs[:8] or log.splitlines()[-15:]))
    k = 72 / 72.27  # TeX pt → PostScript pt
    w, h, d = (float(v) * k for v in m.groups())
    return work / "m.pdf", w, h, d


def get_data(vc, oid):
    d = (vc.run("document.node", {"id": oid}).get("attrs") or {}).get("data") or {}
    return dict(d) if isinstance(d, list) else d


def place_designcraft(vc, pdf, x, top, w):
    """A vector graphic on the page, sized from the TeX box. DesignCraft keeps the PDF live inside the frame."""
    r = vc.run("file.place", {"path": str(pdf), "x": x, "y": top, "width": w, "pdfCrop": "crop"})
    return r.get("id")


def place(vc, spec, below_id=None):
    pdf, w, h, d = typeset(spec["src"], spec["size"], spec["font"], spec["color"], spec["display"],
                           spec["text"], spec["preamble"], spec["engine"])
    x = spec["x"] - w * {"left": 0, "center": 0.5, "right": 1}[spec.get("align") or "left"]
    y = spec["y"]
    if vc.app == "designcraft":
        keep = pdf.parent.parent / f"vc-latex-{abs(hash(spec['src']))}.pdf"  # the frame links its file: keep it
        shutil.copy(pdf, keep)
        return place_designcraft(vc, keep, x, y - h, w), (w, h, d)
    cx, cy = x + w / 2, y - h + (h + d) / 2  # page = the TeX box; its baseline is h below the top
    r = vc.run("file.place", {"path": str(pdf), "link": False, "textAs": "outlines", "crop": "crop", "at": [cx, cy]})
    gid = r["ids"][0]
    name = spec.get("name") or ("math: " + spec["src"])[:80]
    vc.run("object.setProps", {"id": gid, "name": name, "data": {"latex": json.dumps(spec)}})
    if below_id is not None:
        vc.run("layer.move", {"ids": [gid], "target": below_id, "place": "above"})
    shutil.rmtree(pdf.parent, ignore_errors=True)
    return gid, (w, h, d)


def spec_of(vc, oid):
    data = get_data(vc, oid)
    if "latex" not in data:
        raise VCError(f"object {oid} wasn't placed by latex_math.py (no data-latex)")
    return json.loads(data["latex"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="?")
    ap.add_argument("--app", default="vectorcraft", help="vectorcraft (default) or designcraft")
    ap.add_argument("--x", type=float)
    ap.add_argument("--y", type=float)
    ap.add_argument("--size", type=float)
    ap.add_argument("--font")
    ap.add_argument("--color")
    ap.add_argument("--display", action="store_true", default=None)
    ap.add_argument("--text", action="store_true", default=None)
    ap.add_argument("--preamble")
    ap.add_argument("--engine")
    ap.add_argument("--name")
    ap.add_argument("--align", choices=["left", "center", "right"], help="x is the baseline's left end (default), centre or right end")
    ap.add_argument("--replace", type=int, metavar="ID")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    vc = Craft(a.app)
    if a.list:
        for m in vc.run("document.find", {"name": "math: ", "limit": 500})["matches"]:
            try:
                s = spec_of(vc, m["id"])
                print(f"#{m['id']}  {s['src']!r}  at {s['x']:.1f},{s['y']:.1f}  {s['size']}pt {s['font']}")
            except VCError:
                pass
        return
    defaults = {"x": None, "y": None, "size": 12.0, "font": "cm", "color": "#000000", "display": False,
                "text": False, "preamble": "", "engine": "pdflatex", "name": None, "align": "left"}
    if a.replace is not None:
        spec = spec_of(vc, a.replace)
    else:
        spec = dict(defaults)
    for k in defaults:
        v = getattr(a, k)
        if v is not None:
            spec[k] = v
    if a.src:
        spec["src"] = a.src
    if spec.get("src") is None or spec["x"] is None or spec["y"] is None:
        ap.error("give the LaTeX source and --x/--y (or --replace ID)")
    if a.replace is not None:
        vc.run("edit.undoGroup.begin", {"label": "Edit math"})
        try:
            gid, dims = place(vc, spec, below_id=a.replace)
            vc.run("edit.clear", {"ids": [a.replace]})
        finally:
            vc.run("edit.undoGroup.end")
    else:
        gid, dims = place(vc, spec)
    w, h, d = dims
    x0 = spec["x"] - w * {"left": 0, "center": 0.5, "right": 1}[spec.get("align") or "left"]
    print(json.dumps({"id": gid, "width": round(w, 2), "height": round(h, 2), "depth": round(d, 2),
                      "bounds": [round(x0, 2), round(spec["y"] - h, 2), round(w, 2), round(h + d, 2)]}))


if __name__ == "__main__":
    try:
        main()
    except VCError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
