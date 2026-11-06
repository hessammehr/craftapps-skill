# Recipes (tested on VectorCraft, Oct 2026)

All snippets are `command.batch` / `vc.seq` steps unless shown as calls. `vc` is
`sys.path.insert(0, "<skill>/scripts"); from craft import Craft; vc = Craft("vectorcraft")`.
Units are pt, y down. Look up any command's full parameters with `craft.py vectorcraft params <id>`.

## Documents

```python
d = vc.run("file.new", {"title": "Fig 2", "width": 505, "height": 300, "units": "Points"})   # → {index}
vc.run("document.activate", {"index": d["index"]})
vc.open("/abs/path/fig - v3.svg")                       # app.open → {index, title, format, warnings}
vc.ui()["documents"]                                    # [{title, dirty}], activeDocument
vc.inspect()                                            # artboards, layers (tree), selection, history
vc.call("document.inspect", {"depth": 0})               # cheap: artboards + history, no tree
vc.run("document.node", {"id": 12})                     # one object in full (runs, fonts, anchors, xf)
vc.run("document.find", {"text": "Catalyst"})            # → {matches: [{id, name, kind, path}], total}
vc.run("document.find", {"kind": "Path", "within": [x, y, w, h], "minArea": 100})
```

## Shapes, paths, lines

```python
("shape.rectangle", {"x": 40, "y": 40, "width": 200, "height": 120, "radius": 6})   # → {id}, kind Rectangle
("shape.ellipse",   {"x": 10, "y": 10, "width": 30, "height": 20})
("shape.line",      {"x1": 0, "y1": 50, "x2": 100, "y2": 50})                      # kind Line
("shape.star",      {"cx": 110, "cy": 230, "radius1": 50, "radius2": 22, "points": 5})
("shape.polygon",   {"cx": 0, "cy": 0, "radius": 20, "sides": 6})
("path.create",     {"d": "M330 22 H412 L397.4 50.3 H315.4 Z"})                   # any SVG path data
("path.create",     {"anchors": [{"x": 0, "y": 0, "out": [30, -20]}, {"x": 60, "y": 0, "in": [30, -20]}], "closed": False})
# many marks as ONE object (axis ticks): major every 5th
("path.create", {"d": " ".join(f"M{x0+k*dx:.2f} {y} V{y + (4.3 if k % 5 == 0 else 2.8)}" for k in range(20))})
# pie wedge (SVG arcs work): centre, start point, arc, close
("path.create", {"d": f"M{cx} {cy} L{x0} {y0} A{r} {r} 0 {large} 1 {x1} {y1} Z"})
# quadratic arc (standing-wave line)
("path.create", {"d": f"M{cx-h} {y} Q{cx} {y-10} {cx+h} {y}"})
```

## Paint and stroke (set explicitly: new art inherits the last paint)

```python
("paint.setFill",   {"color": "#5599ff"})                 # selection (the object just made)
("paint.setFill",   {"ids": [12, 13], "none": True})
("paint.setStroke", {"color": "#000000"})
("stroke.set",      {"weight": 1.417, "cap": "round", "join": "round"})
("stroke.set",      {"dash": [4, 3]})                       # dashed; null for solid
("stroke.set",      {"endArrow": "Triangle", "arrowAlign": "tip"})   # also startArrow; see params for the list
("paint.setFill",   {"gradient": {"kind": "radial", "stops": [            # radial droplet
    {"offset": 0, "color": "#3771c8"}, {"offset": 0.55, "color": "#3771c8"}, {"offset": 1, "color": "#8fafe0"}]}})
("paint.setFill",   {"gradient": {"kind": "linear", "angle": 90, "stops": [...]}})
("object.setProps", {"ids": [5], "opacity": 60, "blend": "Multiply", "name": "halo"})
```
Python shorthand: `vc.rect(x, y, w, h, fill="#f2f2f2", stroke="none")`, `vc.path(d, fill="none", stroke="#ccc", weight=1.5)`,
`vc.ellipse(...)`, `vc.style(id, fill, stroke, weight)`. Each returns the new id.

