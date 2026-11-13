"""Design A for the merged item newshv-163 / newshv-237 / newshv-235 (newshv.shp, palette 5, one frame each).

Identity (brief, enemy_behaviour): what each thing IS decides the build.
- newshv-163: a small red CAR, ground layer, drives UP the screen nose first (y -9..-2 px/tick against a
  scroll of 1), so its top (row 3) is the bonnet and the yellow pixels at rows 5-6 are its HEADLIGHTS on the
  front wings; the two yellow pixels at row 24 are its tail lamps. Wheels stand on the HD ground (z = 0).
  Reading of the sprite (no ink ring: kind "none", the model goes to the outer edge):
    bonnet rows 3-8 (pal 71, the 72-73 streaks are sheen), dark cowl row 8 (68), windscreen rows 9-11
    (146-149, median 147) with dark A-pillars at the corners (cols 8 / 14), side windows cols 7-8 / 14-15
    (rows 11-14 and 16-18) split by a red B-pillar at row 15, roof cols 9-13 rows 12-18 (71), rear window
    rows 19-20 (147), boot lid rows 21-24 (71); the outer column of the body is a step darker (69-70:
    the wing slope in shade, D176: given 70). Grey 100-102 pixels outside the body at rows 9-11 and 20-21
    are the TYRES showing past the wheel arch flares (rows 8 / 19 dark red: the flare lips).
- newshv-237: a finned blue ROCKET pointing LEFT (custom event 49: swoops, then x -6..0 px/tick, leaves on
  the left: it flies nose first). 24x16-ish. Round closed body flying free (bottom 1 px above the ground),
  fins level at the axis height (D163). Rows 10-15 body (median 55), joint band cols 10-12 (52), canards
  cols 4-8, main fins cols 11-15 (56), dark neck cols 15-19 (51) carried between two dark tail strakes
  (interior ink, pal 1) with blue nav lights at cols 16 and 18 (156 / 152), and a wide tail shroud ring
  at cols 20-22 (rows 9-16, 56) round the nozzle (its front face is the ink column 20).
- newshv-235: the same rocket mirrored to point RIGHT (the sprite is 237 mirrored pixel for pixel).

Not a one-model script any more: building this file (tools/build-models.sh assets/blender/enemies/lib_b111.py)
exports all three models (enemies/newshv-163, -237, -235 plus their spriteModels entries); the entry scripts
newshv-163.py / newshv-237.py / newshv-235.py build one each (main(which)).
    Blender --background --factory-startup --python lib_b111.py -- [--model car|r237|r235] [--views DIR] [--no-bake]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

PX = 1 / 12
pchip = T.pchip


def W(p):
    """sprite px (x = column edge, y = row edge, z up in px) -> Blender units (origin = sprite centre)."""
    return Vector(((p[0] - 12) * PX, (14 - p[1]) * PX, p[2] * PX))


class Part:
    """A bmesh built in sprite px; converted to Blender units when made an object."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, vs, mat):
        if len({id(v) for v in vs}) < 3:
            return None
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        return face

    def obj(self, coll, mats, mirror_x=None):
        bm = self.bm
        for v in bm.verts:
            x, y, z = v.co
            if mirror_x is not None:
                x = 2 * mirror_x - x
            v.co = W((x, y, z))
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        o = bpy.data.objects.new(self.name, me)
        coll.objects.link(o)
        return o


def tube(P, rings, mats, cap0=True, cap1=True):
    """Bridge consecutive rings (lists of verts, same length); mats(i, k) or a slot."""
    def mat(i, k):
        return mats(i, k) if callable(mats) else mats
    out = []
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        n = max(len(r0), len(r1))
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1:
                face = P.f((r0[0], r1[j], r1[k]), mat(i, k))
            elif len(r1) == 1:
                face = P.f((r0[k], r0[j], r1[0]), mat(i, k))
            else:
                face = P.f((r0[k], r0[j], r1[j], r1[k]), mat(i, k))
            out.append(face)
    c0 = c1 = None
    if cap0 and len(rings[0]) > 2:
        c0 = P.f(list(reversed(rings[0])), mat(0, 0))
    if cap1 and len(rings[-1]) > 2:
        c1 = P.f(rings[-1], mat(len(rings) - 2, 0))
    return out, c0, c1


def hull_points(P, pts, mat):
    """A convex hull of px points as one closed part."""
    bm = P.bm
    vs = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in vs if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    for f in {f for v in live if v.is_valid for f in v.link_faces}:
        f.material_index = mat


