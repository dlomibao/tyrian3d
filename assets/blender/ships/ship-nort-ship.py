"""Nort ship (player ship, tyrian.shp#8 frames 220 and 222 drawn side by side as one 48x28
object): a 3D version of its sprite.

A wide grey delta. A pointed nose with a dark canopy, framed by a bright arch, runs into a round
ribbed drum behind the cockpit (about 9 px across, standing about 4 px above the wings) and a
pale raised spine behind it; broad swept wings with a blue leading-edge band (a light-blue
highlight row behind it) and two chevron rails; under each wing root a round engine nacelle
(about 9 px across) swells out behind the trailing edge, with two dark vents cut into its top,
and tapers to a rounded tail. Two short red-tipped guns sit on the shoulders beside the nose. A
thin dark skirt under the wings, nose and nacelles covers the sprite's black outline pixels.
Symmetric about the middle of sprite column 23; the origin is the middle of the 48x28 block.

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
from lib_b141 import P, X, Y, dome, loft, slab, span_wing, tube  # noqa: E402

NAME = "ship-nort-ship"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 23.5  # the middle of sprite column 23 (pixel edges)


def mir(c):
    return 2 * AXIS - c


def lerp_table(table, key, k0=0):
    """Linear interpolation of the rows of `table` (tuples) at table[...][k0] == key."""
    if key <= table[0][k0]:
        return list(table[0])
    for a, b in zip(table, table[1:]):
        if a[k0] <= key <= b[k0]:
            t = (key - a[k0]) / ((b[k0] - a[k0]) or 1)
            return [x + (y - x) * t for x, y in zip(a, b)]
    return list(table[-1])


# Left wing planform, tip to centre: (col, front row, back row, thickness, z mid), pixel edges.
# The main wing stops about a pixel inside the sprite's black outline; SKIRT, a thinner dark
# plate under it, reaches the outline's outer edge.
WING = [
    (5.7, 17.6, 20.6, 0.9, 0.0),
    (6.5, 16.8, 21.5, 1.1, 0.0),
    (7.5, 15.8, 22.4, 1.3, 0.0),
    (8.5, 14.8, 23.3, 1.5, 0.0),
    (9.5, 13.8, 24.2, 1.7, 0.0),
    (10.6, 12.8, 24.2, 1.9, 0.0),
    (11.2, 12.2, 23.0, 2.0, 0.0),
    (12.0, 11.4, 21.8, 2.2, 0.0),
    (13.5, 10.6, 21.4, 2.5, 0.0),
    (15.0, 9.8, 21.4, 2.8, 0.0),
    (16.5, 8.2, 21.4, 3.0, 0.0),
    (18.5, 6.6, 21.4, 3.2, 0.0),
    (AXIS, 6.4, 21.4, 3.4, 0.0),
]
SKIRT = [
    (4.8, 17.3, 20.5, 0.5, -0.45),
    (5.5, 16.6, 21.1, 0.7, -0.5),
    (6.5, 15.7, 22.4, 0.8, -0.55),
    (7.5, 14.7, 23.4, 0.9, -0.6),
    (8.5, 13.7, 24.4, 1.0, -0.65),
    (9.5, 12.7, 25.3, 1.1, -0.7),
    (10.6, 11.7, 25.3, 1.2, -0.75),
    (11.4, 10.8, 24.3, 1.3, -0.8),
    (12.5, 9.8, 22.0, 1.4, -0.85),
    (14.0, 9.4, 22.0, 1.6, -0.9),
    (15.6, 7.6, 22.0, 1.8, -0.95),
    (17.2, 5.9, 22.0, 1.9, -1.0),
    (19.0, 5.0, 22.2, 2.0, -1.0),
    (AXIS, 5.0, 22.4, 2.0, -1.0),
]

# Nose (row, half width, half height, z centre), drum and spine along the axis; power as lofted.
NOSE = [(0.3, 0, 0, 0.9), (0.8, 1.4, 1.0, 0.9), (1.8, 2.4, 1.7, 1.0), (2.8, 3.4, 2.3, 1.1),
        (3.8, 4.3, 2.8, 1.2), (5.0, 4.8, 3.2, 1.3), (6.3, 5.2, 3.5, 1.4), (7.6, 5.0, 3.6, 1.4),
        (8.4, 4.4, 3.4, 1.4)]
NOSE_SKIRT = [(-0.3, 0, 0, 0.6), (0.1, 1.6, 0.6, 0.6), (1.1, 2.6, 1.0, 0.6), (2.1, 3.5, 1.3, 0.6),
              (3.1, 4.6, 1.6, 0.6), (4.2, 5.6, 1.8, 0.6), (5.6, 5.8, 2.0, 0.6), (6.6, 5.6, 2.0, 0.6),
              (7.6, 4.8, 2.0, 0.6)]
NOSE_POW = 0.8
DRUM_Z, DRUM_R, DRUM_H = 2.0, 4.2, 4.1  # round drum behind the cockpit (rows 7-13)
DRUM = [(7.0, 3.3, 3.2, DRUM_Z), (7.4, DRUM_R, DRUM_H, DRUM_Z), (12.6, DRUM_R, DRUM_H, DRUM_Z),
        (13.0, 3.7, 3.6, DRUM_Z)]
DRUM_POW = 0.92
RIBS = [8.9, 10.2, 11.5]  # rib rows behind the bright front ring at 7.6
SPINE = [(13.0, 2.7, 3.3, 1.2), (16.0, 2.7, 3.1, 1.1), (19.0, 2.6, 2.8, 1.0), (20.8, 2.3, 2.3, 0.8),
         (21.6, 1.6, 1.5, 0.6)]
SPINE_POW = 0.75

# Left nacelle (col, row, half width, half height, z centre): under the wing root, swelling out
# behind the trailing edge to a round section about 9.6 px across, then tapering to a rounded
# tail leaning in toward column 18.
POD = [(16.5, 12.8, 0, 0, -1.8), (16.5, 14.0, 2.6, 1.6, -1.8), (16.5, 16.2, 3.8, 2.4, -1.6),
       (16.5, 18.5, 4.4, 3.0, -1.2), (16.5, 20.3, 4.7, 3.8, -0.8), (16.5, 21.6, 4.8, 4.3, -0.6),
       (16.6, 23.0, 4.8, 4.3, -0.6), (16.8, 24.0, 4.0, 3.8, -0.6)]
TAIL = [(16.8, 24.0, 4.0, 3.8, -0.6), (17.5, 25.0, 2.9, 2.9, -0.6), (18.0, 26.0, 2.4, 2.4, -0.6),
        (18.4, 27.0, 1.9, 1.9, -0.6), (18.5, 27.6, 1.3, 1.2, -0.6), (18.5, 27.9, 0, 0, -0.6)]
# The nacelle's dark skirt from row 20 back (col, row, half width, half height, z centre).
POD_SKIRT = [(16.5, 20.3, 5.6, 2.7, -1.9), (16.5, 21.6, 5.7, 3.0, -1.9), (16.6, 23.0, 5.7, 3.0, -1.9),
             (16.6, 24.5, 4.7, 2.6, -1.6), (17.4, 25.5, 3.6, 2.0, -1.3), (17.9, 26.5, 3.1, 1.6, -1.2),
             (18.3, 27.5, 2.5, 1.2, -1.1), (18.4, 27.9, 1.8, 0.9, -1.0), (18.4, 28.1, 0, 0, -1.0)]
POD_POW = 0.95


def ring_top(dx, hw, hh, z, power):
    """Top of a lofted superellipse ring (half width hw, half height hh, centre z) at offset dx."""
    if hw <= 0 or abs(dx) >= hw:
        return None
    return z + hh * (1 - (abs(dx) / hw) ** (2 / power)) ** (power / 2)


def wing_top(c, r, table=WING):
    """Height (px) of the wing's upper surface at column c, row r (the span_wing profile)."""
    if c > AXIS:
        c = mir(c)
    if c < table[0][0]:
        return None
    _, f, b, t, zm = lerp_table(table, c)
    if not f <= r <= b:
        return None
    chord = b - f
    le = min(2.0, 0.22 * chord)
    prof = [(f, 0.0), (f + le, 0.42 * t), (f + 0.38 * chord, 0.5 * t), (f + 0.78 * chord, 0.4 * t), (b, 0.1 * t)]
    for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
        if r0 <= r <= r1:
            return zm + z0 + (z1 - z0) * (r - r0) / ((r1 - r0) or 1)
    return zm


