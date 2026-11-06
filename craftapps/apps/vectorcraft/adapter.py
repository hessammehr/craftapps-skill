"""VectorCraft: state, file operations and the document outline for craft.py."""


def inspect(c, **kw):
    return c.call("document.inspect", kw)


def state(c):
    u = c.call("ui.inspect")
    docs = u.get("documents") or []
    active = u.get("activeDocument")
    out = {"document": None, "dirty": None, "documents": [d["title"] for d in docs], "tool": u.get("tool"),
           "selection": [], "dialog": (u.get("ui") or {}).get("dialog") and u["ui"]["dialog"].get("kind"),
           "busy": u.get("background") or None, "revision": None}
    if u.get("fileDialog"):
        out["dialog"] = f"file dialog: {u['fileDialog']}"
    if active is not None and docs:
        d = c.call("document.inspect", {"depth": 0})
        out.update(document=docs[active]["title"], dirty=docs[active]["dirty"], selection=d.get("selection") or [],
                   revision=len(d.get("history") or []))
    return out


def history_len(c):
    return len(c.call("document.inspect", {"depth": 0}).get("history") or [])


def open(c, path):  # noqa: A001
    r = c.call("app.open", {"path": path})
    if r and "index" in r:
        c.run("document.activate", {"index": r["index"]})
    return r


def save(c, path, **kw):
    return c.run("document.save", {"path": path, **kw})


def export(c, path, **kw):
    return c.run("document.export", {"path": path, **kw})


def render(c, path, scale=None, page=None):
    p = {"path": path}
    if scale:
        p["scale"] = scale
    if page is not None:
        p["artboard"] = page
    return c.call("ui.render", p)


def tree(c, max_depth=99):
    doc = c.call("document.inspect")
    for i, a in enumerate(doc.get("artboards", [])):
        print(f"artboard {i} '{a.get('name')}' at {a['x']:.1f},{a['y']:.1f} size {a['width']:.1f}x{a['height']:.1f} pt")
    sel = set(doc.get("selection") or [])

    def walk(n, d):
        if d > max_depth:
            return
        bits = [f"#{n.get('id')}", n.get("kind", "Layer"), repr(n.get("name"))]
        if n.get("text") is not None:
            bits.append(repr(n["text"].replace("\n", "⏎")[:60]))
        for k in ("fill", "stroke"):
            if n.get(k) not in (None, "None"):
                bits.append(f"{k}={n[k]}")
        if n.get("strokeWidth"):
            bits.append(f"sw={n['strokeWidth']:g}")
        if n.get("opacity", 1) < 1:
            bits.append(f"op={n['opacity']:.2f}")
        if n.get("bounds"):
            b = n["bounds"]
            bits.append(f"@{b['x']:.1f},{b['y']:.1f} {b['width']:.1f}x{b['height']:.1f}")
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


def dialog_info(c):
    return (c.call("ui.inspect").get("ui") or {}).get("dialog")


def dialog_set(c, fields):
    return c.call("ui.dialog.set", {"fields": [{"field": k, "value": v} for k, v in fields.items()]})


def dialog_ok(c):
    return c.call("ui.dialog.confirm")


def dialog_cancel(c):
    return c.call("ui.dialog.cancel")
