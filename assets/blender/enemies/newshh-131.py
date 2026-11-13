"""Gold carapace pod (newshh.shp size 2, frame 131), a D65 hard-surface flyer.

WHAT IT IS: the lead (bottom) segment of GYGES's (2.2) swaying 7-piece column: an
assembly-newshh-55 drill spike on top, five newshh-93 bronze bowls, and this pod at the bottom.
Type 425, armour 20, no fire; it weaves -4..+4 px/tick with the column (each link in its own
phase). It flies: a round, closed belly, nothing standing on the ground. Built in the column's
bronze (newshh-93's satin metal) as a beetle-like carapace pointed at the bottom.

Reading of the sprite (24x28; pixel (c, r) covers [c, c+1] x [r, r+1]; ink ring all round, the
model's edge on its inner side, D74):
- Head cap (rows 1-3, cols 6-18): a rounded cap in front, its hot spot (28-31) sheen; palette 22.
  A cut groove under it (row 4) with two short slots down beside the keel (cols 10 / 14, rows 4-6),
  dark (18).
- Carapace (rows 4-23): one bronze shell, lit left half 22-25, shaded right half 18-21 (lighting:
  the shell is crested along the keel). Palette 22.
- Keel (col 12, rows 6-23): a pale raised ridge from the cap join to the point; palette 26 (its
  median, the 29-31 hot spots left out).
- Shoulder lobes (rows 10-17, cols 3-6 / 18-21): rounded pads on the flanks, the shell's 22.
- Tail plate seams (cols 6-9 / 15-17, rows 17-22): the dark lines from each lobe to the point: a
  panel groove (18) bounding the tail plate.
- Ears (rows 5-8, cols 3-4 / 20-21): tan tabs at the shoulders, palette 23; the ink round them is
  the outline.
Underside (unseen): a round belly, palette 20.

Coordinates while building: sprite px, x = column edge - 12.5 (the symmetry axis: column 12's
centre), y = row edge (down the sprite = toward the front), z up. To Blender: X = (x + 0.5) / 12,
Y = (14 - y) / 12, Z = z / 12 (newshh-93's placement).

  tools/build-models.sh -j 2 assets/blender/enemies/newshh-131.py
  (or Blender -b -P assets/blender/enemies/newshh-131.py -- [--views DIR] [--no-bake])
Exports public/models/enemies/newshh-131.glb and src/render/spriteModels/newshh-131.json.
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

NAME = "newshh-131"
TAG = "nshh131A"
PX = 1 / 12
W, H = 24, 28

# palette index -> (metallic, roughness): newshh-93's satin bronze (D53)
PROPS = {18: (0.22, 0.62), 20: (0.28, 0.55), 22: (0.34, 0.4), 23: (0.34, 0.38), 26: (0.36, 0.34)}
SLOT, BELLY, SHELL, EAR, KEEL = 18, 20, 22, 23, 26

pchip = T.pchip


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def band(a, b, soft, x):
    """1 between a and b, easing to 0 over `soft` outside them."""
    return smoothstep(a - soft, a, x) * (1 - smoothstep(b, b + soft, x))


# --- plan and heights --------------------------------------------------------------------------------

# Shell half width per row edge y (inner edge of the ink ring, D74), ears left out (they are their
# own parts), smooth through the pixel steps.
HW = pchip([0.9, 1.2, 1.6, 2.5, 3.5, 4.4, 5.5, 6.5, 7.5, 8.5, 9.5, 10.4, 11.2, 12.0, 13.5, 15.0, 16.0, 16.8,
            17.8, 18.8, 19.6, 20.5, 21.5, 22.4, 23.1, 23.7, 24.15],
           [3.0, 3.9, 4.4, 5.4, 6.4, 7.0, 7.0, 7.1, 7.4, 7.6, 7.6, 8.2, 9.0, 9.35, 9.4, 9.35, 8.9, 8.5,
            8.1, 7.5, 7.0, 6.3, 5.4, 4.3, 2.8, 1.4, 0.15])
# Belly depth below the waist.
BD = pchip([0.9, 2.0, 4.0, 8.0, 14.0, 19.0, 22.0, 23.5, 24.15], [1.0, 2.0, 2.8, 3.2, 3.2, 2.6, 1.6, 0.8, 0.3])
ZW = 0.35   # the waist (the belly's top edge)
RIM = 0.6   # the shell's edge
HEAD = 8.2  # top of the head cap
CROWN = 6.8  # the carapace crown behind the head (keel not included)
KEEL_H = 1.7  # how far the keel stands proud
FLANK = 0.85  # cross-section exponent: under 1 rounds the shell (no side walls)
CAP_END = 4.3  # the cap's back edge


def head_top(y, x):
    hw = HW(y)
    if y <= 3.2:
        h = HEAD * max(0.0, 1 - ((y - 3.2) / 2.35) ** 2) ** 0.6  # a rounded brow, not a wall
    else:
        h = HEAD - 0.6 * (y - 3.2) / 1.1
    h = max(h, RIM + 0.4)
    a = min(1.0, abs(x) / hw)
    return RIM + (h - RIM) * (1 - a * a) ** 0.7


def keel(y):
    """Keel height and width (sigma, px): full from row 6, easing down toward the point."""
    k = KEEL_H * (0.5 + 0.5 * smoothstep(4.4, 6.5, y)) * (1 - 0.4 * smoothstep(12.0, 23.0, y))
    k *= 1 - 0.6 * smoothstep(22.8, 24.2, y)
    sig = 1.25 - 0.45 * smoothstep(12.0, 23.0, y)
    return k, sig


# The tail plate's seam (left side; mirrored): from the lobe's lower edge to beside the point.
SEAM = [(-6.4, 16.9), (-5.6, 18.6), (-4.6, 20.3), (-3.7, 21.8), (-3.0, 22.9)]


# The slots down beside the keel under the cap (cols 10 / 14, rows 4-6; left side, mirrored).
SLOTS = [(-5.5, 4.62), (-4.2, 4.55), (-2.9, 4.5), (-2.05, 4.75), (-2.0, 5.5), (-1.95, 6.3), (-1.9, 6.9)]


def body_top(y, x):
    hw = HW(y)
    a = min(1.0, abs(x) / hw)
    # the crown: level behind the head, falling in a smooth arch to the point
    e = max(0.0, y - 10.5) / 16.5
    s = RIM + (CROWN - RIM) * max(0.0, 1 - e * e) ** 0.55
    s *= 0.8 + 0.2 * smoothstep(CAP_END, 6.8, y)   # the body tucks under the cap's back lip
    s = RIM + (s - RIM) * (1 - 0.65 * smoothstep(21.0, 24.3, y))   # the point slopes down to a prow
    z = RIM + (s - RIM) * (1 - a * a) ** FLANK
    k, sig = keel(y)
    z += k * math.exp(-(x / sig) ** 2)
    # shoulder lobes: rounded pads on the flanks
    for side in (-1, 1):
        r2 = ((x - side * 7.4) / 3.0) ** 2 + ((y - 13.0) / 4.3) ** 2
        if r2 < 1:
            z += 2.4 * (1 - r2) ** 1.6 * (1 - 0.7 * a ** 6)
    return max(z, RIM * (1 - a) + 0.2 * a)


def top_z(y, x):
    if y < CAP_END:
        return head_top(y, x)
    if y < CAP_END + 0.15:
        return max(head_top(y, x), body_top(y, x))
    return body_top(y, x)


def top_pal(j):
    """Top segment j (between top samples j and j+1): the keel stripe is the segments between the
    keel's fixed samples (+-0.62 px, closing up toward the point), so its edges run smooth."""
    c = NHALF - 1
    return KEEL if c - 2 <= j <= c + 1 else SHELL


