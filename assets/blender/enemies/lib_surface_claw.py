"""lib_surface_claw: shared builder of SURFACE's (Episode 4.4) mid-level guardian, a mirrored pair of
armoured spiked gauntlets (newsh^.shp, ten pieces on two rigid links, each claw 60x56 px). Used only by
assembly-newsh-caret-11.py (the right claw: 11, 13, 49, 50, 52) and assembly-newsh-caret-92.py (the left
claw: 92, 94, 129, 131, 133). Each wrapper exports only its own five pieces.

  right claw (screen x 214-274): 11 (2x2) | 13 (2x2) over 49 (1x1) | 50 (2x2) | 52 (2x2)
  left claw  (screen x -26..34): 92 (2x2) | 94 (2x2) over 129 (2x2) | 131 (2x2) | 133 (1x1)

Piece places from the enemy_behaviour trace (4.4 SURFACE) and tyrian2.c's draw: every piece is drawn
centred on (ex + 6, ey + 7). The left claw is the right one mirrored with its top-left (92's spikes and
knuckles) 2 px further right, built faired, not cut and shifted.

What it is (read from the sprite, light from the upper right on the right claw, mirrored on the left):
- A faceted grey armoured block, the back of a gauntlet: a crisp top plate, a broad sloped inner flank,
  a steep outer flank and a sloped wrist face behind a crease.
- A blue eye lens (11 x 7 px, tilted ~31 deg) set into the top plate in a dark socket.
- Four long steel spikes fanning up and inward from a row of knuckle bosses on the block's front.
The pale streaks are sheen, the ink ring and the dark flank are lighting: not modelled as paint.

The pieces are read straight from the game data with tools/sprite_data.py (newsh^.shp, palette 5):
reference/models/newsh-caret-11 and the others don't exist (the catalogue run stops before SURFACE's
guardian spawns at t 5900), so the spriteModels entries are written here.

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh-caret-11.py (and ...-92.py)
Each piece exports to public/models/enemies/<piece>.glb at its own origin, with its outline shell, and
src/render/spriteModels/<piece>.json. A normal build writes nothing else; `--review DIR` also writes
review renders and top-view masks to DIR.
"""

import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve()


def _repo():
    for p in HERE.parents:
        if (p / "package.json").exists() and (p / "assets" / "blender" / "common.py").exists():
            return p
    env = os.environ.get("TYRIAN_REPO")
    if env and (Path(env) / "assets" / "blender" / "common.py").exists():
        return Path(env)
    raise SystemExit("can't find the repo: run from assets/blender/enemies/ or set TYRIAN_REPO")


ROOT = _repo()
WT = ROOT
sys.path.insert(0, str(ROOT / "assets" / "blender"))
sys.path.insert(0, str(ROOT / "tools"))
import common  # noqa: E402
import sprite_data  # noqa: E402

NAME = "lib_surface_claw"
TAG = "nshclaw"
PX = 1 / 12
SHEET = "newsh^.shp"
PALETTE = 5

# (model, sprite index, size 1|2, ex, ey) from the trace; top-left = (ex-6, ey-7) for 2x2, (ex, ey) for
# 1x1; the model's origin is the piece centre (ex + 6, ey + 7).
RIGHT = [("newsh-caret-11", 11, 2, 220, -28), ("newsh-caret-13", 13, 2, 244, -28),
         ("newsh-caret-49", 49, 1, 214, -7), ("newsh-caret-50", 50, 2, 232, 0),
         ("newsh-caret-52", 52, 2, 256, 0)]
LEFT = [("newsh-caret-92", 92, 2, -6, -28), ("newsh-caret-94", 94, 2, 16, -28),
        ("newsh-caret-129", 129, 2, -20, 0), ("newsh-caret-131", 131, 2, 4, 0),
        ("newsh-caret-133", 133, 1, 22, -7)]
RIGHT_TL = (214, -35)   # each claw's 60x56 box, top-left in screen px
LEFT_TL = (-26, -35)
CLAW_W, CLAW_H = 60, 56


# ---- sprite data (tools/sprite_data.py: decoded from the game data; the catalogue has no folder) --

def _sheet():
    return sprite_data.data_file(ROOT, SHEET).read_bytes()


def sprite_pixels(sheet, index, size):
    return sprite_data.compose(sheet, size, index)


