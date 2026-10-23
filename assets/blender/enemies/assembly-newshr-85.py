"""Domed city (newshr.shp, nine 2x2 pieces in a 3x3 block): a 3D version of its sprites.

Seen in episode 3 (levels 3.4 and 3.19). Nine ground enemies side by side make one 72x84 px
structure: an egg-shaped purple glass dome (narrow end up the screen, a white glare at its upper
left and a bright rim down its right side) over a cluster of blue-grey skyscrapers, standing on
cobbled brown ground with a dark shadow ring around the dome's foot.

    newshr-5   newshr-7   newshr-9        (top row: the dome's back, transparent corners)
    newshr-43  newshr-45  newshr-47       (middle: the city, ground at the sides)
    newshr-81  newshr-83  newshr-85       (bottom: the dome's front rim and the ground)

The glass is a shell from the dome's foot up to a window over the city (the sprite shows the
towers through it), so its back half stands as a curved wall behind the towers and its sides and
front are a lower rim. Shell faces take the purple shade the sprite has at that spot. The towers
are boxes on the sprite's building blocks, tallest at the back (the sprite draws them in an
oblique view, so each block's drawn area is its footprint here), coloured by the block's average
shade. The ground is a low slab with cobbles where the sprite's ground is brown. The whole thing is
built once in assembly coordinates and cut into the nine pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshr-85.py [-- --preview out.png]
(the preview is the whole city; each piece also gets <piece>.png next to it).
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newshr-85"
ROOT = common.repo_root(__file__)
GRID = [["newshr-5", "newshr-7", "newshr-9"],
        ["newshr-43", "newshr-45", "newshr-47"],
        ["newshr-81", "newshr-83", "newshr-85"]]
PIECES = [n for row in GRID for n in row]
W, H = 72, 84  # assembly size in px; (0, 0) is the top-left corner of newshr-5
TAG = "nshr85"


def X(c):
    """Assembly pixel edge column (fractions allowed) to Blender X; the block's centre is 0."""
    return (c - W / 2) / 12


def Y(r):
    """Assembly pixel edge row to Blender Y (sprite up is +Y)."""
    return (H / 2 - r) / 12


# --- the sprite as one index map ---------------------------------------------------------------

def index_map():
    """Every piece's first frame placed in the 72x84 block: rows of palette indices (-1 empty)."""
    m = [[-1] * W for _ in range(H)]
    for gr, names in enumerate(GRID):
        for gc, name in enumerate(names):
            frame = common.load_sprite(ROOT, name)["frames"][0]
            for r, row in enumerate(frame["pixels"]):
                for c, v in enumerate(row):
                    m[gr * 28 + r][gc * 24 + c] = v
    return m


def sample(m, c, r, keep, radius=1, remap=None):
    """Mean of the indices that `keep` accepts around pixel (c, r), or None. `remap` maps indices
    from another ramp (the glare's greys) onto the one being averaged."""
    vals = []
    for rr in range(int(r) - radius, int(r) + radius + 1):
        for cc in range(int(c) - radius, int(c) + radius + 1):
            if 0 <= rr < H and 0 <= cc < W and keep(m[rr][cc]):
                v = m[rr][cc]
                vals.append(remap.get(v, v) if remap else v)
    return sum(vals) / len(vals) if vals else None


# --- outlines (pixel edges) --------------------------------------------------------------------

# The dome's outer edge, (row, left column, right column + 1), read off the sprite's outline.
EGG = [(2.2, 27, 36), (3, 24.5, 39), (5, 20.5, 43), (7, 17.5, 46), (9, 15.5, 48), (11, 13.5, 50),
       (13, 11.5, 52), (15, 10.5, 53), (17, 9.5, 54), (19, 8.5, 55), (21, 7.5, 56), (23, 6.5, 57),
       (25, 5.5, 58), (27, 4.5, 59), (30, 3.5, 60), (34, 2.5, 61), (40, 1.5, 62), (44, 1.5, 62.5),
       (48, 1.5, 61.5), (51, 2.5, 61), (54, 3.5, 59.5), (56, 5, 58.5), (58, 7.5, 57.5),
       (60, 10.5, 55), (62, 13.5, 52.5), (64, 17, 50), (66, 23, 46), (67.6, 30, 39)]

