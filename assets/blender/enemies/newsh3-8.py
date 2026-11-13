"""newsh3-8: the grey pincer craft with a flame jet (newsh3.shp frames 8 and 46).

Exports public/models/enemies/newsh3-8.glb and src/render/spriteModels/newsh3-8.json
(common.export_sprite_model); with --out x.glb it also writes a review copy there.

    blender --background --python assets/blender/enemies/newsh3-8.py [-- --out x.glb]

What it is (4.4 SURFACE, 4.5 CORE, 4.8 ICE EXIT): a flyer that crosses the screen right to left,
blades and flame first. Seen from above, two curved scimitar blades (one above the other, mirrored
about row edge 13.5) sweep left from knuckle housings on the right; a polished cross rod joins the
two knuckles, a weapon jet (red sheath, orange core, yellow hot spot) fires left from the rod between
the blades and a small red plume leaves the rod's right side. The two frames only change the flame
and plume, so the body is shared and the flames are frame parts (common.frame_part).

Sprite coordinates are pixel edges in the 24x28 block (column c spans c..c+1, row r spans r..r+1);
1 px = 1/12 unit, the block centre is the origin, sprite up is +Y, heights in px go through P().
The plan follows each frame's INNER mask (tools/sprite_mask.py, D74): the game draws the ink ring.
"""

import bisect
import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = "newsh3-8"
FRAMES = (8, 46)
W, H = 24, 28
MIRROR = 13.5  # the two blades mirror each other about this row edge


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402


def X(c):
    return (c - W / 2) / 12


def Y(r):
    return (H / 2 - r) / 12


def P(px):
    return px / 12


