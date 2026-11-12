"""Brown horned bowl (newshh.shp size 2, frame 93), a D65 hard-surface flyer.

WHAT IT IS: a free-flying bronze craft shaped like a horned bowl (a Chinese sycee ingot read as a
machine). Type 424, mv 0, armour 10, no fire; in GYGES (2.2) it comes in columns of five that sway
like a snake. It flies: a round, closed belly under it, nothing standing on the ground.

Reading of the sprite (24x28; pixel (c, r) covers [c, c+1] x [r, r+1]; ink ring all round):
- Front wall (rows 13-19): the bowl's outer wall sloping down toward the player, two facets meeting
  in a ridge down column 12 (lit left half 22-25, shaded right half 17-20: lighting, not paint).
  Built as a gabled glacis on a lofted hull, the ridge a raised strip (24).
- Rim (rows 11-12): a pale rolled lip across the bowl (24-31 on its lit left, 21-23 right): a
  flattened tube, palette 24.
- Dome (rows 6-10, cols 8-16): sits in the bowl behind the rim, its top-left sheen (30/31) is
  lighting; palette 22, with a dark collar (19) where the sprite's row 10 shadow is.
- Horns (cols 2-5 / 19-22, rows 5-11): the bowl's ends curling up and back, palette 22.
- Bowl wings (rows 8-11 beside the dome): the inner slopes rising to the horns, palette 21.
Medians (16-18 shading and 29-31 sheen left out): front wall 21, ridge 24, rim 24 (the pale band
cols 6-17), dome 22, horns 22, wings 21; dark well 19; belly 20 (unseen from above).

Coordinates while building: sprite px, x = column edge - 12.5 (the symmetry axis: column 12's
centre), y = row edge (down the sprite = toward the front), z up. To Blender: X = (x + 0.5) / 12,
Y = (14 - y) / 12, Z = z / 12 (the same placement as lib_b018.px / row).

  Blender -b -P assets/blender/enemies/newshh-93.py -- [--views DIR] [--no-bake]
Exports public/models/enemies/newshh-93.glb and src/render/spriteModels/newshh-93.json.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path("/Users/dlomibao/projects/tyrian-scratch/e2-enemies-1/newshh-93/final")
NAME = "newshh-93"
TAG = "nshh93A"
PX = 1 / 12
W, H = 24, 28

# palette index -> (metallic, roughness); satin metal (D53)
PROPS = {19: (0.25, 0.6), 20: (0.28, 0.55), 21: (0.32, 0.45), 22: (0.34, 0.4), 24: (0.36, 0.36)}
DARK, BELLY, WALL, DOME, TRIM = 19, 20, 21, 22, 24

pchip = T.pchip


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# --- plan and heights --------------------------------------------------------------------------------

# Hull half width per row edge y (inner edge of the ink ring, D74), smooth through the steps.
HW = pchip([6.3, 6.6, 7.0, 7.5, 8.0, 8.45, 8.75, 9.05, 9.4, 12.3, 12.75, 13.3, 14.6, 16.0, 17.2, 18.2, 18.9, 19.5, 19.85, 20.05],
           [0.8, 1.9, 2.9, 3.7, 4.4, 4.9, 7.2, 9.35, 9.5, 9.5, 9.2, 8.7, 8.5, 8.0, 7.45, 6.8, 6.1, 5.2, 4.2, 2.8])
# Ridge height down the front wall (the bowl's outer wall, steepening toward its foot).
ZR = pchip([12.4, 13.5, 15.0, 16.5, 17.8, 18.9, 19.6, 20.05], [5.15, 4.95, 4.5, 3.85, 3.0, 2.15, 1.45, 0.9])
# Belly depth below the waist, and the waist height.
BD = pchip([6.3, 6.6, 8.0, 10.0, 15.0, 18.5, 19.6, 20.05], [0.9, 1.9, 2.6, 3.0, 3.0, 2.5, 1.7, 0.9])
ZW = 0.7

# Top profile samples across a section, as a = |x| / hw.
A_TOP = [0.0, 0.1, 0.22, 0.34, 0.46, 0.58, 0.68, 0.76, 0.83, 0.89, 0.94, 0.975, 1.0]
A_BEL = [0.96, 0.86, 0.7, 0.5, 0.26, 0.0]


def top_raw(a, y):
    """Height of the hull top at a = |x| / hw before the edge roll."""
    hw = HW(y)
    front = ZR(max(y, 12.4)) - 1.8 * a * min(1.0, hw / 9.0) * (0.3 + 0.7 * smoothstep(12.3, 13.8, y))          # gabled glacis
    bowl = 3.6 + 2.6 * smoothstep(0.3, 0.9, a) * (0.25 + 0.75 * smoothstep(8.7, 10.2, y))                       # well + wings rising to the horns
    stern = 3.4 - 0.6 * a * a                                         # deck under the dome
    wb = smoothstep(8.5, 9.1, y)
    wf = smoothstep(11.5, 12.5, y)
    return stern * (1 - wb) + bowl * wb * (1 - wf) + front * wf


def a_roll(y):
    return 0.82 - 0.06 * smoothstep(12.0, 13.0, y)


def top_z(a, y):
    a0 = a_roll(y)
    if a <= a0:
        return top_raw(a, y)
    h0 = top_raw(a0, y)
    t = (a - a0) / (1 - a0)
    base = ZW + 0.35
    return base + (h0 - base) * math.sqrt(max(0.0, 1 - t * t))


def section(y, grow=0.0):
    """Closed loop (x, z), anticlockwise seen from +y: top from x=-hw to +hw, belly back."""
    hw = HW(y) + grow
    bd = BD(y)
    pts = []
    for a in [-v for v in reversed(A_TOP[1:])] + A_TOP:
        pts.append((a * hw, top_z(abs(a), y) + grow))
    for a in A_BEL:
        pts.append((a * hw, ZW - bd * math.sqrt(max(0.0, 1 - a ** 2.2))))
    for a in reversed(A_BEL[:-1]):
        pts.append((-a * hw, ZW - bd * math.sqrt(max(0.0, 1 - a ** 2.2))))
    return pts


NT = 2 * len(A_TOP) - 1  # top points (indices 0..NT-1)


# --- mesh helpers --------------------------------------------------------------------------------------

class Mesh:
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.pal = self.bm.faces.layers.int.new("pal")

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, vs, pal):
        if len({id(v) for v in vs}) < 3:
            return None
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face[self.pal] = pal
        return face


def loft(m, rings, palf, cap0=True, cap1=True, cap_pal=None):
    """rings: [(y, [(x, z)...])] same counts; palf(i_ring, j_seg) -> pal."""
    vr = [[m.v((x, y, z)) for x, z in pts] for y, pts in rings]
    n = len(vr[0])
    for i in range(len(vr) - 1):
        for j in range(n):
            k = (j + 1) % n
            m.f((vr[i][j], vr[i][k], vr[i + 1][k], vr[i + 1][j]), palf(i, j))
    if cap0:
        m.f(vr[0], cap_pal if cap_pal is not None else palf(0, 0))
    if cap1:
        m.f(vr[-1], cap_pal if cap_pal is not None else palf(len(vr) - 2, 0))
    return vr


def sweep(m, path, radii, pal, sides=12, up=(0, 0, 1), caps=True, start_angle=0.0):
    """A tube along path [(x,y,z)], radii [(ra, rb)] (ra across, rb toward `up`)."""
    path = [Vector(p) for p in path]
    upv = Vector(up)
    rings = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        side = t.cross(upv)
        if side.length < 1e-4:
            side = t.cross(Vector((1, 0, 0)))
        side.normalize()
        u2 = side.cross(t).normalized()
        ra, rb = radii[i] if isinstance(radii[i], (tuple, list)) else (radii[i], radii[i])
        if ra < 1e-4 and rb < 1e-4:
            rings.append([m.v(tuple(p))])
            continue
        ring = []
        for s in range(sides):
            th = start_angle + 2 * math.pi * s / sides
            q = p + side * (math.cos(th) * ra) + u2 * (math.sin(th) * rb)
            ring.append(m.v(tuple(q)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 and len(r1) == 1:
            continue
        if len(r1) == 1:
            for s in range(len(r0)):
                m.f((r0[s], r0[(s + 1) % len(r0)], r1[0]), pal)
        elif len(r0) == 1:
            for s in range(len(r1)):
                m.f((r0[0], r1[(s + 1) % len(r1)], r1[s]), pal)
        else:
            for s in range(sides):
                m.f((r0[s], r0[(s + 1) % sides], r1[(s + 1) % sides], r1[s]), pal)
    if caps:
        if len(rings[0]) > 1:
            m.f(rings[0], pal)
        if len(rings[-1]) > 1:
            m.f(rings[-1], pal)


def mirror_copy(m, v0, f0):
    """Mirror the verts/faces added since (v0, f0) across x = 0."""
    bm = m.bm
    bm.verts.index_update()
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    new = {}
    for v in list(bm.verts[v0:]):
        new[v.index] = bm.verts.new((-v.co.x, v.co.y, v.co.z))
    faces = list(bm.faces[f0:])
    for f in faces:
        vs = [new[v.index] for v in reversed(f.verts)]
        nf = bm.faces.new(vs)
        nf[m.pal] = f[m.pal]


# --- parts ---------------------------------------------------------------------------------------------

SEAMS = (16.4,)       # belt seams across the front wall
SEAM_W, SEAM_D = 0.14, 0.2


def hull(m):
    ys = [6.3, 6.38, 6.5, 6.65, 6.9, 7.3, 7.7, 8.1, 8.45, 8.65, 8.85, 9.05, 9.3, 9.7, 10.2, 10.7,
          11.2, 11.6, 11.95, 12.3, 12.65, 13.0, 13.45, 13.9, 14.4, 14.9, 15.4, 15.9]
    ys += [17.0, 17.5, 18.0, 18.45, 18.85, 19.2, 19.5, 19.72, 19.88, 19.98, 20.05]
    rings = []
    for y in ys:
        if y == 17.0:
            for s in SEAMS:
                rings += [(s - SEAM_W, section(s - SEAM_W)), (s - SEAM_W, section(s - SEAM_W, -SEAM_D)),
                          (s + SEAM_W, section(s + SEAM_W, -SEAM_D)), (s + SEAM_W, section(s + SEAM_W))]
        rings.append((y, section(y)))
    # The first and last rings shrink to round the ends.
    def shrink(pts, k, zc):
        return [(x * k, zc + (z - zc) * k) for x, z in pts]
    y0, p0 = rings[0]
    rings[0] = (y0, shrink(p0, 0.55, 2.0))
    rings.insert(0, (y0 - 0.05, shrink(p0, 0.2, 2.0)))
    y1, p1 = rings[-1]
    rings[-1] = (y1, shrink(p1, 0.7, 0.6))
    rings.append((y1 + 0.05, shrink(p1, 0.25, 0.6)))
    ymid = [(rings[i][0] + rings[i + 1][0]) / 2 for i in range(len(rings) - 1)]

    def palf(i, j):
        y = ymid[i]
        if j >= NT - 1:
            return BELLY
        # top segment j between top points j and j+1; a at its middle
        a = abs((j + 0.5) - (NT - 1) / 2) / ((NT - 1) / 2)
        if j in (0, NT - 2):
            return BELLY  # the side band (the roll's last step)
        if y < 8.9:
            return DARK
        if y < 12.3:
            return DARK if a < 0.3 else WALL
        return WALL

    loft(m, rings, palf, cap_pal=BELLY)


def ridge(m):
    ys = [12.6, 13.2, 14.0, 14.8, 15.6, 16.4, 17.2, 17.9, 18.5, 19.0, 19.35, 19.6]
    rings = []
    for y in ys:
        z = ZR(y)
        k = 1.0 - 0.45 * smoothstep(19.0, 19.6, y)
        w0, w1 = 0.5 * k, 0.24 * k
        rings.append((y, [(-w0, z - 0.5), (w0, z - 0.5), (w0, z + 0.02), (w1, z + 0.26), (-w1, z + 0.26), (-w0, z + 0.02)]))
    loft(m, rings, lambda i, j: TRIM)


def rim(m):
    path = [(-8.0, 11.35, 5.95), (-7.3, 11.6, 5.6), (-6.0, 11.85, 5.42), (-4.4, 11.98, 5.36), (-2.3, 12.07, 5.33),
            (0.0, 12.1, 5.32)]
    path = path + [(-x, y, z) for x, y, z in reversed(path[:-1])]
    radii = [(1.12, 0.85)] * len(path)
    sweep(m, path, radii, TRIM, sides=12)
    # bolt heads along the rim's top, a pixel apart in pairs
    for x in (-5.2, -2.6, 2.6, 5.2):
        y = 12.0 - 0.0005 * x * x
        z = 5.33 + 0.004 * x * x + 0.8
        sweep(m, [(x, y, z - 0.15), (x, y, z + 0.14), (x, y, z + 0.16)], [(0.24, 0.24), (0.2, 0.2), (0.0, 0.0)], TRIM, sides=8)


def dome(m):
    cy, z0, hd = 8.25, 2.6, 4.75
    rxf, rxb, ryf, ryb = 5.2, 4.5, 2.4, 2.15

    def plan(th, k):
        c, s = math.cos(th), math.sin(th)
        ry = ryf if s > 0 else ryb
        rx = rxf + (rxb - rxf) * smoothstep(0.0, -1.0, s)
        return rx * c * k, cy + ry * s * k

    n = 32
    # lower band (to phi 34 deg), a seam, then the cap
    phis = [(0, 0.0), (12, 0.0), (24, 0.0), (34, 0.0), (34, -0.13), (37, -0.13), (37, 0.0), (48, 0.0), (60, 0.0), (71, 0.0),
            (81, 0.0), (88, 0.0)]
    rings = []
    for deg, g in phis:
        ph = math.radians(deg)
        k = math.cos(ph)
        ring = []
        for i in range(n):
            th = 2 * math.pi * i / n
            x, y = plan(th, k)
            # grow inward for the seam (radially)
            if g:
                x, y = x * (1 + g / 5.0), cy + (y - cy) * (1 + g / 2.4)
            ring.append(m.v((x, y, z0 + hd * math.sin(ph) + (g * 0.3 if g else 0))))
        rings.append(ring)
    top = m.v((0.0, cy + 0.05, z0 + hd))
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            m.f((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]), DOME)
    for i in range(n):
        m.f((rings[-1][i], rings[-1][(i + 1) % n], top), DOME)
    m.f(list(reversed(rings[0])), DOME)
    # dark collar where the dome meets the well
    col = []
    for i in range(n + 1):
        th = 2 * math.pi * i / n
        x, y = plan(th, 1.0)
        col.append((x * 0.99, cy + (y - cy) * 0.98, z0 + 0.6))
    sweep_loop(m, col[:-1], 0.3, 0.3, DARK)


def sweep_loop(m, pts, ra, rb, pal, sides=8):
    """A closed ring tube through pts."""
    n = len(pts)
    P = [Vector(p) for p in pts]
    rings = []
    for i in range(n):
        t = (P[(i + 1) % n] - P[i - 1]).normalized()
        side = t.cross(Vector((0, 0, 1))).normalized()
        u2 = side.cross(t).normalized()
        rings.append([m.v(tuple(P[i] + side * math.cos(2 * math.pi * s / sides) * ra + u2 * math.sin(2 * math.pi * s / sides) * rb))
                      for s in range(sides)])
    for i in range(n):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for s in range(sides):
            m.f((r0[s], r0[(s + 1) % sides], r1[(s + 1) % sides], r1[s]), pal)


HORN_PATH = [(-7.95, 10.9, 4.2), (-8.0, 10.0, 5.5), (-8.1, 9.0, 6.75), (-8.35, 8.0, 7.75), (-8.7, 7.15, 8.45),
             (-9.0, 6.45, 8.85), (-9.15, 5.95, 8.95), (-9.2, 5.75, 8.8)]
HORN_R = [(1.6, 1.95), (1.55, 1.8), (1.42, 1.55), (1.18, 1.25), (0.85, 0.95), (0.55, 0.62), (0.3, 0.33), (0.0, 0.0)]


def horns(m):
    bm = m.bm
    v0, f0 = len(bm.verts), len(bm.faces)
    sweep(m, HORN_PATH, HORN_R, DOME, sides=14, up=(1, 0, 0))
    # a machined collar round the horn's root, where it leaves the bowl
    sweep(m, [(-7.9, 10.75, 4.45), (-7.93, 10.35, 5.05), (-7.95, 9.95, 5.62)],
          [(1.72, 2.1), (1.74, 2.12), (1.66, 2.0)], TRIM, sides=14, up=(1, 0, 0))
    bm.verts.ensure_lookup_table()
    mirror_copy(m, v0, f0)


def chine(m):
    """A rubbing strake along the waist, from the shoulders round the front."""
    ys = [9.3, 10.5, 12.0, 13.5, 15.0, 16.5, 17.8, 18.8, 19.4]
    for sx in (-1, 1):
        path = [(sx * (HW(y) - 0.1), y, ZW + 0.15) for y in ys]
        radii = [(0.0, 0.0) if i in (0, len(ys) - 1) else (0.22, 0.26) for i in range(len(ys))]
        radii[1] = radii[-2] = (0.16, 0.2)
        sweep(m, path, radii, DARK, sides=6)


# --- object ------------------------------------------------------------------------------------------

MATS = {}


def mat_of(sprite, idx):
    if idx not in MATS:
        met, rough = PROPS[idx]
        MATS[idx] = common.palette_material(sprite, idx, TAG, metallic=met, roughness=rough)
    return MATS[idx]


def to_object(m, sprite, coll, smooth_angle=34):
    bm = m.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    M = Matrix(((PX, 0, 0, 0.5 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)  # the y reflection flipped them
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    pals = sorted({f[m.pal] for f in bm.faces})
    me = bpy.data.meshes.new(m.name)
    slot = {}
    for p in pals:
        slot[p] = len(me.materials)
        me.materials.append(mat_of(sprite, p))
    for f in bm.faces:
        f.material_index = slot[f[m.pal]]
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(m.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    return obj


def join(objs, name):
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


def build(sprite, coll):
    parts = []
    for nm, fn, ang in (("hull", hull, 40), ("ridge", ridge, 30), ("rim", rim, 40), ("dome", dome, 40),
                        ("horns", horns, 40), ("chine", chine, 40)):
        m = Mesh(f"{TAG}_{nm}")
        fn(m)
        parts.append(to_object(m, sprite, coll, ang))
    return join(parts, NAME)


def apply_weighted(obj):
    bpy.context.view_layer.update()
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(obj)


def bake(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    bpy.context.view_layer.update()
    T.TINT = (0.97, 0.98, 1.0)
    T.TEXTURED = tuple(range(len(obj.data.materials)))
    try:
        T.bake_maps(obj, out_dir, size=1024, samples=48)
    finally:
        T.TINT, T.TEXTURED = tint, textured


# --- measurement and views (scratch) ---------------------------------------------------------------

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


def pal_grid(objs):
    deps = bpy.context.evaluated_depsgraph_get()
    rows = []
    for r in range(H):
        row = []
        for c in range(W):
            X, Y = (c + 0.5 - W / 2) * PX, (H / 2 - (r + 0.5)) * PX
            best = None
            for o in objs:
                ev = o.evaluated_get(deps)
                hit, loc, nrm, fi = ev.ray_cast(Vector((X, Y, 5.0)), Vector((0, 0, -1)))
                if hit and (best is None or loc.z > best[0]):
                    mat = o.data.materials[o.data.polygons[fi].material_index]
                    best = (loc.z, int(mat.name.split("_")[1]))
            row.append(best[1] if best else -1)
        rows.append(row)
    return rows


def top_mask(objs, path):
    scene = bpy.context.scene
    for o in scene.objects:
        o.hide_render = o not in objs
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    K = 20
    scene.render.resolution_x, scene.render.resolution_y = W * K, H * K
    scene.render.resolution_percentage = 100
    c = cam(scene, "top_mask", (0, 0, 10), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    scene.camera = c
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def lit_views(show, out):
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o not in show and o.name != "ground"
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
    if "sun" not in bpy.data.objects:
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 3.2
        scene.collection.objects.link(sun)
        sun.rotation_euler = (math.radians(35), math.radians(-30), math.radians(20))
        fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
        fill.data.energy = 0.9
        scene.collection.objects.link(fill)
        fill.rotation_euler = (math.radians(-60), math.radians(40), 0)
        bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.6))
        gr = bpy.context.active_object
        gr.name = "ground"
        gm = bpy.data.materials.new("ground")
        gm.use_nodes = True
        next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.05, 0.09, 0.05, 1)
        gr.data.materials.append(gm)
    V = 480
    scene.render.resolution_x = scene.render.resolution_y = V
    d = 4.0
    t = math.radians(32)
    views = {
        "top": ((0, 0, d), 2.4, (0, 0, 0)),
        "game": ((0, -d * math.sin(t), d * math.cos(t)), 2.4, (0, 0, 0.3)),
        "q34": ((d * 0.55, -d * 0.6, d * 0.55), None, (0, 0, 0.3)),
        "q34b": ((-d * 0.6, d * 0.55, d * 0.5), None, (0, 0, 0.3)),
        "front": ((0, -d, 0.35), 2.4, (0, 0, 0.35)),
        "side": ((d, 0, 0.35), 2.4, (0, 0, 0.35)),
        "rear": ((0, d, 0.35), 2.4, (0, 0, 0.35)),
        "under": ((d * 0.4, -d * 0.5, -d * 0.6), None, (0, 0, 0)),
    }
    for name, (loc, ortho, look) in views.items():
        bpy.data.objects["ground"].hide_render = name in ("under", "side", "front", "rear")
        c = cam(scene, f"v_{name}", loc, look, ortho=ortho, lens=50)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        scene.render.filepath = str(out / f"v_{name}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(TAG)
    bpy.context.view_layer.update()
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    obj = build(sprite, coll)
    # The outline shell comes from a sealed pre-cull copy (D90, D118).
    pre = obj.copy()
    pre.data = obj.data.copy()
    coll.objects.link(pre)
    T.cull_hidden(obj)
    apply_weighted(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{TAG}: {tris} triangles")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        top_mask([obj], views / "top.png")
        (views / "pal.json").write_text(json.dumps(pal_grid([obj])))
    fmt = "AUTO"
    for o in bpy.data.objects:
        o.hide_render = False
    pre.hide_render = True
    if "--no-bake" not in argv:
        bd = HERE / "bake"
        bd.mkdir(parents=True, exist_ok=True)
        bake(obj, bd)
        fmt = "WEBP"
    sh = common.outline_shell(pre, coll, voxel=0.02, faces=1500, smooth=6, inside=0.0)
    sh.name = f"{NAME}_outline"
    # held just inside the culled model (D90)
    sw = sh.modifiers.new("inside", "SHRINKWRAP")
    sw.target = obj
    sw.wrap_method = "NEAREST_SURFACEPOINT"
    sw.wrap_mode = "INSIDE"
    sw.offset = -0.004
    common._apply_modifiers(sh)
    bpy.data.objects.remove(pre, do_unlink=True)
    bpy.context.view_layer.update()
    common.export_sprite_model(WT, [obj, sh], "enemies/newshh-93", sprite["sprites"], image_format=fmt)
    if views:
        sh.hide_render = True
        lit_views([obj], views)
        scene = bpy.context.scene
        c = cam(scene, "toplit", (0, 0, 4), (0, 0, 0), ortho=H * PX)
        c.rotation_euler = (0, 0, 0)
        scene.render.resolution_x, scene.render.resolution_y = W * 16, H * 16
        scene.camera = c
        scene.render.filepath = str(views / "top_lit.png")
        bpy.ops.render.render(write_still=True)
    (HERE / "stats.json").write_text(json.dumps({"triangles": tris, "shell_faces": len(sh.data.polygons)}))


if __name__ == "__main__":
    main()
