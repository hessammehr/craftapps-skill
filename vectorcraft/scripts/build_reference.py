#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Regenerate the skill's generated references from the running app (and the upstream docs).

  build_reference.py [--no-docs]

Writes, next to this script's parent folder:
  references/menus.md      every menu item: path, label, shortcut, the command (and params) it runs
  references/commands.md   every command id with label, menu and shortcut (params: `vc.py params ID`)
  references/tools.md      the toolbar, flyout groups and tool shortcuts
  references/upstream/     control-protocol.md and mcp.md from github.com/storytold/vectorcraft (grep them)
Run it after VectorCraft updates (the app version is recorded at the top of each file).
"""
import datetime
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vc import VC, catalogue  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent / "references"
DOCS = "https://raw.githubusercontent.com/storytold/vectorcraft/main/docs/"


def main():
    vc = VC()
    cat = catalogue(vc, refresh=True)
    stamp = f"Generated {datetime.date.today()} from the running app by scripts/build_reference.py; regenerate after updates."
    ROOT.mkdir(exist_ok=True)

    # menus ---------------------------------------------------------------------
    lines = ["# VectorCraft menus", "", stamp, "",
             "Format: `Menu > Submenu > Item` · shortcut · `command` [params the item passes]. "
             "Shortcuts are macOS (Cmd = ⌘, Alt = ⌥ Option); on Windows/Linux Cmd is Ctrl.", ""]
    # Submenus whose items depend on the machine or recent use: one summary line each
    # (keeps recent file names and the installed font list out of the reference).
    dynamic = {("File", "Open Recent Files"): "the recently opened files (`file.openRecent1`…)",
               ("Type", "Font"): "one item per installed font family (`text.setStyle {font}`)",
               ("Type", "Recent Fonts"): "recently used fonts (`type.recentFont1`…)"}
    cur, seen_dyn = None, set()
    for m in cat["menus"]:
        key = tuple(m["path"][:2])
        if key in dynamic:
            if key not in seen_dyn:
                seen_dyn.add(key)
                lines.append(f"- {key[1]} > … · {dynamic[key]}")
            continue
        top = m["path"][0]
        if top != cur:
            lines += ["", f"## {top}", ""]
            cur = top
        p = " > ".join(m["path"][1:] + [m["label"]])
        sc = f" · **{m['shortcut']}**" if m.get("shortcut") else ""
        par = f" {json.dumps(m['params'], ensure_ascii=False)}" if m.get("params") else ""
        lines.append(f"- {p}{sc} · `{m.get('command')}`{par}")
    (ROOT / "menus.md").write_text("\n".join(lines) + "\n")

    # commands -------------------------------------------------------------------
    menus = {}
    for m in cat["menus"]:
        if m.get("command") and tuple(m["path"][:2]) not in dynamic:
            menus.setdefault(m["command"], []).append(m)
    lines = ["# VectorCraft command index", "", stamp, "",
             "Every command `engine.execute` runs. Full parameter docs: `vc.py params <id>` (or `vc.py find <words> --params`).",
             "Menu column: where a person finds it (blank: done with a tool, panel, dialog or only by automation).", "",
             "| id | label | menu | shortcut |", "|---|---|---|---|"]
    for c in sorted(cat["commands"], key=lambda c: c["id"]):
        mm = menus.get(c["id"], [])
        where = " > ".join(mm[0]["path"] + [mm[0]["label"]]) if mm else " > ".join(c.get("menu") or [])
        if len(mm) > 1:
            where += f" (+{len(mm) - 1} more)"
        sc = c.get("shortcut") or (mm[0].get("shortcut") if mm else "") or ""
        lines.append(f"| `{c['id']}` | {c.get('label') or ''} | {where} | {sc} |")
    (ROOT / "commands.md").write_text("\n".join(lines) + "\n")

    # tools ---------------------------------------------------------------------------
    lines = ["# VectorCraft tools", "", stamp, "",
             "Each group is one toolbar button; the first tool shows, the others are in its flyout "
             "(press and hold the button, or Alt-click it to cycle). Select by automation with "
             "`ui.tool.select {tool: id}`; double-clicking a button runs `tool.options {tool: id}`.", "",
             "| button | tool id | label | shortcut |", "|---|---|---|---|"]
    for i, grp in enumerate(cat["tools"], 1):
        for j, t in enumerate(grp):
            lines.append(f"| {i if j == 0 else '↳'} | `{t['id']}` | {t['label']} | {t.get('shortcut') or ''} |")
    (ROOT / "tools.md").write_text("\n".join(lines) + "\n")
    print(f"wrote menus.md ({len(cat['menus'])} items), commands.md ({len(cat['commands'])}), tools.md")

    if "--no-docs" not in sys.argv:
        up = ROOT / "upstream"
        up.mkdir(exist_ok=True)
        for name in ("control-protocol.md", "mcp.md"):
            try:
                with urllib.request.urlopen(DOCS + name, timeout=30) as r:
                    (up / name).write_bytes(r.read())
                print(f"fetched upstream/{name}")
            except OSError as e:
                print(f"could not fetch {name}: {e} (kept the old copy if any)")


if __name__ == "__main__":
    main()