# Fixed x samples about the keel (so its stripe edges run straight), then fractions of the half width.
X_IN = [0.0, 0.31, 0.62, 1.0, 1.5, 2.0, 2.6]
A_OUT = [0.36, 0.44, 0.52, 0.6, 0.67, 0.73, 0.79, 0.84, 0.885, 0.925, 0.955, 0.98, 1.0]
A_BEL = [0.97, 0.88, 0.72, 0.5, 0.26, 0.0]


def top_xs(hw):
    k = min(1.0, hw / 7.2)   # near the point the inner samples close up with the width
    inner = [x * k for x in X_IN]
    outer = [max(a * hw, inner[-1] + 0.05 * (i + 1)) for i, a in enumerate(A_OUT)]
    outer = [min(o, hw * (0.38 + 0.62 * (i + 1) / len(A_OUT))) if hw < 7.2 else o for i, o in enumerate(outer)]
    half = inner + outer
    half = [min(v, hw) for v in half]
    for i in range(1, len(half)):  # strictly increasing
        if half[i] <= half[i - 1]:
            half[i] = half[i - 1] + 1e-3
    half[-1] = max(half[-1], half[-2] + 1e-3)
    return [-v for v in reversed(half[1:])] + half


NHALF = len(X_IN) + len(A_OUT)
NT = 2 * NHALF - 1


