# VectorCraft

Vector editor with Illustrator's layout, tools, menus, panels and shortcuts; reads and writes SVG, PDF, `.ai`, EPS,
DXF and `.vectorcraft`. Use Illustrator's vocabulary with the person. Read `SKILL.md` first; this file is what is specific to VectorCraft.

- **Port:** `--control 12345` by default; no token. Started without the flag, it has no port (needs a relaunch).
- **Grouping:** `command.batch` is atomic and one undo step; `edit.undoGroup.begin/end` groups anything, with Python logic between.
- **More here:** `recipes.md` (tested snippets), `manual-howto.md` (task → tool/menu for teaching), `protocol.md` (methods),
  `tools.py` (TikZ arrows, SVG units). Worked reasoning: the workflows below.
- **Surface:** `craft.py vectorcraft families`. Sweep: 1,337 commands, 902 run or refuse with a stated reason on a scratch document, 435 skipped for outside effects, none hung.

## The model in five facts

1. **Coordinates** are points (1/72 in), **y down**, origin at the first artboard's top-left. Inkscape mm
   files open at their true size (1 mm = 2.83465 pt), so `tree` bounds are pt.
2. **Objects have integer ids** (`craft.py vectorcraft tree`). Ids are stable within a session and change on reopen. Find
   things by content, not remembered ids: `document.find {text|name|kind|within|intersects|minArea…}`.
   Kinds: imported art is mostly `Path`/`Group`/`Type`. Live shapes you draw stay `Rectangle`, `Ellipse`,
   `Line`, `Star`… (filter `kind` accordingly).
3. **Commands act on `ids`/`id` when given, else on the selection**, and new objects become the selection.
   So inside a batch a `paint.setFill` without ids styles the object just created.
4. **New art inherits the current paint** (the last fill/stroke you set), type included. Give every new
   object its paint explicitly: `text.create {…, color}`, or `paint.setFill`/`paint.setStroke` right after it.
   (Tested: "?" labels came out in the box colour and vanished.)
5. **`text.create` y is the baseline** of the first line. For Arial the top of the type bounds is
   `y − 0.905·size`. Multi-line text uses `\n`. `justify: "center"` centres each line on x. Leading defaults
   to auto (120 %): set it with `text.setStyle {leading}` to match a design.

## Doing work: batch vs seq vs single calls

- `craft.py vectorcraft run <command> '<json>'` runs one command (one undo step each).
- `craft.py vectorcraft batch steps.json --label "…"` uses **`command.batch`**: atomic, one undo step, everything rolled
  back if any step fails. Steps can't reference ids created earlier in the same batch, so chain through the
  selection, or use `seq`.
- `craft.py vectorcraft seq steps.json --label "…"` runs steps one by one inside an undo group, so **`"$N.id"` references to
  earlier results work** (`{"id": "$0.id"}`, `{"ids": ["$2.id"]}`). On error it undoes what it did (and only
  that).
