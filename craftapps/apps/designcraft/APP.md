# DesignCraft

Page layout in the style of InDesign: spreads, parent pages, threaded text frames, paragraph and character styles, tables, books, data merge. Reads IDML and INDD,
writes `.designcraft`, IDML, PDF (including PDF/X) and EPUB. Use InDesign's vocabulary with the person. Read `SKILL.md` first; this file is what is specific to DesignCraft.

- **Port:** only with `--control`, so `craft.py designcraft launch`; no token. If it's running without a port, it has to be saved, quit and relaunched: ask.
- **Grouping:** steps one by one, one undo entry each. `script.run {text}` takes a JSON array of `{command, params}` (or `command.id {json}` lines) with `$N.path` references, and refuses the whole script before running if a command or parameter is wrong.
- **Surface:** `craft.py designcraft families`. Sweep: 734 commands, 501 run or refuse with a stated reason on a scratch page, 233 skipped for outside effects, none hung.
- **Upstream agent guide:** `craft.py designcraft docs` fetches `agents.md`, worth reading for data merge, books and alternates.

## How a document works

**Items** live on spreads, positioned by spread coordinates in points, y down: `rect: [x0, y0, x1, y1]`. Frames hold **stories**; threading makes one story flow through several frames.
`craft.py designcraft tree` lists spreads, items and stories. Style text through **paragraph and character styles**, not one-off formatting, so the person can change the whole document at once.

