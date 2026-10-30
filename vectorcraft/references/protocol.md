# Control protocol (summary; full text in upstream/control-protocol.md and upstream/mcp.md)

Transport: TCP `127.0.0.1:<port>` (`--control <port>` at launch; here 12345). One JSON object per line:
`{"id": 1, "method": "...", "params": {...}}` → `{"id": 1, "ok": true, "result": ...}` or `{"ok": false, "error": "..."}`.
Not HTTP. A malformed line (no string `method`, not JSON) gets an error and the connection is **closed**:
reconnect (`vc.VC` does). At most 16 connections. An idle connection closes after 5 min. A request unanswered
after 60 s errors with `timeout: … will not run` (safe to retry) or `… still running` (check before retrying).
No authentication: the port is local only.

## Methods

| Method | Params | Notes |
|---|---|---|
| `engine.execute` | `{command, params}` | run any of ~1,190 commands (`engine.commands`). Unknown param keys are refused before running, with a "did you mean". (`command` is an accepted alias method.) |
| `engine.commands` | – | catalogue: id, label, menu, shortcut, `params` doc, enabled |
| `document.inspect` | `{depth?, childLimit?, ids?, kind?, limit?, offset?}` | artboards, layer tree (id, kind, name, bounds, fill, stroke, strokeWidth, opacity, text…), selection, key object, history |
| `ui.inspect` | – | tool, toolOptions, documents `[{title, dirty}]`, activeDocument, `ui.dialog` (open dialog kind + fields), `fileDialog`, `background` jobs, `ui.status`, canvas rect |
| `ui.menu.list` / `ui.menu.invoke` | `{command, params}` | menu tree (path, label, shortcut, command, params) / invoke an item |
| `ui.contextMenu.list` | – | right-click menu for the current selection |
| `ui.tool.list` / `ui.tool.select` | `{tool}` | toolbar groups / pick a tool |
| `ui.pointer` | `{events: [{kind: down\|drag\|up\|move\|doubleclick, x, y, space?: "doc"\|"screen", mods?}]}` | drive the active tool like the mouse (document coordinates by default) |
| `ui.key` / `ui.text` | `{key, shift?, alt?, cmd?}` / `{text}` | synthetic keyboard |
| `ui.click` / `ui.drag` / `ui.move` / `ui.wheel` | screen points | raw UI input (panels, buttons); budgets: ≤256 drag steps, ≤1,024 queued events |
| `ui.set` | `{rulers?, outline?, grid?, smartGuides?, boundingBox?, panel?, …}` | view toggles |
| `ui.dialog.set` / `.confirm` / `.cancel` | `{field, value}` or `{fields: [{field, value}]}` | fill/submit/close the open dialog (fields from `ui.inspect`) |
| `ui.screenshot` | `{path?, data?}` | window PNG (needs a visible frame: fails with the screen locked) |
| `ui.render` | `{path?, scale?, artboard?, data?}` | headless artboard PNG, white background, no UI |
| `app.open` | `{path}` | open any readable format → `{index, title, format, warnings, …}` |
| `app.save` / `app.export` / `app.quit` | `{path?…}` | host-level save/export (same options as `document.export`); quit asks about unsaved docs |

## Commands worth knowing by family (`vc.py find <family>`)

`file.*` (new, place, close, export dialogs) · `document.*` (open, save, export, exportPdf, find, node, json,
activate, setup) · `shape.*` · `path.*` (create, setAnchors, moveAnchors, join, …) · `text.*` / `type.*` ·
`paint.*` · `stroke.*` · `object.*` (move, scale, rotate, align, group, arrange, pathfinder, clippingMask,
compoundPath, blend, setProps) · `select.*` · `layer.*` · `artboard.*` · `effect.*` / `appearance.*` ·
`swatch.*` · `symbol.*` · `edit.*` (undo, redo, undoGroup.begin/end, copy, paste*, clear) · `view.*` ·
`window.panel` · `tool.options` · `ui.paramDialog` · `command.batch`.

## Dialogs (for "show me" and for options a command opens)

- Open: `tool.options {tool}` (selection → Move; rotate/scale/reflect/shear; artboard → Artboard Options),
  `ui.paramDialog {command, label?, params}` (any command), `effect.dialog {effect, index?}`, the `ui.*Dialog`
  and `ui.*Options` commands (`vc.py find dialog`).
- Read: `ui.inspect` → `ui.dialog = {kind, fields}`. Set: `ui.dialog.set`. Apply: `ui.dialog.confirm`. Abandon:
  `ui.dialog.cancel`.
- Saves/closes of modified documents open a `saveChanges` dialog (`{"pending": "saveChanges"}`):
  `ui.dialog.confirm` saves; `ui.dialog.set {field: "discard", value: true}` + confirm discards; cancel aborts.
- Anything needing a file without `path` opens a native picker for the human and returns `"cancelled"`.

## Closing a document you created (scratch work)

```python
vc.run("document.activate", {"index": i}); r = vc.run("file.close", check=False)
if isinstance(r, dict) and r.get("pending") == "saveChanges":
    vc.call("ui.dialog.set", {"field": "discard", "value": True}); vc.call("ui.dialog.confirm")
```
Only for documents you made or opened yourself, and only when nothing in them needs keeping.

## Headless alternative

`vectorcraft-cli` (separate download on macOS) offers `mcp` (an MCP server that proxies to the running app
or runs headless), `run --in x --export y`, `convert in.svg out.pdf`. Not installed here: the raw port
covers everything.
