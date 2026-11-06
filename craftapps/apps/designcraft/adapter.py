"""DesignCraft: state, file operations and the page outline for craft.py."""


def inspect(c, **kw):
    return c.call("document.inspect", kw)


def state(c):
    u = c.call("ui.inspect")
    docs = u.get("documents") or []
    active = u.get("activeDocument")
    out = {"document": None, "dirty": None, "documents": [d["title"] for d in docs], "tool": u.get("tool"), "selection": [],
           "dialog": (u["dialog"].get("kind") or u["dialog"].get("id") or "open") if isinstance(u.get("dialog"), dict) else u.get("dialog"),
           "busy": None, "revision": None, "page": u.get("currentPage")}
    if active is not None and docs:
        d = c.call("document.inspect")
        sel = d.get("selection") or {}
        out.update(document=docs[active]["title"], dirty=docs[active]["dirty"], selection=sel.get("items") or [])
    return out


def history_len(c):
    return 0  # DesignCraft reports only canUndo, not a depth


def open(c, path):  # noqa: A001
    return c.call("app.open", {"path": path})


def save(c, path, **kw):
    return c.run("file.saveAs", {"path": path, **kw})


def export(c, path, **kw):
    if path.lower().endswith(".pdf"):
        return c.run("file.exportPdf", {"path": path, **kw})
    return c.call("app.export", {"path": path, **kw})


def render(c, path, scale=None, page=None):
    p = {"path": path}
    if scale:
        p["scale"] = scale
    if page is not None:
        p["page"] = page
    return c.call("ui.render", p)


def tree(c, max_depth=99):
    d = c.call("document.inspect")
    s = d.get("settings") or {}
    print(f"{d.get('title')}: {d.get('pageCount')} page(s) {s.get('pageWidth', 0):.1f}x{s.get('pageHeight', 0):.1f} pt, "
          f"facing={s.get('facingPages')}, layers: {[x['name'] for x in d.get('layers', [])]}")
    print("para styles:", d.get("paragraphStyles"), " char styles:", d.get("characterStyles"))
    for sp in d.get("spreads", []):
        print(f"spread {sp.get('index')}: pages {[p.get('index', p.get('number')) for p in sp.get('pages', [])]}")
        for it in sp.get("items", []) if max_depth > 0 else []:
            print("  ", {k: it[k] for k in it if k in ("id", "kind", "content", "name", "rect", "bounds", "story", "fill", "stroke", "layer")})
    for st in d.get("stories", []) if max_depth > 0 else []:
        t = str(st.get("text", ""))
        print(f"story #{st.get('id')}: {t[:70]!r} overset={st.get('overset')}")


def dialog_info(c):
    return c.call("ui.inspect").get("dialog")


def dialog_set(c, fields):
    return [c.call("ui.dialog.set", {"field": k, "value": v}) for k, v in fields.items()]


def dialog_ok(c):
    return c.call("ui.dialog.confirm")


def dialog_cancel(c):
    return c.call("ui.dialog.cancel")
