"""Green crystal clusters (newshj.shp frames 267, 269, 271, an assembly of 3 pieces): a 3D version
of their sprites.

Seen in episode 2 (levels 2.2, 2.21, 2.22) and episode 4. Three 2x2 ground enemies side by side
(sprite.json `assemblyLayout`) are the lower ends of two big clusters of long green crystals that
hang down into a V each, the crystals separated by dark seams and lit pale green at their tips.
The clusters carry on above these pieces (that part is other sprites), so the crystals are cut at
the pieces' top edge.

Every crystal is a long prism with a sharp ridge, traced from the sprite: its outline row by row
comes from the runs of pixels between the dark seams, the ridge follows the brightest pixels, and
each facet takes the palette colour of the pixels it covers. A low dark base fills the seams. The
whole object is built once in assembly coordinates and cut into the three pieces with
common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshj-267.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b096 as lib  # noqa: E402

NAME = "assembly-newshj-267"
ROOT = common.repo_root(__file__)
PIECES = ["newshj-267", "newshj-269", "newshj-271"]
# Assembly pixel (0, 0) is the top-left of newshj-267's block (screen 112, 74); the strip of three
# blocks is 72 x 28 px and its centre (screen 148, 88) is the Blender origin.
CX0, CY0 = 148, 88
W, H = 72, 28
G = lib.Grid(W, H)
SEAMS = {1, 32}  # the outline colour and the near-black green between crystals
BASE = 32  # the dark base the crystals stand in


def composite():
    """Every piece's pixels in one W x H grid (-1 transparent) and all their colours."""
    grid = [[-1] * W for _ in range(H)]
    colors = {}
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        colors.update(data["colors"])
        entry = next(e for e in data["assemblyLayout"] if e["model"] == name)
        c0, r0 = entry["cx"] - CX0 + W // 2 - 12, entry["cy"] - CY0 + H // 2 - 14
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[r0 + r][c0 + c] = v
    return grid, colors


def runs(row, keep):
    """Maximal runs [c0, c1] of columns whose pixel passes `keep`."""
    out, start = [], None
    for c, v in enumerate(row + [-1]):
        if keep(v) and start is None:
            start = c
        elif not keep(v) and start is not None:
            out.append((start, c - 1))
            start = None
    return out


def trace_strips(grid):
    """Link each row's runs of crystal pixels to the run above they overlap most: one strip per
    crystal, a list of (row, c0, c1)."""
    strips, active = [], []
    for r, row in enumerate(grid):
        segs = runs(row, lambda v: v >= 0 and v not in SEAMS)
        taken, nxt = set(), []
        for seg in segs:
            best, overlap = None, 0
            for k, strip in enumerate(active):
                if k in taken:
                    continue
                _, a0, a1 = strip[-1]
                o = min(a1, seg[1]) - max(a0, seg[0]) + 1
                if o > overlap:
                    best, overlap = k, o
            if best is None:
                strip = []
                strips.append(strip)
            else:
                taken.add(best)
                strip = active[best]
            strip.append((r, *seg))
            nxt.append(strip)
        active = nxt
    return strips


def luminance(colors, v):
    r, g, b = colors[str(v)]
    return 0.3 * r + 0.59 * g + 0.11 * b


