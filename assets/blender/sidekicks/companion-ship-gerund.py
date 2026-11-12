"""Companion Ship Gerund (sidekick option 21; tyrian.shp#9 frame 49, drawn 2x2 = a 24x28 block): the final design.

What it is: a small trailing escort fighter (style 1) in blue steel. Reading the sprite (symmetric
about the middle of column 12; rows 7-19, columns 3-21; one frame, no banking, so D93 does not apply):
- a round cockpit pod down the middle (columns 9-15, rows 8-17, palette 59): a round nose (rows 8-10),
  parallel flanks, rounded aft corners to a flat stern at row edge 18. The pale 60-63 ring round the
  canopy and down column 9 is its lit rim (sheen), not paint;
- a dark grey bubble canopy (rows 10-13, columns 10-14, 102); the 110 pixel is a glint;
- a grey dorsal spine (column 12, rows 14-17, 107) sloping down between two brown engine nacelles
  (columns 10-14, rows 16-17, 163/164; dark flanks 161) whose dark nozzles (162) end at row 18-19;
  dark intake pockets ahead of them and gills beside them (51);
- either side a gun rail (column 7: a bright streak down a 1 px part = a cylinder, 60) with a purple
  muzzle housing in front (rows 9-10, 85/89) and a breech block behind (row 15, 91), joined to the
  pod by a dark recessed pylon (column 8, 48);
- outside the rails, short swept wings (columns 4-6, rows 10-14, 53), lit on the middle column: a
  chordwise ridge.

Design B leads with silhouette and readability from the small tilted game camera: a tall pod with a
high, clearly separate canopy bubble; rails standing well above the low wings with a dark slot
between rail and pod (the pylon sits low); a gabled wing that splits into a lit and a shaded facet;
nacelles that rise clear of the aft deck either side of the spine. Then detail where the camera
sees: chamfered armour plates with real panel gaps (nose cap seam, lengthwise shoulder seams), a
machined canopy collar, cooling collars on the rail barrels, octagonal housings, intake grilles,
gill louvres, spine access grooves, nozzles with lips and dark bores. Underside: a plain closed belly.

Units while building: sprite px, x = column edge - 12.5 (the symmetry axis), r = row edge (aft is +r),
z up. Blender: X = (x + 0.5) / 12, Y = (14 - r) / 12, Z = z / 12.

    Blender --background --factory-startup --python companion-ship-gerund.py -- [--out x.glb] [--no-bake]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)
MODEL = "sidekicks/companion-ship-gerund"

NAME = "sidekick-companion-ship-gerund"
TAG = "gerundB"
PX = 1 / 12
pchip, frange, Part, hull, cbox = T.pchip, T.frange, T.Part, T.hull, T.cbox


def ST(pts):
    return pchip([p[0] for p in pts], [p[1] for p in pts])


# --- materials ------------------------------------------------------------------------------------
(HULL, CORE, COLLAR, GLASS, SPINE, NACELLE, NOZZLE, BORE, TROUGH, RAIL, FRONT, BREECH, PYLON, WING,
 GROOVE) = range(15)
# The sprite's own palette index per region (median, darkest/brightest 15% dropped as lighting):
# pod 59, canopy 102, spine 107, engine 163, nozzle 162, trough 51, rail 60, rail front 88,
# rail rear 91, neck 48, wing 53. The panel-gap core is the pod's ramp two steps down (56).
PAL_OF = {HULL: 59, CORE: 56, COLLAR: 59, GLASS: 102, SPINE: 107, NACELLE: 163, NOZZLE: 162, BORE: 161,
          TROUGH: 51, RAIL: 60, FRONT: 88, BREECH: 91, PYLON: 48, WING: 53, GROOVE: 102}
TEXTURED = tuple(k for k in PAL_OF if k != GLASS)
TINT = (0.97, 0.99, 1.0)


def materials(sprite):
    def rgb(i):
        return common.srgb(*sprite["colors"][str(i)])

    def pal(slot, tag, metallic, roughness):
        i = PAL_OF[slot]
        return common.material(f"pal_{i}_{TAG}_{tag}", rgb(i), metallic=metallic, roughness=roughness)
    # Satin metal: metallic 0.3-0.45, roughness 0.3-0.45 (not mirror), the glass glossy.
    return [
        pal(HULL, "hull", 0.42, 0.36),
        pal(CORE, "core", 0.3, 0.6),
        pal(COLLAR, "collar", 0.45, 0.28),
        pal(GLASS, "glass", 0.1, 0.12),
        pal(SPINE, "spine", 0.42, 0.34),
        pal(NACELLE, "nacelle", 0.38, 0.42),
        pal(NOZZLE, "nozzle", 0.42, 0.42),
        pal(BORE, "bore", 0.1, 0.8),
        pal(TROUGH, "intake", 0.3, 0.55),
        pal(RAIL, "rail", 0.45, 0.3),
        pal(FRONT, "muzzle", 0.35, 0.4),
        pal(BREECH, "breech", 0.35, 0.4),
        pal(PYLON, "pylon", 0.3, 0.55),
        pal(WING, "wing", 0.4, 0.4),
        pal(GROOVE, "groove", 0.2, 0.7),
    ]


# --- the pod ----------------------------------------------------------------------------------------
# Half width on the sprite's inner mask (D74): round nose rows 8-10, parallel flanks |x| 3.5 (columns
# 9-15), rounded aft corners, flat stern at row edge 18. Includes the armour plates' standoff D.
D = 0.12
PW = ST([[7.88, 0.15], [8.05, 0.95], [8.5, 1.6], [9.0, 2.1], [9.5, 2.6], [10.0, 3.05], [10.5, 3.38],
         [11.2, 3.52], [16.6, 3.52], [17.3, 3.4], [17.75, 3.05], [18.0, 2.6]])
# Deck height (centre line) and belly; the waist (widest point) at ZM.
ZT = ST([[7.88, 1.35], [8.3, 2.0], [9.0, 2.6], [10.0, 3.0], [12.0, 3.2], [14.0, 3.12], [15.5, 2.88],
         [17.0, 2.58], [18.0, 2.42]])
ZB = ST([[7.88, 1.15], [8.5, 0.62], [10.0, 0.32], [16.0, 0.26], [18.0, 0.42]])
ZM = 1.25
E_TOP, E_BOT = 2.4, 3.0
N_POD = 24
R0, R1 = 7.88, 18.0


def sp(t, e):
    return math.copysign(abs(t) ** (2 / e), t)


def pod_loop(r, grow=0.0):
    """Section of the pod's core at row r (outer surface minus D, plus grow)."""
    rr = min(max(r, R0), R1)
    w = max(PW(rr) - D + grow, 0.05)
    ht = max(ZT(rr) - ZM - D + grow, 0.05)
    hb = max(ZM - ZB(rr) - D + grow, 0.05)
    pts = []
    for k in range(N_POD):
        a = 2 * math.pi * k / N_POD
        c, s = math.cos(a), math.sin(a)
        z = ZM + (ht * sp(s, E_TOP) if s >= 0 else hb * sp(s, E_BOT))
        pts.append((w * sp(c, E_TOP if s >= 0 else E_BOT), z))
    return pts, (0.0, ZM)


