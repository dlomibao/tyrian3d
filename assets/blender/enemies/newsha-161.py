"""Grey pod, left half (newsha.shp frame 161), a twin-nosed patrol pod.

What it is: newsha-161 and its mirror newsha-163 are always placed 24 px apart (SOH JIN events
49-52, GAUNTLET), so together they draw ONE 48x28 craft lying across the screen: a body of
revolution with a ringed hub at the seam, a light ringed barrel either side, then a cone to a nose
with a dark glass canopy on its upper (+Y) flank. It moves 1-3 px/tick against the terrain: a
free-flying craft, centred on Z = 0, closed all round. This script builds the left half (nose to
-X, hub against the right tile edge, x = +1.0 units); nose=+1 mirrors it into newsha-163.

Reading of the sprite (column/row edges of the 24x28 block; no ink border, so the model goes to the
outer edge, D74). The plan is round, centred on row edge 14:
- Cone, columns 6-14: half width 1, 2, 3, 4, 5, 6, 6, 7, 7 px: a pchip ogive through the middles
  of those steps to a fine point at 5.55, with a darker nose cap (cols 6-7, index 101) behind a
  seam ring. Index 103 (trimmed median).
- Canopy, columns 9-14, rows 8-13: dark glass (98-100, median 99) on the upper flank, its front and
  rear edges slanted (row 13 starts at col 9, row 9 at col 11; rear col 13 -> 15). A bubble patch
  over the hull in a raised bezel (102). The 108 pixel at (12, 9) is sheen, not geometry.
- Row 14, cols 7-14: the light line under the canopy: a dorsal rail (sill), index 106.
- Barrel, columns 15-20 (half width 8): a lip proud of the cone at edge 15, two light bands
  (cols 15-17, 19-20; index 107, upper half lit to 109-111 = sheen) either side of a groove (col 18,
  index 103 in the lit half).
- Collar, columns 21-22 (half width 6): a chamfered shoulder down from the barrel, a ring with a
  groove and bolts, index 104.
- Hub, column 23 (half width 5): neutral grey (palette 10; 7/10/11 alternate down the column) =
  a fluted ring. Red lamps (116, emissive) at its +Y end (row 9) and -Y end (rows 17-18).
Undersides: the same body of revolution, nothing else.

Run: blender --background --python assets/blender/enemies/newsha-161.py [-- --models newsha-163]

Exports public/models/enemies/newsha-161.glb (model + outline shell, D51/D90) with its
src/render/spriteModels entry; newsha-163.py runs this script for the mirror half. Palette indices
(the PAL table) are hull/cone 102, nose cap 101, glass 100, bezel 103, rail 104, bands 106,
groove 104, collar 102, hub 10, lamps 115.
"""

import bisect
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

NAME = "newsha-161"
PX = 1 / 12
K = 0.82  # half height / half width of every cross-section (round, a little flattened)
SIDES = 32

# Material slots and palette indices (median of each region's pixels, extremes trimmed).
HULL, NOSE, BAND, GROOVE, COLLAR, HUB, RED, GLASS, BEZEL, RAIL, BOLT = range(11)
PAL = {HULL: 102, NOSE: 101, BAND: 106, GROOVE: 104, COLLAR: 102, HUB: 10, RED: 115,
       GLASS: 100, BEZEL: 103, RAIL: 104, BOLT: 106}


def X(e):
    """Column edge -> model X (left half: nose at -X)."""
    return (e - 12) * PX


# --- Plan curve of the cone (column edge, half width px) ----------------------------------------
CONE = [(5.55, 0.0), (5.75, 0.55), (6.2, 1.0), (7.0, 1.6), (8.0, 2.5), (9.0, 3.5), (10.0, 4.5),
        (11.0, 5.45), (12.0, 6.1), (13.0, 6.6), (14.0, 7.05), (15.0, 7.4)]
cone_r = T.pchip([p[0] for p in CONE], [p[1] for p in CONE])


def r_hull(e):
    """Smooth half width of the hull under the canopy and rail (cone, then barrel)."""
    if e <= 15.0:
        return max(0.0, cone_r(e))
    return 8.0


