# SolidCraft

Parametric 3D CAD in the style of Fusion: sketches, a feature timeline (History bar), components and joints, plus surfacing, sheet metal, plastic
features, weldments, motion studies and rendering. Read `SKILL.md` first; this file is what is specific to SolidCraft.

- **Port:** on by default, whatever launched it: 27878 or the next free port, published in `control/current.port`. `craft.py` finds it, and the token.
  So you can usually attach to the person's session with no relaunch. A launch with `--control` doesn't take the foreground.
- **Auth:** a per-launch token, read from `control/<port>.token` next to `current.port`.
- **Grouping:** `engine.batch` rolls everything back on failure (at most 10,000 commands); each step stays its own undo entry. `edit.checkpoint` →
  `edit.restore_checkpoint` returns to a point, undo history included.
- **Surface:** `craft.py solidcraft families`. Sweep: 570 commands, 457 run or refuse with a stated reason on a scratch part, 113 skipped for outside effects, none hung.

## How a design works

History-based, like Fusion: **sketch → feature → body**, with every step in a timeline that recomputes when anything changes. So the valuable output
isn't a shape, it's a model that can still change. Prefer:

- **Named parameters** for what might change (`parameters.add {name, expression, unit}`). Expressions work nearly everywhere, sketch points included: `"W / 2"`.
- **Editing features** over rebuilding: `timeline.edit {feature, set}`, `parameters.change {name, expression}` (the reply says how much recomputed and any errors).
- **Names.** `timeline.rename` features you'll refer to. Features, sketches and bodies are addressed by name or id.
- **Geometry picks by world point:** `{"edges": [[x,y,z]]}` is a point on the edge, in mm. Read positions from `document.inspect {measure: true}` (bounding boxes, volume, area, face types).

A STEP import has no history: it arrives as one Import feature, with edits on top of it (`solid.press_pull`, `solid.offset_face`, `face.delete`, `solid.move`).

## Whole-task recipe (tested)

```python
c = Craft("solidcraft")
for name, value in (("W", "80 mm"), ("L", "60 mm"), ("T", "8 mm"), ("vial_d", "16 mm"), ("pitch", "24 mm")):
    c.run("parameters.add", {"name": name, "expression": value, "unit": "mm"})
c.run("sketch.create", {"plane": "XY"})
c.run("sketch.rectangle.center", {"center": [0, 0], "corner": ["W / 2", "L / 2"]})
c.run("sketch.finish")
c.run("solid.extrude", {"distance": "T"})                                  # feature "Extrude1", body "Body1"
c.run("sketch.create", {"plane": "XY"})
c.run("sketch.circle.center", {"center": [-24, -12], "radius": "vial_d / 2"})
c.run("sketch.finish")
c.run("solid.extrude", {"distance": "T", "operation": "cut"})              # "Extrude2"
c.run("solid.pattern.rectangular", {"features": ["Extrude2"], "dir1": [1, 0, 0], "count1": 3, "spacing1": "pitch",
                                    "dir2": [0, 1, 0], "count2": 2, "spacing2": "pitch"})
c.run("solid.fillet", {"edges": [[40, 30, 4], [-40, 30, 4], [40, -30, 4], [-40, -30, 4]], "radius": "4 mm"})
c.run("material.assign", {"bodies": ["Body1"], "material": "Aluminum"})    # material.list; then assembly.mass_properties
c.run("parameters.change", {"name": "W", "expression": "100 mm"})          # the whole model rebuilds
c.call("ui.view", {"view": "iso"}); c.call("ui.view", {"view": "fit"})
c.render("part.png"); c.save("part.sc"); c.export("part.step")             # also .stl, .3mf, .obj, .urdf
```

Assemblies: `component.create {name}` (it becomes active: new sketches and features go in it; `component.activate` to switch), `file.insert_step {path}` (STEP, IGES,
FCStd, 3dm: a new component), `file.insert_mesh` (STL, OBJ, 3MF), `component.insert_design` (a linked `.sc`: all its solid bodies, placed as in that design;
`occurrence.copy` places another, starting where its source is, and `occurrence.move {matrix, space}` moves by a rigid matrix), then `joint.create {type, a, b}` with origins such as `{"occurrence": "Lid:1", "circle": [x, y, z]}`. `joint.list` reports
conflicts and degrees of freedom; `joint.solve`, `joint.drive`, `motion.study` move and study them.