def cbox(P, x0, x1, y0, y1, z0, z1, ch, mat, chz=None):
    hull_points(P, T.cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


def ellipsoid(P, c, axes, radii, mat, nu=14, nv=7):
    """A closed ellipsoid: centre c, orthonormal axes (a, b, up), radii (ra, rb, rc)."""
    c = Vector(c)
    a, b, u = (Vector(x) for x in axes)
    ra, rb, rc = radii
    rings = []
    for j in range(1, nv):
        th = math.pi * j / nv - math.pi / 2
        ring = []
        for k in range(nu):
            ph = 2 * math.pi * k / nu
            p = c + a * (ra * math.cos(th) * math.cos(ph)) + b * (rb * math.cos(th) * math.sin(ph)) + u * (rc * math.sin(th))
            ring.append(P.v(tuple(p)))
        rings.append(ring)
    bot = P.v(tuple(c - u * rc))
    top = P.v(tuple(c + u * rc))
    tube(P, [[bot]] + rings + [[top]], mat, cap0=False, cap1=False)


def materials(sprite, table, tag):
    return [common.palette_material(sprite, idx, f"{tag}_{name}", metallic=metal, roughness=rough,
                                    emission_strength=glow)
            for name, idx, metal, rough, glow in table]


def boolean(obj, cutter):
    mod = obj.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    try:
        mod.material_mode = "TRANSFER"
    except Exception:
        pass
    bpy.context.view_layer.update()
    common._apply_modifiers(obj)


# =====================================================================================================
# newshv-163: the red car
# =====================================================================================================
CAR = "newshv-163"
CX = 11.5  # body centre line (columns 6-16)
CAR_MATS = [
    ("paint", 71, 0.45, 0.32, 0.0),
    ("paint_side", 70, 0.45, 0.36, 0.0),
    ("pillar", 70, 0.45, 0.36, 0.0),
    ("cowl", 68, 0.4, 0.5, 0.0),
    ("trim", 67, 0.3, 0.55, 0.0),
    ("glass", 147, 0.3, 0.08, 0.0),
    ("tyre", 101, 0.0, 0.85, 0.0),
    ("rim", 102, 0.75, 0.32, 0.0),
    ("well", 100, 0.0, 0.9, 0.0),
    ("grille", 100, 0.5, 0.55, 0.0),
    ("lamp", 123, 1.0, 0.9, 1.0),
    ("tail", 123, 1.0, 0.9, 0.8),
]
CM = {n: i for i, (n, *_r) in enumerate(CAR_MATS)}
CAR_GLOW = {"lamp", "tail"}

# plan half widths (car-relative), sprite rows (y = row edge)
WT_ = pchip([3.1, 3.5, 4.5, 5.5, 6.5, 7.4, 22.5, 23.5, 24.5, 24.85],
            [1.4, 1.95, 3.6, 4.6, 5.3, 5.5, 5.5, 4.7, 3.7, 3.15])
WL_ = pchip([3.1, 3.5, 4.5, 5.5, 6.5, 7.3, 7.95, 12.0, 12.6, 18.35, 18.95, 21.9, 22.5, 23.5, 24.5, 24.85],
            [1.4, 1.95, 3.6, 4.6, 5.3, 5.5, 5.95, 5.95, 5.5, 5.5, 5.95, 5.95, 5.5, 4.7, 3.7, 3.15])
ZT_ = pchip([3.1, 3.35, 3.9, 4.8, 6.0, 8.4, 11.0, 19.0, 21.3, 23.2, 24.4, 24.85],
            [3.55, 3.85, 4.15, 4.4, 4.62, 4.85, 4.95, 4.95, 4.9, 4.8, 4.6, 4.3])
ZB_ = pchip([3.1, 4.2, 6.0, 23.0, 24.3, 24.85], [1.4, 1.1, 0.95, 0.95, 1.1, 1.35])
ZS_ = pchip([3.1, 5.0, 23.5, 24.85], [2.6, 2.9, 2.9, 2.8])

WHEELS = (10.3, 20.55)  # wheel centres (rows)
WR = 1.8  # wheel radius px
W_IN, W_OUT = 4.65, 6.5  # tyre inner / outer face (car-relative |x|)

DOOR_LINES = (12.75, 15.5, 18.4)  # door shut lines (side only)
TOP_LINES = (8.45, 21.35)  # bonnet rear edge, boot lid front edge (top only)
GROOVE = 0.09


def car_ring(y):
    """Right half of the body section at row y: [(u, z, tag)] from bottom centre to top centre."""
    wt, wl = float(WT_(y)), float(WL_(y))
    zt, zb, zs = float(ZT_(y)), float(ZB_(y)), float(ZS_(y))
    h = zt - zb
    z1 = zb + min(0.25, 0.1 * h)
    z2 = zb + min(0.75, 0.25 * h)
    z3 = min(max(zs, z2 + 0.1 * h), zb + 0.55 * h)
    z4 = z3 + min(0.35, 0.1 * h)
    z5 = zt - min(1.0, 0.22 * h)
    z6 = zt - min(0.45, 0.1 * h)
    z7 = zt - min(0.15, 0.04 * h)
    xs = wt - min(0.95, 0.5 * wt)
    return [
        (0.0, zb, "bot"),
        (wl - min(0.7, 0.45 * wl), zb, "bot"),
        (wl - 0.2, z1, "side"),
        (wl, z2, "side"),
        (wl, z3, "side"),
        (wt + 0.3 * (wl - wt), z4, "side"),
        (wt - 0.1, z5, "side"),
        (wt - 0.3, z6, "shoulder"),
        (wt - min(0.62, 0.3 * wt), z7, "shoulder"),
        (xs + 0.1, zt - 0.05, "top"),
        (xs, zt - 0.06, "hoodline"),
        (xs - 0.1, zt - 0.06, "top"),
        (0.5 * (xs - 0.1), zt + 0.0, "top"),
        (0.0, zt + 0.03, "top"),
    ]


def car_stations():
    ys = [3.1, 3.18, 3.3, 3.45, 3.65, 3.9]
    y = 4.2
    while y < 24.3:
        ys.append(round(y, 3))
        y += 0.7
    ys += [24.45, 24.6, 24.72, 24.8, 24.85]
    for g in DOOR_LINES + TOP_LINES:
        ys += [g - 0.08, g, g + 0.08]
    for wy in WHEELS:  # arch edges get stations so the flare reads clean
        ys += [wy - 2.25, wy + 2.25]
    ys = sorted(set(round(v, 3) for v in ys))
    out = []
    for v in ys:  # drop stations closer than 0.06 to a groove triplet's members
        if out and v - out[-1] < 0.05:
            continue
        out.append(v)
    return out


def build_car_body(P):
    ys = car_stations()
    rings = []
    tags_all = []
    for y in ys:
        half = car_ring(y)
        right = half
        left = [(-u, z, t) for u, z, t in reversed(half[1:-1])]
        loop = right + left
        g_door = any(abs(y - g) < 1e-3 for g in DOOR_LINES)
        g_top = any(abs(y - g) < 1e-3 for g in TOP_LINES)
        hood_run = (3.9 <= y <= TOP_LINES[0]) or (TOP_LINES[1] <= y <= 24.6)
        ring = []
        for u, z, t in loop:
            if g_door and t == "side" and z > float(ZB_(y)) + 0.3:
                u -= GROOVE * (1 if u > 0 else -1)
            if g_top and t in ("top", "hoodline"):
                z -= GROOVE
            if t == "hoodline" and hood_run:
                z -= GROOVE
            ring.append(P.v((CX + u, y, z)))
        rings.append(ring)
        tags_all.append([t for _u, _z, t in loop])
    n = len(rings[0])
    wtv = [float(WT_(y)) for y in ys]

    def mat(i, k):
        y = 0.5 * (ys[i] + ys[i + 1])
        a, b = rings[i][k].co, rings[i][(k + 1) % n].co
        u = abs(0.5 * (a.x + b.x) - CX)
        z = 0.5 * (a.z + b.z)
        t1, t2 = tags_all[i][k], tags_all[i][(k + 1) % n]
        if "bot" in (t1, t2) and z < float(ZB_(y)) + 0.05:
            return CM["well"]
        if u > wtv[i] - 0.55 or t1 == "side" or t2 == "side":
            return CM["paint_side"]
        if 8.05 < y < 8.75 and u < wtv[i] - 1.0:
            return CM["cowl"]
        return CM["paint"]
    faces, c0, c1 = tube(P, rings, mat)
    # grille in the nose face, a recessed panel in the tail face
    for cap, m, th in ((c0, CM["grille"], 0.32), (c1, CM["trim"], 0.38)):
        if cap is None:
            continue
        res = bmesh.ops.inset_region(P.bm, faces=[cap], thickness=th, depth=-0.12, use_even_offset=True)
        cap.material_index = m


def gh_outline(yf, sides, yr, nf=8, nr=7, pf=2.6, pr=2.4):
    """Right half of a greenhouse plan ring: front arc, side stations [(u, y)], rear arc."""
    a0, y0 = sides[0]
    al, yl = sides[-1]
    pts, zone = [], []
    for k in range(nf):
        t = (k / nf) * math.pi / 2
        pts.append((a0 * math.sin(t) ** (2 / pf), y0 - (y0 - yf) * math.cos(t) ** (2 / pf)))
        zone.append("front")
    for u, y in sides:
        pts.append((u, y))
        zone.append("side")
    for k in range(1, nr + 1):
        t = (k / nr) * math.pi / 2
        pts.append((al * math.cos(t) ** (2 / pr), yl + (yr - yl) * math.sin(t) ** (2 / pr)))
        zone.append("rear")
    return pts, zone


GH_BASE = (8.7, [(4.4, 10.9), (4.5, 11.8), (4.5, 12.8), (4.5, 13.9), (4.5, 14.9), (4.5, 16.1), (4.5, 17.0),
                 (4.5, 17.9), (4.45, 18.7), (4.35, 19.4)], 21.0)
GH_ROOF = (12.0, [(2.45, 12.9), (2.45, 13.4), (2.45, 13.9), (2.45, 14.4), (2.45, 14.95), (2.45, 16.05),
                  (2.5, 16.6), (2.6, 17.2), (2.85, 17.9), (3.2, 18.45)], 19.0)
GH_Z = [4.6, 5.0, 5.25, 5.7, 6.25, 6.85, 7.35, 7.72, 7.9, 8.0]


def build_greenhouse(P):
    bp, zone = gh_outline(*GH_BASE)
    rp, _ = gh_outline(*GH_ROOF)
    nh = len(bp)
    rcx = sum(p[1] for p in rp) / nh

    def full(pts):
        return pts + [(-u, y) for u, y in reversed(pts[1:-1])]
    bfull, rfull = full(bp), full(rp)
    zfull = zone + list(reversed(zone[1:-1]))
    n = len(bfull)
    rings = []
    for z in GH_Z:
        f = min(max((z - 5.0) / 3.0, 0.0), 1.0) ** 1.2
        rings.append([P.v((CX + (1 - f) * b[0] + f * r[0], (1 - f) * b[1] + f * r[1], z)) for b, r in zip(bfull, rfull)])
    # roof crown: two inner rings
    for s, z in ((0.82, 8.13), (0.45, 8.2)):
        rings.append([P.v((CX + s * r[0], rcx + s * (r[1] - rcx), z)) for r in rfull])
    nside = len(GH_BASE[1])
    nf = 8

    # right-half segment index for every full-loop segment
    seg_map = []
    for k in range(n):
        if k < nh - 1:
            seg_map.append(k)
        else:
            seg_map.append(n - 1 - k)  # left half: segment k mirrors right segment n-1-k
    b_lo = GH_Z.index(5.25)
    b_hi = GH_Z.index(7.72)

    def mat(i, k):
        if i >= len(GH_Z) - 1:
            return CM["paint"]
        if not (b_lo <= i < b_hi):
            return CM["pillar"] if i < b_lo else CM["paint"]
        s = seg_map[k]
        if s < nf:  # front arc
            return CM["pillar"] if s == nf - 1 else CM["glass"]
        if s < nf + nside - 1:  # side segments
            y0 = GH_BASE[1][s - nf][1]
            return CM["pillar"] if abs(y0 - 14.9) < 1e-3 else CM["glass"]
        if s == nf + nside - 1:  # first rear-arc segment: C-pillar
            return CM["pillar"]
        return CM["glass"]
    faces, c0, c1 = tube(P, rings, mat, cap0=True, cap1=True)
    if c1 is not None:
        c1.material_index = CM["paint"]
    glass = [f for f in faces if f is not None and f.material_index == CM["glass"]]
    res = bmesh.ops.inset_region(P.bm, faces=glass, thickness=0.11, depth=-0.07, use_even_offset=True)
    for f in res["faces"]:
        f.material_index = CM["trim"]


def build_wheels(P):
    prof = [(W_IN, 0.0), (W_IN, 1.4), (W_IN + 0.08, 1.68), (W_IN + 0.22, WR), (W_OUT - 0.18, WR),
            (W_OUT - 0.05, 1.68), (W_OUT, 1.42), (W_OUT - 0.04, 1.18), (W_OUT - 0.16, 1.1),
            (W_OUT - 0.22, 0.62), (W_OUT - 0.1, 0.52), (W_OUT - 0.07, 0.0)]
    sides = 16
    for yw in WHEELS:
        for s in (-1, 1):
            rings = []
            for u, r in prof:
                if r == 0:
                    rings.append([P.v((CX + s * u, yw, WR))])
                    continue
                rings.append([P.v((CX + s * u, yw + r * math.cos(2 * math.pi * k / sides),
                                   WR + r * math.sin(2 * math.pi * k / sides))) for k in range(sides)])

            def mat(i, k):
                return CM["tyre"] if i < 6 else CM["rim"]
            tube(P, rings, mat, cap0=False, cap1=False)


def frange(a, b, step):
    out, v = [], a
    while (step > 0 and v < b) or (step < 0 and v > b):
        out.append(v)
        v += step
    out.append(b)
    return out


def path_tube(P, pts, rx, rz, sides, mat):
    """A closed-ended tube along a plan path (x, y, z), its section an ellipse rx (plan) x rz (up)."""
    pts = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        t = Vector((b.x - a.x, b.y - a.y, 0)).normalized()
        side = Vector((-t.y, t.x, 0))
        rings.append([P.v(tuple(p + side * (math.cos(2 * math.pi * k / sides) * rx)
                                + Vector((0, 0, math.sin(2 * math.pi * k / sides) * rz)))) for k in range(sides)])
    tube(P, rings, mat)


def build_details(P):
    # headlights: lenses on the front wing tops along the corner diagonal (pixels (8,5)+(7,6) and mirror)
    for s in (-1, 1):
        d = Vector((s * 0.7071, 0.7071, 0))
        side = Vector((-d.y, d.x, 0))
        c = (CX + s * 3.6, 5.95, float(ZT_(5.95)) - 0.16)
        tilt = Vector((s * 0.35, -0.25, 1.0)).normalized()  # follows the wing's roll-off to the corner
        b2 = tilt.cross(d).normalized()
        a2 = b2.cross(tilt).normalized()
        ellipsoid(P, c, (a2, b2, tilt), (1.2, 0.52, 0.36), CM["lamp"], nu=14, nv=6)
        # dark bezel ring under the lens
        ellipsoid(P, Vector(c) - tilt * 0.07, (a2, b2, tilt), (1.36, 0.66, 0.33), CM["trim"], nu=14, nv=5)
    # tail lamps on the boot's rear edge (pixels (9,24) and (13,24))
    for s in (-1, 1):
        cbox(P, CX + s * 1.35, CX + s * 2.65, 24.25, 24.97, 3.7, 4.42, 0.1, CM["tail"])
    # bumpers: a rub strip wrapping the nose and the tail at bumper height
    for ys, zb in ((frange(6.6, 3.1, -0.3), 1.95), (frange(22.4, 24.85, 0.3), 1.9)):
        pts = [(CX + float(WL_(y)) - 0.1, y, zb) for y in ys]
        ye = ys[-1]
        sgn = -1 if ye < 10 else 1
        pts += [(CX + 0.5 * float(WL_(ye)), ye + sgn * 0.02, zb), (CX, ye + sgn * 0.02, zb)]
        pts += [(2 * CX - x, y, z) for x, y, z in reversed(pts[:-1])]
        path_tube(P, pts, 0.16, 0.32, 8, CM["trim"])
    # door mirrors on the door tops just behind the A-pillars
    for s in (-1, 1):
        cbox(P, CX + s * 4.3, CX + s * 5.2, 11.45, 12.0, 5.05, 5.7, 0.12, CM["paint_side"])
        cbox(P, CX + s * 4.05, CX + s * 4.5, 11.6, 11.9, 4.8, 5.25, 0.05, CM["trim"])
    # door handles (small dark slots on the doors)
    for s in (-1, 1):
        for y0 in (14.25, 17.35):
            cbox(P, CX + s * 5.38, CX + s * 5.56, y0, y0 + 0.55, 4.05, 4.28, 0.03, CM["trim"])
    # exhaust tip under the rear bumper
    cbox(P, CX + 2.4, CX + 3.2, 24.3, 25.0, 1.15, 1.75, 0.15, CM["grille"])
    # wipers resting at the windscreen base
    for u0 in (-2.7, 0.2):
        cbox(P, CX + u0, CX + u0 + 2.4, 8.78, 8.92, 5.0, 5.12, 0.03, CM["trim"])


def build_car(sprite, coll):
    mats = materials(sprite, CAR_MATS, CAR)
    body = Part("body")
    build_car_body(body)
    body_o = body.obj(coll, mats)
    for yw in WHEELS:
        for s in (-1, 1):
            cut = Part("well_cut")
            rings = []
            for u in (4.25, 8.0):
                rings.append([cut.v((CX + s * u, yw + 2.22 * math.cos(2 * math.pi * k / 24),
                                     WR + 0.05 + 2.22 * math.sin(2 * math.pi * k / 24))) for k in range(24)])
            tube(cut, rings, 0)
            co = cut.obj(coll, [mats[CM["well"]]])
            boolean(body_o, co)
            bpy.data.objects.remove(co, do_unlink=True)
    gh = Part("greenhouse")
    build_greenhouse(gh)
    gh_o = gh.obj(coll, mats)
    det = Part("detail")
    build_wheels(det)
    build_details(det)
    det_o = det.obj(coll, mats)
    bpy.context.view_layer.update()
    obj = T.join([body_o, gh_o, det_o], CAR)
    common._apply_modifiers(obj)
    me = obj.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    return obj, mats


# =====================================================================================================
# newshv-237 / newshv-235: the finned rocket (built for 237, nose LEFT; 235 is its mirror)
# =====================================================================================================
ROCKET_MATS = [
    ("body", 55, 0.5, 0.34, 0.0),
    ("joint", 52, 0.5, 0.4, 0.0),
    ("fin", 56, 0.5, 0.34, 0.0),
    ("canard", 55, 0.5, 0.36, 0.0),
    ("neck", 51, 0.55, 0.42, 0.0),
    ("strake", 1, 0.4, 0.55, 0.0),
    ("shroud", 56, 0.55, 0.3, 0.0),
    ("shroud_face", 1, 0.4, 0.55, 0.0),
    ("bore", 48, 0.3, 0.7, 0.0),
    ("light", 156, 1.0, 0.9, 1.2),
    ("light2", 152, 1.0, 0.9, 1.0),
]
RM = {n: i for i, (n, *_r) in enumerate(ROCKET_MATS)}
ROCKET_GLOW = {"light", "light2"}
YC, ZC = 13.0, 4.2  # rocket axis: between rows 12 and 13 (row edge 13), 4.2 px up

# radius along x (sprite columns): blunt ogive nose, body r 3, joint band, boat-tail to the neck
R_PROFILE = [(0.92, 0.0), (1.0, 0.95), (1.2, 1.55), (1.5, 2.05), (1.85, 2.45), (2.3, 2.8), (2.75, 2.96), (3.35, 3.0),
             (9.9, 3.0), (15.0, 3.0), (15.3, 2.85), (15.7, 2.2), (15.95, 2.05), (20.0, 2.05), (21.2, 2.2), (22.0, 2.45), (22.6, 2.6)]
R_ = pchip([p[0] for p in R_PROFILE], [p[1] for p in R_PROFILE])
R_GROOVES = (3.45, 9.95, 12.05, 15.0)
R_SIDES = 22


def rocket_stations():
    xs = [0.92, 0.96, 1.0, 1.1, 1.2, 1.35, 1.5, 1.7, 1.85, 2.05, 2.3, 2.5, 2.75, 3.05]
    x = 3.6
    while x < 22.6:
        xs.append(round(x, 3))
        x += 0.7
    xs += [15.3, 15.5, 15.7, 15.95, 20.0, 21.2, 22.0, 22.6]
    for g in R_GROOVES:
        xs += [g - 0.07, g, g + 0.07]
    xs = sorted(set(round(v, 3) for v in xs))
    out = []
    for v in xs:
        if out and v - out[-1] < 0.05:
            continue
        out.append(v)
    return out


def build_rocket_body(P):
    xs = rocket_stations()
    rings = []
    for x in xs:
        r = float(R_(x)) if x > 0.92 else 0.0
        if any(abs(x - g) < 1e-3 for g in R_GROOVES):
            r -= 0.09
        if 10.02 <= x <= 11.98:
            r -= 0.06  # the joint band sits a hair proud of nothing: a slightly slimmer collar ring
        if r <= 0:
            rings.append([P.v((x, YC, ZC))])
            continue
        rings.append([P.v((x, YC + r * math.cos(2 * math.pi * k / R_SIDES), ZC + r * math.sin(2 * math.pi * k / R_SIDES)))
                      for k in range(R_SIDES)])

    def mat(i, k):
        xm = 0.5 * (xs[i] + xs[i + 1])
        if 9.95 <= xm <= 12.05:
            return RM["joint"]
        if xm > 15.15:
            return RM["neck"]
        return RM["body"]
    tube(P, rings, mat, cap0=False, cap1=False)
    # nozzle exit: a lip turning into a dark bore that ends in a closed throat
    last = rings[-1]
    lip = [P.v((22.6, YC + 2.2 * math.cos(2 * math.pi * k / R_SIDES), ZC + 2.2 * math.sin(2 * math.pi * k / R_SIDES)))
           for k in range(R_SIDES)]
    throat = [P.v((21.3, YC + 1.4 * math.cos(2 * math.pi * k / R_SIDES), ZC + 1.4 * math.sin(2 * math.pi * k / R_SIDES)))
              for k in range(R_SIDES)]
    tip = P.v((21.1, YC, ZC))
    tube(P, [last, lip, throat, [tip]], lambda i, k: RM["neck"] if i == 0 else RM["bore"], cap0=False, cap1=False)
    # launch-rail lugs on the back
    for x0 in (5.0, 12.9):
        cbox(P, x0, x0 + 0.8, YC - 0.4, YC + 0.4, ZC + 2.75, ZC + 3.3, 0.1, RM["joint"])


def offset_poly(pts, d):
    """Inset a convex counter-clockwise polygon by d (simple miter)."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x))
        n1 = Vector((-e1.y, e1.x))
        m = (n0 + n1)
        if m.length < 1e-6:
            m = n0
        m.normalize()
        k = d / max(m.dot(n0), 0.3)
        out.append(p1 + m * k)
    return out


def plate(P, poly, z, t, mat, bevel=0.22):
    """A level plate in plan (x, y) at height z, thickness t, with chamfered (knife) edges."""
    # orient counter-clockwise
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    if area < 0:
        poly = list(reversed(poly))
    inner = offset_poly(poly, bevel)
    edge = [P.v((p[0], p[1], z)) for p in poly]
    top = [P.v((p.x, p.y, z + t / 2)) for p in inner]
    bot = [P.v((p.x, p.y, z - t / 2)) for p in inner]
    n = len(poly)
    for k in range(n):
        j = (k + 1) % n
        P.f((edge[k], edge[j], top[j], top[k]), mat)
        P.f((edge[j], edge[k], bot[k], bot[j]), mat)
    P.f(top, mat)
    P.f(list(reversed(bot)), mat)


def mirror_y(poly):
    return [(x, 2 * YC - y) for x, y in poly]


MAIN_FIN = [(10.0, 10.9), (10.0, 10.0), (10.45, 9.0), (11.2, 7.0), (12.05, 6.05), (14.9, 6.05), (16.0, 7.1), (16.0, 10.9)]
CANARD = [(3.6, 10.9), (3.6, 10.0), (4.7, 9.0), (6.3, 8.0), (8.0, 8.0), (9.0, 9.0), (9.2, 10.0), (9.2, 10.9)]


def build_rocket_fins(P):
    for poly in (MAIN_FIN, mirror_y(MAIN_FIN)):
        plate(P, poly, ZC, 0.7, RM["fin"], bevel=0.3)
    for poly in (CANARD, mirror_y(CANARD)):
        plate(P, poly, ZC, 0.55, RM["canard"], bevel=0.25)


def build_rocket_tail(P):
    # ring tail (cols 20-22): a thin-walled ring fin round the nozzle, its leading edge rolled
    prof = [(19.95, 3.45), (20.05, 3.7), (20.3, 3.95), (22.0, 3.95), (22.35, 3.55), (22.95, 2.95),
            (22.8, 2.85), (22.2, 3.25), (20.3, 3.3), (20.0, 3.35)]
    rings = [[P.v((x, YC + r * math.cos(2 * math.pi * k / 28), ZC + r * math.sin(2 * math.pi * k / 28)))
              for k in range(28)] for x, r in prof]
    rings.append(rings[0])

    def mat(i, k):
        if i >= 6 or i == 0 or i == 9:
            return RM["shroud_face"]
        return RM["shroud"]
    tube(P, rings, mat, cap0=False, cap1=False)
    # tail strakes: a dark web from the neck out to a rail at rows 9 (and 16), lights on the rails
    for s in (1, -1):
        def yy(y):
            return YC + s * (y - YC)
        y0, y1 = sorted((yy(9.55), yy(11.4)))
        cbox(P, 15.1, 21.2, y0, y1, ZC - 0.22, ZC + 0.22, 0.06, RM["strake"])
        y0, y1 = sorted((yy(9.0), yy(9.95)))
        cbox(P, 15.25, 21.2, y0, y1, ZC - 0.42, ZC + 0.42, 0.14, RM["strake"])
        ellipsoid(P, (16.5, yy(9.0), ZC + 0.36), ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (0.45, 0.9, 0.26), RM["light"])
        ellipsoid(P, (18.5, yy(9.45), ZC + 0.34), ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (0.45, 0.5, 0.3), RM["light2"])


def build_rocket(sprite, coll, name, mirror):
    mats = materials(sprite, ROCKET_MATS, name)
    P = Part(name + "_part")
    build_rocket_body(P)
    build_rocket_fins(P)
    build_rocket_tail(P)
    o = P.obj(coll, mats, mirror_x=12.0 if mirror else None)
    bpy.context.view_layer.update()
    obj = T.join([o], name)
    common._apply_modifiers(obj)
    me = obj.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    return obj, mats


# =====================================================================================================
# bake, views, measurements (scratch only)
# =====================================================================================================

def bake(obj, glow_slots, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT = (0.98, 0.98, 1.0)
    T.TEXTURED = tuple(i for i in range(len(obj.data.materials)) if i not in glow_slots)
    try:
        T.bake_maps(obj, out_dir, size=512, samples=96)
    finally:
        T.TINT, T.TEXTURED = tint, textured


def pal_grid(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(deps)
    rows = []
    for r in range(28):
        row = []
        for c in range(24):
            hit, loc, nrm, fi = ev.ray_cast(W((c + 0.5, r + 0.5, 40.0)), Vector((0, 0, -1)))
            if not hit:
                row.append(-1)
                continue
            m = obj.data.materials[obj.data.polygons[fi].material_index]
            row.append(int(m.name.split("_")[1]))
        rows.append(row)
    return rows


def cam(scene, name, loc, look, ortho=None, lens=50):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    c = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return c


def top_mask(obj, out):
    scene = bpy.context.scene
    for o in scene.objects:
        o.hide_render = o is not obj
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    K = 10
    scene.render.resolution_x, scene.render.resolution_y = 24 * K, 28 * K
    scene.render.resolution_percentage = 100
    c = cam(scene, "top_mask", (0, 0, 10), (0, 0, 0), ortho=28 / 12)
    c.rotation_euler = (0, 0, 0)
    scene.camera = c
    scene.render.filepath = str(out / "top_mask.png")
    bpy.ops.render.render(write_still=True)


def lit_views(obj, out, zc):
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o is not obj
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.16, 0.18, 0.2, 1)
    bg.inputs[1].default_value = 0.7
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(20))
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 0.8
    scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(-60), math.radians(40), 0)
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.002))
    g = bpy.context.active_object
    g.name = "ground"
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.12, 0.1, 0.07, 1)
    g.data.materials.append(gm)
    V = 400
    scene.render.resolution_x = scene.render.resolution_y = V
    d = 4.0
    tilt = math.radians(32)
    views = {
        "top": ((0, 0, d), 2.4, (0, 0, 0)),
        "side": ((d, 0, zc), 2.4, (0, 0, zc)),
        "front": ((0, d, zc), 2.4, (0, 0, zc)),
        "rear": ((0, -d, zc), 2.4, (0, 0, zc)),
        "q34": ((d * 0.6, d * 0.6, d * 0.65), None, (0, 0, zc)),
        "q34b": ((-d * 0.65, -d * 0.45, d * 0.55), None, (0, 0, zc)),
        "game": ((0, -d * math.sin(tilt), d * math.cos(tilt)), None, (0, 0, zc)),
        "under": ((d * 0.4, -d * 0.5, -d * 0.55), None, (0, 0, zc)),
    }
    for name, (loc, ortho, look) in views.items():
        g.hide_render = name in ("under",)
        c = cam(scene, f"v_{name}", loc, look, ortho=ortho, lens=55)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        scene.render.filepath = str(out / f"v_{name}.png")
        bpy.ops.render.render(write_still=True)


def main(which=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if which is None and "--model" in argv:
        which = argv[argv.index("--model") + 1]
    for w in ([which] if which else ["car", "r237", "r235"]):
        build_one(w, argv)


def build_one(which, argv):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    name = {"car": CAR, "r237": "newshv-237", "r235": "newshv-235"}[which]
    sprite = common.load_sprite(WT, name)
    coll = common.reset_collection(name)
    views = Path(argv[argv.index("--views") + 1]) / which if "--views" in argv else None
    if which == "car":
        obj, mats = build_car(sprite, coll)
        table, glow, zc = CAR_MATS, CAR_GLOW, 4.0 * PX
    else:
        obj, mats = build_rocket(sprite, coll, name, mirror=(which == "r235"))
        table, glow, zc = ROCKET_MATS, ROCKET_GLOW, ZC * PX
    glow_slots = {i for i, row in enumerate(table) if row[0] in glow}
    # outline shell from the closed model, before culling hidden faces (D90, D118)
    sh = common.outline_shell(obj, coll, voxel=0.012, faces=1800, smooth=6, inside=0.004)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{name}: {tris} triangles, shell {len(sh.data.polygons)} faces")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        sh.hide_render = True
        top_mask(obj, views)
        (views / "pal.json").write_text(json.dumps(pal_grid(obj)))
        (views / "stats.json").write_text(json.dumps({"tris": tris, "shell": len(sh.data.polygons)}))
        sh.hide_render = False
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        sh.hide_render = True
        try:
            bake(obj, glow_slots, Path(tempfile.mkdtemp(prefix="nshv163A_bake_")))
        finally:
            sh.hide_render = False
        fmt = "WEBP"
    common.export_sprite_model(WT, [obj, sh], f"enemies/{name}", sprite["sprites"], image_format=fmt)
    if views:
        sh.hide_render = True
        lit_views(obj, views, zc)


if __name__ == "__main__":
    main()