def hull_stations():
    """(edge, half width px, material) along the axis, nose to seam."""
    st = [(5.55, 0.0, NOSE)]
    e = 5.6
    while e < 7.0:
        st.append((e, cone_r(e), NOSE))
        e += 0.15 if e < 6.2 else 0.3
    # nose-cap seam ring
    st += [(7.0, cone_r(7.0), NOSE), (7.0, cone_r(7.0) - 0.22, GROOVE), (7.22, cone_r(7.22) - 0.22, GROOVE),
           (7.22, cone_r(7.22), HULL)]
    e = 7.5
    while e < 15.0 - 1e-6:
        if 11.3 < e < 12.1:
            # panel seam ring round the cone, just behind the canopy's front
            for g, dd, m in ((11.55, 0.0, HULL), (11.55, 0.2, GROOVE), (11.75, 0.2, GROOVE), (11.75, 0.0, HULL)):
                st.append((g, cone_r(g) - dd, m))
            e = 12.1
            continue
        st.append((e, cone_r(e), HULL))
        e += 0.4
    st.append((15.0, cone_r(15.0), HULL))
    # barrel lip, band A, groove, band B
    st += [(15.0, 7.75, BAND), (15.18, 8.0, BAND), (17.85, 8.0, BAND), (18.0, 7.78, BAND),
           (18.0, 7.55, GROOVE), (18.9, 7.55, GROOVE), (18.9, 7.78, BAND), (19.05, 8.0, BAND),
           (20.82, 8.0, BAND), (21.0, 7.75, BAND),
           # shoulder down to the collar
           (21.0, 6.55, COLLAR), (21.2, 6.1, COLLAR), (21.9, 6.1, COLLAR), (21.95, 5.85, COLLAR),
           (22.15, 5.85, COLLAR), (22.2, 6.1, COLLAR), (22.85, 6.1, COLLAR), (23.0, 5.8, COLLAR),
           (23.0, 5.0, HUB)]
    return st


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, vs, mat, smooth=True):
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        face.smooth = smooth
        return face


def ring(e, r, sides=SIDES, phase=0.5, radii=None):
    pts = []
    for i in range(sides):
        a = 2 * math.pi * (i + phase) / sides
        rr = (radii[i] if radii else r) * PX
        pts.append((X(e), rr * math.cos(a), K * rr * math.sin(a)))
    return pts


def loft(M, rings, mats, cap0=True, cap1=True):
    """rings: list of point lists (or a single point); mats: material per band between rings."""
    vs = [[M.v(p) for p in rg] for rg in rings]
    for k, (a, b) in enumerate(zip(vs, vs[1:])):
        n = max(len(a), len(b))
        for i in range(n):
            j = (i + 1) % n
            if len(a) == 1:
                M.f((a[0], b[i], b[j]), mats[k])
            elif len(b) == 1:
                M.f((a[i], b[0], a[j]), mats[k])
            else:
                M.f((a[i], b[i], b[j], a[j]), mats[k])
    if cap0 and len(vs[0]) > 2:
        M.f(list(vs[0]), mats[0], smooth=False)
    if cap1 and len(vs[-1]) > 2:
        M.f(list(reversed(vs[-1])), mats[-1], smooth=False)


def build_hull(M):
    st = hull_stations()
    rings = []
    mats = []
    for k, (e, r, m) in enumerate(st):
        rings.append([(X(e), 0.0, 0.0)] if r == 0 else ring(e, r))
        if k:
            mats.append(m)
    loft(M, rings, mats, cap0=False, cap1=True)


def build_hub(M):
    """Fluted hub ring, column 23 to the seam (x edge 24): 12 ribs."""
    n = 36
    radii = [5.0 if (i % 3) != 2 else 4.6 for i in range(n)]
    radii_in = [4.5] * n
    rings = [ring(22.99, 0, n, radii=radii_in), ring(23.0, 0, n, radii=radii), ring(24.0, 0, n, radii=radii)]
    loft(M, rings, [HUB, HUB], cap0=True, cap1=True)