## Type

```python
# point type: y = baseline of line 1; Arial top-of-bounds = y - 0.905*size
("text.create", {"x": 143.3, "y": 55.3, "text": "Classic organic\nsynthesis", "size": 12,
                 "font": "Arial", "justify": "center", "color": "#000000"})
("text.create", {"x": 0, "y": 16, "text": "a", "size": 20, "font": "Arial", "style": "Bold", "color": "#000"})
("text.create", {"x": 10, "y": 20, "text": "long caption …", "size": 9, "area": {"width": 200, "height": 60}})  # area type, wraps
("text.setText",  {"id": 28, "text": "Time (ms)"})                 # keeps the FIRST run's style: flattens coloured runs
# insert into styled text without losing runs (byte offsets into the UTF-8 text)
at = "".join(r["text"] for r in vc.run("document.node", {"id": f})["kind"]["runs"]).encode().index(b")(") + 1
("text.editRange", {"id": f, "start": at, "end": at, "insert": "×"})  # takes the neighbouring style
("text.setStyle", {"ids": [25, 26], "leading": 15, "size": 12, "font": "Helvetica", "fill": "#333"})
("text.setStyle", {"id": 7, "start": 0, "end": 4, "style": "Bold"})   # a byte range
("text.setFormat", {"id": 7, "position": "subscript", "start": 1, "end": 2})  # H₂O-style (byte offsets)
("type.createOutlines", {})                                          # selection → paths
```
`vc.run("text.fontList")` lists installed families; imported missing fonts show in `app.open`'s `warnings`.

## Selecting, stacking, grouping, layers

```python
("select.set", {"ids": [3, 4]}); ("select.all", {}); ("select.allOnArtboard", {"artboard": 1})
("select.anchors", {"id": 2, "anchors": [[0, 4], [0, 5]], "mode": "set"})   # [subpath, anchor] pairs
("path.moveAnchors", {"dx": 0, "dy": -8.1})                                 # move just those anchors
("object.group", {"ids": [25, 26, 27]})                                     # → {id}
("object.ungroup", {})
("layer.move", {"ids": [h1, h2], "target": droplet_id, "place": "below"})   # stack relative to an object
("object.arrange.bringToFront", {"ids": [9]})                               # / sendToBack / bringForward / sendBackward
("layer.setProps", {"name": "Annotations"})                                  # current layer (or {id, …})
("layer.new", {"name": "Scale", "top": True})                               # becomes current: new art goes there
("object.setProps", {"ids": [4], "locked": True, "visible": False})
```

## Moving, transforming, aligning

```python
("object.move", {"ids": [25, 26, 27], "dx": 0, "dy": -15})
("object.move", {"ids": [5], "dx": 20, "dy": 0, "copy": True})     # then object.transformAgain {} repeats (Cmd+D)
("object.scale", {"ids": [5], "sx": 50, "sy": 50, "origin": [x, y], "strokes": False})
("object.rotate", {"ids": [5], "angle": 45})                         # counter-clockwise, about the centre
("object.reflect", {"axis": "vertical"})
("object.transform", {"matrix": [1, 0, 0, s, 0, ty], "strokes": False})
("object.align", {"horizontal": "center", "to": "artboard", "artboard": 0})
("object.distribute", ...)  # see params
```

## Artboards

```python
("file.new", {"width": 260, "height": 220, "units": "Points", "artboards": 3,
              "artboardLayout": {"layout": "row", "spacing": 40}})
("artboard.new", {"x": 900, "y": 0, "width": 300, "height": 200, "name": "inset"})
("artboard.setProps", {"index": 0, "width": 442.9})
("artboard.setProps", {"artboards": [{"index": 0, "name": "v1"}, {"index": 1, "name": "v2"}]})
("artboard.fitToArt", {"indices": [0, 1]})
("artboard.fitToSelection", {"index": 2})
("artboard.rearrange", {"layout": "row", "spacing": 30})
("file.place", {"path": "/abs/fig.svg", "link": False, "crop": "crop", "at": [cx, cy]})   # crop: frame = SVG viewBox
```

