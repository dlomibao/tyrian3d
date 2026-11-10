"""The SAVARA fighter squadron (newshf-85, -77, -55, -53), batch b023, rebuilt as flying fighters.

All four are FLYING FIGHTERS spawned on the sky layer, flying DOWN the screen: the nose is the
bottom end of every sprite, the tail the top. Undersides are closed, rounded, plain.

newshf-85 (newshf.shp 85 / 87 / 89, the gold beetle fighter) is built here from its sprite. Reading
of the level frame 87 (centre line = column 13's centre; u = column edge - 13.5, y = row edge, down
the screen = forward, z up, all in sprite px):
- a broad gold shield hull (the beetle's carapace and head, rows 10.5-25): half width 13 - y/2 from
  row 11 (7.5 px) straight to the pointed nose at row 25, a low dome in section (the pale 28/30
  pixels down its crest at rows 13-15 and along the snout are sheen) with its edge skirt low;
  two raised wing-case (elytra) plates on its back split by a centre seam, a triangular scutellum
  plate between their roots, a head seam at row 16.75 and a snout seam at row 21;
- two pale-blue sensor lights (109, emissive) in grey bezels on the scutellum at u = -/+1, row 12;
- a round dark maw (16) at rows 17-20 cut into the head, a pale fang (30) rising from its floor;
- two swept-back claw blades (27) from the hull's rear corners to points beside the tail
  (u -/+7.1, row 6.6): a round outer spine (the pale outer column is sheen on it), thinning to a
  sharp inner edge that is grey steel (10) over rows 8-10.5, with a grey cuff at the root;
- behind the hull a narrow waist (rows 8-10, 3 px) and a rear engine segment (rows 5-8) in darker
  gold (22) with grey side plates (8), two grey thruster nozzles (10) at its rear corners (the grey
  "horns" of the sprite, rows 4-5, u -/+3) and a pale tail stinger (28) rising back to row 2.
The frames roll the craft about its long axis: 87 level, 85 right side up, 89 left side up (the
claws and hull pull in a pixel each side, the stinger moves a pixel).

newshf-55, -53 and -77 are pixel-exact recolours of D121/D65 flagships (same masks, IoU 1.0, a fixed
index map): newshf-55 = newshf-47's level frame 49 (+16, maw 1 -> 1, eyes 116 -> 132),
newshf-53 = newshf-11 (+32, glass and bores 1 -> 34), newshf-77/79 = newshf-123's frames 123/125
(+99, deep 1 -> 96, the body one step darker: fuse 106, wing/fin 105, tail 104, as the sprite's
wings sit at 104-105). They are built by the flagship scripts themselves (loaded as modules, nothing
edited), with the palette index remapped and the export redirected here.

    blender --background --python assets/blender/enemies/newshf-85.py [-- --only 85,77,55,53] [--no-bake]

Run alone it builds newshf-85, -85-f2, -85-f3; newshf-77.py, newshf-55.py and newshf-53.py call run()
here for their own craft. Exports public/models/enemies/<model>.glb and the spriteModels entries.
"""

