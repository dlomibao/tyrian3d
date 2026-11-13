"""Batch b060 (newsh8.shp): the four merged items (assembly-newsh8-229, assembly-newsh8-9, newsh8-115,
newsh8-129), rebuilt to the D65 standard in this one script (the other three scripts call main() here
for their own models; lib_b060 is no longer used).

(1) assembly-newsh8-229, the antlered spider (newsh8-229 + newsh8-231, 48x28 px; 3.4 IXMUCANE / 3.9
SAWBLADES, terrain fixed on the top layer, so a creature walking on the upper terrain). What it is: a
chitin spider seen from above, mirror symmetric about sprite column 23. In the middle a glossy red
abdomen made of two domed wing cases (the sprite's ink column 23 is the groove between them), above
it a red teardrop bead (an eye/sensor) held on two grey stalks over a dark neck, below it two grey
jointed fangs that hook in under the abdomen. Each side a brown cephalothorax hump, from which four
brown legs run out: each rises to a knee and comes down to a claw tip on the ground, and from above
they curl like antlers. Chitin joints are modelled collars. The three walk frames (229/233/273 and
231/235/275) move the leg tips 1 px a frame along the leg (the antler and third leg pull in, the
second and fourth reach out) and swing the fang feet in: a leg set and an outline shell per frame
(common.frame_part), the body static.

(2) assembly-newsh8-9 (newsh8-9 over newsh8-87, 24x56 px; IXMUCANE): a falling rock pod. newsh8-9 is a
hollow boulder husk: a rim of rock round a dark pit, three rock fangs on its lower lip; over its
frames a lumpy rock worm pushes out of the pit and down over the lip, newsh8-87 its tapering tail
below; frame 85 the worm alone (mushroom head). Rock: lofted/remeshed closed bodies shaded by the
D175 facet ramp (lib_newshd_rock.facet_ramp, imported). Twelve models as the current script
(newsh8-9..-f8, newsh8-87..-f4), animated ones with a worm per frame.

(3) newsh8-115, a grey dome craft flying up the screen: a three-panel metal dome with a glowing lamp
in its nose, a dark rim, a brown crossbar under it with a glowing core socket in the middle, and two
brown struts that end in hooked flukes. Frames 115/117/119 pulse the lamp and core (palette frames)
and curl the hooks (a hook pair per frame).

(4) newsh8-129, the carrot prop: an orange tapered body with modelled growth rings, a green leaf tuft
and a brown porthole with a small yellow light, lying on the terrain.

Run: blender --background --python assets/blender/enemies/assembly-newsh8-229.py [-- --only spider,dome,carrot,worm]
(run directly it builds only the spider, --only spider; assembly-newsh8-9.py, newsh8-115.py and
newsh8-129.py load this file and build the worm, dome and carrot, so a full tools/build-models.sh run
writes each glb once; exports public/models/enemies/<model>.glb and src/render/spriteModels/<model>.json for each model;
--design <glb> also writes all objects at their assembly places, --manifest <json> a summary).
"""

import bisect
import json
import math
import random
import re
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "assets" / "blender" / "enemies"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import lib_newshd_rock as RK  # noqa: E402
import sprite_mask as SM  # noqa: E402

HERE = Path(__file__).resolve().parent
PX = 1 / 12


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


# --- helpers (copied, not shared) ---------------------------------------------------------------

def pchip(xs, ys):
    """Monotone cubic interpolation (copy of usp_talon.pchip)."""
    n = len(xs)
    if n == 1:
        return lambda x: ys[0]
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
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def se(a, n):
    """Superellipse cos/sin with exponent n."""
    c, s = math.cos(a), math.sin(a)
    return math.copysign(abs(c) ** (2 / n), c), math.copysign(abs(s) ** (2 / n), s)


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


class Mesh:
    """A bmesh in sprite px: u right, v down the sprite (screen down), z up."""

    def __init__(self):
        self.bm = bmesh.new()

    def loft(self, rings, mats, cap0=True, cap1=True, smooth=True):
        """rings: lists of (u, v, z) of equal length (a 1-point ring is a pole); mats[i] is the
        band i -> i+1's material (an int: all)."""
        bm = self.bm
        vs = [[bm.verts.new(p) for p in r] for r in rings]
        mats = mats if isinstance(mats, list) else [mats] * (len(rings) - 1)
        faces = []
        for i, (r0, r1) in enumerate(zip(vs, vs[1:])):
            n = max(len(r0), len(r1))
            for k in range(n):
                j = (k + 1) % n
                if len(r0) == 1 and len(r1) == 1:
                    continue
                if len(r0) == 1:
                    q = (r0[0], r1[k], r1[j])
                elif len(r1) == 1:
                    q = (r0[k], r1[0], r0[j])
                else:
                    q = (r0[k], r1[k], r1[j], r0[j])
                f = bm.faces.new(q)
                f.material_index = mats[i]
                f.smooth = smooth
                faces.append(f)
        if cap0 and len(vs[0]) > 2:
            f = bm.faces.new(list(reversed(vs[0])))
            f.material_index = mats[0]
            faces.append(f)
        if cap1 and len(vs[-1]) > 2:
            f = bm.faces.new(vs[-1])
            f.material_index = mats[-1]
            faces.append(f)
        return faces

    def pod(self, stations, mat, axis="v", sides=20, step=0.4, mats_of=None, n=2.4):
        """A closed body lofted along v: stations (v, cu, cz, hw, hh), pchip-interpolated, poles at
        both ends (hw 0). mats_of(v) -> material per band (default `mat`)."""
        vs = [s[0] for s in stations]
        fs = [pchip(vs, [s[i] for s in stations]) for i in range(1, 5)]
        cnt = max(2, int(round((vs[-1] - vs[0]) / step)))
        rings, mats = [], []
        for i in range(cnt + 1):
            v = vs[0] + (vs[-1] - vs[0]) * i / cnt
            cu, cz, hw, hh = (f(v) for f in fs)
            if i in (0, cnt) or hw < 1e-3:
                rings.append([(cu, v, cz)])
            else:
                ring = []
                for k in range(sides):
                    c, s = se(2 * math.pi * k / sides, n)
                    ring.append((cu + hw * c, v, cz + hh * s))
                rings.append(ring)
            if i:
                mats.append(mats_of(v) if mats_of else mat)
        return self.loft(rings, mats, cap0=False, cap1=False)

    def lathe(self, profile, cu, cz, sides=16, rz=1.0, mat=0, mats_of=None):
        """Solid of revolution about a line along v through (cu, cz): profile [(v, r)]."""
        rings, mats = [], []
        for i, (v, r) in enumerate(profile):
            if r <= 1e-6:
                rings.append([(cu, v, cz)])
            else:
                rings.append([(cu + r * math.cos(2 * math.pi * k / sides), v, cz + r * rz * math.sin(2 * math.pi * k / sides))
                              for k in range(sides)])
            if i:
                mats.append(mats_of(v) if mats_of else mat)
        return self.loft(rings, mats, cap0=False, cap1=False)

    def sweep(self, ctrl, mats, sides=10, step=0.42, ext=0.0, taper=1.6, hh_k=1.05, collars=(), claw=0.8,
              root_cap=True, n=2.2, tip=True):
        """A tube along a pchip path through ctrl [(u, v, z, hw)] (hw: horizontal half width px), the
        tip at ctrl[0]. ext > 0 extends the tip that far along its tangent, < 0 trims it. Collars:
        arc positions (px from the base path's tip) of raised joint rings. mats = (body, collar, claw)."""
        t = [0.0]
        for a, b in zip(ctrl, ctrl[1:]):
            t.append(t[-1] + math.dist(a[:3], b[:3]))
        fu, fv, fz, fw = (pchip(t, [p[i] for p in ctrl]) for i in range(4))
        total = t[-1]
        s0 = max(0.0, -ext)
        cnt = max(2, int(round((total - s0) / step)))
        ss = [s0 + (total - s0) * i / cnt for i in range(cnt + 1)]
        pts = [(Vector((fu(s), fv(s), fz(s))), fw(s), s) for s in ss]
        if ext > 0:
            d = (pts[0][0] - pts[1][0]).normalized()
            k = max(1, int(round(ext / step)))
            pre = [(pts[0][0] + d * ext * (k - i) / k, pts[0][1], -ext * (k - i) / k) for i in range(k)]
            pts = pre + pts
        acc = [0.0]
        for a, b in zip(pts, pts[1:]):
            acc.append(acc[-1] + (b[0] - a[0]).length)
        rings, bands = [], []
        body, collar_m, claw_m = mats
        for i, (p, w, s) in enumerate(pts):
            d = acc[i]
            if i == 0 and tip:
                rings.append([tuple(p)])
                continue
            tw = min(1.0, (d / taper)) ** 0.6 if tip else 1.0
            bump = 0.0
            for c in collars:
                bump = max(bump, 1 - smoothstep(0.18, 0.42, abs(s - c)))
            hw = w * (0.32 + 0.68 * tw) * (1 + 0.16 * bump)
            hh = hw * hh_k
            if i == 0:
                tan = pts[1][0] - pts[0][0]
            elif i == len(pts) - 1:
                tan = pts[-1][0] - pts[-2][0]
            else:
                tan = pts[i + 1][0] - pts[i - 1][0]
            tan.normalize()
            side = tan.cross(Vector((0, 0, 1)))
            if side.length < 1e-4:
                side = Vector((1, 0, 0))
            side.normalize()
            up = side.cross(tan).normalized()
            if up.z < 0:
                up = -up
            ring = []
            for k in range(sides):
                c, sn = se(2 * math.pi * k / sides, n)
                q = p + side * (c * hw) + up * (sn * hh)
                ring.append(tuple(q))
            rings.append(ring)
        for i in range(1, len(pts)):
            s, d = pts[i][2], acc[i]
            near = any(abs(s - c) < 0.3 for c in collars)
            bands.append(claw_m if (tip and d < claw) else (collar_m if near else body))
        return self.loft(rings, bands, cap0=False, cap1=root_cap)

    def to_object(self, name, mats, coll, xf, smooth_angle=40.0):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        for v in bm.verts:
            v.co = xf(v.co)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        try:
            me.set_sharp_from_angle(angle=math.radians(smooth_angle))
        except Exception:
            pass
        return obj


