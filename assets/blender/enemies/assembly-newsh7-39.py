"""assembly-newsh7-39, design A: a grey armoured ground fortress with a glass tube bank, a big blue
lens and a canister in a well (newsh7.shp 1 | 3 over 39 | 41; CAMANIS 3.1 and ICESECRET 4.20).

What it is (read from the 48x56 sprite, light from the upper left):
- A square deck (cols 1-42, rows 1-36) with a raised curb on its back and sides, glass skylights in
  the two back corners, a raised bar across the back, armour panels with small blue ports down both
  sides and a sloped front lip (the dark rows 35-36 left of the casemate).
- Between two raised pillars (cols 10-13 and 30-33) a well holds a blue tank lying north-south,
  sunk to its axis, with a wider collar in the middle (cols 19-26, rows 7-18).
- In front of the well the casemate: two buttresses with a lit ridge (cols 11 and 32) and outer
  bevels, chamfered shoulders (rows 20-24), running out past the deck onto the ice to a rounded
  glacis (rows 41-50). On its deck a bank of four glowing glass tubes under a steel shroud (cols
  17-27, rows 19-30) between two blue lamps; below a ledge (row 33) a lower front bay holds two
  lamp boxes (glass tops, raked glowing faces, rows 36-41) on either side of a rib, and the glacis
  centre is a dark socket with the big blue lens (rows 42-48). Blue pipes run down both sides in
  wall channels (cols 5-6, 37-38) and two small vents glow at the foot (cols 12-13, 30-31).
The icy-blue edge (ramp 48-62 round the right and bottom) is ground, not model (D130): nothing is
built for it; IoU is measured with the ice made transparent (refmask.py). The black rows 49-50 and the
dark patch right of the casemate are drop shading: lighting, not modelled.

Exports public/models/enemies/newsh7-{1,3,39,41}.glb (each piece with its own outline shell) and
src/render/spriteModels/newsh7-*.json, as the earlier script did. Self-contained.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)

NAME = "assembly-newsh7-39"
PIECES = ["newsh7-1", "newsh7-3", "newsh7-39", "newsh7-41"]
# Piece centres relative to the block centre (screen 260, -4): 1/3 at cy -18, 39/41 at cy 10, cx 248/272.
LAYOUT = [("newsh7-1", -12, -14), ("newsh7-3", 12, -14), ("newsh7-39", -12, 14), ("newsh7-41", 12, 14)]
PX = 1 / 12

DECK = 0.16       # deck top
CURB = 0.035      # curb above the deck
ZW, ZR, ZI = 0.27, 0.445, 0.42   # casemate: outer wall top, ridge, inner deck
CORE = 0.41       # core deck between the buttresses (under the tube bank)
BAY = 0.24        # lower front bay floor (under the lamp boxes)


def X(u):
    """Pixel-edge column u of the 48x56 block (0 = left edge) to Blender X."""
    return (u - 24) * PX


def Y(v):
    """Pixel-edge row v (0 = top edge) to Blender Y (sprite up = +Y)."""
    return (28 - v) * PX


def P(u, v, z):
    return (X(u), Y(v), z)


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


# Glacis: the casemate's top falls away over rows 40-51 (a rounded, convex fall).
GLACIS = pchip([40.0, 42.0, 44.5, 47.0, 49.5, 51.0], [1.0, 0.95, 0.80, 0.56, 0.30, 0.16])


# ---- small bmesh helpers ------------------------------------------------------------------------

def hull(bm, pts, mat, smooth=False):
    """Convex hull of `pts` added to `bm` (coplanar triangles merged), material `mat`."""
    tmp = bmesh.new()
    for p in pts:
        tmp.verts.new(p)
    res = bmesh.ops.convex_hull(tmp, input=tmp.verts[:])
    junk = res["geom_interior"] + res["geom_unused"]
    if junk:
        bmesh.ops.delete(tmp, geom=list({g for g in junk if isinstance(g, bmesh.types.BMVert)}), context="VERTS")
    bmesh.ops.dissolve_limit(tmp, angle_limit=math.radians(0.5), verts=tmp.verts[:], edges=tmp.edges[:])
    for f in tmp.faces:
        f.material_index = mat
        f.smooth = smooth
    me = bpy.data.meshes.new("tmp")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def cbox(bm, u0, u1, v0, v1, z0, z1, mat, ch=0.4, chz=None):
    """A box over pixel edges u0..u1, v0..v1, z0..z1 with chamfered vertical corners and top edges
    (`ch` px across, `chz` units down)."""
    chz = ch * PX if chz is None else chz
    c = ch * PX
    x0, x1, y0, y1 = X(u0), X(u1), Y(v1), Y(v0)
    pts = []
    for z, inset in ((z0, 0.0), (z1 - chz, 0.0), (z1, c)):
        a0, a1, b0, b1 = x0 + inset, x1 - inset, y0 + inset, y1 - inset
        pts += [(a0 + c, b0, z), (a1 - c, b0, z), (a1, b0 + c, z), (a1, b1 - c, z),
                (a1 - c, b1, z), (a0 + c, b1, z), (a0, b1 - c, z), (a0, b0 + c, z)]
    hull(bm, pts, mat)


def loft(bm, rings, mat, cap0=True, cap1=True, smooth=True, mats=None):
    """Faces between consecutive rings (equal-length loops of 3D points); `mats` per ring segment."""
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(vs, vs[1:]):
        for i in range(n):
            f = bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
            f.material_index = mats[i] if mats else mat
            f.smooth = smooth
    for ring, on in ((vs[0], cap0), (vs[-1], cap1)):
        if on:
            f = bm.faces.new(ring)
            f.material_index = mat
            f.smooth = False


def extrude_u(bm, u0, u1, prof, mat, mats=None):
    """A prism across columns u0..u1 with a closed (v, z) profile; `mats` per profile segment."""
    loft(bm, [[P(u0, v, z) for v, z in prof], [P(u1, v, z) for v, z in prof]], mat, smooth=False, mats=mats)


def tube_path(bm, pts, r, mat, sides=12, caps=True):
    """A round tube along a polyline of 3D points lying in a plane of constant X (pipes running
    down the sprite)."""
    pts = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(pts):
        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        t = (b - a).normalized()
        n1 = Vector((1, 0, 0))
        n2 = t.cross(n1).normalized()
        rings.append([p + r * (math.cos(2 * math.pi * k / sides) * n1 + math.sin(2 * math.pi * k / sides) * n2)
                      for k in range(sides)])
    loft(bm, rings, mat, cap0=caps, cap1=caps)


def arc(c, r, a0, a1, n, x):
    """Points (x, y, z) on a circle in the plane X = x round (y, z) centre c, angles a0..a1."""
    return [(x, c[0] + r * math.cos(a0 + (a1 - a0) * k / n), c[1] + r * math.sin(a0 + (a1 - a0) * k / n))
            for k in range(n + 1)]


def ellipsoid(bm, centre, ex, ey, ez, rx, ry, rz, mat, segs=24, rings=10, zmin=-1.0):
    """An ellipsoid (radii along the unit axes ex, ey, ez), cut flat below local z = zmin*rz."""
    c = Vector(centre)
    pts = []
    for i in range(rings + 1):
        th = math.pi / 2 * i / rings
        for j in range(segs):
            ph = 2 * math.pi * j / segs
            for s in (1, -1):
                lz = s * rz * math.cos(th)
                if lz < zmin * rz:
                    lz = zmin * rz
                pts.append(c + ex * (rx * math.sin(th) * math.cos(ph)) + ey * (ry * math.sin(th) * math.sin(ph))
                           + ez * lz)
    hull(bm, pts, mat, smooth=True)


# ---- parts ----------------------------------------------------------------------------------------

def build_deck(bm, M, detail=True):
    """The deck, with the well cut out between the pillars, a curb, a sloped front lip."""
    # Deck pieces (abutting, so no two tops overlap): north strip, west and east blocks, under the casemate.
    cbox(bm, 1, 43, 1, 6, 0.0, DECK, M["deck"], ch=0.01)
    cbox(bm, 1, 14, 6, 35.5, 0.0, DECK, M["deck"], ch=0.01)
    cbox(bm, 30, 43, 6, 35.5, 0.0, DECK, M["deck"], ch=0.01)
    cbox(bm, 14, 30, 19.5, 37, 0.0, DECK, M["deck"], ch=0.01)
    # Front lip (rows 35-36 dark): slopes from the deck down to the ice.
    for u0, u1 in ((1, 14), (30, 43)):
        extrude_u(bm, u0, u1, [(35.5, 0.0), (37.0, 0.0), (37.0, 0.05), (35.5, DECK)], M["deck"])
    # Well floor.
    cbox(bm, 14, 30, 6, 19.5, 0.0, DECK - 0.06, M["dark"], ch=0.01)
    if not detail:
        return
    # Curb round the back and sides: chamfered on its inner top edge.
    cprof = lambda: None  # noqa: E731
    del cprof
    hull(bm, [P(u, v, z) for u in (1, 43) for v, z in ((1, 0.1), (1, DECK + CURB), (1.55, DECK + CURB),
                                                        (2.0, DECK + 0.01), (2.0, 0.1))], M["curb"])
    for u0, u1, ui in ((1, 2, 2.0), (42, 43, 42.0)):
        outer = u0 if u0 == 1 else u1
        pts = []
        for v in (2.0, 35.3):
            for u, z in ((outer, 0.1), (outer, DECK + CURB), (outer + (0.55 if outer == 1 else -0.55), DECK + CURB),
                         (ui, DECK + 0.01), (ui, 0.1)):
                pts.append(P(u, v, z))
        hull(bm, pts, M["curb"])
    # Back bar (rows 3-5, between the skylights).
    cbox(bm, 9, 35, 3, 6, DECK - 0.01, DECK + 0.045, M["bar"], ch=0.6)
    # Skylights in the back corners: frame, then a low hipped glass top.
    for u in (3, 36):
        cbox(bm, u, u + 5, 3, 8, DECK - 0.01, DECK + 0.03, M["frame"], ch=0.35)
        cbox(bm, u + 0.8, u + 4.2, 3.8, 7.2, DECK + 0.02, DECK + 0.062, M["skylight"], ch=0.9, chz=0.022)
    # Armour panels with small blue ports down both sides.
    for v0, v1, port in ((9, 14, True), (15, 20, True), (21, 27, False)):
        cbox(bm, 3, 8, v0, v1, DECK - 0.01, DECK + 0.05, M["panel"], ch=0.5)
        cbox(bm, 36, 41, v0, v1, DECK - 0.01, DECK + 0.05, M["panel"], ch=0.5)
        if port:
            cbox(bm, 5.9, 8.1, v0 - 0.1, v0 + 2.1, DECK + 0.02, DECK + 0.07, M["port"], ch=0.35)
            cbox(bm, 35.9, 38.1, v0 - 0.1, v0 + 2.1, DECK + 0.02, DECK + 0.07, M["port"], ch=0.35)
    # Low armour boxes beside the casemate's flanks (rows 27-34).
    cbox(bm, 1.8, 5.2, 27, 35, DECK - 0.01, DECK + 0.06, M["panel"], ch=0.5)
    cbox(bm, 38.8, 42.2, 27, 35, DECK - 0.01, DECK + 0.06, M["panel"], ch=0.5)
    # Bolt heads at the deck corners.
    for u, v in ((2.7, 2.7), (41.3, 2.7), (2.7, 34.3), (41.3, 34.3)):
        ellipsoid(bm, P(u, v, DECK), Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)),
                  0.4 * PX, 0.4 * PX, 0.025, M["curb"], segs=10, rings=3, zmin=0.0)


def build_well(bm, M, detail=True):
    """Pillars either side of the well and the blue tank lying in it."""
    for u0 in (10, 30):
        cbox(bm, u0, u0 + 4, 7, 19.6, DECK - 0.01, 0.30, M["pillar"], ch=0.5)
        if detail:
            # A cap plate on each pillar with a seam either side.
            cbox(bm, u0 + 0.6, u0 + 3.4, 7.6, 18.6, 0.29, 0.315, M["pillar"], ch=0.4)
    if not detail:
        return
    # The tank: a cylinder (axis north-south at column edge 23) sunk to just under the well floor.
    zc = 0.035
    ZFLOOR = DECK - 0.075  # the tank's lower half is cut off inside the well floor
    stations = [(6.6, 0.0), (6.75, 1.6), (7.0, 2.4), (7.5, 2.85), (11.4, 2.85), (11.6, 3.2), (11.9, 3.95),
                (16.4, 3.95), (16.7, 3.2), (16.9, 2.55), (19.6, 2.55)]
    sides = 28
    rings = []
    for v, r in stations:
        rr = max(r, 0.02) * PX
        rings.append([P(23 + rr / PX * math.cos(2 * math.pi * k / sides), v,
                        max(ZFLOOR, zc + rr * math.sin(2 * math.pi * k / sides))) for k in range(sides)])
    loft(bm, rings, M["tank"])
    # Collar bands at both ends of the drum, a little proud.
    for v0, v1 in ((11.9, 12.5), (15.8, 16.4)):
        rings = []
        for v in (v0, v1):
            rr = 4.12 * PX
            rings.append([P(23 + rr / PX * math.cos(2 * math.pi * k / sides), v,
                            max(ZFLOOR, zc + rr * math.sin(2 * math.pi * k / sides))) for k in range(sides)])
        loft(bm, rings, M["tank"])
    # Saddles under it.
    for v in (9.0, 17.6):
        cbox(bm, 18.2, 27.8, v, v + 1.0, DECK - 0.07, DECK - 0.01, M["bar"], ch=0.3)


def butt_ring(v, sgn, groove=0.0):
    """One cross-section of a buttress at row edge v; sgn 1 = left, -1 = right (mirrored about col 22).
    `groove` > 0 sinks the top by that much (a panel seam across the buttress)."""
    if v <= 24.0:
        uo = 9.5 - (v - 19.5) / 4.5 * 3.5
    else:
        uo = 6.0
    g = GLACIS(v)
    prof = [(uo, 0.0), (uo, ZW * g), (uo + 0.5, (ZW + 0.04) * g), (11.0, ZR * g - 0.01), (11.5, ZR * g),
            (12.0, ZR * g - 0.012), (12.5, ZI * g), (13.4, ZI * g), (14.0, ZI * g - 0.04), (14.0, 0.0)]
    if groove:
        prof = [(u, z - groove if 0 < k < len(prof) - 1 else z) for k, (u, z) in enumerate(prof)]
    if sgn < 0:
        prof = list(reversed(prof))
    return [P(u if sgn > 0 else 44 - u, v, z) for u, z in prof]


def build_casemate(bm, M, detail=True):
    vs = [19.5, 20.5, 21.5, 22.5, 23.5, 24.0, 28.0, 32.0, 36.0, 40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0,
          47.0, 48.0, 49.0, 50.0, 51.0]
    seams = (27.0, 37.5) if detail else ()
    rows = [(v, 0.0) for v in vs]
    for s_ in seams:
        rows += [(s_ - 0.3, 0.0), (s_, 0.016), (s_ + 0.3, 0.0)]
    rows.sort()
    for sgn in (1, -1):
        loft(bm, [butt_ring(v, sgn, g) for v, g in rows], M["case"])
    # Core between the buttresses: deck, ledge, drop into the front bay, bay floor, socket glacis.
    prof = [(19.5, 0.0), (19.5, CORE), (32.6, CORE), (33.3, CORE - 0.012), (34.0, 0.37), (35.6, BAY),
            (41.0, BAY), (41.8, 0.232), (44.0, 0.215), (47.0, 0.13), (49.2, 0.06), (50.0, 0.03), (50.0, 0.0)]
    mats = [M["case"], M["core"], M["core"], M["core"], M["dark"], M["bayfloor"], M["socket"], M["socket"],
            M["socket"], M["socket"], M["socket"], M["socket"], M["case"]]
    extrude_u(bm, 14, 30, prof, M["case"], mats=mats)
    if not detail:
        return
    # Tube bank: dark blue backing, four glowing glass tubes, a steel shroud over their middle.
    cbox(bm, 16.5, 28.5, 19.5, 31.2, CORE - 0.01, CORE + 0.045, M["backing"], ch=0.4)
    zt, rt = CORE + 0.07, 1.08 * PX
    for u in (18.0, 21.0, 24.0, 27.0):
        pts = [P(u, v, zt) for v in (19.6, 30.9)]
        tube_path(bm, pts, rt, M["tube"], sides=14)
        for v in (19.6, 30.9):
            ellipsoid(bm, P(u, v, zt), Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)),
                      rt, rt * 0.7, rt, M["tube"], segs=14, rings=4)
        tube_path(bm, [P(u, v, zt) for v in (24.0, 29.0)], rt + 0.012, M["shroud"], sides=14)
        # Saddle under the shroud, so it sits on the backing.
        cbox(bm, u - 1.2, u + 1.2, 24.2, 28.8, CORE + 0.03, zt, M["shroud"], ch=0.2)
    # Clamp bands at the shroud's ends.
    for v in (23.6, 28.9):
        cbox(bm, 16.8, 28.2, v, v + 0.5, CORE + 0.03, zt + rt + 0.016, M["shroud"], ch=0.2)
    # Blue lamps either side of the tubes, in bezels.
    for u0, u1, mat in ((14.0, 16.0, M["lampL"]), (29.0, 31.0, M["lampR"])):
        cbox(bm, u0 - 0.3, u1 + 0.3, 23.7, 26.3, CORE - 0.02, CORE + 0.03, M["bezel"], ch=0.3)
        ellipsoid(bm, P((u0 + u1) / 2, 25.0, CORE + 0.03), Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)),
                  (u1 - u0) / 2 * PX, 1.0 * PX, 0.035, mat, segs=14, rings=5, zmin=0.0)
    # Front bay: two lamp boxes (glass tops, raked glowing faces) and a rib between them.
    for u0, u1 in ((15.0, 20.0), (24.0, 29.0)):
        extrude_u(bm, u0, u1, [(35.9, BAY - 0.02), (35.9, 0.37), (37.8, 0.37), (38.2, 0.36), (41.3, 0.265),
                               (41.6, BAY - 0.04)],
                  M["frame"], mats=[M["frame"], M["glasstop"], M["frame"], M["lampbox"], M["lampbase"], M["frame"]])
    extrude_u(bm, 20.0, 24.0, [(35.7, BAY - 0.02), (35.7, 0.36), (36.3, 0.375), (40.2, 0.375), (41.4, 0.30),
                               (41.4, BAY - 0.02)],
              M["rib"], mats=[M["rib"]] * 6)
    # The lens: a deep blue bezel and a domed lens set into the socket glacis.
    th = math.atan2(0.215 - 0.13, 3.0 * PX)
    ey = Vector((0, math.cos(th), math.sin(th)))
    en = Vector((0, -math.sin(th), math.cos(th)))
    ex = Vector((1, 0, 0))
    c = Vector(P(22.6, 45.6, 0.165))
    ellipsoid(bm, c - en * 0.01, ex, ey, en, 6.5 * PX, 3.75 * PX, 0.035, M["rim"], segs=32, rings=4, zmin=-0.6)
    ellipsoid(bm, c + en * 0.005, ex, ey, en, 5.6 * PX, 3.0 * PX, 0.085, M["lens"], segs=40, rings=10, zmin=-0.5)
    # Pipes in channels down the casemate's flanks: a grey mount, then the pipe following the glacis
    # and turning down into the ice.
    for sgn in (1, -1):
        u = 6.0 if sgn > 0 else 38.0
        ua, ub = (4.95, 6.6) if sgn > 0 else (37.4, 39.05)
        cbox(bm, ua, ub, 37.1, 40.3, 0.0, 0.25, M["case"], ch=0.3)
        path = [P(u, v, z) for v, z in ((40.0, 0.215), (42.0, 0.205), (44.0, 0.185), (46.0, 0.155), (47.6, 0.125))]
        # elbow down to the ground at row ~49.6
        cy, cz, r = Y(47.6), 0.125 - 0.12, 0.12
        for k in range(1, 7):
            a = math.pi / 2 - (math.pi / 2) * k / 6
            path.append((X(u), cy - r * math.cos(a), cz + r * math.sin(a)))
        path.append((X(u), cy - r, -0.01))
        tube_path(bm, path, 0.95 * PX, M["pipeL"] if sgn > 0 else M["pipeR"], sides=12)
        # flange collars
        for v in (40.4, 44.3):
            z = 0.215 if v < 41 else 0.183
            tube_path(bm, [P(u, v - 0.3, z), P(u, v + 0.3, z)], 1.15 * PX, M["bezel"], sides=12)
    # Vents at the glacis foot.
    for u0, u1, mat in ((12.0, 14.0, M["ventL"]), (30.0, 32.0, M["ventR"])):
        g0, g1 = GLACIS(47.0), GLACIS(49.6)
        extrude_u(bm, u0, u1, [(46.9, 0.0), (46.9, ZI * g0 + 0.008), (49.6, ZI * g1 + 0.008), (49.6, 0.0)], mat)


def materials(sprite):
    tag = "n7_39a"

    def pal(i, metallic, roughness, spec=None, **kw):
        m = common.palette_material(sprite, i, tag, metallic=metallic, roughness=roughness, **kw)
        if spec is not None:
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    glow = dict(metallic=1.0, roughness=0.55)
    spec = [
        ("deck", 4, 0.5, 0.5, None, 0),
        ("curb", 7, 0.5, 0.45, None, 0),
        ("bar", 5, 0.5, 0.5, None, 0),
        ("panel", 6, 0.5, 0.45, None, 0),
        ("pillar", 6, 0.5, 0.45, None, 0),
        ("dark", 3, 0.4, 0.6, None, 0),
        ("case", 7, 0.55, 0.42, 0.6, 0),
        ("core", 6, 0.55, 0.42, 0.6, 0),
        ("bayfloor", 4, 0.5, 0.5, None, 0),
        ("socket", 2, 0.45, 0.55, None, 0),
        ("rib", 7, 0.55, 0.42, None, 0),
        ("frame", 130, 0.55, 0.40, None, 0),
        ("skylight", 129, 0.6, 0.2, 0.8, 0),
        ("port", 130, 0.6, 0.2, 0.8, 0),
        ("tank", 56, 0.6, 0.32, 0.7, 0),
        ("backing", 54, 0.5, 0.45, None, 0),
        ("tube", 158, *glow.values(), None, 0.6),
        ("shroud", 130, 0.6, 0.35, 0.7, 0),
        ("bezel", 3, 0.5, 0.45, None, 0),
        ("lampL", 155, *glow.values(), None, 1.0),
        ("lampR", 153, *glow.values(), None, 1.0),
        ("glasstop", 57, 0.6, 0.2, 0.8, 0),
        ("lampbox", 154, *glow.values(), None, 0.9),
        ("lampbase", 151, *glow.values(), None, 0.6),
        ("rim", 147, 0.6, 0.35, None, 0),
        ("lens", 152, 1.0, 0.35, None, 0.55),
        ("pipeL", 129, 0.6, 0.3, 0.7, 0),
        ("pipeR", 130, 0.6, 0.3, 0.7, 0),
        ("ventL", 54, *glow.values(), None, 0.5),
        ("ventR", 56, *glow.values(), None, 0.5),
    ]
    mats, M, seen = [], {}, {}
    for key, idx, met, rough, sp, em in spec:
        sig = (idx, met, rough, sp, em)
        if sig not in seen:
            seen[sig] = len(mats)
            mats.append(pal(idx, met, rough, spec=sp, emission_strength=em))
        M[key] = seen[sig]
    return mats, M


def build(coll, detail=True, name=NAME):
    sprite = common.load_sprite(ROOT, PIECES[0])
    for n in PIECES[1:]:
        sprite["colors"].update(common.load_sprite(ROOT, n)["colors"])
    mats, M = materials(sprite)
    bm = bmesh.new()
    build_deck(bm, M, detail)
    build_well(bm, M, detail)
    build_casemate(bm, M, detail)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    for p in me.polygons:
        p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(34))
    return obj


def sink_shell(shell, model, margin, reach):
    """Keep the outline shell under the model's top surface (D90/D118: ink on the silhouette only).

    The voxel shell is smoothed, so it bridges the model's creases (the hood's trim strips, the gem bezel, the
    engine-bay channel, the hood/nose step) and stood above the surface there: its back faces drew as dark
    scribbles across the hood and the plate. Every shell vertex is dropped to `margin` under the topmost
    model surface within `reach` of it (seen from straight above). x and y are untouched, so the silhouette (and the ink round it) is
    the same."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    moved = 0
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):  # the lowest top within `reach`: a shell edge spans ~0.6 px, so a vertex
            a = 2 * math.pi * k / 12  # beside a raised strip must not ride at the strip's height
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
            moved += 1
    shell.data.update()
    print(shell.name, "sunk", moved, "of", len(shell.data.vertices))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj = build(coll)
    pieces = common.split_assembly(obj, LAYOUT)
    # The outline shell's source (D90/D118): a sealed copy without the small detail (tank, tubes, lamps,
    # curb, panels), so the smoothed shell can't bridge the grooves and draw ink across the top.
    plain = build(coll, detail=False, name=NAME + "_plain")
    sealed = common.split_assembly(plain, LAYOUT)
    bpy.data.objects.remove(plain, do_unlink=True)
    bpy.context.view_layer.update()
    shells = {}
    for name, cx, cy in LAYOUT:
        p = pieces[name]
        for poly in p.data.polygons:
            poly.use_smooth = True
        p.data.set_sharp_from_angle(angle=math.radians(34))
        src = sealed[name]
        bpy.context.view_layer.update()
        sh = common.outline_shell(src, coll, voxel=0.018, faces=6000, inside=0.012)
        sh.name = sh.data.name = f"{name}_outline"
        sink_shell(sh, src, margin=0.03, reach=0.09)
        print("SHELL", name, len(sh.data.vertices), "verts")
        bpy.data.objects.remove(src, do_unlink=True)
        shells[name] = sh
    for name, _, _ in LAYOUT:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"])


if __name__ == "__main__":
    main()