def surf(e, y):
    """Point on the hull's upper surface over plan (edge e, Y px) and its outward normal."""
    r = r_hull(e)
    h = 1e-3
    dr = (r_hull(e + h) - r_hull(e - h)) / (2 * h)
    zz = K * math.sqrt(max(r * r - y * y, 1e-6))
    n = Vector((-r * dr, y, zz / (K * K)))  # grad of y^2 + (z/K)^2 - r(x)^2, per px
    n.normalize()
    return Vector((X(e), y * PX, zz * PX)), n


def build_canopy(M):
    """Bubble canopy on the upper flank: a skewed rounded patch over plan x 9-15.5, Y 0.15-4.95."""
    y0, y1 = 0.15, 4.95

    def plan(u, v):
        # u in [-1, 1] across Y, v in [-1, 1] along x
        y = y0 + (u + 1) / 2 * (y1 - y0)
        xf = 8.95 + 0.5 * (y - y0)
        xr = 12.4 + 0.65 * (y - y0)
        e = xf + (v + 1) / 2 * (xr - xf)
        return e, y

    nA, nR = 32, 6
    P = 4.0

    def edge(a):
        c, s = math.cos(a), math.sin(a)
        return (math.copysign(abs(c) ** (2 / P), c), math.copysign(abs(s) ** (2 / P), s))

    def lift(rho):
        return 0.28 + 0.6 * (1 - rho * rho)

    centre = None
    rings = []
    for k in range(1, nR + 1):
        rho = k / nR
        rg = []
        for i in range(nA):
            a = 2 * math.pi * i / nA
            u, v = edge(a)
            e, y = plan(u * rho, v * rho)
            p, n = surf(e, y)
            rg.append(p + n * lift(rho) * PX)
        rings.append(rg)
    e, y = plan(0, 0)
    p, n = surf(e, y)
    centre = p + n * lift(0) * PX
    loft(M, [[tuple(centre)]] + [[tuple(q) for q in rg] for rg in rings], [GLASS] * nR, cap0=False, cap1=False)
    # Bezel: from the glass edge out and down into the hull.
    bez = []
    for rho, d in ((1.0, 0.28), (1.0, 0.48), (1.06, 0.42), (1.12, -0.4)):
        rg = []
        for i in range(nA):
            a = 2 * math.pi * i / nA
            u, v = edge(a)
            e, y = plan(u * rho, v * rho)
            p, n = surf(e, y)
            rg.append(tuple(p + n * d * PX))
        bez.append(rg)
    loft(M, bez, [BEZEL] * 3, cap0=False, cap1=False)


def build_rail(M):
    """Dorsal sill rail under the canopy, row 14 (plan Y -0.85..0.05), nose seam to the barrel lip."""
    ya, yb = -0.95, -0.05
    rings = []
    e = 7.3
    stations = []
    while e < 15.0:
        stations.append(e)
        e += 0.5
    stations.append(14.95)
    for e in stations:
        pa, na = surf(e, ya)
        pb, nb = surf(e, yb)
        rings.append([tuple(pa - na * 0.3 * PX), tuple(pa + na * 0.22 * PX),
                      tuple(pb + nb * 0.22 * PX), tuple(pb - nb * 0.3 * PX)])
    vs = [[M.v(p) for p in rg] for rg in rings]
    for a, b in zip(vs, vs[1:]):
        for i in range(3):
            M.f((a[i], b[i], b[i + 1], a[i + 1]), RAIL, smooth=False)
    M.f(list(reversed(vs[0])), RAIL, smooth=False)
    M.f(list(vs[-1]), RAIL, smooth=False)


def stud(M, centre, normal, radius, height, mat, sides=6):
    n = Vector(normal).normalized()
    ref = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
    u = n.cross(ref).normalized()
    w = n.cross(u)
    c = Vector(centre)
    base = [c - n * 0.3 * PX + radius * (math.cos(2 * math.pi * i / sides) * u + math.sin(2 * math.pi * i / sides) * w)
            for i in range(sides)]
    top = [c + n * height + 0.8 * radius * (math.cos(2 * math.pi * i / sides) * u + math.sin(2 * math.pi * i / sides) * w)
           for i in range(sides)]
    vb = [M.v(p) for p in base]
    vt = [M.v(p) for p in top]
    for i in range(sides):
        j = (i + 1) % sides
        M.f((vb[i], vb[j], vt[j], vt[i]), mat, smooth=False)
    M.f(list(vt), mat, smooth=False)