def xform(W, H, cu=None, cv=None):
    """px (u, v, z) -> Blender, the model's box centre at the origin (cu, cv override it)."""
    cu = W / 2 if cu is None else cu
    cv = H / 2 if cv is None else cv
    return lambda p: Vector(((p[0] - cu) * PX, (cv - p[1]) * PX, p[2] * PX))


def mat(sprite, idx, tag, metallic=0.3, roughness=0.5, glow=0.0, frames=None, spec=None):
    m = common.palette_material(sprite, idx, tag, metallic=metallic, roughness=roughness,
                                emission_strength=glow, frames=frames)
    if spec is not None:
        bsdf = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
        for key in ("Specular IOR Level", "Specular"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = spec
                break
    return m


def join(objs, name, coll):
    """A joined copy of `objs` (for a sealed shell source)."""
    bm = bmesh.new()
    mats = []
    for o in objs:
        tmp = bmesh.new()
        tmp.from_mesh(o.data)
        tmp.transform(o.matrix_world)
        me = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def shell_multi(obj, coll, voxel=0.012, faces=3000, smooth=6, inside=0.0, min_extent=0.0004):
    """common.outline_shell, but keeping EVERY outer voxel island (the shared helper keeps only the
    largest, so a model of disjoint parts lost the ink on the smaller ones). Islands lying inside
    another island's box (an open model's inner shells) are dropped."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    coll.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    rm.use_smooth_shade = True
    apply_mods(shell)
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

    def box(isl):
        xs = [v.co.x for v in isl]
        ys = [v.co.y for v in isl]
        zs = [v.co.z for v in isl]
        return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    boxes = [box(i) for i in islands]
    keep = set()
    for i, b in enumerate(boxes):
        if (b[1] - b[0]) * (b[3] - b[2]) < min_extent:
            continue
        inner = any(j != i and o[0] < b[0] and o[1] > b[1] and o[2] < b[2] and o[3] > b[3] and o[4] < b[4] and o[5] > b[5]
                    for j, o in enumerate(boxes))
        if not inner:
            keep |= {v.index for v in islands[i]}
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    nf = len(shell.data.polygons)
    if nf > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / nf
    apply_mods(shell)
    if inside > 0:
        sw = shell.modifiers.new("inside", "SHRINKWRAP")
        sw.target = obj
        sw.wrap_method = "NEAREST_SURFACEPOINT"
        sw.wrap_mode = "INSIDE"
        sw.offset = -inside
        apply_mods(shell)
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def apply_mods(obj):
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def cut_open(obj, layout, coll, suffix):
    """Cut `obj` to each piece's 24x28 box WITHOUT filling the cut (for outline shells, so no ink is
    drawn across the seam), moved to the piece's origin. layout: [(name, cx px, cy px)]."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline{suffix}")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(f"{name}_outline{suffix}", me)
        coll.objects.link(sh)
        for poly in me.polygons:
            poly.use_smooth = True
        sh["tyrian_outline"] = True
        out[name] = sh
    return out


def split(obj, layout, coll):
    pieces = common.split_assembly(obj, layout, coll)
    return pieces


def load_rows(name, frame):
    data = json.loads((WT / "reference" / "models" / name / "sprite.json").read_text())
    fr = next(f for f in data["frames"] if f["index"] == frame)
    return [[int(v) for v in r.split()] for r in fr["pixels"]]


# =================================================================================================
# (1) The antlered spider
# =================================================================================================

SP_AXIS = 23.5  # the sprite's mirror axis: the centre of column 23 (u = c + 0.5)
SP_FRAMES = [(229, 231), (233, 235), (273, 275)]
SP_LAYOUT = [("newsh8-229", -12, 0), ("newsh8-231", 12, 0)]  # piece centres, px from the assembly centre


def C(c, r):
    """Pixel centre (column, row) to (u, v)."""
    return c + 0.5, r + 0.5