def build(colors, grid):
    coll = common.reset_collection(NAME)
    sprite = {"name": NAME, "colors": colors}
    mats, slot = [], {}

    def mat(index):
        if index not in slot:
            slot[index] = len(mats)
            rough = 0.9 if index == BASE else 0.6
            mats.append(common.palette_material(sprite, index, "nshj267", metallic=0.0, roughness=rough))
        return slot[index]

    bm = bmesh.new()

    # Dark base under each cluster (left of column 36 and right of it), seams included.
    for lo, hi in ((0, 36), (36, W)):
        left, right = [], []
        for r, row in enumerate(grid):
            filled = [c for c in range(lo, hi) if row[c] >= 0 and row[c] != 1]
            if filled:
                left.append((min(filled), r))
                right.append((max(filled) + 1, r))
        rows = [r for _, r in left]
        outline = [(c, r + 0.5) for c, r in left]
        outline[0] = (left[0][0], -1.0)
        bottom = rows[-1] + 1
        outline += [(left[-1][0], bottom), (right[-1][0], bottom)]
        outline += [(c, r + 0.5) for c, r in reversed(right)]
        outline[-1] = (right[0][0], -1.0)
        lib.plate(bm, G, outline, 0.0, 0.05, mat=mat(BASE))

    for strip in trace_strips(grid):
        first, last = strip[0][0], strip[-1][0]
        width = max(c1 - c0 + 1 for _, c0, c1 in strip)
        top = min(0.34, 0.12 + 0.035 * width)
        # Ridge column: the brightness-weighted centre of each row, smoothed down the strip.
        ridge = []
        for r, c0, c1 in strip:
            w = [luminance(colors, grid[r][c]) ** 2 for c in range(c0, c1 + 1)]
            ridge.append(sum((c0 + i) * wi for i, wi in enumerate(w)) / sum(w))
        ridge = [sum(ridge[max(0, i - 1):i + 2]) / len(ridge[max(0, i - 1):i + 2]) for i in range(len(ridge))]

        def height(r):
            h = top * min(1.0, (last - r + 1) / 4)  # the tip slopes down
            if first > 0:
                h *= min(1.0, (r - first + 1) / 3)
            return max(h, 0.07)

        # Sections: (y row, x left edge col, ridge col, x right edge col, ridge height, pixel row).
        secs = []
        for (r, c0, c1), rc in zip(strip, ridge):
            rc = min(max(rc, c0 - 0.2), c1 + 0.2)
            secs.append((r, c0 - 0.5, rc, c1 + 0.5, height(r), r))
        r, l, rc, rr, h, pr = secs[0]
        secs.insert(0, (-1.0 if first == 0 else r - 0.45, l, rc, rr, h * (1.0 if first == 0 else 0.6), pr))
        r, l, rc, rr, h, pr = secs[-1]
        secs.append((r + 0.45, l + 0.15, rc, rr - 0.15, h * 0.45, pr))

        # Each ring: the bottom left corner, N facets up to the ridge and N down again, the bottom
        # right corner. Each facet takes the colour of the pixel under it.
        n = 3
        rings = []
        for r, l, rc, rr, h, _ in secs:
            he = 0.35 * h + 0.03
            y = G.Y(r)
            top = [(l + (rc - l) * k / n, he + (h - he) * k / n) for k in range(n)]
            top += [(rc + (rr - rc) * k / n, h + (he - h) * k / n) for k in range(n + 1)]
            ring = [bm.verts.new((G.X(l), y, 0.0))]
            ring += [bm.verts.new((G.X(x), y, z)) for x, z in top]
            ring.append(bm.verts.new((G.X(rr), y, 0.0)))
            rings.append(ring)
        for i in range(len(rings) - 1):
            a, b = rings[i], rings[i + 1]
            pr = secs[i][5] if i > 0 else secs[1][5]
            _, l, rc, rr, _, _ = secs[i]
            row = grid[pr]

            def px(c):
                c = min(max(c, l + 0.5), rr - 0.5)
                v = row[min(max(int(round(c)), 0), W - 1)]
                return v if v >= 0 and v != 1 else BASE

            xs = [v.co.x * 12 - 0.5 + W / 2 for v in a]  # back to columns
            m = len(a)
            for k in range(m - 1):
                f = bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]))
                f.material_index = mat(px((xs[k] + xs[k + 1]) / 2))
                f.smooth = False
            f = bm.faces.new((a[m - 1], a[0], b[0], b[m - 1]))
            f.material_index = mat(BASE)
        for ring, flip, (_, c0, c1) in ((rings[0], True, strip[0]), (rings[-1], False, strip[-1])):
            f = bm.faces.new(list(reversed(ring)) if flip else ring)
            r = strip[0][0] if flip else strip[-1][0]
            f.material_index = mat(grid[r][(c0 + c1) // 2])

    return lib.to_object(NAME, bm, mats, coll)


def composite_png(grid, colors, out):
    """The whole object's sprite as one image, padded to the 24:28 shape render_preview expects
    for size 6 (72 x 84 px, the strip in the middle)."""
    import numpy as np
    img = np.zeros((84, 72, 4), dtype=np.float32)
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if v >= 0:
                img[28 + r, c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 72, 84, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    grid, colors = composite()
    obj = build(colors, grid)
    layout = []
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        entry = next(e for e in data["assemblyLayout"] if e["model"] == name)
        layout.append((name, entry["cx"] - CX0, entry["cy"] - CY0))
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_args()
    if out:
        import tempfile
        ref = composite_png(grid, colors, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=6, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