def build_bolts(M):
    """Six bolts round the collar ring's upper half (column 21.55)."""
    for deg in (-75, -45, -15, 15, 45, 75):
        a = math.radians(90 + deg)
        r = 6.1
        p = Vector((X(21.55), r * math.cos(a) * PX, K * r * math.sin(a) * PX))
        n = Vector((0, math.cos(a), math.sin(a) / K)).normalized()
        stud(M, p, n, 0.32 * PX, 0.18 * PX, BOLT)


def build_lamps(M):
    """Red marker lamps on the hub: +Y end (row 9) and -Y end (rows 17-18), a lens in a housing."""
    for y_plan in (4.45, -4.3):
        r = 5.0
        z = K * math.sqrt(r * r - y_plan * y_plan)
        a = math.atan2(z / K, y_plan)
        p = Vector((X(23.5), y_plan * PX, z * PX))
        n = Vector((0, math.cos(a), math.sin(a) / K)).normalized()
        # housing (hub grey) and lens dome (red)
        stud(M, p, n, 0.75 * PX, 0.2 * PX, HUB, sides=8)
        c = p + n * 0.2 * PX
        ref = Vector((1, 0, 0))
        u = n.cross(ref).normalized()
        w = n.cross(u)
        rings = []
        for t, s in ((0.0, 0.6), (0.22, 0.55), (0.42, 0.32)):
            rings.append([tuple(c + n * t * PX + s * PX * (math.cos(2 * math.pi * i / 8) * u + math.sin(2 * math.pi * i / 8) * w))
                          for i in range(8)])
        rings.append([tuple(c + n * 0.5 * PX)])
        loft(M, rings, [RED] * 3, cap0=True, cap1=False)


def materials(sprite, tag):
    spec = {HULL: (0.35, 0.42), NOSE: (0.4, 0.45), BAND: (0.4, 0.36), GROOVE: (0.35, 0.55),
            COLLAR: (0.4, 0.42), HUB: (0.5, 0.35), RED: (0.2, 0.35), GLASS: (0.3, 0.08),
            BEZEL: (0.55, 0.45), RAIL: (0.55, 0.35), BOLT: (0.6, 0.4)}
    sub = {HULL: "hull", NOSE: "nose", BAND: "band", GROOVE: "groove", COLLAR: "collar", HUB: "hub",
           RED: "lamp", GLASS: "glass", BEZEL: "bezel", RAIL: "rail", BOLT: "bolt"}
    out = []
    for slot in range(11):
        m, r = spec[slot]
        out.append(common.palette_material(sprite, PAL[slot], f"{tag}_{sub[slot]}", metallic=m, roughness=r,
                                           emission_strength=1.5 if slot == RED else 0.0))
    return out


def build(sprite, coll, nose=-1, name=NAME):
    M = Mesh()
    build_hull(M)
    build_hub(M)
    build_canopy(M)
    build_rail(M)
    build_bolts(M)
    build_lamps(M)
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    if nose > 0:
        for v in bm.verts:
            v.co.x = -v.co.x
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    tag = name
    me = bpy.data.meshes.new(tag)
    bm.to_mesh(me)
    bm.free()
    for m in materials(sprite, tag):
        me.materials.append(m)
    obj = bpy.data.objects.new(tag, me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(35))
    return obj


def build_model(sprite, name, nose):
    coll = common.reset_collection(name)
    obj = build(sprite, coll, nose=nose, name=name)
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{name}: {tris} triangles")
    bpy.context.view_layer.update()
    sh = common.outline_shell(sealed, coll, voxel=0.03, faces=1500, smooth=6, inside=0.004)
    sh.name = f"{name}_outline"
    bpy.data.objects.remove(sealed, do_unlink=True)
    return [obj, sh]


def main(only=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if only is None and "--models" in argv:
        only = argv[argv.index("--models") + 1]
    for name, nose in (("newsha-161", -1), ("newsha-163", 1)):
        if only and name != only:
            continue
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        sprite = common.load_sprite(WT, name)
        objs = build_model(sprite, name, nose)
        common.export_sprite_model(WT, objs, f"enemies/{name}", sprite["sprites"])


if __name__ == "__main__":
    main(only=NAME)