def palette(k):
    return [tuple(c) for c in sprite_data.palette_rgb(ROOT, k)]


def piece_boxes(pieces, tl):
    """[(model, index, size, u0, v0, w, h, cu, cv)] in claw-local px (u right, v down)."""
    out = []
    for name, idx, size, ex, ey in pieces:
        x0, y0 = (ex - 6, ey - 7) if size == 2 else (ex, ey)
        w, h = (24, 28) if size == 2 else (12, 14)
        out.append((name, idx, size, x0 - tl[0], y0 - tl[1], w, h, ex + 6 - tl[0], ey + 7 - tl[1]))
    return out


def composite(pieces, tl):
    sheet = _sheet()
    idx = [[-1] * CLAW_W for _ in range(CLAW_H)]
    for name, i, size, u0, v0, w, h, cu, cv in piece_boxes(pieces, tl):
        for y, row in enumerate(sprite_pixels(sheet, i, size)):
            for x, val in enumerate(row):
                if val >= 0:
                    idx[v0 + y][u0 + x] = val
    return idx


# ---- coordinates (claw-local pixel edges; built for the right claw) --------------------------------

def X(u):
    return u * PX


def Y(v):
    return -v * PX


def pchip(xs, ys):
    """Monotone cubic interpolation through (xs, ys) (Fritsch-Carlson)."""
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
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(n - 1) if xs[k] <= x)
        t = (x - xs[i]) / h[i]
        h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
        h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


# ---- mesh helpers -----------------------------------------------------------------------------------

def add_hull(bm, pts, mat, smooth=False):
    tmp = bmesh.new()
    for p in pts:
        tmp.verts.new(p)
    res = bmesh.ops.convex_hull(tmp, input=tmp.verts[:])
    junk = [g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)]
    if junk:
        bmesh.ops.delete(tmp, geom=list(set(junk)), context="VERTS")
    bmesh.ops.dissolve_limit(tmp, angle_limit=math.radians(0.5), verts=tmp.verts[:], edges=tmp.edges[:])
    for f in tmp.faces:
        f.material_index = mat
        f.smooth = smooth
    me = bpy.data.meshes.new("_tmp")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def add_mesh(bm, build):
    tmp = bmesh.new()
    build(tmp)
    me = bpy.data.meshes.new("_tmp")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def ellipsoid(bm, c, rx, ry, rz, mat, segs=20, rings=10, zmin=-1.0, rot=0.0):
    """Ellipsoid at Blender point c with radii in units, rotated `rot` rad about Z; zmin flattens."""
    tmp = bmesh.new()
    bmesh.ops.create_uvsphere(tmp, u_segments=segs, v_segments=rings, radius=1.0)
    cr, sr = math.cos(rot), math.sin(rot)
    for vv in tmp.verts:
        z = max(vv.co.z, zmin)
        x, y = vv.co.x * rx, vv.co.y * ry
        vv.co = Vector((c[0] + x * cr - y * sr, c[1] + x * sr + y * cr, c[2] + z * rz))
    for f in tmp.faces:
        f.material_index = mat
        f.smooth = True
    me = bpy.data.meshes.new("_tmp")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def lathe(bm, p0, p1, prof, mat, sides=12, smooth=True, cap0=True, cap1=True, sharp=()):
    """A solid of revolution along p0 -> p1 (Blender points). prof: [(t 0..1, radius units)];
    a radius of 0 is a point. `sharp`: profile indices whose ring is a hard edge."""
    p0, p1 = Vector(p0), Vector(p1)
    axis = (p1 - p0)
    ln = axis.length
    a = axis.normalized()
    ref = Vector((0, 0, 1)) if abs(a.z) < 0.9 else Vector((1, 0, 0))
    s = a.cross(ref).normalized()
    up = s.cross(a).normalized()
    rings = []
    for t, r in prof:
        c = p0 + a * (t * ln)
        if r <= 0:
            rings.append([bm.verts.new(c)])
        else:
            rings.append([bm.verts.new(c + s * (r * math.cos(2 * math.pi * k / sides))
                                       + up * (r * math.sin(2 * math.pi * k / sides))) for k in range(sides)])
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for k in range(sides):
            j = (k + 1) % sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                f = bm.faces.new((r0[0], r1[j], r1[k]))
            elif len(r1) == 1:
                f = bm.faces.new((r0[k], r0[j], r1[0]))
            else:
                f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = mat
            f.smooth = smooth
    if cap0 and len(rings[0]) > 1:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = mat
        f.smooth = False
    if cap1 and len(rings[-1]) > 1:
        f = bm.faces.new(rings[-1])
        f.material_index = mat
        f.smooth = False
    for i in sharp:
        r = rings[i]
        if len(r) > 1:
            for k in range(sides):
                e = bm.edges.get((r[k], r[(k + 1) % sides]))
                if e is not None:
                    e.smooth = False
    return rings


