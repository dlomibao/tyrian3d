"""newshd-228: merging ice orbs (newshd.shp size 1, frames 228/247/266/285/304; 12 x 14 px).

Reading of the sprite (tools/calibration/rubric.md, "Reading a sprite"):
- Each orb is 6 x 6 px with its ink ring; inside the ring a 4 x 4 px round body (rows 5-8). The
  pale 60/62 pixels on the upper left are the glint (sheen) and the 55/57 lower right the shadow
  side: lighting, so the body is one colour, 59 (the median of the body ignoring both ends).
- 228: two orbs apart (centres on column edges 3 and 9). 247: they touch (no ink between them on
  rows 6-7: the bodies meet). 285: one orb (centre 6).
- 266 / 304: the orbs squeezed into one lumpy 6 x 4 px body (cols 3-8) with a dark seam down it.
  266: the left lobe is the big one (glint col 4), the seam bows right (cols 6-7, 54/53/51) and the
  small right lobe sits in shadow (56/54). 304: the mirror: a small lit left lobe (60), the seam at
  col 5 (55/51) and the big right lobe with the glint at col 6. Read as geometry: the two lobes
  trade sizes as the blob wobbles, so each frame gets its own body (common.frame_part) with the
  crease where the sprite draws the seam; the light then puts the sheen on the big lobe itself.

Model: each stage is a metaball field (round lobes that fuse smoothly as they close in, which is
what the sprite shows), converted to a mesh. Ice-glass material: palette 59, low roughness, a little
metallic for a cold satin sheen. The fused seam is a real crease (the saddle between the lobes)
with the sprite's seam index (53 on 266, 55 on 304) as a bead lying in it from ground to ground;
the body is cut along the seam curve (one smooth edge loop) where 266's shaded small lobe (56)
meets the body, and shades with normals from the field itself. A small frost collar where an orb
meets the ground (a flattened contact, closed flat underside). Outline shell (D51), one per
body (common.outline_shell keeps one island); the -f3 shells are tagged per frame.

Run: tools/build-models.sh assets/blender/enemies/newshd-228.py
writes public/models/enemies/newshd-228{,-f2,-f3,-f4}.glb and their src/render/spriteModels entries.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = WT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import common  # noqa: E402
import lib_b075 as L  # noqa: E402

NAME = "newshd-228"
PX = 1 / 12
W, H = 12, 14

# Stage: (suffix, frames, [ (frame tag or None, lobes [(x edge, radius px)], seam (x edge, index) or None) ])
R0 = 2.02  # a free orb's radius in px (the 4 x 4 body inside the ink ring)
STAGES = [
    ("", [228], [(None, [(3.0, R0)], None), (None, [(9.0, R0)], None)]),
    ("-f2", [247], [(None, [(4.0, R0), (8.0, R0)], None)]),
    # seam: x edge at rows 5/8 (y = +-1.5 px), bow toward x at the middle, groove depth px, seam
    # index, and the small lobe's index (266's small lobe sits in shadow: its pixels 58/56/54/54)
    ("-f3", [266, 304], [(266, [(4.95, 1.98), (7.5, 1.62)],
                          dict(x=6.55, bow=0.45, depth=0.3, w=0.42, index=53, small=56, side=1)),
                         (304, [(4.5, 1.62), (7.05, 1.98)],
                          dict(x=5.15, bow=-0.3, depth=0.3, w=0.42, index=55, small=59, side=-1))]),
    ("-f4", [285], [(None, [(6.0, R0)], None)]),
]
STIFF = {"-f2": 8.0}  # the touching pair: a tight neck (the sprite keeps rows 5 and 8 apart)
ZC = 0.93  # lobe centre height as a share of its radius: a slightly settled contact on the ground


def bx(c):
    return (c - W / 2) * PX


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)
    for m in list(bpy.data.metaballs):
        bpy.data.metaballs.remove(m)


def metaball_mesh(name, lobes, coll, res, stiff=2.0):
    """A mesh of a metaball field of balls [(x, y, z, R)] in Blender units."""
    mb = bpy.data.metaballs.new(name + "_mb")
    mb.resolution = res
    mb.render_resolution = res
    mb.threshold = 0.6
    for x, y, z, r in lobes:
        e = mb.elements.new()
        e.co = (x, y, z)
        e.radius = r
        e.stiffness = stiff
    ob = bpy.data.objects.new(name + "_mbobj", mb)
    coll.objects.link(ob)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.metaballs.remove(mb)
    return me


_K = {}


def calib(coll, stiff):
    """Surface radius / element radius of one isolated ball (threshold 0.6)."""
    if stiff not in _K:
        me = metaball_mesh("calib", [(0, 0, 0, 1.0)], coll, 0.02, stiff)
        _K[stiff] = max(v.co.x for v in me.vertices)
        bpy.data.meshes.remove(me)
    return _K[stiff]


def body(name, lobes, seam, mats, coll, stiff=2.0):
    k = calib(coll, stiff)
    balls = [(bx(c), 0.0, ZC * r * PX, r * PX / k) for c, r in lobes]
    me = metaball_mesh(name, balls, coll, 0.28 * PX, stiff)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    # settle on the ground: flatten what falls below z = 0 (a closed flat contact)
    for v in bm.verts:
        if v.co.z < 0:
            v.co.z = 0.0
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.material_index = 0
        f.smooth = True
    if seam:
        # The seam: a narrow groove down the blob where the lobes press together, along a curve
        # x(y) = x + bow * (1 - (y / 1.5)^2) (pixel edges, y in px from the blob's middle row),
        # pushed in along the surface normal, deepest on top and fading toward the ground.
        bm.normal_update()
        wid = 0.32
        def dx_of(co):
            yy = co.y / PX
            return co.x / PX + W / 2 - (seam["x"] + seam["bow"] * (1 - (yy / 1.5) ** 2))
        moves = []
        for v in bm.verts:
            if v.co.z <= 1e-6:
                continue
            g = math.exp(-(dx_of(v.co) / wid) ** 2)
            fade = min(1.0, v.co.z / (1.2 * PX))
            moves.append((v, v.normal * (-seam["depth"] * PX * g * fade)))
        for v, m in moves:
            v.co += m
        for f in bm.faces:
            c = f.calc_center_median()
            dx = dx_of(c)
            if abs(dx) < 0.36 and c.z > 0.25 * PX:
                f.material_index = 1
            elif dx * seam["side"] > 0:
                f.material_index = 2
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    me.shade_smooth()
    return ob


def smin(a, b, k):
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k * 0.25


def seam_dx(seam, x, y):
    return x - (seam["x"] + seam["bow"] * (1 - (y / 1.5) ** 2))


def sdf(lobes, seam, p, k=2.2):
    """Signed distance (px) of the blob: a smooth union of the lobes, minus the seam groove."""
    x, y, z = p
    d = None
    for c, r in lobes:
        di = math.sqrt((x - c) ** 2 + y * y + (z - ZC * r) ** 2) - r
        d = di if d is None else smin(d, di, k)
    if seam:
        g = math.exp(-(seam_dx(seam, x, y) / seam.get("w", 0.34)) ** 2)
        d += seam["depth"] * g * min(1.0, max(z, 0.0) / 1.2)
    return d


def sdf_mesh(name, lobes, seam, mats, coll, nu=72, nv=36):
    """The blob as a UV sphere (poles up/down) round its centre, each vertex moved out along its
    ray to the surface (the blob is star-shaped from there): an even, smooth mesh."""
    cx = sum(c for c, _ in lobes) / len(lobes)
    cz = 0.9 * max(r for _, r in lobes)
    bm = bmesh.new()
    rings = []
    for j in range(1, nv):
        th = math.pi * j / nv
        ring = []
        for i in range(nu):
            ph = 2 * math.pi * i / nu
            dvec = (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))
            lo, hi = 0.0, 6.0
            for _ in range(40):
                m = (lo + hi) / 2
                q = (cx + dvec[0] * m, dvec[1] * m, cz + dvec[2] * m)
                if sdf(lobes, seam, q) < 0:
                    lo = m
                else:
                    hi = m
            px_, py_, pz_ = cx + dvec[0] * lo, dvec[1] * lo, max(0.0, cz + dvec[2] * lo)
            ring.append(bm.verts.new((bx(px_), py_ * PX, pz_ * PX)))
        rings.append(ring)
    top = bm.verts.new((bx(cx), 0, (cz + 2.0) * PX))
    # the top pole: find it too
    lo, hi = 0.0, 6.0
    for _ in range(40):
        m = (lo + hi) / 2
        if sdf(lobes, seam, (cx, 0, cz + m)) < 0:
            lo = m
        else:
            hi = m
    top.co.z = (cz + lo) * PX
    bot = bm.verts.new((bx(cx), 0, 0.0))
    for a, b in zip(rings, rings[1:]):
        for i in range(nu):
            i2 = (i + 1) % nu
            bm.faces.new((a[i], b[i], b[i2], a[i2]))
    for i in range(nu):
        i2 = (i + 1) % nu
        bm.faces.new((top, rings[0][i], rings[0][i2]))
        bm.faces.new((bot, rings[-1][i2], rings[-1][i]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
        f.material_index = 0
    if seam:
        seam_cut(bm, seam)
        seam_bead(bm, lobes, seam, cz)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    me.shade_smooth()
    if seam:
        sdf_normals(me, lobes, seam)
    return ob


def seam_cut(bm, seam):
    """Cut the body along the seam curve so the small lobe's colour changes on one smooth edge
    loop (not face by face): shear the mesh so the curve is the plane x = 0 (x' = seam_dx), bisect
    there, shear back. The new vertices sit on the old edges (chord sag ~0.004 px)."""
    def curve(yp):
        return seam["x"] + seam["bow"] * (1 - (yp / 1.5) ** 2)
    for v in bm.verts:
        v.co.x = (v.co.x / PX + W / 2 - curve(v.co.y / PX)) * PX
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-7, plane_co=(0, 0, 0), plane_no=(1, 0, 0))
    for f in bm.faces:
        f.smooth = True
        f.material_index = 2 if f.calc_center_median().x * seam["side"] > 0 else 0
    for v in bm.verts:
        v.co.x = bx(v.co.x / PX + curve(v.co.y / PX))


def sdf_normals(me, lobes, seam):
    """Shading normals from the blob's own field (its gradient, groove included): the seam's
    groove and the colour cut add thin faces, and averaged face normals there pinched into a
    star-shaped highlight. The flat contact keeps straight-down normals; the bead keeps its own."""
    e = 0.02
    # a softened groove for shading: the full groove's steep walls are a few facets wide, and their
    # normals interpolated across those facets streaked the sheen beside the bead
    seam = dict(seam, depth=seam["depth"] * 0.35, w=seam.get("w", 0.34) * 1.4)

    def grad(x, y, z):
        g = Vector((sdf(lobes, seam, (x + e, y, z)) - sdf(lobes, seam, (x - e, y, z)),
                    sdf(lobes, seam, (x, y + e, z)) - sdf(lobes, seam, (x, y - e, z)),
                    sdf(lobes, seam, (x, y, z + e)) - sdf(lobes, seam, (x, y, z - e))))
        return g.normalized()
    vn = {}
    for v in me.vertices:
        vn[v.index] = grad(v.co.x / PX + W / 2, v.co.y / PX, max(v.co.z / PX, 0.0))
    cn = me.corner_normals
    out = [None] * len(me.loops)
    for p in me.polygons:
        flat = all(me.vertices[i].co.z < 1e-6 for i in p.vertices)
        for li in p.loop_indices:
            if p.material_index == 1:
                out[li] = tuple(cn[li].vector)
            elif flat:
                out[li] = (0.0, 0.0, -1.0)
            else:
                out[li] = tuple(vn[me.loops[li].vertex_index])
    me.normals_split_custom_set(out)


def seam_bead(bm, lobes, seam, cz, rad=0.25, sink=0.1, sides=10, n=64):
    """The dark seam: a smooth bead lying in the groove from ground to ground over the top, its
    path found on the surface (rays in the y-z plane through the seam curve)."""
    def curve(yp):
        return seam["x"] + seam["bow"] * (1 - (yp / 1.5) ** 2)

    def hit(a):
        sy, cz_ = math.sin(a), math.cos(a)
        y = 0.0
        for _ in range(4):
            x = curve(y)
            lo, hi = 0.0, 6.0
            for _ in range(40):
                m = (lo + hi) / 2
                if sdf(lobes, seam, (x, sy * m, cz + cz_ * m)) < 0:
                    lo = m
                else:
                    hi = m
            y = sy * lo
        r = lo - sink
        return Vector((x, sy * r, cz + cz_ * r))

    def foot(sgn, ze):
        """Where the seam meets the ground: the surface along y at height ze on the seam curve."""
        lo, hi = 0.0, 6.0
        for _ in range(40):
            m = (lo + hi) / 2
            if sdf(lobes, seam, (curve(sgn * m), sgn * m, ze)) < 0:
                lo = m
            else:
                hi = m
        y = sgn * (lo - sink)
        return Vector((curve(y), y, ze))

    # ground to ground over the top: rays across the blob (y) down to the bead's resting height,
    # then the foot on the ground, so the crease runs right down to the contact
    ze = rad * 0.5
    mid = []
    for k in range(n + 1):
        p = hit(-2.6 + 5.2 * k / n)
        if p.z >= ze + 0.12:
            mid.append(p)
    pts = [foot(-1, ze)] + mid + [foot(1, ze)]
    n = len(pts) - 1
    rings = []
    for k, p in enumerate(pts):
        t = (pts[min(k + 1, n)] - pts[max(k - 1, 0)]).normalized()
        u = Vector((1, 0, 0))
        u = (u - t * u.dot(t)).normalized()
        v = t.cross(u)
        ring = []
        for j in range(sides):
            q = 2 * math.pi * j / sides
            w = p + (u * math.cos(q) + v * math.sin(q)) * rad
            ring.append(bm.verts.new((bx(w.x), w.y * PX, max(w.z, 0.0) * PX)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for j in range(sides):
            j2 = (j + 1) % sides
            f = bm.faces.new((a[j], a[j2], b[j2], b[j]))
            f.material_index = 1
            f.smooth = True
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        f = bm.faces.new(list(reversed(ring)) if rev else ring)
        f.material_index = 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def build(sprite, suffix, frames, bodies, coll):
    name = NAME + suffix
    objs, shells = [], []
    for i, (tag, lobes, seam) in enumerate(bodies):
        mats = [common.palette_material(sprite, 59, f"{name}_ice", metallic=0.15, roughness=0.14)]
        if seam:
            mats.append(common.palette_material(sprite, seam["index"], f"{name}_seam{tag}", metallic=0.15,
                                                roughness=0.3))
            mats.append(common.palette_material(sprite, seam["small"], f"{name}_ice", metallic=0.15, roughness=0.14))
        oname = f"{name}_body{i}" + (f"_{tag}" if tag else "")
        if suffix == "-f2":  # the touching pair: metaballs give the small neck between them
            ob = body(oname, lobes, seam, mats, coll, STIFF.get(suffix, 2.0))
        else:
            ob = sdf_mesh(oname, lobes, seam, mats, coll, nu=64 if seam else 40, nv=26 if seam else 20)
        if tag:
            common.frame_part(ob, [tag])
        objs.append(ob)
        # one outline per body; the -f3 bodies each get their own, tagged for their frame (the
        # big lobe swaps sides, so one shared shell let the other frame's lobe stick out of it)
        bpy.context.view_layer.objects.active = ob
        sh = common.outline_shell(ob, coll, voxel=0.006, faces=900)
        sh.name = f"{name}_outline{i}"
        if tag:
            common.frame_part(sh, [tag])
        shells.append(sh)
    return objs, shells


def main():
    sprite = common.load_sprite(WT, NAME)
    clear()
    for suffix, frames, bodies in STAGES:
        coll = common.reset_collection(NAME + suffix)
        objs, shells = build(sprite, suffix, frames, bodies, coll)
        common.export_sprite_model(WT, objs + shells, f"enemies/{NAME}{suffix}", L.frames_subset(sprite, frames))
        tris = 0
        for o in objs:
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
        print(f"built {NAME}{suffix}: {tris} triangles, {len(shells)} shell(s)")
        for o in objs + shells:
            o.hide_render = True
            o.hide_set(True)


if __name__ == "__main__":
    main()
