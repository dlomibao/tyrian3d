"""Grey organism on a tube wall, the GYGES drill column's base (newshh.shp 85, 87, 123, 125): its sprites in 3D.

Seen in level 2.4. Four 2x2 enemies: a stalk (with its purple vein sleeve) standing on a soft grey saucer body on the
GYGES tube wall, a large bright dome at the stalk's west foot and two purple lobes (the west siphon, the east pad) on
the body's rim. The silver cap on the stalk's top is newshh-79 (its own script). lib_b063 builds the other pieces of
the set; this script builds and cuts the block itself (QA 2026-11-17 L3: the curled, segment-grooved abdomen read as
a ribbed tube where the sprite draws a flat grey disc).

How the game draws it: the level places the bottom pair (123, 125) only 21 px below the top pair (85, 87), not 28,
and draws the top pair last (opaque, wall included), so on screen the top tiles hide the bottom tiles' first 7 rows
(GYGES t2530-2590, `tyrianHarness.view.draws.items`: 85 at y 49, 123 at y 70; the cap 79 21 px above 85). A body
modelled on the art's 28 px stack was cut in half on screen at the top tiles' south edge (the dome sliced through,
a straight ledge across the body). So the creature is modelled on the GAME's stack ("G" rows: the top tiles' rows
0-27, the bottom tiles' rows k at 21 + k):
- one height field over the plan, the same function for both halves: a soft saucer (a quarter-round rim with a
  vertical tangent at the outline, two low humps where the sprite's 103-104 lobes are) smooth-maxed with the big
  dome and with the stalk's D section running on down until it sinks into the body (the sprite's dark 96-99 flank);
- each half is that field over its OWN sprite's plan (the top tiles' traced outline to row 28; the bottom tiles'
  outline from their row 0), so every piece's top view is its own sprite's; where the two overlap (G rows 21-28)
  the bottom half's surface lies a little under the top half's (the top tiles are the ones the game shows there);
- the upper stalk is lib_b063's lofted tube, ending over the height field;
- the ink shell is one sealed union of both halves, squashed to under half height, so its back faces stay under
  the body's top and only the outer silhouette is inked (no rings where the dome, siphon and pad sit on the body).

Run: blender --background --python assets/blender/enemies/assembly-newshh-125.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import lib_b063 as lib  # noqa: E402

X, Y, PX, Z_B = lib.X, lib.Y, lib.PX, lib.Z_B
common = lib.common

SHIFT = 7  # px: the bottom tiles sit 21 px under the top ones in the game, not 28 (art row = G row + 7 below 28)
# The body's plan in ART coordinates (the sprites stacked at 28 px; block pixel corner coords, col, row), traced from
# the creature mask (rows 21-47: the 103-104 body, its 98-101 south rim, the dark east lobe under the stalk's foot,
# the pad's lobe, the dome's north edge at rows 21-23). Across cols 19-34 the north edge runs under the stalk tube,
# which hides it. Closed, smoothed with Catmull-Rom; the top half takes its rows to 28, the bottom half its rows from
# 28 (moved up SHIFT rows).
DISC = [(7.4, 24.4), (10.2, 23.8), (11.8, 23.2), (12.9, 22.2), (14.4, 21.3), (16.3, 20.9), (18.4, 21.0),
        (21.0, 20.6), (26.0, 20.4), (31.0, 20.8), (33.4, 21.8), (35.0, 23.4), (36.4, 25.4),
        (37.2, 28.6), (38.0, 30.2), (40.0, 30.9), (42.4, 31.4), (43.5, 32.8),
        (43.8, 34.6), (43.0, 36.6), (42.4, 38.6), (41.5, 40.6), (40.6, 42.6), (39.4, 44.2), (37.4, 45.3),
        (34.0, 45.6), (31.4, 45.0), (29.6, 44.4), (27.0, 44.4), (25.0, 45.0), (23.2, 45.9), (20.4, 46.6),
        (16.4, 46.9), (13.2, 46.6), (11.0, 45.7), (9.2, 44.7), (7.9, 43.3), (6.8, 41.5), (5.6, 39.5), (4.5, 37.3),
        (3.6, 35.2), (3.1, 33.0), (2.6, 31.0), (2.4, 29.2), (2.7, 27.7), (3.7, 26.3), (5.3, 25.2)]
# Everything below is in G rows (the game's stack).
RIM_R = 3.2  # px: the body's rounded rim (quarter ellipse from the outline, vertical tangent at the wall)
BODY_H = 2.3  # px over the sole: the saucer's base height; the humps add to it
HUMPS = [(13.0, 31.0, 7.0, 1.5), (30.0, 30.0, 4.5, 0.9)]  # col, row, sigma px, extra height px (the 104 lobes)
# The stalk's foot, continued as part of the height field: lib_b063's stations (col, row, half width, z top px),
# then on down until it sinks into the body's east lobe (on screen the dark flank ends at the top tiles' edge).
FOOT = [(24.1, 13.0, 7.1, 2.4), (25.0, 18.0, 7.5, 2.2), (26.6, 22.6, 8.0, 1.8), (29.0, 26.2, 7.6, 1.0),
        (31.0, 28.6, 5.6, -0.3), (32.4, 30.4, 3.0, -1.9)]
TUBE_END = 3  # the tube runs over FOOT[:TUBE_END + 1] (to row 26.2), then the height field carries the foot
GLAND = (16.6, 25.0, 8.0, 5.8, 4.6)  # the big soft dome at the stalk's west foot: col, row, rx, ry, z top px
TIP = (6.5, 26.2, 3.5, 1.7, 2.0, -32.0)  # west siphon (the top tiles' 82-91 wedge): col, row, rx, ry, z top, angle
PAD = (35.9, 41.6 - SHIFT, 5.3, 3.7, 1.9, -39.4)  # east pad: the sprite's elongated, angled lobe
EDGE_DIP = 0.1  # px: the top half's surface at its south edge (row 28), under the bottom half's
UNDER = 0.25  # px: the bottom half's surface under the top half's, where both carry it (G rows 21-28)
SOLE_DROP = 0.05  # px: the sole under the rim's foot (a closed wall all round)
SHELL_SQUASH = 0.45  # the ink shell's height, as a fraction of the model's (over the sole)


def closed_catmull(pts, step=0.4):
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        k = max(2, int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / step))
        for j in range(k):
            t = j / k
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2
                                    + (-a + 3 * b - 3 * c + d) * t3) for a, b, c, d in zip(p0, p1, p2, p3)))
    return out


def clip_rows(poly, keep, row, step=0.4):
    """Sutherland-Hodgman against one row line: keep "north" (rows <= row) or "south" (rows >= row) of a closed
    plan polygon; the cut is resampled every `step` px."""
    inside_ = (lambda p: p[1] <= row) if keep == "north" else (lambda p: p[1] >= row)
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if inside_(a):
            out.append(a)
        if inside_(a) != inside_(b):
            t = (row - a[1]) / (b[1] - a[1])
            out.append((a[0] + (b[0] - a[0]) * t, row))
    res = []
    for i, p in enumerate(out):  # resample the long straight cut
        res.append(p)
        q = out[(i + 1) % len(out)]
        if abs(p[1] - row) < 1e-9 and abs(q[1] - row) < 1e-9:
            k = int(abs(q[0] - p[0]) / step)
            res += [(p[0] + (q[0] - p[0]) * j / k, row) for j in range(1, k)]
    return np.array(res)


def seg_dist(p, a, b):
    """Distance from points p (N, 2) to segments a->b (M, 2): (N, M) distances, (N, M) params t."""
    ab = b - a
    ap = p[:, None, :] - a[None, :, :]
    t = np.clip((ap * ab[None]).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-12)[None], 0.0, 1.0)
    q = a[None] + t[..., None] * ab[None]
    return np.linalg.norm(p[:, None, :] - q, axis=-1), t


def inside(p, poly):
    x, y = p[:, 0][:, None], p[:, 1][:, None]
    x0, y0 = poly[:, 0][None], poly[:, 1][None]
    x1, y1 = np.roll(poly[:, 0], -1)[None], np.roll(poly[:, 1], -1)[None]
    cross = ((y0 > y) != (y1 > y)) & (x < (x1 - x0) * (y - y0) / np.where(y1 == y0, 1e-12, y1 - y0) + x0)
    return cross.sum(1) % 2 == 1


def edge_dist(p, poly):
    return seg_dist(p, poly, np.roll(poly, -1, axis=0))[0].min(1)


def sdf(p, poly):
    return edge_dist(p, poly) * np.where(inside(p, poly), 1.0, -1.0)


_art = closed_catmull(DISC)
TOP_POLY = clip_rows(_art, "north", 28.6)
BOT_POLY = clip_rows(_art, "south", 28.0) - np.array([0.0, SHIFT])
# The bottom tiles' first rows west of the dome lie outside the top tiles' plan (on screen the original's top tiles
# paint wall over them); their square north-west corner is rounded into a quarter ellipse, so the body's rim there
# reads as one curve (a few px of the bottom sprite's corner, within the top-view rule).
NW_ARC = (10.5, 24.4, 8.1, 3.4)  # centre col, G row, radii


def _round_corner(poly, cc, cr, rc, rr):
    zone = (poly[:, 0] < cc) & (poly[:, 1] < cr)
    # the zone is one run along the loop: roll it to the middle, then swap the run for the arc
    k = int(np.flatnonzero(~zone)[0])
    poly = np.roll(poly, -k, axis=0)
    zone = np.roll(zone, -k)
    i = np.flatnonzero(zone)
    a, b = i[0], i[-1]
    th0, th1 = (math.pi, 1.5 * math.pi) if poly[a][1] > poly[b][1] else (1.5 * math.pi, math.pi)
    arc = [(cc + rc * math.cos(t), cr + rr * math.sin(t)) for t in np.linspace(th0, th1, 24)]
    return np.concatenate([poly[:a], np.array(arc), poly[b + 1:]])


BOT_POLY = _round_corner(BOT_POLY, *NW_ARC)


def union_dist(p):
    """Distance inside the union of both halves' plans (the creature on screen), 0 outside."""
    return np.maximum(np.maximum(sdf(p, TOP_POLY), sdf(p, BOT_POLY)), 0.0)