import importlib.util
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
WT = HERE.parent.parent.parent
sys.path[:0] = [str(WT / "assets" / "blender")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = set(ARGV[ARGV.index("--only") + 1].split(",")) if "--only" in ARGV else {"85"}
BAKE = "--no-bake" not in ARGV
NAME = "newshf-85"
PX = 1 / 12
UX = 1.5  # u = 0 (column 13's centre, x edge 13.5) is 1.5 px right of the 24 px block's centre
ROLL = math.radians(float(ARGV[ARGV.index("--roll") + 1]) if "--roll" in ARGV else 30.0)
Z_AXIS = float(ARGV[ARGV.index("--zaxis") + 1]) if "--zaxis" in ARGV else 0.5  # roll axis height

# --- materials -----------------------------------------------------------------------------------
BODY, ELY, CLAW, REAR, STING, GREY, SIDE, LIGHT, MAW, FANG, DARK = range(11)
MATS = [(BODY, 23, "body", 0.3, 0.42), (ELY, 25, "elytra", 0.3, 0.4), (CLAW, 26, "claw", 0.3, 0.4),
        (REAR, 22, "rear", 0.3, 0.45), (STING, 28, "sting", 0.25, 0.4), (GREY, 10, "grey", 0.55, 0.36),
        (SIDE, 8, "side", 0.55, 0.4), (LIGHT, 109, "light", 0.0, 0.2), (MAW, 16, "maw", 0.1, 0.7),
        (FANG, 30, "fang", 0.2, 0.35), (DARK, 4, "dark", 0.3, 0.6)]


def materials(sprite):
    out = []
    for slot, idx, tag, met, rough in MATS:
        kw = {"emission_strength": 2.0} if slot == LIGHT else {}
        out.append(common.palette_material(sprite, idx, f"nshf85A_{tag}", metallic=met, roughness=rough, **kw))
    return out


# --- shield hull ---------------------------------------------------------------------------------
SW = T.pchip([10.55, 10.8, 11.3, 12.0, 16.0, 18.0, 20.0, 23.0, 24.3, 25.0, 25.4],
             [6.3, 7.15, 7.42, 7.0, 5.05, 4.2, 3.2, 1.6, 0.9, 0.45, 0.05])
SZT = T.pchip([10.55, 11.0, 12.5, 14.5, 17.0, 20.0, 23.0, 25.4], [2.2, 2.75, 3.35, 3.55, 3.4, 2.9, 2.0, 0.55])
SZB = T.pchip([10.55, 11.0, 12.5, 14.5, 17.0, 20.0, 23.0, 25.4], [-0.7, -1.0, -1.25, -1.4, -1.55, -1.5, -1.05, -0.1])
# right half of the section from the top centre round to the keel: (fraction of half width,
# fraction of height from the bottom). A low chamfered dome over a skirt edge, a round belly.
SEC = [(0.0, 1.0), (0.36, 0.965), (0.64, 0.87), (0.84, 0.7), (0.95, 0.52), (1.0, 0.36), (0.95, 0.2),
       (0.75, 0.06), (0.4, 0.0)]


def ring_from(sec, w, zt, zb, grow=0.0):
    h = zt - zb
    full = [(w * a, zb + h * b) for a, b in sec] + [(-w * a, zb + h * b) for a, b in reversed(sec)][:-1]
    c = (0.0, zb + h * 0.45)
    if grow:
        vn, _ = T.offset_loop(full, c)
        full = [(x + nx * grow, z + nz * grow) for (x, z), (nx, nz) in zip(full, vn)]
    return full, c


def shield_loop(y, grow=0.0):
    return ring_from(SEC, max(SW(y), 0.02), SZT(y), SZB(y), grow)


def surf_top(sec, w, zt, zb, u):
    h = zt - zb
    a = min(abs(u) / max(w, 1e-6), 1.0)
    for (a0, b0), (a1, b1) in zip(sec, sec[1:]):
        if a0 <= a <= a1 + 1e-9:
            f = (a - a0) / max(a1 - a0, 1e-9)
            return zb + h * (b0 + (b1 - b0) * f)
    return zb + h * sec[-1][1]


def shield_top(u, y):
    return surf_top(SEC[:6], SW(y), SZT(y), SZB(y), u)


def groove_rings(loopf, ys, grooves, d=0.16, gw=0.12):
    allst = [(s, 0.0) for s in ys if all(abs(s - g) > gw + 0.15 for g in grooves)]
    for g in grooves:
        allst += [(g - gw - 0.03, 0.0), (g - gw, -d), (g + gw, -d), (g + gw + 0.03, 0.0)]
    allst.sort()
    return [(loopf, y, gr) for y, gr in allst]


def build_shield(P):
    ys = [10.55, 10.65, 10.8, 11.0, 11.3, 11.7, 12.2, 12.8, 13.5, 14.3, 15.1, 15.9, 16.4, 17.2, 18.0, 18.8,
          19.6, 20.4, 21.6, 22.3, 23.0, 23.6, 24.1, 24.6, 25.0, 25.25, 25.4]
    rings = groove_rings(shield_loop, ys, (16.75, 21.0))
    T.loft_rings(P, rings, [BODY] * (len(rings) - 1))


# --- fuselage: waist and rear engine segment -----------------------------------------------------
FY = [3.95, 4.3, 5.0, 6.0, 7.6, 8.05, 8.5, 9.6, 10.05, 10.5, 11.5, 13.5]
FW = T.pchip(FY, [0.8, 1.15, 2.45, 2.6, 2.6, 2.05, 1.7, 1.7, 2.05, 2.6, 3.0, 3.0])
FZT = T.pchip(FY, [1.25, 1.75, 2.2, 2.4, 2.4, 2.05, 1.85, 1.85, 2.1, 2.45, 2.7, 2.7])
FZB = T.pchip(FY, [0.05, -0.3, -0.6, -0.8, -0.8, -0.5, -0.4, -0.4, -0.5, -0.7, -0.9, -0.9])
FSEC = [(0.0, 1.0), (0.45, 0.95), (0.8, 0.8), (0.98, 0.58), (1.0, 0.42), (0.9, 0.2), (0.6, 0.04), (0.25, 0.0)]


def fus_loop(y, grow=0.0):
    return ring_from(FSEC, FW(y), FZT(y), FZB(y), grow)


def fus_top(u, y):
    return surf_top(FSEC[:5], FW(y), FZT(y), FZB(y), u)


def build_fuselage(P):
    ys = [3.95, 4.15, 4.5, 5.0, 5.6, 6.3, 7.0, 7.6, 8.05, 8.5, 9.0, 9.6, 10.05, 10.5, 11.5, 13.5]
    rings = groove_rings(fus_loop, ys, (5.35, 7.8), d=0.14, gw=0.1)
    T.loft_rings(P, rings, [REAR] * (len(rings) - 1))


# --- mesh helpers (from newshf-47) ---------------------------------------------------------------

def lathe(P, centre, axis, profile, sides, mats, phase=0.0):
    axis = Vector(axis).normalized()
    ref = Vector((1, 0, 0)) if abs(axis.x) < 0.9 else Vector((0, 1, 0))
    a = (ref - axis * ref.dot(axis)).normalized()
    b = axis.cross(a)
    rows = []
    for r, h in profile:
        c = Vector(centre) + axis * h
        if r < 1e-6:
            rows.append([P.v(c)])
        else:
            rows.append([P.v(c + (a * math.cos(phase + 2 * math.pi * k / sides) +
                                  b * math.sin(phase + 2 * math.pi * k / sides)) * r) for k in range(sides)])
    mats = mats if isinstance(mats, list) else [mats] * (len(rows) - 1)
    for j, (r0, r1) in enumerate(zip(rows, rows[1:])):
        n = max(len(r0), len(r1))
        for i in range(n):
            k = (i + 1) % n
            if len(r0) == 1:
                P.f((r0[0], r1[i], r1[k]), mats[j])
            elif len(r1) == 1:
                P.f((r0[i], r0[k], r1[0]), mats[j])
            else:
                P.f((r0[i], r0[k], r1[k], r1[i]), mats[j])
    if len(rows[0]) > 1:
        P.f(list(reversed(rows[0])), mats[0])
    if len(rows[-1]) > 1:
        P.f(rows[-1], mats[-1])


def sweep(P, pts, radii, sides, mat, flat=1.0, phase=0.5):
    pts = [Vector(p) for p in pts]
    ts = [(pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(len(pts))]
    up = Vector((0, 0, 1))
    rows = []
    for p, t, r in zip(pts, ts, radii):
        ref = up if abs(t.dot(up)) < 0.95 else Vector((0, 1, 0))
        n = (ref - t * ref.dot(t)).normalized()
        bn = t.cross(n)
        if r < 1e-6:
            rows.append([P.v(p)])
            continue
        rows.append([P.v(p + (bn * math.cos(2 * math.pi * (k + phase) / sides) * r +
                              n * math.sin(2 * math.pi * (k + phase) / sides) * r * flat)) for k in range(sides)])
    for r0, r1 in zip(rows, rows[1:]):
        n = max(len(r0), len(r1))
        for i in range(n):
            k = (i + 1) % n
            if len(r0) == 1:
                P.f((r0[0], r1[i], r1[k]), mat)
            elif len(r1) == 1:
                P.f((r0[i], r0[k], r1[0]), mat)
            else:
                P.f((r0[i], r0[k], r1[k], r1[i]), mat)
    if len(rows[0]) > 1:
        P.f(list(reversed(rows[0])), mat)
    if len(rows[-1]) > 1:
        P.f(rows[-1], mat)


def drape(P, poly, ztop, off0, off1, ch, mat, nsub=4, rings=(0.66, 0.33)):
    """A plate lying on a surface: footprint the convex polygon `poly` [(u, y)], each edge split in
    `nsub`, its top following ztop(u, y) + off1 with chamfered edges `ch`, its base ztop + off0.
    The top is filled with concentric rings shrunk towards the centroid (so it stays curved)."""
    bnd = []
    n = len(poly)
    for i in range(n):
        (u0, y0), (u1, y1) = poly[i], poly[(i + 1) % n]
        for k in range(nsub):
            t = k / nsub
            bnd.append((u0 + (u1 - u0) * t, y0 + (y1 - y0) * t))
    cu = sum(p[0] for p in bnd) / len(bnd)
    cy = sum(p[1] for p in bnd) / len(bnd)

    def shrink(pts, d):
        out = []
        for u, y in pts:
            du, dy = u - cu, y - cy
            ln = math.hypot(du, dy) or 1e-9
            out.append((u - du / ln * d, y - dy / ln * d))
        return out

    def scale(pts, s):
        return [(cu + (u - cu) * s, cy + (y - cy) * s) for u, y in pts]

    top0 = shrink(bnd, ch)
    loops = [[P.v((u, y, ztop(u, y) + off0)) for u, y in bnd],
             [P.v((u, y, ztop(u, y) + off1 - ch)) for u, y in bnd],
             [P.v((u, y, ztop(u, y) + off1)) for u, y in top0]]
    for s in rings:
        loops.append([P.v((u, y, ztop(u, y) + off1)) for u, y in scale(top0, s)])
    m = len(bnd)
    for r0, r1 in zip(loops, loops[1:]):
        for i in range(m):
            k = (i + 1) % m
            P.f((r0[i], r0[k], r1[k], r1[i]), mat)
    c = P.v((cu, cy, ztop(cu, cy) + off1))
    for i in range(m):
        P.f((loops[-1][i], loops[-1][(i + 1) % m], c), mat)
    P.f(list(reversed(loops[0])), mat)


def mirror(P, start_vert):
    bm = P.bm
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[start_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    ret = bmesh.ops.duplicate(bm, geom=list(verts) + faces)
    for g in ret["geom"]:
        if isinstance(g, bmesh.types.BMVert):
            g.co.x = -g.co.x
    bmesh.ops.reverse_faces(bm, faces=[g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)])


def top_of(u, y):
    """The hull's upper surface under (u, y): the higher of shield and fuselage."""
    z = -9.0
    if 10.55 <= y <= 25.4 and abs(u) <= SW(y):
        z = max(z, shield_top(u, y))
    if 3.95 <= y <= 13.5 and abs(u) <= FW(y):
        z = max(z, fus_top(u, y))
    return z


# --- parts ---------------------------------------------------------------------------------------

def build_plates(P):
    """Elytra plates either side of a centre seam, a scutellum between their roots."""
    s = len(P.bm.verts)
    ely = [(2.95, 10.85), (6.35, 10.9), (6.7, 11.55), (4.05, 16.45), (0.16, 16.45), (0.16, 14.75)]
    drape(P, ely, shield_top, -0.35, 0.26, 0.18, ELY, nsub=4)
    mirror(P, s)
    # bolt heads on each wing case: rear outer corner and front
    for bu, by in ((-5.2, 11.6), (-2.6, 15.4)):
        for sgn in (-1, 1):
            u = bu * sgn
            z = shield_top(u, by) + 0.2
            lathe(P, (u, by, z - 0.12), (0, 0, 1), [(0.0, 0.0), (0.34, 0.0), (0.34, 0.14), (0.22, 0.22), (0.0, 0.22)],
                  6, GREY)
    scut = [(-2.75, 10.75), (2.75, 10.75), (0.0, 14.55)]
    drape(P, scut, top_of, -0.3, 0.36, 0.16, ELY, nsub=4)


def build_lights(P):
    for u in (-1.0, 1.0):
        y = 11.95
        z = top_of(u, y) + 0.3
        lathe(P, (u, y, z - 0.35), (0, 0, 1), [(0.0, 0.0), (0.82, 0.0), (0.82, 0.32), (0.66, 0.42), (0.56, 0.42),
                                               (0.56, 0.3), (0.0, 0.3)], 12, GREY)
        lathe(P, (u, y, z - 0.05), (0, 0, 1), [(0.54, 0.0), (0.5, 0.14), (0.36, 0.26), (0.18, 0.33), (0.0, 0.35)],
              12, LIGHT)


# maw: a round port in the head, rows 17-20 (centre row 18.5), +-1.5 px
MAW_C = (0.0, 18.5)
MAW_R = 1.42


def build_maw_cutter(P):
    n = 16
    def ring(r, dz):
        return [P.v((MAW_C[0] + r * math.cos(2 * math.pi * k / n), MAW_C[1] + r * math.sin(2 * math.pi * k / n),
                     shield_top(MAW_C[0] + r * math.cos(2 * math.pi * k / n),
                                MAW_C[1] + r * math.sin(2 * math.pi * k / n)) + dz)) for k in range(n)]
    rings = [ring(MAW_R + 0.3, 2.0), ring(MAW_R + 0.3, 0.05), ring(MAW_R, -0.28), ring(MAW_R - 0.25, -0.75)]
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            k = (i + 1) % n
            P.f((r0[i], r0[k], r1[k], r1[i]), MAW)
    P.f(rings[0], MAW)
    c = P.v((MAW_C[0], MAW_C[1], shield_top(*MAW_C) - 0.85))
    for i in range(n):
        P.f((rings[-1][i], rings[-1][(i + 1) % n], c), MAW)


def build_fang(P):
    z0 = shield_top(*MAW_C) - 0.8
    pts = [(0.0, 18.75, z0 - 0.1), (0.0, 18.65, z0 + 0.35), (0.0, 18.45, z0 + 0.75), (0.0, 18.2, z0 + 1.05)]
    sweep(P, pts, [0.48, 0.42, 0.26, 0.0], 8, FANG, flat=1.0)


def build_snout(P):
    """A keel ridge down the snout (the pale centre line, rows 21-24)."""
    poly = [(-0.55, 21.35), (0.55, 21.35), (0.42, 24.1), (0.0, 24.6), (-0.42, 24.1)]
    drape(P, poly, shield_top, -0.3, 0.2, 0.12, BODY, nsub=3)


def claw_outer(y):
    return T.pchip([6.6, 7.0, 7.6, 8.5, 11.0, 11.8, 12.6, 13.2], [-7.05, -7.36, -7.45, -7.45, -7.42, -6.9, -6.0, -5.5])(y)


def claw_inner(y):
    return T.pchip([6.6, 7.0, 7.5, 10.5, 11.1, 13.2], [-7.05, -7.02, -6.75, -3.8, -3.5, -3.4])(y)


CT = T.pchip([6.6, 7.2, 8.5, 10.5, 13.2], [0.15, 1.0, 1.7, 2.2, 2.4])
CZ = T.pchip([6.6, 7.3, 8.5, 10.5, 13.2], [0.75, 0.5, 0.3, 0.3, 0.3])
# section from the outer spine to the inner edge: (fraction outer -> inner, z offset as a fraction of
# the thickness); top side first, then back along the bottom.
CSEC_TOP = [(0.0, 0.02), (0.07, 0.4), (0.22, 0.58), (0.42, 0.5), (0.56, 0.36)]
CSEC_EDGE = (1.0, 0.0)
CSEC_BOT = [(0.6, -0.2), (0.35, -0.36), (0.12, -0.32)]


def claw_z(y, f):
    """Height of the claw's mid surface at fraction f across it (0 outer spine, 1 inner edge): about
    the roll axis' height, so the rocking frames close the claws in by the roll alone."""
    zi = CZ(y) + 0.15
    zo = CZ(y)
    return zo + (zi - zo) * f


def build_claw(P):
    """Left claw: a loft along y from the tip (row 6.6) into the hull (row 13); the right is its mirror."""
    s = len(P.bm.verts)
    ys = [6.6, 6.8, 7.1, 7.5, 8.0, 8.6, 9.2, 9.8, 10.4, 11.0, 11.8, 12.6, 13.2]
    rows = []
    for y in ys:
        a, b = claw_outer(y), claw_inner(y)
        d, t = b - a, CT(y)
        if y <= 6.6 + 1e-6:
            rows.append([P.v((a, y, claw_z(y, 0.0)))])
            continue
        pts = [(a + d * f, claw_z(y, f) + t * g) for f, g in CSEC_TOP] + [(b, claw_z(y, 1.0))] + \
              [(a + d * f, claw_z(y, f) + t * g) for f, g in CSEC_BOT]
        rows.append([P.v((u, y, z)) for u, z in pts])
    nt = len(CSEC_TOP)
    for j, (r0, r1) in enumerate(zip(rows, rows[1:])):
        ym = (ys[j] + ys[j + 1]) / 2
        n = max(len(r0), len(r1))
        for i in range(n):
            k = (i + 1) % n
            # the inner edge's two facets (top and bottom of the blade) are grey steel over rows 8-10.6
            blade = (i in (nt - 1, nt)) and 7.9 <= ym <= 11.3
            mat = GREY if blade else CLAW
            if len(r0) == 1:
                P.f((r0[0], r1[i], r1[k]), mat)
            else:
                P.f((r0[i], r0[k], r1[k], r1[i]), mat)
    P.f(rows[-1], CLAW)
    mirror(P, s)


def build_rear(P):
    s = len(P.bm.verts)
    # grey side plate on the engine segment's flank (cols 11 / 15, rows 5-8)
    drape(P, [(1.45, 5.2), (2.5, 5.25), (2.5, 7.6), (1.45, 7.55)], fus_top, -0.4, 0.16, 0.1, SIDE, nsub=3)
    # thruster nozzle at the rear corner (the sprite's grey horn, col 16, rows 4-5), pointing back
    c = (2.78, 6.05, 0.55)
    lathe(P, c, (0, -1, 0.1), [(0.0, -0.05), (0.4, -0.05), (0.5, 0.25), (0.5, 1.45), (0.45, 1.95),
                               (0.3, 1.95), (0.3, 1.65), (0.0, 1.55)], 12,
          [GREY, GREY, GREY, GREY, GREY, DARK, DARK])
    # pylon tying the nozzle to the segment
    T.hull(P, T.cbox(1.8, 2.6, 4.9, 5.9, 0.2, 1.0, 0.12), REAR)
    mirror(P, s)
    # intake grille: three ribs across the engine segment's back
    for y0 in (5.75, 6.45, 7.15):
        drape(P, [(-1.3, y0), (1.3, y0), (1.3, y0 + 0.36), (-1.3, y0 + 0.36)], fus_top, -0.3, 0.18, 0.08, REAR, nsub=3)
    # tail stinger, rising back from the segment's rear to row 2
    sweep(P, [(0.0, 5.4, 1.6), (0.0, 4.4, 2.0), (0.0, 3.4, 2.35), (0.0, 2.5, 2.6), (0.0, 2.0, 2.7), (0.0, 1.75, 2.72)],
          [0.75, 0.64, 0.55, 0.46, 0.3, 0.0], 8, STING, phase=0.0)
    lathe(P, (0.0, 4.85, 1.5), (0, -1, 0.3), [(0.0, -0.25), (0.9, -0.25), (1.0, -0.05), (1.0, 0.2), (0.85, 0.3),
                                              (0.0, 0.3)], 10, REAR)


# --- assembly ------------------------------------------------------------------------------------

def to_blender(roll):
    """Build px -> Blender, rolled by `roll` (radians, + lifts the right side: the top moves to -u)."""
    c, s = math.cos(roll), math.sin(roll)
    R = Matrix(((c, 0, -s, s * Z_AXIS), (0, 1, 0, 0), (s, 0, c, Z_AXIS - c * Z_AXIS), (0, 0, 0, 1)))
    B = Matrix(((PX, 0, 0, UX * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    return B @ R


def finish(P, mats, coll, name, roll=0.0):
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.transform(bm, matrix=to_blender(roll), verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(34))
    return obj


def join_objs(objs, name, coll):
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in objs[0].data.materials:
        me.materials.append(mat)
    for o in objs:
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(data)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(34))
    return obj


def build85(sprite, coll, name, roll):
    mats = materials(sprite)
    B = T.Part(name + "_hull")
    build_shield(B)
    body = finish(B, mats, coll, name + "_hull", roll)
    C = T.Part(name + "_cut")
    build_maw_cutter(C)
    cutter = finish(C, mats, coll, name + "_cut", roll)
    mod = body.modifiers.new("maw", "BOOLEAN")
    mod.operation, mod.solver, mod.object, mod.material_mode = "DIFFERENCE", "EXACT", cutter, "TRANSFER"
    dg = bpy.context.evaluated_depsgraph_get()
    cut = bpy.data.meshes.new_from_object(body.evaluated_get(dg))
    old = body.data
    body.modifiers.clear()
    body.data = cut
    bpy.data.meshes.remove(old)
    cdata = cutter.data
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.meshes.remove(cdata)
    P = T.Part(name + "_rest")
    build_fuselage(P)
    build_plates(P)
    build_lights(P)
    build_fang(P)
    build_snout(P)
    build_claw(P)
    build_rear(P)
    rest = finish(P, mats, coll, name + "_rest", roll)
    obj = join_objs([body, rest], name, coll)
    for p in obj.data.polygons:  # plates and blocks: flat facets
        if p.material_index in (GREY, SIDE):
            p.use_smooth = False
    return obj


def bake(obj, textured, model):
    tint, tex = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = (1.0, 1.0, 1.0), textured
    try:
        T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{model}_bake_"), size=512, samples=48)
    finally:
        T.TINT, T.TEXTURED = tint, tex
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", model)


def frame_sprites(sprite, indices):
    out = []
    for s in sprite["sprites"]:
        fr = [f for f in s["frames"] if f in indices]
        if fr:
            out.append({**s, "frames": fr})
    return out


def export(objs, model, sprites):
    common.export_sprite_model(WT, objs, f"enemies/{model}", sprites, image_format="WEBP" if BAKE else "AUTO")


def main85():
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME + "_A")
    for k, (frame, roll) in enumerate(((85, ROLL), (87, 0.0), (89, -ROLL))):
        model = NAME if k == 0 else f"{NAME}-f{k + 1}"
        obj = build85(sprite, coll, model, roll)
        src = obj.copy()
        src.data = obj.data.copy()
        coll.objects.link(src)
        T.cull_hidden(obj, grid=3, ndirs=40)
        if BAKE:
            bake(obj, (BODY, ELY, CLAW, REAR, STING, GREY, SIDE, FANG, DARK), model)
        shell = common.outline_shell(src, coll)
        bpy.data.objects.remove(src, do_unlink=True)
        shell.name = shell.data.name = f"{model}_outline"
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        print(f"{model} (frame {frame}): {tris} triangles")
        export([obj, shell], model, frame_sprites(sprite, [frame]))


# --- recolours of the flagships (newshf-47 / -11 / -123), built by their own scripts -------------

def load_module(script, modname):
    spec = importlib.util.spec_from_file_location(modname, WT / "assets" / "blender" / "enemies" / script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Patched:
    """common.palette_material with a remapped index."""

    def __init__(self, remap):
        self.remap = remap

    def __enter__(self):
        self.pm = common.palette_material
        pm, remap = self.pm, self.remap

        def palette_material(sprite, index, tag, **kw):
            return pm(sprite, remap(index), tag, **kw)

        common.palette_material = palette_material

    def __exit__(self, *a):
        common.palette_material = self.pm


def main55():
    mod = load_module("newshf-47.py", "nshf47_flagship")
    mod.TAG = "nshf55A"
    sprite = common.load_sprite(WT, "newshf-55")
    coll = common.reset_collection("newshf-55_A")
    with Patched(lambda i: {1: 1, 116: 132}.get(i, i + 16)):
        obj = mod.build(sprite, coll, "newshf-55", 0.0)
        shell = common.outline_shell(obj, coll)
        shell.name = "newshf-55_outline"
        print("newshf-55: triangles", sum(len(p.vertices) - 2 for p in obj.data.polygons))
        export([obj, shell], "newshf-55", sprite["sprites"])


def main53():
    mod = load_module("newshf-11.py", "nshf11_flagship")
    mod.NAME = "newshf-53"
    saved = sys.argv
    sys.argv = saved[:saved.index("--") + 1] + ([] if BAKE else ["--no-bake"]) if "--" in saved else saved + ["--"] + ([] if BAKE else ["--no-bake"])
    try:
        with Patched(lambda i: 34 if i == 1 else i + 32):
            mod.main()
    finally:
        sys.argv = saved


def main77():
    mod = load_module("newshf-123.py", "nshf123_flagship")
    mod.NAME = "newshf-77"
    mod.FRAMES = [(77, "newshf-77", mod.ROLL), (79, "newshf-77-f2", 0.0)]
    saved = sys.argv
    sys.argv = saved[:saved.index("--") + 1] + ([] if BAKE else ["--no-bake"]) if "--" in saved else saved + ["--"] + ([] if BAKE else ["--no-bake"])
    try:
        # +99 except the body: the sprite's wings sit at 104-105 (f77 median 104.5, f79 105, ignoring
        # the 96 ink and 109-111 highlights), so fuselage 8 -> 106, wing/fin 7 -> 105, tail 6 -> 104.
        with Patched(lambda i: {1: 96, 6: 104, 7: 105, 8: 106}.get(i, i + 99)):
            mod.main()
    finally:
        sys.argv = saved


def run(only):
    if "85" in only:
        main85()
    if "55" in only:
        main55()
    if "53" in only:
        main53()
    if "77" in only:
        main77()


if __name__ == "__main__":
    run(ONLY)