def pchip(xs, ys):
    """Monotone cubic interpolation through (xs, ys) (copied from usp_talon.pchip)."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0] + m[0] * (x - xs[0])
        if x >= xs[-1]:
            return ys[-1] + m[-1] * (x - xs[-1])
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def curve(pts):
    xs, ys = zip(*pts)
    return pchip(list(xs), list(ys))


# --- Plan (sprite px edges), fitted to the inner mask -------------------------------------------

# Upper blade: outer (top) edge and inner (bottom) edge, rows as functions of the column edge x.
BLADE_OUT = curve([(0.35, 7.55), (1.2, 7.05), (3.0, 6.35), (5.0, 5.45), (6.8, 4.85), (8.4, 4.3),
                   (10.2, 4.02), (12.5, 3.95), (15.5, 4.0), (17.4, 4.3), (19.3, 4.85), (20.9, 5.5),
                   (22.2, 6.05), (23.0, 6.6)])
BLADE_IN = curve([(0.35, 7.6), (1.5, 7.95), (6.0, 8.05), (10.4, 8.05), (11.2, 8.5), (12.5, 8.9),
                  (13.6, 9.3), (14.4, 9.95), (15.3, 10.55), (16.2, 10.85), (18.0, 10.9), (19.5, 10.6),
                  (20.4, 10.0), (21.0, 9.25), (22.4, 8.85), (23.0, 8.5)])
# Thickness of the blade (px) along it.
BLADE_T = curve([(0.35, 0.3), (2.0, 0.75), (6.0, 1.3), (11.0, 1.85), (16.0, 2.2), (21.0, 2.3), (23.0, 1.8)])
BLADE_X0, BLADE_X1 = 0.45, 23.0
GROOVES = (5.6, 10.6)  # transverse panel breaks on the blade top
# Blade top profile across it (u: 0 outer edge .. 1 inner edge) as fractions of the thickness; the
# dip at u 0.40 is the longitudinal panel line, scaled by groove depth along x.
TOP = [(0.0, 0.12), (0.05, 0.42), (0.3, 0.8), (0.36, 0.83), (0.40, 0.80), (0.44, 0.86), (0.56, 1.0),
       (0.74, 1.0), (0.85, 0.8), (1.0, 0.6)]
BOT = [(1.0, -0.22), (0.86, -0.44), (0.55, -0.5), (0.2, -0.32), (0.0, -0.02)]

# Knuckle housing at the blade root: plan rows rt (top) .. rb (bottom) over x 13.4..21.4.
HUB_X0, HUB_X1, HUB_XC = 13.4, 21.4, 17.5
HUB_TOP = curve([(13.4, 7.6), (15.0, 6.6), (17.5, 6.15), (20.0, 6.6), (21.4, 7.6)])
HUB_BOT = curve([(13.4, 8.9), (14.2, 9.6), (15.0, 10.45), (16.0, 10.95), (17.5, 11.0), (19.0, 10.9),
                 (20.0, 10.4), (20.8, 9.6), (21.4, 8.9)])

ROD_X, ROD_R, ROD_Z = 19.4, 1.45, 0.9  # cross rod on column edge 19.5, along the rows
ROD_R0, ROD_R1 = 9.6, 2 * MIRROR - 9.6
COLLAR_R = 1.75

# Weapon jet per frame: (column centre, top row edge, bottom row edge) read off each frame's inner
# mask, base buried in the rod. Core: (x, row, half width px) along the orange core; spot: the
# yellow hot spot (x, row, half x, half y).
FLAME = {
    8: dict(sheath=[(3.75, 14.5, 14.5), (4.5, 14.0, 15.0), (6.5, 13.05, 14.95), (8.5, 12.95, 15.0),
                    (9.5, 12.1, 15.0), (11.0, 12.0, 15.95), (12.5, 11.9, 15.95), (13.5, 11.1, 15.0),
                    (14.5, 11.05, 14.95), (15.5, 11.1, 14.6), (16.5, 11.2, 14.0), (17.5, 11.6, 13.9),
                    (18.6, 12.0, 14.0)],
            core=[(8.6, 13.5, 0.0), (9.6, 13.4, 0.55), (11.5, 13.0, 0.95), (13.5, 12.75, 1.15),
                  (15.5, 12.95, 0.95), (17.0, 13.3, 0.6), (18.3, 13.4, 0.5)],
            spot=(13.9, 12.55, 1.05, 0.55)),
    46: dict(sheath=[(4.75, 13.5, 13.5), (5.5, 13.05, 13.95), (6.5, 13.0, 14.0), (7.5, 12.1, 14.0),
                     (9.5, 12.0, 14.0), (10.5, 11.1, 14.0), (11.5, 11.1, 14.9), (12.5, 12.0, 15.9),
                     (13.5, 12.05, 15.9), (14.5, 12.1, 14.9), (15.5, 13.0, 14.6), (16.5, 13.05, 14.0),
                     (17.5, 13.05, 13.95), (18.6, 13.0, 14.0)],
             core=[(7.6, 13.5, 0.0), (8.6, 13.5, 0.45), (10.5, 13.45, 0.6), (12.4, 13.5, 0.62),
                   (13.8, 13.55, 0.45), (14.8, 13.6, 0.0)],
             spot=(12.6, 13.5, 0.7, 0.42)),
}
FLAME_GROW = 0.12
# Rear plume out of the rod's right side, per frame: (x, half width px).
PLUME = {8: [(20.6, 1.5), (21.5, 1.45), (22.4, 1.25), (23.0, 0.8), (23.6, 0.45), (24.0, 0.0)],
         46: [(20.6, 1.5), (21.2, 1.4), (21.7, 0.9), (22.1, 0.5), (23.2, 0.45), (23.95, 0.0)]}


# --- Mesh helpers ---------------------------------------------------------------------------------

def bridge(bm, rings, mat, cap0=True, cap1=True):
    """Bridge rings (lists of BMVerts, same count; a 1-vertex ring is a tip) with quads, cap ends."""
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        n = max(len(r0), len(r1))
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                f = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                f = (r0[i], r0[j], r1[0])
            else:
                f = (r0[i], r0[j], r1[j], r1[i])
            faces.append(bm.faces.new(f))
    if cap0 and len(rings[0]) > 2:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap1 and len(rings[-1]) > 2:
        faces.append(bm.faces.new(rings[-1]))
    for f in faces:
        f.material_index = mat
    return faces


def ring(bm, pts):
    return [bm.verts.new(p) for p in pts]


def mirror_from(bm, start, mat_map):
    """Duplicate the geometry from vertex `start` on, mirrored about row edge MIRROR (faces flipped),
    with material slots remapped through mat_map."""
    y0 = Y(MIRROR)
    bm.verts.ensure_lookup_table()
    verts = bm.verts[start:]
    faces = {f for v in verts for f in v.link_faces}
    vmap = {v: bm.verts.new((v.co.x, 2 * y0 - v.co.y, v.co.z)) for v in verts}
    for f in faces:
        nf = bm.faces.new([vmap[v] for v in reversed(f.verts)])
        nf.material_index = mat_map.get(f.material_index, f.material_index)


def frange(a, b, step):
    n = max(1, int(math.ceil((b - a) / step - 1e-9)))
    return [a + (b - a) * i / n for i in range(n + 1)]


# --- Parts ----------------------------------------------------------------------------------------

def blade_stations():
    xs = set(round(x, 4) for x in frange(BLADE_X0, 22.4, 0.7))
    for g in GROOVES:
        xs |= {round(g - 0.22, 4), round(g, 4), round(g + 0.22, 4)}
    xs |= {1.0, 1.6}
    xs = sorted(xs)
    return [(x, 1.0) for x in xs] + [(22.75, 0.82), (22.95, 0.55), (23.05, 0.22)]


def build_blade(bm, mat, detail=True):
    """The upper blade: a lofted scimitar with a chamfered crest near its inner edge."""
    rings = [[bm.verts.new((X(0.25), Y(7.58), P(0.05)))]]
    for x, s in blade_stations():
        ro, ri = BLADE_OUT(min(x, 23.0)), BLADE_IN(min(x, 23.0))
        mid, w = (ro + ri) / 2, (ri - ro)
        ro, ri = mid - w * s / 2, mid + w * s / 2
        w = ri - ro
        t = BLADE_T(min(x, 23.0)) * (0.45 + 0.55 * s)
        groove = 0.0
        line = 0.0
        if detail:
            for g in GROOVES:
                if abs(x - g) < 1e-3:
                    groove = 0.2
            # longitudinal panel line from x 2.5 to 13, faded at its ends
            if 2.5 < x < 13.0:
                line = min(1.0, (x - 2.5) / 1.5, (13.0 - x) / 1.5)
        pts = []
        for u, k in TOP:
            if abs(u - 0.40) < 1e-6:
                k = 0.85 - 0.14 * line if detail else 0.85
            if groove and 0.1 < u < 0.95:
                k -= groove
            pts.append((X(x), Y(ro + u * w), P(t * k)))
        for u, k in BOT:
            pts.append((X(x), Y(ro + u * w), P(t * k)))
        rings.append(ring(bm, pts))
    return bridge(bm, rings, mat)


DRUM_C = (17.6, 8.2)  # pivot drum centre (col, row edges)
DRUM_R = 2.3  # plan radius px
# Drum profile bottom to top: (radius fraction, z px). Chamfered rim, a groove, a domed cap and a
# pivot boss in the middle.
DRUM_PROF = [(0.0, -0.9), (0.8, -0.9), (0.97, -0.6), (1.0, -0.3), (1.0, 2.2), (0.95, 2.42), (0.88, 2.5),
             (0.84, 2.45), (0.8, 2.5), (0.6, 2.62), (0.34, 2.7), (0.3, 2.8), (0.18, 2.85), (0.0, 2.86)]
DRUM_PROF_SEAL = [(0.0, -0.9), (0.8, -0.9), (0.97, -0.6), (1.0, -0.3), (1.0, 2.2), (0.95, 2.42),
                  (0.86, 2.52), (0.55, 2.64), (0.0, 2.72)]


def drum_radius(a):
    """Plan radius (px) of the drum at angle a (0 = +col, pi/2 = up the sprite): a circle, eased
    in toward the rod below so it stays inside the mask's rows 10-11."""
    r = DRUM_R
    down = max(0.0, -math.sin(a))  # toward higher rows (sprite down)
    return r * (1 - 0.06 * down ** 3)


