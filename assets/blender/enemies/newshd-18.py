"""Large grey asteroid with a glowing vent (newshd.shp frames 18, 55, 93): a 3D version of its sprite.

The sprite is newshd-5's rock with a vent set into its right lobe (columns 18-20, rows 10-14): a red
lens with darker corners, an orange cross and a yellow-white core on frame 18, the rock round it
lit by the glow; a step cooler on frame 55; out on frame 93, where a dark scorched bed is left. So
the rock is newshd-5's (built from its SPEC) with a shallow bed pressed into the lobe, and in it a
plate lying in the rock face with a low lens dome on it, in the sprite's colours per region. The
frames only cool the glow, so one model covers them all: the lens dims on frame 55
(palette_material frames=) and is gone on frame 93 (common.frame_part), showing the scorched
bed (pal_5); the rock round the vent takes the glow's pal_11 on frame 18 only, newshd-5's
mid-tone pal_7 on the other two. Matte rock, AO/roughness bake, D90 outline shell.

    blender -b --factory-startup -P assets/blender/enemies/newshd-18.py -- [--no-bake] [--out file.glb]
    (or tools/build-models.sh -j 2 assets/blender/enemies/newshd-18.py)
"""

import importlib.util
import math
import sys
from pathlib import Path

import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib_newshd_rock as lib  # noqa: E402

common = lib.common

NAME = "newshd-18"
_spec = importlib.util.spec_from_file_location("newshd_5", HERE / "newshd-5.py")
_rock5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rock5)
SPEC = _rock5.SPEC

# The vent's rectangle, pixel edges: columns 18-20, rows 10-14.
C0, C1, R0, R1 = 18, 21, 10, 15
SOCKET = 0.03          # socket depth below the rock face (units)
DOME_H = 1.0 / 12      # the lens's height above the plate
SCORCH = 5             # the scorched bed frame 93 shows where the vent was
HALO = 11              # the rock lit by the glow round the vent on frame 18


def face_plane(bvh, g):
    """Least-squares plane z = a + b x + c y through the rock's top over the vent's rectangle."""
    import numpy as np
    pts = []
    for k in range(7):
        for j in range(7):
            u = C0 + (C1 - C0) * k / 6
            v = R0 + (R1 - R0) * j / 6
            hit = bvh.ray_cast(Vector((g.x(u), g.y(v), 5.0)), Vector((0, 0, -1)))
            if hit[0] is not None:
                pts.append(hit[0])
    A = np.array([[1.0, p.x, p.y] for p in pts])
    z = np.array([p.z for p in pts])
    a, b, c = np.linalg.lstsq(A, z, rcond=None)[0]
    return lambda x, y: a + b * x + c * y


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


STATE = {}


def paint(sprite, g, obj):
    """Press the vent's bed into the lobe (the rock under the rectangle down to a plane in its
    face) and paint the scorched bed and the glow-lit rock."""
    import bpy
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    plane = face_plane(bvh, g)
    STATE["plane"] = plane
    x0, x1, y0, y1 = g.x(C0), g.x(C1), g.y(R1), g.y(R0)
    m = 0.02
    pressed = set()
    for v in obj.data.vertices:
        c = v.co
        if x0 - m < c.x < x1 + m and y0 - m < c.y < y1 + m and c.z > plane(c.x, c.y) - SOCKET:
            c.z = plane(c.x, c.y) - SOCKET
            pressed.add(v.index)
    obj.data.update()
    obj.data.materials.append(common.palette_material(sprite, SCORCH, NAME, metallic=0.0, roughness=0.85))
    obj.data.materials.append(common.palette_material(sprite, HALO, f"{NAME}-glow", metallic=0.05, roughness=0.72,
                                                      frames={55: SPEC["mid"], 93: SPEC["mid"]}))
    for p in obj.data.polygons:
        c = p.center
        u, v = g.uv(c.x, c.y)
        if any(i in pressed for i in p.vertices):
            p.material_index = 1        # the vent's bed and its walls
        elif p.normal.z > 0.3 and C0 - 1.6 < u < C1 + 1.6 and R0 - 1.6 < v < R1 + 0.6:
            p.material_index = 2        # the rock the glow lights on frame 18
        else:
            p.material_index = 0


def parts(sprite, g, obj, coll):
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
    x0, x1, y0, y1 = g.x(C0), g.x(C1), g.y(R1), g.y(R0)
    e = 0.004
    box(bm, [(x0 + e, y0 + e), (x1 - e, y0 + e), (x1 - e, y1 - e), (x0 + e, y1 - e)], plane, -0.002, -SOCKET - 0.01, RED)
    for c, r in ((C0, R0), (C1 - 1, R0), (C0, R1 - 1), (C1 - 1, R1 - 1)):
        cx0, cx1, cy0, cy1 = g.x(c) + e, g.x(c + 1) - e, g.y(r + 1) + e, g.y(r) - e
        box(bm, [(cx0, cy0), (cx1, cy0), (cx1, cy1), (cx0, cy1)], plane, 0.002, -0.01, DARK)
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
        v.co.z += plane(v.co.x, v.co.y) - 0.006
    bm.normal_update()
    hx0, hx1, hy0, hy1 = g.x(19), g.x(20), g.y(13), g.y(12)
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