def legs_ctrl():
    """The four brown legs of the left side at frame 229, tip first: [(u, v, z, hw)] in px.
    Height: from the hump the leg rises to a knee and comes down to its claw on the ground."""
    def L(*pts):
        return [(c + 0.5, r + 0.5, z, w) for c, r, z, w in pts]
    antler = L((13.0, 0.75, 0.9, 0.55), (13.0, 2.0, 2.4, 0.6), (13.15, 3.7, 4.2, 0.75), (14.1, 5.0, 5.6, 1.0),
               (15.4, 6.3, 6.3, 1.0), (16.9, 7.6, 6.4, 1.3), (17.25, 9.6, 6.0, 1.45), (17.5, 11.2, 5.4, 1.55))
    second = L((9.0, 8.75, 0.9, 0.55), (9.05, 10.0, 2.6, 0.62), (10.0, 10.9, 4.3, 1.0), (11.0, 12.0, 5.5, 1.2),
               (12.6, 13.0, 6.0, 1.42), (14.6, 13.3, 5.8, 1.5), (16.6, 13.1, 5.2, 1.5))
    third = L((5.0, 11.75, 0.9, 0.55), (5.0, 13.0, 2.6, 0.62), (5.1, 15.0, 4.2, 0.75), (5.75, 16.6, 5.0, 0.95),
              (6.9, 18.0, 5.3, 1.05), (9.2, 18.55, 5.2, 1.05), (12.2, 18.45, 5.0, 1.05), (14.6, 17.8, 4.7, 1.3),
              (16.2, 16.9, 4.4, 1.4))
    fourth = L((1.0, 18.75, 0.9, 0.55), (1.15, 20.0, 2.4, 0.62), (1.6, 21.4, 3.6, 0.78), (3.1, 22.9, 4.3, 1.0),
               (4.6, 23.45, 4.6, 1.0), (8.0, 23.45, 4.6, 1.0), (10.9, 23.3, 4.4, 1.0), (12.4, 22.6, 4.3, 0.95),
               (13.0, 21.2, 4.2, 0.75), (12.9, 19.9, 4.3, 1.1), (14.6, 18.2, 4.5, 1.15))
    return {"antler": antler, "second": second, "third": third, "fourth": fourth}


# Arc positions of each leg's joints (px from the frame-229 tip): the knee and the hip.
COLLARS = {"antler": (4.4, 9.2), "second": (3.6, 7.3), "third": (4.4, 9.6), "fourth": (3.9, 12.3)}
# Tip extension per frame (px along the leg): the antler and third leg pull in, the others reach.
TIP_EXT = {"antler": (0, -1, -2), "second": (0, 1, 2), "third": (0, -1, -2), "fourth": (0, 1, 2)}
FANG_FOOT = (0.0, -1.0, -2.0)  # columns the fang's foot moves in (toward the axis... outward-left on screen)


def fang_ctrl(k):
    """The grey fang (left) on frame k: from under the hump down to a knee, hooking back in."""
    f = FANG_FOOT[k]
    pts = [(20.0 + f, 25.5, 0.8, 0.55), (18.9 + f, 24.3, 1.3, 0.65), (18.0 + f, 23.0, 1.8, 0.8),
           (17.0 + 0.8 * f, 21.9, 2.4, 1.2), (15.6, 21.2, 2.9, 1.4), (16.5, 19.6, 3.3, 1.05), (17.5, 18.0, 3.7, 0.9),
           (18.3, 16.3, 4.0, 0.95), (18.5, 15.3, 4.1, 1.0)]
    return [(c + 0.5, r + 0.5, z, w) for c, r, z, w in pts]


def mirror_ctrl(ctrl):
    return [(2 * SP_AXIS - u, v, z, w) for u, v, z, w in ctrl]


def spider_mats(sprite):
    t = "nsh8_229A"
    return [
        mat(sprite, 23, t, metallic=0.15, roughness=0.42, spec=0.6),   # 0 leg chitin (lit half's median 23; both halves 22)
        mat(sprite, 19, t, metallic=0.15, roughness=0.5),              # 1 joint collars, claws
        mat(sprite, 20, t, metallic=0.15, roughness=0.45, spec=0.6),   # 2 cephalothorax (median 20)
        mat(sprite, 70, t, metallic=0.2, roughness=0.22, spec=0.8),    # 3 abdomen wing cases (median 69.5)
        mat(sprite, 65, t, metallic=0.1, roughness=0.5),               # 4 dark red groove / under
        mat(sprite, 70, t + "b", metallic=0.25, roughness=0.15, spec=1.0),  # 5 the bead
        mat(sprite, 6, t, metallic=0.6, roughness=0.38),               # 6 grey stalks (6)
        mat(sprite, 7, t, metallic=0.6, roughness=0.36),               # 7 grey fangs (median 6.5)
        mat(sprite, 3, t, metallic=0.5, roughness=0.5),                # 8 dark neck / waist / fang joints
    ]


LEG, JOINT, THX, ABD, GROOVE, BEAD, STALK, FANG, DARK = range(9)


def spider_body(M):
    """The static body (both sides)."""
    for side in (1, -1):
        def U(u):
            return u if side > 0 else 2 * SP_AXIS - u
        # Cephalothorax hump: a chitin pod over columns 15-20, rows 8-17, highest toward the neck.
        st = [(7.6, 18.3, 4.2, 0.0, 0.0), (8.4, 18.3, 4.6, 1.5, 1.6), (10.0, 18.4, 4.7, 2.15, 2.3),
              (12.0, 17.9, 4.5, 2.75, 2.4), (15.0, 17.2, 4.1, 2.4, 2.1), (16.8, 16.3, 3.8, 1.7, 1.7),
              (18.0, 16.0, 3.5, 0.0, 0.0)]
        st = [(v, U(cu), cz, hw, hh) for v, cu, cz, hw, hh in st]
        M.pod(st, THX, sides=14, n=2.3)
        # Shoulder plate by the neck (columns 19-20, rows 9-14).
        st = [(8.6, 20.2, 4.4, 0.0, 0.0), (9.3, 20.3, 4.5, 1.0, 1.1), (11.5, 20.4, 4.5, 1.25, 1.3),
              (13.8, 20.3, 4.3, 1.0, 1.1), (14.6, 20.2, 4.2, 0.0, 0.0)]
        st = [(v, U(cu), cz, hw, hh) for v, cu, cz, hw, hh in st]
        M.pod(st, THX, sides=12, n=2.2)
        # Abdomen wing case (one of two domed lobes; their meeting line is the groove).
        cu = SP_AXIS - side * 1.75
        st = [(12.7, cu + side * 0.4, 4.6, 0.0, 0.0), (13.2, cu + side * 0.25, 4.6, 1.05, 1.0),
              (14.3, cu, 4.6, 1.85, 1.75), (16.2, cu - side * 0.3, 4.5, 2.2, 1.9), (17.8, cu, 4.3, 1.85, 1.7),
              (19.0, cu + side * 0.45, 4.0, 1.15, 1.25), (19.9, cu + side * 0.9, 3.7, 0.5, 0.6), (20.2, cu + side * 1.1, 3.6, 0.0, 0.0)]
        M.pod(st, ABD, sides=16, n=2.15)
        # Grey stalk under the bead (columns 22 and 24, rows 8-11), leaning in to hold it.
        u0 = SP_AXIS - side * 1.0
        M.sweep([(u0 - side * 0.15, 7.6, 7.2, 0.5), (u0, 9.0, 6.5, 0.5), (u0, 11.0, 5.6, 0.52), (u0, 12.4, 4.8, 0.55)],
                (STALK, DARK, STALK), sides=8, ext=0.0, tip=False, collars=(2.6,), root_cap=True)
    # Dark pleural folds between the humps and the abdomen (the sprite's ink column 19 / 27, rows 15-19).
    for side in (1, -1):
        cu = SP_AXIS - side * 4.0
        M.pod([(14.6, cu, 3.4, 0.0, 0.0), (15.4, cu, 3.5, 0.9, 1.1), (18.0, cu + side * 0.2, 3.3, 0.95, 1.1),
               (19.6, cu + side * 0.6, 3.0, 0.0, 0.0)], DARK, sides=10)
    # Dark neck between the stalks and the waist under the bead (rows 8-12, ink in the sprite).
    M.pod([(7.4, SP_AXIS, 5.4, 0.0, 0.0), (8.0, SP_AXIS, 5.4, 2.2, 1.2), (11.0, SP_AXIS, 5.0, 2.4, 1.4),
           (12.6, SP_AXIS, 4.6, 2.0, 1.6), (13.6, SP_AXIS, 4.2, 0.0, 0.0)], DARK, sides=12)
    # Groove floor between the wing cases (dark red), and the belly closing the abdomen.
    M.pod([(13.0, SP_AXIS, 3.9, 0.0, 0.0), (13.6, SP_AXIS, 4.0, 1.2, 1.9), (17.5, SP_AXIS, 3.9, 1.4, 1.9),
           (19.6, SP_AXIS, 3.4, 0.0, 0.0)], GROOVE, sides=12)
    # The bead: a red teardrop gem, pointed toward the top of the screen (rows 3.6-8.8).
    M.lathe([(3.65, 0.0), (4.1, 0.3), (4.9, 0.62), (5.8, 1.15), (6.7, 1.48), (7.5, 1.42), (8.2, 1.1), (8.7, 0.6),
             (8.95, 0.0)], SP_AXIS, 7.4, sides=16, rz=1.0, mat=BEAD)
    # A dark seating ring where the stalks hold the bead.
    M.lathe([(7.7, 0.0), (7.8, 1.0), (8.4, 1.25), (8.9, 0.9), (9.1, 0.0)], SP_AXIS, 7.0, sides=14, rz=0.8, mat=DARK)


