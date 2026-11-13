"""Shared builder for EYESPY's (4.13) grey robot arms: assembly-newsh9-39 (left arm, newsh9 1/3/39) and
assembly-newsh9-45 (right arm, newsh9 5/7/45, its pixel mirror). Design A of the D65 rebuild.

WHAT IT IS: two grey manipulator arms hung either side of the EYESPY boss (e4:351-356 spawn them at t4500
on the top layer, rigid). Read from the 48 x 56 px left drawing:
- a SHOULDER HOUSING across the top (a rounded drum lying along the screen, pal 7) with two machined
  KNUCKLE DOMES on its crown (pal 10; their hot spots are sheen);
- a lower NECK DECK (pal 6) where the upper arm leaves the housing;
- the UPPER ARM: a raised armoured COWL (pal 9) with a broad glacis on its outer side over a rounded
  box BEAM (pal 5) slanting down to the lower left, ending in a dark WRIST GEARBOX (pal 3);
- a BALL JOINT (pal 9) at the elbow;
- a C-shaped YOKE beside the arm: a bright rolled LIP (pal 10) over a recessed dark SOCKET (pal 4, a hub
  at its centre) into the JAW block (pal 9); under the jaw a hydraulic ACTUATOR pod (pal 4) with two
  piston RODS (pal 7) meeting at a clevis;
- the FOREARM drum (pal 7, two machined bands) hanging under the elbow;
- the CLAW: an open hoop of round tubing (pal 6) over a tapered FINGER (pal 4), its right side one
  bright run of pipe (pal 9) down into a glowing blue GEM (pal 153) held in the finger's tip.
Air unit: everything z >= 0, the underside a plain closed shape.

Units while building: left-drawing pixel EDGES (c = column edge, r = row edge, down the screen) and z
in px; Blender X = (c - 24) / 12, Y = (28 - r) / 12, Z = z / 12. The right arm is the left mirrored.

Used by assembly-newsh9-39.py (exports the left pieces) and assembly-newsh9-45.py (the right pieces):
run(script_file, side) builds only that side. Review outputs (--views / --pieces DIR) only on a flag.
"""


import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

WT = common.repo_root(__file__)
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "assembly-newsh9-39"
TAG = "nsh9arm"
W, H = 48, 56
WINDOWS = {
    "left": {"newsh9-1": (0, 0), "newsh9-3": (24, 0), "newsh9-39": (0, 28)},
    "right": {"newsh9-5": (0, 0), "newsh9-7": (24, 0), "newsh9-45": (24, 28)},
}

# material slots
(HOUSE, KNUCK, NECK, COWL, BEAM, WRIST, BALL, LIP, SOCK, HUB, JAW, ACT, ROD, FORE, HOOP, FING, PIPE,
 GEM) = range(18)


def V(c, r, z):
    return Vector(((c - W / 2) / 12, (H / 2 - r) / 12, z / 12))


def _faces(bm, faces, mat, smooth):
    for f in faces:
        f.material_index = mat
        f.smooth = smooth


# --- geometry helpers (px) ------------------------------------------------------------------------

def ring_frame(t):
    t = t.normalized()
    up = Vector((0, 0, 1))
    side = t.cross(up)
    if side.length < 1e-6:
        side = Vector((1, 0, 0))
    side.normalize()
    return side, side.cross(t).normalized()


def tube(bm, stations, sides=16, mat=ROD, cap0=True, cap1=True, smooth=True, zscale=1.0, matf=None,
         closed=False):
    """A round tube along stations [(c, r, z, radius)] (px). `closed` joins the last ring to the first
    (a loop). matf(c, r) -> material per segment (optional)."""
    pts = [Vector((c, r, z)) for c, r, z, _ in stations]
    n = len(pts)
    rings = []
    for i, (c, r, z, rad) in enumerate(stations):
        if closed:
            t = pts[(i + 1) % n] - pts[i - 1]
        else:
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        side, upv = ring_frame(t)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            p = pts[i] + side * (rad * math.cos(a)) + upv * (rad * zscale * math.sin(a))
            ring.append(bm.verts.new(V(p.x, p.y, p.z)))
        rings.append(ring)
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for si, (r0, r1) in enumerate(pairs):
        fs = [bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k])) for k in range(sides)]
        m = mat
        if matf:
            a, b = stations[si], stations[(si + 1) % n]
            m = matf((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        _faces(bm, fs, m, smooth)
    if not closed:
        for end, cap in ((0, cap0), (-1, cap1)):
            if not cap:
                continue
            ring = rings[end]
            ctr = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring))
            fs = []
            for k in range(sides):
                a, b = ring[k], ring[(k + 1) % sides]
                fs.append(bm.faces.new((b, a, ctr) if end == 0 else (a, b, ctr)))
            _faces(bm, fs, mat if not matf else matf(*stations[end][:2]), smooth)


