"""PhotoCraft: state, file operations and the layer outline for craft.py."""


def inspect(c, **kw):
    return c.run("document.inspect", kw)


def state(c):
    u = c.call("ui.inspect")
    s = u.get("session") or {}
    docs = s.get("documents") or []
    d = u.get("document") or {}
    jobs = u.get("jobs") or {}
    busy = [k for k in ("running", "opening", "saving") if jobs.get(k)]
    dialogs = u.get("dialogs") or []
    modal = [k for k, v in (u.get("distort") or {}).items() if v]
    if u.get("textEdit"):
        modal.append("typing text")
    return {"document": d.get("name"), "dirty": next((x["dirty"] for x in docs if x.get("name") == d.get("name")), None),
            "documents": [x.get("name") for x in docs], "tool": u.get("tool"),
            "selection": {"layers": d.get("selectedLayers") or [], "pixels": d.get("selectionBounds")},
            "dialog": ([x.get("id") or x.get("kind") for x in dialogs] + modal) or None,
            "busy": busy or None, "revision": d.get("revision")}


def history_len(c):
    return len((c.call("ui.inspect").get("document") or {}).get("history") or [])


def open(c, path):  # noqa: A001
    return c.call("app.open", {"path": path})


def save(c, path, **kw):
    return c.call("app.save", {"path": path, **kw})


def export(c, path, **kw):
    """A flattened copy in the format of the extension; the document keeps its own path (app.save warns what it lost).
    file.saveACopy is disabled over the control channel."""
    return c.call("app.save", {"path": path, **kw})


def render(c, path, scale=None, page=None):
    """PhotoCraft has no ui.render: a flattened PNG copy shows the composite and leaves the document as it is."""
    return c.call("app.save", {"path": path})


def activate(c, index):
    return c.run("document.activate", {"document": index})


def tree(c, max_depth=99):
    d = c.call("ui.inspect").get("document") or {}
    if not d:
        print("no document")
        return
    print(f"{d.get('name')} {d.get('width')}x{d.get('height')} px {d.get('mode')} {d.get('depth')}-bit, "
          f"{d.get('resolution')} ppi; selection: {d.get('selectionBounds')}; active layer #{d.get('activeLayer')}")
    print("history:", " > ".join(map(str, (d.get("history") or [])[-6:])))

    def walk(n, depth):
        if depth > max_depth:
            return
        bits = [f"#{n.get('id')}", n.get("kind"), repr(n.get("name"))]
        if n.get("blend") not in (None, "Normal"):
            bits.append(n["blend"])
        if n.get("opacity", 1) < 1:
            bits.append(f"op={n['opacity']:.2f}")
        if n.get("bounds"):
            bits.append("@" + ",".join(f"{v:g}" for v in n["bounds"]))
        for k, lab in (("hasMask", "MASK"), ("hasVectorMask", "VMASK"), ("clipped", "CLIPPED")):
            if n.get(k):
                bits.append(lab)
        if not n.get("visible", True):
            bits.append("HIDDEN")
        if n.get("selected"):
            bits.append("*sel*")
        print("  " * depth + " ".join(str(b) for b in bits))
        for k in n.get("children") or []:
            walk(k, depth + 1)

    for layer in d.get("layers") or []:
        walk(layer, 0)


def _dialog_id(c):
    d = c.call("ui.inspect").get("dialogs") or []
    return d[-1]["id"] if d else None


def dialog_info(c):
    d = c.call("ui.inspect").get("dialogs") or []
    return d[-1] if d else None


def dialog_set(c, fields):
    i = _dialog_id(c)
    return [c.call("ui.dialog.set", {"dialog": i, "field": k, "value": v}) for k, v in fields.items()]


def dialog_ok(c):
    return c.call("ui.dialog.confirm", {"dialog": _dialog_id(c)})


def dialog_cancel(c):
    return c.call("ui.dialog.cancel", {"dialog": _dialog_id(c)})