def top_z(x, r):
    """The pod's outer deck height at (x, r)."""
    rr = min(max(r, R0), R1)
    w, h = PW(rr), ZT(rr) - ZM
    if abs(x) >= w:
        return ZM
    return ZM + h * (1 - abs(x / w) ** E_TOP) ** (1 / E_TOP)


def build_pod(P):
    L = lambda y: pod_loop(y)  # noqa: E731
    T.loft(P, L, [R0 + 0.02] + frange(8.05, 18.0, 0.5), CORE, cap0=True)
    # Nose cap: all round, its back edge chamfered; the seam behind it at r 9.6.
    T.plate(P, L, 8.12, 9.55, HULL, d=D, ch0=False, ystep=0.35, c=0.1)
    sec = T.Section(L, 8.12)
    tip = [sec.at(k, D) for k in range(sec.n)]
    # Its tip: a small flat chamfer face (a convex hull of the cap's front ring and a quarter-size
    # copy of it at the very front), not a point.
    cx, cz = sec.centre
    face = [(cx + (x - cx) * 0.3, 7.88, cz + (z - cz) * 0.3 + 0.05) for x, _, z in tip]
    hull(P, tip + face, HULL)
    # Body: a deck plate (shoulder to shoulder over the top) and a lower plate (flanks and belly);
    # their lengthwise seams run along the shoulders (k = 1.6 and 10.4: 24 and 156 degrees).
    T.plate(P, L, 9.68, 17.98, HULL, s0=1.6, s1=10.4, d=D, c=0.1, ystep=0.6)
    T.plate(P, L, 9.68, 17.98, HULL, s0=-13.4, s1=1.4, d=D, c=0.1, ystep=0.6)