def spider_legs(M, k):
    ctrl = legs_ctrl()
    for side in (1, -1):
        for leg, pts in ctrl.items():
            p = pts if side > 0 else mirror_ctrl(pts)
            M.sweep(p, (LEG, JOINT, JOINT), sides=10, ext=TIP_EXT[leg][k] * (1.7 if TIP_EXT[leg][k] > 0 else 1.0), collars=COLLARS[leg], claw=0.75,
                    taper=1.8)
        # Spine on the fourth leg's back (the sprite's dark pixels 6-7 on row 22) and the spur under
        # its outer bend (column 11, rows 24-25).
        sp = [(6.6, 22.0, 5.2, 0.0), (6.8, 22.9, 4.8, 0.5), (7.0, 23.5, 4.4, 0.55)]
        sp = [(u + 0.5, v + 0.5, z, w) for u, v, z, w in sp]
        M.sweep(sp if side > 0 else mirror_ctrl(sp), (JOINT, JOINT, JOINT), sides=8, taper=0.6, claw=0.0)
        sp = [(11.0, 25.35, 2.2, 0.0), (11.0, 24.6, 3.0, 0.5), (11.05, 23.6, 4.1, 0.6)]
        sp = [(u + 0.5, v + 0.5, z, w) for u, v, z, w in sp]
        M.sweep(sp if side > 0 else mirror_ctrl(sp), (LEG, JOINT, JOINT), sides=8, taper=0.9, claw=0.5)
        f = fang_ctrl(k)
        M.sweep(f if side > 0 else mirror_ctrl(f), (FANG, DARK, DARK), sides=10, collars=(4.4,), claw=0.0, taper=0.7,
                hh_k=1.0)


def build_spider():
    s229 = common.load_sprite(WT, "newsh8-229")
    s231 = common.load_sprite(WT, "newsh8-231")
    sprite = dict(s229)
    sprite["colors"] = {**s229["colors"], **s231["colors"]}
    coll = common.reset_collection("assembly-newsh8-229")
    mats = spider_mats(sprite)
    xf = xform(48, 28)
    M = Mesh()
    spider_body(M)
    body = M.to_object("spider_body", mats, coll, xf, smooth_angle=62)
    legs = []
    for k in range(3):
        M = Mesh()
        spider_legs(M, k)
        legs.append(M.to_object(f"spider_legs_{k}", mats, coll, xf, smooth_angle=62))
    out = {"newsh8-229": [], "newsh8-231": []}
    for name, piece in split(body, SP_LAYOUT, coll).items():
        piece.name = piece.data.name = name
        out[name].append(piece)
    for k, lo in enumerate(legs):
        for i, (name, piece) in enumerate(split(lo, SP_LAYOUT, coll).items()):
            fr = SP_FRAMES[k][i]
            piece.name = piece.data.name = f"{name}-legs-{fr}"
            out[name].append(common.frame_part(piece, [fr]))
        # The outline: a sealed whole (body + this frame's legs), one shell, cut open at the seam.
        whole = join([body, lo], f"spider_sealed_{k}", coll)
        sh = shell_multi(whole, coll, voxel=0.010, faces=7000, smooth=4, inside=0.004)
        for i, (name, s) in enumerate(cut_open(sh, SP_LAYOUT, coll, f"-{SP_FRAMES[k][i]}").items()):
            out[name].append(common.frame_part(s, [SP_FRAMES[k][i]]))
        for o in (whole, sh):
            bpy.data.objects.remove(o, do_unlink=True)
    for o in [body] + legs:
        bpy.data.objects.remove(o, do_unlink=True)
    return [("newsh8-229", out["newsh8-229"], [f[0] for f in SP_FRAMES], (-1.0, 0.0)),
            ("newsh8-231", out["newsh8-231"], [f[1] for f in SP_FRAMES], (1.0, 0.0))]


# =================================================================================================
# (3) The dome craft newsh8-115
# =================================================================================================

D_AXIS = 12.5
D_FRAMES = [115, 117, 119]


def dome_mats(sprite):
    t = "nsh8_115A"
    return [
        mat(sprite, 6, t, metallic=0.2, roughness=0.55, spec=0.3),  # 0 dome panels (grey median 7; one step darker: the lit dome read silver in game)
        mat(sprite, 5, t, metallic=0.55, roughness=0.42),       # 1 panel seams / dark rim
        mat(sprite, 3, t, metallic=0.5, roughness=0.5),         # 2 skirt under the rim
        mat(sprite, 122, t + "-lamp", metallic=1.0, roughness=0.85, glow=1.2, frames={117: 121, 119: 120}),  # 3 nose lamp
        mat(sprite, 119, t + "-core", metallic=1.0, roughness=0.85, glow=1.4, frames={117: 123, 119: 123}),  # 4 core
        mat(sprite, 125, t + "-hot", metallic=1.0, roughness=0.85, glow=1.0, frames={117: 126, 119: 127}),  # 5 core centre
        mat(sprite, 22, t, metallic=0.2, roughness=0.45),       # 6 brown crossbar / struts (median 22)
        mat(sprite, 19, t, metallic=0.2, roughness=0.5),        # 7 dark brown: joints, hook tips
        mat(sprite, 114, t, metallic=0.4, roughness=0.45),      # 8 dark red lamp bezel / core socket
    ]


