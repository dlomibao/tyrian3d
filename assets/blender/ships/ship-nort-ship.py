"""Nort ship (player ship, tyrian.shp#8 frames 220 and 222 drawn side by side as one 48x28
object): a 3D version of its sprite, its parts placed where the concept
(assets/blender/features/concepts/ship-nort-ship.jpg, registered to the sprite in
assets/blender/textures/ship-nort-ship/concept.png) draws them.

A wide grey hard-surface delta built of separate chamfered plates. A pointed nose cowl holds a
dark glass canopy and runs back into a round drum behind the cockpit; behind the drum a raised
spine plate runs down the middle between two big angular body blocks, each with a two-part intake
grille cut into its back and a round engine nozzle trailing behind it. Outside the blocks, across a
dark machinery channel, a long swept wing panel on each side carries a blue band along its
leading edge and ends in a short tip nub. A red gun barrel stands on each shoulder beside the nose,
with a red light at its foot in the channel, and small blue canards sit beside the nose tip.
Polished metal hull: the sprite's highlights are shine. Symmetric about the middle of sprite
column 23; the origin is the middle of the 48x28 block.

Run: blender --background --python assets/blender/ships/ship-nort-ship.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import bmesh  # noqa: E402
import bpy  # noqa: E402

import common  # noqa: E402
import lib_b048 as L  # noqa: E402
from lib_b141 import P, X, Y, dome, loft, tube  # noqa: E402

NAME = "ship-nort-ship"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 23.5  # the middle of sprite column 23 (pixel edges)


def mir(c):
    return 2 * AXIS - c


def shell_top(r):
    """Top of the nose cowl (px) at row r: low at the tip, rising toward the drum."""
    return 1.8 + 0.27 * r


def wing_dz(c):
    """Lift of a wing panel's top (px) at column c: thickest at the root, tapering to the tip."""
    t = min(max((17.9 - abs(c - AXIS)) / (17.9 - 9.2), 0.0), 1.0)
    return 0.4 + 1.0 * t


def plate(bm, outline, z0, z1, bevel, mat, dz=None):
    """A chamfered plate on an outline of (col, row) pixel edges, heights in px; dz(col, row)
    lifts its top."""
    pts = [(X(c), Y(r)) for c, r in outline]
    before = set(bm.verts)
    L.bevel_plate(bm, pts, P(z0), P(z1), P(bevel), (mat,) * 4)
    if dz:
        for v in set(bm.verts) - before:
            if v.co.z > P(z0) + 1e-5:
                v.co.z += P(dz(v.co.x * 12 + 24, 14 - v.co.y * 12))


