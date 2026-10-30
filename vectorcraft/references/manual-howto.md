# Teaching mode: helping a person do it by hand

VectorCraft deliberately mirrors Illustrator: same tools, shortcuts, menus and panel names. So anything a
person learns here transfers, and Illustrator tutorials apply. Shortcuts below are macOS (Cmd ⌘, Alt ⌥
Option, Shift ⇧). On Windows/Linux, Cmd is Ctrl and Alt is Alt.

## Three ways to help

1. **Explain.** Turn the plan (or the script you would run) into numbered manual steps. One action per
   step: *where* (tool, menu path, panel), *what* (click, drag, type), *values* (exact numbers, colours,
   names), and *what they should see*. Get menu paths and shortcuts from the app, not from memory:
   ```bash
   uv run ~/.claude/skills/vectorcraft/scripts/vc.py how "Outline Stroke"   # menu path(s), shortcut, params
   uv run ~/.claude/skills/vectorcraft/scripts/vc.py how arrange            # several matches
   uv run ~/.claude/skills/vectorcraft/scripts/vc.py how ellipse            # tool + shortcut + which flyout
   grep -n "Clipping Mask" ~/.claude/skills/vectorcraft/references/menus.md
   ```
   Commands with no menu entry (`shape.*`, `path.create`, `text.create`, `paint.*`, `stroke.set`…) are done
   with a **tool** or a **panel** (map below).
2. **Show me.** Do it live, step by step, while they watch the app. Pause between steps and say what just
   happened and where on screen. Let them perform the key click whenever possible:
   - point at an object: `select.set {ids}` (selection handles show it); `view.setZoom` / `view.fitArtboard`
     to frame it;
   - open the panel they need: `window.panel {panel: "stroke"}` (ids are in `menus.md` › Window);
   - open a dialog prefilled and let *them* press OK: `tool.options {tool: "selection"}` (Move),
     `"rotate"|"scale"|"reflect"|"shear"`, `ui.paramDialog {command, label, params}` for any command,
     `effect.dialog {effect}` for an effect. Read what is open with `ui.inspect` → `ui.dialog`; fill fields with
     `ui.dialog.set {fields: [{field, value}]}`; close with `ui.dialog.cancel` if they decline;
   - select the tool they should use: `ui.tool.select {tool}` (the toolbar button lights up);
   - take `vc.py shot win.png` and look at it to describe positions accurately ("top-right panel, third tab").
   - Undo anything you demonstrated if they want to do it themselves: `vc.py undo`.