def build_canopy(G, F):
    """The dark bubble over rows 10-13, columns 10-14, in a raised machined collar."""
    cr, rx, ry, fw = 12.0, 2.45, 2.05, 0.34
    n = 28
    zb = top_z(0, cr)
    rings = []
    for k in range(n):
        a = 2 * math.pi * k / n
        ca, sa = math.cos(a), math.sin(a)

        def at(g, dz, base=True):
            x, r = (rx + g) * ca, cr + (ry + g * ry / rx) * sa
            return (x, r, (top_z(x, r) if base else zb) + dz)
        rings.append([F.v(at(fw, -0.3)), F.v(at(fw, 0.02)), F.v(at(fw * 0.55, 0.16)), F.v(at(0.02, 0.16)),
                      F.v(at(-0.06, -0.25))])
    for k in range(n):
        a, b = rings[k], rings[(k + 1) % n]
        for i in range(4):
            F.f((a[i], a[i + 1], b[i + 1], b[i]), COLLAR, away=(0.0, cr, zb - 1.5))
    # Glass: a dome, its crown a little aft of centre; rises 0.95 over the collar.
    steps, hgt = 7, 0.95
    domes = []
    for j in range(steps):
        t = j / steps
        ph = t * math.pi / 2
        s = math.cos(ph)
        ring = []
        for k in range(n):
            a = 2 * math.pi * k / n
            x, r = rx * s * math.cos(a), cr + 0.12 * (1 - s) + ry * s * math.sin(a)
            base = top_z(x, r) + 0.1 if j == 0 else 0.0
            z = base if j == 0 else None
            ring.append([x, r, z])
        domes.append(ring)
    # Heights: edge follows the deck under the collar's top, then a smooth cap.
    edge_z = [p[2] for p in domes[0]]
    top = max(edge_z) + hgt
    out = []
    for j, ring in enumerate(domes):
        ph = j / steps * math.pi / 2
        vs = []
        for k, (x, r, z) in enumerate(ring):
            if z is None:
                z = edge_z[k] + (top - edge_z[k]) * math.sin(ph)
            vs.append(G.v((x, r, z)))
        out.append(vs)
    crown = G.v((0.0, cr + 0.12, top))
    gc = (0.0, cr, zb - 0.5)
    for l0, l1 in zip(out, out[1:]):
        for k in range(n):
            m = (k + 1) % n
            G.f((l0[k], l0[m], l1[m], l1[k]), GLASS, away=gc)
    for k in range(n):
        G.f((out[-1][k], out[-1][(k + 1) % n], crown), GLASS, away=gc)
    low = [G.v((x, r, z - 0.4)) for (x, r, z) in [tuple(v.co) for v in out[0]]]
    for k in range(n):
        m = (k + 1) % n
        G.f((out[0][k], out[0][m], low[m], low[k]), GLASS, away=gc)
    G.f(low, GLASS, out=(0, 0, -1))


def build_spine(P):
    """The grey dorsal spine (column 12, rows 14-17) from the collar's back down to the stern."""
    zt = ST([[13.75, 3.45], [15.0, 3.36], [16.5, 3.08], [18.05, 2.72]])
    rs = frange(13.75, 18.05, 0.45)
    rings = []
    for k, r in enumerate(rs):
        hb, ht = 0.45, 0.24
        z = zt(r)
        zb = top_z(0, min(r, 17.9)) - 0.35
        rings.append([P.v(p) for p in ((-hb, r, zb), (hb, r, zb), (hb, r, z - 0.22), (ht, r, z), (-ht, r, z),
                                       (-hb, r, z - 0.22))])
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        c = (0.0, rs[k], zt(rs[k]) - 0.6)
        for i in range(6):
            j = (i + 1) % 6
            P.f((a[i], a[j], b[j], b[i]), SPINE, away=c)
    P.f(rings[0], SPINE, out=(0, -1, 0))
    P.f(rings[-1], SPINE, out=(0, 1, 0))
    # Access-panel grooves across the spine top.
    for r in (15.2, 16.7):
        z = zt(r)
        hull(P, cbox(-0.27, 0.27, r - 0.05, r + 0.05, z - 0.06, z + 0.012, 0.01), GROOVE)