# The window in the glass over the city (counter-clockwise from the top of the central tower),
# the inner edge of the purple in the sprite.
WINDOW = [(35, 9), (29.5, 9), (29.5, 17), (26, 20), (20, 21), (19, 26), (15.5, 27), (14.5, 23.5),
          (10, 23.5), (9.5, 30), (8.5, 40), (8.5, 48), (10, 54), (13, 57.5), (18, 59.5), (24, 61.5),
          (30, 62), (37, 63), (42, 62.5), (47, 60), (51, 56), (54, 52), (55, 46), (55, 39.5),
          (51, 37), (47, 33), (45.5, 27), (45, 20), (40, 19.5), (37.5, 19.5), (36, 12)]

CENTRE = (32.0, 37.0)  # the dome's middle, in pixel edges


def egg_outline():
    left = [(l, r) for r, l, _ in EGG]
    right = [(rr, r) for r, _, rr in reversed(EGG)]
    return left + right  # down the left side, up the right side


def ray_hit(poly, centre, angle):
    """Farthest point where a ray from `centre` at `angle` crosses the closed polygon."""
    cx, cy = centre
    dx, dy = math.cos(angle), math.sin(angle)
    best = None
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-9:
            continue
        t = ((x1 - cx) * ey - (y1 - cy) * ex) / den
        u = ((x1 - cx) * dy - (y1 - cy) * dx) / den
        if t > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t > best):
            best = t
    return (cx + dx * best, cy + dy * best)


def inside(poly, x, y):
    hit = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


# --- geometry ----------------------------------------------------------------------------------

def box(bm, c0, c1, r0, r1, z0, z1, side_mat, top_mat):
    """A box over pixel edges c0..c1, r0..r1, from z0 to z1, with its own top material."""
    xs, ys = (X(c0), X(c1)), (Y(r1), Y(r0))
    v = [bm.verts.new((xs[i], ys[j], z)) for z in (z0, z1) for j in (0, 1) for i in (0, 1)]
    # v index: bottom 0..3 (x0y0, x1y0, x0y1, x1y1), top 4..7
    quads = [((0, 2, 3, 1), side_mat), ((4, 5, 7, 6), top_mat), ((0, 1, 5, 4), side_mat),
             ((1, 3, 7, 5), side_mat), ((3, 2, 6, 7), side_mat), ((2, 0, 4, 6), side_mat)]
    for idx, mat in quads:
        f = bm.faces.new([v[i] for i in idx])
        f.material_index = mat
        f.smooth = False