def build_hub(bm, mat, detail=True, sides=28):
    """The pivot drum the blade swings on: a vertical cylinder with a chamfered, grooved cap."""
    cx, cr = DRUM_C
    rings = []
    for f, z in (DRUM_PROF if detail else DRUM_PROF_SEAL):
        if f == 0:
            rings.append([bm.verts.new((X(cx), Y(cr), P(z)))])
            continue
        pts = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            r = drum_radius(a) * f
            pts.append((X(cx + r * math.cos(a)), Y(cr - r * math.sin(a)), P(z)))
        rings.append(ring(bm, pts))
    faces = bridge(bm, rings, mat, cap0=False, cap1=False)
    if detail:
        # six bolt heads round the cap
        for k in range(6):
            a = 2 * math.pi * (k + 0.5) / 6
            bx, by = cx + 0.72 * DRUM_R * math.cos(a), cr - 0.72 * DRUM_R * math.sin(a)
            bolt = []
            for zz, rr in ((2.5, 0.22), (2.7, 0.22), (2.78, 0.13)):
                bolt.append(ring(bm, [(X(bx) + P(rr) * math.cos(t), Y(by) + P(rr) * math.sin(t), P(zz))
                                      for t in (2 * math.pi * j / 6 for j in range(6))]))
            faces += bridge(bm, bolt, mat)
    return faces


