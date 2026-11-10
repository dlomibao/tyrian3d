"""Grey swept-wing fighter (newshf.shp frame 11, 24x28 block, one frame): a 3D version of its sprite.

Seen in episodes 1, 3 and 4.

Reading of the sprite (light from the upper left; it flies nose DOWN the screen, so row 25 is the
nose and the top of the picture the tail). Centre line: column 12 (pixel centre, x edge 12.5).
- A round fuselage: half width 1.5 px from the tail (row 2) to row 8, 2.5 px from row 9 (wing
  roots) to row 22, then a nose cone to a point at row 26. The bright pair of columns 11-12 down
  rows 9-14 is the sheen on its round top; a darker band across it at row 13 is a panel seam; the
  flat run of 7s across row 15 is the canopy's rear frame; the dark pixel at (12, 20) is the joint
  of a darker nose cone (region median 6 against the body's 7).
- Canopy: the dark slot (columns 11-13, rows 16-19, index 1) with a bright pixel on its centre line
  (12, 17) = glass with its glint; the 6s above and below the glint = a centre frame bow.
- Wings swept back 45 degrees to tips beside the tail: outer edge column 3 (rows 6-8), trailing
  edge a 45-degree line from the tip (row 6) to the root (row 10), leading edge a 2:1 line from the
  tip (row 9) to the nose (row 20). The lit diagonal 9-10 line about 1.5 px inside the leading edge
  is a crease: the crest of a faceted wing section, not paint.
- Dark pixels at the wing roots behind the wing (columns 9 and 15, rows 9-12) = a recess: a vent
  grille on each wing root.
- Guns (columns 8 and 16, rows 16-18, a lit 12 on top) = short cannon barrels in fairings on the
  wing roots, the muzzle just past the leading edge.
- A small tailplane (rows 3-5, columns 8-16, trailing edge row 3) and an upright fin along the
  centre line (column 12, rows 1-8, its right side in shadow: the 1s of column 13), its tip
  overhanging the tail (rows 1-2): a swept fin with a tip fairing.
Colours (region medians, darkest/brightest fifth left out): body 7, nose cone 6, wings 7, tailplane
and fin 8, guns 8, canopy glass 1 with a frame of 6, vent and nozzle recesses 4, bores 1.
Underside: closed, no detail.

    blender --background --python assets/blender/enemies/newshf-11.py [-- --no-bake]

Exports public/models/enemies/newshf-11.glb (objects newshf-11 + newshf-11_outline) and its
src/render/spriteModels entry. No concept projection bake: AO/roughness bake only (D50-D53, D65).
Coordinates while building: sprite px, x = column edge - 12.5 (the centre line), y = row edge
(down), z up; shifted by CX to the block's centre, then usp_talon.finish
(X = x / 12, Y = (14 - y) / 12, Z = z / 12).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
WT = HERE.parent.parent.parent
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, hull, pchip, plate  # noqa: E402

NAME = "newshf-11"
PX = 1 / 12
CX = 0.5  # the centre line (column edge 12.5) from the block's centre (12)

(BODY, NOSE, WING, TAIL, GLASS, FRAME, GUN, DARK, VOID) = range(9)
PAL_OF = {BODY: 7, NOSE: 6, WING: 7, TAIL: 8, GLASS: 1, FRAME: 6, GUN: 8, DARK: 4, VOID: 1}
TEXTURED = (BODY, NOSE, WING, TAIL, FRAME, GUN, DARK)


def materials(sprite):
    def pal(slot, tag, metallic, roughness):
        return common.palette_material(sprite, PAL_OF[slot], f"{NAME}_{tag}", metallic=metallic,
                                       roughness=roughness)
    return [
        pal(BODY, "body", 0.4, 0.4),
        pal(NOSE, "nose", 0.35, 0.44),
        pal(WING, "wing", 0.4, 0.42),
        pal(TAIL, "tail", 0.4, 0.4),
        pal(GLASS, "glass", 0.0, 0.07),
        pal(FRAME, "frame", 0.4, 0.38),
        pal(GUN, "gun", 0.45, 0.36),
        pal(DARK, "recess", 0.2, 0.7),
        pal(VOID, "bore", 0.0, 0.9),
    ]


# --- fuselage -------------------------------------------------------------------------------------

FW = pchip([1.95, 2.3, 3.0, 8.75, 9.15, 9.6, 10.5, 20.3, 21.5, 22.6, 23.4, 24.3, 25.0, 25.55, 25.95],
           [1.15, 1.45, 1.5, 1.5, 2.15, 2.45, 2.55, 2.55, 2.45, 2.15, 1.75, 1.45, 1.05, 0.6, 0.08])
FZ = pchip([1.95, 9.0, 15.0, 21.0, 24.0, 25.95], [0.55, 0.45, 0.45, 0.35, 0.2, 0.05])
NF = 16


def fus_loop(y, grow=0.0):
    """16 points round the fuselage: 0 top centre, 4 right, 8 keel, 12 left. Round (the sprite's
    sheen says so), a little flatter underneath."""
    w = FW(y) + grow
    zc = FZ(y)
    ht, hb = FW(y) * 0.95 + grow, FW(y) * 0.8 + grow
    pts = []
    for k in range(NF):
        a = math.pi / 2 - 2 * math.pi * k / NF
        s = math.sin(a)
        pts.append((w * math.cos(a), zc + (ht if s > 0 else hb) * s))
    return pts, (0.0, zc)


def fus_top(x, y):
    w = FW(y)
    t = min(1.0, abs(x) / max(w, 1e-6))
    return FZ(y) + FW(y) * 0.95 * math.sqrt(max(0.0, 1 - t * t))


def ring_loft(P, rings, mats, cap0=True, cap1=True, cap_out=None):
    """rings: [(points [(x,y,z)], centre (x,y,z))]; mats[i] between ring i and i+1."""
    vs = [([P.v(p) for p in pts], c) for pts, c in rings]
    for i, ((r0, c0), (r1, c1)) in enumerate(zip(vs, vs[1:])):
        n = len(r0)
        cen = tuple((Vector(c0) + Vector(c1)) / 2)
        step = abs(c0[1] - c1[1]) < 1e-6 and abs(rings[i][0][0][1] - rings[i + 1][0][0][1]) < 1e-6
        if step:  # a groove wall: faces +y when the later ring is the smaller
            size = [sum((Vector(p) - Vector(c)).length for p in pts) for pts, c in (rings[i], rings[i + 1])]
            out = (0, 1 if size[1] < size[0] else -1, 0)
        for a in range(n):
            b = (a + 1) % n
            if step:
                P.f((r0[a], r0[b], r1[b], r1[a]), mats[i], out=out)
            else:
                P.f((r0[a], r0[b], r1[b], r1[a]), mats[i], away=cen)
    o0, o1 = cap_out if cap_out else ((0, -1, 0), (0, 1, 0))
    if cap0:
        P.f(vs[0][0], mats[0], out=o0)
    if cap1:
        P.f(vs[-1][0], mats[-1], out=o1)


SEAMS = [(4.4, BODY), (8.9, BODY), (13.5, BODY), (20.25, NOSE)]  # (row, material after it)
GW, GD = 0.11, 0.13  # seam half width and depth


def build_fuselage(P, D):
    ys = [2.3, 2.7, 3.4, 4.4, 5.6, 7.0, 8.1, 8.55, 8.9, 9.15, 9.4, 9.8, 10.5, 11.6, 12.6, 13.5, 14.5, 15.5, 16.5,
          17.6, 18.7, 19.6, 20.25, 21.0, 21.8, 22.6, 23.4, 24.1, 24.7, 25.15, 25.5, 25.75, 25.9]
    rings, mats = [], []
    mat = BODY
    seams = dict(SEAMS)
    for y in ys:
        if y in seams:
            for yy, g in ((y - GW, 0.0), (y - GW, -GD), (y + GW, -GD), (y + GW, 0.0)):
                pts, (cx, cz) = fus_loop(yy, g)
                rings.append(([(x, yy, z) for x, z in pts], (cx, yy, cz)))
                mats.append(mat)
            mat = seams[y]
            mats[-1] = mat
            continue
        pts, (cx, cz) = fus_loop(y)
        rings.append(([(x, y, z) for x, z in pts], (cx, y, cz)))
        mats.append(mat)
    ring_loft(P, rings, mats[:-1] if len(mats) == len(rings) else mats)
    # Dorsal spine plates either side of the seam at row 13.5 (the sheen catches their edges).
    plate(D, fus_loop, 9.55, 13.3, BODY, -1.0, 1.0, d=0.14, c=0.08, depth=0.3, ystep=0.8)
    plate(D, fus_loop, 13.7, 15.05, BODY, -1.0, 1.0, d=0.14, c=0.08, depth=0.3, ystep=0.7)
    # Canopy's rear frame hoop (row 15's flat run of 7s).
    plate(D, fus_loop, 15.15, 15.65, BODY, -3.2, 3.2, d=0.2, c=0.07, depth=0.3, ystep=0.5)


def lathe(P, cx, cz, prof, n=16, sign=1):
    """Revolve [(y, r, mat)] about the line x=cx, z=cz (along y); each band takes its first station's
    material; r = 0 makes a point. `sign` +1 when the profile runs toward +y along its outside
    (outward normal (-dr, dy) in the (y, r) plane), -1 when it runs toward -y."""
    rows = []
    for y, r, _m in prof:
        if r < 1e-6:
            rows.append([P.v((cx, y, cz))])
        else:
            rows.append([P.v((cx + r * math.cos(2 * math.pi * (k + 0.5) / n), y,
                              cz + r * math.sin(2 * math.pi * (k + 0.5) / n))) for k in range(n)])
    for i in range(len(rows) - 1):
        (y0, r0, m), (y1, r1, _m) = prof[i], prof[i + 1]
        ny, nr = sign * -(r1 - r0), sign * (y1 - y0)
        A, B = rows[i], rows[i + 1]
        for a in range(n):
            b = (a + 1) % n
            ang = 2 * math.pi * (a + 1) / n
            out = (nr * math.cos(ang), ny, nr * math.sin(ang))
            if len(A) == 1:
                P.f((A[0], B[b], B[a]), m, out=out)
            elif len(B) == 1:
                P.f((A[a], A[b], B[0]), m, out=out)
            else:
                P.f((A[a], A[b], B[b], B[a]), m, out=out)
    return rows


def build_nozzle(D):
    """The engine nozzle at the tail (row 2): a shroud, its lip, a dark bore and a darker back."""
    prof = [(2.9, 1.42, FRAME), (1.98, 1.22, FRAME), (1.98, 0.86, DARK), (2.45, 0.82, VOID), (2.45, 0.0, VOID)]
    lathe(D, 0.0, FZ(2.3), prof, sign=-1)


# --- canopy ---------------------------------------------------------------------------------------

CGW = pchip([15.7, 16.2, 17.5, 19.0, 19.6, 19.95], [0.85, 1.22, 1.32, 1.18, 0.85, 0.35])
CRISE = pchip([15.7, 16.4, 18.0, 19.3, 19.95], [0.3, 0.72, 0.8, 0.5, 0.08])


def glass_top(y):
    return fus_top(0.0, y) + CRISE(y)


def build_canopy(D):
    pts = []
    n = 10
    for y in [15.7, 16.0, 16.5, 17.2, 18.0, 18.8, 19.4, 19.75, 19.95]:
        w = CGW(y)
        base = fus_top(w, y) - 0.25
        top = glass_top(y)
        for k in range(n + 1):
            t = math.pi * k / n
            x = w * math.cos(t)
            pts.append((x, y, base + (top - base) * math.sin(t) ** 0.55))
    hull(D, pts, GLASS)
    # Centre frame bow along the glass (the 6s either side of the glint at (12, 17)).
    st = [15.75, 16.6, 17.5, 18.4, 19.2, 19.85]
    for y0, y1 in zip(st, st[1:]):
        bp = []
        for y in (y0, y1):
            z = glass_top(y)
            for x in (-0.17, 0.17):
                bp += [(x, y, z - 0.15), (x * 0.6, y, z + 0.07)]
        hull(D, bp, FRAME)
    # Windscreen arch where the glass meets the nose (row 19.9).
    ap = []
    for k in range(9):
        t = math.pi * k / 8
        w = CGW(19.85) + 0.15
        x = w * math.cos(t)
        z = fus_top(x, 19.9) + (glass_top(19.85) - fus_top(0, 19.9)) * math.sin(t) ** 0.6
        for y in (19.75, 20.05):
            ap += [(x, y, z + 0.08), (x * 0.9, y, z - 0.2)]
    hull(D, ap, FRAME)


# --- wings ----------------------------------------------------------------------------------------

LE = pchip([1.8, 2.0, 2.5, 3.0, 4.0, 9.0, 9.3, 9.5], [21.3, 21.0, 20.55, 20.1, 19.0, 9.0, 8.75, 8.45])
TE = pchip([1.8, 3.0, 3.8, 4.45, 5.0, 8.25, 9.25, 9.5], [10.3, 10.15, 9.98, 9.8, 9.25, 6.0, 6.0, 6.3])
WTH = pchip([1.8, 4.0, 7.0, 9.0, 9.35, 9.5], [0.85, 0.68, 0.48, 0.34, 0.26, 0.16])


def wing_z0(u):
    return 0.02 + 0.03 * (u - 2.0)


def wing_section(u, le, te, th, z0, flap=True):
    """(y, z) loop of a faceted wing section at span u: leading edge, a 45-percent crest (the
    sprite's lit crease), a flap seam 80 percent back, a thin trailing edge; flatter underneath."""
    c = le - te

    def y(f):
        return le - f * c
    up = [(0.0, 0.05), (0.07, 0.5), (0.42, 1.0), (0.66, 0.8)]
    if flap:
        up += [(0.78, 0.6), (0.80, 0.6 - 0.12 / max(th, 0.12)), (0.82, 0.55)]
    up += [(1.0, 0.12 / max(th, 0.12) * 0.5)]
    lo = [(1.0, -0.05), (0.5, -0.55), (0.1, -0.32), (0.02, -0.08)]
    pts = [(y(f), z0 + k * th) for f, k in up] + [(y(f), z0 + k * th) for f, k in lo]
    return pts


def build_wing(W, s, stations, le, te, th, z0f, mat, flap=True):
    rings = []
    for u in stations:
        sec = wing_section(u, le(u), te(u), th(u), z0f(u), flap)
        cy = (le(u) + te(u)) / 2
        rings.append(([(s * u, yy, zz) for yy, zz in sec], (s * u, cy, z0f(u))))
    ring_loft(W, rings, [mat] * (len(rings) - 1), cap_out=((-s, 0, 0), (s, 0, 0)))


WING_U = [1.8, 2.4, 3.0, 3.6, 4.3, 5.0, 5.7, 6.4, 7.1, 7.8, 8.25, 8.7, 9.0, 9.2, 9.35, 9.5]
TLE = pchip([0.8, 1.5, 2.0, 3.0, 4.0, 4.3, 4.5], [8.6, 7.55, 7.0, 6.0, 5.0, 4.82, 4.55])
TTE = pchip([0.8, 4.2, 4.5], [3.05, 3.05, 3.25])
TTH = pchip([0.8, 2.5, 4.5], [0.3, 0.24, 0.14])
TAIL_U = [0.8, 1.4, 2.0, 2.6, 3.2, 3.8, 4.2, 4.38, 4.5]


def build_guns(D, s):
    """A cannon on each wing root (columns 8 / 16): a fairing, the barrel and a muzzle ring."""
    x = s * 4.0

    prof = [(12.3, 0.0, GUN), (12.8, 0.42, GUN), (13.6, 0.52, GUN), (16.1, 0.52, GUN), (16.6, 0.36, GUN),
            (16.6, 0.27, GUN), (18.55, 0.27, GUN), (18.55, 0.34, GUN), (19.1, 0.34, GUN), (19.1, 0.17, VOID),
            (18.8, 0.17, VOID), (18.8, 0.0, VOID)]
    lathe(D, x, 0.42, prof, n=10, sign=1)
    # A strap clamping the barrel to its fairing.
    hull(D, T.cbox(x - 0.62, x + 0.62, 14.5, 14.95, 0.42 - 0.62, 0.42 + 0.62, 0.15), FRAME)


def build_vent(D, s):
    """The dark recess behind each wing root (columns 9 / 15, rows 10-12): a grille in a raised lip."""
    x0, x1, y0, y1 = 2.45, 3.6, 10.25, 12.6
    z = 0.62

    def X(a, b):
        return tuple(sorted((s * a, s * b)))
    for a, b, c, d in ((x0, x1, y0, y0 + 0.28), (x0, x1, y1 - 0.28, y1), (x1 - 0.25, x1, y0, y1)):
        hull(D, T.cbox(*X(a, b), c, d, -0.1, z + 0.12, 0.07), FRAME)
    hull(D, T.cbox(*X(x0, x1 - 0.2), y0 + 0.2, y1 - 0.2, -0.1, z - 0.1, 0.04), DARK)
    for yy in (10.95, 11.6, 12.2):
        hull(D, T.cbox(*X(x0 + 0.05, x1 - 0.22), yy - 0.08, yy + 0.08, z - 0.3, z + 0.02, 0.03), FRAME)


def build_fin(D):
    """Upright swept fin on the centre line (column 12, rows 1-8) with a tip fairing."""
    root_le, root_te = (9.3, fus_top(0, 9.3) - 0.35), (2.35, fus_top(0, 2.35) - 0.3)
    tip_le, tip_te = (3.7, 5.2), (1.2, 5.2)
    pts = []
    for (yl, zl), (yt, zt), half in ((root_le, root_te, 0.36), (tip_le, tip_te, 0.2)):
        c = yl - yt
        for f, w in ((0.0, 0.08), (0.35, 1.0), (0.75, 0.75), (1.0, 0.1)):
            y = yl - f * c
            z = zl + (zt - zl) * f
            pts += [(-half * w, y, z), (half * w, y, z)]
    hull(D, pts, TAIL)
    # Tip fairing: a slim pod along the fin's top, pointed aft.
    prof = [(4.3, 0.0), (3.8, 0.26), (3.1, 0.4), (1.6, 0.4), (1.2, 0.3), (1.03, 0.12)]
    pp = []
    for y, r in prof:
        if r == 0.0:
            pp.append((0.0, y, 5.2))
            continue
        for k in range(8):
            a = 2 * math.pi * (k + 0.5) / 8
            pp.append((r * math.cos(a), y, 5.2 + r * math.sin(a) * 0.9))
    hull(D, pp, TAIL)


# --- assembly -------------------------------------------------------------------------------------

def shifted(part):
    for v in part.bm.verts:
        v.co.x += CX
    return part


def build(coll, sprite):
    mats = materials(sprite)
    P = Part(f"{NAME}_core", smooth_angle=35)
    D = Part(f"{NAME}_detail", smooth_angle=35)
    Wp = Part(f"{NAME}_wings", smooth_angle=12)
    build_fuselage(P, D)
    build_nozzle(D)
    build_canopy(D)
    build_fin(D)
    for s in (-1, 1):
        build_wing(Wp, s, WING_U, LE, TE, WTH, wing_z0, WING)
        build_wing(Wp, s, TAIL_U, TLE, TTE, TTH, lambda u: 0.55, TAIL, flap=False)
        build_guns(D, s)
        build_vent(D, s)
    objs = [T.finish(shifted(p), mats, coll) for p in (P, D, Wp)]
    obj = T.join(objs, NAME)
    if "--no-recalc" not in sys.argv:  # hull/plate hints leave a few faces inward (fin): 128 back hits -> 0
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
    return obj, mats


def back_hits(obj):
    """How many first hits of rays from above / the sides / the front land on a face pointing away
    (an inward face): should be 0."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    tree = BVHTree.FromBMesh(bm)
    bm.faces.ensure_lookup_table()
    bad = tot = 0
    where = {}
    for d in (Vector((0, 0, -1)), Vector((1, 0, -0.6)), Vector((-1, 0, -0.6)), Vector((0, 1, -0.6)),
              Vector((0, -1, -0.6)), Vector((0, 0, 1))):
        d.normalize()
        for i in range(60):
            for j in range(60):
                a, b = -1.2 + 2.4 * i / 59, -1.4 + 2.8 * j / 59
                o = Vector((a, b, 0)) - d * 3 if abs(d.z) > 0.99 else Vector((a, b, 0.05)) - d * 3
                loc, n, _i, _dist = tree.ray_cast(o, d)
                if loc is not None:
                    tot += 1
                    if n.dot(d) > 0:
                        bad += 1
                        f = bm.faces[_i]
                        key = (f.material_index, round(loc.y * 12), round(loc.x * 12))
                        where[key] = where.get(key, 0) + 1
    bm.free()
    return bad, tot, sorted(where.items(), key=lambda kv: -kv[1])[:25]


def outline_shell_parts(obj, coll, voxel=0.01, faces=1500, smooth=4, inside=0.004, min_verts=120, target=None):
    """Copied from assets/blender/enemies/newshf-1.py (candidate for common.outline_shell(keep="outer")):
    common.outline_shell keeping every outer island, held `inside` the model (Shrinkwrap, D88)."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{(target or obj).name}_outline", me)
    coll.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    rm.use_smooth_shade = True
    common._apply_modifiers(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bm.verts.ensure_lookup_table()
    seen, islands = set(), []
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
    islands.sort(key=len, reverse=True)
    islands = [i for i in islands if len(i) >= min_verts]
    trees = []
    for isl in islands:
        ids = {v.index for v in isl}
        fs = {f for v in isl for f in v.link_faces}
        verts = [v.co.copy() for v in isl]
        remap = {v.index: k for k, v in enumerate(isl)}
        polys = [[remap[v.index] for v in f.verts] for f in fs if all(v.index in ids for v in f.verts)]
        trees.append(BVHTree.FromPolygons(verts, polys))

    def inside_of(p, tree):
        hits, o, d = 0, p.copy(), Vector((0.137, 0.291, 0.947)).normalized()
        for _ in range(64):
            loc, _n, _i, _dist = tree.ray_cast(o, d)
            if loc is None:
                break
            hits += 1
            o = loc + d * 1e-5
        return hits % 2 == 1

    keep = set()
    for k, isl in enumerate(islands):
        sample = isl[:: max(1, len(isl) // 24)]
        buried = any(sum(inside_of(v.co, trees[j]) for v in sample) > 0.6 * len(sample) for j in range(k))
        if not buried:
            keep.update(v.index for v in isl)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
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
    if inside > 0:
        sw = shell.modifiers.new("inside", "SHRINKWRAP")
        sw.target = target or obj
        sw.wrap_method = "NEAREST_SURFACEPOINT"
        sw.wrap_mode = "INSIDE"
        sw.offset = inside
        common._apply_modifiers(shell)
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    body, _mats = build(coll, sprite)
    print("BACKHITS", back_hits(body))
    src = body.copy()
    src.data = body.data.copy()
    src.name = f"{NAME}_shellsrc"
    coll.objects.link(src)
    T.cull_hidden(body)
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        bake_dir = Path(tempfile.mkdtemp(prefix="newshf11_bake_"))
        tint, textured = T.TINT, T.TEXTURED
        T.TINT, T.TEXTURED = (1.0, 1.0, 1.0), TEXTURED
        try:
            T.bake_maps(body, bake_dir, size=512, samples=48)
        finally:
            T.TINT, T.TEXTURED = tint, textured
        for img in bpy.data.images:
            if img.name in ("talon_colour", "talon_rm"):
                img.name = img.name.replace("talon", NAME)
        fmt = "WEBP"
    shell = outline_shell_parts(src, coll, voxel=0.01, faces=1500, smooth=4, inside=0.005, target=body)
    bpy.data.objects.remove(src)
    shell.name = f"{NAME}_outline"
    print(f"{NAME}: triangles {tris} (shell excluded)")
    common.export_sprite_model(WT, [body, shell], f"enemies/{NAME}", sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