def stone(bm, rng, c, r, z, rx_px, ry_px, h, mat, sides=7):
    """A cobble: an irregular polygon with a bevelled flat top, centred on pixel edges (c, r)."""
    a0 = rng.random() * math.tau
    base, top = [], []
    for i in range(sides):
        a = a0 + math.tau * i / sides
        k = rng.uniform(0.8, 1.1)
        x, y = math.cos(a) * rx_px * k / 12, math.sin(a) * ry_px * k / 12
        base.append(bm.verts.new((X(c) + x, Y(r) + y, z)))
        top.append(bm.verts.new((X(c) + x * 0.65, Y(r) + y * 0.65, z + h)))
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(base)))]
    for i in range(sides):
        j = (i + 1) % sides
        faces.append(bm.faces.new((base[i], base[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat
        f.smooth = False


def slab_px(bm, poly, z0, z1, mat):
    """An extruded outline of pixel-edge points, z0 to z1."""
    pts = [(X(c), Y(r)) for c, r in poly]
    # common.slab wants counter-clockwise seen from above; normals get recalculated anyway.
    n = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = False


# --- the city ----------------------------------------------------------------------------------

# Building blocks: (col0, col1, row0, row1, height). Their drawn facades are their footprints.
TOWERS = [
    (29.5, 35, 9, 24, 0.66),  # the central tower, tallest, at the back
    (26, 36, 21.5, 37, 0.46),  # the block at its foot
    (37.5, 45, 19.5, 34, 0.54),  # the right tower
    (36, 45, 33, 41, 0.36),
    (10, 15, 23.5, 41, 0.48),  # the left tower
    (15, 19, 28, 40, 0.3),
    (19, 26, 21, 33, 0.5),
    (19, 23, 33, 41, 0.38),
    (31, 36, 37, 47, 0.3),
    (26.5, 30.5, 37.5, 47, 0.32),  # the light front tower
    (23.5, 26.5, 39.5, 48, 0.24),
    (33, 45, 41, 51, 0.24),
    (44.5, 50, 30, 51, 0.3),
    (49.5, 55, 38.5, 52, 0.18),
    (9, 15.5, 41, 51, 0.22),
    (15, 20.5, 40, 48, 0.22),
    (20.5, 26, 33, 41, 0.28),
    (15, 24, 48, 57, 0.14),
    (24, 33, 47, 60, 0.12),
    (33, 41, 51, 61, 0.12),
    (41, 51, 50, 59, 0.12),
]


def build(sprite, m):
    coll = common.reset_collection(NAME)
    glass = dict(metallic=0.25, roughness=0.15)
    rock = dict(metallic=0.0, roughness=0.9)
    city = dict(metallic=0.45, roughness=0.35)
    pal = lambda i, **kw: common.palette_material(sprite, i, TAG, **kw)  # noqa: E731
    glass_idx = [82, 84, 86, 88, 90, 92, 95]
    city_idx = [97, 99, 100, 101, 102, 103, 105, 107]
    ground_idx = [16, 17, 18, 19, 20]
    mats = ([pal(i, **glass) for i in glass_idx] + [pal(i, **city) for i in city_idx]
            + [pal(i, **rock) for i in ground_idx])
    G0, C0, S0 = 0, len(glass_idx), len(glass_idx) + len(city_idx)

    def nearest(idx_list, base, value):
        k = min(range(len(idx_list)), key=lambda i: abs(idx_list[i] - value))
        return base + k

    glare = {9: 91, 10: 92, 11: 92, 13: 95, 14: 95, 109: 95, 110: 95}  # greys in the glare
    is_glass = lambda v: 80 <= v <= 95 or v in glare  # noqa: E731

    def glass_mat(c, r):
        v = sample(m, c, r, is_glass, remap=glare)
        if v is None:
            return G0 + 1
        return nearest(glass_idx, G0, v)

    bm = bmesh.new()

    # Ground: a low slab under the bottom two rows of pieces and the city floor in the window.
    slab_px(bm, [(0, 28), (0, 84), (72, 84), (72, 28)], 0.0, 0.03, S0)
    slab_px(bm, WINDOW, 0.0, 0.035, C0)

    # Cobbles where the sprite's ground is brown, outside the dome.
    egg = egg_outline()
    rng = random.Random(85)
    step = 4.3
    r = 28 + step / 2
    while r < H:
        c = (rng.random() * step) / 2
        while c < W:
            cc, rr = c + rng.uniform(-0.8, 0.8), r + rng.uniform(-0.8, 0.8)
            v = sample(m, cc, rr, lambda x: 16 <= x <= 20, radius=1)
            if v is not None and not inside(egg, cc, rr) and 0 < cc < W and 28 < rr < H:
                stone(bm, rng, cc, rr, 0.03, rng.uniform(2.3, 2.9), rng.uniform(1.9, 2.4),
                      rng.uniform(0.025, 0.04), nearest(ground_idx, S0, v + 1.2))
            c += step
        r += step

    # The glass shell from the dome's foot up to the window.
    N, K = 96, 6
    Hd = 0.62
    outer, inner = [], []
    for i in range(N):
        a = 2 * math.pi * i / N
        outer.append(ray_hit(egg, CENTRE, a))
        inner.append(ray_hit(WINDOW, CENTRE, a))

    def dome_z(r_norm):
        return Hd * max(0.0, 1 - r_norm * r_norm) ** 0.7

    rings = []
    rings.append([bm.verts.new((X(o[0]), Y(o[1]), 0.0)) for o in outer])  # foot
    for k in range(K + 1):
        t = k / K
        ring = []
        for o, n in zip(outer, inner):
            p = (o[0] + (n[0] - o[0]) * t, o[1] + (n[1] - o[1]) * t)
            ro = math.dist(o, CENTRE)
            rn = math.dist(p, CENTRE) / ro if ro else 0
            ring.append(bm.verts.new((X(p[0]), Y(p[1]), max(0.05, dome_z(rn)))))
        rings.append(ring)
    rings.append([bm.verts.new((X(n[0]), Y(n[1]), 0.035)) for n in inner])  # window floor
    for k in range(len(rings) - 1):
        r0, r1 = rings[k], rings[k + 1]
        for i in range(N):
            j = (i + 1) % N
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            if 1 <= k < K + 1:  # the curved top: the sprite's shade at the face's middle
                cx = sum(v.co.x for v in f.verts) / 4 * 12 + W / 2
                cy = H / 2 - sum(v.co.y for v in f.verts) / 4 * 12
                f.material_index = glass_mat(cx, cy)
                f.smooth = True
            else:  # the foot and the cut edge over the city
                f.material_index = G0 + 1
                f.smooth = False

    # The towers, coloured by their block's average shade (outline pixels left out).
    for c0, c1, r0, r1, h in TOWERS:
        vals = [m[rr][cc] for rr in range(int(r0), int(math.ceil(r1))) for cc in range(int(c0), int(math.ceil(c1)))
                if 96 <= m[rr][cc] <= 109]
        avg = sum(vals) / len(vals) if vals else 100
        top = nearest(city_idx, C0, avg - 1)
        side = nearest(city_idx, C0, min(avg, 100) - 1)
        light = nearest(city_idx, C0, avg + 5)
        box(bm, c0 + 0.45, c1 - 0.45, r0 + 0.45, r1 - 0.45, 0.035, h, side, top)
        # The lit roof edge at the back and the lit corner down the left, as the sprite draws them.
        box(bm, c0 + 0.45, c1 - 0.45, r0 + 0.45, r0 + 1.6, h, h + 0.02, light, light)
        box(bm, c0 + 0.45, c0 + 1.4, r0 + 1.6, r1 - 0.45, h, h + 0.012, light, light)

    return to_object(NAME, bm, mats, coll)


def to_object(name, bm, mats, coll):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in mats:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def merged_sprite():
    """newshr-85's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newshr-85")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def layout():
    """(piece, cx, cy) in assembly pixels relative to the block's centre, as split_assembly wants."""
    return [(name, gc * 24 + 12 - W / 2, gr * 28 + 14 - H / 2)
            for gr, names in enumerate(GRID) for gc, name in enumerate(names)]


def composite_png(m, colors, out):
    """The whole block's sprite as one image, 72 x 84 px, already the 24:28 shape render_preview expects."""
    import numpy as np
    img = np.zeros((H, W, 4), dtype=np.float32)
    for r in range(H):
        for c in range(W):
            v = m[r][c]
            if v >= 0:
                img[r, c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    m = index_map()
    obj = build(sprite, m)
    pieces = common.split_assembly(obj, layout())
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    print(f"whole: {len(obj.data.polygons)} faces")
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(m, sprite["colors"], Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=6, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
