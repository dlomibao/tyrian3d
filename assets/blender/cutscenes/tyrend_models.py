"""The two ships of tyrend.anm (episode 3's ending, DECISIONS.md D219), built for the cutscene only
(they never appear in a level), measured from the original CG's frames. Both use the game's model
axes: nose +Y, top +Z, port -X. Imported by tyrend.py.

- build_fighter(): the slim grey-green fighter of shots B-E, the player's ship by the script's text: a
  long needle nose, a long dark canopy, a slim fuselage in blocky camouflage panels, a dark rounded
  engine block over the rear half with four nozzles in a 2x2 cluster, a gun rod under the nose, a rail
  on the engine block, and two long slender swept wings with tip pods. 2.2 units long.
- build_hull(): the hull that sweeps past the camera in shot A, the escape pod the text mentions: a
  smooth, rounded olive-brown lens with streaky plating, a long pale-lavender window band along its
  port upper flank and a row of round portholes behind it. 9.2 units long.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import common as c  # assets/art/common.py (tyrend.py puts it on the path)


# --- Geometry helpers ----------------------------------------------------------------------------

def loft(name, sections, sides=32, mat=None, smooth=True):
    """A closed tube along Y through elliptical sections [(y, half_width, half_height, z_centre)]."""
    bm = bmesh.new()
    rings = []
    for y, w, h, zc in sections:
        rings.append([bm.verts.new((w * math.cos(a), y, zc + h * math.sin(a)))
                      for a in (2 * math.pi * i / sides for i in range(sides))])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = c.mesh_object(name, mesh, mat)
    if smooth:
        c.smooth(obj)
    return obj


def rounded_box(name, centre, half, bevel, mat):
    bpy.ops.mesh.primitive_cube_add(location=centre)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = half
    bpy.ops.object.transform_apply(scale=True)
    m = obj.modifiers.new("bevel", "BEVEL")
    m.width = bevel
    m.segments = 5
    obj.data.materials.append(mat)
    c.smooth(obj)
    return obj


def rod(name, a, b, r, mat, verts=12):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=(b - a).length, location=(a + b) / 2)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(mat)
    c.smooth(obj)
    return obj


def wing(name, side, mat):
    """A tapered, swept slab from the fuselage side out to a tip, on side +1 (starboard) or -1."""
    s = side
    root_le, root_te = Vector((0.15 * s, 0.02, -0.03)), Vector((0.15 * s, -0.62, -0.03))
    tip_le, tip_te = Vector((1.06 * s, -1.02, -0.13)), Vector((1.06 * s, -1.2, -0.13))
    t_root, t_tip = 0.035, 0.014
    bm = bmesh.new()
    pts = [root_le, tip_le, tip_te, root_te]
    thick = [t_root, t_tip, t_tip, t_root]
    top = [bm.verts.new(p + Vector((0, 0, t))) for p, t in zip(pts, thick)]
    bot = [bm.verts.new(p - Vector((0, 0, t))) for p, t in zip(pts, thick)]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((top[i], bot[i], bot[j], top[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = c.mesh_object(name, mesh, mat)
    m = obj.modifiers.new("bevel", "BEVEL")
    m.width = 0.008
    m.segments = 2
    return obj, (tip_le + tip_te) / 2


# --- Materials -----------------------------------------------------------------------------------

def camo_material(name):
    """The fighter's skin: blocky grey-green panels (Chebychev Voronoi cells in three shades), a
    little metallic, like the CG's flat-shaded camouflage."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Metallic"].default_value = 0.35
    b.inputs["Roughness"].default_value = 0.45
    tc = c.node(nt, "ShaderNodeTexCoord")
    mp = c.node(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (5.0, 2.2, 5.0)  # panels longer than wide
    c.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    vor = c.node(nt, "ShaderNodeTexVoronoi", p_distance="CHEBYCHEV", Scale=3.2, Randomness=0.9)
    c.link(nt, mp.outputs[0], vor.inputs["Vector"])
    sep = c.node(nt, "ShaderNodeSeparateColor")
    c.link(nt, vor.outputs["Color"], sep.inputs["Color"])
    shades = c.ramp(nt, [(0.0, c.srgb(70, 84, 82)), (0.4, c.srgb(98, 114, 108)), (0.75, c.srgb(122, 138, 128)),
                         (0.92, c.srgb(150, 170, 160))], interpolation="CONSTANT")
    c.link(nt, sep.outputs[0], shades.inputs["Fac"])
    c.link(nt, shades.outputs["Color"], b.inputs["Base Color"])
    return mat


WINDOW = c.srgb(128, 120, 168)


def hull_material(name, window):
    """The pod's olive-brown plating, streaked along its length (the CG's smeared texture), with the
    pale-lavender window band painted in by window(nt, coord) (a 0..1 mask socket)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Metallic"].default_value = 0.2
    b.inputs["Roughness"].default_value = 0.55
    tc = c.node(nt, "ShaderNodeTexCoord")
    mp = c.node(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.6, 0.15, 2.6)  # long streaks along Y
    c.link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    noise = c.node(nt, "ShaderNodeTexNoise", Scale=3.0, Detail=6.0, Roughness=0.6)
    c.link(nt, mp.outputs[0], noise.inputs["Vector"])
    shades = c.ramp(nt, [(0.3, c.srgb(38, 38, 28)), (0.46, c.srgb(60, 59, 43)), (0.58, c.srgb(80, 77, 56)),
                         (0.7, c.srgb(98, 90, 68))])
    c.link(nt, noise.outputs["Fac"], shades.inputs["Fac"])
    mask = window(nt, tc.outputs["Object"])
    col = c.node(nt, "ShaderNodeMix", p_data_type="RGBA")
    c.link(nt, mask, col.inputs["Factor"])
    c.link(nt, shades.outputs["Color"], col.inputs[6])
    col.inputs[7].default_value = (*WINDOW, 1)
    c.link(nt, col.outputs[2], b.inputs["Base Color"])
    rough = c.node(nt, "ShaderNodeMapRange", **{"To Min": 0.55, "To Max": 0.3})
    c.link(nt, mask, rough.inputs["Value"])
    c.link(nt, rough.outputs[0], b.inputs["Roughness"])
    return mat


def _ellipse_mask(nt, coord, centre, radii, soft=0.06):
    """1 inside the ellipse ((y/hy - cu)/ru)^2 + ((z/hz - cv)/rv)^2 < 1 on the hull's port side
    (x < 0), 0 outside, with a soft edge."""
    hx, hy, hz = HULL
    sep = c.node(nt, "ShaderNodeSeparateXYZ")
    c.link(nt, coord, sep.inputs[0])
    def term(axis, h, cen, rad):
        a = c.node(nt, "ShaderNodeMath", p_operation="MULTIPLY_ADD", values={1: 1 / (h * rad), 2: -cen / rad})
        c.link(nt, sep.outputs[axis], a.inputs[0])
        sq = c.node(nt, "ShaderNodeMath", p_operation="POWER", values={1: 2.0})
        c.link(nt, a.outputs[0], sq.inputs[0])
        return sq.outputs[0]
    add = c.node(nt, "ShaderNodeMath", p_operation="ADD")
    c.link(nt, term("Y", hy, centre[0], radii[0]), add.inputs[0])
    c.link(nt, term("Z", hz, centre[1], radii[1]), add.inputs[1])
    inside = c.node(nt, "ShaderNodeMapRange", **{"From Min": 1.0, "From Max": 1.0 - soft, "To Min": 0.0, "To Max": 1.0})
    c.link(nt, add.outputs[0], inside.inputs["Value"])
    port = c.node(nt, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": -0.1, "To Min": 0.0, "To Max": 1.0})
    c.link(nt, sep.outputs["X"], port.inputs["Value"])
    both = c.node(nt, "ShaderNodeMath", p_operation="MULTIPLY")
    c.link(nt, inside.outputs[0], both.inputs[0])
    c.link(nt, port.outputs[0], both.inputs[1])
    return both.outputs[0]


# --- The ships -----------------------------------------------------------------------------------

def _root(name, parts):
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    for p in parts:
        p.parent = root
    root.rotation_mode = "QUATERNION"
    return root


def build_fighter():
    """Returns (root, points): points names the engine nozzles, the nose light and the wing tips."""
    camo = camo_material("fighter_camo")
    dark = c.material("fighter_engine", c.srgb(44, 46, 48), metallic=0.6, roughness=0.34)
    glass = c.material("fighter_glass", c.srgb(14, 18, 20), metallic=0.2, roughness=0.08)
    nozzle = c.material("fighter_nozzle", c.srgb(10, 10, 10), roughness=0.6)
    parts = []
    # The fuselage: a needle nose swelling to a slim body.
    parts.append(loft("fighter_body", [
        (1.10, 0.004, 0.004, 0.0),
        (0.86, 0.03, 0.03, 0.0),
        (0.60, 0.075, 0.065, 0.005),
        (0.36, 0.12, 0.1, 0.015),
        (0.10, 0.16, 0.12, 0.015),
        (-0.25, 0.18, 0.13, 0.0),
        (-0.65, 0.17, 0.12, -0.02),
        (-1.00, 0.14, 0.1, -0.03),
        (-1.06, 0.1, 0.07, -0.03),
    ], mat=camo))
    # The canopy: long and low, behind the nose.
    parts.append(loft("fighter_canopy", [
        (0.60, 0.01, 0.01, 0.06),
        (0.50, 0.055, 0.04, 0.075),
        (0.32, 0.075, 0.06, 0.09),
        (0.14, 0.06, 0.05, 0.09),
        (0.06, 0.02, 0.02, 0.08),
    ], mat=glass))
    # The engine block over the rear half: dark, rounded, its front end curved.
    parts.append(rounded_box("fighter_engine", (0.0, -0.64, 0.12), (0.17, 0.44, 0.12), 0.1, dark))
    # Four nozzles in a 2x2 cluster on its rear face.
    nozzles = []
    for x in (-0.07, 0.07):
        for z in (0.07, 0.18):
            n = rod("fighter_nozzle", (x, -1.06, z), (x, -1.1, z), 0.05, nozzle, verts=16)
            parts.append(n)
            nozzles.append(Vector((x, -1.11, z)))
    # A rail along the engine block's top, sticking out behind it; a gun rod under the nose.
    parts.append(rod("fighter_rail", (0.1, -0.3, 0.255), (0.1, -1.32, 0.255), 0.013, dark))
    parts.append(rod("fighter_gun", (-0.13, 0.05, -0.07), (-0.13, 0.58, -0.07), 0.013, dark))
    # The wings, each with a tip pod.
    tips = {}
    for side in (-1, 1):
        w, tip = wing(f"fighter_wing_{side}", side, camo)
        parts.append(w)
        parts.append(rod(f"fighter_pod_{side}", tip + Vector((0, 0.16, 0)), tip - Vector((0, 0.16, 0)), 0.024, dark))
        tips[side] = tip
    root = _root("fighter", parts)
    return root, {
        "nozzles": nozzles,
        "engine": sum(nozzles, Vector()) / len(nozzles),
        "nose_light": Vector((-0.13, 0.6, -0.07)),
        "starboard_tip": tips[1] + Vector((0, 0.17, 0)),
        "port_tip": tips[-1] + Vector((0, 0.17, 0)),
    }


HULL = (1.8, 4.6, 1.3)  # half extents (x, y, z) of the pod's lens


def _ellipsoid(name, mat, scale=1.0, keep=None, segments=128, rings=64):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    bmesh.ops.scale(bm, vec=Vector(HULL) * scale, verts=bm.verts)
    if keep:
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if not keep(f.calc_center_median())], context="FACES")
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = c.mesh_object(name, mesh, mat)
    c.smooth(obj)
    return obj


def build_hull():
    # The window band: a long oval on the port upper flank over the front half, painted into the
    # plating (a smooth edge at any distance).
    plate = hull_material("pod_plate", lambda nt, coord: _ellipse_mask(nt, coord, (0.34, 0.62), (0.25, 0.13)))
    lavender = c.material("pod_porthole", WINDOW, metallic=0.1, roughness=0.3)
    hx, hy, hz = HULL
    parts = [_ellipsoid("pod_hull", plate)]

    # Portholes: a row of round domes along the port flank, behind and below the window.
    for k in range(6):
        u = 0.02 - 0.1 * k
        v = 0.44
        y, z = u * hy, v * hz
        x = -hx * math.sqrt(max(0.0, 1 - u * u - v * v))
        normal = Vector((x / hx**2, y / hy**2, z / hz**2)).normalized()
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0, location=(x, y, z))
        dome = bpy.context.active_object
        dome.name = f"pod_porthole_{k}"
        dome.rotation_euler = normal.to_track_quat("Z", "Y").to_euler()
        dome.scale = (0.13, 0.13, 0.04)
        dome.data.materials.append(lavender)
        c.smooth(dome)
        parts.append(dome)
    return _root("pod", parts)