## Copy between documents

```python
vc.run("document.activate", {"index": src}); vc.run("select.set", {"ids": ids}); vc.run("edit.copy")
vc.run("document.activate", {"index": dst}); vc.run("edit.pasteInPlace")    # same coordinates; or edit.paste
```

## Render, compare, export, save

```python
vc.render("/abs/out.png", artboard=0, scale=2)                      # ui.render: artboard only, no UI
vc.call("ui.screenshot", {"path": "/abs/win.png"})                  # the whole window (for teaching)
vc.run("document.export", {"path": "/abs/fig.svg"})                 # then: apps/vectorcraft/tools.py svgunits fig.svg mm
vc.run("document.export", {"path": "/abs/fig.svg", "svg": {"preserveEditing": True, "outlineText": False}})
vc.run("document.export", {"path": "/abs/fig.pdf"})                 # every artboard, one page each
vc.run("document.export", {"path": "/abs/fig.pdf", "range": "2"})
vc.run("document.export", {"path": "/abs/fig.png", "ppi": 300, "background": "white"})
vc.run("document.export", {"path": "/abs/fig.png", "useArtboards": True, "ppi": 150})  # fig-<artboard name>.png each
vc.run("document.save", {"path": "/abs/fig - v4.vectorcraft"})       # native; the document now has this path
```
```bash
uv run <skill>/scripts/compare.py mine.png target.png --pt-scale 2 --blur 1.5 --out diff.png
```

## One undo step for scripted logic

```python
vc.run("edit.undoGroup.begin", {"label": "Add panel b"})
try:
    ...  # any number of vc.run / helper calls, with Python logic between them
finally:
    vc.run("edit.undoGroup.end")
```
Or `vc.seq([...], label)` with `"$N.id"` references (rolls back on error). Or `vc.batch([...], label)` (atomic, no references).

## TikZ arrows and LaTeX math

```python
sys.path.insert(0, "<skill>/apps/vectorcraft"); from tools import tikz_arrow, get_data
g = tikz_arrow(vc, (20, 20), (180, 20), tip="to", width=1.0)            # TikZ ->   → group id
g = tikz_arrow(vc, (20, 60), (180, 80), tip="to", width=1, bend=30)     # to[bend left=30]
g = tikz_arrow(vc, (20, 100), (180, 100), tip="stealth", both=True, color="#555555")
spec = json.loads(get_data(vc, g)["tikz"])                               # to redraw with new endpoints
```
```bash
uv run <skill>/scripts/latex_math.py '\frac{\partial c}{\partial t} = D\nabla^2 c' --x 40 --y 60 --size 11 --font sans
uv run <skill>/scripts/latex_math.py --replace <id> 'new source'      # same place and options
```

## Effects (live, editable in the Appearance panel)

```python
vc.run("effect.list")                                               # ids + defaults
("effect.apply", {"ids": [5], "effect": "stylize.dropShadow", "params": {"opacity": 40, "blur": 4}})
("effect.apply", {"effect": "path.offsetPath", "params": {"offset": 2}})
("effect.expandAppearance", {})                                     # bake effects into paths
```

## Pathfinder / booleans

`craft.py vectorcraft find pathfinder` → `object.pathfinder.unite|minusFront|intersect|exclude|divide|…` on the selection (exact
booleans). Shape Builder is the `shapeBuilder` tool (drive with `ui.pointer`).

## Driving a tool like the mouse (rarely needed; for demos)

```python
vc.call("ui.tool.select", {"tool": "ellipse"})
vc.call("ui.pointer", {"events": [{"kind": "down", "x": 100, "y": 100}, {"kind": "drag", "x": 150, "y": 140},
                                  {"kind": "up", "x": 200, "y": 180}]})            # document coordinates
```