def poly_area(pts):
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                     for i in range(len(pts)))


def offset_poly(pts, ds):
    """Move each edge i (pts[i] -> pts[i+1]) inward by ds[i] (or one d) and intersect neighbours."""
    n = len(pts)
    if not isinstance(ds, (list, tuple)):
        ds = [ds] * n
    sgn = 1 if poly_area(pts) > 0 else -1
    lines = []
    for i in range(n):
        a, b = Vector(pts[i]), Vector(pts[(i + 1) % n])
        d = (b - a).normalized()
        lines.append((a + Vector((-d.y, d.x)) * sgn * ds[i], d))
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


def chaikin(pts, it=2, keep=()):
    """Corner-cutting (closed polygon): rounds the plan where the sprite is round."""
    for _ in range(it):
        out = []
        n = len(pts)
        for i in range(n):
            a, b = Vector(pts[i]), Vector(pts[(i + 1) % n])
            out.append(tuple(a * 0.75 + b * 0.25))
            out.append(tuple(a * 0.25 + b * 0.75))
        pts = out
    return pts


def block(bm, outline, z0, z1, mat, top_mat=None, insets=0.8, chz=0.8, round_it=1, steps=2):
    """A hard-surface block on a plan outline (pixel edges): vertical walls from z0, then a rounded
    chamfer (`steps` facets, a quarter round) of plan inset `insets` (per edge allowed) and height
    `chz` to the flat top at z1. The outline is corner-rounded by Chaikin first."""
    n0 = len(outline)
    if isinstance(insets, (list, tuple)):
        ins = list(insets)
    else:
        ins = [insets] * n0
    pts = outline
    for _ in range(round_it):  # carry per-edge insets through the corner cutting
        newp, newi = [], []
        n = len(pts)
        for i in range(n):
            a, b = Vector(pts[i]), Vector(pts[(i + 1) % n])
            newp += [tuple(a * 0.75 + b * 0.25), tuple(a * 0.25 + b * 0.75)]
            newi += [ins[i], (ins[i] + ins[(i + 1) % n]) / 2]
        pts, ins = newp, newi
    n = len(pts)
    layers = [[bm.verts.new(V(c, r, z0)) for c, r in pts]]
    for k in range(steps + 1):
        a = 0.5 * math.pi * k / steps
        f = 1 - math.cos(a)
        ring = offset_poly(pts, [d * f for d in ins]) if f > 1e-6 else pts
        z = z1 - chz + chz * math.sin(a)
        layers.append([bm.verts.new(V(c, r, z)) for c, r in ring])
    walls = []
    for lo, hi in zip(layers, layers[1:]):
        for k in range(n):
            walls.append(bm.faces.new((lo[k], lo[(k + 1) % n], hi[(k + 1) % n], hi[k])))
    _faces(bm, walls, mat, True)
    _faces(bm, [bm.faces.new(list(reversed(layers[0])))], mat, False)
    top = bm.faces.new(layers[-1])
    _faces(bm, [top], top_mat if top_mat is not None else mat, False)
    return top


def superellipse(theta, p):
    cs, sn = math.cos(theta), math.sin(theta)
    return math.copysign(abs(cs) ** (2 / p), cs), math.copysign(abs(sn) ** (2 / p), sn)


