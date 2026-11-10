"""Blimp mine (newshi.shp frames 19, 38, 57, 76, 95): a glossy dark-red sphere with a bore through it.

What it is (scratch object-audit/behaviour.txt, D120): enemy type 511, launched only by the SAVARA
blimp's pieces (newshi 79/81/115/121) in 1.8, 1.12, 1.17 SAVARA and 3.10 SAVARA Y; it never moves
(mv 0, 0) and sits on the water after the blimp drifts on, armour 2. Its 18-step frame cycle
19-38-57-76-95-76-57-38 only brightens dark red to pink and back (a pulse); nothing rotates. So it
is a floating mine: a round ball, with an equator seam, pulsing through the palette.

The sprite is authoritative for the top view: an outer rim, an inner ink line and a see-through
centre (the ground shows there, palette 0) with a bright comma at the upper right. Read as a ball,
the rim and comma are its lit top (the brightest pixels sit upper right, the light's side; they are
sheen, not geometry), and the see-through centre is a bore through it: the ball is cut through,
top to bottom, along the sprite's transparent region and its ink (tools/sprite_mask.py inner mask).
The bore's plan is the earlier fit (scratch fix1/n19/fit19b.py, grid IoU 1.0 on frames 19-76):
  ball    outline circle centre (6.01, 7.01) r 5.88, half height 0.9 r, resting on the water
  bore    the circle centre (6.37, 6.52) r 4.69 minus the comma's plan (its edge a fair curve from
          (3.79, 3.51) down to (8.0, 8.2), hooking back to (7.3, 10.7)), plus a small round end
          centre (8.77, 9.76) r 0.97 (the sprite's see-through pixel at (8, 9))
  seam    a band round the equator on the outline circle, one shade darker
  colour  one palette material stepping through the frames' shades: medians 67, 69, 72, 74, 77
          (frames 19, 38, 57, 76, 95; palette_material frames=, D17); the seam a step darker; the
          bore's walls the dark step under the sprite's inner ink (64, 65, 67, 69, 70), so the cut
          reads as a dark well into the ball from the tilted camera (unseen from straight above)

Units: Blender X = (x - 6) / 12, Y = (7 - y) / 12, Z = z / 12 (sprite px, y down, z up).
The underside is the ball's own round bottom, no detail. No texture bake: at 12 px the maps would
not show, so there is no textures folder. Outline shell for the game's ink (D51), held a hair
inside the model (inside=).

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

RC, R_OUT = (6.013, 7.012), 5.882        # the ball's outline (px, y down)
HC, R_HOLE = (6.373, 6.516), 4.685       # the circle the bore is cut from
NC, R_NOTCH = (8.769, 9.761), 0.971      # the small round end of the bore by the hook's tail
# The hook's edge (px, y down), tip first: the bore is the circle above minus the plan to the upper
# right of this curve (the sprite's bright comma, which is the ball's lit top seen past the bore).
BLADE_EDGE = [(3.794, 3.51), (4.234, 4.607), (5.593, 5.352), (6.879, 6.209), (7.779, 7.184), (7.986, 8.194),
              (7.201, 9.176), (7.302, 10.694)]
BLADE_BACK_R = R_HOLE + 0.5
RZ = 0.9 * R_OUT       # the ball's half height: a little oblate, it rides low
ZC = RZ                # its centre: the bottom just touches the water
SEAM_H = 0.42          # half height of the equator seam band (px)
SHELL_SINK = 0.006     # the outline shell held this far (BU) under the ball (sink)
SEAM_IN = 0.14         # the shell sits this far inside the band, so the band reads as a seam


def W(x, y, z):
    return Vector(((x - CX) / 12, (CY - y) / 12, z / 12))


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
    """The hook's plan (px, y down) and, per point, whether it is on the cutting edge: the edge,
    then back along an arc outside the bore circle."""
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


def mesh_obj(name, bm, mats, coll):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def prism(name, pts, z0, z1, coll):
    """A vertical prism over a closed plan (px, y down)."""
    bm = bmesh.new()
    lo = [bm.verts.new(W(x, y, z0)) for x, y in pts]
    hi = [bm.verts.new(W(x, y, z1)) for x, y in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_obj(name, bm, [], coll)


def circle(c, r, n=96):
    return [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def boolean(obj, cutter, op):
    mod = obj.modifiers.new(op.lower(), "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = cutter
    common._apply_modifiers(obj)
    bpy.data.objects.remove(cutter, do_unlink=True)


def ball(coll, mat):
    """The shell: an oblate sphere a hair inside the seam band's radius."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=1.0)
    r = (R_OUT - SEAM_IN) / 12
    for v in bm.verts:
        v.co = Vector((v.co.x * r, v.co.y * r, v.co.z * RZ / 12))
    bmesh.ops.translate(bm, vec=W(RC[0], RC[1], ZC), verts=bm.verts)
    for f in bm.faces:
        f.material_index = 0
    return mesh_obj(NAME, bm, [mat], coll)