def bm_object(name, bm, mats, coll):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def apply_mods(obj):
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def boolean(target, cutter, op="DIFFERENCE"):
    mod = target.modifiers.new("b", "BOOLEAN")
    mod.operation = op
    mod.object = cutter
    mod.solver = "EXACT"
    mod.material_mode = "INDEX"
    apply_mods(target)


# ---- the design (right claw, claw-local px) ----------------------------------------------------------

# The armour block is a loft (fix round 1: it was a convex hull cut to a prism, which read as a
# triangulated blob with shard-like walls). Stations run from the knuckle row (front, upper left) to
# the wrist (rear, lower right). Each station is a straight line from the lower-left flank's edge
# (LB) to the upper-right flank's edge (RB) carrying one chamfered cross-section: skirt, broad sloped
# inner flank, chamfer, top plate, a raised plate break, the sheen ridge, a steep outer flank, skirt.
# LB and RB are the inner edge of the sprite's ink (the silhouette), so the skirt stands on the
# sprite's line all the way round as one continuous wall; the knuckle housings cover the front.
LB = [(16.0, 31.4), (16.2, 34.2), (17.6, 36.2), (36.0, 54.6), (39.5, 55.6), (44.0, 55.8)]
RB = [(35.5, 17.2), (38.6, 20.5), (41.0, 23.8), (44.4, 25.3), (46.6, 27.6), (48.6, 30.7), (51.6, 33.6),
      (52.9, 38.1), (58.9, 44.5), (58.9, 50.5)]
LB_CORNER, RB_CORNER = 3, 8
# Station keys: (lambda, arc px along LB, arc px along RB). 0.80 is the wrist crease the sprite shows
# running from (54.7, 40.3) to (39, 56); behind it the wrist face slopes down to the rear edge.
LAM_CREASE = 0.80
CREASE_PTS = ((39.0, 56.0), (54.7, 40.3))
SEAM_LAM = 0.24          # transverse plate seam behind the knuckle housings
# Cross-section: (fraction of the station width from LB, z key). z keys are resolved per station.
SECTION = [(0.085, "bot"), (0.0, "foot"), (0.0, "skirtL"), (0.04, "chamL"), (0.25, "flank"),
           (0.285, "plateE"), (0.42, "plate"), (0.555, "plate"), (0.585, "plate"), (0.612, "brk"),
           (0.75, "brk"), (0.865, "brk"), (0.895, "ridge"), (0.955, "outer"), (1.0, "skirtR"),
           (1.0, "foot"), (0.915, "bot")]
GROOVE_IDX = range(3, 15)   # section points pressed down in a seam groove
# Knuckle bulges where the spikes root (u, v, radius px, z centre)
BOSSES = [(34.2, 21.2, 3.2, 0.60), (28.3, 22.9, 2.9, 0.58), (23.2, 27.2, 2.6, 0.52), (19.3, 31.7, 2.5, 0.46)]
# Spikes (axes fitted to the sprite's inner mask): root (u, v, z), tip (u, v, z), radius px at the
# root, the middle and near the tip
SPIKES = [((33.8, 20.8, 0.68), (35.0, 0.3, 1.20), (2.15, 1.80, 0.85)),
          ((28.3, 22.4, 0.66), (17.5, 1.0, 1.12), (2.25, 1.65, 0.85)),
          ((22.3, 27.0, 0.60), (4.8, 6.9, 1.02), (2.10, 1.60, 0.85)),
          ((18.1, 32.4, 0.54), (-0.2, 18.4, 0.90), (2.20, 1.40, 0.85))]
# The left claw's spikes, fitted to its own sprite (mirrors of the above, 92's two moved 2 px right;
# its second spike runs from 92 into 94 and leans 3.6 deg steeper than the mirror)
LEFT_SPIKES = [((28.5, 20.8), (26.85, 0.3)), ((34.1, 22.4), (41.3, 1.0)), ((38.0, 27.0), (55.2, 6.9)),
               ((41.9, 32.4), (60.0, 18.4))]