def tube(P, x, z, prof, mats, n=12, cap0=True, cap1=True, rot=0.0):
    """A round (or n-gon) part along r at (x, z): prof [(r, radius)], mats per segment."""
    rings = []
    for r, rad in prof:
        rings.append([P.v((x + rad * math.cos(2 * math.pi * k / n + rot), r, z + rad * math.sin(2 * math.pi * k / n + rot)))
                      for k in range(n)])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        m = mats[i] if isinstance(mats, (list, tuple)) else mats
        rm = (prof[i][0] + prof[i + 1][0]) / 2
        for k in range(n):
            j = (k + 1) % n
            if abs(prof[i][0] - prof[i + 1][0]) < 1e-6:
                P.f((a[k], a[j], b[j], b[k]), m, out=(0, 1 if prof[i + 1][1] < prof[i][1] else -1, 0))
            else:
                P.f((a[k], a[j], b[j], b[k]), m, away=(x, rm, z))
    m0 = mats[0] if isinstance(mats, (list, tuple)) else mats
    m1 = mats[-1] if isinstance(mats, (list, tuple)) else mats
    if cap0:
        P.f(rings[0], m0, out=(0, -1, 0))
    if cap1:
        P.f(rings[-1], m1, out=(0, 1, 0))


NAC = dict(x=1.25, z=2.2, R=0.84, r0=15.85, r1=18.0, noz=0.56, end=18.85)


def build_engines(P):
    N = NAC
    for s in (-1, 1):
        x, z, R = s * N["x"], N["z"], N["R"]
        # Nacelle: rounded intake lip, body, a machined band, then the nozzle bell.
        # It flares aft: narrow at the intake (row 16: column 11 only), full width at row 17.
        tube(P, x, z, [(N["r0"], 0.45 * R), (N["r0"] + 0.1, 0.66 * R), (N["r0"] + 0.35, 0.74 * R), (16.9, 0.9 * R),
                       (16.9, 0.96 * R), (17.15, 0.96 * R), (17.15, 0.96 * R), (N["r1"], 0.93 * R)],
             [NACELLE, NACELLE, NACELLE, NACELLE, NACELLE, NACELLE, NACELLE], n=14, cap0=False, cap1=False)
        tube(P, x, z, [(N["r0"], 0.45 * R), (N["r0"] + 0.15, 0.28 * R)], BORE, n=14, cap0=False, cap1=True)
        # Nozzle: a lip, the bell, its rim, a dark bore.
        tube(P, x, z, [(N["r1"], 0.93 * R), (N["r1"], N["noz"] * 1.02), (N["r1"] + 0.1, N["noz"]),
                       (N["end"], 0.92 * N["noz"]), (N["end"], 0.68 * N["noz"]), (N["end"] - 0.35, 0.6 * N["noz"])],
             [NOZZLE, NOZZLE, NOZZLE, NOZZLE, BORE], n=14, cap0=False, cap1=True)
        # Intake grille ahead of the nacelle (the sprite's dark 51 at column 11, row 15): a raised
        # dark ramp with two bars.
        x0, x1 = sorted((s * 0.72, s * 1.9))
        zf = top_z(1.3, 14.6)
        hull(P, [(xx, r, zz) for xx in (x0, x1) for r, zz in ((14.6, zf - 0.25), (14.6, zf + 0.03),
                                                             (15.9, zf + 0.3), (15.9, zf - 0.3))], TROUGH)
        for rb in (14.95, 15.3, 15.65):
            zb = zf + 0.04 + (rb - 14.6) / 1.3 * 0.27
            hull(P, cbox(x0 + 0.08, x1 - 0.08, rb - 0.04, rb + 0.04, zb - 0.06, zb + 0.05, 0.015), TROUGH)
        # Gill louvres beside the nacelle (the dark 51 at column 10, row 16).
        gx0, gx1 = sorted((s * 1.8, s * 2.7))
        zg0 = top_z(2.25, 16.3)
        hull(P, cbox(gx0, gx1, 15.8, 16.85, zg0 - 0.25, zg0 + 0.03, 0.03), TROUGH)
        for k, rg in enumerate((16.0, 16.32, 16.64)):
            zg = top_z(2.35, rg)
            hull(P, cbox(gx0, gx1, rg - 0.13, rg + 0.13, zg - 0.2, zg + 0.07, 0.03), TROUGH)


RAILD = dict(x=5.0, z=1.62, R=0.52)