def section(y):
    """Closed loop (x, z): top from x = -hw to +hw, then the belly back."""
    hw = HW(y)
    xs = top_xs(hw)
    edge = xs[-1]
    pts = [(x, top_z(y, x)) for x in xs]
    bd = BD(y)
    for a in A_BEL:
        pts.append((a * edge, ZW - bd * math.sqrt(max(0.0, 1 - a ** 2.2))))
    for a in reversed(A_BEL[:-1]):
        pts.append((-a * edge, ZW - bd * math.sqrt(max(0.0, 1 - a ** 2.2))))
    return pts


# --- mesh helpers (newshh-93's) ---------------------------------------------------------------------

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

def hull(m):
    ys = [0.9 + 0.3 * k for k in range(12)]                    # 0.9 .. 4.2 (the cap)
    ys += [CAP_END, CAP_END + 0.15, 4.6, 4.8, 5.0, 5.3, 5.6, 6.0, 6.5, 7.0]
    ys += [7.6 + 0.6 * k for k in range(15)]                   # 7.6 .. 16.0
    ys += [16.4 + 0.4 * k for k in range(18)]                  # 16.4 .. 23.2
    ys += [23.5, 23.75, 23.95]
    rings = [(y, section(y)) for y in ys]

    # The front rounds over in two shrinking rings.
    def shrink(pts, k, zc):
        return [(x * k, zc + (z - zc) * k) for x, z in pts]
    y0, p0 = rings[0]
    rings.insert(0, (y0 - 0.12, shrink(p0, 0.62, 0.8)))
    rings.insert(0, (y0 - 0.2, shrink(p0, 0.22, 0.8)))
    ymid = [(rings[i][0] + rings[i + 1][0]) / 2 for i in range(len(rings) - 1)]

    vr = [[m.v((x, y, z)) for x, z in pts] for y, pts in rings]
    n = len(vr[0])
    for i in range(len(vr) - 1):
        y = ymid[i]
        for j in range(n):
            k = (j + 1) % n
            if j < NT - 1:
                pal = top_pal(j) if y >= 5.6 else SHELL
            else:
                pal = BELLY
            m.f((vr[i][j], vr[i][k], vr[i + 1][k], vr[i + 1][j]), pal)
    m.f(list(reversed(vr[0])), SHELL)
    # the point
    tip = m.v((0.0, 24.3, 0.9))
    last = vr[-1]
    for j in range(n):
        k = (j + 1) % n
        m.f((last[j], last[k], tip), SHELL if j < NT - 1 else BELLY)


EAR_PATH = [(-7.3, 4.75, 1.9), (-7.9, 5.4, 2.25), (-8.3, 6.5, 2.35), (-8.2, 7.6, 2.2), (-7.7, 8.45, 1.85),
            (-7.35, 8.8, 1.6)]
EAR_R = [(0.0, 0.0), (0.95, 0.85), (1.2, 1.05), (1.15, 1.0), (0.8, 0.7), (0.0, 0.0)]


def trim(m):
    """The dark slots beside the keel and the tail plate's seams: rounded inlays sunk flush into the
    shell (smooth lines, not face-picked pixel steps)."""
    v0, f0 = len(m.bm.verts), len(m.bm.faces)
    for pts, (ra, rb) in ((SLOTS, (0.4, 0.32)), (SEAM, (0.32, 0.26))):
        path, radii = [], []
        for i, (x, y) in enumerate(pts):
            path.append((x, y, body_top(y, x) - 0.05))
            end = i in (0, len(pts) - 1)
            radii.append((ra * 0.55, rb * 0.55) if end else (ra, rb))
        sweep(m, path, radii, SLOT, sides=8)
    mirror_copy(m, v0, f0)


def ears(m):
    v0, f0 = len(m.bm.verts), len(m.bm.faces)
    sweep(m, EAR_PATH, EAR_R, EAR, sides=12)
    mirror_copy(m, v0, f0)


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
    slot_of = {}
    for p in pals:
        slot_of[p] = len(me.materials)
        me.materials.append(mat_of(sprite, p))
    for f in bm.faces:
        f.material_index = slot_of[f[m.pal]]
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
    for nm, fn, ang in (("hull", hull, 42), ("trim", trim, 50), ("ears", ears, 50)):
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
        import tempfile
        bd = Path(tempfile.mkdtemp(prefix="nshh131_bake_"))
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
    common.export_sprite_model(WT, [obj, sh], f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
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
    if views:
        (views / "stats.json").write_text(json.dumps({"triangles": tris, "shell_faces": len(sh.data.polygons)}))


if __name__ == "__main__":
    main()