def ellipse(c, r, rx, ry, n=20):
    return [(c + rx * math.cos(2 * math.pi * i / n), r + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def cut_into(bm, part, cutters, mats, cut_mat):
    """Boolean-subtract boxes from the bmesh `part` and append the result to `bm`. Each cutter is
    (x0, x1, y0, y1, z0, z1) in sprite px edges (cols, rows, heights); the cut walls and floor take
    material index cut_mat."""
    tmp = []

    def obj_from(bmx, name):
        me = bpy.data.meshes.new(name)
        bmx.to_mesh(me)
        bmx.free()
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        tmp.append(ob)
        return ob

    bmesh.ops.remove_doubles(part, verts=part.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(part, faces=part.faces)
    target = obj_from(part, f"{NAME}_cut_target")
    bc = bmesh.new()
    for x0, x1, y0, y1, z0, z1 in cutters:
        res = bmesh.ops.create_cube(bc, size=1.0)
        for v in res["verts"]:
            v.co = ((X(x0) if v.co.x < 0 else X(x1)), (Y(y1) if v.co.y < 0 else Y(y0)),
                    (P(z0) if v.co.z < 0 else P(z1)))
    for f in bc.faces:
        f.material_index = cut_mat
    bmesh.ops.recalc_face_normals(bc, faces=bc.faces)
    cutter = obj_from(bc, f"{NAME}_cutter")
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    if hasattr(mod, "material_mode"):
        mod.material_mode = "INDEX"
    deps = bpy.context.evaluated_depsgraph_get()
    ev = target.evaluated_get(deps)
    me = ev.to_mesh()
    bm.from_mesh(me)
    ev.to_mesh_clear()
    for ob in tmp:
        me = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)


# Left-side outlines traced from the registered concept, (col, row) pixel edges.
WING = [(12.3, 10.1), (14.3, 10.1), (14.3, 10.9), (10.3, 17.4), (10.5, 22.6), (11.0, 24.4), (10.6, 25.0),
        (9.6, 25.0), (8.8, 24.2), (5.9, 21.3), (5.6, 17.4), (6.1, 16.5)]
BLOCK = [(11.1, 19.7), (17.1, 12.3), (19.8, 12.3), (19.8, 23.5), (19.1, 24.0), (11.8, 24.1), (11.0, 23.2)]
GRILLES = [(12.8, 15.9), (16.7, 19.3)]  # intake grille columns, rows 21.0-23.0
NOZZLE_C = 17.4


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    hull = dict(metallic=0.45, roughness=0.4)
    mats = [
        pal(10, **hull),  # 0 wings, body blocks
        pal(11, **hull),  # 1 nose cowl, spine
        pal(10, metallic=0.45, roughness=0.35),  # 2 drum
        pal(4, metallic=0.3, roughness=0.6),  # 3 machinery deck in the channels
        pal(2, metallic=0.0, roughness=0.85),  # 4 grilles, nozzle mouths, recesses
        pal(52, metallic=0.1, roughness=0.06),  # 5 canopy glass
        pal(69, metallic=0.4, roughness=0.35),  # 6 red gun barrels
        pal(70, metallic=0.1, roughness=0.4, emission_strength=2.5),  # 7 red lights
        pal(59, metallic=0.35, roughness=0.35),  # 8 blue band (upper)
        pal(57, metallic=0.35, roughness=0.35),  # 9 blue band (lower), canards
        pal(7, metallic=0.6, roughness=0.35),  # 10 nozzles, gun mounts
        pal(12, metallic=0.55, roughness=0.3),  # 11 bright trim: canopy frame, wing ridge
    ]
    (HULL, COWL, DRUM, DECK, DARK, GLASS, RED, LIGHT, BLUE, BLUE2, NOZ, TRIM) = range(12)
    smooth_mats = {DRUM, GLASS, RED, LIGHT, NOZ}
    bm = bmesh.new()

    # Machinery deck under everything, seen in the channels between wings, guns and blocks.
    plate(bm, [(9.8, 18.0), (15.4, 10.4), (mir(15.4), 10.4), (mir(9.8), 18.0), (mir(9.8), 22.0), (9.8, 22.0)],
          -1.0, 0.4, 0.2, DECK)

    # Nose cowl: a pointed shield from the tip back to the drum, sloping up toward the back.
    cowl = [(23.5, 0.0), (25.2, 0.5), (27.0, 2.2), (28.8, 5.0), (30.8, 7.6), (31.4, 9.9), (30.6, 10.5),
            (16.4, 10.5), (15.6, 9.9), (16.2, 7.6), (18.2, 5.0), (20.0, 2.2), (21.8, 0.5)]
    plate(bm, cowl, -0.5, shell_top(0), 0.6, COWL, dz=lambda c, r: 0.27 * r)
    # Canopy: a bright frame ring set in the cowl holding a dark glossy glass bubble.
    zc = shell_top(5.5)  # cowl top at the canopy's centre
    plate(bm, ellipse(AXIS, 5.5, 3.0, 3.2, 18), zc - 1.0, zc + 0.25, 0.25, TRIM)
    dome(bm, AXIS, 5.5, 2.55, 2.75, 1.7, z=zc + 0.1, rings=5, sides=18, mat=GLASS)

    # Drum behind the cockpit: an elliptical wall and a rounded top, the tallest part, machined:
    # a raised rim band round the wall top and a ring band part-way up the dome.
    DZ = 4.7
    plate(bm, ellipse(AXIS, 11.1, 4.2, 2.9, 24), -0.5, DZ, 0.15, DRUM)
    plate(bm, ellipse(AXIS, 11.1, 4.45, 3.1, 24), DZ - 0.9, DZ + 0.3, 0.2, NOZ)
    dome(bm, AXIS, 11.1, 4.05, 2.75, 2.1, z=DZ, rings=6, sides=24, mat=DRUM, bottom=False)
    k, n = 0.62, 24
    zr = DZ + 2.1 * math.sqrt(1 - k * k)
    ring = [(AXIS + 4.05 * k * math.cos(2 * math.pi * i / n), 11.1 + 2.75 * k * math.sin(2 * math.pi * i / n),
             0.28, 0.32, zr) for i in range(n + 2)]
    tube(bm, ring, sides=6, mat=NOZ)

    # Spine plate down the middle (rows 14-22), a dark vent cut into its foot.
    spine = bmesh.new()
    plate(spine, [(20.1, 13.4), (mir(20.1), 13.4), (mir(20.1), 20.0), (mir(20.9), 21.9), (20.9, 21.9), (20.1, 20.0)],
          -0.5, 4.2, 0.5, COWL)
    cut_into(bm, spine, [(22.3, mir(22.3), 21.0, 21.95, 2.4, 9.0)], mats, DARK)

    for side in (1, -1):
        cc = (lambda c: c) if side == 1 else mir

        def O(pts):
            return [(cc(c), r) for c, r in pts]

        # Swept wing panel (thickest at the root) with its tip nub, the blue leading-edge band and
        # two chevron ridges with a dark groove between them, bending down into the tip prong.
        plate(bm, O(WING), -0.6, 2.0, 0.45, HULL, dz=lambda c, r: wing_dz(c))
        plate(bm, O([(5.0, 17.9), (6.0, 17.6), (6.0, 20.6), (5.0, 20.3)]), 0.0, 2.6, 0.25, NOZ)

        def on_wing(pts, hw, hh, lift):
            return [(cc(c), r, hw, hh, 2.0 + wing_dz(cc(c)) + lift) for c, r in pts]

        tube(bm, on_wing([(12.1, 12.5), (7.6, 17.6)], 0.45, 0.2, -0.05), sides=4, mat=BLUE, power=0.5)
        tube(bm, on_wing([(7.6, 17.6), (7.6, 21.6)], 0.45, 0.2, -0.05), sides=4, mat=BLUE2, power=0.5)
        ridge1 = [(13.2, 12.3), (8.9, 17.5), (8.9, 20.8), (7.3, 22.3)]
        ridge2 = [(13.6, 11.2), (10.1, 16.9), (10.1, 22.0), (8.9, 23.4)]
        groove = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(ridge1, ridge2)]
        tube(bm, on_wing(groove, 0.32, 0.08, -0.02), sides=4, mat=DARK, power=0.5)
        tube(bm, on_wing(ridge1, 0.32, 0.55, 0.35), sides=6, mat=TRIM)
        tube(bm, on_wing(ridge2, 0.32, 0.55, 0.35), sides=6, mat=HULL)

        # Body block with its intake grille (two bays split by a post) cut into its back.
        part = bmesh.new()
        plate(part, O(BLOCK), -0.8, 5.0, 0.8, HULL)
        cuts = []
        for c0, c1 in GRILLES:
            a, b = sorted((cc(c0), cc(c1)))
            cuts.append((a, b, 21.0, 23.0, 3.4, 9.0))
        cut_into(bm, part, cuts, mats, DARK)
        # Grille slats across each bay.
        for c0, c1 in GRILLES:
            for k in range(1, 4):
                rr = 21.0 + 0.5 * k
                tube(bm, [(cc(c0 + 0.1), rr, 0.1, 0.12, 3.8), (cc(c1 - 0.1), rr, 0.1, 0.12, 3.8)], sides=4, mat=NOZ)

        # Engine nozzle trailing behind the block: a housing ring, a banded nozzle, a dark mouth.
        plate(bm, O([(12.0, 23.2), (21.0, 23.2), (21.0, 25.0), (14.0, 25.2), (12.0, 24.8)]), -0.6, 1.4, 0.3, HULL)
        plate(bm, O([(19.6, 21.3), (22.4, 21.3), (22.4, 22.8), (21.9, 24.0), (19.6, 24.0)]), -0.6, 3.4, 0.3, HULL)
        # Nozzle: slimmer (about 78% of the old radius) and longer, mid-grey hull with one darker
        # band; only the mouth is dark.
        S, ZN = 0.78, 1.2
        noz = [(22.8, 3.3, 2.2), (24.4, 3.5, 2.3), (25.4, 3.6, 2.2), (26.5, 3.1, 2.0), (27.5, 2.65, 1.8),
               (28.1, 2.4, 1.6)]

        def nc(r):
            return cc(NOZZLE_C + 0.25 * (r - 23.0))

        loft(bm, [(r, nc(r), w * S, h * S, ZN) for r, w, h in noz], sides=16, mat=HULL, power=0.95)
        loft(bm, [(24.7, nc(24.7), 3.6 * S, 2.35 * S, ZN), (25.2, nc(25.2), 3.65 * S, 2.35 * S, ZN)],
             sides=16, mat=NOZ, power=0.95)
        loft(bm, [(27.8, nc(27.8), 1.7 * S, 1.2 * S, ZN), (28.18, nc(28.18), 1.7 * S, 1.2 * S, ZN)],
             sides=12, mat=DARK, power=0.95)

        # Shoulder gun: a grey mount, a red barrel with a lit tip, a red light at its foot.
        plate(bm, O([(14.7, 8.8), (16.3, 8.8), (16.3, 12.9), (14.7, 12.9)]), -0.5, 2.4, 0.3, NOZ)
        plate(bm, O([(14.1, 6.0), (16.9, 6.0), (16.9, 9.6), (14.1, 9.6)]), -0.5, 1.0, 0.2, DECK)
        tube(bm, [(cc(15.4), 5.2, 0, 0, 3.1), (cc(15.4), 5.4, 0.65, 0.65, 3.1), (cc(15.4), 5.9, 0.75, 0.75, 3.1)],
             sides=10, mat=LIGHT, cap_end=False)
        tube(bm, [(cc(15.4), 5.9, 0.75, 0.75, 3.1), (cc(15.4), 9.4, 0.75, 0.75, 3.1)], sides=10, mat=RED,
             cap_start=False)
        tube(bm, [(cc(15.4), 9.3, 0.88, 0.88, 3.1), (cc(15.4), 10.5, 0.88, 0.88, 3.1)], sides=10, mat=NOZ)
        tube(bm, [(cc(15.4), 10.5, 0.55, 0.55, 3.0), (cc(15.4), 13.0, 0.55, 0.55, 2.9)], sides=10, mat=LIGHT)

        # Blue canards on the nose flanks beside the tip (sprite columns 20 and 27, rows 2-3), standing
        # proud of the cowl.
        plate(bm, O([(19.0, 2.4), (20.6, 1.8), (21.0, 3.9), (19.0, 4.4)]), 1.0, 3.4, 0.2, BLUE)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    for poly in obj.data.polygons:
        poly.use_smooth = poly.material_index in smooth_mats
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = ROOT / "reference" / "models" / NAME / frame["image"]
        common.render_preview([obj], out, ref, size=(frame["width"], frame["height"]))


if __name__ == "__main__":
    main()
