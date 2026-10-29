"""Beno Wallop Beam (sidekicks 27 and 28, tyrian.shp#9 frame 43): a 3D version of its sprite.

A two-player-only sidekick, 2x2 sprite, one frame. The sprite shows a round lilac-grey pod about
20 px across with a grey gun barrel lying along its spine and pointing up the screen (forward),
its tip glowing red-orange-yellow. Read as a small machine it is a ball turret:

- The pod: a ball of painted lilac metal (palette 88, the sprite's mid-tone), 20 px across and
  19 px long, a little flattened (15 px tall) and cut flat underneath, where a dark mounting hub
  sits. The sprite's dark ring and lower-right shading are the light, not paint.
- The yoke: the barrel lies in a channel cut right through the front of the pod (the sprite shows
  background through the 1 px gaps either side of the barrel in rows 6-13), 9 px wide, so the
  pod's front is two rounded cheeks with crisp, lit inner walls (the bright column 7) cradling the
  barrel, which is held at the back by its breech.
- The barrel: a turned metal cylinder (palette 10) 7 px across lying in the channel, its top
  standing proud of the pod, with the sprite's bands as real collars and grooves: a wide collar at
  rows 2-3, a groove, a collar at row 5, a groove where it enters the yoke, a long body, a last
  groove at row 10, and a narrower breech that runs back into a recess in the pod (rows 12-16).
- The muzzle (rows 0-1): an emitter ring wider than the barrel, glowing (palette 122 emissive,
  the sprite's orange band), capped by a dark-red rim (114) with a hot yellow core (125) in its
  face: the beam's lens.
- Side hatches (rows 14-16, the dark blocks either side of the breech): two recessed panels set
  into the pod's top, with the inner ball forming their floor.
- The belt (rows 17-18, the bright band across the pod): a raised ring round the pod, the seam
  between its front and rear shells.
- The rear housing (rows 20-25, the lighter block with dark sides at the back): a bevelled box
  fairing lying along the back of the pod with a dark exhaust nozzle at its end.

Run: blender --background --python assets/blender/sidekicks/beno-wallop-beam.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "sidekick-beno-wallop-beam"
MODEL = "sidekicks/beno-wallop-beam"
ROOT = common.repo_root(__file__)
P = 1 / 12  # one sprite pixel

# Everything below is in sprite px; the 24x28 block is centred on the origin, so column edge c is
# x = c - 12 and row edge r is y = 14 - r.
CX = 0.5  # the pod's and barrel's centre line (between columns 12 and 13)
POD_Y = -1.5  # the pod's centre (rows 6-24)
POD_R = (10.5, 9.8, 7.7)  # pod radii x, y, z
POD_FLOOR = -5.0  # the pod is cut flat underneath here
SHELL = 0.9  # depth of the hatches and the channel walls' lip (inner ball is this much smaller)
SLOT_HW = 4.5  # half width of the barrel channel
SLOT_Y0 = 1.6  # the channel's back wall
SLOT_FLOOR = -20.0  # the channel goes right through: the front is a yoke of two cheeks
BARREL_Z = 5.6  # the barrel's axis height
METAL = dict(metallic=0.45, roughness=0.38)  # painted pod
STEEL = dict(metallic=0.85, roughness=0.28)  # turned barrel


def v(x, y, z):
    return Vector((x * P, y * P, z * P))


def ellipsoid(bm, radii, centre, segments, rings, mat, floor=None):
    """A UV ellipsoid (radii in px) added to bm, optionally cut flat (and capped) at z = floor."""
    geom = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    verts = geom["verts"]
    for vert in verts:
        vert.co = Vector((centre[0] + vert.co.x * radii[0], centre[1] + vert.co.y * radii[1],
                          centre[2] + vert.co.z * radii[2])) * P
    faces = list({f for vert in verts for f in vert.link_faces})
    for f in faces:
        f.material_index = mat
    if floor is not None:
        cut = bmesh.ops.bisect_plane(bm, geom=list(set(verts) | {e for vv in verts for e in vv.link_edges} | set(faces)),
                                     plane_co=(0, 0, floor * P), plane_no=(0, 0, 1), clear_inner=True)
        edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        fill = bmesh.ops.edgenet_fill(bm, edges=edges)
        for f in fill["faces"]:
            f.material_index = mat


def cylinder_y(bm, x, z, y0, y1, r, sides, mat, r1=None):
    """A cylinder (or cone, r -> r1) along +Y from y0 to y1, axis at (x, z), in px."""
    r1 = r if r1 is None else r1
    rings = []
    for y, rad in ((y0, r), (y1, r1)):
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            ring.append(bm.verts.new(v(x + rad * math.cos(a), y, z + rad * math.sin(a))))
        rings.append(ring)
    a, b = rings
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat
    bm.faces.new(list(reversed(a))).material_index = mat
    bm.faces.new(b).material_index = mat


def box(bm, lo, hi, mat, matrix=None):
    """An axis-aligned box from lo to hi (px), optionally transformed by matrix (in units)."""
    geom = bmesh.ops.create_cube(bm, size=1.0)
    for vert in geom["verts"]:
        co = Vector(((lo[0] + hi[0]) / 2 + vert.co.x * (hi[0] - lo[0]), (lo[1] + hi[1]) / 2 + vert.co.y * (hi[1] - lo[1]),
                     (lo[2] + hi[2]) / 2 + vert.co.z * (hi[2] - lo[2]))) * P
        vert.co = matrix @ co if matrix else co
    for f in {f for vert in geom["verts"] for f in vert.link_faces}:
        f.material_index = mat


def torus_y(bm, y, rx, rz, z, minor, major_seg, minor_seg, mat):
    """A ring round the Y axis at y: an elliptical centre line (rx, rz) with a round tube."""
    grid = []
    for i in range(major_seg):
        a = 2 * math.pi * i / major_seg
        c = Vector((CX + rx * math.cos(a), y, z + rz * math.sin(a)))
        n = Vector((rz * math.cos(a), 0, rx * math.sin(a))).normalized()
        ring = []
        for k in range(minor_seg):
            b = 2 * math.pi * k / minor_seg
            p = c + n * (minor * math.cos(b)) + Vector((0, 1, 0)) * (minor * math.sin(b))
            ring.append(bm.verts.new(p * P))
        grid.append(ring)
    for i in range(major_seg):
        a, b = grid[i], grid[(i + 1) % major_seg]
        for k in range(minor_seg):
            m = (k + 1) % minor_seg
            bm.faces.new((a[k], b[k], b[m], a[m])).material_index = mat


def obj_of(name, bm, mats, coll, sharp=35.0):
    obj = common.mesh_object(name, bm, mats, coll, smooth=True)
    obj.data.set_sharp_from_angle(angle=math.radians(sharp))
    return obj


def apply_boolean(target, cutter, operation="DIFFERENCE"):
    """Apply a boolean (exact solver) to target and return it; the cutter is deleted."""
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = operation
    mod.object = cutter
    mod.solver = "EXACT"
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    target.modifiers.remove(mod)
    old = target.data
    target.data = mesh
    bpy.data.meshes.remove(old)
    data = cutter.data
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.meshes.remove(data)
    return target


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(89, **METAL),        # 0 pod
        pal(86, **METAL),        # 1 pod recess floors (the hatch panels' darker lilac)
        pal(90, **METAL),        # 2 belt and rear housing (the lighter bands)
        pal(80, metallic=0.2, roughness=0.6),  # 3 dark: hub, nozzle throat
        pal(10, **STEEL),        # 4 barrel
        pal(12, **STEEL),        # 5 collars
        pal(6, **STEEL),         # 6 grooves and breech
        pal(114, metallic=0.6, roughness=0.35),  # 7 muzzle rim (dark red)
        pal(122, metallic=0.0, roughness=0.4, emission_strength=2.0),  # 8 emitter ring glow
        pal(125, metallic=0.0, roughness=0.3, emission_strength=4.0),  # 9 lens core
    ]
    POD, FLOORMAT, LIGHT, DARK, BARREL, COLLAR, GROOVE, RIM, GLOW, CORE = range(10)

    # The pod shell, with the channel and hatches cut through it.
    bm = bmesh.new()
    ellipsoid(bm, POD_R, (CX, POD_Y, 0.0), 28, 14, POD, floor=POD_FLOOR)
    pod = obj_of(f"{NAME}-pod", bm, mats, coll, sharp=40)
    for lo, hi in (
        ((CX - SLOT_HW, SLOT_Y0, SLOT_FLOOR), (CX + SLOT_HW, 20, 20)),  # the barrel channel
        ((CX - 3.3, -2.6, BARREL_Z - 0.4), (CX + 3.3, SLOT_Y0 + 0.5, 20)),  # the breech recess
        ((CX - 8.0, -2.7, 4.0), (CX - 3.8, -0.4, 20)),  # left hatch
        ((CX + 3.8, -2.7, 4.0), (CX + 8.0, -0.4, 20)),  # right hatch
    ):
        bmc = bmesh.new()
        box(bmc, lo, hi, 0)
        apply_boolean(pod, common.mesh_object(f"{NAME}-cut", bmc, [], coll))

    # The inner ball: the floor of the hatches (it stays under the shell elsewhere). It's cut by the
    # channel too, so the channel keeps its flat floor.
    bm = bmesh.new()
    inner = [r - SHELL for r in POD_R]
    ellipsoid(bm, inner, (CX, POD_Y, 0.0), 20, 10, FLOORMAT, floor=POD_FLOOR + 0.2)
    core = obj_of(f"{NAME}-core", bm, mats, coll, sharp=40)
    bmc = bmesh.new()
    box(bmc, (CX - SLOT_HW - 0.01, SLOT_Y0 - 0.01, SLOT_FLOOR - 0.01), (CX + SLOT_HW + 0.01, 20, 20), 0)
    bmc2 = bmesh.new()
    box(bmc2, (CX - 3.31, -2.61, BARREL_Z - 0.41), (CX + 3.31, SLOT_Y0 + 0.6, 20), 0)
    apply_boolean(core, common.mesh_object(f"{NAME}-cut", bmc, [], coll))
    apply_boolean(core, common.mesh_object(f"{NAME}-cut", bmc2, [], coll))

    # A bevel on the pod's cut edges: crisp but catching the light.
    bev = pod.modifiers.new("bevel", "BEVEL")
    bev.width = 0.25 * P
    bev.segments = 1
    bev.limit_method = "ANGLE"
    bev.angle_limit = math.radians(50)
    bev.harden_normals = False

    # Barrel, collars, muzzle, belt, rear housing, hub: one hard-surface object.
    bm = bmesh.new()
    S = 14
    z = BARREL_Z
    cylinder_y(bm, CX, z, -2.4, 2.0, 2.6, S, GROOVE)          # breech (in the recess)
    cylinder_y(bm, CX, z, 1.6, 3.0, 3.2, S, BARREL)          # row 11
    cylinder_y(bm, CX, z, 3.0, 4.0, 2.85, S, GROOVE)          # row 10 groove
    cylinder_y(bm, CX, z, 4.0, 7.0, 3.3, S, BARREL)          # rows 7-9 body
    cylinder_y(bm, CX, z, 7.0, 8.0, 2.85, S, GROOVE)          # row 6 groove
    cylinder_y(bm, CX, z, 8.0, 9.0, 3.5, S, COLLAR)          # row 5 collar
    cylinder_y(bm, CX, z, 9.0, 10.0, 2.95, S, GROOVE)          # row 4 groove
    cylinder_y(bm, CX, z, 10.0, 12.0, 3.5, S, COLLAR)         # rows 2-3 collar
    cylinder_y(bm, CX, z, 12.0, 13.1, 3.9, S, GLOW)           # row 1 emitter ring
    cylinder_y(bm, CX, z, 13.0, 13.9, 3.2, S, RIM, r1=2.7)    # row 0 rim
    cylinder_y(bm, CX, z, 13.6, 14.05, 1.7, 12, CORE)         # the lens core in the rim's face

    # The belt: the seam ring between the front and rear shells (rows 17-18).
    yb = -4.0
    k = math.sqrt(max(0.0, 1 - ((yb - POD_Y) / POD_R[1]) ** 2))
    torus_y(bm, yb, POD_R[0] * k - 0.2, POD_R[2] * k - 0.2, 0.0, 0.45, 28, 5, LIGHT)

    # The rear housing: a box fairing along the back of the pod, following its slope, with a nozzle.
    y0, y1 = -5.0, -10.6
    def surf(y):
        return POD_R[2] * math.sqrt(max(0.0, 1 - ((y - POD_Y) / POD_R[1]) ** 2))
    za, zb = surf(y0) - 0.6, surf(y1 + 0.6) - 0.2
    ang = math.atan2(za - zb, y0 - y1)
    length = math.hypot(y0 - y1, za - zb)
    mid = Vector((CX, (y0 + y1) / 2, (za + zb) / 2)) * P
    m = Matrix.Translation(mid) @ Matrix.Rotation(ang, 4, "X") @ Matrix.Translation(-mid)
    nb = len(bm.verts)
    box(bm, (CX - 2.4, (y0 + y1) / 2 - length / 2, (za + zb) / 2 - 1.6),
        (CX + 2.4, (y0 + y1) / 2 + length / 2, (za + zb) / 2 + 0.8), LIGHT, matrix=m)
    # Taper its top: the upper edges lean in a little, so it reads as a fairing, not a brick.
    bm.verts.ensure_lookup_table()
    local = m.inverted()
    for vert in bm.verts[nb:]:
        lc = local @ vert.co
        if lc.z > ((za + zb) / 2) * P:
            lc.x = CX * P + (lc.x - CX * P) * 0.7
            vert.co = m @ lc
    # The nozzle at the housing's end, pointing back and a little down.
    end = m @ (Vector((CX, (y0 + y1) / 2 - length / 2, (za + zb) / 2)) * P)
    ex, ey, ez = end.x / P, end.y / P, end.z / P
    nb = len(bm.verts)
    cylinder_y(bm, 0.0, 0.0, -1.0, 0.2, 1.6, 12, DARK, r1=1.8)
    bm.verts.ensure_lookup_table()
    rot = Matrix.Rotation(ang, 4, "X")
    for vert in bm.verts[nb:]:
        vert.co = rot @ vert.co + Vector((ex, ey, ez)) * P

    # The mounting hub under the flat belly.
    cylinder_y(bm, 0.0, 0.0, -0.6, 0.6, 4.0, 16, DARK)
    hub_from = len(bm.verts) - 32
    bm.verts.ensure_lookup_table()
    rot = Matrix.Rotation(math.pi / 2, 4, "X")
    for vert in bm.verts[hub_from:]:
        vert.co = rot @ vert.co + Vector((CX, POD_Y, POD_FLOOR - 0.5)) * P

    parts = obj_of(f"{NAME}-parts", bm, mats, coll, sharp=35)

    return [pod, core, parts]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objs = build(sprite)
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"])
    dg = bpy.context.evaluated_depsgraph_get()
    tris = 0
    for o in objs:
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        print(f"  {o.name}: {len(me.loop_triangles)} triangles")
        o.evaluated_get(dg).to_mesh_clear()
    print(f"triangles: {tris}")
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = ROOT / "reference" / "models" / NAME / frame["image"]
        common.render_preview(objs, out, ref, size=frame["size"], frame=frame["index"])


if __name__ == "__main__":
    main()
