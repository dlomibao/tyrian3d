"""Grey rail pod (newsh2.shp frame 271): a 3D version of its sprite.

Seen in episode 1 (levels 1.28, 1.3, 1.36) and episode 3. It flies sideways with its nose to the
left of the screen: a round, bullet-shaped steel pod (a nose cap split from the body by a seam ring
with vent slots), a brown armour collar round its rear half, a recessed sensor bay framed in armour
on top holding a dark housing with two glowing red glass lenses, a small brass plate ahead of the
bay, and a round engine at the tail (a flange, a grooved drum and a nozzle). Two flat grey rails run
alongside, above and below it on the screen: dark framed bars with a lighter bar set in a groove,
each carried by an angular brown arm that bends out to the back, and a grey post from the arm in
to the engine. Shapes and positions are traced from the concept (textures/newsh2-271/concept.png,
registered on the sprite) inside the sprite's outline; the features are listed in
assets/blender/features/newsh2-271.json. The sprite is mirror symmetric about row edge 13.5.
One frame, one model.

Run: blender --background --python assets/blender/enemies/newsh2-271.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b048 as L  # noqa: E402
from lib_b048 import common  # noqa: E402

NAME = "newsh2-271"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = L.PX
AXIS = 13.5  # row edge the sprite is mirror symmetric about
SQ = 2 ** 0.5  # a 4-sided sweep has its corners at 45 degrees: scale by this for a flat-topped box


def X(c):
    """Sprite column edge (fractions allowed) to X."""
    return (c - 12) / 12


def Y(r):
    """Sprite row edge (fractions allowed) to Y."""
    return L.ey(r)


YA = Y(AXIS)


def plate(bm, pts, z0, z1, bevel, mat):
    """A chamfered plate on a convex outline of (column edge, row edge), heights in px."""
    L.bevel_plate(bm, [(X(c), Y(r)) for c, r in pts], z0 * PX, z1 * PX, bevel * PX, (mat,) * 4)


BAY_FLOOR = 4.6  # px above the axis: the sensor bay's floor (the pod's top is at about 6.5)


def cut_bay(bm, mats, dark):
    """Cut the sensor bay's recess out of the pod's shell (a boolean through a temporary object);
    the recess walls get the dark material."""
    coll = bpy.context.scene.collection
    me = bpy.data.meshes.new("tmp271s")
    bm.to_mesh(me)
    for m in mats:
        me.materials.append(m)
    shell = bpy.data.objects.new("tmp271s", me)
    coll.objects.link(shell)
    cb = bmesh.new()
    x0, x1, y0, y1 = X(10.9), X(18.0), Y(16.4), Y(10.6)
    L.box(cb, x0, y0, x1, y1, BAY_FLOOR * PX, 20 * PX)
    cme = bpy.data.meshes.new("tmp271c")
    cb.to_mesh(cme)
    cb.free()
    cutter = bpy.data.objects.new("tmp271c", cme)
    coll.objects.link(cutter)
    mod = shell.modifiers.new("bay", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    mod.use_self = True
    mod.use_hole_tolerant = True
    dg = bpy.context.evaluated_depsgraph_get()
    ev = shell.evaluated_get(dg)
    out = ev.to_mesh()
    bm.clear()
    bm.from_mesh(out)
    ev.to_mesh_clear()
    for o, m in ((shell, me), (cutter, cme)):
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(m)
    e = 1e-4
    for f in bm.faces:
        c = f.calc_center_median()
        if x0 - e <= c.x <= x1 + e and y0 - e <= c.y <= y1 + e and c.z > BAY_FLOOR * PX - e:
            if abs(f.normal.z) < 0.9 or c.z < BAY_FLOOR * PX + e:
                f.material_index = dark
                f.smooth = False


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.5, roughness=0.45),  # 0 steel pod
        pal(24, metallic=0.45, roughness=0.45),  # 1 brown armour collar, bay frame
        pal(10, metallic=0.65, roughness=0.3),  # 2 engine drum
        pal(3, metallic=0.2, roughness=0.6),  # 3 dark recesses: bay floor, vents, grooves
        pal(4, metallic=0.5, roughness=0.4),  # 4 dark housing, rail bed
        pal(119, metallic=0.2, roughness=0.08, emission_strength=4.0),  # 5 red glass lenses
        pal(121, metallic=0.0, roughness=0.1, emission_strength=5.0),  # 6 orange lens cores
        pal(26, metallic=0.6, roughness=0.3),  # 7 brass plate
        pal(5, metallic=0.55, roughness=0.4),  # 8 rail frames
        pal(7, metallic=0.65, roughness=0.3),  # 9 rail inner bars
        pal(23, metallic=0.35, roughness=0.5),  # 10 brown arms
        pal(9, metallic=0.65, roughness=0.3),  # 11 engine flange, posts
        pal(13, metallic=0.7, roughness=0.25),  # 12 nozzle rim
        pal(6, metallic=0.5, roughness=0.4),  # 13 lens divider
    ]
    HULL, COLLAR, ENGINE, DARK, HOUSING, RED, ORANGE, GOLD, RAILF, RAILB, ARM, FLANGE, RIM, DIV = range(14)
    bm = bmesh.new()  # the pod's shell, cut for the sensor bay below
    K = 0.88  # the pod is round: nearly as tall as it is wide

    def ring(stations, mat, k=K, sides=16, **kw):
        """A round section along X on the axis: (column edge, half width px), height k * width."""
        L.sweep(bm, [(X(c), YA, 0.0, w * PX, k * w * PX) for c, w in stations], sides=sides, mat=mat, **kw)

    # Nose cap: a bullet from the tip (column 0) to the seam ring at column 6.6.
    ring([(0.0, 0.0), (0.12, 1.0), (0.5, 1.9), (1.0, 2.6), (2.0, 3.6), (3.0, 4.4), (4.0, 5.0), (5.0, 5.5),
          (6.0, 5.85), (6.5, 6.0)], HULL)
    # Seam ring between the cap and the body, a dark groove.
    ring([(6.45, 5.5), (7.05, 5.5)], DARK, cap_start=False, cap_end=False)
    # Body to the collar.
    ring([(6.95, 6.3), (7.6, 6.9), (8.5, 7.25), (9.5, 7.4), (13.5, 7.4)], HULL)
    # Brown armour collar round the rear half, proud of the body, rounding off to the engine.
    ring([(13.1, 7.2), (13.3, 7.6), (16.5, 7.6), (17.1, 7.2), (17.7, 6.6), (18.2, 5.9), (18.6, 5.0),
          (18.75, 4.3)], COLLAR)

    cut_bay(bm, mats, DARK)
    hull = bm
    bm = bmesh.new()
    me = bpy.data.meshes.new("tmp271h")
    hull.to_mesh(me)
    hull.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)

    # Vent slots in the seam, above and below the axis on the screen (concept rows 9.5-11, 16-17.5).
    for r0, r1 in ((9.6, 11.2), (15.8, 17.4)):
        L.box(bm, X(6.3), Y(r1), X(7.0), Y(r0), 3.3 * PX, 4.9 * PX, mat=DARK)

    # Sensor bay (concept columns 10.8-18, rows 10.6-16.4), cut into the pod: an armour frame round a
    # dark recess, a raised dark housing in it holding two red glass lenses split by a divider.
    L.box(bm, X(10.9), Y(16.4), X(18.0), Y(10.6), BAY_FLOOR * PX - 0.5 * PX, BAY_FLOOR * PX, mat=DARK)
    zf0, zf1, bv = 3.6, 6.75, 0.3
    plate(bm, [(10.5, 10.9), (11.3, 10.9), (11.3, 16.1), (10.5, 16.1)], zf0, zf1 - 0.1, bv, HULL)  # front rim
    plate(bm, [(17.5, 10.9), (18.3, 10.9), (18.3, 16.1), (17.5, 16.1)], zf0, zf1, bv, COLLAR)  # back rim
    for r0, r1 in ((10.2, 10.95), (16.05, 16.8)):  # side rims: grey over the body, brown on the collar
        plate(bm, [(10.9, r0), (13.4, r0), (13.4, r1), (10.9, r1)], zf0, zf1 - 0.55, bv, HULL)
        plate(bm, [(13.3, r0), (17.9, r0), (17.9, r1), (13.3, r1)], zf0, zf1 - 0.35, bv, COLLAR)
    plate(bm, [(12.9, 11.4), (17.3, 11.4), (17.7, 11.9), (17.7, 15.1), (17.3, 15.6), (12.9, 15.6), (12.5, 15.1),
               (12.5, 11.9)], BAY_FLOOR - 0.2, 5.6, 0.25, HOUSING)
    plate(bm, [(14.2, 11.9), (15.4, 11.9), (15.6, 12.5), (15.6, 14.5), (15.4, 15.1), (14.2, 15.1), (13.9, 14.5),
               (13.9, 12.5)], 5.0, 6.35, 0.25, RED)
    plate(bm, [(16.4, 12.0), (17.2, 12.0), (17.4, 12.6), (17.4, 14.4), (17.2, 15.0), (16.4, 15.0), (16.2, 14.4),
               (16.2, 12.6)], 5.0, 6.3, 0.22, RED)
    plate(bm, [(15.6, 11.6), (16.2, 11.6), (16.2, 15.4), (15.6, 15.4)], 5.0, 6.25, 0.15, DIV)
    for c in (14.75, 16.8):
        L.ellipsoid(bm, X(c), YA, 6.3 * PX, 0.35 * PX, 0.6 * PX, 0.2 * PX, mat=ORANGE, segments=8, rings=3)
    # Brass plate ahead of the bay (concept columns 8.8-10.8, rows 12.9-14.1).
    plate(bm, [(8.8, 12.9), (11.0, 12.9), (11.0, 14.1), (8.8, 14.1)], 5.6, 7.0, 0.2, GOLD)

    # Engine at the tail: flange, drum with a groove ring at column 21, nozzle rim.
    ring([(18.4, 3.9), (18.5, 4.4), (19.4, 4.4), (19.5, 3.8)], FLANGE, k=1.0)
    ring([(19.4, 3.8), (20.8, 3.8), (20.9, 3.2), (21.45, 3.2), (21.55, 3.6), (22.6, 3.6), (23.2, 3.2),
          (23.6, 2.8)], ENGINE, k=1.0)
    ring([(23.5, 2.85), (23.9, 2.65), (24.0, 1.8), (23.8, 0.0)], RIM, k=1.0, sides=12)

    # One rail and its arm (the upper ones on screen), mirrored below.
    side = bmesh.new()

    def splate(pts, z0, z1, bevel, mat):
        L.bevel_plate(side, [(X(c), Y(r)) for c, r in pts], z0 * PX, z1 * PX, bevel * PX, (mat,) * 4)

    # Rail: a dark framed bar (rows 2-5, columns 7.8-17.6) with a lighter bar in its groove.
    splate([(8.2, 2.1), (17.0, 2.1), (17.6, 2.7), (17.6, 4.9), (8.2, 4.9), (7.8, 4.5), (7.8, 2.5)],
           -1.0, 0.35, 0.2, HOUSING)
    splate([(8.0, 2.1), (17.0, 2.1), (17.5, 2.6), (17.5, 2.95), (8.0, 2.95)], -0.2, 0.9, 0.2, RAILF)
    splate([(8.0, 4.05), (17.5, 4.05), (17.5, 4.9), (8.0, 4.9)], -0.2, 0.9, 0.2, RAILF)
    splate([(7.85, 2.95), (8.5, 2.95), (8.5, 4.05), (7.85, 4.05)], -0.2, 0.9, 0.15, RAILF)
    splate([(8.6, 3.05), (16.3, 3.05), (16.3, 3.95), (8.6, 3.95)], 0.0, 0.62, 0.15, RAILB)
    # Brown arm: an angular beam from the rail's back end out to the tail.
    w, h, z = 1.35 * SQ * PX, 0.8 * SQ * PX, 0.15 * PX
    L.sweep(side, [(X(16.2), Y(3.5), z, w, h), (X(18.2), Y(3.5), z, w, h), (X(20.6), Y(6.0), z, w, h),
                   (X(24.0), Y(6.0), z, w * 0.95, h)], sides=4, mat=ARM, smooth=False)
    # Grey post from the arm in to the engine (column 21, rows 6.5-10).
    L.sweep(side, [(X(21.0), Y(6.6), 0.0, 0.6 * PX, 0.6 * PX), (X(21.0), Y(10.3), 0.0, 0.6 * PX, 0.6 * PX)],
            sides=8, mat=FLANGE)
    me = bpy.data.meshes.new("tmp271")
    side.to_mesh(me)
    side.free()
    bm.from_mesh(me)
    for v in me.vertices:
        v.co.y = 2 * YA - v.co.y
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return L.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