def loft(bm, stations, mat, sides=24, p=2.6, dense=0.5, matf=None, cap0=True, cap1=True, grooves=(), normal=None):
    """A faired loft along a plan polyline: stations [(c, r, hw, zb, zt)], the section a superellipse
    of exponent p, half-width hw across the axis and z from zb to zt. Stations are interpolated with
    pchip along the arc length (D52) every `dense` px. `grooves` [(s_px, depth_px, width_px)] cut
    modelled panel lines round the crown (upper half only, so the plan is untouched).
    matf(c, r, z, nz) -> material for a face (optional)."""
    s = [0.0]
    for a, b in zip(stations, stations[1:]):
        s.append(s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    fs = [T.pchip(s, [st[k] for st in stations]) for k in range(5)]
    L = s[-1]
    m = max(2, int(math.ceil(L / dense)))
    ss = sorted(set([L * i / m for i in range(m + 1)] + s
                    + [g[0] + d for g in grooves for d in (-g[2] / 2, -g[2] / 6, g[2] / 6, g[2] / 2)]))
    ss = [x for x in ss if 0 <= x <= L]
    rings = []
    for x in ss:
        c, r, hw, zb, zt = (f(x) for f in fs)
        e = 0.05
        c1, r1 = fs[0](min(L, x + e)), fs[1](min(L, x + e))
        c0, r0 = fs[0](max(0, x - e)), fs[1](max(0, x - e))
        tx, ty = c1 - c0, r1 - r0
        ln = math.hypot(tx, ty) or 1
        nx, ny = (-ty / ln, tx / ln) if normal is None else normal
        gd = 0.0
        for g in grooves:
            if abs(x - g[0]) < g[2] / 3:
                gd = max(gd, g[1])
        zm, hz = (zb + zt) / 2, (zt - zb) / 2
        ring = []
        for k in range(sides):
            th = 2 * math.pi * k / sides
            u, w = superellipse(th, p)
            sc = 1.0
            if gd and w > 0.2:
                sc = 1 - gd / max(hz, 0.5) * min(1, (w - 0.2) / 0.5)
            ring.append(bm.verts.new(V(c + nx * hw * u * sc, r + ny * hw * u * sc, zm + hz * w * sc)))
        rings.append(ring)
    faces = []
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            faces.append(bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k])))
    _faces(bm, faces, mat, True)
    for end, cap in ((0, cap0), (-1, cap1)):
        if not cap:
            continue
        ring = rings[end]
        f = bm.faces.new(list(reversed(ring)) if end == 0 else ring)
        _faces(bm, [f], mat, False)
        faces.append(f)
    if matf:
        for f in faces:
            f.normal_update()
            q = f.calc_center_median()
            f.material_index = matf(q.x * 12 + W / 2, H / 2 - q.y * 12, q.z * 12, f.normal.z)
    return faces


def ellipsoid(bm, c, r, z, a, b, h, mat, rot=0.0, segs=20, rings=10, lower=1.0, flat=1.0):
    """An ellipsoid at (c, r, z): semi-axes a (along c, turned by rot degrees), b, h; `lower` scales the
    lower half's height, `flat` < 1 broadens the crown."""
    res = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    for v in res["verts"]:
        x, y, t = v.co
        t = (abs(t) ** flat if t > 0 else t * lower)
        u, w = x * a, -y * b
        v.co = V(c + u * ca - w * sa, r + u * sa + w * ca, z + t * h)
    fs = list({f for v in res["verts"] for f in v.link_faces})
    _faces(bm, fs, mat, True)
    return fs


def cyl(bm, c, r, z0, z1, rc, rr, mat, sides=24, top_mat=None, ch=0.3):
    """A vertical elliptic cylinder with a chamfered top edge."""
    rings = []
    for z, s in ((z0, 1.0), (z1 - ch, 1.0), (z1, 1 - ch / max(min(rc, rr), 0.5))):
        rings.append([bm.verts.new(V(c + rc * s * math.cos(2 * math.pi * k / sides),
                                     r + rr * s * math.sin(2 * math.pi * k / sides), z)) for k in range(sides)])
    fs = []
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            fs.append(bm.faces.new((a[k], b[k], b[(k + 1) % sides], a[(k + 1) % sides])))
    _faces(bm, fs, mat, True)
    _faces(bm, [bm.faces.new(rings[0])], mat, False)
    _faces(bm, [bm.faces.new(list(reversed(rings[-1])))], top_mat if top_mat is not None else mat, False)