Keep watching `overset` on stories (text that doesn't fit): `document.inspect` → `stories[].overset`. Check it after every text change.

Default A4 documents have **facing pages**, so a spread can hold two pages. Item coordinates are relative to the spread.

## Whole-task recipe (tested)

```python
c = Craft("designcraft")
c.run("file.new", {"preset": "A4"})
title = c.run("frame.create", {"rect": [40, 60, 555, 110], "content": "text"})     # → {id, story}
c.run("story.setText", {"story": title["story"], "text": "A title"})
c.run("style.paragraph.create", {"name": "Title", "chars": {"fontFamily": "Arial", "fontStyle": "Bold", "size": 22}, "para": {"spaceAfter": 6}})
c.run("text.placeCaret", {"frame": title["id"]}); c.run("style.paragraph.apply", {"name": "Title"})   # styles act on the text selection or caret
c.run("file.place", {"path": "/abs/fig.png", "spread": 0, "x": 40, "y": 130, "width": 250})           # PNG, PDF and SVG tested; vector stays vector
a = c.run("frame.create", {"rect": [40, 340, 290, 780], "content": "text"})
b = c.run("frame.create", {"rect": [305, 340, 555, 780], "content": "text"})
t = c.run("text.thread", {"from": a["id"], "to": b["id"]})                         # the stories merge: use t["story"] from here
c.run("story.setText", {"story": t["story"], "text": "Long body text…"})
c.run("style.paragraph.create", {"name": "Body", "chars": {"fontFamily": "Arial", "size": 10, "leading": {"kind": "points", "value": 13}}, "para": {"align": "fullyJustified"}})
c.run("text.placeCaret", {"frame": a["id"]}); c.run("style.paragraph.apply", {"name": "Body"})
c.run("layout.pages.insert", {})
frame = c.run("frame.create", {"spread": 1, "rect": [40, 60, 555, 300], "content": "text"})
c.run("text.placeCaret", {"frame": frame["id"]})
c.run("table.insert", {"rows": 3, "columns": 3, "headerRows": 1, "width": 515})    # at the text caret
c.save("/abs/layout.designcraft"); c.export("/abs/layout.pdf"); c.render("/abs/p1.png", page=0, scale=1.3)
```

**Math:** `uv run <skill>/scripts/latex_math.py '\frac{a}{b}' --app designcraft --font sans --size 14 --x 40 --y 220` places LaTeX as a vector graphic on a baseline.
**From VectorCraft:** export PDF or SVG and `file.place` them (tested), or `ui.paste {text: svg}` for editable paths (needs a visible window).

## Driving the GUI

```bash
craft.py designcraft call ui.tool.select '{"tool": "rectangleFrame"}'             # tools: craft.py designcraft tools
craft.py designcraft call ui.pointer '{"events": [{"kind": "down", "x": 100, "y": 100}, {"kind": "drag", "x": 300, "y": 240}, {"kind": "up", "x": 300, "y": 240}]}'
craft.py designcraft call ui.menu.invoke '{"command": "object.textFrameOptions"}' # no params: opens the dialog if the item has one
craft.py designcraft call ui.dialog.open '{"id": "paragraphStyleOptions", "fields": {"name": "Body", "section": "Basic Character Formats"}}'
craft.py designcraft dialog set '{"field": "value"}'; craft.py designcraft dialog ok
craft.py designcraft call ui.set '{"zoom": 1, "page": 0, "fit": "page"}'          # also rulers, guides, frameEdges, baselineGrid
```

Pointer and key input is queued across frames. After a drag, wait for the document state, and for `canUndo` before testing undo. `ui.key` doesn't reach native-menu shortcuts like Cmd+Z on macOS; use `ui.menu.invoke` or `edit.undo`. `ui.text` types into a text frame; `ui.ime` sends input-method events.

## Command families

| Family | What |
|---|---|
| `app` (74) | what menus and dialogs run: open, save, export, place, links, swatch and style loading |
| `object` (60), `transform` (10) | arrange, group, lock, fill, stroke, opacity, effects, `textFrameOptions`; move, scale, rotate, step and repeat |
| `frame`, `path` (15), `select` (8) | frames, Bézier paths, selection in stacks and groups |
| `type` (43), `text` (17), `story` (9), `style` (28) | character and paragraph attributes, caret and selection, threading, whole-story text, styles, CJK features |
| `table` (41) | insert, convert, rows, columns, merge, cell text and graphics, sort |
| `layout` (28), `guide` (10), `layer` (9) | pages, parents, margins and columns, alternates, liquid layout; guides; layers |
| `swatch` (13), `color` (11), `ink` | swatches, colour settings, separations |
| `book` (10), `data` (10), `xml` (10), `note` (9), `library` (8), `links` (7) | books, data merge, tagged content, notes, libraries, placed links |
| `file` (37) | new, open, save, place, export (`exportPdf`, `exportIdml`, `exportEpub`), recovery |
| `view` (47), `window` (47), `edit` (19) | view and panels; undo, paste into, step and repeat |

Control methods: grep `craft.py designcraft docs` for `| \`ui.`.

## Headless

```bash
designcraft-cli run --cmd 'file.new={"preset":"A4"}' --cmd 'frame.create={"rect":[40,40,300,200],"content":"text"}' --export out.pdf   # tested
designcraft-cli script job.json --in in.designcraft --save out.designcraft --export out.pdf
designcraft-cli commands FILTER; designcraft-cli describe COMMAND; designcraft-cli validate-pdf out.pdf --standard x4
designcraft-cli app --port P COMMAND JSON      # send one command to a running app
```

In `/Applications/DesignCraft.app/Contents/MacOS/` on macOS.

## Teaching fundamentals

Pages panel for pages and parents, Layers and Properties on the right; as in InDesign. Teach first: place on parent pages what repeats; thread frames rather than splitting stories; style with paragraph styles; red overset markers mean the text doesn't fit. `craft.py designcraft how WORDS` gives any menu path.

## Pitfalls

- **Threading merges stories:** the second frame's story id stops existing. Use the id `text.thread` returns.
- **`style.paragraph.apply` takes only a name** and acts on the current text selection or caret: place the caret first. `text.selectStory` needs a frame and a point.
- **`style.paragraph.create` takes `chars` and `para` objects,** and `align` values are InDesign's: `fullyJustified`, `leftJustified`, not `justify`.
- **`leading` is `{"kind": "points", "value": 13}`** or `{"kind": "auto"}`, not a number.
- **`table.insert` works at the text caret,** so it needs a text frame with the caret placed.
- **`ui.render` pages are 0-based; `file.exportPdf` page ranges are 1-based.**
- **`app.quit` over the channel doesn't ask about unsaved changes,** unlike the menu's. Use it only for instances you started, after saving.
- **Placed files stay linked:** keep them where they are, or `links.embed`. `latex_math.py` keeps its PDFs in the temporary folder, so embed them for a document you're keeping.
