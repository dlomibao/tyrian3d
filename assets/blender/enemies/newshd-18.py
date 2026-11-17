"""Large grey asteroid with a glowing vent (newshd.shp frames 18, 55, 93): a 3D version of its sprite,
on the crag builder (lib_crag_rock, D239).

What it is: newshd-5's rock (built from that sprite with its seed, so the two are one stone) with a
vent set into its right lobe (columns 18-20, rows 10-14): a red lens with darker corners, an orange
cross and a yellow-white core on frame 18, the rock round it lit by the glow; a step cooler on frame
55; out on frame 93, where a dark scorched bed is left. The bed is a low plinth of the stone's own
rock joined into it there (the rectangle crosses a crevice, and a plate laid on the stones alone
would bridge it), its top scorched; on it a plate with a low lens dome, in the sprite's colours per
region. The frames only cool the glow, so one model
covers them all: the lens dims on frame 55 (palette_material frames=) and is gone on frame 93
(common.frame_part), showing the scorched bed (two index steps under its stone, as the sprite's
pixels there go from frame 5 to frame 93); the faces of the stone round the vent take
the glow's pal_11 on frame 18 only, the stone's own index on the other two.

    blender -b --factory-startup -P assets/blender/enemies/newshd-18.py -- [--no-bake] [--out file.glb]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_crag_rock as lib  # noqa: E402

common = lib.common

NAME = "newshd-18"
SPEC = {"seed": 5, "source": "newshd-5", "min_px": 6, "merge": 3.0, "blur": 0.5, "q": 0.82}  # newshd-5's

# The vent's rectangle, pixel edges: columns 18-20, rows 10-14.
C0, C1, R0, R1 = 18, 21, 10, 15
PLATE = 0.012          # the plate's thickness on the bed (units)
DOME_H = 1.0 / 12      # the lens's height above the plate
SCORCH = 2             # the scorched bed frame 93 shows where the vent was: this many index steps
                       # darker than its stone (the sprite: 9-10 -> 6, 8 -> 5, 6 -> 4)
HALO = 11              # the rock lit by the glow round the vent on frame 18
STATE = {}


def face_plane(bvh, g):
    """The plane the vent lies in: least squares through the higher two thirds of the rock's top over
    the vent's rectangle (the stone's face, not the crevice beside it), held to a gentle slope and
    lifted until no rock of the rectangle stands above it."""
    pts = []
    for k in range(9):
        for j in range(9):
            u = C0 + (C1 - C0) * k / 8
            v = R0 + (R1 - R0) * j / 8
            hit = bvh.ray_cast(Vector((g.x(u), g.y(v), 5.0)), Vector((0, 0, -1)))
            if hit[0] is not None:
                pts.append(hit[0])
    zs = sorted(p.z for p in pts)
    keep = [p for p in pts if p.z >= zs[len(zs) // 3]]
    A = np.array([[1.0, p.x, p.y] for p in keep])
    z = np.array([p.z for p in keep])
    a, b, c = np.linalg.lstsq(A, z, rcond=None)[0]
    k = min(1.0, 0.35 / max(math.hypot(b, c), 1e-6))
    cx, cy = g.x((C0 + C1) / 2), g.y((R0 + R1) / 2)
    b, c = b * k, c * k
    z0 = max(p.z - b * (p.x - cx) - c * (p.y - cy) for p in pts) + 0.004
    return lambda x, y: z0 + b * (x - cx) + c * (y - cy)


def box(bm, corners, plane, top, bottom, mat=0):
    up = [bm.verts.new((x, y, plane(x, y) + top)) for x, y in corners]
    dn = [bm.verts.new((x, y, plane(x, y) + bottom)) for x, y in corners]
    faces = [bm.faces.new(up), bm.faces.new(dn[::-1])]
    for i in range(4):
        j = (i + 1) % 4
        faces.append(bm.faces.new((up[i], dn[i], dn[j], up[j])))
    for f in faces:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    return faces


def paint(sprite, s, obj, info):
    """The vent's bed: a low plinth of the stone's own rock joined into it, its top the vent's plane
    (a frustum, a pixel wider at its foot, so it runs out into the stone and the crevice beside it),
    scorched where the vent lies; and the glow-lit rock round it."""
    coll = obj.users_collection[0]
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    plane = face_plane(bvh, s)
    STATE["plane"] = plane
    x0, x1, y0, y1 = s.x(C0), s.x(C1), s.y(R1), s.y(R0)
    m, f = 0.01, 1.0 / 12
    # the stone under the vent: the one most of the rectangle lies on
    lab = info["_maps"]["lab"]
    under = lab[R0:R1, C0:C1].ravel()
    k = int(np.bincount(under[under >= 0]).argmax())
    pal = next(t["pal"] for t in info["stones"] if t["k"] == k)
    stone = info["_mats"][pal]
    scorch = common.palette_material(sprite, max(4, pal - SCORCH), f"{NAME}-bed", metallic=0.0, roughness=0.9)
    halo = common.palette_material(sprite, HALO, f"{NAME}-glow", metallic=0.0, roughness=0.9, frames={55: pal, 93: pal})
    pb = bmesh.new()
    top = [(x0 - m, y0 - m), (x1 + m, y0 - m), (x1 + m, y1 + m), (x0 - m, y1 + m)]
    foot = [(x0 - f, y0 - f), (x1 + f, y0 - f), (x1 + f, y1 + f), (x0 - f, y1 + f)]
    up = [pb.verts.new((x, y, plane(x, y))) for x, y in top]
    dn = [pb.verts.new((x, y, plane(x, y) - 0.45)) for x, y in foot]
    pb.faces.new(up).material_index = 1
    pb.faces.new(dn[::-1])
    for i in range(4):
        j = (i + 1) % 4
        pb.faces.new((up[i], dn[i], dn[j], up[j]))
    bmesh.ops.recalc_face_normals(pb, faces=pb.faces[:])
    plinth = common.mesh_object(f"{NAME}_plinth", pb, [stone, scorch], coll, smooth=None)
    lib._boolean(obj, plinth, "UNION")
    bpy.data.objects.remove(plinth)
    bpy.context.view_layer.update()
    me = obj.data
    slots = {mm.name: i for i, mm in enumerate(me.materials) if mm}
    me.materials.append(halo)
    hs = len(me.materials) - 1
    for p in me.polygons:
        c = p.center
        u, v = s.uv(c.x, c.y)
        if p.material_index == slots.get(stone.name) and p.normal.z > 0.3 and C0 - 1.6 < u < C1 + 1.6 and R0 - 1.6 < v < R1 + 0.6:
            p.material_index = hs        # the rock the glow lights on frame 18
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False


def parts(sprite, s, obj, coll):
    """The vent: a plate lying in the bed (red 119, darker 117 corners) and a low lens dome on it
    (the orange 122 cross, the yellow-white 126 core), a step cooler on frame 55, gone on 93."""
    plane = STATE["plane"]
    tag = f"{NAME}-vent"
    mats = [
        common.palette_material(sprite, 119, tag, metallic=0.0, roughness=0.6, emission_strength=4.0, frames={55: 117}),
        common.palette_material(sprite, 117, tag, metallic=0.0, roughness=0.6, emission_strength=3.0, frames={55: 115}),
        common.palette_material(sprite, 122, tag, metallic=0.0, roughness=0.3, emission_strength=5.0, frames={55: 120}),
        common.palette_material(sprite, 126, tag, metallic=0.0, roughness=0.3, emission_strength=6.0, frames={55: 124}),
    ]
    RED, DARK, HOT, CORE = range(4)
    bm = bmesh.new()
    x0, x1, y0, y1 = s.x(C0), s.x(C1), s.y(R1), s.y(R0)
    e = 0.004
    box(bm, [(x0 + e, y0 + e), (x1 - e, y0 + e), (x1 - e, y1 - e), (x0 + e, y1 - e)], plane, PLATE, -0.01, RED)
    for c, r in ((C0, R0), (C1 - 1, R0), (C0, R1 - 1), (C1 - 1, R1 - 1)):
        cx0, cx1, cy0, cy1 = s.x(c) + e, s.x(c + 1) - e, s.y(r + 1) + e, s.y(r) - e
        box(bm, [(cx0, cy0), (cx1, cy0), (cx1, cy1), (cx0, cy1)], plane, PLATE + 0.004, -0.01, DARK)
    plate = set(bm.faces)
    # the lens: a half ellipsoid on the plate, sheared onto the rock's slope
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2 - 0.012, (y1 - y0) / 2 - 0.012
    sides, rings = 24, 6
    loops = []
    for k in range(rings):
        t = (math.pi / 2) * k / rings
        loops.append([bm.verts.new((cx + rx * math.cos(t) * math.cos(a), cy + ry * math.cos(t) * math.sin(a),
                                    DOME_H * math.sin(t))) for a in (2 * math.pi * (i + 0.5) / sides for i in range(sides))])
    tip = bm.verts.new((cx, cy, DOME_H))
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((l0[i], l0[j], l1[j], l1[i]))
    for i in range(sides):
        bm.faces.new((loops[-1][i], loops[-1][(i + 1) % sides], tip))
    bm.faces.new(list(reversed(loops[0])))
    for v in [w for loop in loops for w in loop] + [tip]:
        v.co.z += plane(v.co.x, v.co.y) + PLATE - 0.004
    bm.normal_update()
    hx0, hx1, hy0, hy1 = s.x(19), s.x(20), s.y(13), s.y(12)
    for f in bm.faces:
        if f in plate:
            continue
        c = f.calc_center_median()
        in_col = hx0 <= c.x <= hx1
        in_row = hy0 <= c.y <= hy1
        if in_col and in_row and c.z - plane(c.x, c.y) > DOME_H * 0.55:
            f.material_index = CORE
        elif (in_col or in_row) and c.z - plane(c.x, c.y) > DOME_H * 0.2:
            f.material_index = HOT
        else:
            f.material_index = RED
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    vent = common.mesh_object(f"{NAME}_vent", bm, mats, coll, smooth=False)
    return [common.frame_part(vent, [18, 55])]


if __name__ == "__main__":
    lib.main(NAME, SPEC, paint=paint, parts=parts)