def bolt(bm, c, r, z, rad=0.38, h=0.32, mat=HUB):
    tube(bm, [(c, r, z - 0.3, rad), (c, r, z + h, rad), (c, r, z + h + 0.12, rad * 0.6)], sides=6, mat=mat,
         smooth=False)


# --- the left arm ---------------------------------------------------------------------------------

def build_left(bm):
    # SHOULDER HOUSING: a rounded drum lying along the screen (rows 3-12, cols 24-46), crown about 8.7
    # px, two seam grooves round it.
    hs = [(24.3, 8.2, 12.4, 5.0), (25.2, 7.1, 12.5, 6.2), (26.3, 6.1, 12.6, 6.8), (27.2, 5.25, 12.6, 7.2),
          (29.0, 5.1, 12.7, 7.6), (30.6, 4.95, 12.8, 7.9), (31.4, 4.2, 12.8, 8.1), (32.6, 3.8, 12.8, 8.3),
          (33.5, 3.1, 12.8, 8.5), (36.0, 2.95, 12.8, 8.7), (38.6, 3.05, 12.7, 8.7), (39.4, 3.75, 12.6, 8.6),
          (40.6, 3.95, 12.45, 8.5), (41.4, 4.0, 12.1, 8.3), (42.1, 4.05, 11.05, 8.1), (43.6, 4.15, 10.95, 7.6),
          (44.4, 4.85, 10.9, 7.2), (45.1, 5.6, 10.75, 6.6), (45.7, 6.3, 10.4, 5.6), (46.1, 7.2, 9.7, 4.2)]
    loft(bm, [(c, (rt + rb) / 2, (rb - rt) / 2, 0.6, zt) for c, rt, rb, zt in hs], HOUSE, sides=28, p=2.4,
         grooves=[(5.5, 0.3, 0.6), (19.2, 0.3, 0.6)], normal=(0.0, 1.0))
    # end hub on the outer end of the drum (machined boss)
    tube(bm, [(45.75, 8.25, 3.0, 1.35), (46.15, 8.25, 3.0, 1.15)], sides=14, mat=HUB)
    # knuckle domes on the crown
    ellipsoid(bm, 37.4, 5.7, 7.7, 2.05, 2.2, 1.55, KNUCK, segs=18, rings=9, lower=0.6)
    ellipsoid(bm, 41.5, 6.9, 7.5, 1.85, 2.0, 1.45, KNUCK, segs=18, rings=9, lower=0.6)
    for cc, rr in ((37.4, 5.7), (41.5, 6.9)):
        tube(bm, [(cc, rr, 7.1, 2.25 if cc < 40 else 2.05), (cc, rr, 7.9, 2.25 if cc < 40 else 2.05)],
             sides=18, mat=HUB, cap0=False, cap1=True)

    # NECK DECK where the upper arm leaves the housing (rows 8-12, cols 19-28), a lower deck.
    block(bm, [(19.15, 10.1), (20.1, 9.05), (24.0, 9.0), (24.3, 8.4), (26.0, 7.9), (27.6, 9.8), (27.8, 12.4),
               (17.15, 12.7), (17.9, 11.15)], 0.8, 6.6,
          NECK, insets=[0.9, 0.9, 0.9, 0.6, 0.6, 0.6, 0.6, 0.9, 0.9], chz=0.9, round_it=0)

    # COWL: the raised armour over the upper arm (rows 11-20, cols 16-28), a broad glacis down its
    # outer side.
    before = set(bm.faces)
    block(bm, [(17.3, 11.6), (27.7, 11.2), (27.8, 14.0), (26.8, 18.2), (25.0, 20.0), (19.6, 19.4),
               (16.05, 16.4), (16.1, 13.0)], 1.0, 9.0, COWL,
          insets=[0.8, 0.6, 0.6, 0.6, 0.8, 3.0, 3.8, 2.6], chz=2.2, steps=1)
    for f in set(bm.faces) - before:  # the outer glacis is a darker side panel (pal 5, the sprite's band)
        f.normal_update()
        q = f.calc_center_median()
        if abs(f.normal.z) < 0.99 and q.x * 12 + W / 2 < 20.6 and q.z * 12 > 2.0:
            f.material_index = BEAM
    bolt(bm, 25.4, 13.0, 9.0, mat=COWL)
    bolt(bm, 24.8, 17.6, 9.0, mat=COWL)

    # BEAM: a rounded box slanting down to the lower left under the cowl.
    u = Vector((-0.68, 0.733))
    a0 = Vector((21.4, 17.6))
    st = []
    for s_, hw, zt in ((0.0, 4.6, 7.0), (3.0, 4.85, 6.8), (7.0, 4.95, 6.4), (10.5, 4.75, 6.0), (13.0, 4.5, 5.4)):
        q = a0 + u * s_
        st.append((q.x, q.y, hw, 0.5, zt))
    loft(bm, st, BEAM, sides=24, p=3.2, grooves=[(8.6, 0.25, 0.5)])

    # WRIST GEARBOX at the beam's lower end (rows 24-31, cols 8-18).
    block(bm, [(9.1, 24.3), (12.6, 23.4), (17.6, 26.4), (17.8, 30.4), (12.8, 31.0), (8.6, 31.3), (7.6, 31.3),
               (8.1, 30.2), (9.1, 29.9)], 0.3, 4.6,
          WRIST, insets=0.9, chz=1.0)

    # BALL JOINT at the elbow (rows 19-29.5, cols 17-25).
    ellipsoid(bm, 21.05, 24.45, 4.3, 3.95, 5.0, 4.3, BALL, segs=24, rings=12, lower=0.85)

    # SOCKET: a recessed dark cup inside the yoke (rows 13-23, cols 26-35), a hub at its centre.
    block(bm, [(24.6, 15.0), (26.8, 12.9), (31.0, 12.8), (34.2, 14.3), (35.7, 18.6), (35.7, 24.2), (29.6, 24.2),
               (28.9, 23.0), (26.0, 23.0), (25.95, 24.0), (24.45, 24.0), (24.4, 19.0)], 0.4, 3.0, SOCK, insets=0.5,
          chz=0.5, round_it=0)
    cyl(bm, 30.6, 18.6, 2.6, 3.5, 1.7, 1.8, HUB, sides=16)
    # LIP: the bright rolled edge of the yoke, arching over the socket into the jaw.
    lip = [(26.9, 12.6, 7.3, 1.0), (28.6, 12.75, 7.6, 1.1), (30.6, 13.05, 7.6, 1.15), (32.4, 13.9, 7.5, 1.15),
           (33.7, 15.5, 7.3, 1.1), (34.9, 17.2, 7.1, 1.05), (36.4, 18.4, 6.9, 0.95), (37.6, 19.0, 6.6, 0.8)]
    tube(bm, [(c, r, z, rad * 1.15) for c, r, z, rad in lip], sides=14, mat=LIP, zscale=1.1)
    # the yoke's curved web under the lip, down to the socket floor (hidden from above by the lip)
    loft(bm, [(c, r, rad * 0.75, 1.0, z) for c, r, z, rad in lip], SOCK, sides=16, p=4.0)

    # JAW block under the housing (rows 13-22, cols 34-44).
    block(bm, [(34.6, 13.0), (35.6, 12.7), (40.8, 12.6), (41.7, 13.0), (42.0, 13.95), (43.6, 13.95), (44.05, 14.4),
               (44.05, 22.0), (43.6, 22.6), (43.0, 23.05), (37.4, 22.8), (34.9, 20.4), (34.0, 16.5)], 1.2, 7.2,
          JAW, insets=0.9, chz=1.2, steps=3, round_it=0)
    bolt(bm, 41.6, 15.6, 7.2, mat=JAW)
    bolt(bm, 41.6, 19.4, 7.2, mat=JAW)
    # ACTUATOR pod under the jaw (rows 21-27.5, cols 34-43), tapering down the screen.
    loft(bm, [(39.0, 21.0, 4.0, 0.6, 4.8), (38.7, 23.0, 3.6, 0.6, 4.4), (38.0, 24.6, 3.0, 0.7, 3.9),
              (37.3, 25.9, 2.2, 0.8, 3.4), (36.4, 26.6, 1.6, 1.0, 2.9), (35.7, 27.0, 0.9, 1.2, 2.5)],
         ACT, sides=20, p=2.6, grooves=[(2.4, 0.2, 0.45), (4.2, 0.2, 0.45)])
    # RODS: two piston rods meeting at a clevis under the socket.
    loft(bm, [(28.6, 21.4, 1.5, 0.4, 2.0), (31.6, 24.0, 1.7, 0.4, 2.0), (34.6, 26.6, 1.3, 0.5, 2.0)], WRIST,
         sides=16, p=3.0)
    tube(bm, [(28.2, 20.9, 3.1, 0.7), (31.4, 23.8, 3.0, 0.72), (34.6, 26.4, 2.8, 0.7)], sides=10, mat=ROD)
    tube(bm, [(35.55, 19.6, 4.6, 0.75), (35.55, 23.0, 3.8, 0.78), (35.55, 26.5, 2.9, 0.75)], sides=10, mat=ROD)
    tube(bm, [(33.2, 27.1, 2.4, 1.05), (35.6, 27.1, 2.4, 1.05)], sides=10, mat=HUB)

    # FOREARM drum hanging under the elbow (rows 29-39, cols 15-22): a round drum along the screen with
    # two machined bands.
    fr = [(28.0, 2.6), (28.8, 3.1), (29.5, 3.25), (30.2, 3.3), (32.0, 3.3), (32.15, 3.5), (32.85, 3.5), (33.0, 3.3),
          (35.0, 3.3), (35.15, 3.5), (35.85, 3.5), (36.0, 3.3), (37.0, 3.0), (37.9, 2.5), (38.7, 1.6)]
    tube(bm, [(18.55 - max(0, r - 35.5) * 0.35, r, 3.6, rad) for r, rad in fr], sides=20, mat=FORE)

    # CLAW: an open hoop of round tubing over a tapered finger, the hoop's right side one bright run of
    # pipe down into the gem.
    hc, hr, ax, ay = 9.95, 35.3, 2.7, 3.0
    hoop = []
    for k in range(28):
        t = 2 * math.pi * k / 28
        hoop.append((hc + ax * math.cos(t), hr + ay * math.sin(t), 2.9, 1.45))
    tube(bm, hoop, sides=14, closed=True, zscale=1.25,
         matf=lambda c, r: PIPE if (c > hc + 1.4 and r > hr - 2.2) else HOOP)
    # the palm under the hoop and the mount joining it to the forearm (dark, low)
    block(bm, [(6.0, 33.4), (6.1, 32.4), (7.1, 31.4), (7.4, 31.0), (12.0, 31.6), (13.0, 31.0), (16.6, 31.0),
               (16.9, 39.9), (13.0, 39.9), (8.4, 38.0)], 0.3, 1.9, WRIST, insets=0.4, chz=0.4, round_it=0)
    loft(bm, [(10.9, 38.9, 4.9, 0.4, 3.6), (10.2, 41.2, 4.2, 0.4, 3.7), (9.85, 43.0, 3.7, 0.4, 3.6),
              (9.0, 45.0, 3.8, 0.5, 3.4), (8.0, 46.7, 3.75, 0.6, 3.2), (7.4, 48.3, 3.5, 0.7, 2.9),
              (7.45, 49.5, 3.1, 0.9, 2.5), (7.25, 50.6, 2.3, 1.2, 2.0)], FING, sides=22, p=2.6,
         grooves=[(4.0, 0.2, 0.45)])
    pipe = [(12.95, 37.0, 3.0, 0.9), (12.85, 38.6, 3.5, 0.9), (12.3, 40.6, 3.9, 0.9), (11.3, 42.8, 4.0, 0.88),
            (10.1, 44.8, 3.85, 0.85), (8.9, 46.2, 3.6, 0.8)]
    tube(bm, pipe, sides=12, mat=PIPE, zscale=1.1)
    # GEM held in the finger's tip
    ellipsoid(bm, 6.45, 48.6, 3.0, 2.45, 1.85, 1.9, GEM, rot=38, segs=20, rings=10, lower=0.8)