def build_ring_band(bm, x0, x1, r_fn, row, z, mat, sides=14, axis="x"):
    """A body of revolution along X (axis 'x') at a row, or along the rows (axis 'y') at column x0."""
    rings = []
    for s, r in r_fn:
        if axis == "x":
            pts = [(X(s), Y(row) + P(r) * math.cos(a), P(z) + P(r) * math.sin(a))
                   for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))]
        else:
            pts = [(X(x0) + P(r) * math.cos(a), Y(s), P(z) + P(r) * math.sin(a))
                   for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))]
        rings.append([bm.verts.new(pts[0])] if r == 0 else ring(bm, pts))
    return bridge(bm, rings, mat)


def build_rod(bm, mat_rod, mat_collar, detail=True):
    """The polished cross rod between the knuckles, with a collar where it leaves each knuckle."""
    prof = [(ROD_R0, ROD_R * 0.9), (ROD_R0 + 0.4, ROD_R), (2 * MIRROR - ROD_R0 - 0.4, ROD_R),
            (2 * MIRROR - ROD_R0, ROD_R * 0.9)]
    build_ring_band(bm, ROD_X, None, prof, None, ROD_Z, mat_rod, sides=14, axis="y")
    for r0 in (10.55, 2 * MIRROR - 11.6):
        prof = [(r0, COLLAR_R * 0.88), (r0 + 0.12, COLLAR_R), (r0 + 0.93, COLLAR_R), (r0 + 1.05, COLLAR_R * 0.88)]
        build_ring_band(bm, ROD_X, None, prof, None, ROD_Z, mat_collar, sides=14, axis="y")
    if detail:
        # the jet port on the rod's left face and the plume port on its right: short glowing rings
        build_ring_band(bm, None, None, [(18.0, 0.0), (18.15, 0.62), (18.6, 0.66), (18.7, 0.0)],
                        MIRROR, ROD_Z, mat_collar, sides=12)
        build_ring_band(bm, None, None, [(20.3, 0.0), (20.45, 0.95), (21.0, 1.0), (21.12, 0.0)],
                        MIRROR, ROD_Z, mat_collar, sides=12)


def build_body(bm, M, detail=True):
    start = len(bm.verts)
    build_blade(bm, M["blade_up"], detail)
    build_hub(bm, M["hub_up"], detail)
    mirror_from(bm, start, {M["blade_up"]: M["blade_lo"], M["hub_up"]: M["hub_lo"]})
    build_rod(bm, M["rod"], M["collar"], detail)


def ellipse_loft(bm, stations, row_fn, z, mat, sides=12, zscale=0.7, zmax=1.1):
    """A loft along X of ellipses: stations (x, half width px), centred on row_fn(x), height z px."""
    rings = []
    for x, hw in stations:
        r = row_fn(x)
        if hw <= 0:
            rings.append([bm.verts.new((X(x), Y(r), P(z)))])
            continue
        hz = min(zmax, hw * zscale)
        rings.append(ring(bm, [(X(x), Y(r) + P(hw) * math.cos(a), P(z) + P(hz) * math.sin(a))
                               for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))]))
    return bridge(bm, rings, mat)


def build_flame(bm, frame, M):
    spec = FLAME[frame]
    sh = spec["sheath"]
    # soften the per-column steps into a licking flame: 3-tap average, grown back by the shrink
    def soft(vals, grow):
        out = [vals[0]] + [(vals[i - 1] + 2 * vals[i] + vals[i + 1]) / 4 for i in range(1, len(vals) - 1)] + [vals[-1]]
        return [v + grow * (1 if 0 < i < len(vals) - 1 else 0) for i, v in enumerate(out)]
    tops = soft([t for _, t, _ in sh], -FLAME_GROW)
    bots = soft([b for _, _, b in sh], FLAME_GROW)
    top = curve([(c, t) for (c, _, _), t in zip(sh, tops)])
    bot = curve([(c, b) for (c, _, _), b in zip(sh, bots)])
    x0, x1 = sh[0][0] - 0.3, sh[-1][0]
    st = []
    for x in frange(x0, x1, 0.5):
        hw = max(0.08, (bot(x) - top(x)) / 2)
        st.append((x, hw if x > x0 + 1e-6 else 0.0))
    ellipse_loft(bm, st, lambda x: (top(x) + bot(x)) / 2, ROD_Z, M["flame"], sides=10, zscale=0.9, zmax=1.55)
    # orange core, its top just above the sheath's
    core = spec["core"]
    crow = curve([(c, r) for c, r, _ in core])
    chw = curve([(c, w) for c, _, w in core])
    cst = [(x, max(0.06, chw(x))) for x in frange(core[0][0], core[-1][0], 0.4)]
    cst[0] = (cst[0][0], 0.0)
    cst[-1] = (cst[-1][0], 0.0)
    ellipse_loft(bm, cst, crow, ROD_Z + 0.6, M["core"], sides=8, zscale=1.0, zmax=1.15)
    sx, sr, ax, ay = spec["spot"]
    sides, rings = 12, []
    for i in range(7):
        t = math.pi * i / 6
        xx = sx - ax * math.cos(t)
        s = math.sin(t)
        if i in (0, 6):
            rings.append([bm.verts.new((X(xx), Y(sr), P(ROD_Z + 1.45)))])
        else:
            rings.append(ring(bm, [(X(xx), Y(sr) + P(ay * s) * math.cos(a), P(ROD_Z + 1.45) + P(0.45 * s) * math.sin(a))
                                   for a in (2 * math.pi * (k + 0.5) / sides for k in range(sides))]))
    bridge(bm, rings, M["spot"])
    # rear plume
    ellipse_loft(bm, PLUME[frame], lambda x: MIRROR, ROD_Z, M["plume"], sides=12, zscale=0.65, zmax=0.95)
    ellipse_loft(bm, [(20.9, 0.0), (21.2, 0.7), (22.0, 0.6), (22.6, 0.0)], lambda x: MIRROR, ROD_Z + 0.2,
                 M["plume_core"], sides=10, zscale=0.8)