def smax(a, b, k=1.0):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.maximum(a, b) + h * h * k / 4


def heights(p):
    """z (px) of the height field at plan points p (col, G row); the dome's and the foot's margins over the rest
    (px); the foot's offset across in half widths (east +); the humps' height (px); the distance in from the outline
    (px); whether the nearest outline lies to the south."""
    d = union_dist(p)
    south = union_dist(p + np.array([0.0, 0.5])) < d - 0.4  # the outline within ~37 degrees of due south
    s = np.sqrt(np.clip(1 - (1 - np.minimum(d / RIM_R, 1.0)) ** 2, 0.0, 1.0))
    c, r = p[:, 0], p[:, 1]
    hump = np.zeros(len(p))
    for hc, hr, sg, hh in HUMPS:
        hump += hh * np.exp(-((c - hc) ** 2 + (r - hr) ** 2) / (2 * sg * sg))
    body = BODY_H + hump
    gc, gr, grx, gry, gzt = GLAND
    q = ((c - gc) / grx) ** 2 + ((r - gr) / gry) ** 2
    # a full round dome (its foot, under the body's top, is blended into it by the smooth max)
    dome = (gzt - Z_B) * np.clip(1 - q, 0.0, 1.0) ** 0.75
    # The foot: the tube's own D section (superellipse n 2.2) along a fine centreline; slightly under the tube
    # where the tube still runs, so the two never fight.
    fine = np.array(lib.catmull(FOOT, 0.25))
    fd, ft = seg_dist(p, fine[:-1, :2], fine[1:, :2])
    j = fd.argmin(1)
    t = ft[np.arange(len(p)), j]
    st = fine[j] + (fine[j + 1] - fine[j]) * t[:, None]
    tang = fine[j + 1, :2] - fine[j, :2]
    tang /= np.linalg.norm(tang, axis=1)[:, None]
    off = p - st[:, :2]
    x = off[:, 0] * tang[:, 1] - off[:, 1] * tang[:, 0]  # + east of the line (right of travel, rows down)
    along = (off * tang).sum(1)
    w, zt = st[:, 2], st[:, 3]
    end = (j == len(fine) - 2) & (along > 1e-6)
    u = np.clip(np.abs(x) / np.maximum(w, 1e-6), 0.0, 1.0)
    foot = np.where(end | (np.abs(x) >= w), 0.0, (zt - Z_B) * np.clip(1 - u ** 2.2, 0.0, 1.0) ** (1 / 2.2))
    foot *= np.where(st[:, 1] < FOOT[TUBE_END][1], 0.97, 1.0)
    h = smax(smax(body, dome, 1.8), foot, 1.2)
    m_dome = dome - np.maximum(body, foot)
    m_foot = foot - np.maximum(body, dome)
    return Z_B + s * h, m_dome, m_foot, x / np.maximum(w, 1e-6), hump, d, south