def mirror(bm):
    for v in bm.verts:
        v.co.x = -v.co.x + 1 / 12
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])


def merged_sprite():
    data = common.load_sprite(WT, "newsh9-1")
    for side in WINDOWS.values():
        for n in side:
            data["colors"].update(common.load_sprite(WT, n)["colors"])
    return data


STEEL_SPEC = 0.5 * ((1.0 / 3.0) ** 2 / 0.04)  # F0 of IOR 2.0 via Specular IOR Level (D176)


def materials(sprite):
    def pal(i, metallic, roughness, spec=True, emission=0.0):
        m = common.palette_material(sprite, i, TAG, metallic=metallic, roughness=roughness,
                                    emission_strength=emission)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        if spec and "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = STEEL_SPEC
        return m
    return [
        pal(7, 0.45, 0.40),  # HOUSE
        pal(10, 0.5, 0.34),  # KNUCK
        pal(6, 0.45, 0.42),  # NECK
        pal(9, 0.45, 0.38),  # COWL
        pal(5, 0.45, 0.42),  # BEAM
        pal(3, 0.35, 0.55),  # WRIST
        pal(9, 0.5, 0.34),  # BALL
        pal(10, 0.5, 0.32),  # LIP
        pal(4, 0.3, 0.6, spec=False),  # SOCK
        pal(3, 0.4, 0.5),  # HUB
        pal(9, 0.45, 0.38),  # JAW
        pal(4, 0.4, 0.48),  # ACT
        pal(7, 0.55, 0.3),  # ROD
        pal(7, 0.45, 0.4),  # FORE
        pal(6, 0.45, 0.4),  # HOOP
        pal(4, 0.4, 0.48),  # FING
        pal(9, 0.5, 0.34),  # PIPE
        pal(153, 1.0, 0.7, spec=False, emission=0.6),  # GEM (D126/D173: glow on metallic 1, rough)
    ]


