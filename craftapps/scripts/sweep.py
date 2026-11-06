#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Send every command of an app's catalogue to a scratch document in an ISOLATED instance and classify the replies.

  sweep.py APP OUT.json [--port P] [--token-file F]

Run it against `craft.py APP launch --isolated` only: it really runs the commands. Commands with effects outside the
document (quit, files, browser, preferences, windows) are skipped. Use it after an app update or when adding an app, to
see what is reachable and whether refusals explain themselves. Classes: ok, asks_params (refused, naming what it needs),
needs_context (refused: needs a selection, a tool, an object), opened_dialog, other_error, timeout, skipped.
"""
import collections
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from craft import Craft, CraftError  # noqa: E402

SKIP = re.compile(r"quit|exit|close|crash|^help\.|discord|website|github|update|print|reveal|send_to|easyprint|slicer|install|plugin"
                  r"|^prefs|^settings|shortcut|workspace|recover|^script\.|^file\.|^doc\.|^app\.|import|export|load|save|open|place|relink"
                  r"|^ui\.|^window\.|^diagnostics|^engine\.|agent|language|purge|^links\.|^library\.|^book\.|render\.|^data\.|droplet|automate|^actions\.|^addon\.|folder")
PARAMS = re.compile(r"missing|must |invalid param|required|expected|needs? a|give |unknown param|is not a|not a valid", re.I)
CONTEXT = re.compile(r"not available|no selection|nothing selected|select |no document|no active|requires|while |no such|not found|no object|no layer|there is no|isn't|none |empty|only ", re.I)
SEEDS = {
    "vectorcraft": [("file.new", {"width": 400, "height": 300, "units": "Points"}), ("shape.rectangle", {"x": 40, "y": 40, "width": 100, "height": 80})],
    "photocraft": [("file.new", {"width": 400, "height": 300, "name": "sweep"}), ("select.rect", {"x": 50, "y": 50, "width": 100, "height": 80})],
    "designcraft": [("file.new", {"preset": "A4"}), ("frame.create", {"rect": [40, 40, 300, 300], "content": "text"})],
    "solidcraft": [("file.new", {}), ("sketch.create", {"plane": "XY"}), ("sketch.rectangle.two_point", {"p0": [0, 0], "p1": [40, 30]}), ("sketch.finish", {}), ("solid.extrude", {"distance": 20})],
}


def main():
    a = sys.argv[1:]
    app, out = a[0], a[1]
    port = int(a[a.index("--port") + 1]) if "--port" in a else None
    tf = a[a.index("--token-file") + 1] if "--token-file" in a else None
    c = Craft(app, port=port, timeout=45, token_file=tf)
    cmds = c.call("engine.commands")

    def seed():
        for cmd, p in SEEDS[app]:
            c.run(cmd, p, check=False)

    seed()
    res, fails = {}, 0
    for i, x in enumerate(cmds):
        cid = x["id"]
        if SKIP.search(cid):
            res[cid] = {"class": "skipped"}
            continue
        if i % 40 == 0 and not c.state().get("document"):
            seed()
        t0 = time.time()
        try:
            r = c.run(cid, {}, check=False)
            fails = 0
        except CraftError as e:
            res[cid] = {"class": "timeout", "error": str(e)[:200]}
            fails += 1
            if fails >= 3:
                print("stopping: the app stopped answering", file=sys.stderr)
                break
            continue
        err = r.get("error") if isinstance(r, dict) and r.get("ok") is False else None
        kind = "ok" if err is None else "asks_params" if PARAMS.search(err) else "needs_context" if CONTEXT.search(err) else "other_error"
        res[cid] = {"class": kind, "ms": int((time.time() - t0) * 1000), **({"error": err[:240]} if err else {})}
        try:
            if c.state().get("dialog"):
                res[cid]["class"] = "opened_dialog"
                c.adapter.dialog_cancel(c)
        except (CraftError, RuntimeError):
            pass
    Path(out).write_text(json.dumps(res, indent=0))
    cnt = collections.Counter(v["class"] for v in res.values())
    print(app, dict(cnt), "of", len(cmds), "documented params:", sum(bool(x.get("params")) for x in cmds))


if __name__ == "__main__":
    main()
