#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10", "numpy>=1.26"]
# ///
"""Compare two renders (PNG) and say where they differ.

  compare.py A.png B.png [--out diff.png] [--threshold 40] [--blur 1.5] [--pt-scale 2]

Both images are resized to A's size if needed (a warning says so). Prints the share of
differing pixels and the bounding boxes of the largest differing regions in A's pixel
coordinates and, when --pt-scale is given (pixels per point used for the render), in
document points so they can be matched against `craft.py APP tree` bounds. Writes a diff image
(A greyed out, differences in red where only A has ink, blue where only B has ink).
"""
import argparse
import sys

import numpy as np
from PIL import Image, ImageFilter


def load(p, size=None, blur=0):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    im = Image.alpha_composite(bg, im).convert("RGB")
    if size and im.size != size:
        print(f"note: resized {p} from {im.size} to {size}", file=sys.stderr)
        im = im.resize(size, Image.LANCZOS)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im).astype(np.int16)


def regions(mask, max_regions=12):
    """Coarse connected regions via a downsampled grid (no scipy needed)."""
    h, w = mask.shape
    cell = max(4, min(h, w) // 60)
    gh, gw = (h + cell - 1) // cell, (w + cell - 1) // cell
    pad = np.zeros((gh * cell, gw * cell), bool)
    pad[:h, :w] = mask
    grid = pad.reshape(gh, cell, gw, cell).any(axis=(1, 3))
    seen = np.zeros_like(grid)
    out = []
    for y, x in zip(*np.nonzero(grid)):
        if seen[y, x]:
            continue
        stack, cells = [(y, x)], []
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            cells.append((cy, cx))
            for ny in range(cy - 1, cy + 2):
                for nx in range(cx - 1, cx + 2):
                    if 0 <= ny < gh and 0 <= nx < gw and grid[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        ys, xs = zip(*cells)
        x0, y0, x1, y1 = min(xs) * cell, min(ys) * cell, (max(xs) + 1) * cell, (max(ys) + 1) * cell
        npx = int(sum(mask[cy * cell:(cy + 1) * cell, cx * cell:(cx + 1) * cell].sum() for cy, cx in cells))
        out.append((npx, (x0, y0, min(x1, w), min(y1, h))))
    out.sort(reverse=True)
    return out[:max_regions]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--out")
    ap.add_argument("--threshold", type=int, default=40, help="per-channel difference counted as a change")
    ap.add_argument("--blur", type=float, default=0, help="Gaussian blur radius (px) applied first; 1-2 ignores sub-point text shifts")
    ap.add_argument("--pt-scale", type=float, help="pixels per document point of the renders (ui.render scale)")
    a_ = ap.parse_args()
    A = load(a_.a, blur=a_.blur)
    B = load(a_.b, (A.shape[1], A.shape[0]), a_.blur)
    diff = np.abs(A - B).max(axis=2) > a_.threshold
    share = diff.mean() * 100
    print(f"differing pixels: {share:.2f}% ({int(diff.sum())} of {diff.size})")
    for npx, (x0, y0, x1, y1) in regions(diff):
        s = f"  region px [{x0},{y0} → {x1},{y1}]  ({npx} px)"
        if a_.pt_scale:
            k = a_.pt_scale
            s += f"  ≈ pt x={x0/k:.1f} y={y0/k:.1f} w={(x1-x0)/k:.1f} h={(y1-y0)/k:.1f}"
        print(s)
    if a_.out:
        grey = (A.mean(axis=2, keepdims=True) * 0.25 + 191).repeat(3, axis=2)
        inkA = A.mean(axis=2) < B.mean(axis=2)
        out = grey.copy()
        out[diff & inkA] = (220, 30, 30)
        out[diff & ~inkA] = (30, 80, 230)
        Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(a_.out)
        print(f"diff image: {a_.out} (red: ink only in A, blue: ink only in B)")


if __name__ == "__main__":
    main()