def build(side):
    sprite = merged_sprite()
    coll = common.reset_collection(f"{NAME}-{side}")
    bm = bmesh.new()
    build_left(bm)
    if side == "right":
        mirror(bm)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(f"{NAME}-{side}")
    bm.to_mesh(mesh)
    bm.free()
    for m in materials(sprite):
        mesh.materials.append(m)
    obj = bpy.data.objects.new(f"{NAME}-{side}", mesh)
    coll.objects.link(obj)
    return obj, coll, sprite


def split_open(obj, layout):
    """Each piece keeps the part of `obj` inside its 24 x 28 px window, open along the cut (the
    neighbouring piece closes the surface; no cap wall to show where the renderer lifts a piece, D181)."""
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


def layout(side):
    return [(n, x0 + 12 - W / 2, y0 + 14 - H / 2) for n, (x0, y0) in WINDOWS[side].items()]


def finish_normals(obj):
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(40))


def make_side(side):
    obj, coll, sprite = build(side)
    bpy.context.view_layer.update()
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    shell = common.outline_shell(sealed, coll, voxel=0.012, faces=5000, smooth=4, inside=0.004, islands="outer")
    bpy.data.objects.remove(sealed, do_unlink=True)
    shell.name = f"{NAME}-{side}_outline"
    T.cull_hidden(obj, grid=4, ndirs=40)
    finish_normals(obj)
    lay = layout(side)
    bodies = split_open(obj, lay)
    shells = split_open(shell, lay)
    pieces = []
    for n, _, _ in lay:
        b, sh = bodies[n], shells[n]
        b.name = n
        sh.name = f"{n}_outline"
        sh["tyrian_outline"] = True
        finish_normals(b)
        sh.data.shade_smooth()
        if len(sh.data.polygons) == 0:
            print(f"WARNING: {n} outline has no mesh")
        pieces.append((n, b, sh))
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME} ({side}): whole {tris} tris, z max {max(v.co.z for v in obj.data.vertices) * 12:.2f} px; "
          + ", ".join(f"{n} {sum(len(p.vertices) - 2 for p in b.data.polygons)} tris / shell "
                      f"{len(sh.data.polygons)} faces" for n, b, sh in pieces))
    return obj, shell, pieces


def run(script_file, side):
    """Build one arm and export its three pieces (models and spriteModels entries)."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    obj, shell, pieces = make_side(side)
    root = common.repo_root(script_file)
    for n, b, sh in pieces:
        data = common.load_sprite(root, n)
        common.export_sprite_model(root, [b, sh], f"enemies/{n}", data["sprites"])
    if "--pieces" in argv:  # review output only
        pdir = Path(argv[argv.index("--pieces") + 1])
        for n, b, sh in pieces:
            common.export_glb([b, sh], str(pdir / f"{n}.glb"))