def axial_top(table, c, r, power):
    if not table[0][0] <= r <= table[-1][0]:
        return None
    _, hw, hh, z = lerp_table(table, r)
    return ring_top(c - AXIS, hw, hh, z, power)


def pod_top(c, r):
    if c > AXIS:
        c = mir(c)
    path = POD + TAIL[1:]
    if not path[0][1] <= r <= path[-1][1]:
        return None
    pc, _, hw, hh, z = lerp_table(path, r, k0=1)
    return ring_top(c - pc, hw, hh, z, POD_POW)


def surf(c, r):
    """The highest base surface (wing, nose, drum, spine, nacelle) at column c, row r (px)."""
    hs = [wing_top(c, r), axial_top(NOSE, c, r, NOSE_POW), axial_top(DRUM, c, r, DRUM_POW),
          axial_top(SPINE, c, r, SPINE_POW), pod_top(c, r)]
    hs = [h for h in hs if h is not None]
    return max(hs) if hs else 0.0


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


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.1, roughness=0.5),  # 0 wing and nacelle grey
        pal(7, metallic=0.1, roughness=0.5),  # 1 nose, gun barrels, wing-tip edges
        pal(11, metallic=0.1, roughness=0.4),  # 2 pale spine
        pal(13, metallic=0.2, roughness=0.35),  # 3 bright rails and canopy frame
        pal(5, metallic=0.2, roughness=0.55),  # 4 dark grooves
        pal(57, metallic=0.2, roughness=0.35),  # 5 blue leading-edge band
        pal(1, metallic=0.1, roughness=0.7),  # 6 vents and seams
        pal(52, metallic=0.3, roughness=0.1),  # 7 canopy glass
        pal(70, metallic=0.2, roughness=0.4, emission_strength=2.5),  # 8 red gun lights
        pal(54, metallic=0.2, roughness=0.3),  # 9 blue canards
        pal(2, metallic=0.1, roughness=0.7),  # 10 dark outline skirt
        pal(6, metallic=0.25, roughness=0.5),  # 11 nacelle tails
        pal(59, metallic=0.2, roughness=0.3),  # 12 light-blue highlight row
        pal(10, metallic=0.1, roughness=0.45),  # 13 drum
        pal(12, metallic=0.2, roughness=0.35),  # 14 drum ribs
        pal(61, metallic=0.3, roughness=0.1),  # 15 canopy highlight
        pal(14, metallic=0.2, roughness=0.35),  # 16 brightest rails (inner chevron)
    ]
    (WINGM, NOSEM, SPINEM, RIDGE, GROOVE, BLUE, VENT, GLASS, RED, CANARD, SKIRT_M, TAIL_M, LBLUE, DRUM_M, RIB,
     GLINT, WHITE) = range(17)
    POD_M = WINGM
    BARREL = NOSEM  # gun barrels and wing edges share pal 7
    bm = bmesh.new()

    def mirror_rows(table):
        return [(mir(c), *rest) for c, *rest in reversed(table[:-1])]

    # Wings: the main plate and the dark outline skirt under it, each one loft tip to tip.
    span_wing(bm, WING + mirror_rows(WING), mat=WINGM)
    span_wing(bm, SKIRT + mirror_rows(SKIRT), mat=SKIRT_M)

    # Nose fuselage (and its dark skirt), the drum behind the cockpit with its ribs, the spine.
    loft(bm, [(r, AXIS, w, h, z) for r, w, h, z in NOSE], sides=16, mat=NOSEM, power=NOSE_POW)
    loft(bm, [(r, AXIS, w, h, z) for r, w, h, z in NOSE_SKIRT], sides=12, mat=SKIRT_M, power=0.7)
    loft(bm, [(r, AXIS, w, h, z) for r, w, h, z in DRUM], sides=16, mat=DRUM_M, power=DRUM_POW)
    # Bright front ring (the crossbar of the canopy frame, row 7) and three ribs, about 0.4 px proud.
    for r, m, d in [(7.6, RIDGE, 0.45)] + [(r, RIB, 0.4) for r in RIBS]:
        loft(bm, [(r - 0.3, AXIS, DRUM_R + d, DRUM_H + d, DRUM_Z), (r + 0.3, AXIS, DRUM_R + d, DRUM_H + d, DRUM_Z)],
             sides=16, mat=m, power=DRUM_POW)
    # Dark seam at the drum's back (row 13), then the pale spine down to the notch at row 21.
    loft(bm, [(12.9, AXIS, 3.8, 3.7, DRUM_Z), (13.6, AXIS, 2.9, 3.0, 1.6)], sides=14, mat=VENT, power=0.85)
    loft(bm, [(r, AXIS, w, h, z) for r, w, h, z in SPINE], sides=14, mat=SPINEM, power=SPINE_POW)

    # Canopy: a dark glass dome over columns 21-25, rows 3-7, with a light-blue glint (column 24).
    ztop = surf(AXIS, 5.3)
    dome(bm, AXIS, 5.3, 2.2, 2.1, 1.8, z=ztop - 0.9, rings=4, sides=14, mat=GLASS)
    gz = lambda c, r: ztop - 0.9 + 1.8 * math.sqrt(max(0, 1 - ((c - AXIS) / 2.2) ** 2 - ((r - 5.3) / 2.1) ** 2))  # noqa: E731
    tube(bm, [(24.5, 3.9, 0.35, 0.2, gz(24.5, 3.9) + 0.05), (24.5, 5.6, 0.35, 0.2, gz(24.5, 5.6) + 0.05)],
         sides=4, mat=GLINT)

    for side in (1, -1):
        cc = (lambda c: c) if side == 1 else mir  # column on this side

        def on(path, hw, hh, lift):
            return [(cc(c), r, hw, hh, surf(c, r) + lift) for c, r in path]

        # Canopy frame: the bright arch from the canopy's front corner down its side, continuing
        # as the shoulder ridge out to column 16 row 10.
        tube(bm, on([(21.7, 2.8), (20.8, 4.0), (20.5, 5.5), (19.8, 7.0), (18.6, 8.4), (16.6, 10.6)], 0.6, 0.35, 0.05),
             sides=6, mat=RIDGE, power=0.7)
        # Blue canards beside the nose tip (column 19, rows 2-3).
        tube(bm, [(cc(20.8), 4.4, 0.7, 0.45, 1.7), (cc(19.6), 2.5, 0.7, 0.4, 1.5), (cc(19.3), 1.8, 0, 0, 1.4)],
             sides=6, mat=CANARD)
        # Shoulder gun: red-lit barrel at column 15, rows 5-9, a grey body to row 12, a red light at 12.
        tube(bm, [(cc(15.5), 5.0, 0, 0, 1.2), (cc(15.5), 5.3, 0.8, 0.7, 1.2), (cc(15.5), 9.0, 0.85, 0.75, 1.2)],
             sides=8, mat=RED, cap_end=False)
        tube(bm, [(cc(15.5), 9.0, 0.9, 0.8, 1.2), (cc(15.5), 11.9, 1.0, 0.85, 1.1)], sides=8, mat=BARREL, cap_end=False)
        tube(bm, [(cc(15.5), 11.9, 1.0, 0.85, 1.1), (cc(15.5), 12.9, 0.9, 0.7, 1.0)], sides=8, mat=RED)
        # Dark outline under the gun (columns 14 and 16, rows 5-9).
        tube(bm, [(cc(15.5), 5.0, 0, 0, 0.6), (cc(15.5), 5.6, 1.1, 0.5, 0.6), (cc(15.5), 6.3, 1.3, 0.5, 0.6),
                  (cc(15.5), 10.0, 1.3, 0.5, 0.4)],
             sides=6, mat=SKIRT_M)
        # Dark outline of the notch between the nacelles (columns 21-22, rows 21-23).
        notch = [(20.8, 21.0), (22.9, 21.0), (22.9, 23.0), (22.0, 23.0), (22.0, 24.0), (20.8, 24.0)]
        slab(bm, [(cc(c), r) for c, r in notch], -1.6, 0.0, mat=SKIRT_M)

        # Blue leading-edge band: a darker outer row and a light-blue inner row.
        tube(bm, on([(11.6, 13.4), (8.5, 16.5), (7.4, 17.7), (7.4, 18.8)], 0.55, 0.2, 0.08), sides=4, mat=BLUE)
        tube(bm, on([(11.7, 14.5), (8.6, 17.6)], 0.5, 0.2, 0.1), sides=4, mat=LBLUE)
        # Wing rails: the inner chevron from row 12 down to the trailing edge, and the outer one
        # behind the blue band bending down into the tip prong; a dark groove between them.
        tube(bm, on([(18.9, 12.2), (15.5, 15.6), (12.4, 18.8), (12.1, 20.0), (12.2, 21.0)], 0.6, 0.3, 0.05),
             sides=6, mat=WHITE, power=0.7)
        tube(bm, on([(13.0, 14.0), (10.5, 16.5), (8.8, 18.4), (8.6, 21.0), (9.5, 23.0)], 0.6, 0.3, 0.05),
             sides=6, mat=RIDGE, power=0.7)
        tube(bm, on([(14.4, 14.9), (10.8, 18.4), (10.6, 21.4)], 0.45, 0.15, 0.05), sides=4, mat=GROOVE)
        # Dark channel beside the spine (columns 19-20, rows 13-20).
        tube(bm, on([(20.2, 13.4), (20.2, 16.5), (20.2, 20.9)], 0.9, 0.15, 0.05), sides=4, mat=GROOVE)
        # Grey wing-tip edge (column 6, rows 17-21).
        tube(bm, on([(6.4, 17.4), (6.4, 21.2)], 0.5, 0.3, -0.1), sides=6, mat=BARREL)

        # Engine nacelle: round body (two dark vents cut into its top at rows 21-23, columns 13-15
        # and 17-19), a darker rounded tail, and a dark skirt under it reaching the outline.
        part = bmesh.new()
        # Lofted across the rows (rings square to the sprite's columns) so the leaning tail's
        # outline follows the sprite's rows.
        loft(part, [(r, cc(c), w, h, z) for c, r, w, h, z in POD], sides=16, mat=POD_M, power=POD_POW, cap_end=False)
        loft(part, [(r, cc(c), w, h, z) for c, r, w, h, z in TAIL], sides=16, mat=TAIL_M, power=POD_POW,
             cap_start=False)
        vents = []
        for c0, c1 in ((13.1, 15.9), (17.1, 19.9)):
            a, b = sorted((cc(c0), cc(c1)))
            floor = min(pod_top(c0, 22.0), pod_top(c1, 22.0)) - 0.6
            vents.append((a, b, 21.0, 23.0, floor, 9.0))
        cut_into(bm, part, vents, mats, VENT)
        loft(bm, [(r, cc(c), w, h, z) for c, r, w, h, z in POD_SKIRT], sides=10, mat=SKIRT_M, power=POD_POW)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


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