def height_field(bm, slot, poly, under_top=False):
    """The body over one half's plan `poly` (col, G row): CDT of the outline, offset rings near it (the rim's curve)
    and an interior grid; z from heights(); a sole a hair under the rim's foot, joined to it by a wall (where the
    plan's edge is inside the other half, the wall stands in that half's body). `under_top`: the bottom half, whose
    surface sinks UNDER px where the top half covers it (fading out at the top half's south edge, row 28), so the
    two never fight there; the top half's plan edge is sampled into it, so the step follows that edge."""
    outline = poly
    n = len(outline)
    area = 0.5 * np.sum(outline[:, 0] * np.roll(outline[:, 1], -1) - np.roll(outline[:, 0], -1) * outline[:, 1])
    tng = np.roll(outline, -1, axis=0) - np.roll(outline, 1, axis=0)
    tng /= np.maximum(np.linalg.norm(tng, axis=1), 1e-9)[:, None]
    nrm = np.stack([-tng[:, 1], tng[:, 0]], 1)
    probe = outline + nrm * 0.2
    if inside(probe, outline).mean() < 0.5:
        nrm = -nrm
    pts = [outline]
    for dd in (0.1, 0.25, 0.45, 0.7, 1.0, 1.4, 1.9, 2.5, 3.2):
        ring = outline + nrm * dd
        ok = inside(ring, outline) & (edge_dist(ring, outline) > 0.75 * dd)
        pts.append(ring[ok][::1 if dd < 1.2 else 2])
    step = 0.45
    gc, gr = np.meshgrid(np.arange(0, 48, step) + 0.2, np.arange(10, 50, step) + 0.15)
    grid = np.stack([gc.ravel(), gr.ravel()], 1)
    grid = grid[inside(grid, outline)]
    grid = grid[edge_dist(grid, outline) > 3.5]
    pts.append(grid)
    if under_top:
        edge = TOP_POLY[(TOP_POLY[:, 1] < 28.0) & inside(TOP_POLY, outline) & (edge_dist(TOP_POLY, outline) > 0.2)]
        pts.append(edge)
    allp = np.concatenate(pts)
    # (x, y) = (col, -row) flips the winding: a loop clockwise in (col, row) is CCW there.
    loop = list(range(n)) if area < 0 else list(reversed(range(n)))
    verts, _, faces, orig, _, _ = delaunay_2d_cdt([Vector((c, -r)) for c, r in allp], [], [loop], 1, 1e-5)
    p2 = np.array([(v.x, -v.y) for v in verts])
    z, m_dome, m_foot, xo, hump, dist, south = heights(p2)
    if under_top:
        covered = (sdf(p2, TOP_POLY) > 0.05) & (p2[:, 1] < 28.0)
        z -= np.where(covered, UNDER * np.clip((28.0 - p2[:, 1]) / 0.3, 0.0, 1.0), 0.0)
    else:  # the top half dips a hair at its south edge, so its cut face there stays under the bottom half's surface
        z -= EDGE_DIP * np.clip((p2[:, 1] - 27.5) / 0.5, 0.0, 1.0)
    bv = [bm.verts.new((X(c), Y(r), zz * PX)) for (c, r), zz in zip(p2, z)]
    edge_v = {}
    for i, o in enumerate(orig):
        for k in o:
            if k < n:
                edge_v[k] = bv[i]
    top = [bm.faces.new([bv[i] for i in f]) for f in faces]
    ring = []
    for k in range(n):
        v = edge_v[k]
        if not ring or ring[-1] is not v:
            ring.append(v)
    if ring[0] is ring[-1]:
        ring.pop()
    sole = [bm.verts.new((v.co.x, v.co.y, (Z_B - SOLE_DROP) * PX)) for v in ring]
    walls = []
    for i in range(len(ring)):
        j = (i + 1) % len(ring)
        walls.append(bm.faces.new((ring[i], ring[j], sole[j], sole[i])))
    base = bm.faces.new(list(reversed(sole)))
    base.material_index = slot[100]
    bmesh.ops.triangulate(bm, faces=[base], quad_method="BEAUTY", ngon_method="BEAUTY")
    for f in walls:
        f.material_index = slot[100]
        f.smooth = False
    idx = {v: i for i, v in enumerate(bv)}
    for f in top:
        f.smooth = True
        ids = [idx[v] for v in f.verts]
        md, mf, dm = m_dome[ids].mean(), m_foot[ids].mean(), dist[ids].mean()
        # One palette step at a time between neighbouring regions, so no boundary reads as a seam.
        if md > 2.4:
            f.material_index = slot[105]  # the dome's crest (the sprite's 105-106; its 107-108 is sheen)
        elif md > 0.9:
            f.material_index = slot[104]  # the dome
        elif md > 0.25:
            f.material_index = slot[103]
        elif mf > 0.25:
            # the stalk's foot: its east flank dark (96-99) as the tube above it, lighter as it sinks into the body
            east = xo[ids].mean() > 0.3
            f.material_index = slot[(99 if east else 100) if mf > 1.0 else (100 if east else 101) if mf > 0.5 else 101]
        elif south[ids].all() and dm < 1.0:
            f.material_index = slot[100]  # the south belly under the rim (the rings sit at 1.0 and RIM_R)
        elif south[ids].all() and dm < RIM_R:
            f.material_index = slot[101]
        elif hump[ids].mean() > 1.0:
            f.material_index = slot[103]  # the lobes' crests (the sprite's 104 fields)
        else:
            f.material_index = slot[102]