# --- Materials ------------------------------------------------------------------------------------

def spec(mat, level):
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = level
    return mat


def materials(sprite):
    pal = common.palette_material
    defs = [
        # key, material
        ("blade_up", spec(pal(sprite, 7, NAME, metallic=0.3, roughness=0.4), 0.65)),
        ("blade_lo", spec(pal(sprite, 5, NAME, metallic=0.3, roughness=0.4), 0.65)),
        ("hub_up", spec(pal(sprite, 7, NAME + "-hub", metallic=0.35, roughness=0.34), 0.7)),
        ("hub_lo", spec(pal(sprite, 5, NAME + "-hub", metallic=0.35, roughness=0.34), 0.7)),
        ("rod", spec(pal(sprite, 6, NAME + "-rod", metallic=0.45, roughness=0.3), 0.75)),
        ("collar", spec(pal(sprite, 4, NAME + "-collar", metallic=0.6, roughness=0.4), 0.6)),
        ("flame", pal(sprite, 118, NAME, metallic=1.0, roughness=0.9, emission_strength=1.25)),
        ("core", pal(sprite, 121, NAME, metallic=1.0, roughness=0.9, emission_strength=1.05)),
        ("spot", pal(sprite, 123, NAME, metallic=1.0, roughness=0.9, emission_strength=1.0)),
        ("plume", pal(sprite, 118, NAME + "-plume", metallic=1.0, roughness=0.9, emission_strength=1.2,
                      frames={46: 120})),
        ("plume_core", pal(sprite, 121, NAME + "-plumecore", metallic=1.0, roughness=0.9, emission_strength=1.05,
                           frames={46: 122})),
    ]
    keys = [k for k, _ in defs]
    return {k: i for i, k in enumerate(keys)}, [m for _, m in defs]


def finish(name, bm, mats, coll, sharp_deg=24):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    me.shade_smooth()
    if sharp_deg:
        me.set_sharp_from_angle(angle=math.radians(sharp_deg))
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def tris(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def build():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    M, mats = materials(sprite)
    bm = bmesh.new()
    build_body(bm, M)
    body = finish(NAME, bm, mats, coll)
    objs = [body]
    manifest = {"body_tris": tris(body)}
    for f in FRAMES:
        bm = bmesh.new()
        build_flame(bm, f, M)
        fl = finish(f"{NAME}-flame-{f}", bm, mats, coll, sharp_deg=None)
        common.frame_part(fl, [f])
        objs.append(fl)
        manifest[f"flame_{f}_tris"] = tris(fl)
    # Outline shell from a sealed copy of the body (no grooves, no ports): ink on the silhouette only.
    bm = bmesh.new()
    build_body(bm, M, detail=False)
    seal = finish(NAME + "_seal", bm, mats, coll, sharp_deg=None)
    bpy.context.view_layer.update()
    shell = common.outline_shell(seal, coll, voxel=0.005, faces=1600, smooth=4, inside=0.002, islands="outer")
    bpy.data.objects.remove(seal, do_unlink=True)
    shell.name = f"{NAME}_outline"
    assert len(shell.data.polygons) > 0, "empty outline shell"
    manifest["shell_faces"] = len(shell.data.polygons)
    objs.append(shell)
    common.export_sprite_model(ROOT, objs, f"enemies/{NAME}", sprite["sprites"])
    out = arg("--out")
    if out:
        common.export_glb(objs, Path(out))
    print("MANIFEST", json.dumps(manifest))


if __name__ == "__main__":
    build()