def seam(coll, mat):
    """The equator seam: a band with rounded edges, its outer face on the ball's outline."""
    prof = [(-SEAM_IN - 0.05, -SEAM_H), (-0.06, -SEAM_H), (0.0, -SEAM_H + 0.12), (0.0, SEAM_H - 0.12),
            (-0.06, SEAM_H), (-SEAM_IN - 0.05, SEAM_H)]
    segs = 192
    bm = bmesh.new()
    rings = []
    for i in range(segs):
        t = 2 * math.pi * i / segs
        c, s = math.cos(t), math.sin(t)
        rings.append([bm.verts.new(W(RC[0] + (R_OUT + dr) * c, RC[1] + (R_OUT + dr) * s, ZC + dz)) for dr, dz in prof])
    n = len(prof)
    for i in range(segs):
        a, b = rings[i], rings[(i + 1) % segs]
        for k in range(n):
            bm.faces.new((a[k], b[k], b[(k + 1) % n], a[(k + 1) % n])).material_index = 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_obj(f"{NAME}_seam", bm, [mat], coll)


def bore(obj, coll):
    """Cut the bore through the ball, top to bottom: the circle minus the hook's plan, plus the
    small round end by the tail (the sprite's see-through pixels and their ink)."""
    z0, z1 = -2.0, 2 * ZC + 2.0
    cut = prism("bore", circle(HC, R_HOLE), z0, z1, coll)
    hook, _ = blade_outline()
    boolean(cut, prism("hook", hook, z0 - 1, z1 + 1, coll), "DIFFERENCE")
    boolean(cut, prism("notch", circle(NC, R_NOTCH, 40), z0, z1, coll), "UNION")
    boolean(obj, cut, "DIFFERENCE")


def build(sprite):
    coll = common.reset_collection(NAME)
    # One shade per frame, read off the same pixels of every frame (the 18-step cycle pulses dark red
    # to pink and back, D17): {sprite frame: palette index}; the seam one step darker.
    shades = {19: 67, 38: 69, 76: 74, 95: 77}
    seam_shades = {19: 66, 38: 67, 76: 72, 95: 74}
    ball_mat = common.palette_material(sprite, 72, f"{NAME}-ball", frames=shades, metallic=0.3, roughness=0.22)
    seam_mat = common.palette_material(sprite, 69, f"{NAME}-seam", frames=seam_shades, metallic=0.45,
                                       roughness=0.35)
    well_mat = common.palette_material(sprite, 67, f"{NAME}-well", frames={19: 64, 38: 65, 76: 69, 95: 70},
                                       metallic=0.3, roughness=0.5)
    obj = ball(coll, ball_mat)
    bore(obj, coll)
    for p in obj.data.polygons:  # the boolean adds the cutters' empty slot: drop it
        p.material_index = 0
    while len(obj.data.materials) > 1:
        obj.data.materials.pop()
    obj.data.materials.append(well_mat)
    walls = 0
    for p in obj.data.polygons:  # the bore's walls: inside the ball's surface at their height
        c = p.center
        x, y, z = c.x * 12 + CX, CY - c.y * 12, c.z * 12
        rho = (R_OUT - SEAM_IN) * math.sqrt(max(0.0, 1 - ((z - ZC) / RZ) ** 2))
        if math.hypot(x - RC[0], y - RC[1]) < rho - 0.08:
            p.material_index = 1
            walls += 1
    print(f"{NAME}: {walls} bore wall faces")
    sm = seam(coll, seam_mat)
    obj.data.materials.append(seam_mat)
    for p in sm.data.polygons:
        p.material_index = 0
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    sm.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
    me = obj.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(40))
    return obj, coll


def sink(shell, d):
    """Move the outline shell d (BU) in along its normals: on a smooth ball the remeshed shell sits
    almost on the surface and would show through it in any view that draws it (its ink is drawn
    pushed out from it in game, so this only thins the ink by d)."""
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bm.normal_update()
    for v in bm.verts:
        v.co -= v.normal * d
    bm.to_mesh(shell.data)
    bm.free()


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
    shell = common.outline_shell(obj, coll, voxel=0.007, faces=1800, smooth=4, inside=0.01)
    sink(shell, SHELL_SINK)
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