# Eye: centre (u, v), radii px (major, minor) of the blue lens, major axis angle (rad, screen: +u
# right, +v down); the dark 4 ring round it is a raised socket bezel BEZEL px wide.
EYE = dict(u=40.1, v=40.1, a=5.5, b=3.5, ang=math.atan2(-0.52, 0.85))
BEZEL = 1.4

# The left claw is this one mirrored (u -> 60 - u); 92's part (its spikes and knuckles: u < 37,
# v < 28 after mirroring) sits 2 px further right. The block's sprite rows >= 28 are exact mirrors, so
# the block takes the shift only at its front, eased in over 1.5 px (no tear).
MIRROR_U = 60.0
SHIFT92 = 2.0


def left_xform(u, v, region92):
    u = MIRROR_U - u
    if region92:
        u += SHIFT92
    return u, v


def in92(u_mirrored, v):
    return u_mirrored < 37.0 and v < 28.0


def _smooth01(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def left_xform_soft(u, v):
    um = MIRROR_U - u
    w = _smooth01((28.6 - v) / 1.6) * _smooth01((38.0 - um) / 1.5)
    return um + SHIFT92 * w, v


def materials(colors):
    sprite = {"name": NAME, "colors": {str(i): list(c) for i, c in enumerate(colors)}}

    def pal(i, metallic, rough, emission=0.0, spec=None):
        m = common.palette_material(sprite, i, TAG, metallic=metallic, roughness=rough, emission_strength=emission)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if spec is not None and "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    spec = [
        # block: the sprite's median is 5 with the shadowed inner flank (3-4) in it and lit plates at 7;
        # 6 with a satin, less metallic finish so it lands on the sprite's mid grey in the game
        ("armour", 6, 0.35, 0.42, 0.0),
        ("boss", 5, 0.7, 0.36, 0.0),      # knuckle bulges (dark 3-7 cluster)
        ("collar", 4, 0.8, 0.40, 0.0),    # knuckle housing cuffs
        ("spike", 9, 1.0, 0.28, 0.0),     # spikes: median 8-9, polished steel
        ("socket", 4, 0.6, 0.50, 0.0),    # eye socket bezel (the sprite's dark ring, 4)
        ("lens", 53, 1.0, 0.38, 1.0),     # eye lens: blue median 53, glowing (D126/D173)
        ("seam", 3, 0.6, 0.55, 0.0),      # socket floor
    ]
    mats, M = [], {}
    by = {}
    for key, i, met, r, em in spec:
        sig = (i, met, r, em)
        if sig not in by:
            by[sig] = len(mats)
            m = pal(i, met, r, em)
            mats.append(m)
        M[key] = by[sig]
    return mats, M


# ---- the lofted block ----------------------------------------------------------------------------------

def _arc(poly):
    s = [0.0]
    for (a, b), (c, d) in zip(poly, poly[1:]):
        s.append(s[-1] + math.hypot(c - a, d - b))
    return s


def _at(poly, arc, t):
    t = min(max(t, 0.0), arc[-1])
    for i in range(len(poly) - 1):
        if arc[i + 1] >= t:
            k = (t - arc[i]) / max(arc[i + 1] - arc[i], 1e-9)
            return (poly[i][0] + (poly[i + 1][0] - poly[i][0]) * k, poly[i][1] + (poly[i + 1][1] - poly[i][1]) * k)
    return poly[-1]


def _closest_arc(poly, arc, p):
    best = (1e9, 0.0)
    for i in range(len(poly) - 1):
        (a, b), (c, d) = poly[i], poly[i + 1]
        dx, dy = c - a, d - b
        L2 = dx * dx + dy * dy
        k = max(0.0, min(1.0, ((p[0] - a) * dx + (p[1] - b) * dy) / L2))
        q = (a + dx * k, b + dy * k)
        dd = math.hypot(q[0] - p[0], q[1] - p[1])
        if dd < best[0]:
            best = (dd, arc[i] + k * math.sqrt(L2))
    return best[1]


def _boundary(poly, crease_pt):
    arc = _arc(poly)
    ac = _closest_arc(poly, arc, crease_pt)

    def f(lam):
        if lam <= LAM_CREASE:
            return _at(poly, arc, ac * lam / LAM_CREASE)
        return _at(poly, arc, ac + (arc[-1] - ac) * (lam - LAM_CREASE) / (1 - LAM_CREASE))
    return f


