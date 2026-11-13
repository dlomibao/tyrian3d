"""Helpers shared by batch b089's model scripts: the grey multi-barrel gun works of DREAD-NOT (level 4.14;
newsh9.shp frames 235, 236, 238, 239, 254, 258, 274 and 276).

Those eight 2x2 sprites are windows onto two big drawings in the sprite sheet, each 3x4 tiles
(36x56 px): a "left" gun works (tiles from 235) and a "right" one (tiles from 238) that is (nearly)
its mirror image. Each is a weapons cluster bolted to the dreadnought's deck: an armoured gun house with
a NE glacis, a big gun out of its west face (muzzle brake, sight lug), a thin cooled gun out of its
east side on a cradle, an elevation drum, an armoured vault trunk down the screen to a dark junction
block carrying a tapered gun to the lower right, a stepped telescoping gun straight down on a
trunnion drum, and a strut to the hull (D183 design A of assembly-newsh9-276). The left drawing is close to a mirror of the right but not
exact, so build_right(left=True) takes the left sprites' own outline before mirror_left flips it.

The whole gun works is built once (composite pixel edges c, r of the 36x56 drawing; Blender
X = (c - 18) / 12, Y = (28 - r) / 12, Z = z / 12), a sealed pre-cull copy becomes the outline shell
(islands="outer", D189), and each sprite's 24x28 window is cut out of body and shell (open cuts, the
windows overlap by 12 px so the neighbouring piece closes the surface, D181). Each window is exported
as enemies/<name> (body + _outline) by run(); a wrapper script exports only its own windows.

Ground object: the base sits on z = 0 and everything builds upward.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

ROOT = common.repo_root(__file__)
WT = ROOT
TAG = "nsh9gw"
W, H = 36, 56
WINDOWS = {
    "left": {"newsh9-235": (0, 0), "newsh9-236": (12, 0), "newsh9-254": (0, 14), "newsh9-274": (12, 28)},
    "right": {"newsh9-238": (0, 0), "newsh9-239": (12, 0), "newsh9-258": (12, 14), "newsh9-276": (0, 28)},
}
ALL = [n for side in WINDOWS.values() for n in side]

# material slots
BORE, DARK, ROOF, GUN, LIGHT, BRAKE, TRUNK = range(7)


def V(c, r, z):
    return Vector(((c - W / 2) / 12, (H / 2 - r) / 12, z / 12))


# --- geometry helpers (px) ------------------------------------------------------------------------

def _faces(bm, faces, mat, smooth):
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


def ring_frame(t):
    """Side and up vectors of a ring perpendicular to tangent t (px space, z up)."""
    t = t.normalized()
    up = Vector((0, 0, 1))
    side = t.cross(up)
    if side.length < 1e-6:
        side = Vector((1, 0, 0))
    side.normalize()
    upv = side.cross(t).normalized()
    return side, upv


def tube(bm, stations, sides=16, mat=GUN, cap0=None, cap1=None, smooth=True, zscale=1.0, mats=None):
    """A round tube along stations [(c, r, z, radius)] (straight segments). Rings carry a vertex at the
    side extremes so the plan width is exact. cap0/cap1: None (flat fan), ("bore", r_in, depth, mat),
    or False (open). `mats` optional per-segment material list."""
    pts = [Vector((c, r, z)) for c, r, z, _ in stations]
    rings = []
    for i, (c, r, z, rad) in enumerate(stations):
        t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        side, upv = ring_frame(t)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            p = pts[i] + side * (rad * math.cos(a)) + upv * (rad * zscale * math.sin(a))
            ring.append(bm.verts.new(V(p.x, p.y, p.z)))
        rings.append(ring)
    for si, (r0, r1) in enumerate(zip(rings, rings[1:])):
        fs = [bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k])) for k in range(sides)]
        _faces(bm, fs, mats[si] if mats else mat, smooth)
    for end, cap in ((0, cap0), (-1, cap1)):
        if cap is False:
            continue
        ring = rings[end]
        c, r, z, rad = stations[end]
        p = Vector((c, r, z))
        t = (pts[1] - pts[0]) if end == 0 else (pts[-1] - pts[-2])
        t.normalize()
        if end == 0:
            t = -t
        if cap is None or cap == "flat":
            f = bm.faces.new(ring if end == -1 else list(reversed(ring)))
            _faces(bm, [f], mat if not mats else mats[0 if end == 0 else -1], False)
            continue
        _, r_in, depth, bmat = cap
        side, upv = ring_frame(t)
        inner = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            q = p + side * (r_in * math.cos(a)) + upv * (r_in * zscale * math.sin(a))
            inner.append(q)
        # match orientation to the outer ring: rebuild inner from the outer ring's directions
        outer_co = [Vector(((v.co.x * 12) + W / 2, H / 2 - v.co.y * 12, v.co.z * 12)) for v in ring]
        inner = [p + (q - p) * (r_in / max(rad, 1e-6)) for q in outer_co]
        iv = [bm.verts.new(V(q.x, q.y, q.z)) for q in inner]
        dv = [bm.verts.new(V(*(q - t * depth))) for q in inner]
        fs = [bm.faces.new((ring[k], ring[(k + 1) % sides], iv[(k + 1) % sides], iv[k])) for k in range(sides)]
        _faces(bm, fs, mat if not mats else mats[0 if end == 0 else -1], False)
        fs = [bm.faces.new((iv[k], iv[(k + 1) % sides], dv[(k + 1) % sides], dv[k])) for k in range(sides)]
        _faces(bm, fs, bmat, True)
        f = bm.faces.new(dv)
        _faces(bm, [f], bmat, False)


def poly_area(pts):
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                     for i in range(len(pts)))


def offset_poly(pts, ds):
    """Move each edge i (pts[i] -> pts[i+1]) inward by ds[i] (or a single d) and intersect neighbours."""
    n = len(pts)
    if not isinstance(ds, (list, tuple)):
        ds = [ds] * n
    sgn = 1 if poly_area(pts) > 0 else -1  # in (c, r) with r down: positive area = clockwise on screen
    lines = []
    for i in range(n):
        a, b = Vector(pts[i]), Vector(pts[(i + 1) % n])
        d = (b - a).normalized()
        nrm = Vector((-d.y, d.x)) * sgn  # inward
        lines.append((a + nrm * ds[i], d))
    out = []
    for i in range(n):
        p1, d1 = lines[i - 1]
        p2, d2 = lines[i]
        den = d1.x * d2.y - d1.y * d2.x
        if abs(den) < 1e-9:
            out.append(tuple(p2))
            continue
        tt = ((p2.x - p1.x) * d2.y - (p2.y - p1.y) * d2.x) / den
        q = p1 + d1 * tt
        out.append((q.x, q.y))
    return out


def prism(bm, outline, z0, z1, ch=0.5, mat=DARK, top_mat=None, knee=None, top_inset=None, chz=None, top=None):
    """A block on a plan outline (pixel edges): vertical walls from z0 to z1 - chz, then a chamfer (or a
    glacis when top_inset per edge is large) to the flat top at z1, inset by ch (or per-edge top_inset).
    The top face is one n-gon."""
    chz = ch if chz is None else chz
    ins = top_inset if top_inset is not None else ch
    zk = z1 - chz if knee is None else knee
    top = top or offset_poly(outline, ins)
    rings = [[bm.verts.new(V(c, r, z0)) for c, r in outline],
             [bm.verts.new(V(c, r, zk)) for c, r in outline],
             [bm.verts.new(V(c, r, z1)) for c, r in top]]
    n = len(outline)
    walls = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n):
            walls.append(bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k])))
    _faces(bm, walls, mat, False)
    _faces(bm, [bm.faces.new(list(reversed(rings[0])))], mat, False)
    _faces(bm, [bm.faces.new(rings[2])], top_mat if top_mat is not None else mat, False)


def box(bm, c0, c1, r0, r1, z0, z1, ch=0.25, mat=DARK):
    prism(bm, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, ch=ch, mat=mat)


def vault(bm, c0, c1, stations, mat=TRUNK, n=14, p=2.6, cap0=True, cap1=True):
    """A rounded vault (a squashed half-pipe on a short vertical base) running down the screen.
    stations: [(r, inset_left, inset_right, z_top, z_base)] (grooves/hoops/waist)."""
    rings = []
    for r, il, ir, zt, zb in stations:
        cx, hw = (c0 + il + c1 - ir) / 2, (c1 - ir - c0 - il) / 2
        ring = [bm.verts.new(V(cx - hw, r, 0.0))]
        for k in range(n + 1):
            th = math.pi * (1 - k / n)
            cs, sn = math.cos(th), math.sin(th)
            x = cx + hw * math.copysign(abs(cs) ** (2 / p), cs)
            z = zb + (zt - zb) * abs(sn) ** (2 / p)
            ring.append(bm.verts.new(V(x, r, z)))
        ring.append(bm.verts.new(V(cx + hw, r, 0.0)))
        rings.append(ring)
    m = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        fs = [bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k])) for k in range(m - 1)]
        fs.append(bm.faces.new((r0[m - 1], r0[0], r1[0], r1[m - 1])))
        _faces(bm, fs[:-1], mat, True)
        _faces(bm, fs[-1:], mat, False)
    if cap0:
        _faces(bm, [bm.faces.new(rings[0])], mat, False)
    if cap1:
        _faces(bm, [bm.faces.new(list(reversed(rings[-1])))], mat, False)


def drum(bm, c0, c1, r, z, rad, sides=20, mat=LIGHT, hub=0.6, hub_mat=GUN):
    """A cylinder along X with chamfered ends and a raised hub on each end face."""
    e = min(0.35, (c1 - c0) / 6)
    tube(bm, [(c0, r, z, rad * 0.86), (c0 + e, r, z, rad), (c1 - e, r, z, rad), (c1, r, z, rad * 0.86)],
         sides=sides, mat=mat)
    for cc, dc in ((c0, -hub), (c1, hub)):
        tube(bm, [(cc - 0.05 * (1 if dc > 0 else -1), r, z, rad * 0.5), (cc + dc, r, z, rad * 0.45)],
             sides=12, mat=hub_mat)


def bolt(bm, c, r, z, rad=0.32, h=0.3, mat=GUN):
    tube(bm, [(c, r, z - 0.2, rad), (c, r, z + h, rad), (c, r, z + h + 0.12, rad * 0.6)], sides=6, mat=mat,
         smooth=False)


# --- the gun works (right side) -------------------------------------------------------------------

def build_right(bm, left=False):
    """The right gun works in the right drawing's pixel frame. left=True builds the same machine with
    the left drawing's own outline (still in this frame; mirror_left flips it): the left sprites are
    not an exact mirror of the right ones. Their glacis sits 1 px further in along the whole slope,
    and the trunk is 1 px narrower on its gun-side edge (left drawing col 9) from the hoop to the
    junction, with a 1 px waist at rows 23-24 (fitted to newsh9-235/236/254/274's inner masks)."""
    g = 1.0 if left else 0.0  # glacis shift toward the house (px)
    # ---- gun house (armoured, NE glacis) ----
    wst = 5.0 if left else 4.0  # the left drawing's mantlet step is one row lower
    house = [(11.2, 1.0), (13.9 - g * 1.25, 1.0), (15.7 - g * 1.2, 2.5), (19.55 - g, 6.5), (20.3 - g * 0.7, 7.6 if left else 7.5),
             (23.4 - g, 10.6), (23.4 - g, 10.8), (10.5, 10.8), (10.5, wst), (11.2, wst)]
    # per-edge top inset: north face, NE glacis, south face, west face (mantlet side)
    roof = [(11.8, 2.4), (12.0, 2.4), (13.3 - g * 0.8, 3.6), (16.9 - g, 7.3), (17.6 - g, 8.1), (19.9 - g, 10.15),
            (20.0 - g, 10.2), (11.2, 10.2), (11.2, wst + 0.6), (11.8, wst + 0.6)]
    prism(bm, house, 0.0, 9.0, mat=DARK, top_mat=ROOF, knee=2.4, top=roof)
    # raised roof armour plate, and bolts
    plate = ([(12.5, 5.0), (12.6, 5.0), (17.3, 9.6), (12.5, 9.6)] if left else
             [(12.5, 4.2), (12.7, 4.2), (18.4, 9.6), (12.5, 9.6)])
    prism(bm, plate, 8.6, 9.35, ch=0.25, mat=ROOF)
    for c, r in ((12.2, 3.4), (12.2, 9.75), (16.0, 9.75), (19.0 - g * 1.1, 9.75)):
        bolt(bm, c, r, 9.3, rad=0.28, h=0.18, mat=GUN)
    # thin gun breech block on the house's SE corner
    prism(bm, [(16.6, 10.2), (20.3, 10.2), (20.3, 15.6), (16.6, 15.6)], 0.0, 7.0, ch=0.6, mat=DARK, top_mat=ROOF)
    bolt(bm, 17.6, 14.4, 6.95, rad=0.28, h=0.2)
    bolt(bm, 19.3, 14.4, 6.95, rad=0.28, h=0.2)

    # ---- big gun (west) ----
    zb = 4.4
    # mantlet collar where it leaves the house
    tube(bm, [(12.6, 9.05, zb, 4.3), (11.6, 9.05, zb, 4.5), (10.9, 9.05, zb, 4.3)], sides=24, mat=DARK,
         cap0=None, cap1=None)
    st = [(11.0, 9.0, zb, 4.0), (8.6, 9.0, zb, 3.95), (8.5, 9.0, zb, 4.08), (7.7, 9.0, zb, 4.08),
          (7.6, 9.0, zb, 3.9), (5.0, 9.0, zb, 3.85)]
    tube(bm, st, sides=24, mat=GUN, cap0=None, cap1=None)
    # muzzle brake: two baffles with a vent gap, bore at the front
    # (the left drawing's brake is one row shorter on its south side and has no sight lug)
    zb2 = zb + 0.05
    rb, kb = (9.0, 0.93) if left else (9.15, 1.0)  # brake axis row, radius scale
    tube(bm, [(5.1, rb, zb2, 4.2 * kb), (4.8, rb, zb2, 4.55 * kb), (3.7, rb, zb2, 4.55 * kb),
              (3.55, rb, zb2, 4.3 * kb)], sides=24, mat=BRAKE)
    tube(bm, [(3.6, rb, zb2, 3.5 * kb), (3.2, rb, zb2, 3.5 * kb)], sides=24, mat=BRAKE)
    # the front baffle keeps its full size (the left drawing's brake reaches row 13 at its muzzle only)
    tube(bm, [(3.3, 9.15, zb2, 4.3), (3.15, 9.15, zb2, 4.55), (2.15, 9.15, zb2, 4.55), (2.0, 9.15, zb2, 4.3)],
         sides=24, mat=BRAKE, cap1=("bore", 2.2, 3.0, BORE))
    if not left:
        # sight lug on the brake's north flank (the sprite's 1 px nub, row 4 col 3)
        box(bm, 3.0, 4.0, 3.95, 5.4, 3.3, 5.6, ch=0.2, mat=BRAKE)

    # ---- elevation drum under the house ----
    drum(bm, 10.6 if left else 10.0, 16.9, 12.65, 4.4, 2.75, mat=LIGHT, hub=0.4)

    # ---- thin gun (east) on its cradle ----
    zt = 4.6
    cradle = ([(19.8, 13.4), (29.0, 13.4), (29.0, 14.6), (25.0, 15.0), (23.2, 16.0), (23.0, 17.0), (19.8, 17.0)]
              if left else
              [(19.8, 13.4), (29.0, 13.4), (29.0, 14.6), (25.0, 15.0), (24.0, 17.0), (19.8, 17.0)])
    prism(bm, cradle, 0.0, 3.6, ch=0.35, mat=DARK)
    st = [(19.6, 12.5, zt, 1.5)]
    for x in (21.0, 22.2, 23.4, 24.6):  # cooling rings
        st += [(x, 12.5, zt, 1.5), (x + 0.12, 12.5, zt, 1.68), (x + 0.48, 12.5, zt, 1.68), (x + 0.6, 12.5, zt, 1.5)]
    st += [(29.4, 12.5, zt, 1.45), (29.5, 12.5, zt, 1.6), (30.95, 12.5, zt, 1.6)]
    tube(bm, st, sides=16, mat=LIGHT, cap1=("bore", 0.8, 1.2, BORE))

    # ---- trunk (rounded armoured vault down the screen) ----
    hoops = (17.05, 20.2) if left else (16.2, 20.2)
    stations = [(12.6, 1.0, 0.0, 6.6, 1.0), (hoops[0] - 0.4, 1.0, 0.0, 6.6, 1.0), (hoops[0] - 0.1, 0.0, 0.0, 6.6, 1.0)]
    for r0 in hoops:  # reinforcing hoops
        stations += [(r0, 0.0, 0.0, 6.6, 1.0), (r0 + 0.05, -0.12, -0.12, 6.9, 1.0),
                     (r0 + 0.95, -0.12, -0.12, 6.9, 1.0), (r0 + 1.0, 0.0, 0.0, 6.6, 1.0)]
    if left:
        stations += [(21.9, 0.0, 0.0, 6.5, 1.0), (22.6, 0.1, 0.0, 6.3, 1.0), (22.9, 0.2, 1.0, 6.2, 1.0),
                     (24.7, 0.2, 1.0, 6.2, 1.0), (25.0, 0.2, 0.0, 6.0, 1.0), (26.8, 0.2, 0.0, 6.0, 1.0)]
    else:
        stations += [(21.9, 0.0, 0.0, 6.5, 1.0), (22.2, 0.15, 0.6, 6.2, 1.0), (22.5, 0.2, 0.8, 6.2, 1.0),
                     (24.7, 0.2, 0.8, 6.2, 1.0), (25.0, 0.2, 0.0, 6.0, 1.0), (26.8, 0.2, 0.0, 6.0, 1.0)]
    vault(bm, 9.0, 22.0 if left else 23.0, stations, mat=TRUNK)
    # panel seams across the vault top (modelled grooves between the hoops)
    # (the hoops above carry the joints; a row of bolts along each hoop)
    for r0 in hoops:
        for c in ((11.6, 15.5, 19.4) if left else (12.0, 16.0, 20.0)):
            bolt(bm, c, r0 + 0.5, 6.7, rad=0.25, h=0.28, mat=GUN)

    # ---- junction block ----
    south = [(17.0, 22.9), (17.0, 29.6), (16.2, 30.4), (15.0, 31.5), (13.0, 32.5), (10.0, 34.0)]
    if left:  # west face at col 9 with a boss at rows 25-26, an ink gap to the strut at rows 27-28
        J = [(7.0, 29.1), (9.0, 28.9), (9.0, 27.1), (8.1, 26.8), (8.1, 25.2), (9.0, 24.9), (9.0, 22.9)] + south + \
            [(7.3, 34.0)]
        plate = offset_poly([(9.0, 34.0), (9.0, 22.9)] + south, 1.6)
    else:
        J = [(7.0, 26.2), (8.0, 25.0), (8.0, 24.1), (9.1, 22.9)] + south + [(7.3, 34.0)]
        plate = offset_poly(J, 1.6)
    prism(bm, J, 0.0, 6.0, ch=0.8, mat=DARK)
    prism(bm, plate, 5.6, 6.35, ch=0.25, mat=DARK)
    for c, r in ((10.3 if left else 9.6, 25.4), (14.6, 25.4), (14.4, 29.0)):
        bolt(bm, c, r, 6.3, rad=0.3, h=0.2)

    # ---- strut west to the hull (cut flat at col 1) ----
    S = ([(1.0, 30.0), (3.7, 30.0), (6.3, 27.0), (7.0, 27.0), (7.0, 29.0), (7.7, 29.2), (7.7, 34.0), (6.0, 35.0),
          (3.9, 35.0), (3.9, 34.0), (1.0, 34.0)] if left else
         [(1.0, 30.0), (3.7, 30.0), (7.2, 26.2), (7.7, 26.2), (7.7, 34.0), (6.0, 35.0), (3.9, 35.0), (3.9, 34.0),
          (1.0, 34.0)])
    prism(bm, S, 0.0, 3.8, ch=0.4, mat=DARK)
    bolt(bm, 2.3, 31.4, 3.75, rad=0.3, h=0.2)

    # ---- down gun: trunnion drum + stepped telescoping barrel ----
    drum(bm, 3.7, 10.5, 31.8, 3.6, 2.3, mat=GUN, hub_mat=DARK)
    zd = 3.4
    a0, a1 = Vector((7.8, 33.0)), Vector((9.4, 44.0))

    def ax(y):
        return a0.x + (a1.x - a0.x) * (y - a0.y) / (a1.y - a0.y)
    st = [(ax(32.4), 32.4, zd, 2.25), (ax(34.6), 34.6, zd, 2.25)]
    for y0, y1, rad in ((34.7, 35.9, 3.0), (35.9, 38.9, 2.5), (38.9, 41.9, 2.0), (41.9, 44.0, 1.5)):
        st += [(ax(y0), y0, zd, rad - 0.15), (ax(y0 + 0.2), y0 + 0.2, zd, rad), (ax(y1 - 0.5), y1 - 0.5, zd, rad),
               (ax(y1 - 0.45), y1 - 0.45, zd, rad - 0.12)]
    st[-1] = (ax(44.0), 44.0, zd, 1.5)
    st[-2] = (ax(43.9), 43.9, zd, 1.5)
    tube(bm, st, sides=16, mat=GUN, cap0=None, cap1=("bore", 0.7, 1.0, BORE))

    # ---- SE gun: breech ring + tapered barrel ----
    zs = 3.4
    d = Vector((0.85, 0.527))
    o = Vector((16.8, 25.7))

    def at(s):
        q = o + d * s
        return q.x, q.y
    # (s along the axis, radius)
    prof = [(0.0, 2.6), (1.6, 2.65), (1.7, 2.9), (3.2, 2.9), (3.3, 2.5), (4.6, 2.45), (11.3, 2.05),
            (11.4, 2.2), (13.6, 2.2)]
    tube(bm, [(*at(s), zs, rad) for s, rad in prof], sides=16, mat=GUN, cap0=None, cap1=("bore", 1.0, 1.0, BORE),
         mats=[GUN, BRAKE, BRAKE, GUN, GUN, GUN, GUN, BRAKE])


def mirror_left(bm):
    """The left gun works: column c' = 31 - c (edges e' = 32 - e), i.e. Blender x -> -x - 4/12."""
    for v in bm.verts:
        v.co.x = -v.co.x - 4 / 12
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])


