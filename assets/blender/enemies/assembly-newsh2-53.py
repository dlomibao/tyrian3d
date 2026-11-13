"""Red machinery block (newsh2.shp frames 15, 17, 53, 55 in a 2x2): a 3D version of its sprites.

Seen in levels 1.30 and 3.17. Four 2x2 enemies (types 42-45, 12 armour) make one 48 x 56 px block of
machinery set into grey rock (sprite.json `assemblyLayout`): a red elbow pipe and a chrome-coupled top
pipe, two glowing orange canister lights, a red tower, a brass lens box with a red lens, twin red
vented panels, a gunmetal housing with a plank hatch and louvres framed by red trim (the "P"), a drum
with a bronze sleeve and brass strut, a red saddle block, brown posts and rods, ringed by island
rock and sand.

A hard-surface rebuild in the manner of the USP Talon and the player ships (DECISIONS.md D50-D53).
Every part is drawn in sprite pixels: c = column, r = row (pixel EDGES of the 48 x 56 grid), z = px
above the rock ground; Blender X = (c - 24) / 12, Y = (28 - r) / 12, Z = (z + ZOFF) / 12. The red
masses, the housing, the lens box frame and the "P" stem are armour plates over a dark core with real
gaps (modelled panel lines); hex bolt heads in the plates' own paint; bolted pipe flanges (the big
elbow into the lens box, the top pipe's flange disc); stanchions under the elbow; louvred tower
flanks and housing louvres; the lower annex split along its slant as the sprite draws it.

Sprite authority (tools/calibration/rubric.md): the top view covers the whole 48 x 56 rectangle (the
sprite is opaque everywhere); each part's palette index is the sprite's own median over that part
(darkest and brightest 15 % dropped: shading and sheen); satin metal. Bright spots are sheen: no
geometry for them. The rock and sand round the machine are island rock: the sprite's own pixels as
the islands' relief (lib_tiles.sprite_rock, DECISIONS.md D66) at the rock ground (z = 0), one rock
object per piece with no outline and no shadow, so the block stands in the island instead of in a
rimmed tray. The machine's underside has no detail.

No concept projection bake (maps.json says "bake": "model", so texture_bake.py skips it, like the
player ships in #84): plain palette materials, the detail is modelled.

Game contract: palette materials pal_<index>_nsh2a53<finish>; the whole block is built once, clipped
to the rectangle and cut into the four pieces newsh2-15 / -17 / -53 / -55 with common.split_assembly
at the layout's centres (pivots = piece centres), each exported as enemies/<piece> with its own
spriteModels entry and its one sprite frame, plus an outline shell per piece (common.outline_shell,
D51) round its machine, and its rock. No engines.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-53.py [-- --preview out.png]
(the preview is the whole block; each piece also gets <piece>.png next to it).
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent),
                str(Path(__file__).resolve().parents[1] / "tiles")]
import common  # noqa: E402
import lib_b053 as lib  # noqa: E402
import lib_tiles as lt  # noqa: E402

NAME = "assembly-newsh2-53"
ROOT = common.repo_root(__file__)
GW, GH = 48, 56
PX = 1 / 12
ZOFF = -1.5  # the rock ground (z = 0 px) sits 1.5 px below the origin; machinery up to ~9.5 px above it
BED = -2.4  # how far below the rock ground parts are cut off (px)
TAG = "nsh2a53"



def P(c, r, z):
    return Vector(((c - GW / 2) * PX, (GH / 2 - r) * PX, (z + ZOFF) * PX))


# ------------------------------------------------------------------------------------------------
# palette families and the sprite median of a part (shading and sheen dropped)
# ------------------------------------------------------------------------------------------------

def fam(i):
    if 65 <= i <= 78:
        return "red"
    if 116 <= i <= 125:
        return "orange"
    if 22 <= i <= 28:
        return "gold"
    if 163 <= i <= 166:
        return "brown"
    if 167 <= i <= 173:
        return "sand"
    if 80 <= i <= 106:
        return "blue"
    return "grey"


FAMSET = {
    "grey": lambda i: 1 <= i <= 15, "red": lambda i: fam(i) == "red",
    "orange": lambda i: fam(i) == "orange", "gold": lambda i: fam(i) == "gold",
    "brown": lambda i: 162 <= i <= 166, "sand": lambda i: fam(i) == "sand",
    "blue": lambda i: fam(i) == "blue", "darkbrown": lambda i: i == 16 or 160 <= i <= 163,
}


class Ctx:
    pass


C = Ctx()


def lum(i):
    r, g, b = C.colors[str(i)]
    return 0.299 * r + 0.587 * g + 0.114 * b


def median(family, rects):
    px = []
    for c0, r0, c1, r1 in rects:
        for r in range(max(0, math.floor(r0)), min(GH, math.ceil(r1))):
            for c in range(max(0, math.floor(c0)), min(GW, math.ceil(c1))):
                v = C.grid[r][c]
                if v >= 0 and FAMSET[family](v):
                    px.append(v)
    if not px:
        return None
    px.sort(key=lambda a: (lum(a), a))
    k = int(len(px) * 0.15) if len(px) >= 5 else 0
    t = px[k:len(px) - k]
    return t[(len(t) - 1) // 2]


# ------------------------------------------------------------------------------------------------
# materials: one per (palette index, finish)
# ------------------------------------------------------------------------------------------------

FINISH = {  # metallic, roughness, emission
    "rock": (0.0, 0.88, 0), "sand": (0.0, 0.95, 0), "deck": (0.25, 0.75, 0),
    "paint": (0.3, 0.42, 0), "metal": (0.75, 0.36, 0), "gun": (0.6, 0.5, 0),
    "brass": (0.65, 0.4, 0), "dark": (0.3, 0.7, 0), "glow": (0.0, 0.4, 4.0),
    "lens": (0.1, 0.12, 0), "chrome": (0.9, 0.22, 0),
}


def mat_slot(index, finish):
    key = (index, finish)
    if key not in C.slots:
        met, rough, em = FINISH[finish]
        m = common.palette_material(C.sprite, index, TAG + finish, metallic=met, roughness=rough,
                                    emission_strength=em)
        C.slots[key] = len(C.mats)
        C.mats.append(m)
    return C.slots[key]


PARTS = []


def g(f, rects):
    return (f, rects)


def resolve(pal, finish):
    if isinstance(pal, tuple):
        idx = median(*pal)
        if idx is None:
            idx = 7
        src = {"family": pal[0], "rects": pal[1]}
    else:
        idx, src = pal, "explicit"
    return idx, mat_slot(idx, finish), src


def part(name, pal, finish, fn, *args, **kw):
    idx, slot, src = resolve(pal, finish)
    f0 = len(C.bm.faces)
    fn(slot, *args, **kw)
    PARTS.append({"name": name, "pal": idx, "finish": finish, "src": src, "faces": len(C.bm.faces) - f0})
    return slot


# ------------------------------------------------------------------------------------------------
# primitives (all in sprite px coordinates)
# ------------------------------------------------------------------------------------------------

def _area(pts):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) / 2


def _inset(pts, d):
    n = len(pts)
    ccw = _area(pts) > 0
    out = []
    for i in range(n):
        a, b, c = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e1, e2 = (b - a).normalized(), (c - b).normalized()
        n1 = Vector((-e1.y, e1.x)) if ccw else Vector((e1.y, -e1.x))
        n2 = Vector((-e2.y, e2.x)) if ccw else Vector((e2.y, -e2.x))
        m = n1 + n2
        m = m.normalized() if m.length > 1e-6 else n1
        L = d / max(0.35, m.dot(n1))
        out.append((b.x + m.x * L, b.y + m.y * L))
    return out


def _done(f0, slot, smooth=False):
    C.bm.faces.ensure_lookup_table()
    for f in C.bm.faces[f0:]:
        f.material_index = slot
        f.smooth = smooth


def prism(slot, pts, z0, z1, ch=0.4, top_slot=None, ch_bottom=0.0):
    """Polygon footprint (c, r) extruded z0..z1 with a chamfered top edge (ch px)."""
    bm = C.bm
    f0 = len(bm.faces)
    ch = min(ch, (z1 - z0) * 0.45)
    if _area(pts) > 0:  # make it clockwise in (c, r) = counter-clockwise in Blender XY
        pts = list(reversed(pts))
    top = _inset(pts, ch) if ch > 0 else pts
    rings = []
    if ch_bottom > 0:
        rings.append([bm.verts.new(P(c, r, z0)) for c, r in _inset(pts, ch_bottom)])
        rings.append([bm.verts.new(P(c, r, z0 + ch_bottom)) for c, r in pts])
    else:
        rings.append([bm.verts.new(P(c, r, z0)) for c, r in pts])
    if ch > 0:
        rings.append([bm.verts.new(P(c, r, z1 - ch)) for c, r in pts])
    rings.append([bm.verts.new(P(c, r, z1)) for c, r in top])
    n = len(pts)
    bm.faces.new(list(reversed(rings[0])))
    tf = bm.faces.new(rings[-1])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    _done(f0, slot)
    if top_slot is not None:
        tf.material_index = top_slot
    return tf


def box(slot, c0, r0, c1, r1, z0, z1, ch=0.4, **kw):
    return prism(slot, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, ch, **kw)


def _bez_fillet(path, rad, n=6):
    """Round the corners of a polyline of (c, r, z, radius) with quadratic arcs of ~rad px."""
    if len(path) < 3:
        return path
    out = [path[0]]
    for i in range(1, len(path) - 1):
        A, B, Cc = (Vector(p[:3]) for p in path[i - 1:i + 2])
        u, v = (A - B), (Cc - B)
        t = min(rad, u.length * 0.49 if i > 1 else u.length * 0.98, v.length * 0.49 if i < len(path) - 2 else v.length * 0.98)
        p0, p2 = B + u.normalized() * t, B + v.normalized() * t
        rr = path[i][3]
        for k in range(n + 1):
            s = k / n
            q = p0 * (1 - s) ** 2 + B * 2 * s * (1 - s) + p2 * s * s
            out.append((q.x, q.y, q.z, rr))
    out.append(path[-1])
    return out


def tube(slot, path, sides=16, caps=True, fillet=None, cap_slot=None):
    """A round pipe through (c, r, z, radius) px points, parallel-transport frames, smooth sides."""
    if fillet:
        path = _bez_fillet(path, fillet)
    bm = C.bm
    f0 = len(bm.faces)
    W = [P(*p[:3]) for p in path]
    tang = []
    for i in range(len(W)):
        t = W[min(i + 1, len(W) - 1)] - W[max(i - 1, 0)]
        tang.append(t.normalized())
    ref = Vector((0, 0, 1)) if abs(tang[0].z) < 0.9 else Vector((1, 0, 0))
    nn = tang[0].cross(ref).normalized()
    rings = []
    for i, p in enumerate(W):
        t = tang[i]
        nn = (nn - t * nn.dot(t)).normalized()
        bb = t.cross(nn)
        rr = path[i][3] * PX
        rings.append([bm.verts.new(p + nn * (math.cos(2 * math.pi * k / sides) * rr)
                                   + bb * (math.sin(2 * math.pi * k / sides) * rr)) for k in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            k2 = (k + 1) % sides
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    _done(f0, slot, smooth=True)
    if caps:
        for ring in (rings[0], rings[-1]):
            f = bm.faces.new(ring)
            f.material_index = slot if cap_slot is None else cap_slot
            f.smooth = False


def cylx(slot, r, z, segs, sides=16, **kw):
    """Coaxial sections along the columns at row r: [(c0, c1, radius), ...] -> collars, grooves."""
    for c0, c1, rad in segs:
        tube(slot, [(c0, r, z, rad), (c1, r, z, rad)], sides, **kw)


def cyly(slot, c, z, segs, sides=16, **kw):
    for r0, r1, rad in segs:
        tube(slot, [(c, r0, z, rad), (c, r1, z, rad)], sides, **kw)


def cylz(slot, c, r, z0, z1, rad, sides=18, **kw):
    tube(slot, [(c, r, z0, rad), (c, r, z1, rad)], sides, **kw)


def blob(slot, c, r, z0, rx, ry, rz, seed=0, bump=0.0, seg=14, rings=6, smooth=False):
    """Half-ellipsoid on z0 closed by a flat base (boulders, domes)."""
    bm = C.bm
    f0 = len(bm.faces)
    rnd = random.Random(seed)
    lobes = [(rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.random(), 0.05 + rnd.random() * bump) for _ in range(4)]
    rows = []
    for j in range(rings):
        ph = (math.pi / 2) * j / rings
        row = []
        for k in range(seg):
            th = 2 * math.pi * (k + 0.5 * (j % 2)) / seg
            d = (math.cos(th) * math.cos(ph), math.sin(th) * math.cos(ph), math.sin(ph))
            f = 1.0
            if bump:
                f += sum(a * max(0.0, d[0] * u + d[1] * v + d[2] * w) for u, v, w, a in lobes)
            row.append(bm.verts.new(P(c + d[0] * rx * f, r - d[1] * ry * f, z0 + d[2] * rz * f)))
        rows.append(row)
    f = 1.0 + (sum(a * max(0.0, w) for u, v, w, a in lobes) if bump else 0)
    apex = bm.verts.new(P(c, r, z0 + rz * f))
    for a, b in zip(rows, rows[1:]):
        for k in range(seg):
            k2 = (k + 1) % seg
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    for k in range(seg):
        bm.faces.new((rows[-1][k], rows[-1][(k + 1) % seg], apex))
    bm.faces.new(list(reversed(rows[0])))
    _done(f0, slot, smooth=smooth)


def bolt(slot, c, r, z, rad=0.32, h=0.3, sides=6):
    pts = [(c + rad * math.cos(2 * math.pi * k / sides + 0.3), r + rad * math.sin(2 * math.pi * k / sides + 0.3))
           for k in range(sides)]
    prism(slot, pts, z - 0.1, z + h, ch=0.08)


def bolts(slot, pts, z, **kw):
    for c, r in pts:
        bolt(slot, c, r, z, **kw)
    return []


def slats_x(slot, c0, c1, rows, half, z0, z1, ch=0.15):
    for r in rows:
        box(slot, c0, r - half, c1, r + half, z0, z1, ch)




def bolt_axis(slot, c, r, z, axis, rad=0.28, h=0.32):
    """A hex bolt head standing out of a face along `axis` (c, r, z)."""
    a = Vector(axis).normalized()
    p0 = Vector((c, r, z)) - a * 0.08
    p1 = Vector((c, r, z)) + a * h
    tube(slot, [(p0.x, p0.y, p0.z, rad), (p1.x, p1.y, p1.z, rad)], sides=6)


def plated(slot, core, c0, r0, c1, r1, z0, z1, ch=0.4, cuts_c=(), cuts_r=(), gap=0.24, depth=0.6):
    """Armour plates over a dark core: the cells between the cuts are separate chamfered plates with
    real gaps (modelled panel lines) between them; the core shows in the gaps."""
    box(core, c0 + 0.15, r0 + 0.15, c1 - 0.15, r1 - 0.15, z0, z1 - depth + 0.05, 0.0)
    cs, rs = [c0, *cuts_c, c1], [r0, *cuts_r, r1]
    for i in range(len(cs) - 1):
        for j in range(len(rs) - 1):
            a = cs[i] + (gap / 2 if i else 0)
            b = cs[i + 1] - (gap / 2 if i + 1 < len(cs) - 1 else 0)
            u = rs[j] + (gap / 2 if j else 0)
            v = rs[j + 1] - (gap / 2 if j + 1 < len(rs) - 1 else 0)
            box(slot, a, u, b, v, z1 - depth, z1, ch)


# ------------------------------------------------------------------------------------------------
# the model
# ------------------------------------------------------------------------------------------------

def build():
    C.bm = bmesh.new()

    # ---- ground: the island rock, and the dark floor between the parts (the sprite's dark pixels
    # there), are lib_tiles.sprite_rock's, in main ----
    DARK = mat_slot(2, "dark")  # the dark cores showing in the plates' gaps

    # ---- top pipe (row 3.5): couplings, red flange, polished rod over a brass-studded tray, spring ----
    ZT = 4.6
    chrome = g("grey", [[7, 2, 13, 5]])
    part("topCouplingL", chrome, "chrome", cylx, 3.5, ZT,
         [(7.0, 7.4, 1.6), (7.45, 8.6, 2.1), (8.65, 10.2, 1.7), (10.25, 12.6, 2.1)])
    part("topFlange", g("red", [[13, 2, 14, 6]]), "paint", cylx, 3.5, ZT, [(12.6, 14.3, 2.4)])
    part("topFlangeBolts", chrome, "chrome",  # bolt circle on the flange disc's east face
         lambda s: [bolt_axis(s, 14.3, 3.5 + 1.75 * math.cos(2 * math.pi * (k + 0.5) / 6),
                              ZT + 1.75 * math.sin(2 * math.pi * (k + 0.5) / 6), (1, 0, 0), rad=0.24, h=0.3) for k in range(6)])
    part("topRod", g("grey", [[18, 3, 27, 4]]), "chrome", cylx, 3.3, ZT, [(14.3, 28.0, 0.85)], sides=12)
    part("topSpring", g("grey", [[24, 3, 28, 4]]), "chrome", cylx, 3.3, ZT,
         [(25.2 + 0.45 * i, 25.45 + 0.45 * i, 1.25 if i % 2 else 0.95) for i in range(6)], sides=12)
    part("topCouplingR", g("grey", [[28, 2, 35, 5]]), "chrome", cylx, 3.5, ZT,
         [(28.0, 29.2, 1.6), (29.25, 31.0, 2.05), (31.05, 31.6, 1.6), (31.65, 33.4, 2.05), (33.45, 34.8, 1.2)])
    part("rodTray", g("brown", [[15, 4, 28, 5]]), "brass",
         lambda s: [box(s, c0, 3.9, c1, 5.0, 0, 2.6, 0.3) for c0, c1 in ((15.0, 17.0), (18.9, 21.0), (22.9, 25.0), (26.9, 28.0))])
    part("trayStuds", g("gold", [[18, 4, 27, 5]]), "brass",
         lambda s: [box(s, c - 0.5, 4.0, c + 0.5, 4.95, 2.4, 3.1, 0.2) for c in (18.4, 22.4, 26.4)])
    part("rodSupport", g("grey", [[19, 6, 27, 7]]), "gun", box, 19.0, 5.4, 27.0, 6.8, 0, 1.6, 0.3)
    part("saddleL", g("grey", [[7, 2, 13, 5]]), "gun", box, 8.0, 2.0, 11.6, 5.0, 0, ZT - 1.4, 0.3)
    part("saddleR", g("grey", [[28, 2, 35, 5]]), "gun", box, 29.0, 2.2, 33.0, 4.8, 0, ZT - 1.4, 0.3)

    # ---- red pipes: thin elbow off the left coupling; big elbow (wide leg, reducer, bend, drop) ----
    red_l = g("red", [[3, 8, 10, 15], [5, 7, 17, 10]])
    part("thinRedPipe", g("red", [[5, 2, 7, 7]]), "paint", tube,
         [(7.2, 3.5, ZT, 1.0), (5.9, 3.5, ZT, 1.0), (5.9, 5.0, ZT + 0.6, 1.0), (5.9, 7.6, ZT + 2.4, 1.0)],
         sides=12, fillet=1.2)
    ZB = 6.8
    part("bigElbowLeg", red_l, "paint", cyly, 6.4, ZB, [(11.2, 16.2, 3.25)], sides=24)
    part("bigElbowReducer", red_l, "paint", tube, [(6.4, 11.25, ZB, 3.25), (6.4, 10.4, ZB, 2.05)], sides=24, caps=True)
    part("bigElbow", red_l, "paint", tube,
         [(6.4, 10.6, ZB, 1.85), (6.4, 8.7, ZB, 1.85), (15.0, 8.7, ZB, 1.75), (15.2, 10.8, 1.6, 1.55)],
         sides=18, fillet=2.2)
    part("bigElbowBand", g("red", [[3, 11, 10, 13]]), "paint", cyly, 6.4, ZB, [(12.6, 13.6, 3.5)], sides=24)
    part("bigElbowCollar", g("red", [[11, 7, 14, 10]]), "paint", cylx, 8.7, ZB, [(10.8, 11.9, 2.15)], sides=18)
    part("bandBolts", chrome, "chrome",
         lambda s: [bolt(s, 6.4 + dc, 13.1, ZB + 3.3, rad=0.3, h=0.3) for dc in (-1.5, 1.5)])
    part("lensBoxFlange", g("grey", [[0, 16, 9, 17]]), "metal", box, 0, 15.7, 9.6, 17.0, 0, 7.9, 0.35)
    # The bolted flange where the big elbow's leg enters the lens box, and its bolt circle.
    part("elbowFlange", g("red", [[3, 14, 10, 16]]), "paint", cyly, 6.4, ZB, [(14.6, 15.65, 3.65)], sides=24)
    part("elbowFlangeBolts", chrome, "chrome",
         lambda s: [bolt_axis(s, 6.4 + 3.05 * math.cos(2 * math.pi * (k + 0.5) / 8), 14.6,
                              ZB + 3.05 * math.sin(2 * math.pi * (k + 0.5) / 8), (0, -1, 0), rad=0.26, h=0.32)
                    for k in range(8) if math.sin(2 * math.pi * (k + 0.5) / 8) > -0.5])
    # Stanchions: one under the big elbow's run (by its collar) and one under its leg.
    part("stanchionRun", g("grey", [[11, 7, 14, 10]]), "gun",
         lambda s: [box(s, 11.85, 7.9, 12.85, 9.5, 0, 5.4, 0.15), box(s, 11.3, 7.4, 13.4, 10.0, 0, 0.9, 0.2)])
    part("stanchionLeg", g("grey", [[3, 11, 10, 16]]), "gun",
         lambda s: [box(s, 4.6, 13.8, 8.2, 14.4, 0, 4.0, 0.15), box(s, 4.0, 13.4, 8.8, 14.8, 0, 0.9, 0.2)])

    # ---- two canister lights on a cradle ----
    ZL = 4.8
    part("lightCradle", g("grey", [[19, 11, 22, 21]]), "gun", box, 12.4, 10.8, 20.2, 21.6, 0, 2.6, 0.3)
    part("lightMountN", g("grey", [[10, 11, 13, 15]]), "gun", box, 9.8, 10.8, 13.0, 15.0, 0, 6.4, 0.5)
    part("lightMountS", g("grey", [[10, 18, 13, 22]]), "gun", box, 9.8, 17.8, 13.0, 21.6, 0, 6.0, 0.5)
    for nm, rr, sr in (("lightN", 13.5, [14, 12, 19, 15]), ("lightS", 19.5, [14, 18, 19, 21])):
        part(nm, g("orange", [sr]), "glow", cylx, rr, ZL, [(13.8, 19.0, 1.55)], sides=18)
        cap = g("grey", [[13, rr - 1.5, 14, rr + 1.5], [19, rr - 1.5, 20, rr + 1.5]])
        part(nm + "Core", 124, "glow", cylx, rr, ZL, [(15.8, 17.0, 1.58)], sides=18)
        part(nm + "Caps", cap, "metal", cylx, rr, ZL,
             [(13.0, 13.55, 1.85), (13.6, 13.95, 1.65), (18.85, 19.3, 1.65), (19.35, 19.9, 1.85)], sides=18)
        part(nm + "Guard", cap, "metal", cylx, rr, ZL, [(15.5, 15.75, 1.68), (17.05, 17.3, 1.68)], sides=18)
        part(nm + "Saddles", g("grey", [[19, 11, 22, 21]]), "gun",
             lambda s, rr=rr: [box(s, c - 0.35, rr - 1.2, c + 0.35, rr + 1.2, 2.4, ZL - 0.6, 0.12) for c in (14.4, 18.4)])
    part("lightLink", g("grey", [[16, 15, 19, 18]]), "metal", cyly, 17.4, ZL,
         [(14.8, 15.6, 1.2), (15.65, 17.4, 1.45), (17.45, 18.4, 1.2)])
    part("redTee", g("red", [[11, 15, 16, 18]]), "paint", box, 10.8, 15.0, 16.0, 17.9, 0, 6.2, 0.6)
    part("redTeeBolts", g("red", [[11, 15, 16, 18]]), "paint", lambda s: bolts(s, [(11.5, 15.7), (15.3, 15.7), (11.5, 17.2), (15.3, 17.2)], 6.2, rad=0.28))

    # ---- red tower: chamfered lid on a body with a dark seam; vents on the faces the camera sees ----
    tower_pal = g("red", [[22, 8, 28, 11]])
    part("towerN", tower_pal, "paint", prism,
         [(22.8, 7.8), (27.2, 7.8), (28.0, 8.6), (28.0, 11.0), (22.0, 11.0), (22.0, 8.6)], 0, 10.4, 0.9)
    part("towerCap", tower_pal, "paint", prism,
         [(23.4, 8.3), (26.6, 8.3), (27.2, 8.9), (27.2, 10.5), (22.8, 10.5), (22.8, 8.9)], 10.2, 11.0, 0.35)
    part("towerSeam", g("red", [[22, 11, 28, 12]]), "dark", box, 22.2, 10.9, 27.8, 11.9, 0, 8.6, 0.2)
    part("towerS", g("red", [[22, 12, 28, 16]]), "paint", lambda s: plated(s, DARK, 22.0, 11.9, 28.0, 15.8, 0, 9.4, 0.7, cuts_r=(13.9,)))
    part("towerVent", g("darkbrown", [[22, 15, 28, 16]]), "dark", box, 22.8, 15.6, 27.2, 15.95, 2.4, 7.6, 0.0)
    part("towerVentSlats", g("red", [[22, 12, 28, 16]]), "paint",
         lambda s: [box(s, 22.9, 15.5, 27.1, 16.25, z - 0.3, z + 0.3, 0.12) for z in (3.2, 4.6, 6.0, 7.2)])
    part("towerBolts", g("red", [[22, 8, 28, 11]]), "paint",
         lambda s: bolts(s, [(22.9, 12.7), (27.1, 12.7), (22.9, 15.0), (27.1, 15.0)], 9.4, rad=0.3)
         + bolts(s, [(23.7, 9.0), (26.3, 9.0), (23.7, 10.0), (26.3, 10.0)], 11.0, rad=0.26))
    # Louvred vents on both tower flanks (body and lid): seen from the sides and at 3/4.
    for c, d in ((28.0, 1), (22.0, -1)):
        for r0, r1, z0, z1 in ((12.4, 15.3, 2.0, 8.4), (8.8, 10.6, 5.0, 9.6)):
            part("towerFlankVent", g("darkbrown", [[22, 15, 28, 16]]), "dark", box,
                 min(c, c + d * 0.25), r0, max(c, c + d * 0.25), r1, z0, z1, 0.0)
            part("towerFlankSlats", g("red", [[22, 12, 28, 16]]), "paint",
                 lambda s, c=c, d=d, r0=r0, r1=r1, z0=z0, z1=z1: [
                     box(s, min(c, c + d * 0.45), r0 + 0.15, max(c, c + d * 0.45), r1 - 0.15, zz, zz + 0.4, 0.0)
                     for zz in [z0 + 0.6 + 0.9 * i for i in range(int((z1 - z0 - 0.6) / 0.9))]])
    part("towerPost", g("brown", [[31, 7, 33, 15]]), "brass", cyly, 32.0, 3.4, [(6.4, 15.6, 0.95)], sides=12)
    part("towerPostCollar", g("gold", [[31, 13, 32, 15]]), "brass", cyly, 32.0, 3.4, [(12.9, 14.9, 1.25)], sides=12)
    part("rockCleat", g("brown", [[41, 11, 43, 14]]), "brass", box, 41.2, 11.0, 42.9, 12.9, 0, 3.2, 0.4)

    # ---- lens box (left): bronze frame, brass edge, recessed face, glossy red lens in a bezel ----
    lbp = g("brown", [[1, 17, 10, 20], [1, 20, 2, 27], [7, 20, 10, 26]])
    part("lensBoxCore", lbp, "brass", box, 0.9, 17.0, 10.0, 27.0, 0, 5.4, 0.3)  # under the recessed face
    part("lensBoxFrame", lbp, "brass",  # a frame round the face, so the face is seen from above
         lambda s: [plated(s, DARK, 0.9, 17.0, 10.0, 19.95, 0, 7.6, 0.45, cuts_c=(5.4,)),
                    box(s, 0.9, 19.9, 2.05, 27.0, 0, 7.6, 0.35),
                    box(s, 8.95, 19.9, 10.0, 21.9, 0, 7.6, 0.35)])
    part("lensBoxEdge", g("gold", [[0, 17, 1, 27]]), "brass", box, 0, 17.0, 1.1, 27.0, 0, 7.9, 0.35)
    part("lensFace", g("grey", [[2, 20, 9, 27]]), "dark", box, 2.0, 19.9, 9.0, 26.95, 5.2, 7.35, 0.2)
    part("lensFaceSlot", g("grey", [[9, 22, 10, 26]]), "dark", box, 9.0, 21.8, 9.95, 26.95, 5.2, 7.3, 0.1)
    part("lensBezel", g("grey", [[2, 20, 3, 24], [3, 20, 7, 21]]), "metal", cylz, 4.9, 22.4, 6.0, 8.2, 2.6, 24)
    part("lensBezelRing", g("grey", [[2, 20, 3, 24], [3, 20, 7, 21]]), "chrome", tube,
         [(4.9, 22.4, 8.15, 2.35), (4.9, 22.4, 8.45, 2.35)], sides=24)
    part("lens", g("red", [[3, 21, 7, 24]]), "lens", blob, 4.9, 22.4, 8.0, 2.0, 2.0, 1.5, seg=20, rings=6, smooth=True)
    part("lensBoxBolts", chrome, "chrome",
         lambda s: bolts(s, [(1.6, 17.7), (9.3, 17.7), (1.5, 19.4), (1.5, 26.3)], 7.6, rad=0.3))
    part("lensSill", g("gold", [[0, 27, 10, 28]]), "brass", box, 0, 27.0, 10.0, 28.1, 0, 7.4, 0.35)
    part("bayFrame", g("brown", [[2, 28, 10, 29]]), "brass", box, 1.6, 28.1, 10.0, 29.2, 0, 5.4, 0.35)
    part("bayEdge", g("gold", [[1, 28, 2, 32]]), "brass", box, 0.6, 28.1, 1.7, 32.4, 0, 5.2, 0.3)
    part("bayFloor", g("grey", [[2, 29, 10, 34]]), "dark", box, 1.7, 29.2, 9.4, 34.0, 0, 1.2, 0.1)
    part("bayBlock", g("red", [[3, 30, 7, 34]]), "paint", prism,
         [(3.0, 30.0), (6.0, 30.0), (6.0, 30.8), (7.0, 30.8), (7.0, 34.0), (3.0, 34.0)], 0, 4.4, 0.5)

    # ---- twin red panels with vented skirts ----
    for i, a in enumerate((11.0, 14.6)):
        part(f"panel{i}", g("red", [[11, 22, 14, 26], [15, 22, 18, 26]]), "paint",
             lambda s, a=a: plated(s, DARK, a, 21.8, a + 3.4, 26.0, 0, 7.0, 0.5, cuts_r=(23.6,), depth=0.5))
        part(f"panelBolts{i}", g("red", [[11, 22, 14, 26], [15, 22, 18, 26]]), "paint", lambda s, a=a: bolts(s, [(a + 0.8, 22.5), (a + 2.7, 22.5)], 7.0, rad=0.26))
        part(f"panelSkirt{i}", g("red", [[11, 26, 12, 30], [15, 26, 16, 30]]), "paint", prism,
             [(a, 26.0), (a + 3.4, 26.0), (a + 3.4, 30.2), (a + 3.0, 30.2), (a + 3.0, 26.6), (a + 0.9, 26.6), (a + 0.9, 30.2), (a, 30.2)],
             0, 5.0, 0.3)
        part(f"panelVent{i}", g("darkbrown", [[12, 26, 14, 30], [16, 26, 18, 30]]), "dark", box, a + 0.9, 26.6, a + 3.0, 30.2, 0, 2.6, 0.1)
        part(f"panelSlats{i}", g("darkbrown", [[12, 26, 14, 30], [16, 26, 18, 30]]), "gun", slats_x, a + 0.9, a + 3.0, (27.2, 28.2, 29.2), 0.22, 2.0, 3.9, 0.1)
    part("panelSeam", g("red", [[14, 22, 15, 30]]), "dark", box, 14.4, 21.9, 14.6, 26.0, 0, 6.2, 0.05)

    # ---- central housing: dark gunmetal, stepped plates (panel lines), red trim ribs, hatch, louvres ----
    HT = 6.2
    hp = g("grey", [[19, 18, 34, 21], [19, 28, 28, 33]])
    part("housingN", hp, "gun", lambda s: plated(s, DARK, 18.6, 17.6, 34.0, 21.0, 0, HT, 0.45, cuts_c=(26.4,)))
    part("housingS1", hp, "gun", lambda s: plated(s, DARK, 18.6, 27.0, 34.0, 30.0, 0, HT, 0.45, cuts_c=(24.2,)))
    part("housingS2", hp, "gun", box, 18.6, 30.2, 28.8, 33.2, 0, HT - 0.35, 0.4)  # stepped plate: a panel line
    part("housingS2b", hp, "gun", box, 28.8, 30.2, 34.0, 33.2, 0, HT - 0.35, 0.4)
    part("housingWell", hp, "gun", box, 18.6, 21.0, 34.0, 27.0, 0, HT - 1.7, 0.1)
    part("housingMullion", hp, "gun", box, 22.5, 21.0, 23.1, 27.0, 0, HT, 0.15)
    # The lower annex: a dark core under two plates split along its slant (the sprite's diagonal).
    ap = g("grey", [[19, 34, 28, 42]])
    part("housingAnnexCore", 2, "dark", prism,
         [(18.8, 33.2), (28.8, 33.2), (28.8, 42.6), (24.4, 42.6), (19.6, 37.4), (19.6, 33.2)], 0, 3.7, 0.0)
    part("annexPlateW", ap, "gun", prism,
         [(18.9, 33.3), (23.8, 33.3), (23.8, 38.3), (22.4, 39.9), (19.6, 37.3), (19.6, 33.3)], 3.6, 4.2, 0.3)
    part("annexPlateE", ap, "gun", prism,
         [(24.05, 33.3), (28.7, 33.3), (28.7, 42.5), (24.5, 42.5), (22.6, 40.2), (24.05, 38.5)], 3.6, 4.4, 0.3)
    part("annexBolts", chrome, "chrome", lambda s: bolts(s, [(20.3, 34.0), (23.3, 34.0), (23.3, 37.6)], 4.2, rad=0.26)
         + bolts(s, [(24.6, 34.0), (28.1, 34.0), (28.1, 37.4)], 4.4, rad=0.26))
    trim = g("red", [[19, 16, 35, 18]])
    part("trimTop", trim, "paint", box, 18.6, 15.9, 35.2, 17.7, 0, HT + 1.2, 0.5)
    part("trimRight", g("red", [[34, 17, 35, 34]]), "paint", box, 33.9, 17.6, 35.2, 34.0, 0, HT + 1.2, 0.45)
    part("trimMid", g("red", [[21, 27, 34, 28]]), "paint", box, 20.6, 26.9, 34.0, 28.1, HT - 0.4, HT + 0.9, 0.35)
    part("trimLow", g("red", [[29, 33, 35, 35]]), "paint", box, 28.8, 33.0, 35.2, 34.0, 0, HT + 1.2, 0.45)
    part("trimStem", g("red", [[29, 35, 32, 49]]), "paint",  # the stem of the "P": two plates
         lambda s: [plated(s, DARK, 28.8, 34.8, 31.8, 42.4, 0, HT + 1.0, 0.5, depth=0.5),
                    plated(s, DARK, 28.8, 42.4, 30.9, 49.0, 0, HT + 1.0, 0.5, depth=0.5)])
    part("trimStemRib", g("red", [[29, 35, 32, 49]]), "paint", box, 29.4, 36.0, 30.4, 47.8, HT + 0.8, HT + 1.3, 0.25)
    part("trimBolts", trim, "paint",
         lambda s: bolts(s, [(19.4, 16.8), (23.0, 16.8), (27.0, 16.8), (31.0, 16.8), (34.55, 16.8),
                             (34.55, 22.0), (34.55, 26.0), (34.55, 31.0), (34.55, 33.9)], HT + 1.2, rad=0.28)
         + bolts(s, [(30.3, 35.4), (30.3, 48.3)], HT + 1.0, rad=0.28))
    part("pBox", g("red", [[32, 42, 35, 43], [34, 43, 35, 48]]), "paint", prism,
         [(30.9, 41.8), (35.0, 41.8), (35.0, 49.0), (34.0, 49.0), (34.0, 42.8), (30.9, 42.8)],
         0, HT, 0.4)
    part("pBoxFloor", g("grey", [[32, 43, 34, 48]]), "dark", box, 30.9, 42.8, 34.0, 49.0, 0, 2.0, 0.1)
    part("switchBase", g("brown", [[31, 43, 33, 47]]), "brass", box, 30.95, 43.0, 32.7, 47.8, 0, 4.0, 0.35)
    part("switchLever", g("gold", [[31, 44, 33, 46]]), "brass", box, 31.2, 43.8, 32.4, 45.2, 3.6, 5.4, 0.2)
    hf = g("darkbrown", [[23, 21, 30, 22], [23, 22, 24, 27]])
    for k, b in (("N", (23.0, 21.0, 30.0, 21.9)), ("S", (23.0, 26.6, 30.0, 27.0)), ("W", (23.0, 21.9, 23.8, 26.6)), ("E", (29.7, 21.9, 30.0, 26.6))):
        part("hatchFrame" + k, hf, "dark", box, *b, 0, HT - 0.3, 0.2)
    hb = g("brown", [[24, 23, 30, 27]])
    for k, (c0, c1) in enumerate(((23.8, 25.3), (25.45, 26.9), (27.05, 28.3), (28.45, 29.7))):
        part(f"hatchPlank{k}", hb, "brass", box, c0, 21.9, c1, 26.6, 0, HT - 0.7, 0.2)  # planks with modelled gaps
    part("hatchFloor", g("darkbrown", [[23, 21, 24, 27]]), "dark", box, 23.8, 21.9, 29.7, 26.6, 0, HT - 1.2, 0.0)
    part("hatchHandle", g("gold", [[18, 4, 27, 5]]), "brass", box, 25.9, 23.9, 27.5, 24.5, HT - 0.75, HT - 0.35, 0.12)
    part("louvreLWell", g("grey", [[19, 23, 22, 24], [19, 25, 22, 26]]), "dark", box, 19.0, 21.8, 22.6, 27.0, 0, HT - 1.6, 0.1)
    part("louvreL", g("grey", [[19, 22, 22, 23], [19, 24, 22, 25], [19, 26, 22, 27]]), "metal", slats_x,
         19.2, 22.4, (22.5, 24.5, 26.5), 0.45, HT - 1.8, HT - 0.3, 0.2)
    part("louvreRWell", g("grey", [[30, 23, 34, 24], [30, 25, 34, 26]]), "dark", box, 30.0, 21.8, 33.9, 27.0, 0, HT - 1.6, 0.1)
    part("louvreR", g("grey", [[30, 22, 34, 23], [30, 24, 34, 25], [30, 26, 34, 27]]), "metal", slats_x,
         30.2, 33.7, (22.5, 24.5, 26.5), 0.45, HT - 1.8, HT - 0.3, 0.2)
    part("latch", g("brown", [[28, 19, 30, 21]]), "brass", box, 28.0, 18.9, 30.0, 20.8, HT - 0.2, HT + 0.5, 0.2)
    part("ridge", g("grey", [[20, 19, 25, 20]]), "metal", box, 19.8, 18.9, 25.2, 20.0, HT - 0.2, HT + 0.4, 0.2)
    part("ventBoxA", g("grey", [[29, 29, 31, 32]]), "gun", box, 29.0, 28.9, 30.9, 32.8, HT - 0.3, HT + 0.5, 0.25)
    part("ventBoxB", g("grey", [[32, 29, 34, 32]]), "gun", box, 31.6, 28.9, 33.8, 32.8, HT - 0.3, HT + 0.4, 0.25)
    part("ventSlots", g("darkbrown", [[12, 26, 14, 30]]), "dark",
         lambda s: [box(s, c - 0.15, 29.3, c + 0.15, 32.4, HT + 0.3, HT + 0.55, 0.0) for c in (29.6, 30.3, 32.3, 33.1)])
    part("annexVent", g("grey", [[25, 39, 28, 42]]), "gun", box, 24.8, 38.6, 28.4, 42.0, 3.8, 4.7, 0.3)
    part("annexVentSlats", g("darkbrown", [[12, 26, 14, 30]]), "dark",
         lambda s: [box(s, 25.2, r - 0.14, 28.0, r + 0.14, 4.6, 4.8, 0.0) for r in (39.3, 40.1, 40.9, 41.6)])
    part("sideRailBase", g("darkbrown", [[36, 22, 37, 33]]), "dark", box, 35.6, 22.6, 37.0, 35.4, 0, 2.8, 0.3)
    part("sideRail", g("brown", [[37, 22, 38, 38]]), "brass", box, 36.8, 22.6, 37.95, 35.0, 0, 4.2, 0.4)
    part("railStuds", g("gold", [[37, 23, 38, 24], [37, 32, 38, 35]]), "brass",
         lambda s: [box(s, 36.85, r - 0.5, 37.9, r + 0.5, 4.0, 4.7, 0.2) for r in (23.2, 32.5, 34.2)])
    part("railCleat", g("darkbrown", [[36, 17, 40, 18]]), "dark", box, 35.6, 16.6, 39.4, 17.8, 0, 3.0, 0.3)
    part("cable", g("darkbrown", [[39, 38, 40, 47]]), "dark", tube,
         [(39.4, 37.6, 0.9, 0.55), (39.5, 42.0, 0.9, 0.55), (39.4, 46.8, 0.9, 0.55)], sides=8)
    part("cableBracket", g("brown", [[36, 44, 39, 45]]), "brass", box, 35.6, 43.8, 39.0, 45.0, 0, 2.2, 0.25)

    # ---- lower left: big drum along X with a bronze armour sleeve and a red saddle block ----
    DR, DZ, DRAD = 40.7, 0.6, 7.1
    part("drumRimW", g("grey", [[6, 35, 7, 46]]), "metal", cylx, DR, DZ, [(5.9, 6.9, 6.7)], sides=28)
    part("drumSleeve", g("brown", [[7, 34, 12, 48]]), "brass", cylx, DR, DZ, [(6.9, 11.9, 7.2)], sides=28)
    part("drumChevron", g("gold", [[7, 36, 12, 42]]), "brass", tube,
         [(7.3 + 4.1 * t, 34.4 + 7.2 * t, DZ + math.sqrt(DRAD ** 2 + 0.1 - (34.4 + 7.2 * t - DR) ** 2), 0.95)
          for t in [k / 10 for k in range(11)]], sides=10)  # the sprite's strut: about 2 px wide
    part("drumStrutLow", g("gold", [[7, 43, 8, 46]]), "brass", tube,  # the strut's short lower arm
         [(7.6, 42.9 + 0.3 * k, DZ + math.sqrt(DRAD ** 2 + 0.1 - (42.9 + 0.3 * k - DR) ** 2), 0.7) for k in range(10)],
         sides=10)
    part("drumBody", g("grey", [[12, 34, 19, 39]]), "gun", cylx, DR, DZ, [(11.9, 19.0, DRAD)], sides=28)
    part("drumRings", g("grey", [[13, 34, 14, 39], [17, 34, 18, 39]]), "metal", cylx, DR, DZ,
         [(12.8, 13.5, 7.35), (16.75, 17.45, 7.35)], sides=28)
    part("drumRimE", g("grey", [[19, 33, 20, 39]]), "metal", cylx, DR, DZ, [(19.0, 19.9, 7.4)], sides=28)
    part("saddleUpper", g("red", [[13, 39, 19, 42]]), "paint", prism, [(12.8, 38.8), (19.0, 38.8), (19.0, 39.9), (18.0, 40.9), (17.0, 42.0), (12.8, 42.0)], 0, 8.9, 0.6)
    part("saddleLower", g("red", [[13, 43, 19, 47]]), "paint", prism,
         [(15.9, 42.0), (17.0, 42.0), (17.0, 42.9), (19.1, 42.9), (19.1, 45.6), (17.6, 46.9), (13.6, 46.9), (12.8, 45.8), (12.8, 42.9), (15.9, 42.9)],
         0, 7.4, 0.6)
    part("saddleBolts", g("red", [[13, 39, 19, 42]]), "paint",
         lambda s: bolts(s, [(13.5, 39.5), (18.3, 39.5), (13.5, 41.4), (16.2, 41.4)], 8.9, rad=0.3)
         + bolts(s, [(13.6, 45.6), (17.4, 45.9)], 7.4, rad=0.3))
    part("rod", g("brown", [[23, 45, 29, 46]]), "brass", cylx, 45.5, 4.8, [(21.8, 29.0, 0.6)], sides=10)
    part("rodCap", g("red", [[21, 44, 22, 46]]), "paint", cylx, 45.3, 4.8, [(20.5, 21.9, 1.05)], sides=12)

    bm = C.bm
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in C.mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    C.coll.objects.link(obj)
    return obj


def clip_rect(obj):
    """Cut everything to the 48 x 56 px rectangle (the pieces' boxes) and above BED, filling the
    cut faces, so the block stays closed."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    hw, hh = GW / 2 * PX, GH / 2 * PX
    zb = (BED + ZOFF) * PX
    for co, no in (((-hw, 0, 0), (-1, 0, 0)), ((hw, 0, 0), (1, 0, 0)), ((0, -hh, 0), (0, -1, 0)),
                   ((0, hh, 0), (0, 1, 0)), ((0, 0, zb), (0, 0, -1))):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bm.to_mesh(obj.data)
    bm.free()


def build_block():
    """The whole block, clipped, in assembly coordinates; returns (obj, grid, colors, pieces_layout)."""
    grid, colors, x0, y0, layout = lib.assembly_grid(ROOT, "newsh2-53")
    C.grid, C.colors = grid, colors
    C.sprite = common.load_sprite(ROOT, "newsh2-53")
    C.sprite["colors"] = colors
    C.slots, C.mats = {}, []
    PARTS.clear()
    C.coll = common.reset_collection(NAME)
    obj = build()
    clip_rect(obj)
    cx0, cy0 = x0 + GW // 2, y0 + GH // 2
    pieces_layout = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in layout]
    return obj, grid, colors, pieces_layout


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    obj, grid, colors, pieces_layout = build_block()
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: whole block {tris} triangles")
    # The island rock round the machine (D66), at the rock ground.
    rocks = lt.build_sprite_rock(ROOT, [obj], pieces_layout, GW, GH, C.coll, TAG + "rock", ground=ZOFF * PX, grid=grid)
    pieces = common.split_assembly(obj, pieces_layout, C.coll)
    shells = {}
    for name, cx, cy in pieces_layout:
        p = pieces[name]
        # The outline shell (D51) from a closed copy of the piece.
        src = p.copy()
        src.data = p.data.copy()
        C.coll.objects.link(src)
        shell = common.outline_shell(src, C.coll, faces=800, islands="outer")
        bpy.data.objects.remove(src)
        shell.name = shell.data.name = f"{name}_outline"
        shell.hide_render = True
        shells[name] = shell
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [p, shell, rocks[name]], f"enemies/{name}", data["sprites"])
        pt = sum(len(q.vertices) - 2 for q in p.data.polygons)
        st = sum(len(q.vertices) - 2 for q in shell.data.polygons)
        rt = sum(len(q.vertices) - 2 for q in rocks[name].data.polygons)
        print(f"{NAME}: piece {name} at ({cx}, {cy}) px: {pt} triangles; shell {st} triangles; rock {rt} triangles")

    if "--preview" in argv:
        import tempfile
        out = Path(argv[argv.index("--preview") + 1])
        w, h = len(grid[0]), len(grid)
        Wp = max(w, round(h * 24 / 28))
        Hp = round(Wp * 28 / 24)
        Wp = max(Wp, round(Hp * 24 / 28))
        ref = lib.composite_png(grid, colors, Path(tempfile.mkdtemp()) / "assembly.png", pad_to=(Wp, Hp))
        for name, cx, cy in pieces_layout:
            rocks[name].location = (cx * PX, -cy * PX, 0)
        common.render_preview([obj, *rocks.values()], str(out), str(ref), size=Wp / 12, view_px=640)
        for name, _, _ in pieces_layout:
            rocks[name].location = (0, 0, 0)
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name], rocks[name]], str(out.parent / f"{name}.png"), img, size=2)
    return dict(obj=obj, pieces=pieces, shells=shells, rocks=rocks, grid=grid, layout=pieces_layout)


if __name__ == "__main__":
    main()
