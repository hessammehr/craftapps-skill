# PhotoCraft

Raster editor in the style of Photoshop: layers, masks, adjustment layers, filters, selections, type, shapes, brushes, Camera Raw, actions and batch. Reads and writes PSD. Use
Photoshop's vocabulary with the person. Read `SKILL.md` first; this file is what is specific to PhotoCraft.

- **Port:** only with `--control`, so `craft.py photocraft launch`. If it's already running without a port, it has to be saved, quit and relaunched: ask.
- **Auth:** a token file, created by `launch` and read by `craft.py`. A running instance's token path is taken from its command line.
- **File access:** channel paths must be under the folders given at launch (home by default, `--roots DIR` to narrow). Relative paths are relative to that root.
- **Grouping:** none in the GUI: each command is one history state. `c.seq` undoes its own steps on failure. `history.newSnapshot` marks a point; `history.selectState` jumps back.
- **Surface:** `craft.py photocraft families`. Sweep: 965 commands, 788 run or refuse with a stated reason on a scratch image, 177 skipped for outside effects, none hung.

## How a document works

Non-destructive by habit, as in Photoshop: **prefer adjustment layers, masks and smart filters to painting on pixels**, and keep the original layer untouched.
`craft.py photocraft tree` shows the stack, top first, with ids, kinds, bounds and masks. Most commands act on the active layer; pass `{"layer": id}` to be explicit.

**Check what you've changed:** `tree` for the stack and history, `render` for the composite. Sample a pixel with `document.pixel` or `document.sampleColor` when a number matters more than a look.

## Whole-task recipe (tested)

```python
c = Craft("photocraft")
c.open("/abs/micrograph.png")
c.run("layer.duplicate", {"name": "denoised"})
c.run("filter.blur.gaussianBlur", {"radius": 3})                       # on the copy
c.run("select.rect", {"x": 700, "y": 100, "width": 400, "height": 300, "feather": 20})
c.run("layer.layerMask.revealSelection")                               # the blur now shows only there
c.run("layer.newAdjustmentLayer.levels", {"name": "contrast"})
c.run("layer.setAdjustment", {"inBlack": 40, "inWhite": 200, "gamma": 1.1})
c.run("shape.create", {"kind": "rect", "rect": [980, 730, 180, 10], "fill": "#ffffff", "name": "scale bar"})
c.run("type.create", {"x": 1000, "y": 715, "text": "50 µm", "size": 34, "font": "Arial", "color": "#ffffff"})   # y is the baseline
c.save("/abs/micrograph.pcraft")                                       # layered; the document takes this path
c.export("/abs/micrograph_annot.png")                                  # a flattened copy; the document keeps its path
```

Bringing in another image: `file.placeEmbedded` is disabled over the channel. Open it as its own document, then `layer.copyToDocument` into the target, then close the source.

## Driving the GUI

```bash
craft.py photocraft call ui.set '{"tool": "Brush", "brushSize": 12}'     # tools, brush, options bar, panels, zoom, theme: see ui.set in the docs
craft.py photocraft run tools.setColors '{"foreground": "#ffd21f"}'
craft.py photocraft call ui.pointer '{"events": [{"kind": "down", "x": 300, "y": 300, "pressure": 0.8}, {"kind": "move", "x": 420, "y": 340}, {"kind": "up", "x": 600, "y": 360}]}'
craft.py photocraft call ui.menu.invoke '{"id": "filter.blur.gaussianBlur"}'   # opens the real dialog with live preview (note: `id`, not `command`)
craft.py photocraft dialog                                                # kind, title, fields
craft.py photocraft dialog set '{"radius": 4}'; craft.py photocraft dialog ok
```

`ui.pointer` works in **document pixels** and takes pressure, tilt and rotation, like a pen. `engine.execute` never opens a dialog; `ui.menu.invoke` behaves as choosing the menu item. `ui.inspect` is rich: `tool`, `toolOptions`, `document`
(layers, history, selection), `dialogs`, `jobs`, `textEdit`, `distort` (Liquify, Select and Mask and other full-screen modes), `histogram`, `views`. `ui.type {text}` types into the focused field or the text being edited.