def merged_sprite():
    data = common.load_sprite(WT, "newsh9-238")
    for side in WINDOWS.values():
        for n in side:
            data["colors"].update(common.load_sprite(WT, n)["colors"])
    return data


STEEL_SPEC = 0.5 * ((1.0 / 3.0) ** 2 / 0.04)  # F0 of IOR 2.0 via Specular IOR Level (D176)


def materials(sprite):
    def pal(i, metallic, roughness, spec=True):
        m = common.palette_material(sprite, i, TAG, metallic=metallic, roughness=roughness)
        if spec:
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = STEEL_SPEC
        return m
    return [
        pal(2, 0.2, 0.8, spec=False),  # BORE
        pal(3, 0.35, 0.55),  # DARK: house walls, cradle, junction, strut
        pal(4, 0.35, 0.5),  # ROOF
        pal(5, 0.45, 0.42),  # GUN: barrels, breech
        pal(6, 0.45, 0.4),  # LIGHT: thin gun, drum
        pal(4, 0.45, 0.45),  # BRAKE: muzzle brakes, breech rings (same index as ROOF; separate slot)
        pal(4, 0.4, 0.48),  # TRUNK
    ]


def build(side, name):
    sprite = merged_sprite()
    coll = common.reset_collection(name)
    bm = bmesh.new()
    build_right(bm, left=(side == "left"))
    if side == "left":
        mirror_left(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mats = materials(sprite)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj, coll, sprite


def split_open(obj, layout):
    """common.split_assembly without the cap fill (copied from assembly-newshh-45): each piece keeps the
    part of `obj` inside its 24x28 px box, open along the cut. The b089 windows overlap by 12 px, so the
    neighbouring piece always closes the surface; a filled cap (and above all a filled cap on the outline
    shell) drew a dark wall across the gun works where the renderer lifts the later piece (D181)."""
    result = {}
    coll = obj.users_collection[0]
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for mt in obj.data.materials:
            mesh.materials.append(mt)
        piece = bpy.data.objects.new(name, mesh)
        coll.objects.link(piece)
        result[name] = piece
    return result


def layout(side, names):
    out = []
    for n in names:
        x0, y0 = WINDOWS[side][n]
        out.append((n, x0 + 12 - W / 2, y0 + 14 - H / 2))
    return out


def finish_normals(obj):
    me = obj.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(40))
    # keep flagged flat faces flat
    return obj