_ZT = None


def ztop(lam):
    global _ZT
    if _ZT is None:
        _ZT = pchip([0.0, 0.06, 0.25, 0.55, LAM_CREASE], [0.50, 0.62, 0.70, 0.71, 0.69])
    if lam <= LAM_CREASE:
        return _ZT(lam)
    k = (lam - LAM_CREASE) / (1 - LAM_CREASE)
    return 0.69 - 0.27 * (k ** 1.15)


def _zkey(key, zt):
    s = zt / 0.70
    return {"bot": -0.02, "foot": 0.06, "skirtL": 0.20 * s, "chamL": 0.29 * s, "flank": zt - 0.075,
            "plateE": zt - 0.008, "plate": zt + 0.008, "brk": zt + 0.048, "ridge": zt + 0.018,
            "outer": zt - 0.17, "skirtR": max(zt - 0.33, 0.10)}[key]


def _stations():
    lams = [0.0, 0.012]
    n = 34
    for i in range(1, n):
        lams.append(i / n)
    for c in (SEAM_LAM, LAM_CREASE):
        lams = [x for x in lams if abs(x - c) > 0.02]
        lams += [c - 0.007, c, c + 0.007]
    lams += [0.988, 1.0]
    lams = sorted(set(round(x, 5) for x in lams))
    out = []
    for x in lams:
        kind = "groove" if any(abs(x - c) < 1e-6 for c in (SEAM_LAM, LAM_CREASE)) else "plain"
        if x in (0.0, 1.0):
            kind = "end"
        out.append((x, kind))
    return out


def loft_block(xfb, mat, smooth_angle=20.0):
    """The armour block as a closed bmesh in claw-local Blender coords."""
    fl, fr = _boundary(LB, CREASE_PTS[0]), _boundary(RB, CREASE_PTS[1])
    bm = bmesh.new()
    rings = []
    for lam, kind in _stations():
        L, R = fl(lam), fr(lam)
        zt = ztop(lam)
        ring = []
        for j, (f, key) in enumerate(SECTION):
            u, v = L[0] + (R[0] - L[0]) * f, L[1] + (R[1] - L[1]) * f
            z = _zkey(key, zt)
            if kind == "groove" and j in GROOVE_IDX:
                z -= 0.028
            if kind == "end" and z > 0.07:
                z = 0.07 + (z - 0.07) * 0.86
            uu, vv = xfb(u, v)
            ring.append(bm.verts.new((X(uu), Y(vv), z)))
        rings.append(ring)
    n = len(SECTION)
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(n):
            k = (j + 1) % n
            f = bm.faces.new((r0[j], r0[k], r1[k], r1[j]))
            f.material_index = mat
            f.smooth = True
    for ring in (rings[0], rings[-1]):
        f = bm.faces.new(ring)
        f.material_index = mat
        f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], ngon_method="BEAUTY")
    # hard chamfer edges, smooth plates: split edges sharper than smooth_angle
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(smooth_angle):
            e.smooth = False
    return bm


def _ellipse_ring(bm, cx, cy, a, b, rot, zfn, segs):
    cr, sr = math.cos(rot), math.sin(rot)
    out = []
    for k in range(segs):
        t = 2 * math.pi * k / segs
        x, y = a * math.cos(t), b * math.sin(t)
        px, py = cx + x * cr - y * sr, cy + x * sr + y * cr
        out.append(bm.verts.new((px, py, zfn(px, py))))
    return out