3. **Check my work.** They do it by hand, then you inspect and give precise feedback: `vc.py tree` (names,
   bounds, colours), `vc.py node <id>` (font, size, leading, stroke), and `vc.py render` + `compare.py`
   against a target render. Feedback names the object, the property, the value they have and the value
   wanted, and how to fix it ("the 20 label sits 1.5 pt low: select it, then in the Transform panel set
   Y to 152.2").

Adapt depth to the person: experienced Illustrator users want terse paths ("Object › Path › Offset Path…,
2 pt"); beginners need the selection step, what the dialog looks like and what to look for afterwards.

## Fundamentals to teach first (when the person is new)

- **Selection (V)** picks whole objects/groups. **Direct Selection (A)** picks anchor points and segments;
  drag a marquee over just the points to move one edge. **Group Selection** (flyout under A) picks an item
  inside a group. Double-click a group to **isolate** it, and Esc to leave isolation.
- **Fill and Stroke** swatches at the bottom of the toolbar: X swaps which is active, Shift+X swaps the
  colours, `/` sets none, D resets to the default (white fill, black stroke). **New objects take the
  current fill/stroke**, so set them before drawing or restyle after.
- **Layers panel (F7)**: eye = visibility, lock column, drag rows to restack, target circle to select.
- **Smart Guides (Cmd+U)** snap and show distances while dragging. **Rulers (Cmd+R)**. Drag guides out of
  the rulers.
- Precise values: the **Transform panel (Shift+F8)** or the **Properties panel** (X, Y, W, H, rotation)
  with the reference-point grid. Type maths into fields (`+5`, `*2`).
- **Arrow keys** nudge 1 pt (Shift+arrow 10 pt). Alt-drag duplicates. **Cmd+D** repeats the last
  transform (Transform Again).
- Paste variants: **Cmd+F** Paste in Front, **Cmd+B** Paste in Back, **Cmd+Shift+V** Paste in Place.
- **Cmd+Z** undo. **History panel** (Window › History).

## Task → manual method (figure-making)

| Goal | By hand | Automation equivalent |
|---|---|---|
| New figure of a set size | File › New… (Cmd+N): width, height, units, number of artboards | `file.new` |
| Document size/units later | File › Document Setup… (Cmd+Alt+P); Artboard tool (Shift+O) or Window › Artboards | `document.setup`, `artboard.setProps` |
| Rectangle / rounded / ellipse | Rectangle (M) / Rounded Rectangle (flyout) / Ellipse (L): drag, or click once for a size dialog. Shift = square/circle, Alt = from centre | `shape.rectangle`, `shape.ellipse` |
| Straight line | Line Segment tool (\\), Shift for 0/45/90° | `shape.line` |
| Free shape / curve | Pen (P): click = corner, drag = smooth; click the first point to close. Curvature tool (Shift+~) is easier for smooth blobs | `path.create {d \| anchors}` |
| Colour | Select → Fill/Stroke swatch → Color panel (F6) or Swatches; hex field in the Color Picker (double-click the swatch) | `paint.setFill`, `paint.setStroke` |
| Stroke weight, dashes, arrowheads | Window › Stroke (Cmd+F10): Weight, Cap, Corner, Align, **Dashed Line** (dash/gap boxes), **Arrowheads** (start/end menus, Scale, Align: tip at end) | `stroke.set {weight, dash, startArrow, endArrow, arrowAlign}` |
| Gradient | Window › Gradient (Cmd+F9): Type linear/radial, click the ramp to add stops, double-click a stop for its colour; Gradient tool (G) to drag the direction | `paint.setFill {gradient}` |
| Transparency | Window › Transparency (Cmd+Shift+F10): opacity, blend mode | `object.setProps {opacity, blend}` |
| TikZ-style arrow | Stroke panel › Arrowheads: **Arrow** ≈ TikZ stealth, **Concave** ≈ latex; the TikZ `to` (curved open barbs) has no built-in, so copy an existing one (Alt-drag) and rotate it, or ask the agent | `vc.py arrow … --tip to` |
| Equation | No equation editor. Typeset elsewhere (LaTeX/LaTeXiT, as PDF with outlined fonts) → File › Place… (Link off) and line its baseline up with Smart Guides; or ask the agent (`latex_math.py`) | `latex_math.py` (outlines, `--replace` to edit) |
| Text label | Type tool (T): click = point type, drag = area type (wraps). Character panel (Cmd+T): font, size, leading, tracking. Paragraph (Cmd+Alt+T): alignment | `text.create`, `text.setStyle` |
| Subscript / superscript | Select the characters with the Type tool → Character panel (Cmd+T), bottom row of buttons: T¹ superscript, T₁ subscript (also All Caps, Small Caps, Underline, Strikethrough) | `text.setFormat {position, start, end}` |
| Edit existing text | Type tool, click into the text (or double-click it with Selection) | `text.setText` |
| Move exactly | Object › Transform › Move… (Cmd+Shift+M) or Transform panel X/Y; Enter with Selection tool opens Move | `object.move {dx, dy}` |
| Evenly spaced copies (ticks) | Draw one, Alt-drag a copy with Shift, then Cmd+D repeatedly; or Move… with Copy then Cmd+D | `object.move {copy}` + `object.transformAgain`, or one `path.create` |
| Rotate / scale / reflect | Rotate (R), Scale (S), Reflect (O); double-click the tool for exact values; Alt-click sets the origin | `object.rotate/scale/reflect` |
| Align / distribute | Window › Align (Shift+F7): buttons; "Align To" menu: selection / key object / artboard. Click one selected object again to make it the key | `object.align {to}`, `object.distribute` |
| Stacking order | Object › Arrange › Bring to Front Cmd+Shift+] / Forward Cmd+] / Backward Cmd+[ / Back Cmd+Shift+[; or drag in Layers | `object.arrange.*`, `layer.move` |
| Put something behind a given object | Copy it (Cmd+C), select the target, Paste in Back (Cmd+B), delete the original | `layer.move {target, place: "below"}` |
| Group / ungroup | Cmd+G / Cmd+Shift+G | `object.group` / `object.ungroup` |
| Lock / hide | Object › Lock › Selection Cmd+2 / Hide Cmd+3; unlock all Cmd+Alt+2 | `object.setProps {locked, visible}` |
| Move one edge of a box | Direct Selection (A): marquee the edge's two points, then arrow keys or drag with Shift | `select.anchors` + `path.moveAnchors` |
| Combine shapes | Window › Pathfinder (Cmd+Shift+F9): Unite, Minus Front, Intersect, Exclude; or Shape Builder (Shift+M) | `object.pathfinder.*` |
| Join open paths | Select both endpoints (Direct Selection) → Object › Path › Join (Cmd+J) | `path.join` |
| Stroke to filled shape | Object › Path › Outline Stroke | `object.path.outlineStroke` |
| Text to outlines (font-proof) | Type › Create Outlines (Cmd+Shift+O) | `type.createOutlines` |
| Clip an image/region | Put the clipping shape on top, select both, Object › Clipping Mask › Make (Cmd+7) | `object.clippingMask.make` |
| Drop shadow etc. (live) | Effect › Stylize › Drop Shadow…; edit later in Window › Appearance (Shift+F6) | `effect.apply` |
| Multiple artboards | Artboard tool (Shift+O): drag to make, Alt-drag duplicates; Window › Artboards to name/reorder; Object › Artboards › Fit to Artwork Bounds / Rearrange All Artboards… | `artboard.*` |
| Bring in another figure | File › Place… (Cmd+Shift+P); uncheck Link to embed editable art; or open it, Cmd+C, switch tab, Cmd+Shift+V | `file.place`, copy + `edit.pasteInPlace` |
| Duplicate same-styled items in bulk | Select › Same › Fill Color (etc.), then restyle all at once | `select.same.*` |
| Export SVG | File › Export › Export As SVG… (SVG Options: Styling, Fonts → Convert to outlines?, Preserve editing) | `document.export` |
| Export PDF / PNG | File › Save as PDF…; File › Export › Export As PNG… (resolution, Use Artboards for one file each) | `document.export {ppi, useArtboards}` |
| Export each artboard | File › Export › Export for Screens… (Cmd+Alt+E), Artboards tab | `document.exportForScreens`, `useArtboards` |
| Save a new version | File › Save As… (Cmd+Shift+S) with a new name (`… - v4`) | `document.save {path}` |

## Phrasing template

> **Step 3 — Add the time axis ticks.**
> 1. Press **\\** (Line Segment tool). Hold **Shift** and drag a short vertical line under the "0" position
>    (about 4 pt long).
> 2. In **Window › Stroke** (Cmd+F10) set **Weight 1.42 pt**.
> 3. With the **Selection tool (V)**, Alt+Shift-drag the tick 14.2 pt to the right. (Or press Enter →
>    Move…, Horizontal 14.17 pt, Vertical 0, click **Copy**.)
> 4. Press **Cmd+D** 18 more times. Each press repeats the move-and-copy.
> 5. You should now see 20 evenly spaced ticks. Select every 5th and make it longer with Direct Selection.

Then offer: "Want me to do this step while you watch, or check yours when you're done?"

## Translating a script into steps

Walk the script's commands in order. For each, `vc.py how <command>` gives the menu path/shortcut, or the
table above the tool/panel. Merge consecutive commands that are one gesture for a person (create +
`paint.setFill` = "draw it, then click the fill swatch…"), and drop automation-only steps (`document.activate`,
`select.set` → "click it", undo groups).
