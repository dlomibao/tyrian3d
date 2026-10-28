"""Billowing fireball (newshk.shp frames 13, 15, 17, assembly of 3 pieces): a 3D version of its sprites.

Seen in episodes 3 (level 3.12) and 4 (level 4.4). Three 2x2 pieces side by side make one
72x28 px dome of fire bursting up out of the top of a machine (the newsho pieces below it,
modelled elsewhere): a lumpy red and orange rim, yellow billows and a white-hot heart. Its
bottom edge is where it meets the machine, so it is cut flat there; the top rounds off.

The fire is one mound traced pixel by pixel from the sprite: a height field over the sprite's
pixels, standing on a flat base at z = 0. Its height is half an ellipsoid centred on the base
line under the white core (a round arc in both elevations, about 22 px over the core), rolled off
along the ragged outline to a low red rim about 1-2 px tall, and along the front (the base line,
where it meets the machine) to a low rounded wall. On top of that, each pixel rises or sinks a little with how much brighter or
darker it is than the fire around it, so the yellow flame tongues and the orange tendrils show
in relief. Every pixel's top face takes its own palette colour, so the top view matches the
sprite's colours.

The pieces are built straight from the height field (each its own 24x28 px block of pixels),
with normals taken from the whole field, so the mound is smooth across the piece joins. Each
piece has one frame.

Run: blender --background --python assets/blender/enemies/assembly-newshk-17.py [-- --preview out.png]
(the preview is the whole fireball; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b010 as lib  # noqa: E402

NAME = "assembly-newshk-17"
ROOT = common.repo_root(__file__)
# (piece, screen cx, cy) from sprite.json assemblyLayout.
PIECES = [("newshk-13", 92, 71), ("newshk-15", 116, 71), ("newshk-17", 140, 71)]
PX = 1 / 12
DOME_PX = 24.0  # height of the dome's crown over the base, in sprite px (about 22 after the rim and front roll-offs)
RIM_PX = 1.2  # height of the outermost red pixels
# The dome is half an ellipsoid standing on the base line (the sprite's bottom edge), centred on
# the white core: semi-axes in sprite px across (A) and up the sprite (B), a little larger than
# the fire so its ragged outline stays inside the curved surface.
DOME_A_PX, DOME_B_PX = 33.0, 27.0
RIM_ROLL_PX = 5.0  # the ragged outline rolls off over this many px inwards
FRONT_ROLL_PX = 12.0  # the front (the base line, where it meets the machine) rounds off over this many rows
RELIEF_PX = 0.45  # rise per palette step brighter than the fire around a pixel
RELIEF_MAX_PX = 1.6
SMOOTH_PASSES = 2
# Fire shades with a material each (every pixel takes the closest): dark red rim, red, orange,
# three yellows, pale yellow and the white core. The sprite's other shades are a step away.
SHADES = [116, 119, 121, 123, 124, 125, 126, 127]
GLOW_LO, GLOW_HI = 0.2, 0.5  # emission strength of the dark red rim and of the white core


def lab(rgb):
    """sRGB 0-255 to CIE Lab (D65)."""
    c = np.array(rgb, dtype=float) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]) @ c
    f = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(f > 0.008856, np.cbrt(f), 7.787 * f + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def nearest_shade(v, colors):
    """The SHADES entry closest in colour to palette index v."""
    return min(SHADES, key=lambda s: np.linalg.norm(lab(colors[str(v)]) - lab(colors[str(s)])))


def heights(grid):
    """Height (sprite px) of each pixel centre; NaN outside the fire."""
    g = np.array(grid)
    h, w = g.shape
    inside = g >= 0
    # Outside pixels: transparent ones plus a ring above, left and right of the grid. Nothing
    # below: the bottom edge is a cut through the fire.
    out = [(r, c) for r in range(h) for c in range(w) if not inside[r, c]]
    out += [(-1, c) for c in range(-1, w + 1)] + [(r, -1) for r in range(h)] + [(r, w) for r in range(h)]
    out = np.array(out, dtype=float)
    rr, cc = np.nonzero(inside)
    d = np.sqrt(((rr[:, None] - out[None, :, 0]) ** 2 + (cc[:, None] - out[None, :, 1]) ** 2).min(axis=1)) - 0.5
    # Half an ellipsoid centred on the base line under the white core: a round arc across (the
    # front elevation) and up the sprite (the side elevation), highest over the core.
    cols = np.nonzero(inside.any(axis=0))[0]
    xc = (cols.min() + cols.max() + 1) / 2
    ex = (cc + 0.5 - xc) / DOME_A_PX
    ey = (h - (rr + 0.5)) / DOME_B_PX
    e = np.sqrt(np.clip(1.0 - ex ** 2 - ey ** 2, 0.0, 1.0))
    # The ragged outline rolls off (a quarter-round on its inner side) down to the low red rim.
    sr = np.clip(d / RIM_ROLL_PX, 0.0, 1.0)
    rim = 1.0 - (1.0 - sr) ** 2
    # The front (the cut where it meets the machine) rounds off too, to a low wall.
    sf = np.clip((h - rr - 0.5) / FRONT_ROLL_PX, 0.0, 1.0)
    front = np.sqrt(1.0 - (1.0 - sf) ** 2)
    z = np.full((h, w), np.nan)
    z[rr, cc] = RIM_PX + (DOME_PX - RIM_PX) * e * rim * front
    z = smooth(z, inside, SMOOTH_PASSES)
    # Relief: brighter than the surroundings rises, darker sinks (flame tongues, tendrils).
    v = np.where(inside, g, np.nan).astype(float)
    around = smooth(v, inside, 4)
    relief = np.clip(RELIEF_PX * (v - around), -RELIEF_MAX_PX, RELIEF_MAX_PX)
    relief = smooth(relief, inside, 1)
    return np.where(inside, z + relief, np.nan)


def smooth(a, inside, passes):
    """Average each inside pixel with its inside 4-neighbours, `passes` times."""
    a = a.copy()
    h, w = a.shape
    for _ in range(passes):
        acc = np.where(inside, a, 0.0) * 2
        n = inside.astype(float) * 2
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            sh = np.full((h, w), 0.0)
            m = np.zeros((h, w), dtype=bool)
            r0, r1 = max(0, dr), h + min(0, dr)
            c0, c1 = max(0, dc), w + min(0, dc)
            sh[r0 - dr:r1 - dr, c0 - dc:c1 - dc] = np.nan_to_num(a[r0:r1, c0:c1])
            m[r0 - dr:r1 - dr, c0 - dc:c1 - dc] = inside[r0:r1, c0:c1]
            acc += np.where(m, sh, 0.0)
            n += m
        a = np.where(inside, acc / np.maximum(n, 1), np.nan)
    return a


def corner_heights(z, inside):
    """Height (sprite px) at each pixel corner: the mean of the fire pixels touching it."""
    h, w = z.shape
    zc = np.full((h + 1, w + 1), np.nan)
    for r in range(h + 1):
        for c in range(w + 1):
            vals = [z[q, p] for q in (r - 1, r) for p in (c - 1, c)
                    if 0 <= q < h and 0 <= p < w and inside[q, p]]
            if vals:
                zc[r, c] = sum(vals) / len(vals)
    return zc


def corner_normals(zc):
    """Surface normal at each corner from the height field (central differences)."""
    hc, wc = zc.shape
    nrm = np.zeros((hc, wc, 3))
    for r in range(hc):
        for c in range(wc):
            if np.isnan(zc[r, c]):
                continue

            def slope(a, b, step):
                if a is not None and b is not None:
                    return (b - a) / (2 * step)
                if a is not None:
                    return (zc[r, c] - a) / step
                if b is not None:
                    return (b - zc[r, c]) / step
                return 0.0

            def at(q, p):
                if 0 <= q < hc and 0 <= p < wc and not np.isnan(zc[q, p]):
                    return zc[q, p]
                return None

            dzdx = slope(at(r, c - 1), at(r, c + 1), 1.0)
            dzdy = -slope(at(r - 1, c), at(r + 1, c), 1.0)  # rows run down the sprite (-Y)
            n = np.array([-dzdx, -dzdy, 1.0])
            nrm[r, c] = n / np.linalg.norm(n)
    return nrm


def build_piece(name, grid, zc, nrm, c_lo, c_hi, mats, mat_of, coll, w, h):
    """One piece: the fire pixels in columns c_lo..c_hi-1, centred on its own block."""
    xc = (c_lo + c_hi) / 2  # the piece centre, as a grid column edge
    bm = bmesh.new()
    top = {}

    def tv(r, c):
        if (r, c) not in top:
            top[(r, c)] = bm.verts.new(((c - xc) * PX, (h / 2 - r) * PX, zc[r, c] * PX))
        return top[(r, c)]

    loop_normals = {}  # face index -> per-loop normals (top faces only)
    faces = []

    def inside(r, c):
        return 0 <= r < h and c_lo <= c < c_hi and grid[r][c] >= 0

    for r in range(h):
        for c in range(c_lo, c_hi):
            v = grid[r][c]
            if v < 0:
                continue
            corners = [(r + 1, c), (r + 1, c + 1), (r, c + 1), (r, c)]  # counter-clockwise from above
            f = bm.faces.new([tv(*k) for k in corners])
            f.material_index = mat_of[v]
            f.smooth = True
            faces.append((f, [nrm[k] for k in corners]))
            # Walls on every edge whose neighbour isn't fire in this piece: down to the base.
            for (dr, dc), (a, b) in (((0, -1), ((r, c), (r + 1, c))), ((0, 1), ((r + 1, c + 1), (r, c + 1))),
                                     ((-1, 0), ((r, c + 1), (r, c))), ((1, 0), ((r + 1, c), (r + 1, c + 1)))):
                if inside(r + dr, c + dc):
                    continue
                ta, tb = tv(*a), tv(*b)
                ba = bm.verts.new((ta.co.x, ta.co.y, 0.0))
                bb = bm.verts.new((tb.co.x, tb.co.y, 0.0))
                wf = bm.faces.new((ba, bb, tb, ta))
                wf.material_index = mat_of[v]
                wf.smooth = False
    # Base: one quad per row run (never seen; closes the solid).
    for r in range(h):
        c = c_lo
        while c < c_hi:
            if grid[r][c] < 0:
                c += 1
                continue
            c0 = c
            while c < c_hi and grid[r][c] >= 0:
                c += 1
            x0, x1 = (c0 - xc) * PX, (c - xc) * PX
            y0, y1 = (h / 2 - r - 1) * PX, (h / 2 - r) * PX
            bf = bm.faces.new([bm.verts.new(p) for p in ((x0, y0, 0), (x0, y1, 0), (x1, y1, 0), (x1, y0, 0))])
            bf.material_index = mat_of[grid[r][c0]]
            bf.smooth = False
    bm.faces.index_update()
    idx = {f.index: ns for f, ns in faces}
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    # Custom normals from the whole field, so the shading runs on across the piece joins.
    custom = []
    for poly in mesh.polygons:
        ns = idx.get(poly.index)
        for k, li in enumerate(poly.loop_indices):
            custom.append(tuple(ns[k]) if ns is not None else tuple(poly.normal))
    mesh.normals_split_custom_set(custom)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def main():
    grid, colors, (cx0, cy0), w, h = lib.assembly_grid(ROOT, PIECES)
    sprite = {"name": NAME, "colors": colors}
    coll = common.reset_collection(NAME)
    g = np.array(grid)
    inside = g >= 0
    z = heights(grid)
    zc = corner_heights(z, inside)
    nrm = corner_normals(zc)
    left = cx0 - w / 2
    parts = {}
    for m, cx, cy in PIECES:
        c_lo = int(cx - 12 - left)
        near = {v: nearest_shade(v, colors) for line in grid for v in line[c_lo:c_lo + 24] if v >= 0}
        used = sorted(set(near.values()))
        # Fire: not metal, no shine, and it glows in its own colour. The glow stays low (the scene's
        # light already brightens it) so each shade shows as itself from the game camera; stronger
        # glows wash the yellows and oranges out to white.
        mats = [common.palette_material(sprite, i, NAME, metallic=0.0, roughness=0.9,
                                        emission_strength=GLOW_LO + (GLOW_HI - GLOW_LO) * (i - 116) / 11)
                for i in used]
        mat_of = {v: used.index(i) for v, i in near.items()}
        parts[m] = build_piece(m, grid, zc, nrm, c_lo, c_lo + 24, mats, mat_of, coll, w, h)
        parts[m].location = ((cx - cx0) * PX, -(cy - cy0) * PX, 0.0)  # for the preview
    for m, _, _ in PIECES:
        data = common.load_sprite(ROOT, m)
        piece = parts[m]
        loc = piece.location.copy()
        piece.location = (0.0, 0.0, 0.0)
        common.export_sprite_model(ROOT, [piece], f"enemies/{m}", data["sprites"])
        piece.location = loc
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        size = math.ceil(max(w / 24, h / 28)) * 2
        ref = lib.grid_png(grid, colors, Path(tempfile.mkdtemp()) / "assembly.png", size * 12, size * 14)
        common.render_preview(list(parts.values()), str(out), str(ref), size=size, view_px=480)
        for m, _, _ in PIECES:
            data = common.load_sprite(ROOT, m)
            img = ROOT / "reference" / "models" / m / data["frames"][0]["image"]
            loc = parts[m].location.copy()
            parts[m].location = (0.0, 0.0, 0.0)
            common.render_preview([parts[m]], str(out.parent / f"{m}.png"), img, size=2)
            parts[m].location = loc


if __name__ == "__main__":
    main()