Long commands (filters, content-aware fill) can run as jobs: `engine.execute {command, params, wait: false}`, then `jobs.list` / `jobs.cancel`. `status` shows them as busy.

## Command families

| Family | What |
|---|---|
| `layer` (224) | `new.*`, `duplicate`, `setProps`, `arrange.*`, `layerMask.*`, `vectorMask`, `newAdjustmentLayer.*`, `setAdjustment`, smart objects, groups, styles, align, distribute |
| `filter` (124) | blur, sharpen, noise, distort, stylize, render, `filterGallery`, Camera Raw |
| `edit` (79), `history` (14) | undo, fill, stroke, `transform.*`, paste variants, colour profile; states and snapshots |
| `type` (78) | `create edit setStyle`, OpenType, anti-aliasing, warp, on a path |
| `image` (66) | `adjustments.*` (destructive versions), `crop`, resize, canvas, rotation, mode, trim |
| `select` (35), `channel` (22) | `rect lasso magicWand colorRange quick subject object modify.*`; alpha and spot channels |
| `file` (59), `document` (11) | new, automate, scripts, export; `inspect pixel sampleColor` |
| `paint` (28), `brush` (18), `tools` (13), `gradient` (12), `pattern` (10), `swatches` (12) | strokes, healing, clone, dodge and burn; brushes and colours |
| `shape` (9), `path` (25) | vector shapes and paths |
| `view` (31), `count` (7), `slice` (7), `layerComp` (14), `timeline` (7), `actions` (20) | guides, proofing, count tool, slices, layer comps, animation, recorded actions |

Control methods: grep `craft.py photocraft docs` for `` - `ui. ``. `ui.set` alone has dozens of options.

## Headless

```bash
photocraft-cli run in.png --cmd filter.blur.gaussianBlur --params '{"radius": 4}' --out out.png   # tested
photocraft-cli info in.png                                                                        # document JSON
photocraft-cli batch …; photocraft-cli convert a.psd b.png; photocraft-cli droplet …; photocraft-cli commands
photocraft-cli serve --port P                                                                     # a headless session on the same protocol, with `batch`, `doc.place`, `doc.render`
```

In `/Applications/PhotoCraft.app/Contents/MacOS/` on macOS. `serve` has the `doc.*` file methods the GUI channel lacks. Its method list differs: send `methods`.

## Teaching fundamentals

Tools on the left, options bar along the top, panels on the right (Color, Properties, Layers, Channels, Paths); as in Photoshop. Non-destructive habits to teach first: duplicate before destructive edits, Layer › New Adjustment Layer rather than Image › Adjustments, masks rather than erasing. `craft.py photocraft how WORDS` gives any menu path.

## Pitfalls

- **Absolute paths rejected** unless under a root: launch with `--roots`, or relaunch.
- **`file.saveACopy`, `file.placeEmbedded` and similar** are disabled over the channel ("ambient filesystem paths"). Use `app.save`, `app.open`, `layer.copyToDocument`.
- **`ui.dialog.*` takes the dialog's `id`** (`craft.py photocraft dialog …` handles that). The unsaved-changes prompt has id `"discard"`.
- **While a modal is open, commands are refused** ("unavailable while a modal dialog is open").
- **`document.activate` takes `{document: index}`,** unlike VectorCraft's `{index}`.
- **Filters on a type or shape layer** ask to rasterize or convert it first, opening a prompt: select a pixel layer, or make the choice deliberately.
- **Commands fail on the wrong layer kind** ("layer 29 is a Pixel layer, not a shape layer"), and a pixel tool on a type or shape layer opens a Rasterize prompt: select the right layer first.
- **Exports show a toast** in the window ("7 layer(s) flattened"); that's expected, and it doesn't change the document.
- **`select.deselect` errors with no selection**, so check `status` first in scripts.
- **Type:** `fontStyle` selects Bold (`"style"` is ignored); `y` is the baseline of the first line.