- Python: `from craft import Craft; vc = Craft("vectorcraft"); vc.run(...); vc.batch([...]); vc.seq([...])`, plus helpers
  `vc.rect/ellipse/path/text/style` (VectorCraft's adapter). For logic between steps (find → decide → edit), wrap the calls in
  `edit.undoGroup.begin {label}` / `edit.undoGroup.end` (in `try/finally`) to keep one undo step.

## Workflows

### A. Create a figure from scratch
1. Settle size and units first (journal column ≈ 85 mm = 241 pt, double ≈ 178 mm = 505 pt):
   `file.new {title, width, height, units: "Millimeters"|"Points", artboards?, artboardLayout?}`, then activate
   the returned index.
2. Structure: name the default layer (`layer.setProps {name}`) and add layers back-to-front
   (`layer.new {name, top: true}`). Group each panel (`object.group`) and name groups (`object.setProps`).
3. Build with `batch`/`seq` using the recipes. Prefer **one compound path** for repeated marks (ticks,
   grids) via `path.create {d: "M…V… M…V…"}`. For arrows, use Stroke-panel arrowheads
   (`stroke.set {endArrow}`, live and editable) or TikZ-style ones (“Typeset math and TikZ-style arrows”) when the figure should look like LaTeX.
   For equations, use `latex_math.py` (“Typeset math and TikZ-style arrows”), not hand-built sub/superscripts.
4. Render, look, fix, re-render. Then export (“Saving and exporting”).

### B. Amend an existing figure
1. `craft.py vectorcraft open <copy or original>`. Opening doesn't modify the file, but never Save it afterwards.
2. `craft.py vectorcraft tree` (add `--depth 2` for big files) to map the request to objects: text by content, shapes by
   colour/bounds. `craft.py vectorcraft node <id>` gives full detail (font, size, leading, anchors, transform).
3. Apply the change as one batch/seq. Typical tools: `text.setText`, `text.setStyle`, `object.move`, `edit.clear`,
   `select.anchors` + `path.moveAnchors` (moving one edge of a frame), `paint.*`, `stroke.set`,
   `layer.move {ids, target, place: "below"}` (stacking relative to an object), `artboard.setProps`.
4. Render and compare with the "before" render (`compare.py before.png after.png --out diff.png`). Only the
   intended regions should change.
5. Save under a new name (“Saving and exporting”).

### C. Go from one revision to the next (vN → vN+1)
When a target revision exists (or the user describes one):
1. Open both. Render both at the same scale (`--scale 2`). `craft.py vectorcraft tree` both and diff the outlines: objects
   added, removed, moved (bounds), restyled (fill/stroke/size), text changed, artboard resized.
2. Write the change list in plain words first (it's also what you'd tell a person doing it by hand).
3. Apply it to vN in one undo group, **drawing** new content from the recipes, not copying it from vN+1,
   unless the user wants the quick route (copy/paste between documents: `edit.copy`, `document.activate`,
   `edit.pasteInPlace`).
4. Verify: `compare.py yours.png target.png --pt-scale 2 --blur 1.5 --out diff.png`. `--blur` ignores sub-point
   anti-aliasing, and regions come back in pt to match against `tree`. Report what still differs and why
   (deliberate approximations, fonts).

### D. Multi-artboard documents
- Create: `file.new {…, artboards: n, artboardLayout: {layout: "row"|"gridByRow"|…, columns, spacing}}`. Add:
  `artboard.new {x, y, width, height, name}`. Edit many at once:
  `artboard.setProps {artboards: [{index, name, width, …}]}`. Fit: `artboard.fitToArt {indices}` /
  `artboard.fitToSelection {index}`. Tidy: `artboard.rearrange {layout, spacing}`. Art moves with
  rearranged artboards.
- Place an SVG/PDF/`.vectorcraft` onto one: `file.place {path, link: false, at: [cx, cy]}`. For SVGs add
  `crop: "crop"` to frame by the file's viewBox; without it the frame is the art's bounds, stray off-page art
  included (tested: 270.9 pt wide vs the true 222.7).
- Select per artboard: `select.allOnArtboard {artboard}`. Align to an artboard:
  `object.align {to: "artboard", artboard}`.
- Export per artboard: PNG `document.export {path: "x.png", useArtboards: true, ppi}` writes `x-<artboard
  name>.png` each. PDF gives one page per artboard by default. SVG `range: "1-2"` writes one SVG per
  artboard. `ui.render {artboard: i}` previews one.

## Saving and exporting (what the user gets)

- **SVG**: `document.export {path: "…svg"}` (keeps live `<text>`, layers as `<g>`). VectorCraft writes the root
  size **unitless with 1 unit = 1 pt** (as Illustrator does). Browsers/Inkscape read that as px, so the figure
  shows at 75 % size. **Always run `apps/vectorcraft/tools.py svgunits out.svg mm`** (or `pt`) after exporting an SVG meant for
  papers or Inkscape. It reopens in VectorCraft at the same size (tested).
  `svg: {preserveEditing: true}` embeds the native document so VectorCraft reopens it losslessly (bigger file).
  `svg: {outlineText: true}` for no-font-dependency output.
- **PDF** `document.export {path: "…pdf"}` or `document.exportPdf {path, range, standard, …}`. **PNG**
  `{path, ppi: 300, background: "white"}`.
- **Native** `document.save {path: "…vectorcraft"}` keeps everything (effects, symbols). It gives the
  document that path, so later saves go there.
- Saving in the original's format over the original only when the user asks. A VectorCraft-written SVG loses
  Inkscape-only metadata (`inkscape:` layers become plain groups, export hints go).

## Typeset math and TikZ-style arrows

VectorCraft has neither an equation editor nor TikZ arrowheads, so the skill supplies both. Each comes out
as ordinary vector art, grouped and named, with its source stored on the group so it can be regenerated.

**Math (LaTeX → outlines)**: `scripts/latex_math.py`, which needs a TeX install (TeX Live / MacTeX; packages
such as mhchem, siunitx or chemfig work when installed).
```bash
M="uv run <skill>/scripts/latex_math.py"
$M 'k_\mathrm{obs} = \frac{1}{\tau}\ln\frac{[A]_0}{[A]_t}' --x 110 --y 40 --size 12          # Latin Modern
$M 'E = h\nu' --x 20 --y 90 --size 12 --font sans --color '#1f77b4'                    # Helvetica + sansmath (pairs with Arial)
$M '\ce{2 H2 + O2 -> 2 H2O}' --text --preamble '\usepackage[version=4]{mhchem}' --x 120 --y 90 --font sans
$M '\sum_{i=1}^N \int_0^\infty e^{-\lambda_i t}\,dt' --display --x 20 --y 160 --size 14
$M --list                                   # math objects in the active document, with their sources
$M --replace 37 'E = h\nu = \frac{hc}{\lambda}' --size 14     # re-typeset in place (same spot, stacking, options)
```
(x, y) is the left end of the **baseline**, like `text.create`, so math lines up with neighbouring labels
(`--align center|right` makes x the centre or right end, e.g. a rate constant centred over an arrow).
The output prints the box (width, height above the baseline, depth below it). Under the hood:
pdflatex `standalone` → `file.place {textAs: "outlines", crop: "crop"}`, giving one Clip Group named
`math: <source>` with `data-latex`. Tradeoffs to tell the user: the result is glyph **outlines, not live
text**, so edit it with `--replace` (or retype it), not the Type tool. It needs TeX on the machine. Sans
math (sansmath) suits Arial figures but isn't Arial. `--font arial` (lualatex, picked automatically) sets
text-mode content in real Arial (e.g. `'Rate $k_\mathrm{obs}$ (s$^{-1}$)' --text --font arial`), but its math
symbols stay Latin Modern. Units: siunitx follows the text font under `sans`/`arial`.

**TikZ arrows**: `tools.py arrow` / `tikz_arrow()` in `tools.py`, with tip geometry copied from PGF's own definitions
(`to` = TikZ `->`, `latex`, `stealth`), sized from the line width as PGF does. Straight arrows match
pdflatex output pixel for pixel; 30° bends match to within 0.3 pt.
```bash
tools.py arrow 20 20 180 20 --tip to --width 1            # ->
tools.py arrow 20 60 180 80 --tip to --width 1 --bend 30  # to[bend left=30]  (negative = bend right)
tools.py arrow 20 100 180 100 --tip latex --both          # <->-style with latex tips
```
Result: a group (shaft + tip paths) named `arrow (-to)`, with `data-tikz` holding the spec. Tradeoff: unlike
Stroke-panel arrowheads, the tip is separate geometry, so moving an endpoint means redrawing the arrow
(delete the group and call it again with the new points; read the old spec with
`json.loads(get_data(vc, id)["tikz"])`, `from tools import get_data`).
Recolouring and restyling the group works as usual. Manual near-equivalents for the Stroke panel:
`stealth` ≈ **Arrow**, `latex` ≈ **Concave**; `to` has no built-in equivalent (copy an existing one).

## Pitfalls (each one bit during testing)

- Paint inheritance (fact 4) and baseline text (fact 5).
- `ui.menu.invoke` of a dialog item without params may just run the command with defaults. To show a
  dialog use `tool.options {tool}` (Move/Rotate/Scale…), `ui.paramDialog {command, params}`, or `ui.*Dialog`
  commands. Then `ui.dialog.set` / `.confirm` / `.cancel`.
- Native file dialogs: any save/open/export without `path` pops a dialog for the human and returns
  `"cancelled"`. Always pass `path` (absolute).
- Background saves: `document.save`/`export` may return `{background: true}`. Check `ui.inspect` →
  `background` before reading the file immediately.
- The server closes the connection after an error reply. `Craft` reconnects automatically. Idle connections
  close after 5 minutes.
- Imported Inkscape layers inside groups come in as **groups** (nested `Layer 1` groups); only top-level
  `inkscape:groupmode="layer"` become layers.
- Fonts: missing families appear in `warnings` and render in a fallback. Ask before substituting. Type made
  without `font` uses the app default (Source Sans 3), not the figure's font, so always pass `font`.
- `object.setProps {name}` names the object. A text object's tree name is its text.
- `text.setText` flattens styled runs (coloured letters). To insert or replace part of a styled text use
  `text.editRange {id, start, end, insert}` with **byte** offsets into the UTF-8 text (× is 2 bytes).
- Object data (`object.setProps {data}`) reads back from `document.node` as `attrs.data = [[key, value]…]`.
  Use `get_data(vc, id)` (`from tools import get_data`), which returns a dict.