def eye_socket(bm_out, cx, cy, rot, zs, M, segs=40):
    """Raised elliptic bezel round a recessed floor, the glowing lens dome in it. cx, cy Blender;
    zs(x, y) the block's surface height."""
    a, b = EYE["a"] * PX, EYE["b"] * PX
    w = BEZEL * PX
    zmax = max(zs(cx + (a + w) * math.cos(t) * math.cos(rot) - (b + w) * math.sin(t) * math.sin(rot),
                  cy + (a + w) * math.cos(t) * math.sin(rot) + (b + w) * math.sin(t) * math.cos(rot))
               for t in [2 * math.pi * k / 24 for k in range(24)])
    zmax = max(zmax, zs(cx, cy))
    zb = zmax + 0.06
    zf = zb - 0.058
    tmp = bmesh.new()
    prof = [(a + w + 0.45 * PX, lambda x, y: zs(x, y) - 0.03, b + w + 0.45 * PX),
            (a + w, lambda x, y: zb - 0.012, b + w),
            (a + w - 0.4 * PX, lambda x, y: zb, b + w - 0.4 * PX),
            (a + 0.4 * PX, lambda x, y: zb, b + 0.4 * PX),
            (a, lambda x, y: zb - 0.016, b),
            (a, lambda x, y: zf, b)]
    rings = [_ellipse_ring(tmp, cx, cy, ra, rb, rot, zfn, segs) for ra, zfn, rb in prof]
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            f = tmp.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = M["socket"]
    top = tmp.verts.new((cx, cy, zf))
    bot = tmp.verts.new((cx, cy, zf - 0.12))
    for k in range(segs):
        j = (k + 1) % segs
        f = tmp.faces.new((rings[-1][k], rings[-1][j], top))
        f.material_index = M["seam"]
        f = tmp.faces.new((rings[0][j], rings[0][k], bot))
        f.material_index = M["socket"]
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces[:])
    for f in tmp.faces:
        f.smooth = True
    for i in (1, 2, 3, 4, 5):
        for k in range(segs):
            e = tmp.edges.get((rings[i][k], rings[i][(k + 1) % segs]))
            if e is not None and i in (2, 3, 5):
                e.smooth = False
    me = bpy.data.meshes.new("_tmp")
    tmp.to_mesh(me)
    tmp.free()
    bm_out.from_mesh(me)
    bpy.data.meshes.remove(me)
    # the lens: a low glowing dome sitting on the floor, under the bezel top
    ellipsoid(bm_out, (cx, cy, zf - 0.004), a - 0.15 * PX, b - 0.15 * PX, 0.048, M["lens"],
              segs=32, rings=10, zmin=0.0, rot=rot)


def build_claw(coll, mats, M, side, detail=True, name=None):
    """One claw as a single mesh object in claw-local Blender coords."""
    if side == "right":
        def xf(u, v):
            return u, v
        xfb = xf
    else:
        def xf(u, v):
            um = MIRROR_U - u
            return left_xform(u, v, in92(um, v))
        xfb = left_xform_soft
    name = name or f"claw_{side}"
    bm = loft_block(xfb, M["armour"])
    block = bm_object(name + "_block", bm, mats, coll)
    bm.free()
    tree = BVHTree.FromObject(block, bpy.context.evaluated_depsgraph_get())

    def zs_xy(x, y):
        h = tree.ray_cast(Vector((x, y, 5.0)), Vector((0, 0, -1)))
        return h[0].z if h[0] is not None else 0.0

    bm = bmesh.new()
    bm.from_mesh(block.data)
    # knuckle bulges, sunk into the block's front
    for (u, v, r, z) in BOSSES:
        uu, vv = xf(u, v)
        ellipsoid(bm, (X(uu), Y(vv), z), r * PX, r * PX, 0.17, M["boss"], segs=20, rings=10, zmin=-0.6)
    # spikes, each rooted in a machined knuckle housing (a stepped cuff round the root)
    for si, ((ru, rv, rz), (tu, tv, tz), (rb, rm, rt)) in enumerate(SPIKES):
        if side == "right":
            a = (X(ru), Y(rv), rz)
            b = (X(tu), Y(tv), tz)
        else:
            (u0, v0), (u1, v1) = LEFT_SPIKES[si]
            a, b = (X(u0), Y(v0), rz), (X(u1), Y(v1), tz)
        ln = (Vector(b) - Vector(a)).length / PX  # length in px
        tr = [0.0, 0.5, 1.0 - 1.6 / ln]
        fr = pchip(tr, [rb, rm, rt])
        prof = [(0.0, rb * PX * 0.9)]
        for k in range(0, 11):
            t = tr[-1] * k / 10
            prof.append((t, fr(t) * PX))
        prof.append((1.0 - 0.5 / ln, rt * 0.45 * PX))
        prof.append((1.0, 0.0))
        lathe(bm, a, b, prof, M["spike"], sides=12, cap0=True, cap1=False)
        if detail:
            A, B = Vector(a), Vector(b)
            d = (B - A).normalized()
            c0 = A - d * 0.06
            lathe(bm, c0, c0 + d * 0.30, [(0.0, rb * PX * 1.18), (0.42, rb * PX * 1.24), (0.55, rb * PX * 1.14),
                                          (0.80, rb * PX * 1.12), (1.0, rb * PX * 0.98)],
                  M["collar"], sides=16, sharp=(1, 2, 3))
    if detail:
        eu, ev = xf(EYE["u"], EYE["v"])
        ang = EYE["ang"] if side == "right" else math.pi - EYE["ang"]
        eye_socket(bm, X(eu), Y(ev), -ang, zs_xy, M)
    bm.to_mesh(block.data)
    bm.free()
    block.name = name
    return block