def dome_body(M):
    PAN, SEAM, SKIRT, LAMP, CORE, HOT, BAR, BDARK, BEZ = range(9)
    # Dome: in plan a D (round nose at row 3, straight back edge at row 11.6, 19 px wide), its crown
    # high over the middle. Lofted across v; three panels split by two shallow seams (columns 9, 15).
    rings = []
    # plan: the sprite's ogive nose (half width = v + 1 from row 1 to row 8), then straight sides
    half = pchip([1.0, 1.3, 2.0, 3.5, 5.5, 7.5, 8.6, 9.4, 10.5, 13.4], [0.0, 2.0, 3.0, 4.5, 6.45, 8.3, 9.05, 9.3, 9.35, 9.35])
    crown = pchip([1.0, 1.3, 2.0, 3.5, 5.5, 7.5, 8.6, 9.4, 10.5, 11.7, 13.4], [3.4, 4.2, 5.1, 6.4, 7.4, 7.9, 8.0, 7.8, 7.0, 5.6, 3.6])
    NS = 26
    bands = []
    vv = [1.0 + (13.4 - 1.0) * i / 38 for i in range(39)]
    for i, v in enumerate(vv):
        hw = half(v)
        zt = crown(v)
        base = 2.6
        if hw < 1e-3:
            rings.append([(D_AXIS, v, base + 0.6 * (zt - base))])
            continue
        ring = []
        for kk in range(NS + 1):
            a = math.pi * kk / NS  # 0..pi over the top, from +u to -u
            c, s = se(a, 2.3)
            u = D_AXIS + hw * c
            z = base + (zt - base) * s
            # Panel seams: a shallow V groove at |u - axis| = 3.2 px.
            g = abs(abs(u - D_AXIS) - 3.2)
            if g < 0.45 and s > 0.3 and hw > 5.0:
                z -= 0.28 * (1 - g / 0.45)
            ring.append((u, v, z))
        # Close the cross-section along the underside (a flat-ish belly at z = base - 0.6).
        for kk in range(1, 6):
            u = D_AXIS - hw + 2 * hw * kk / 6
            ring.append((u, v, base - 0.6))
        rings.append(ring)
    for i in range(1, len(rings)):
        bands.append(PAN)
    fs = M.loft(rings, bands, cap0=False, cap1=True)
    for f in fs:
        cen = f.calc_center_median()
        if abs(abs(cen.x - D_AXIS) - 3.2) < 0.32 and cen.z > 4:
            f.material_index = SEAM
        if cen.z < 2.6:
            f.material_index = SKIRT
    # Dark rim band round the dome's foot (the sprite's rows 10-11): a chamfered lip at z 2.6-3.6.
    rim = []
    for v, hw in ((9.6, 9.25), (10.2, 9.45), (12.9, 9.45), (13.5, 9.25)):
        rim.append([(D_AXIS + hw * math.cos(math.pi * kk / 20), v, 2.4 + 1.5 * math.sin(math.pi * kk / 20)) for kk in range(21)]
                   + [(D_AXIS - hw + 2 * hw * kk / 4, v, 2.2) for kk in range(1, 4)])
    M.loft(rim, SEAM)
    # Nose lamp: a glowing lens set in a dark red bezel on the dome's nose (rows 0-2, columns 9-15).
    M.lathe([(1.05, 0.0), (1.2, 1.3), (1.6, 2.1), (2.3, 2.7), (3.1, 2.9), (3.7, 2.6), (4.0, 0.0)],
            D_AXIS, 4.6, sides=18, rz=0.7, mat=BEZ)
    M.lathe([(1.15, 0.0), (1.3, 1.0), (1.7, 1.75), (2.3, 2.2), (3.0, 2.35), (3.5, 2.0), (3.7, 0.0)],
            D_AXIS, 5.1, sides=18, rz=0.72, mat=LAMP)
    # Crossbar (rows 13-17, columns 3-21): a brown beam with chamfered ends, slightly arched.
    st = [(3.0, 0.0, 0.0, 15.6), (3.1, 1.9, 1.6, 15.6), (3.5, 2.25, 2.1, 15.6), (9.6, 2.3, 2.3, 15.6), (10.6, 1.95, 2.2, 15.2),
          (14.4, 1.95, 2.2, 15.2), (15.4, 2.3, 2.3, 15.6), (21.5, 2.25, 2.1, 15.6), (21.9, 1.9, 1.6, 15.6), (22.0, 0.0, 0.0, 15.6)]
    rings = []
    for u, hv, hz, cv in st:
        if hv < 1e-3:
            rings.append([(u, cv, 3.4)])
        else:
            rings.append([(u, cv + hv * se(2 * math.pi * kk / 16, 3.0)[0], 3.4 + hz * se(2 * math.pi * kk / 16, 3.0)[1])
                          for kk in range(16)])
    M.loft(rings, BAR, cap0=False, cap1=False)
    # Dark sockets at the bar's ends (the sprite's 16s at columns 4-5).
    for u in (4.6, 20.4):
        M.lathe([(13.4, 0.0), (13.5, 0.75), (14.6, 0.75), (14.7, 0.0)], u, 5.3, sides=10, rz=0.6, mat=BDARK)
    # Core: a glowing emitter (rows 12-16, columns 10-14) in a dark red socket on the bar's middle.
    M.pod([(11.6, D_AXIS, 4.8, 0.0, 0.0), (12.0, D_AXIS, 4.8, 2.3, 2.2), (16.4, D_AXIS, 4.6, 2.6, 2.4),
           (16.9, D_AXIS, 3.8, 0.0, 0.0)], BEZ, sides=16)
    M.pod([(11.8, D_AXIS, 6.0, 0.0, 0.0), (12.1, D_AXIS, 6.1, 2.05, 1.6), (16.0, D_AXIS, 6.0, 2.2, 1.6),
           (16.5, D_AXIS, 5.9, 0.0, 0.0)], CORE, sides=16)
    M.pod([(13.1, D_AXIS, 7.2, 0.0, 0.0), (13.4, D_AXIS, 7.25, 0.85, 0.7), (15.2, D_AXIS, 7.2, 0.9, 0.7),
           (15.5, D_AXIS, 7.1, 0.0, 0.0)], HOT, sides=12)


HOOK_CURL = (0.0, 1.0, 2.2)  # px the hook's tip curls in over the frames


def dome_hooks(M, k):
    PAN, SEAM, SKIRT, LAMP, CORE, HOT, BAR, BDARK, BEZ = range(9)
    c = HOOK_CURL[k]
    # Left strut: down columns 8-9 from the bar (row 17) to row 25, then a thick fluke curling out
    # and up to the tip (column 1-2, row 21 on frame 115).
    pts = [(2.5 + c, 20.7 + 0.15 * c, 2.2, 0.55), (2.75 + c, 22.0, 2.0, 1.0), (3.5 + 0.8 * c, 23.8, 1.9, 1.6 - 0.15 * c),
           (5.6 + 0.4 * c, 24.85, 1.9, 2.1 - 0.15 * c), (7.8, 24.6, 2.0, 2.1), (9.3, 23.0, 2.2, 1.85), (9.3, 21.4, 2.5, 1.85),
           (9.3, 20.2, 2.8, 1.5), (8.9, 18.6, 3.0, 1.45), (9.0, 17.0, 3.3, 1.2)]
    for side in (1, -1):
        p = pts if side > 0 else [(2 * D_AXIS - u, v, z, w) for u, v, z, w in pts]
        M.sweep(p, (BAR, BDARK, BDARK), sides=10, collars=(6.9,), claw=0.6, taper=1.0, hh_k=1.2, n=2.6)


def build_dome():
    sprite = common.load_sprite(WT, "newsh8-115")
    coll = common.reset_collection("newsh8-115")
    mats = dome_mats(sprite)
    xf = xform(24, 28)
    M = Mesh()
    dome_body(M)
    body = M.to_object("newsh8-115", mats, coll, xf)
    objs = [body]
    for k, fr in enumerate(D_FRAMES):
        M = Mesh()
        dome_hooks(M, k)
        h = M.to_object(f"newsh8-115-hooks-{fr}", mats, coll, xf)
        objs.append(common.frame_part(h, [fr]))
        whole = join([body, h], f"dome_sealed_{fr}", coll)
        sh = shell_multi(whole, coll, voxel=0.010, faces=4000, smooth=4, inside=0.004)
        sh.name = sh.data.name = f"newsh8-115_outline-{fr}"
        objs.append(common.frame_part(sh, [fr]))
        bpy.data.objects.remove(whole, do_unlink=True)
    return [("newsh8-115", objs, D_FRAMES, (0.0, 0.0))]


# =================================================================================================
# (4) The carrot newsh8-129
# =================================================================================================

