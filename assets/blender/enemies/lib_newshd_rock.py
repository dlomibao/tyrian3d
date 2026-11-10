"""The newshd.shp asteroids' rock builder (newshd-95, -152, -114, -133, -5, -18, -43; D121, D122).

An asteroid floats in space, so it is round all over: a body lofted from the sprite's inner mask
(inside its ink ring, D74), its top raised into the summit, ridges and lumps the sprite draws and
its underside a plain closed dome, then broken by planar fracture faces (crisp, chamfered edges:
on rock a highlight is a lit face, not sheen), crack grooves and impact pits. Matte palette
materials (the sprite's mid-tone per region; its ink ring, dark limb and white glints are its
lighting), an AO/roughness bake (no concept projection, D50/D65) and an outline shell (D51) made
from a closed copy kept out of the bake (D118).

A model script gives a SPEC (keys below) and calls `main(NAME, SPEC)`:

    mid          rock palette index (material 0); `metallic`, `roughness` (default 0.05, 0.72)
    h_top/h_bot  height of the summit above the waist / depth of the underside below it (units;
                 12 sprite px = 1 unit)
    summit       (column, row) in sprite px: where the top peaks
    summit_gain  extra summit height (fraction of h_top), a Gaussian 2.4 px wide (`summit_r`)
    ridges       [((col, row) end, gain, width px)]: lit crests from the summit
    bumps        [((col, row), gain, radius px)]: lumps (gain > 0) and dents (< 0) on the top
    crests       [((col, row), (col, row), gain, width px)]: lumps along a segment (a lit strip)
    valleys      [([(col, row), ...], gain, width px)]: a crease (gain < 0) or ridge along a
                 polyline, by the distance to its nearest segment (no doubling at the joints)
    sectors, rings_top, rings_bot   the loft's resolution (default 64, 16, 8)
    steps, smooth  the outline trace: rays from the mask's centroid (default 72) and smoothing
                 passes (default 2)
    tilt         how far the top falls away to the right (fraction of h_top per 5 px)
    lumps        noise amplitude on the top; `waist`: how far the widest line wanders in height
    grow         px the body is grown past the inner mask (the rim spalls cut it back)
    seed, fine   noise seed; number of small extra fracture faces (fine_cuts)
    fine_depth   (lo, hi) depth fractions of the fine cuts (default 0.035-0.06)
    rim_spalls   number of shallow spalls round the waist (fine_cuts), so it never reads as a belt;
                 `rim_depth` (lo, hi) their depth fractions (default 0.025-0.04)
    cuts         [(azimuth deg, elevation deg, depth fraction)]: fracture faces; azimuth 0 = +X
                 (screen right), 90 = +Y (screen up); negative elevation for the underside
    cracks       [([(col, row), ...], width, depth)]: V grooves along a polyline over the top
    pits         [((col, row), radius units)]: impact pits (`pit_lift`: the cutter ball's centre
                 above the surface, in radii; default 0.45)
    shell        outline_shell keywords (default D90's: 0.03 voxels, held 0.004 inside)
    bake_with_copy  True only for newshd-95: its shell's source copy stays in the scene during the
                 bake, as D121 built it (the coincident copy darkens its AO about 12%), so its glb
                 is unchanged

build-models.sh skips lib_ files; the model scripts import this next to them.

    blender -b --factory-startup -P assets/blender/enemies/<name>.py -- [--no-bake] [--out file.glb]
"""

import math
import random
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, noise
from mathutils.bvhtree import BVHTree

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import sprite_mask as SM  # noqa: E402

#: D90's outline shell: coarse voxels bridge the fracture edges and crack grooves, and the shell is
#: held a hair inside the rock so its back faces never draw ink across the top.
D90_SHELL = {"voxel": 0.03, "inside": 0.004, "faces": 1500, "smooth": 8}


# --- sprite grid ---------------------------------------------------------------------------------

