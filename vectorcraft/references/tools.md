# VectorCraft tools

Generated 2026-10-30 from the running app by scripts/build_reference.py; regenerate after updates.

Each group is one toolbar button; the first tool shows, the others are in its flyout (press and hold the button, or Alt-click it to cycle). Select by automation with `ui.tool.select {tool: id}`; double-clicking a button runs `tool.options {tool: id}`.

| button | tool id | label | shortcut |
|---|---|---|---|
| 1 | `selection` | Selection Tool | V |
| 2 | `directSelection` | Direct Selection Tool | A |
| ↳ | `groupSelection` | Group Selection Tool |  |
| 3 | `magicWand` | Magic Wand Tool | Y |
| 4 | `lasso` | Lasso Tool | Q |
| 5 | `pen` | Pen Tool | P |
| ↳ | `addAnchor` | Add Anchor Point Tool | + |
| ↳ | `deleteAnchor` | Delete Anchor Point Tool | - |
| ↳ | `anchorPoint` | Anchor Point Tool | Shift+C |
| 6 | `curvature` | Curvature Tool | Shift+~ |
| 7 | `type` | Type Tool | T |
| ↳ | `areaType` | Area Type Tool |  |
| ↳ | `typeOnPath` | Type on a Path Tool |  |
| ↳ | `verticalType` | Vertical Type Tool |  |
| ↳ | `verticalAreaType` | Vertical Area Type Tool |  |
| ↳ | `verticalTypeOnPath` | Vertical Type on a Path Tool |  |
| ↳ | `touchType` | Touch Type Tool | Shift+T |
| 8 | `lineSegment` | Line Segment Tool | \ |
| ↳ | `arc` | Arc Tool |  |
| ↳ | `spiral` | Spiral Tool |  |
| ↳ | `rectangularGrid` | Rectangular Grid Tool |  |
| ↳ | `polarGrid` | Polar Grid Tool |  |
| 9 | `rectangle` | Rectangle Tool | M |
| ↳ | `roundedRectangle` | Rounded Rectangle Tool |  |
| ↳ | `ellipse` | Ellipse Tool | L |
| ↳ | `polygon` | Polygon Tool |  |
| ↳ | `star` | Star Tool |  |
| ↳ | `flare` | Flare Tool |  |
| 10 | `paintbrush` | Paintbrush Tool | B |
| ↳ | `blobBrush` | Blob Brush Tool | Shift+B |
| 11 | `shaper` | Shaper Tool | Shift+N |
| ↳ | `pencil` | Pencil Tool | N |
| ↳ | `smooth` | Smooth Tool |  |
| ↳ | `pathEraser` | Path Eraser Tool |  |
| ↳ | `join` | Join Tool |  |
| 12 | `eraser` | Eraser Tool | Shift+E |
| ↳ | `scissors` | Scissors Tool | C |
| ↳ | `knife` | Knife |  |
| ↳ | `mirrorCut` | Mirror & Cut Tool |  |
| ↳ | `lineCut` | Line Cut Tool |  |
| ↳ | `rectCut` | Rectangle Cut Tool |  |
| 13 | `rotate` | Rotate Tool | R |
| ↳ | `reflect` | Reflect Tool | O |
| 14 | `scale` | Scale Tool | S |
| ↳ | `shear` | Shear Tool |  |
| ↳ | `reshape` | Reshape Tool |  |
| 15 | `width` | Width Tool | Shift+W |
| ↳ | `warp` | Warp Tool | Shift+R |
| ↳ | `twirl` | Twirl Tool |  |
| ↳ | `pucker` | Pucker Tool |  |
| ↳ | `bloat` | Bloat Tool |  |
| ↳ | `scallop` | Scallop Tool |  |
| ↳ | `crystallize` | Crystallize Tool |  |
| ↳ | `wrinkle` | Wrinkle Tool |  |
| 16 | `freeTransform` | Free Transform Tool | E |
| ↳ | `puppetWarp` | Puppet Warp Tool |  |
| 17 | `shapeBuilder` | Shape Builder Tool | Shift+M |
| ↳ | `livePaintBucket` | Live Paint Bucket | K |
| ↳ | `livePaintSelection` | Live Paint Selection Tool | Shift+L |
| 18 | `perspectiveGrid` | Perspective Grid Tool | Shift+P |
| ↳ | `perspectiveSelection` | Perspective Selection Tool | Shift+V |
| 19 | `mesh` | Mesh Tool | U |
| 20 | `gradient` | Gradient Tool | G |
| 21 | `eyedropper` | Eyedropper Tool | I |
| ↳ | `measure` | Measure Tool |  |
| 22 | `blend` | Blend Tool | W |
| ↳ | `objectsOnPath` | Objects on Path Tool |  |
| 23 | `dimension` | Dimension Tool |  |
| 24 | `symbolSprayer` | Symbol Sprayer Tool | Shift+S |
| ↳ | `symbolShifter` | Symbol Shifter Tool |  |
| ↳ | `symbolScruncher` | Symbol Scruncher Tool |  |
| ↳ | `symbolSizer` | Symbol Sizer Tool |  |
| ↳ | `symbolSpinner` | Symbol Spinner Tool |  |
| ↳ | `symbolStainer` | Symbol Stainer Tool |  |
| ↳ | `symbolScreener` | Symbol Screener Tool |  |
| ↳ | `symbolStyler` | Symbol Styler Tool |  |
| 25 | `columnGraph` | Column Graph Tool | J |
| ↳ | `stackedColumnGraph` | Stacked Column Graph Tool |  |
| ↳ | `barGraph` | Bar Graph Tool |  |
| ↳ | `stackedBarGraph` | Stacked Bar Graph Tool |  |
| ↳ | `lineGraph` | Line Graph Tool |  |
| ↳ | `areaGraph` | Area Graph Tool |  |
| ↳ | `scatterGraph` | Scatter Graph Tool |  |
| ↳ | `pieGraph` | Pie Graph Tool |  |
| ↳ | `radarGraph` | Radar Graph Tool |  |
| 26 | `artboard` | Artboard Tool | Shift+O |
| ↳ | `slice` | Slice Tool | Shift+K |
| ↳ | `sliceSelection` | Slice Selection Tool |  |
| 27 | `hand` | Hand Tool | H |
| ↳ | `rotateView` | Rotate View Tool | Shift+H |
| ↳ | `printTiling` | Print Tiling Tool |  |
| 28 | `zoom` | Zoom Tool | Z |
