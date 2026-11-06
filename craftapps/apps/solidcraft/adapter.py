"""SolidCraft: state, file operations and the design outline for craft.py."""


def inspect(c, **kw):
    return c.call("document.inspect", kw)


def state(c):
    u = c.call("ui.inspect")
    d = c.call("document.inspect")
    sel = c.call("ui.selection")
    busy = [k for k, v in (("file", u.get("file_busy")), ("file picker", u.get("file_picker_busy")),
                           ("preview", (u.get("preview") or {}).get("busy")), ("render", (u.get("render") or {}).get("active"))) if v]
    rev = c.call("document.revision")
    return {"document": d.get("name"), "dirty": d.get("dirty"), "documents": u.get("documents"), "tool": u.get("tool"),
            "selection": sel.get("selection") or [], "dialog": sel.get("dialog") or u.get("dialog"),
            "busy": busy or None, "revision": rev.get("revision"), "active_sketch": d.get("active_sketch")}


def history_len(c):
    return c.call("document.inspect").get("undo", 0)


def open(c, path):  # noqa: A001
    return c.call("ui.file", {"path": path})  # a background open: poll status until not busy


def save(c, path, **kw):
    return c.run("file.save_as", {"path": path, **kw})


def export(c, path, **kw):
    return c.run("file.export", {"path": path, **kw})


def render(c, path, scale=None, page=None):
    return c.call("ui.render", {"path": path})


def activate(c, index):
    return c.call("ui.documents", {"action": "switch", "index": index})


def tree(c, max_depth=99):
    d = c.call("document.inspect")
    print(f"{d.get('name')} [{d.get('units')}] revision {d.get('revision')}, undo {d.get('undo')}, dirty={d.get('dirty')}")
    for p in d.get("params", []):
        print(f"param {p.get('name')} = {p.get('expression', p.get('value'))}")
    for s in d.get("sketches", []):
        print(f"sketch #{s.get('id')} {s.get('name')!r}", {k: s[k] for k in s if k in ("plane", "profiles", "fully_constrained", "dof")})
    for i, f in enumerate(d.get("timeline", [])):
        print(f"feature {i}: {f.get('name') or f.get('id')} {f.get('kind', f.get('type', ''))} {'ERROR: ' + str(f['error']) if f.get('error') else ''}")
    for b in d.get("bodies", []):
        print(f"body {b.get('name')!r}", {k: b[k] for k in b if k in ("id", "volume", "bbox", "faces", "edges")})


def dialog_info(c):
    """The open command dialog: title, inputs, what it is waiting for. Controls are named handles (craft.py APP handles)."""
    return c.call("ui.inspect").get("dialog")


def press(c, handle):
    """Click a named control as a person would: toolbar:<command>, dialog:ok, dialog:Distance… (the window must be visible)."""
    hs = {h["name"]: h for h in c.call("ui.handles")}
    if handle not in hs:
        raise RuntimeError(f"no handle {handle!r}; near: {[n for n in hs if handle.split(':')[0] in n][:30]}")
    return c.call("ui.click", {"x": hs[handle]["x"], "y": hs[handle]["y"]})


def dialog_set(c, fields):
    """Click each named field, replace its text, confirm with Tab."""
    import time

    for k, v in fields.items():
        press(c, f"dialog:{k}")
        time.sleep(0.2)
        c.call("ui.key", {"key": "A", "cmd": True})
        c.call("ui.text", {"text": str(v)})
        c.call("ui.key", {"key": "Tab"})
        time.sleep(0.2)


def dialog_ok(c):
    return press(c, "dialog:ok")


def dialog_cancel(c):
    return press(c, "dialog:cancel")