class Grid:
    def __init__(self, sprite, name):
        f = sprite["frames"][0]
        self.w, self.h = f["width"], f["height"]
        idx, colors = SM.load(name, ref=WT / "reference" / "models")
        self.inner = SM.masks(idx, colors)["inner"]

    def x(self, u):  # sprite edge coordinate (column) -> Blender X
        return (u - self.w / 2) / 12

    def y(self, v):
        return (self.h / 2 - v) / 12

    def uv(self, x, y):
        return x * 12 + self.w / 2, self.h / 2 - y * 12

    def val(self, c, r):
        if 0 <= r < self.h and 0 <= c < self.w:
            return 1.0 if self.inner[r][c] else 0.0
        return 0.0

    def field(self, u, v):
        """Bilinear interpolation of the inner mask sampled at pixel centres: its 0.5 contour runs
        through the pixel edges and chamfers the staircase corners."""
        a, b = u - 0.5, v - 0.5
        c0, r0 = math.floor(a), math.floor(b)
        fa, fb = a - c0, b - r0
        return ((1 - fa) * (1 - fb) * self.val(c0, r0) + fa * (1 - fb) * self.val(c0 + 1, r0)
                + (1 - fa) * fb * self.val(c0, r0 + 1) + fa * fb * self.val(c0 + 1, r0 + 1))

    def outline(self, steps=72, grow=0.0, smooth=2):
        cells = [(c + 0.5, r + 0.5) for r in range(self.h) for c in range(self.w) if self.inner[r][c]]
        cu = sum(c for c, _ in cells) / len(cells)
        cv = sum(r for _, r in cells) / len(cells)
        radii = []
        for k in range(steps):
            a = 2 * math.pi * k / steps
            du, dv = math.cos(a), -math.sin(a)
            t, last = 0.0, 1.0
            while t < 30:
                f = self.field(cu + du * t, cv + dv * t)
                if f < 0.5:
                    t -= 0.02 * (0.5 - f) / max(1e-6, last - f)
                    break
                last = f
                t += 0.02
            radii.append(t + grow)
        for _ in range(smooth):
            radii = [(radii[k - 1] + 2 * radii[k] + radii[(k + 1) % steps]) / 4 for k in range(steps)]
        return cu, cv, radii


def radius_at(radii, ang):
    n = len(radii)
    t = (ang % (2 * math.pi)) / (2 * math.pi) * n
    k = int(t)
    f = t - k
    return radii[k % n] * (1 - f) + radii[(k + 1) % n] * f


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px_, py_ = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((px_ - ax) * dx + (py_ - ay) * dy) / L2)) if L2 else 0.0
    return math.hypot(px_ - ax - t * dx, py_ - ay - t * dy), t


# --- the rock ------------------------------------------------------------------------------------

def rock_body(g, spec, sectors=64, rings_top=16, rings_bot=8):
    cu, cv, radii = g.outline(steps=spec.get("steps", 72), grow=spec.get("grow", 0.0), smooth=spec.get("smooth", 2))
    su, sv = spec["summit"]
    ht, hb = spec["h_top"], spec["h_bot"]
    lump_off = Vector((spec["seed"] * 1.37, spec["seed"] * 0.61, 3.3))
    summit_r = spec.get("summit_r", 2.4)
    top_pow = spec.get("top_pow", 0.6)      # < 1: fuller shoulders (the side wall stands up)
    bot_pow = spec.get("bot_pow", 0.85)
    rise = spec.get("rise", 0.85)           # height profile exponents: < 1 a rounder dome
    fall = spec.get("fall", 0.95)

    def height_gain(u, v):
        """Extra height (fraction of h_top) of the top at sprite point (u, v)."""
        d = math.hypot(u - su, v - sv)
        gain = spec["summit_gain"] * math.exp(-(d / summit_r) ** 2)
        for (eu, ev), amp, wid in spec["ridges"]:
            dist, t = seg_dist((u, v), (su, sv), (eu, ev))
            gain += amp * (1 - 0.55 * t) * math.exp(-(dist / wid) ** 2)
        for (bu, bv), amp, rad in spec.get("bumps", []):
            gain += amp * math.exp(-(math.hypot(u - bu, v - bv) / rad) ** 2)
        for a, b, amp, wid in spec.get("crests", []):
            dist, _ = seg_dist((u, v), a, b)
            gain += amp * math.exp(-(dist / wid) ** 2)
        for pts, amp, wid in spec.get("valleys", []):
            dist = min(seg_dist((u, v), a, b)[0] for a, b in zip(pts, pts[1:]))
            gain += amp * math.exp(-(dist / wid) ** 2)
        gain -= spec["tilt"] * (u - cu) / 5.0
        return gain

    bm = bmesh.new()
    rings = []
    # Elevation params: bottom pole -> rim -> top pole.
    phis = [-math.pi / 2 + (math.pi / 2) * k / rings_bot for k in range(1, rings_bot)] + [0.0]
    phis += [(math.pi / 2) * k / rings_top for k in range(1, rings_top)]
    for phi in phis:
        ring = []
        for j in range(sectors):
            a = 2 * math.pi * j / sectors
            r = radius_at(radii, a)
            c = math.cos(phi)
            # superellipse: fuller shoulders than a sphere, so the side wall stands up; the top
            # rings close on the summit (off centre), the bottom ones on the outline's centre
            ru, rv = cu + r * math.cos(a), cv - r * math.sin(a)
            if phi > 0:
                s = c ** top_pow
                u, v = su + s * (ru - su), sv + s * (rv - sv)
            else:
                s = c ** bot_pow
                u, v = cu + s * (ru - cu), cv + s * (rv - cv)
            if phi >= 0:
                z = ht * math.sin(phi) ** rise
                z *= 1 + height_gain(u, v) * (math.sin(phi) ** 1.5)
            else:
                z = -hb * (-math.sin(phi)) ** fall
            p = Vector((g.x(u), g.y(v), z))
            # lumps: mostly vertical on the top, a hair radial off the rim
            nz = noise.noise(p * 4.0 + lump_off)
            if phi > 0:
                p.z += spec["lumps"] * nz * math.sin(phi) * ht * 2
            # the waist wanders up and down so it never reads as a saucer rim
            p.z += spec.get("waist", 0.0) * noise.noise(Vector((math.cos(a), math.sin(a), 0)) * 1.3 + lump_off) * math.cos(phi) ** 2
            ring.append(p)
        rings.append(ring)
    top = Vector((g.x(su), g.y(sv), ht * (1 + height_gain(su, sv))))
    bot_c = Vector((g.x(cu), g.y(cv), -hb))
    top.z += spec["lumps"] * noise.noise(top * 4.0 + lump_off) * ht * 2
    # loft
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    vb, vt = bm.verts.new(bot_c), bm.verts.new(top)
    for r0, r1 in zip(vr, vr[1:]):
        for j in range(sectors):
            k = (j + 1) % sectors
            bm.faces.new((r0[j], r0[k], r1[k], r1[j]))
    for j in range(sectors):
        k = (j + 1) % sectors
        bm.faces.new((vb, vr[0][k], vr[0][j]))
        bm.faces.new((vr[-1][j], vr[-1][k], vt))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm, (cu, cv)