# ---- split into pieces ------------------------------------------------------------------------------

def split(obj, boxes, cuts, coll, suffix=""):
    """One object per piece: the part of `obj` (claw-local) inside the piece's box (u0..u1, v0..v1 in
    px, from `cuts`), cut faces filled, moved so the piece centre is the origin."""
    out = {}
    for (name, idx, size, u0, v0, w, h, cu, cv) in boxes:
        a0, a1, b0, b1 = cuts[name]
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((X(a0), 0, 0), (-1, 0, 0)), ((X(a1), 0, 0), (1, 0, 0)),
                       ((0, Y(b0), 0), (0, 1, 0)), ((0, Y(b1), 0), (0, -1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
            edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if edges:
                filled = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
                for f in filled["faces"]:
                    f.smooth = False
        bmesh.ops.translate(bm, vec=(-X(cu), -Y(cv), 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        p = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(p)
        out[name] = p
    return out


def cuts_for(boxes):
    """Each piece's box; where two boxes overlap (92/94) the cut runs down the middle of the overlap."""
    cuts = {}
    for b in boxes:
        name, _, _, u0, v0, w, h, _, _ = b
        a0, a1, b0, b1 = u0, u0 + w, v0, v0 + h
        for o in boxes:
            if o is b:
                continue
            ou0, ov0, ow, oh = o[3], o[4], o[5], o[6]
            if ov0 < b1 and ov0 + oh > b0 and ou0 < a1 and ou0 + ow > a0:
                mid = (max(a0, ou0) + min(a1, ou0 + ow)) / 2
                if ou0 > a0:
                    a1 = min(a1, mid)
                else:
                    a0 = max(a0, mid)
        cuts[name] = (a0, a1, b0, b1)
    return cuts


def sink_shell(shell, model, margin, reach):
    """Keep the outline shell under the model's top surface (ink on the silhouette only); copied from
    assembly-newsh-caret-54 (originally newshv-10.py, D185)."""
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            a = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
    shell.data.update()


# ---- review (only with --review) --------------------------------------------------------------------

def review(out_dir, claws, pieces_by_side):
    import numpy as np  # noqa: F401  (Blender ships numpy)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("rv") if not scene.world else scene.world
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.25, 0.27, 0.30, 1)
    bg.inputs[1].default_value = 0.6
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 3.2
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    # light from the upper left, high (the game's sun is overhead-ish from the top left)
    sun.rotation_euler = (math.radians(40), 0, math.radians(35))
    fill_d = bpy.data.lights.new("fill", "SUN")
    fill_d.energy = 0.8
    fill = bpy.data.objects.new("fill", fill_d)
    scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(60), 0, math.radians(-150))

    cam_d = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam

    def shoot(path, loc, look, ortho=None, res=(640, 600), lens=50):
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.resolution_percentage = 100
        cam.location = Vector(loc)
        d = Vector(look) - Vector(loc)
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        if ortho:
            cam_d.type = "ORTHO"
            cam_d.ortho_scale = ortho
        else:
            cam_d.type = "PERSP"
            cam_d.lens = lens
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    info = {}
    for side, (objs, shells) in pieces_by_side.items():
        allobj = [o for o in bpy.data.objects if o.type == "MESH"]
        for o in allobj:
            o.hide_render = o not in objs and o not in shells
        cx, cy = X(CLAW_W / 2), Y(CLAW_H / 2)
        # pieces are placed in claw-local coords for review
        # top mask (no shells) at k=8 px per sprite px, ortho exactly over the 60x56 box
        for s in shells:
            s.hide_render = True
        k = 8
        scene.render.resolution_x, scene.render.resolution_y = CLAW_W * k, CLAW_H * k
        cam_d.type = "ORTHO"
        cam_d.ortho_scale = CLAW_W * PX
        cam.location = Vector((cx, cy, 10))
        cam.rotation_euler = (0, 0, 0)
        scene.render.filepath = str(out / f"{side}_top_mask.png")
        bpy.ops.render.render(write_still=True)
        # the outline shells stay hidden: the game draws them only in its outline pass, and a plain
        # render of a shell held 0.01 inside the walls z-fights them into black streaks
        R = 5.6
        shoot(out / f"{side}_top.png", (cx, cy, 10), (cx, cy, 0), ortho=R * 1.0, res=(600, 560))
        shoot(out / f"{side}_side.png", (cx + 12, cy, 0.35), (cx, cy, 0.35), ortho=R, res=(600, 300))
        shoot(out / f"{side}_front.png", (cx, cy + 12, 0.35), (cx, cy, 0.35), ortho=R, res=(600, 300))
        shoot(out / f"{side}_rear.png", (cx, cy - 12, 0.35), (cx, cy, 0.35), ortho=R, res=(600, 300))
        shoot(out / f"{side}_q34.png", (cx + 6, cy - 7, 6), (cx, cy, 0.2), lens=50, res=(600, 560))
        shoot(out / f"{side}_q34b.png", (cx - 7, cy + 6, 5), (cx, cy, 0.2), lens=50, res=(600, 560))
        shoot(out / f"{side}_game.png", (cx, cy - 6.5, 11.5), (cx, cy, 0.0), lens=55, res=(600, 560))
        shoot(out / f"{side}_under.png", (cx, cy, -10), (cx, cy, 0), ortho=R, res=(600, 560))
    return info


# ---- main --------------------------------------------------------------------------------------------

SHELL_FACES = {1: 400, 2: 1200}  # outline shell budget per piece size (boss budget incl. shells)
SIDES = {"right": (RIGHT, RIGHT_TL), "left": (LEFT, LEFT_TL)}


def run(side, argv):
    """Build one claw ('right' or 'left') and export its five pieces."""
    review_dir = argv[argv.index("--review") + 1] if "--review" in argv else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(f"assembly-newsh-caret-{'11' if side == 'right' else '92'}")
    colors = palette(PALETTE)
    mats, M = materials(colors)
    pieces, tl = SIDES[side]
    claw = build_claw(coll, mats, M, side)
    plain = build_claw(coll, mats, M, side, detail=False, name=f"claw_{side}_plain")
    boxes = piece_boxes(pieces, tl)
    cuts = cuts_for(boxes)
    parts = split(claw, boxes, cuts, coll)
    sealed = split(plain, boxes, cuts, coll, suffix="_sealed")
    print("CLAW", side, "TRIS", sum(len(p.vertices) - 2 for p in claw.data.polygons))
    objs, shells = [], []
    for b in boxes:
        name, cu, cv = b[0], b[7], b[8]
        p, src = parts[name], sealed[name]
        bpy.context.view_layer.update()
        sh = common.outline_shell(src, coll, voxel=0.016, faces=SHELL_FACES[b[2]], inside=0.01, islands="outer")
        sh.name = sh.data.name = f"{name}_outline"
        sink_shell(sh, src, margin=0.03, reach=0.08)
        if len(sh.data.vertices) == 0:
            raise SystemExit(f"empty outline shell for {name}")
        bpy.data.objects.remove(src, do_unlink=True)
        print("PIECE", name, "tris", sum(len(q.vertices) - 2 for q in p.data.polygons),
              "shell verts", len(sh.data.vertices))
        es = p.modifiers.new("split", "EDGE_SPLIT")
        es.use_edge_angle = False
        es.use_edge_sharp = True
        apply_mods(p)
        objs.append(p)
        shells.append(sh)
        p.location = sh.location = (X(cu), Y(cv), 0)  # claw-local, for review
    bpy.data.objects.remove(claw, do_unlink=True)
    bpy.data.objects.remove(plain, do_unlink=True)
    bpy.context.view_layer.update()
    if review_dir:
        review(review_dir, None, {side: (objs, shells)})
    for p, sh, b in zip(objs, shells, boxes):
        p.location = sh.location = (0, 0, 0)
        common.export_sprite_model(WT, [p, sh], f"enemies/{b[0]}",
                                   [{"sheet": SHEET, "size": b[2], "frames": [b[1]]}])