def build_rails(P):
    Rl = RAILD
    for s in (-1, 1):
        x, z, R = s * Rl["x"], Rl["z"], Rl["R"]
        # Barrel with two cooling collars.
        tube(P, x, z, [(10.85, R), (12.0, R), (12.0, 1.1 * R), (12.22, 1.1 * R), (12.22, R), (13.55, R),
                       (13.55, 1.1 * R), (13.77, 1.1 * R), (13.77, R), (15.05, R)],
             [RAIL] * 9, n=14, cap0=False, cap1=False)
        # Front housing: octagonal recoil block, chamfered ends, then the muzzle stub with its bore.
        H = 0.62
        tube(P, x, z, [(8.95, 0.34), (9.0, 0.42), (9.12, H), (10.8, H), (10.95, 0.5)], FRONT, n=8,
             rot=math.pi / 8)
        tube(P, x, z, [(8.55, 0.3), (8.95, 0.33)], FRONT, n=10, cap0=False, cap1=False)
        tube(P, x, z, [(8.55, 0.3), (8.55, 0.17), (8.75, 0.15)], BORE, n=10, cap0=False, cap1=True)
        # Breech block (row 15).
        tube(P, x, z, [(14.95, 0.5), (15.08, H), (15.75, H), (15.98, 0.4)], BREECH, n=8, rot=math.pi / 8)


def build_pylons(P):
    """The dark pylon between pod and rail (column 8, rows 10-16): low, in the rail's shadow."""
    for s in (-1, 1):
        xa, xb = 3.1, 4.75
        pts = []
        for x in (xa, xb):
            for r, zt in ((10.15, 1.05), (10.45, 1.28), (16.2, 1.28), (16.75, 1.0)):
                pts += [(s * x, r, zt), (s * x, r + (0.15 if r < 12 else -0.15), 0.62)]
        hull(P, pts, PYLON)


def build_wings(P):
    """Short swept wings outboard of the rails (columns 4-6, rows 10-14): a gabled plate with a
    chordwise ridge at |x| 7 (the sprite's lit middle column), root under the rail."""
    plan = [(4.75, 10.05), (5.9, 9.9), (8.32, 12.32), (8.42, 12.62), (8.42, 14.5), (8.2, 14.93),
            (4.75, 14.95)]
    ridge = [(7.0, 11.0), (7.0, 14.94)]

    def ztop(x):
        if x <= 7.0:
            return 1.15 + (1.55 - 1.15) * (x - 4.75) / (7.0 - 4.75)
        return 1.55 + (0.98 - 1.55) * (x - 7.0) / (8.42 - 7.0)
    zbot = 0.78
    cx, cr = 6.3, 12.6
    for s in (-1, 1):
        pts = []
        for x, r in plan + ridge:
            dx, dr = cx - x, cr - r
            ln = math.hypot(dx, dr) or 1
            c = 0.07
            outer = x > 4.8
            pts.append((s * x, r, ztop(x) - (c if outer else 0)))
            pts.append((s * x, r, zbot + (c if outer else 0)))
            if outer:
                pts.append((s * (x + dx / ln * c), r + dr / ln * c, ztop(x) + (0.0 if x in (7.0,) else 0.0)))
                pts.append((s * (x + dx / ln * c), r + dr / ln * c, zbot))
        hull(P, pts, WING, merge_angle=0.5)
        # Panel lines (inside the plan, so the top-view outline is unchanged): a spar seam across the
        # inboard facet, a trailing-edge flap line along the whole wing, a short aileron break.
        def zt(x):
            return ztop(x)
        for xa, xb in ((5.0, 5.9), (6.0, 6.9)):
            xm = (xa + xb) / 2
            hull(P, [(s * px, py, pz) for px, py, pz in cbox(xa, xb, 14.05, 14.25, zt(xm) - 0.1, zt(xm) + 0.02, 0.02)], GROOVE)
        for xa, xb in ((7.1, 7.8), (7.9, 8.3)):
            xm = (xa + xb) / 2
            hull(P, [(s * px, py, pz) for px, py, pz in cbox(xa, xb, 14.05, 14.25, zt(xm) - 0.1, zt(xm) + 0.02, 0.02)], GROOVE)
        xm = 5.45
        hull(P, [(s * px, py, pz) for px, py, pz in cbox(xm - 0.1, xm + 0.1, 10.9, 13.95, zt(xm) - 0.1, zt(xm) + 0.02, 0.02)], GROOVE)


def finish(part, mats, coll):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0.5 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj


def build(coll, mats):
    H = Part(f"{TAG}_pod", smooth_angle=40)
    build_pod(H)
    Dt = Part(f"{TAG}_details", smooth_angle=35)
    build_spine(Dt)
    build_engines(Dt)
    build_rails(Dt)
    build_pylons(Dt)
    Wg = Part(f"{TAG}_wings", smooth_angle=20)
    build_wings(Wg)
    G = Part(f"{TAG}_glass", smooth_angle=70)
    F = Part(f"{TAG}_collar", smooth_angle=40)
    build_canopy(G, F)
    objs = [finish(p, mats, coll) for p in (H, Dt, Wg, G, F)]
    for o in objs:
        print("gerundB part", o.name, sum(len(q.vertices) - 2 for q in o.data.polygons))
    return objs


# --- texture: baked occlusion and edge wear (copied from the warfly/ship bakes: no shared edits) ----

def bake_maps(obj, out_dir, size=512, samples=64):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    # Wide margins: the islands' gutters get mipmapped into them at game scale (black specks).
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.02, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{TAG}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{TAG}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    # Neutral background (white = no occlusion; mid roughness, satin metal) instead of black, so
    # whatever gutter the extend margin leaves never darkens a mip.
    col_img.generated_color = (TINT[0], TINT[1], TINT[2], 1.0)
    rm_img.generated_color = (1.0, 0.4, 0.4, 1.0)
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(slot, m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        L = nt.links.new
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    L(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.02
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.1
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.003
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                L(math_("MULTIPLY", v, TINT[k]), comb.inputs[k])
            L(comb.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(i, m, mode) for i, m in enumerate(mats)}
        bpy.ops.object.bake(type="EMIT", margin=24, margin_type="EXTEND", use_clear=False)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()

    for i in TEXTURED:
        m = mats[i]
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])



def outline_shell_all(obj, collection, voxel=0.008, faces=1500, smooth=6, min_extent=0.002):
    """common.outline_shell (D51), copied, keeping EVERY outer voxel island above min_extent (top-view
    bbox area, m^2) instead of only the largest: the wings, rails and pylons remesh as islands of their
    own, and with the largest-only rule they lost their ink (the game turns the model's own outline
    off once a shell exists). Inner cavity shells (negative signed volume) are dropped."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    collection.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    for mod in list(shell.modifiers):
        shell.modifiers.remove(mod)
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    rm.use_smooth_shade = True
    common._apply_modifiers(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bm.verts.ensure_lookup_table()
    islands, seen = [], set()
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            isl.append(x)
            stack.extend(e.other_vert(x) for e in x.link_edges)
        islands.append(isl)

    def extent(isl):
        xs = [v.co.x for v in isl]
        ys = [v.co.y for v in isl]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))

    def volume(isl):
        ids = {v.index for v in isl}
        faces_ = {f for v in isl for f in v.link_faces}
        vol = 0.0
        for f in faces_:
            if not all(v.index in ids for v in f.verts):
                continue
            c = [v.co for v in f.verts]
            for k in range(1, len(c) - 1):
                vol += c[0].dot(c[k].cross(c[k + 1])) / 6
        return vol
    keep_ids = set()
    for isl in islands:
        e, vo = extent(isl), volume(isl)
        kept = e >= min_extent and vo > 0
        if len(isl) > 40:
            xs = [v.co.x for v in isl]
            ys = [v.co.y for v in isl]
            print(f"gerundB shell island: {len(isl)} verts, x {min(xs):.2f}..{max(xs):.2f} y {min(ys):.2f}..{max(ys):.2f}, "
                  f"volume {vo:.6f}, {'kept' if kept else 'dropped'}")
        if kept:
            keep_ids |= {v.index for v in isl}
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep_ids], context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    common._apply_modifiers(shell)
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):  # the factory scene's cube, camera and light
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    objs = build(coll, mats)
    obj = T.join(objs, NAME)
    # The outline shell comes from the closed parts BEFORE cull_hidden: the cull deletes the faces
    # hidden under the plates (the pod core, its caps, tube ends), which leaves the pod open, and
    # the voxel remesh of an open surface came out as a hollow skin with no nose and no nozzles.
    shell = outline_shell_all(obj, coll, voxel=0.008, faces=1500)
    print(f"gerundB: outline shell {len(shell.data.polygons)} faces")
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"gerundB: {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        # The shell must not be in the scene while baking: it occludes the AO rays (dark veins).
        coll.objects.unlink(shell)
        bake_maps(obj, tempfile.mkdtemp(prefix="gerundB_bake_"))
        coll.objects.link(shell)
        fmt = "WEBP"
    common.export_sprite_model(WT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    print("gerundB exported")


if __name__ == "__main__":
    main()