def build_carrot():
    sprite = common.load_sprite(WT, "newsh8-129")
    coll = common.reset_collection("newsh8-129")
    t = "nsh8_129A"
    mats = [
        mat(sprite, 121, t, metallic=0.05, roughness=0.75, spec=0.12, glow=0.3),  # 0 orange body (median 121; 30% glow keeps its hue, D126)
        mat(sprite, 120, t, metallic=0.05, roughness=0.75, spec=0.12, glow=0.2),    # 1 growth-ring grooves
        mat(sprite, 197, t, metallic=0.05, roughness=0.55),   # 2 leaves (median ~197)
        mat(sprite, 194, t, metallic=0.05, roughness=0.6),    # 3 leaf stems / dark leaf
        mat(sprite, 182, t, metallic=0.5, roughness=0.35),    # 4 brown porthole rim (median 182)
        mat(sprite, 176, t, metallic=0.3, roughness=0.5),     # 5 dark porthole inside
        mat(sprite, 126, t + "-light", metallic=1.0, roughness=0.85, glow=1.0),  # 6 yellow light
    ]
    BODY, RING, LEAF, STEM, RIM, HOLE, LIGHT = range(7)
    AX = 12.5
    M = Mesh()
    # Body: round in section (lying on the ground), widest at row 12, a point at row 27.
    prof = [(8.95, 0.0), (9.1, 1.8), (9.5, 2.9), (10.5, 4.4), (11.5, 5.3), (13.0, 5.45), (14.5, 5.2), (16.5, 4.4),
            (19.5, 3.4), (22.0, 2.4), (24.0, 1.45), (25.5, 0.65), (26.6, 0.3), (27.0, 0.0)]
    f = pchip([p[0] for p in prof], [p[1] for p in prof])
    grooves = (11.0, 14.2, 19.6, 22.4, 24.6)
    lat = []
    vv = [8.95 + (27.0 - 8.95) * i / 60 for i in range(61)]
    for v in vv:
        r = f(v)
        for g in grooves:
            r *= 1 - 0.07 * max(0.0, 1 - abs(v - g) / 0.35)
        lat.append((v, r))
    def ring_mat(v):
        return RING if any(abs(v - g) < 0.3 for g in grooves) else BODY
    M.lathe(lat, AX + 0.0, 5.0, sides=24, rz=0.92, mats_of=ring_mat)
    # Porthole (rows 14-18, columns 10-14) on top of the body: brown rim, dark well, small light.
    cz = 5.0 + 4.95 * 0.92
    PV = 16.5
    rim = []
    def surf(u, v):  # the body's top surface under (u, v)
        R = f(v)
        return 5.0 + 0.92 * math.sqrt(max(0.0, R * R - (u - AX) ** 2))
    for r, dz in ((2.45, -0.6), (2.5, 0.1), (2.15, 0.4), (1.6, 0.3), (1.4, -0.1)):
        ring = []
        for kk in range(20):
            u, v = 12.5 + r * math.cos(2 * math.pi * kk / 20), PV + r * math.sin(2 * math.pi * kk / 20)
            ring.append((u, v, surf(u, v) + dz))
        rim.append(ring)
    M.loft(rim, RIM, cap0=False, cap1=False)
    M.loft([[(12.5 + 1.45 * math.cos(2 * math.pi * kk / 20), PV + 1.45 * math.sin(2 * math.pi * kk / 20), cz - 0.05) for kk in range(20)],
            [(12.5 + 1.45 * math.cos(2 * math.pi * kk / 20), PV + 1.45 * math.sin(2 * math.pi * kk / 20), cz - 0.6) for kk in range(20)]],
           HOLE, cap0=False, cap1=True)
    M.pod([(PV - 0.75, 12.5, cz - 0.3, 0.0, 0.0), (PV - 0.5, 12.5, cz - 0.25, 0.65, 0.45), (PV + 0.5, 12.5, cz - 0.25, 0.65, 0.45),
           (PV + 0.75, 12.5, cz - 0.3, 0.0, 0.0)], LIGHT, sides=12)
    # Leaf tuft: a stem collar on the crown and three blades fanning up the screen (rows 0-8).
    M.lathe([(7.9, 0.0), (8.0, 1.3), (9.0, 1.5), (9.4, 0.0)], AX, 5.0, sides=12, rz=0.9, mat=STEM)
    blades = [
        [(11.6, 0.5, 7.4, 0.0), (11.7, 1.8, 7.3, 0.65), (12.2, 3.5, 6.9, 1.2), (12.4, 5.5, 6.3, 1.3), (12.5, 8.6, 5.4, 0.9)],
        [(6.7, 1.2, 6.8, 0.0), (7.4, 3.0, 6.7, 0.8), (8.8, 5.0, 6.3, 1.0), (10.4, 6.3, 5.9, 0.9), (11.8, 7.9, 5.4, 0.7)],
        [(16.6, 3.5, 6.6, 0.0), (15.0, 4.3, 6.5, 0.8), (13.6, 5.3, 6.2, 0.9), (12.8, 6.6, 5.9, 0.8), (12.6, 8.0, 5.4, 0.7)],
    ]
    for b in blades:
        # a leaf blade: flat (wide in u, thin in z) with a ridge
        M.sweep([(u + 0.0, v, z, w) for u, v, z, w in b], (LEAF, STEM, LEAF), sides=10, taper=1.6, hh_k=0.45,
                claw=0.0, n=2.0)
    obj = M.to_object("newsh8-129", mats, coll, xform(24, 28))
    sh = shell_multi(obj, coll, voxel=0.010, faces=3000, smooth=4, inside=0.004)
    return [("newsh8-129", [obj, sh], [129], (0.0, 0.0))]


# =================================================================================================
# (2) The rock pod and its worm (assembly-newsh8-9)
# =================================================================================================

UPPER, LOWER = "newsh8-9", "newsh8-87"
WORM_MODELS = [
    ("newsh8-9", UPPER, [9, 11], True),
    ("newsh8-9-f2", UPPER, [13], True),
    ("newsh8-9-f3", UPPER, [15], True),
    ("newsh8-9-f4", UPPER, [17], True),
    ("newsh8-9-f5", UPPER, [47], True),
    ("newsh8-9-f6", UPPER, [49, 51], True),
    ("newsh8-9-f7", UPPER, [53, 55], True),
    ("newsh8-9-f8", UPPER, [85], False),
    ("newsh8-87", LOWER, [87], False),
    ("newsh8-87-f2", LOWER, [89], False),
    ("newsh8-87-f3", LOWER, [91], False),
    ("newsh8-87-f4", LOWER, [93, 123], False),
]


def inner_mask(name, frame):
    idx, colors = SM.load(name, frame)
    return SM.masks(idx, colors)["inner"], idx


class FGrid(RK.Grid):
    """lib_newshd_rock.Grid for one given frame's inner mask."""

    def __init__(self, inner, w=24, h=28):
        self.w, self.h = w, h
        self.inner = inner


