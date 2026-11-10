"""Ring with a blade (newshi.shp frames 19, 38, 57, 76, 95): a hard-surface 3D version of its sprite.

Seen in episode 1 (level sections 10, 29 and 38) and level 3.21, on the ground. A round
rust-red collar (flat top, chamfered edges, bolt heads) with an off-centre hole through it (the
ground shows through), and a curved scimitar plate that fills the hole's upper right from a tip at
the top left round to a hooked tail at the bottom, with a drilled pivot hole at its root.

The sprite is authoritative. Its ink is the constant 32 / 1 / 2 / 3 ring (the same pixels in every
frame); the dark browns 64 / 65 / 66 / 161 of frame 19 are body, as frames 57-95 show (they are 18 /
67 / 72 / 74 / 77 there). The model's top view is the sprite's opaque mask minus the boundary
pixels of those ink indexes, the same mask for every frame (frame 95 drops the tail pixel at (7, 9)).
Fitted on that mask (scratch fix1/n19/fit19b.py, with a 0.18 coverage margin per pixel so the
grid IoU holds in the real render; grid IoU 1.0 on frames 19-76, 0.974 on 95):
  collar  outer circle centre (6.01, 7.01) r 5.88; hole circle centre (6.37, 6.52) r 4.69
  blade   its cutting edge a fair curve from the tip (3.79, 3.51) down to (8.0, 8.2), where it
          hooks back into a tail that meets the collar at (7.3, 10.7); its back runs under the collar
  notch   a drilled pivot hole through the blade's root by the tail, centre (8.77, 9.76) r 0.97
          (the sprite's transparent pixel at (8, 9) and its ink)
  colour  the five frames are one shape getting brighter (dark brown to pale pink): the collar and
          blade medians are 67, 69, 72, 74, 77 (frames 19, 38, 57, 76, 95); the light from the upper
          right is lighting, not paint, so each part is one palette material that steps through
          the frames' shades (palette_material frames=, D17)
The interior ink lines (row 3 and col 9) are the shadowed step from the collar's top down to the
blade, modelled as that step.

Units: Blender X = (x - 6) / 12, Y = (7 - y) / 12, Z = z / 12 (sprite px, y down, z up).
Undersides are a plain closed shape (flat bottoms on the ground). No texture bake: at 12 px the
maps would not show, so there is no textures folder. Outline shell for the game's ink (D51), held
a hair inside the model (inside=) so the collar/blade step draws no crack.

Run: blender --background --python assets/blender/enemies/newshi-19.py [-- --preview out.png]
     [--frames out.png] [--measure DIR]   (--measure writes top.png at 16 texels per sprite px)
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshi-19"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
CX, CY = 6.0, 7.0
SEGS = 192

RC, R_OUT = (6.013, 7.012), 5.882        # collar outer circle (px, y down)
HC, R_HOLE = (6.373, 6.516), 4.685       # the hole
NC, R_NOTCH = (8.769, 9.761), 0.971      # the drilled notch by the blade's tail
# Collar cross-section, a closed (side, offset px, height px) list: 'i' is measured out from the hole
# wall, 'o' in from the outer wall.
RING_PROFILE = [("i", 0.0, 0.0), ("o", 0.0, 0.0), ("o", 0.0, 0.88), ("o", 0.3, 1.2), ("i", 0.34, 1.2),
                ("i", 0.0, 0.86)]
TOP_Z = 1.2
BLADE_TOP = 0.98      # the blade's spine flat
BLADE_EDGE_Z = 0.36   # its cutting edge wall
BLADE_GRIND = 0.55    # width of the grind from the edge up to the spine flat (px)
# The blade's cutting edge (px, y down), tip first; its back hides under the collar.
BLADE_EDGE = [(3.794, 3.51), (4.234, 4.607), (5.593, 5.352), (6.879, 6.209), (7.779, 7.184), (7.986, 8.194),
              (7.201, 9.176), (7.302, 10.694)]
BLADE_BACK_R = R_HOLE + 0.5


def W(x, y, z):
    return Vector(((x - CX) / 12, (CY - y) / 12, z / 12))


def r_hole(c, s):
    """The hole wall's distance from the hole centre along (c, s) (y down): the circle, or the
    notch where it reaches past it."""
    wx, wy = NC[0] - HC[0], NC[1] - HC[1]
    along = wx * c + wy * s
    perp2 = wx * wx + wy * wy - along * along
    r = R_HOLE
    if perp2 < R_NOTCH ** 2:
        r = max(r, along + math.sqrt(R_NOTCH ** 2 - perp2))
    return r


def collar_points(t):
    """(inner wall point, outer wall point) at parameter angle t (px, y down)."""
    c, s = math.cos(t), -math.sin(t)
    ri = r_hole(c, s)
    return (HC[0] + ri * c, HC[1] + ri * s), (RC[0] + R_OUT * c, RC[1] + R_OUT * s)


def ring(bm, mat):
    """The collar, swept round from the closed profile between the hole wall and the outer wall."""
    rings = []
    for i in range(SEGS):
        (ix, iy), (ox, oy) = collar_points(2 * math.pi * i / SEGS)
        dx, dy = ox - ix, oy - iy
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        ring_ = []
        for side, off, z in RING_PROFILE:
            if side == "i":
                x, y = ix + ux * off, iy + uy * off
            else:
                x, y = ox - ux * off, oy - uy * off
            ring_.append(bm.verts.new(W(x, y, z)))
        rings.append(ring_)
    n = len(RING_PROFILE)
    for i in range(SEGS):
        r0, r1 = rings[i], rings[(i + 1) % SEGS]
        for k in range(n):
            f = bm.faces.new((r0[k], r1[k], r1[(k + 1) % n], r0[(k + 1) % n]))
            f.material_index = mat


def flat_width(t):
    (ix, iy), (ox, oy) = collar_points(t)
    return math.hypot(ox - ix, oy - iy) - 0.34 - 0.3


def bolt(bm, x, y, z, r, h, mat, sides=6):
    lo = [bm.verts.new(W(x + r * math.cos(2 * math.pi * (k + .5) / sides),
                         y + r * math.sin(2 * math.pi * (k + .5) / sides), z - 0.1)) for k in range(sides)]
    mid = [bm.verts.new(W(x + r * math.cos(2 * math.pi * (k + .5) / sides),
                          y + r * math.sin(2 * math.pi * (k + .5) / sides), z + 0.6 * h)) for k in range(sides)]
    hi = [bm.verts.new(W(x + .72 * r * math.cos(2 * math.pi * (k + .5) / sides),
                         y + .72 * r * math.sin(2 * math.pi * (k + .5) / sides), z + h)) for k in range(sides)]
    for k in range(sides):
        j = (k + 1) % sides
        for a, b, c, d in ((lo[k], lo[j], mid[j], mid[k]), (mid[k], mid[j], hi[j], hi[k])):
            bm.faces.new((a, b, c, d)).material_index = mat
    bm.faces.new(hi).material_index = mat
    bm.faces.new(list(reversed(lo))).material_index = mat


def chaikin(pl, n):
    """Corner cutting, ends kept: the fitted points become a fair curve."""
    pts = [tuple(p) for p in pl]
    for _ in range(n):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]),
                    (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        out.append(pts[-1])
        pts = out
    return pts


def blade_outline():
    """The blade's plan (px, y down) and, per point, whether it is on the cutting edge: the edge,
    then back along an arc under the collar."""
    pts = chaikin(BLADE_EDGE, 3)
    a0 = math.atan2(-(pts[-1][1] - HC[1]), pts[-1][0] - HC[0])  # math angle (y up)
    a1 = math.atan2(-(pts[0][1] - HC[1]), pts[0][0] - HC[0])
    if a1 < a0:
        a1 += 2 * math.pi
    edge = [True] * len(pts)
    n = 24
    for k in range(0, n + 1):
        a = a0 + (a1 - a0) * k / n
        pts.append((HC[0] + BLADE_BACK_R * math.cos(a), HC[1] - BLADE_BACK_R * math.sin(a)))
        edge.append(False)
    return pts, edge


def blade(bm, mat):
    """A plate with a ground cutting edge: a low wall along the edge, a grind up to the spine flat;
    the back (under the collar) is a plain wall to the same height."""
    base, is_edge = blade_outline()
    n = len(base)
    ne = sum(is_edge)
    top = []
    for i in range(n):
        if not is_edge[i]:
            top.append(base[i])
            continue
        p, q = base[max(i - 1, 0)], base[min(i + 1, ne - 1)]
        ex, ey = q[0] - p[0], q[1] - p[1]
        L = math.hypot(ex, ey)
        nx, ny = ey / L, -ex / L  # towards the blade (upper right of the edge, y down)
        top.append((base[i][0] + nx * BLADE_GRIND, base[i][1] + ny * BLADE_GRIND))
    v0 = [bm.verts.new(W(x, y, 0.0)) for x, y in base]
    v1 = [bm.verts.new(W(x, y, BLADE_EDGE_Z if e else BLADE_TOP)) for (x, y), e in zip(base, is_edge)]
    v2 = [bm.verts.new(W(x, y, BLADE_TOP)) for x, y in top]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((v0[i], v0[j], v1[j], v1[i])).material_index = mat
        if is_edge[i] or is_edge[j]:
            bm.faces.new((v1[i], v1[j], v2[j], v2[i])).material_index = mat
    # the back's v1 and v2 coincide: weld them, then close top and bottom
    bmesh.ops.remove_doubles(bm, verts=v1 + v2, dist=1e-6)
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    for f in bm.faces:
        f.material_index = mat
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def mesh_obj(name, bm, mats, coll):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def drill_notch(obj, coll):
    """Boolean the notch's drilled hole out of the blade (exact solver)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=R_NOTCH / 12, radius2=R_NOTCH / 12, depth=4 / 12)
    bmesh.ops.translate(bm, vec=W(NC[0], NC[1], 1.0), verts=bm.verts)
    cutter = mesh_obj("notch_cutter", bm, [], coll)
    mod = obj.modifiers.new("notch", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    common._apply_modifiers(obj)
    bpy.data.objects.remove(cutter, do_unlink=True)


def build(sprite):
    coll = common.reset_collection(NAME)
    # One shade per frame, read off the same pixels of every frame: {sprite frame: palette index}.
    shades = {19: 67, 38: 69, 76: 74, 95: 77}
    ring_mat = common.palette_material(sprite, 72, f"{NAME}-ring", frames=shades, metallic=0.35, roughness=0.42)
    blade_mat = common.palette_material(sprite, 72, f"{NAME}-blade", frames=shades, metallic=0.4, roughness=0.3)
    bm = bmesh.new()
    blade(bm, 0)
    bl = mesh_obj(f"{NAME}_blade", bm, [ring_mat, blade_mat], coll)
    for p in bl.data.polygons:
        p.material_index = 1
    drill_notch(bl, coll)
    for p in bl.data.polygons:
        p.material_index = 1
    bm = bmesh.new()
    ring(bm, 0)
    nb = 0
    for k in range(10):  # bolt heads on the collar's flat top, where it is wide enough
        t = math.radians(18 + 36 * k)
        if flat_width(t) < 0.75:
            continue
        (ix, iy), (ox, oy) = collar_points(t)
        f = (0.34 + 0.5 * flat_width(t)) / math.hypot(ox - ix, oy - iy)
        bolt(bm, ix + (ox - ix) * f, iy + (oy - iy) * f, TOP_Z, 0.26, 0.16, 0)
        nb += 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    obj = mesh_obj(NAME, bm, [ring_mat, blade_mat], coll)
    print(f"{NAME}: {nb} bolts")
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bl.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
    me = obj.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35))
    return obj, coll


def tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def measure(obj, out_dir, k=16):
    """A flat white top view of the model alone on the sprite's 12 x 14 grid, k texels per px
    (tools/sprite_mask.py <name> --frame F --measure DIR/top.png gives the rule's IoU)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH" and o is not obj:
            o.hide_render = True
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "SINGLE"
    sh.single_color = (1, 1, 1)
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    cd = bpy.data.cameras.new("measure")
    cd.type = "ORTHO"
    cd.ortho_scale = 14 / 12
    cam = bpy.data.objects.new("measure", cd)
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 5)
    scene.camera = cam
    scene.render.resolution_x = 12 * k
    scene.render.resolution_y = 14 * k
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(out_dir / "top.png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in scene.objects:
        o.hide_render = False
    print("measure: wrote", out_dir / "top.png")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv
    sprite = common.load_sprite(ROOT, NAME)
    obj, coll = build(sprite)
    print(f"{NAME}: {tris(obj)} triangles")
    if "--measure" in argv:
        measure(obj, argv[argv.index("--measure") + 1])
    shell = common.outline_shell(obj, coll, voxel=0.007, faces=900, smooth=4, inside=0.01)
    print(f"{NAME}: outline {tris(shell)} triangles")
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"])
    if "--preview" in argv:
        out = argv[argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][2]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])
    if "--frames" in argv:
        common.render_frame_previews([obj], argv[argv.index("--frames") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