def finish(bm, name, mats, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def build_halves(coll, sprite):
    """The top half (85, 87: stalk, sleeve, the body's north band, dome, siphon) and the bottom half (123, 125: the
    body, the pad), both in G rows."""
    mats, slot = lib.block_materials(sprite)
    slot[105] = len(mats)  # the dome's crest, as lib_b063's greys
    mat = common.palette_material(sprite, 105, "nshh125B", metallic=0.25, roughness=0.4)
    lib.set_spec(mat, 0.5)
    mats.append(mat)

    bm = bmesh.new()
    # Upper stalk: lib_b063's tube, flat at the block's north edge (under the cap), its round end over the body.
    faces = lib.tube(bm, lib.STALK[:5] + [(c, r, w, zt, Z_B) for c, r, w, zt in FOOT[2:TUBE_END + 1]],
                     sides=18, end0="flat", end1="round")
    m, nstrip = lib.tube.meta
    for i, f in enumerate(faces):
        r = lib.H / 2 - f.calc_center_median().y / PX
        k = i % m if i < nstrip else -1
        # As lib_b063: the crown 102 in the north rows, the east flank 99, else 100.
        if 7 <= k <= 10 and r < 10.5:
            f.material_index = slot[102]
        elif 0 <= k <= 2 or k == m - 1:
            f.material_index = slot[99]
        else:
            f.material_index = slot[100]

    # Vein sleeve: unchanged from lib_b063 (a ribbed purple tube on the stalk's west side).
    def rib(r):
        return sum(math.exp(-(((r - rr) / 1.0) ** 2)) for rr in lib.SLEEVE_RIBS)

    sleeve = [(c, r, w, zt, max(Z_B, zt - 2.2 * w)) for c, r, w, zt in lib.SLEEVE]
    for f in lib.tube(bm, sleeve, sides=16, n=2.4, wmod=lambda s, c, r: 1.0 + 0.07 * rib(r),
                      zmod=lambda s, c, r: 1.0 + 0.07 * rib(r)):
        f.material_index = slot[85]

    # West siphon: a lobe rising out of the body's rim, its mouth a shallow dimple at the outer (west) end.
    c, r, rx, ry, zt, ang = TIP
    for f in lib.blob(bm, c, r, rx, ry, zt, Z_B, angle_deg=ang, segs=28, rings=12, dimple=(-2.4, 1.3, 0.9, 0.4)):
        f.material_index = slot[87]
    height_field(bm, slot, TOP_POLY)
    top = finish(bm, "newshh125-top", mats, coll)

    bm = bmesh.new()
    height_field(bm, slot, BOT_POLY, under_top=True)
    # East pad: the sprite's elongated lobe, rising out of the body's south-east rim.
    c, r, rx, ry, zt, ang = PAD
    faces = lib.blob(bm, c, r, rx, ry, zt, Z_B, angle_deg=ang, segs=32, rings=12)
    bm.normal_update()
    for f in faces:
        f.material_index = slot[84 if f.normal.z > 0.8 else 83]
    bottom = finish(bm, "newshh125-bottom", mats, coll)
    return top, bottom


def squashed_shell(coll, objs, faces):
    """The ink shell from one copy of both halves squashed toward the sole: the outer silhouette keeps its ink,
    while every contour over the body (the dome's, the siphon's, the pad's) lies under the model's top."""
    srcs = []
    for o in objs:
        src = o.copy()
        src.data = o.data.copy()
        coll.objects.link(src)
        srcs.append(src)
    bm = bmesh.new()
    for s in srcs:
        bm.from_mesh(s.data)
    z0 = Z_B * PX
    for v in bm.verts:
        v.co.z = z0 + (v.co.z - z0) * SHELL_SQUASH
    me = bpy.data.meshes.new("newshh125-shellsrc")
    bm.to_mesh(me)
    bm.free()
    src = bpy.data.objects.new("newshh125-shellsrc", me)
    coll.objects.link(src)
    for s in srcs:
        bpy.data.objects.remove(s)
    sh = common.outline_shell(src, coll, faces=faces, islands="outer")
    bpy.data.objects.remove(src)
    sh.hide_render = True
    return sh


def export_block():
    """assembly-newshh-125: the top half cut into newshh-85 and -87 (G rows 0-28), the bottom half into newshh-123
    and -125 (G rows 21-49), each centred on its own tile, with the union shell cut the same way."""
    coll = common.reset_collection("assembly-newshh-125")
    _, sprite = lib.load_block()
    top, bottom = build_halves(coll, sprite)
    print("assembly-newshh-125: triangles", lib._tri(top) + lib._tri(bottom))
    shell = squashed_shell(coll, [top, bottom], 4200)
    W, H = lib.W, lib.H
    lay_top = [("newshh-85", 12 - W / 2, 14 - H / 2), ("newshh-87", 36 - W / 2, 14 - H / 2)]
    lay_bot = [("newshh-123", 12 - W / 2, 21 + 14 - H / 2), ("newshh-125", 36 - W / 2, 21 + 14 - H / 2)]
    parts = {**lib.split_pieces(top, lay_top, coll), **lib.split_pieces(bottom, lay_bot, coll)}
    shells = {**lib.split_pieces(shell, lay_top, coll, cap=False), **lib.split_pieces(shell, lay_bot, coll, cap=False)}
    for name in ("newshh-85", "newshh-87", "newshh-123", "newshh-125"):
        lib._export([parts[name], lib._outline(shells[name], name)], name)
        parts[name].hide_render = True


if __name__ == "__main__":
    export_block()