def mask_solid(inner, top_fn, bot_fn, step=0.25, smooth_iter=3, grow=0.15):
    """A closed rock solid over a mask: rows of the mask's (smoothed) field sampled every `step` px,
    each sample column extruded from bot_fn(u, v, d) to top_fn(u, v, d) (d: distance in px to the
    mask edge), welded into one closed grid mesh with the rim walls. Returns a Mesh."""
    h, w = len(inner), len(inner[0])

    def val(c, r):
        return 1.0 if 0 <= r < h and 0 <= c < w and inner[r][c] else 0.0

    def field(u, v):
        a, b = u - 0.5, v - 0.5
        c0, r0 = math.floor(a), math.floor(b)
        fa, fb = a - c0, b - r0
        return ((1 - fa) * (1 - fb) * val(c0, r0) + fa * (1 - fb) * val(c0 + 1, r0)
                + (1 - fa) * fb * val(c0, r0 + 1) + fa * fb * val(c0 + 1, r0 + 1))
    nu, nv = int(w / step) + 1, int(h / step) + 1
    F = [[field(i * step, j * step) for i in range(nu)] for j in range(nv)]
    # distance-to-edge (px), by a cheap chamfer pass on the sample grid
    INF = 1e9
    D = [[0.0 if F[j][i] < 0.5 - grow else INF for i in range(nu)] for j in range(nv)]
    for _ in range(2):
        for j in range(nv):
            for i in range(nu):
                if D[j][i] == 0:
                    continue
                best = D[j][i]
                for dj, di, dd in ((-1, 0, 1), (0, -1, 1), (-1, -1, 1.414), (-1, 1, 1.414)):
                    jj, ii = j + dj, i + di
                    if 0 <= jj < nv and 0 <= ii < nu:
                        best = min(best, D[jj][ii] + dd * step)
                D[j][i] = best
        for j in reversed(range(nv)):
            for i in reversed(range(nu)):
                if D[j][i] == 0:
                    continue
                best = D[j][i]
                for dj, di, dd in ((1, 0, 1), (0, 1, 1), (1, 1, 1.414), (1, -1, 1.414)):
                    jj, ii = j + dj, i + di
                    if 0 <= jj < nv and 0 <= ii < nu:
                        best = min(best, D[jj][ii] + dd * step)
                D[j][i] = best
    # the picture's edge counts as the rock's edge too (a little way out), so no flat cut walls
    for j in range(nv):
        for i in range(nu):
            if D[j][i] > 0:
                u, v = i * step, j * step
                D[j][i] = min(D[j][i], u + 0.15, w - u + 0.15, v + 0.15, h - v + 0.15)
    M = Mesh()
    bm = M.bm
    top, bot = {}, {}
    for j in range(nv):
        for i in range(nu):
            if D[j][i] > 0:
                u, v = i * step, j * step
                d = D[j][i]
                top[(i, j)] = bm.verts.new((u, v, top_fn(u, v, d)))
                bot[(i, j)] = bm.verts.new((u, v, bot_fn(u, v, d)))
    faces = []
    for (i, j) in list(top):
        q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        if all(k in top for k in q):
            faces.append(bm.faces.new([top[k] for k in q]))
            faces.append(bm.faces.new([bot[k] for k in reversed(q)]))
    # walls along the boundary edges of the quad set
    quads = {(i, j) for (i, j) in top if all(k in top for k in [(i + 1, j), (i + 1, j + 1), (i, j + 1)])}
    edges = {}
    for (i, j) in quads:
        for a, b in (((i, j), (i + 1, j)), ((i + 1, j), (i + 1, j + 1)), ((i + 1, j + 1), (i, j + 1)), ((i, j + 1), (i, j))):
            key = (min(a, b), max(a, b))
            edges[key] = edges.get(key, 0) + 1
            edges.setdefault(("dir",) + key, (a, b))
    for key, n in list(edges.items()):
        if key[0] == "dir" or n != 1:
            continue
        a, b = edges[("dir",) + key]
        faces.append(bm.faces.new([top[b], top[a], bot[a], bot[b]]))
    # remove verts not used
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # relax the rim (the staircase of the sample grid) toward the 0.5 contour
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for _ in range(smooth_iter):
        bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if v.is_boundary or any(len(e.link_faces) != 2 for e in v.link_edges) or
                                         any(f.normal.z < 0.3 and f.normal.z > -0.3 for f in v.link_faces)],
                              factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=False)
    for f in bm.faces:
        f.smooth = False
    return M


def noise2(u, v, seed, scale=3.0):
    from mathutils import noise
    return noise.noise(Vector((u / scale + seed * 13.1, v / scale - seed * 7.3, seed * 0.37)))


def pod_solid(base_rows, inner):
    """The empty pod husk (frame 9's inner mask): a rock rim round a pit, fangs on the lower lip.
    Height from the sprite's own drawing: the pit (palette 16-18, dark) sinks into a bowl."""
    dark = [[1 if (inner[r][c] and base_rows[r][c] <= 18) else 0 for c in range(24)] for r in range(28)]

    def darkness(u, v):  # blurred pit mask 0..1
        acc = n = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                r, c = int(v) + dr, int(u) + dc
                if 0 <= r < 28 and 0 <= c < 24:
                    acc += dark[r][c] * (2 if dr == dc == 0 else 1)
                    n += 2 if dr == dc == 0 else 1
        return acc / n if n else 0

    def top(u, v, d):
        rim = min(1.0, d / 2.6) ** 0.55
        z = 0.2 + 5.6 * rim + 0.9 * rim * noise2(u, v, 1, 2.2) + 1.1 * (1 - rim) * noise2(u, v, 5, 1.3)
        if v > 16:  # the fangs taper to their points
            z -= 0.12 * (v - 16)
        z -= 5.2 * darkness(u, v) * min(1.0, d / 1.5)
        return max(z, 0.25)

    def bot(u, v, d):
        return -0.2 - 3.2 * min(1.0, d / 3.5) ** 0.7 + 0.6 * noise2(u, v, 9, 1.5)
    return pod_solid_mesh(mask_solid(inner, top, bot, step=0.5, smooth_iter=2))


def pod_solid_mesh(M):
    return M


def worm_rows(pixels, base):
    """Per row, the widest run of the worm's pixels (those that differ from the empty pod `base`,
    or every coloured pixel without one), allowing 1 px gaps: {row: (lo, hi)} (copied from the
    current script)."""
    rows = {}
    for r, line in enumerate(pixels):
        cols = [c for c, v in enumerate(line) if v > 1 and (base is None or v != base[r][c])]
        groups = []
        for c in cols:
            if groups and c - groups[-1][-1] <= 2:
                groups[-1].append(c)
            else:
                groups.append([c])
        if groups:
            g = max(groups, key=lambda g: g[-1] - g[0])
            if g[-1] - g[0] >= 1:
                rows[r] = (g[0], g[-1])
    return rows


