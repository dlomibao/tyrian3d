"""Giant tongue (newsh^.shp frames 267 and 269, an assembly of 2 pieces): a 3D version of their
sprites.

Seen in episode 4 (level 4.25). Two 2x2 enemies one above the other make one 24x56 px tongue
(sprite.json `assemblyLayout`): a broad, thick red tongue with a dark furrow down its middle
(column 11), a pale highlight ridge right of it and glossy patches on its left, rounding to its
tip at the bottom; its torn root at the top is lumpy, with bloody red flesh (indices 114-119)
showing through.

The tongue is lofted down Y from the sprite's own per-row edges with a flattened cross-section,
with the furrow, ridge and glossy patch as thin strips on its top; the root is a few lumps whose
faces take the shade of the sprite pixel under them, with the bloody flesh lying on them. Built once in assembly coordinates and cut into the two pieces with
common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh-caret-269.py
[-- --preview out.png] (the preview is the whole tongue; each piece also gets <piece>.png).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b046 as lib  # noqa: E402

NAME = "assembly-newsh-caret-269"
ROOT = common.repo_root(__file__)
PIECES = ["newsh-caret-267", "newsh-caret-269"]
# Assembly grid 24 x 56 px: newsh-caret-267 is rows 0-27, newsh-caret-269 rows 28-55.
G = lib.Grid(24, 56)
LAYOUT = [("newsh-caret-267", 0, -14), ("newsh-caret-269", 0, 14)]  # piece centres, px from origin
OUTLINE = (1, 64)  # near-black outline pixels
FLESH = [65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 78]
BLOOD = [114, 115, 116, 117, 119]


def extents(pixels):
    """Per row, the leftmost and rightmost non-outline columns."""
    out = {}
    for r, line in enumerate(pixels):
        cs = [c for c, v in enumerate(line) if v >= 0 and v not in OUTLINE]
        if cs:
            out[r] = (min(cs), max(cs))
    return out


def build(colors, pixels):
    coll = common.reset_collection(NAME)
    sprite = {"name": NAME, "colors": colors}
    used = FLESH + BLOOD
    mats = [common.palette_material(sprite, i, "nshc269", metallic=0.0,
                                    roughness=0.3 if i in BLOOD else 0.42) for i in used]
    slot = {i: k for k, i in enumerate(used)}
    bm = bmesh.new()
    ext = extents(pixels)

    # The tongue: per-row edges from the sprite (smoothed), rows 10-48, thick in the middle,
    # thinning to the tip.
    rows = [9.6, 10.5, 11.5, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 43,
            44.5, 46, 47, 47.8]
    edges = []
    for r in rows:
        lo, hi = ext[int(round(r))]
        edges.append((2.5, 19.5) if r < 10 else (lo, hi))
    los = lib.smooth_profile([e[0] for e in edges], passes=2)
    his = lib.smooth_profile([e[1] for e in edges], passes=2)
    sections, shape = [], {}
    for r, lo, hi in zip(rows, los, his):
        hx = (hi - lo + 1) / 2 * lib.PX
        t = (r - 9.6) / (48.6 - 9.6)
        hz = 0.1 + 0.1 * min(1.0, t / 0.15) - 0.11 * max(0.0, (t - 0.65) / 0.35) ** 1.5
        sections.append((G.Y(r), G.X((lo + hi) / 2), hx, hz, 0.0))
        shape[r] = (G.X((lo + hi) / 2), hx, hz)
    sections.append((G.Y(48.6), G.X(11.2), 0.0, 0.0, 0.0))
    power = 0.75
    lib.loft_y(bm, sections, sides=28, mat=slot[71], power=power)

    def top(r, x):
        """Height of the tongue's top surface over row r, X x."""
        r0 = max(k for k in shape if k <= r) if r >= rows[0] else rows[0]
        r1 = min((k for k in shape if k >= r), default=rows[-1])
        f = 0 if r1 == r0 else (r - r0) / (r1 - r0)
        xc, hx, hz = (a + (b - a) * f for a, b in zip(shape[r0], shape[r1]))
        u = min(1.0, abs(x - xc) / hx)
        return hz * (1 - u ** (2 / power)) ** (power / 2)

    def strip(col, r0, r1, half_px, hz, mat, step=2.0, lift=-0.3):
        """A thin strip lying on the top surface down column `col` from row r0 to r1, its width
        tapering at both ends."""
        x = G.X(col)
        secs = [(G.Y(r0 - 0.5), x, 0.0, 0.0, top(r0, x))]
        r = r0
        while r <= r1:
            taper = min(1.0, (r - r0 + 1) / 3, (r1 - r + 1) / 3)
            secs.append((G.Y(r), x, half_px * lib.PX * taper, hz, top(r, x) + hz * lift))
            r += step
        secs.append((G.Y(r1 + 0.5), x, 0.0, 0.0, top(r1, x)))
        lib.loft_y(bm, secs, sides=6, mat=mat)

    # The dark furrow down column 11, the pale ridge right of it (column 14) and a glossy patch on
    # the left bulge (columns 4-8, rows 13-21).
    strip(11.0, 12, 44, 0.8, 0.018, slot[67], lift=0.0)
    strip(14.0, 19, 33, 0.8, 0.025, slot[74])
    zl = top(17.0, G.X(5.8))
    lib.ellipsoid(bm, (G.X(5.8), G.Y(17.0), zl - 0.012), (2.2 * lib.PX, 4.2 * lib.PX, 0.025), segments=12, rings=6,
                  mat=slot[73])

    # The torn root: a broad lump across the top, a knob above it (columns 11-15, rows 2-5) and a
    # lobe on the left (columns 2-6, rows 5-11).
    flesh = lib.ellipsoid(bm, (G.X(10.6), G.Y(8.0), 0.03), (7.4 * lib.PX, 3.6 * lib.PX, 0.15), segments=16, rings=8,
                           mat=slot[67])
    flesh += lib.ellipsoid(bm, (G.X(13.2), G.Y(4.4), 0.03), (2.9 * lib.PX, 2.2 * lib.PX, 0.11), segments=12, rings=6,
                           mat=slot[69])
    flesh += lib.ellipsoid(bm, (G.X(4.4), G.Y(8.4), 0.02), (2.6 * lib.PX, 3.2 * lib.PX, 0.13), segments=12, rings=6,
                           mat=slot[67])
    # Bloody flesh showing through the tears, lying on the root.
    blood = []
    for c, r, rx, ry, z in ((3.6, 9.6, 2.3, 2.2, 0.11), (10.0, 8.4, 2.6, 3.0, 0.15), (15.0, 6.6, 1.9, 2.0, 0.12)):
        blood += lib.ellipsoid(bm, (G.X(c), G.Y(r), z), (rx * lib.PX, ry * lib.PX, 0.045), segments=12, rings=6,
                               mat=slot[117])

    groups = [67, 70, 73]

    def shade_flesh(vals):
        vals = [v for v in vals if v in FLESH]
        if not vals:
            return None
        m = sum(vals) / len(vals) + 0.5
        return slot[min(groups, key=lambda i: abs(i - m))]

    def shade_blood(vals):
        reds = [v for v in vals if v in BLOOD]
        if not reds:
            return shade_flesh(vals)
        return slot[119] if 119 in reds else slot[117]

    lib.paint(flesh, G, pixels, shade_flesh, spread=0.4)
    lib.paint(blood, G, pixels, shade_blood, spread=0.3)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    pixels, colors = lib.assemble_pixels(ROOT, [("newsh-caret-267", 0, 0), ("newsh-caret-269", 0, 28)])
    obj = build(colors, pixels)
    pieces = common.split_assembly(obj, LAYOUT)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        out = Path(out)
        ref = lib.pixels_png(pixels, colors, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