def fine_cuts(spec):
    """Smaller fracture faces spread evenly (golden angle) over the top between the big ones, so
    hardly any of the weathered body is left between breaks."""
    rng = random.Random(spec["seed"])
    out = []
    for k in range(spec.get("fine", 0)):
        az = (k * 137.508 + rng.uniform(-12, 12)) % 360
        el = 30 + 45 * ((k * 0.618) % 1.0)
        lo, hi = spec.get("fine_depth", (0.035, 0.06))
        out.append((az, el, rng.uniform(lo, hi) * (1.25 if el > 50 else 1.0)))
    n = spec.get("rim_spalls", 0)
    for k in range(n):
        az = (360 * k / n + rng.uniform(-10, 10) + 17) % 360
        out.append((az, rng.uniform(-14, 16), rng.uniform(*spec.get("rim_depth", (0.025, 0.04)))))
    return out


def cut_planes(bm, cuts):
    """Fracture faces: slice a cap off along each plane and close it with one flat face."""
    for az, el, depth in cuts:
        a, e = math.radians(az), math.radians(el)
        n = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
        proj = [v.co.dot(n) for v in bm.verts]
        hi, lo = max(proj), min(proj)
        d = hi - depth * (hi - lo)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=n * d, plane_no=n, clear_outer=True)
        cut = [x for x in res["geom_cut"] if isinstance(x, bmesh.types.BMEdge)]
        if cut:
            new = bmesh.ops.holes_fill(bm, edges=cut, sides=0)
            for f in new["faces"]:
                f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def cutter_crack(g, bvh, pts_px, width, depth):
    """A V-section groove cutter following the polyline (sprite px) over the rock's top."""
    bm = bmesh.new()
    pts, nrms = [], []
    dense = []
    for (u0, v0), (u1, v1) in zip(pts_px, pts_px[1:]):
        for k in range(4):
            t = k / 4
            dense.append((u0 + (u1 - u0) * t, v0 + (v1 - v0) * t))
    dense.append(pts_px[-1])
    for u, v in dense:
        hit = bvh.ray_cast(Vector((g.x(u), g.y(v), 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        pts.append(hit[0])
        nrms.append(hit[1])
    rings = []
    for i, (p, n) in enumerate(zip(pts, nrms)):
        tdir = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = tdir.cross(n).normalized()
        nn = side.cross(tdir).normalized()
        taper = 1.0 if 0 < i < len(pts) - 1 else 0.35
        wv = width * taper * (0.75 + 0.25 * math.sin(i * 1.7))
        ring = [p - nn * depth * taper, p + side * wv / 2 + nn * 0.05, p - side * wv / 2 + nn * 0.05]
        rings.append([bm.verts.new(q) for q in ring])
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(3):
            k = (j + 1) % 3
            bm.faces.new((r0[j], r0[k], r1[k], r1[j]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def boolean(obj, cutter_bm, name, solver="EXACT"):
    me = bpy.data.meshes.new(name)
    cutter_bm.to_mesh(me)
    cutter_bm.free()
    cut = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(cut)
    bpy.context.view_layer.update()
    mod = obj.modifiers.new(name, "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = solver  # EXACT drops everything for the thin crack cutter; FLOAT cuts it cleanly
    mod.object = cut
    mod.use_hole_tolerant = True
    common._apply_modifiers(obj)
    bpy.data.objects.remove(cut)


def rock(sprite, name, spec, coll):
    """The rock object (one material, the spec's mid-tone) and the sprite grid it was traced on."""
    g = Grid(sprite, name)
    bm, centre = rock_body(g, spec, sectors=spec.get("sectors", 64), rings_top=spec.get("rings_top", 16),
                           rings_bot=spec.get("rings_bot", 8))
    cut_planes(bm, spec["cuts"] + fine_cuts(spec))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    mat = common.palette_material(sprite, spec["mid"], name, metallic=spec.get("metallic", 0.05),
                                  roughness=spec.get("roughness", 0.72))
    obj = common.mesh_object(name, bm, [mat], coll, smooth=True)
    # detail: crack grooves and impact pits, cut with booleans
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    for k, (pts, w, d) in enumerate(spec.get("cracks", [])):
        boolean(obj, cutter_crack(g, bvh, pts, w, d), f"crack{k}", solver="FLOAT")
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    for k, ((u, v), r) in enumerate(spec.get("pits", [])):
        hit = bvh.ray_cast(Vector((g.x(u), g.y(v), 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        cb = bmesh.new()
        bmesh.ops.create_uvsphere(cb, u_segments=12, v_segments=7, radius=r)
        c = hit[0] + hit[1] * r * spec.get("pit_lift", 0.45)  # higher: a shallower dish
        bmesh.ops.scale(cb, vec=(1, 1, 0.75), verts=cb.verts)
        bmesh.ops.translate(cb, vec=c, verts=cb.verts)
        boolean(obj, cb, f"pit{k}")
    # chamfer the fracture edges (one-segment bevel on sharp edges) and shade: smooth on the
    # weathered body, crisp along the breaks
    bev = obj.modifiers.new("chamfer", "BEVEL")
    bev.width = 0.006
    bev.segments = 1
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(28)
    common._apply_modifiers(obj)
    obj.data.shade_smooth()
    obj.data.set_sharp_from_angle(angle=math.radians(14))
    # a boolean cutter can leave an empty material slot behind: keep the rock's one material
    while len(obj.data.materials) > 1:
        obj.data.materials.pop()
    obj.data.materials[0] = mat
    for p in obj.data.polygons:
        p.material_index = 0
    return obj, mat, g


def main(name, spec, paint=None, parts=None, shell_extra=None):
    """Build, bake and export one asteroid.

    paint(sprite, grid, obj): optional; may append palette materials to obj and set polygon
    material indices (every rock material is baked). parts(sprite, grid, obj, coll): optional
    extra objects exported with the rock, not baked (a glowing vent). shell_extra(sprite, grid,
    obj, coll): optional closed objects joined into the shell's source with the rock."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(WT, name)
    coll = common.reset_collection(name)
    obj, mat, g = rock(sprite, name, spec, coll)
    if paint:
        paint(sprite, g, obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data)
    bm.free()
    tris = len(obj.data.polygons)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    open_edges = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    print(f"{name} {tris} triangles, non-manifold edges {open_edges}")
    # The shell's source: a sealed copy of the rock, kept out of the scene while the bake runs so
    # its occlusion rays never meet it (D118).
    closed = obj.copy()
    closed.data = obj.data.copy()
    if spec.get("bake_with_copy"):
        coll.objects.link(closed)
    extra = parts(sprite, g, obj, coll) if parts else []
    fmt = "AUTO"
    if "--no-bake" not in argv:
        hidden = [o for o in extra if o.name in coll.objects]
        for o in hidden:
            coll.objects.unlink(o)
        tint, textured = T.TINT, T.TEXTURED
        T.TINT, T.TEXTURED = (1.0, 1.0, 1.0), tuple(range(len(obj.data.materials)))
        try:
            T.bake_maps(obj, tempfile.mkdtemp(prefix=f"{name}_bake_"), size=512, samples=64)
        finally:
            T.TINT, T.TEXTURED = tint, textured
        for o in hidden:
            coll.objects.link(o)
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{name}_")
        fmt = "WEBP"
    if closed.name not in coll.objects:
        coll.objects.link(closed)
    if shell_extra:
        more = shell_extra(sprite, g, obj, coll)
        if more:
            for o in bpy.context.view_layer.objects:
                o.select_set(False)
            for o in [closed, *more]:
                o.select_set(True)
            bpy.context.view_layer.objects.active = closed
            bpy.ops.object.join()
    shell = common.outline_shell(closed, coll, **spec.get("shell", D90_SHELL))
    shell.name = shell.data.name = f"{name}_outline"
    bpy.data.objects.remove(closed)
    objs = [obj, *extra, shell]
    if out:
        common.export_glb(objs, out, image_format=fmt)
    else:
        common.export_sprite_model(WT, objs, f"enemies/{name}", sprite["sprites"], image_format=fmt)
    return obj