def worm_loft(M, pixels, base, z_of_row, extend_top=False, extend_bot=False, seed=3, sides=14, mat_i=0, inner=None):
    """A lumpy rock-worm loft following the frame's worm outline (row widths), faired by pchip."""
    rows = worm_rows(pixels, base)
    if inner is not None:  # a worm alone: its inner mask (inside the ink ring) is its outline
        rows = worm_rows([[2 if m else 0 for m in r] for r in inner], None)
    if not rows:
        return []
    rs = sorted(rows)
    runs, cur = [], [rs[0]]
    for r in rs[1:]:
        if r - cur[-1] <= 2:
            cur.append(r)
        else:
            runs.append(cur)
            cur = [r]
    runs.append(cur)
    rs = max(runs, key=len)
    if len(rs) < 2:
        return []
    sec = []
    for i, r in enumerate(rs):
        near = [rows[q] for q in rs[max(0, i - 1):i + 2]] if inner is None else [rows[r]]
        lo = sum(a for a, _ in near) / len(near)
        hi = sum(b for _, b in near) / len(near)
        sec.append((r + 0.5, (lo + hi + 1) / 2, (hi - lo + 1) / 2))
    v0, c0, w0 = sec[0]
    v1, c1, w1 = sec[-1]
    start = [(v0 - 3.5, c0, w0)] if extend_top else [(v0 - 0.55, c0, w0 * 0.55), (v0 - 0.75, c0, 0.0)]
    end = [(v1 + 3.5, c1, w1)] if extend_bot else [(v1 + 0.35, c1, w1 * 0.6), (v1 + 0.55, c1, 0.0)]
    sec = start + sec + end
    if not extend_top:
        sec = [sec[1], sec[0]] + sec[2:]
        sec = sorted(sec, key=lambda s: s[0])
    vs = [s[0] for s in sec]
    fc = pchip(vs, [s[1] for s in sec])
    fw = pchip(vs, [s[2] for s in sec])
    rnd = random.Random(seed)
    cnt = max(3, int((vs[-1] - vs[0]) / 0.5))
    rings = []
    for i in range(cnt + 1):
        v = vs[0] + (vs[-1] - vs[0]) * i / cnt
        w = max(0.0, fw(v))
        c = fc(v)
        z = z_of_row(v)
        if w < 0.05 or ((i == 0 and not extend_top) or (i == cnt and not extend_bot)):
            rings.append([(c, v, z)])
            continue
        hz = min(4.0, w * 0.85)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            lump = 1 + 0.10 * noise2(c + math.cos(a) * 3, v, seed, 1.6)
            ring.append((c + w * math.cos(a) * lump, v, z + hz * math.sin(a) * lump))
        rings.append(ring)
    return M.loft(rings, mat_i, cap0=extend_top, cap1=extend_bot)


def rock_mats(sprite, tag):
    return [mat(sprite, 22, tag, metallic=0.05, roughness=0.72),   # 0 rock mid (the facet ramp's median)
            mat(sprite, 16, tag, metallic=0.0, roughness=0.9)]     # 1 the pit's depth


def worm_z_upper(v):
    """Out of the pit (rows 4-9) and up over the lower lip."""
    return -0.5 + 4.4 * smoothstep(3.0, 13.0, v)


def facet(obj, sprite_rows, inner, sprite_colors, mid=22, faces=None):
    sp = {"name": "x", "colors": sprite_colors, "frames": [{"pixels": [" ".join(str(v) for v in r) for r in sprite_rows]}]}
    sp["frames"][0]["pixels"] = sprite_rows
    g = FGrid(inner)
    RK.facet_ramp(sp, g, obj, {"mid": mid, "metallic": 0.05, "roughness": 0.72}, faces=faces, mid=mid, slot=0)


def build_worm():
    up = common.load_sprite(WT, UPPER)
    lo = common.load_sprite(WT, LOWER)
    colors = {**up["colors"], **lo["colors"]}
    sprite = dict(up)
    sprite["colors"] = colors
    base = load_rows(UPPER, 9)
    base_inner, _ = inner_mask(UPPER, 9)
    out = []
    for name, piece, frames, with_pod in WORM_MODELS:
        coll = common.reset_collection(name)
        tag = "nsh8_9A"
        objs = []
        xf = xform(24, 28)
        animated = len(frames) > 1
        pod_obj = None
        if with_pod:
            M = pod_solid(base, base_inner)
            pod_obj = M.to_object(name if not animated else f"{name}-pod", rock_mats(sprite, tag), coll, xf, smooth_angle=30)
            facet(pod_obj, base, base_inner, colors)
            objs.append(pod_obj)
        worms = []
        for f in frames:
            if with_pod and f == 9:
                continue
            rows = load_rows(piece, f)
            inner, _ = inner_mask(piece, f)
            M = Mesh()
            if with_pod:
                px = rows if f != 11 else [line if r <= 11 else base[r] for r, line in enumerate(rows)]
                wr = worm_rows(px, base)
                worm_loft(M, px, base, worm_z_upper, seed=f, extend_bot=bool(wr) and max(wr) >= 26)
            elif piece == UPPER:
                worm_loft(M, rows, None, lambda v: 3.9, seed=f, extend_bot=True, inner=inner)
            else:
                worm_loft(M, rows, None, lambda v: 3.9, seed=f, extend_top=True, inner=inner)
            if not M.bm.faces:
                continue
            wo = M.to_object(f"{name}-worm-{f}", rock_mats(sprite, tag), coll, xf, smooth_angle=30)
            # cut to the 24x28 box (the lower piece's worm runs up past row 0, the f8 worm down past row 27)
            cutd = common.split_assembly(wo, [(f"{name}-worm-{f}c", 0, 0)], coll)[f"{name}-worm-{f}c"]
            bpy.data.objects.remove(wo, do_unlink=True)
            cutd.name = cutd.data.name = f"{name}-worm-{f}"
            facet(cutd, rows, inner, colors)
            if f == 11:
                for p in cutd.data.polygons:
                    p.material_index = 1  # the dim tip deep in the pit
            worms.append((f, cutd))
        if animated or not with_pod:
            for f, wo in worms:
                objs.append(common.frame_part(wo, [f]) if animated else wo)
        else:
            objs += [wo for _, wo in worms]
        # outlines: per frame a sealed whole (pod + that frame's worm), cut to the box, open seams
        for f in frames:
            parts = ([pod_obj] if pod_obj else []) + [wo for ff, wo in worms if ff == f]
            if not parts:
                continue
            whole = join(parts, f"{name}_sealed_{f}", coll)
            sh = shell_multi(whole, coll, voxel=0.016, faces=3000, smooth=6, inside=0.004)
            sh2 = cut_open(sh, [(name, 0, 0)], coll, f"-{f}")[name]
            for o in (whole, sh):
                bpy.data.objects.remove(o, do_unlink=True)
            sh2.data.materials.clear()
            sh2.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
            objs.append(common.frame_part(sh2, [f]) if animated else sh2)
        for o in objs:
            if not o.get("tyrian_outline"):
                RK.set_facet_normals(o)
        out.append((name, objs, frames, (0.0, 0.0)))
    return out


# =================================================================================================

def sprites_for(name, frames):
    base = re.sub(r"-f\d$", "", name)
    sp = common.load_sprite(WT, base)
    out = []
    for s in sp["sprites"]:
        keep = [f for f in s["frames"] if f in frames]
        if keep:
            out.append({**s, "frames": keep})
    return out


def main(only=None):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    only = only or arg("--only", "spider")
    builders = {"spider": build_spider, "dome": build_dome, "carrot": build_carrot, "worm": build_worm}
    models = []
    for key, fn in builders.items():
        if only and key not in only.split(","):
            continue
        models += fn()
    manifest = {}
    allobjs = []
    for name, objs, frames, off in models:
        for o in objs:
            o["design_model"] = name
            if o.type == "MESH" and o.get("tyrian_outline"):
                assert len(o.data.polygons) > 0, f"{o.name}: empty outline shell"
        manifest[name] = {"frames": frames, "offset": off, "objects": [o.name for o in objs],
                          "tris": sum(len(p.vertices) - 2 for o in objs if not o.get("tyrian_outline") for p in o.data.polygons),
                          "shells": {o.name: len(o.data.polygons) for o in objs if o.get("tyrian_outline")}}
        allobjs += objs
    for name, objs, frames, _ in models:
        common.export_sprite_model(WT, objs, f"enemies/{name}", sprites_for(name, frames))
    design = arg("--design")
    if design:
        for name, objs, _, off in models:
            for o in objs:
                o.location.x += off[0]
                o.location.y += off[1]
        common.export_glb(allobjs, Path(design))
    mf = arg("--manifest")
    if mf:
        Path(mf).write_text(json.dumps(manifest, indent=1))
    print("MANIFEST", json.dumps({k: (v["tris"], len(v["shells"])) for k, v in manifest.items()}))


if __name__ == "__main__":
    main()