def run(side, names, script_name):
    """Build the whole gun works, cut out `names`' windows and export each as enemies/<name>
    (body + outline shell). With `-- --preview out.png` render a top view of the whole thing."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    obj, coll, sprite = build(side, f"{script_name}-whole")
    bpy.context.view_layer.update()
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    shell = common.outline_shell(sealed, coll, voxel=0.012, faces=4000, smooth=4, inside=0.004, islands="outer")
    bpy.data.objects.remove(sealed, do_unlink=True)
    shell.name = f"{script_name}_outline"
    T.cull_hidden(obj, grid=4, ndirs=40)
    finish_normals(obj)
    lay = layout(side, names)
    bodies = split_open(obj, lay)
    shells = split_open(shell, lay)
    for n in names:
        b, sh = bodies[n], shells[n]
        b.name = n
        sh.name = f"{n}_outline"
        sh["tyrian_outline"] = True
        finish_normals(b)
        sh.data.shade_smooth()
        if len(sh.data.polygons) == 0:
            print(f"WARNING: {n} outline has no mesh")
        data = common.load_sprite(ROOT, n)
        common.export_sprite_model(ROOT, [b, sh], f"enemies/{n}", data["sprites"])
        print(f"{n}: {sum(len(p.vertices) - 2 for p in b.data.polygons)} tris, shell {len(sh.data.polygons)} faces")