## Driving the GUI

Fully supported, and the reason to prefer the live app. The controls are named:

```bash
craft.py solidcraft call ui.agent_cursor '{"show": true, "speed": 2}'     # a visible pointer that glides to each button and pick
craft.py solidcraft call ui.start '{"command": "solid.chamfer"}'          # opens the real dialog; the reply says what it's waiting for
craft.py solidcraft call ui.at '{"world": [0, -30, 8]}'                   # → screen point of a model point; also sketch, plane, axis, dimension, handle
craft.py solidcraft call ui.click '{"x": 786, "y": 708}'                  # a real click: it picks whatever is in front
craft.py solidcraft call ui.handles '{"prefix": "dialog"}'                # named controls with positions: dialog:Distance, dialog:ok, dialog:cancel, toolbar:<command>
craft.py solidcraft dialog set '{"Distance": "2 mm"}'; craft.py solidcraft dialog ok
craft.py solidcraft call ui.selection                                     # selection, the dialog's inputs, the hovered item
```

Also: `ui.pick {pixels|rays}` (what's under a point), `select.set {items}` (select without clicking), `ui.view`, `ui.camera`, `ui.menu`, `ui.messages` (status history),
`view.save` / `view.apply` (named views), `document.revision` (cheap change check), `control.subscribe` (pushed events).
A click picks what's visible at that point, occluders included: hide what's in the way (`browser.visibility`) or use `select.set`.

## Command families

| Family | What |
|---|---|
| `sketch` (126) | lines, rectangles, circles, arcs, splines, slots, polygons, `constraint.*`, `dimension`, project, offset, trim; 3D sketches |
| `solid` (36) | `extrude revolve sweep loft pipe coil rib web emboss thread hole shell draft fillet chamfer combine mirror pattern.* press_pull offset_face move split_*`, primitives |
| `surface` (19) | `boundary patch stitch thicken extend trim loft offset ruled blend fair fillet match` |
| `sheet` (13), `frame` (4), `plastic` (7) | sheet metal with flat patterns and DXF, weldment members, plastic bosses, lips, snap fits |
| `construct` (20) | planes, axes and points to build from |
| `parameters` (13), `config` (8) | named values, and configuration tables (variants of a design) |
| `timeline` (22), `browser` (9) | History: `edit redefine reorder suppress rollback roll_to group inspect dependents` |
| `component` (32), `occurrence` (7), `explode` (4), `parts` (4) | assembly structure, linked designs, positions, exploded views, fasteners |
| `joint` (18), `motion` (11), `contact` (7) | joints, drives, gears, motion studies, plots, collisions |
| `inspect` (19), `assembly` (2), `model` (3), `expr` (1) | measure, section, interference, clearance, zebra, curvature, BOM, mass properties |
| `material` (8), `appearance` (10), `canvas` (6) | physical materials, looks, decals, canvases |
| `render` (60) | environment, lights, cameras, shots, the path-traced render workspace |
| `file` (16), `doc` (4), `library` (3), `pointcloud` (4), `mesh` (1) | save, export, insert; recovery; point clouds; mesh conversion |
| `view` (40), `select` (4), `edit` (5), `settings` (7) | view tools, selection, undo, checkpoints, setting profiles |

Control methods beyond commands (`ui.*`): grep `craft.py solidcraft docs` for `| \`ui.`.

## Headless

```bash
solidcraft-cli run script.json --out part.step --save part.sc   # a script: [{"command": …, "params": …}, …]
solidcraft-cli eval --in part.sc                                # measurements as JSON
solidcraft-cli snapshot --in part.sc --out part.png --view iso --width 800 --height 600
solidcraft-cli commands                                         # the catalogue, without a window
```

All tested. `run --in design.sc` applies a script to an existing design, which suits batch variants. `script` turns a design's history back into a script, except for designs with components, which it doesn't support yet.

**Step by step, for batch work:** `run` stops the whole script at the first failure. To check each step and react (retry another way, fall back to
an import), drive `solidcraft-cli mcp --headless --allow-any-path` instead: an MCP server on stdio whose `execute` tool runs one command and replies,
with `batch`, `measure`, `inspect_design`, `undo`, `open`, `save`, `export` and `new_design` alongside. `apps/solidcraft/headless.py` wraps it, with a
time limit on every call:

```python
sys.path.insert(0, "<skill>/apps/solidcraft"); from headless import Session, Hang
with Session(timeout=60) as s:
    r = s.run("solid.fillet", edges=[[40, 30, 4]], radius="4 mm")   # the reply, or {"error": …}
    bodies = s.tool("inspect_design")["bodies"]                      # name, volume_mm3, closed, bbox, faces of each body
```

A call over the limit kills that session and raises `Hang`: start a new `Session` and carry on from the last saved design. Run sessions one at a time;
each holds a whole kernel.

## Teaching fundamentals

Workspaces and tabs along the top (Model, Surface, Assemble, Insert, Inspect, Manage, View, Sheet Metal, Weldments); Browser on the left; History bar at the bottom. Sketch on a plane,
constrain and dimension until it's fully defined, finish, then make a feature from its profile. Double-click a History item to edit it. Press S for command search. `craft.py solidcraft how WORDS` gives the ribbon location and shortcut of anything.

## Checking what you built or imported

Measure after anything you didn't draw yourself, and compare with the source (`inspect_design`, or `document.inspect {measure: true}` live): each body
has `volume_mm3` and `closed`. In version 0.30.1 these needed it:

- **STEP from Open CASCADE** (FreeCAD and others): toroidal fillet faces can arrive as an open body, with `closed: false` and no volume. The reply of
  `file.insert_step` has no warning; the timeline does. Exporting the shape as NURBS first (FreeCAD: `shape.toNurbs().exportStep(…)`) imported cleanly.
  `surface.stitch` closed such a body but with the wrong volume. Helical B-spline solids (threads, springs) came in as closed with absurd volumes
  (−8e24 mm³); import those as a mesh.
- **Body names** of a STEP import come from its header ("Open CASCADE STEP translator 7.8 1"): pass `name`, or rename after.
- **Linked designs:** `component.insert_design` refuses a design holding only meshes ("no solid bodies to link"; insert the mesh instead), and once
  linked a body measured 34.8 mm³ that was 50.3 mm³ in its own design. Compare the linked bodies' volumes with the source.
- **Mesh bodies** can be moved, measured and exported, not used in booleans or features. `mesh.convert {body}` rebuilds a closed mesh of constant
  section (prisms, cylinders) as a solid with planar and cylindrical faces, which can: an STL cylinder came back closed, within 0.02% of its volume.
  `save` refused a design holding a 6.9M-triangle mesh ("design container: mesh too large"); 4M saved.
- **Kernel refusals and hangs:** some booleans (solids that only touch), fillets ("only straight edges can be blended", "the edge is smooth"), extrudes and
  holes failed or never answered where FreeCAD succeeded. Headless, give each call a time limit (above); live, `ui.inspect` shows `busy`.

These change from release to release: test before working around them, and drop a workaround once it is no longer needed.

## Pitfalls

- **A covered window draws no frames:** `ui.screenshot` fails and clicks wait. `ui.render` still works: it shows the model in the window's theme, and `ui.set {"dark": false}` gives a light background for print.
- **Status messages** can report old errors; read `ui.inspect` → `dialog.error` and the reply of your own call, not only the status line.
- **`file.save` and `file.save_as` write design files only**: STEP, STL and so on go through `file.export`.
- **`timeline.export_script`** refuses designs with components (upstream #886).
- **Killing the app** leaves an unclean-exit report and a notice at next start. Quit with `app.quit`, and only apps you started.
- **`app.quit {force: true}` with unsaved changes leaves a recovery entry,** which prompts at the next start. Save first, or clear your own with `doc.recovery_list` and `doc.recovery_discard {id}`.
- **`--isolated`** still writes token, session and recovery files to the real SolidCraft folder.
- **`save` over an existing file** leaves the previous version beside it as `.sc.bak`. Delete your own in batch work; they add up.
- **`file.export_stl {quality}`** sets the chord relative to each body's size (`standard` is coarse on large parts: 0.17 mm on an 848 mm body);
  use `fine` or `finest` for measuring, and `bodies` to export only some.
- **`edit.checkpoint`** takes no name; keep the id it returns. Only the last 16 are kept.
- **Units:** a bare number is in the design's units (mm by default), and in millimetres for world points. Say `"2 in"` when you mean it.
