"""Grey shield ship (newsh9.shp, assembly of 4 pieces): a 3D version of its sprites.

Seen in episode 4 (level 4.40). Four 2x2 enemies make one 48x56 px craft (sprite.json
`assemblyLayout`): a grey shield-shaped hull, square at the top and rounding to a point at the
bottom, with a raised cabin carrying a gridded blue window, blue glass on both shoulders, two
blue lamps and a glowing blue channel down the keel to the tip. newsh9-92 and newsh9-94 (the
lower pieces) have three frames that only change the channel's colours, so one model covers them
and its channel material takes the brighter shade on frames 130/132 and 282/284 (D17).

The craft is built whole in assembly coordinates (left half mirrored about its axis, the edge
between pixel columns 23 and 24), then cut into the four pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-92.py [-- --preview out.png]
(the preview is the whole craft; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b019 as lib  # noqa: E402

NAME = "assembly-newsh9-92"
ROOT = common.repo_root(__file__)
PIECES = ["newsh9-92", "newsh9-94", "newsh9-244", "newsh9-246"]
# Assembly pixel (0, 0) is screen (135, -23); the 48 x 56 px craft's centre (screen 159, 5) is
# the Blender origin.
CENTRE = (159, 5)
G = lib.Grid(48, 56)
AXIS = 24  # pixel edge of the mirror axis


# The hull is a dome: everything built below on a flat base is lifted by DOME (px) times a profile
# of the distance (px) from the hull's side outline, easing up (a parabola) over FALL px
# from the rim to a plateau where the cabin and keel sit; the underside drops by BELLY times that.
DOME, FALL, BELLY = 6.5, 10.0, 0.5
CAB = 2.5 / 12  # the window deck stands this far (units) above the keel
# Hull outline: (row, half-width px, half-height units) down the sprite, square at the top.
# Below row 34 the outline follows a smooth line through the middle of each of the sprite's steps
# in width (half-widths in px, + 0.2 px), so it matches the sprite's rows without a staircase.
# Where a step's corner pixel would be cut off (rows 40, 51 and 53) the line runs through that
# pixel's centre instead.
SMOOTH = [(-0.5, 24.0), (34.5, 24.0), (36.5, 23.0), (39.5, 22.0), (40.5, 21.85), (42.5, 20.2), (44.5, 19.0),
          (46.5, 16.9), (48.5, 14.9), (50.5, 12.9), (51.5, 11.85), (52.5, 9.85), (53.5, 8.85), (54.5, 6.6),
          (55.5, 4.0), (56.0, 0.0)]
HULL = ([(-0.5, 24.1, 0.14), (16.5, 24.1, 0.14), (34.0, 24.1, 0.14)]
        + [(r, w + 0.2, 0.04 + 0.1 * w / 24) for r, w in SMOOTH[2:-1]] + [(55.9, 2.5, 0.05)])


GLASS_OUTLINE = [(0.8, -0.5), (9.6, -0.5), (11, 1.2), (11, 15), (9, 15), (7, 14), (5, 12), (4, 10), (3, 8),
                 (2, 5), (1, 4)]


def densify(points, step):
    """Linear in-between points (tuples starting with a row) so no gap is longer than step rows."""
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        n = max(1, int(-(-(b[0] - a[0]) // step)))
        for k in range(1, n + 1):
            t = k / n
            out.append(tuple(x + (y - x) * t for x, y in zip(a, b)))
    return out


def _outline_dist(c, r):
    """Distance (px) inside the hull's smoothed side outline from pixel-edge point (c, r); 0 outside."""
    x = abs(c - AXIS)
    pts = [(w, row) for row, w in SMOOTH]
    best = 1e9
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        t = max(0.0, min(1.0, ((x - x0) * dx + (r - y0) * dy) / (dx * dx + dy * dy)))
        best = min(best, ((x - x0 - t * dx) ** 2 + (r - y0 - t * dy) ** 2) ** 0.5)
    # Inside test: left of the outline's half-width at this row.
    if r > 56.0:
        return 0.0
    w = pts[0][0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if y0 <= r <= y1 and y1 > y0:
            w = x0 + (x1 - x0) * (r - y0) / (y1 - y0)
            break
    return best if x < w else 0.0


def half_width(r):
    """The hull's half-width (px) at row r."""
    for (r0, w0, _), (r1, w1, _) in zip(HULL, HULL[1:]):
        if r0 <= r <= r1:
            return w0 + (w1 - w0) * (r - r0) / (r1 - r0)
    return 0.0


def dome(bm):
    """Lift every vertex by the dome profile (and drop the underside), keeping the footprint."""
    for v in bm.verts:
        c, r = v.co.x * 12 + G.w / 2, G.h / 2 - v.co.y * 12
        t = min(_outline_dist(c, r) / FALL, 1.0)
        lift = DOME * (1 - (1 - t) ** 2) / 12
        v.co.z += lift if v.co.z > -1e-4 else -BELLY * lift


def fine_top(bm, faces, cuts=2):
    """Cut a slab's top face into small smooth triangles so it can follow the dome."""
    tris = bmesh.ops.triangulate(bm, faces=[faces[0]])["faces"]
    edges = list({e for f in tris for e in f.edges})
    res = bmesh.ops.subdivide_edges(bm, edges=edges, cuts=cuts, use_grid_fill=True)
    for f in res["geom"]:
        if isinstance(f, bmesh.types.BMFace):
            f.smooth = True
    for f in tris:
        if f.is_valid:
            f.smooth = True


def assembly_pixels():
    """The whole craft's first-frame pixels as {(col, row): palette index}."""
    px = {}
    for piece in PIECES:
        data = common.load_sprite(ROOT, piece)
        e = next(e for e in data["assemblyLayout"] if e["model"] == piece)
        x0, y0 = e["cx"] - 12 - (CENTRE[0] - 24), e["cy"] - 14 - (CENTRE[1] - 28)
        for r, row in enumerate(data["frames"][0]["pixels"]):
            vals = row.split() if isinstance(row, str) else row
            for c, v in enumerate(vals):
                if int(v) >= 0:
                    px[(x0 + c, y0 + r)] = int(v)
    return px


WHOLE = [None]  # the uncut craft, for the pieces' normals


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh9a"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    # Materials (lighting pass): the hull is polished grey metal, so the sprite's white streak on
    # the lower-right rim and its dark right flank are the game's sun and environment on a metallic
    # hull, not paint; the shoulder glass and window are glossy glass with a faint glow.
    mats = [
        pal(5, metallic=0.7, roughness=0.3),  # 0 hull grey (its mid-tone)
        pal(4, metallic=0.5, roughness=0.4),  # 1 keel and cabin, darker grey
        pal(7, metallic=0.55, roughness=0.35),  # 2 light grey sill, plate, ribs
        pal(2, metallic=0.2, roughness=0.8),  # 3 dark vents
        common.palette_material(sprite, 149, tag + "glass", metallic=0.05, roughness=0.1,
                                emission_strength=1.2),  # 4 blue shoulder glass
        pal(148, metallic=0.2, roughness=0.3),  # 5 window grid
        pal(151, metallic=0.05, roughness=0.1, emission_strength=1.5),  # 6 window panes
        common.palette_material(sprite, 151, tag + "lamp", emission_strength=2.0),  # 7 lamps (shaded per pixel)
        # 8 glowing channel: it brightens five shades on frames 130/132 and two on 282/284
        # (the sprite's keel gradient 144-155 shifts up as a whole).
        common.palette_material(sprite, 151, tag + "chan", emission_strength=3.0,
                                frames={130: 156, 132: 156, 282: 153, 284: 153}),
        pal(9, metallic=0.6, roughness=0.3),  # 9 bright ridges and rim
        pal(5, metallic=0.7, roughness=0.3),  # 10 shoulder pods (the hull's own metal)
        # 11 right shoulder glass: the same glass as the left (the sprite draws it darker only
        # because it is on the shadow side)
        common.palette_material(sprite, 149, tag + "glass", metallic=0.05, roughness=0.1,
                                emission_strength=1.2),
        # 12 the channel's dark sunk section (rows 41-46), shifting up with the rest of the gradient
        common.palette_material(sprite, 144, tag + "chand", emission_strength=1.0,
                                frames={130: 149, 132: 149, 282: 146, 284: 146}),
        pal(3, metallic=0.4, roughness=0.5),  # 13 shadowed right flank
        common.palette_material(sprite, 157, tag + "core", emission_strength=3.0),  # 14 lamp cores
        pal(10, metallic=0.55, roughness=0.3),  # 15 light lower rim (right)
    ]
    (HULL_M, KEEL, LIGHT, DARK, GLASS, GRID, PANE, LAMP, CHANNEL, BRIGHT, POD, GLASS_R, CHAN_DARK, FLANK,
     CELL, RIM_R) = range(16)
    extra = {}

    def mat_for(key, make):
        if key not in extra:
            mats.append(make())
            extra[key] = len(mats) - 1
        return extra[key]

    def channel(i):
        """The keel channel's shade for sprite index i: its gradient shifts up five shades on frames
        130/132 and two on 282/284."""
        i = min((144, 146, 148, 150, 152, 154), key=lambda q: abs(q - i))
        return mat_for(("c", i), lambda: common.palette_material(
            sprite, i, tag + "chan", emission_strength=2.5,
            frames={130: min(i + 5, 159), 132: min(i + 5, 159), 282: i + 2, 284: i + 2}))

    def lamp(i):
        """A lamp's shade for sprite index i: deep blue, its core cyan-white."""
        i = min((148, 150, 152, 154, 156, 158), key=lambda q: abs(q - i))
        return mat_for(("l", i), lambda: common.palette_material(
            sprite, i, tag + "lamp", emission_strength=2.0 if i < 154 else 3.0))
    bm = bmesh.new()

    # ---- left half (mirrored below) ----

    # Shoulder pod under the glass (columns 0-11, rows 0-20), its lower edge sloping down and in.
    fine_top(bm, lib.slab(bm, G, [(0.4, -0.5), (12, -0.5), (12, 20.5), (8, 20.5), (5, 18.5), (2, 15.5),
                                  (0.4, 13)], -0.05, 0.3, mat=POD, bevel=0.8))
    # The blue glass on it (columns 1-10, rows 0-14); its pixel shades go on as a skin below.
    fine_top(bm, lib.slab(bm, G, GLASS_OUTLINE, 0.26, 0.33, mat=GLASS, bevel=0.3))
    # Bright ridge along the pod's lower edge and the lip that runs in to the keel (rows 13-20).
    lib.tube(bm, G, [(1.2, 14.4, 0.0, 0.0, 0.28), (2.2, 15.6, 0.7, 0.04, 0.285), (5, 18.4, 0.7, 0.04, 0.29),
                     (8, 20.3, 0.7, 0.04, 0.29), (12.5, 20.6, 0.7, 0.04, 0.25), (13.4, 20.6, 0.0, 0.0, 0.24)],
             sides=6, mat=BRIGHT)
    # Panel ribs across the keel's sides (rows 31 and 36) and a dark vent at its shoulder (rows 27-30).
    for r in (31, 36):
        lib.box(bm, G, 12.6, r, 19.6, r + 1, 0.19, 0.235, mat=LIGHT)
    lib.box(bm, G, 12.2, 27, 16, 30.6, 0.2, 0.232, mat=DARK)
    # Small plate either side of the top plate (columns 11-17, rows 0-2), on the window deck.
    lib.box(bm, G, 12.5, -0.5, 17.5, 2.6, 0.18 + CAB, 0.225 + CAB, mat=KEEL)

    lib.mirror_all(bm, G.x(AXIS))
    # Both shoulders' glass is one even mid-blue, glossy: the sprite's darker right glass and its
    # scattered light and dark pixels are its drawn light (shadow side, glints), which the game's
    # lights make on the glossy material.
    px = assembly_pixels()

    # ---- centre parts ----

    # Hull: a rounded shield, square at the top and rounding to the tip (rows 0-55); dome() domes it.
    lib.tube(bm, G, [(AXIS, r, w, h, 0.0) for r, w, h in HULL[:3] + densify(HULL[2:], 2.5)[1:]], sides=24, mat=HULL_M,
                    power=0.6)
    # Keel down the middle (columns 12-35, rows 17-55), standing above the hull.
    keel = [(16.6, 11.6, 0.2), (17.6, 12.0, 0.22), (46, 12.0, 0.22), (48, 11.6, 0.21), (50, 10.8, 0.2),
            (51.5, 9.8, 0.185), (53, 8.0, 0.165), (54.4, 5.6, 0.13), (55.3, 2.5, 0.07)]
    lib.tube(bm, G, [(AXIS, r, w, h, 0.0) for r, w, h in densify(keel, 3)], sides=16, mat=KEEL, power=0.5)
    # The glowing channel down the keel to the tip (columns 20-27, rows 28-54): one round tube
    # standing about 4 px proud of the keel, that dips to just above the keel where it runs dark
    # (rows 41-46) and rises again to the tip. Each ring of faces takes the shade of the sprite's
    # pixel beside the axis in its row (column 24), so the glow's gradient along the keel (dark in the dip, brightening
    # to the tip) is the sprite's; the sprite's darker left edge across it is drawn light, left to
    # the game's lights.
    H, HD = 4.6 / 12, 0.02 + 0.7 / 12

    def chan_h(r):
        if r <= 39.0 or r >= 49.0:
            return H
        if 41.5 <= r <= 46.5:
            return HD
        t = (r - 39.0) / 2.5 if r < 41.5 else (49.0 - r) / 2.5
        return HD + (H - HD) * (0.5 + 0.5 * math.cos(math.pi * t))
    rows = [28.6, 29.2] + [float(r) for r in range(30, 52)] + [51.5]
    pts = [(AXIS, 28.05, 0.0, 0.0, 0.2), (AXIS, 28.6, 3.0, H * 0.7, 0.2)]
    pts += [(AXIS, r, 4.0, chan_h(r), 0.2) for r in rows[1:]]
    pts += [(AXIS, 53.3, 3.9, H * 0.6, 0.2), (AXIS, 54.6, 3.6, H * 0.4, 0.15), (AXIS, 55.3, 2.5, H * 0.25, 0.1)]
    for f in lib.tube(bm, G, pts, sides=16, mat=CHANNEL, power=0.85):
        cen = f.calc_center_median()
        row = min(54, max(28, int((G.h / 2 - cen.y * 12) // 1)))
        f.material_index = channel(px.get((24, row), 151))
    # Two lamps across the keel (rows 18-20 and 23-25, columns 20-27): deep blue lenses about 2 px
    # tall on the keel, each with its bright cyan-white core along the top (the sprite's middle row).
    lh, lz = 1.25 / 12, 0.22 + 0.8 / 12
    for r in (19.5, 24.5):
        for f in lib.tube(bm, G, [(20.0, r, 1.2, lh * 0.55, lz), (20.6, r, 1.5, lh * 0.9, lz)]
                          + [(float(c), r, 1.5, lh, lz) for c in range(21, 28)]
                          + [(27.4, r, 1.5, lh * 0.9, lz), (28.0, r, 1.2, lh * 0.55, lz)], sides=8, mat=LAMP):
            cen = f.calc_center_median()
            col = min(27, max(20, int((cen.x * 12 + G.w / 2) // 1)))
            row = min(int(r) + 1, max(int(r) - 1, int((G.h / 2 - cen.y * 12) // 1)))
            f.material_index = lamp(px.get((col, row), 151))
        lib.box(bm, G, 19.5, r + 1.4, 28.5, r + 2.2, 0.19, 0.24, mat=LIGHT)
    # Cabin (columns 11-36, rows 0-16): the window deck, a step above the keel, with the window in it.
    lib.slab(bm, G, [(11, -0.5), (37, -0.5), (37, 16.5), (35.5, 17.5), (12.5, 17.5), (11, 16.5)],
             -0.06, 0.2 + CAB, mat=KEEL, bevel=0.4)
    lib.box(bm, G, 18, -0.5, 30, 2.6, 0.18 + CAB, 0.24 + CAB, mat=HULL_M)  # plate over the window
    # Window: blue panes sunk about 0.55 px under a raised grid of mullions.
    rows, cols = ((3.6, 8), (8.6, 10), (10.6, 12), (12.6, 16)), ((15.2, 22), (22.6, 26), (26.6, 30), (30.6, 33.8))
    for r0, r1 in rows:
        for c0, c1 in cols:
            lib.box(bm, G, c0, r0, c1, r1, 0.18 + CAB, 0.205 + CAB, mat=PANE)
    mz0, mz1 = 0.18 + CAB, 0.25 + CAB
    for c0, c1 in ((15, 15.2), (22, 22.6), (26, 26.6), (30, 30.6), (33.8, 34)):
        lib.box(bm, G, c0, 2.6, c1, 16, mz0, mz1, mat=GRID)
    for r0, r1 in ((2.6, 3.6), (8, 8.6), (10, 10.6), (12, 12.6)):
        for c0, c1 in cols:
            lib.box(bm, G, c0, r0, c1, r1, mz0, mz1, mat=GRID)
    lib.box(bm, G, 13.6, 2.6, 15, 16, 0.18 + CAB, 0.25 + CAB, mat=KEEL)  # frame either side
    lib.box(bm, G, 34, 2.6, 35.4, 16, 0.18 + CAB, 0.25 + CAB, mat=KEEL)
    lib.box(bm, G, 13.6, 16, 35.4, 17.2, 0.18 + CAB, 0.25 + CAB, mat=LIGHT)  # sill

    dome(bm)
    # The hull is one grey all over: the sprite's dark right flank, dark lower-left rim and bright
    # lower-right rim streak are its drawn light and outline on the domed metal hull, which the
    # game's sun, environment and outline make (FLANK and RIM_R are no longer used on it).
    WHOLE[0] = lib.to_object(NAME, bm, mats, coll)
    return WHOLE[0]


ANIMATED = ["newsh9-92", "newsh9-94"]


def keep_normals(piece, whole, offset):
    """Mark the faces split_assembly filled along the cuts flat, and give every smooth corner the
    uncut craft's normal (interpolated from the face under it), so the shading runs on across the
    cuts instead of creasing there (the seam down the middle of the channel, lamps and hull)."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from mathutils.interpolate import poly_3d_calc
    mesh = piece.data
    hw, hh, eps = 1.0, 14 / 12, 1e-4
    for poly in mesh.polygons:
        vs = [mesh.vertices[i].co for i in poly.vertices]
        if any(all(abs(v.x - b) < eps for v in vs) for b in (-hw, hw)) or \
                any(all(abs(v.y - b) < eps for v in vs) for b in (-hh, hh)):
            poly.use_smooth = False
    src = whole.data
    tree = BVHTree.FromPolygons([v.co.copy() for v in src.vertices], [list(p.vertices) for p in src.polygons])
    corner = src.corner_normals
    off = Vector((offset[0], offset[1], 0.0))
    normals = []
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            if not poly.use_smooth:
                normals.append(poly.normal.copy())
                continue
            co = mesh.vertices[mesh.loops[li].vertex_index].co + off
            hit, _, fi, _ = tree.find_nearest(co)
            sp = src.polygons[fi]
            w = poly_3d_calc([src.vertices[v].co for v in sp.vertices], hit)
            n = Vector()
            for wk, lk in zip(w, sp.loop_indices):
                n += wk * corner[lk].vector
            normals.append(n.normalized())
    mesh.normals_split_custom_set(normals)


def finish(parts, sprite):
    """Smooth normals across the cuts. The channel's tip reaches just into the upper pieces, which
    have one frame: they keep the plain channel colour."""
    for name, obj in parts.items():
        e = next(e for e in sprite["assemblyLayout"] if e["model"] == name)
        keep_normals(obj, WHOLE[0], ((e["cx"] - CENTRE[0]) / 12, -(e["cy"] - CENTRE[1]) / 12))
    for name, obj in parts.items():
        if name not in ANIMATED:
            mats = obj.data.materials
            for i, m in enumerate(mats):
                if m.get("tyrian_frame_pal"):
                    idx = int(m.name.split("_")[1])
                    mats[i] = common.palette_material(sprite, idx, "nsh9achanp", emission_strength=2.5)


def main():
    lib.run_assembly(ROOT, NAME, PIECES, CENTRE, build, size=4, grid_w=48, grid_h=56, finish=finish)


if __name__ == "__main__":
    main()
