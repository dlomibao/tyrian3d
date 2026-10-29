"""Purple armoured pod (newsh2.shp frame 89): a 3D version of its sprite.

Seen in episode 1 (levels 1.25, 1.28, 1.3, 1.36) and episode 3. A deep, boxy purple container with
rounded corners, traced from its concept (assets/blender/features/concepts/newsh2-89.jpg, registered
to the sprite in assets/blender/textures/newsh2-89/concept.png): a faceted blue glass window in a
dark housing at the top edge; a polished metal cage over the upper box (a bar across row 5 that
bends down the flanks, two tall spine bars down the middle, a rectangular bar frame round each side
armour plate, a bar along row 13); a vent in the right flank; a belt of plating across the waist;
and below it the engine bay, a cowl curving round two round ribbed nacelles pointing back, with a
keel of two plates between them. The features are listed in assets/blender/features/newsh2-89.json.
One frame, one model.

Run: blender --background --python assets/blender/enemies/newsh2-89.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b048 as L  # noqa: E402
from lib_b048 import common  # noqa: E402

NAME = "newsh2-89"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = L.PX
AXIS = 12.5  # pixel-edge column of the sprite's centre line

# Everything is traced in sprite pixel edges (column c, row r) from concept.png.
X = lambda c: (c - 12) * PX  # noqa: E731  (the block's centre, x = 0, is pixel edge 12)
Y = L.ey

# Hull cross-section, looking along the pod: (u across -1..1, v bottom 0..top 1). A box: flat
# bottom, steep flanks, a flat top with a chamfer along its edges.
PROFILE = [(0.9, 0.0), (1.0, 0.18), (1.0, 0.8), (0.95, 0.95), (0.88, 1.0),
           (-0.88, 1.0), (-0.95, 0.95), (-1.0, 0.8), (-1.0, 0.18), (-0.9, 0.0)]
# Sections, top edge to bottom edge: (row edge, half width px, top z, bottom z). The outline covers
# the sprite's (its dark ring too; the concept is drawn a pixel inside it). The upper box stands
# 0.44 high to row 14; the waist steps down to 0.4 and the engine bay floor is at 0.2.
TOP_Z, WAIST_Z, BAY_Z = 0.44, 0.40, 0.20  # before LIFT
LIFT = 0.14  # everything is built then raised by this; the hull's floor stays at -0.1
HULL = [(1.0, 7.4, 0.36, 0.02), (1.6, 8.4, 0.40, -0.03), (2.4, 9.4, 0.42, -0.06),
        (3.2, 10.4, 0.43, -0.08), (4.2, 11.1, TOP_Z, -0.1), (5.2, 11.35, TOP_Z, -0.1),
        (14.0, 11.35, TOP_Z, -0.1), (14.01, 11.35, WAIST_Z, -0.1), (16.6, 11.35, WAIST_Z, -0.1),
        (16.61, 11.35, BAY_Z, -0.1), (19.8, 11.35, BAY_Z, -0.1), (20.6, 10.5, BAY_Z, -0.09),
        (21.6, 9.5, BAY_Z, -0.08), (22.6, 8.5, BAY_Z, -0.07), (23.6, 7.5, BAY_Z, -0.06),
        (24.6, 6.5, BAY_Z, -0.05), (25.7, 5.3, 0.18, -0.03)]
BAY_ROW = 16.6


def hull_loft(bm, top_mat, bay_mat):
    rings = [[bm.verts.new((X(AXIS) + u * w * PX, Y(r), zb - LIFT + v * (zt - zb + LIFT))) for u, v in PROFILE]
             for r, w, zt, zb in HULL]
    n = len(PROFILE)
    for (r, *_), r0, r1 in zip(HULL, rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = bay_mat if r >= BAY_ROW - 1e-6 else top_mat
            f.smooth = False
    for f, m in ((bm.faces.new(rings[0]), top_mat), (bm.faces.new(list(reversed(rings[-1]))), bay_mat)):
        f.material_index = m
        f.smooth = False


def plate(bm, outline, z0, z1, bevel, mats, light=(-1, 1)):
    """L.bevel_plate on an outline traced in (column edge, row edge)."""
    if isinstance(mats, int):
        mats = (mats,) * 4
    L.bevel_plate(bm, [(X(c), Y(r)) for c, r in outline], z0, z1, bevel, mats, light=light)


def rect(c0, r0, c1, r1):
    return [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]


def bar(bm, pts, half_w, half_h, mat):
    """A polished metal bar of constant chamfered-square section along (column, row, z) points."""
    L.sweep(bm, [(X(c), Y(r), z, half_w * PX, half_h * PX) for c, r, z in pts], sides=8, mat=mat, smooth=False)


def nacelle(bm, c, mat, rib, dark):
    """A round engine nacelle along the pod (rows 17.3-24.3), ribbed, its nozzle at the rear."""
    r, cz, n = 2.55 * PX, 0.19, 12
    ring = lambda row, k: [(X(c) + k * r * math.cos(a), Y(row), cz + k * r * math.sin(a))  # noqa: E731
                           for a in (2 * math.pi * (i + 0.5) / n for i in range(n))]
    spec = [(17.2, 0.8, mat), (17.7, 1.0, mat), (19.3, 1.0, rib), (19.4, 1.05, rib), (20.3, 1.05, mat),
            (20.4, 1.0, mat), (21.6, 1.0, rib), (21.7, 1.07, rib), (24.2, 1.07, mat), (24.3, 0.82, dark),
            (23.4, 0.7, dark)]
    verts = [[bm.verts.new(p) for p in ring(rw, k)] for rw, k, _ in spec]
    for (_, _, m), a, b in zip(spec[1:], verts, verts[1:]):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((a[i], a[j], b[j], b[i]))
            f.material_index = m
            f.smooth = True
    for f, m in ((bm.faces.new(list(reversed(verts[0]))), mat), (bm.faces.new(verts[-1]), dark)):
        f.material_index = m
        f.smooth = False


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(87, metallic=0.4, roughness=0.45),  # 0 upper box
        pal(83, metallic=0.35, roughness=0.5),  # 1 engine bay floor, lower hull
        pal(90, metallic=0.45, roughness=0.4),  # 2 side armour plates
        pal(91, metallic=0.75, roughness=0.3),  # 3 cage bars (polished metal)
        pal(58, metallic=0.3, roughness=0.06),  # 4 window glass (dark, glossy)
        pal(128, metallic=0.3, roughness=0.06),  # 5 glass facets
        pal(85, metallic=0.45, roughness=0.4),  # 6 engine nacelles, window housing
        pal(80, metallic=0.1, roughness=0.8),  # 7 nozzle interiors, vent
        pal(84, metallic=0.4, roughness=0.45),  # 8 nacelle ribs, cowl sides
        pal(93, metallic=0.75, roughness=0.28),  # 9 spine bars (the brightest metal)
        pal(86, metallic=0.4, roughness=0.45),  # 10 belt, cowl, keel
        pal(92, metallic=0.75, roughness=0.3),  # 11 spine bar flanks
    ]
    UPPER, BAY, PLATE, BAR, GLASS, FACET, POD, DARK, RIB, SPINE, BELT, SPINE_SIDE = range(12)
    bm = bmesh.new()
    hull_loft(bm, UPPER, BAY)

    # Window at the top edge: a dark chamfered housing (cols 8-17, rows 0.15-4.6, covering the
    # sprite's top outline) holding a faceted glass block with bevelled ends.
    plate(bm, [(8.0, 0.15), (17.0, 0.15), (17.0, 3.6), (16.0, 4.6), (9.0, 4.6), (8.0, 3.6)],
          0.15, 0.5, 0.025, POD)
    plate(bm, [(8.7, 0.95), (16.3, 0.95), (16.3, 3.2), (15.45, 4.05), (9.55, 4.05), (8.7, 3.2)],
          0.3, 0.58, 0.06, (GLASS, FACET, GLASS, GLASS), light=(0, 1))

    # Cage. The top bar across row 5.6, bending down both flanks where the box's corners round off.
    bz = TOP_Z + 0.035
    bar(bm, [(1.7, 9.6, 0.33), (1.9, 7.8, bz - 0.02), (2.7, 6.3, bz), (4.0, 5.6, bz), (21.0, 5.6, bz),
             (22.3, 6.3, bz), (23.1, 7.8, bz - 0.02), (23.3, 9.6, 0.33)], 0.72, 0.5, BAR)
    # Spine bars: two tall bars down the middle (cols 10-11 and 13-14), over the top bar, their
    # lower ends chamfered at row 15.
    for c0, c1 in ((10.0, 11.05), (13.0, 14.05)):
        plate(bm, [(c0, 4.7), (c1, 4.7), (c1, 15.0), (c1 - 0.3, 15.5), (c0 + 0.3, 15.5), (c0, 15.0)],
              TOP_Z - 0.03, TOP_Z + 0.15, 0.03, (SPINE, SPINE, SPINE_SIDE, SPINE_SIDE))
    # Bar frames round the side armour plates (left cols 5-6, right cols 18-19, rows 7-13.8) and the
    # bar along row 13 that joins them behind the spines.
    fz0, fz1 = TOP_Z - 0.02, TOP_Z + 0.075
    for c0, c1, stub in ((5.0, 5.95, (5.0, 6.5)), (18.05, 19.0, (17.55, 19.0))):
        plate(bm, rect(c0, 6.95, c1, 13.85), fz0, fz1, 0.02, BAR)
        plate(bm, rect(stub[0], 6.95, stub[1], 7.45), fz0, fz1, 0.02, BAR)
    plate(bm, [(5.0, 12.95), (19.0, 12.95), (19.0, 13.85), (5.0, 13.85)], fz0, fz1 - 0.01, 0.02, BAR)
    # Armour plates inside the frames.
    plate(bm, rect(5.95, 7.45, 10.0, 12.95), TOP_Z - 0.02, TOP_Z + 0.045, 0.025, PLATE)
    plate(bm, rect(14.05, 7.45, 18.05, 12.95), TOP_Z - 0.02, TOP_Z + 0.045, 0.025, PLATE)
    # Vent in the right flank (cols 20.9-21.9, rows 8.4-12.8): a dark recess with three slats.
    plate(bm, rect(20.7, 8.2, 22.1, 13.0), TOP_Z - 0.05, TOP_Z + 0.012, 0.01, RIB)
    plate(bm, rect(20.95, 8.45, 21.85, 12.75), TOP_Z - 0.02, TOP_Z + 0.016, 0.005, DARK)
    for r in (9.3, 10.4, 11.5):
        L.box(bm, X(21.0), Y(r + 0.35), X(21.8), Y(r), TOP_Z - 0.02, TOP_Z + 0.014, mat=RIB)

    # Waist belt (rows 14-16.6): a band of plating wrapping round the box, its lower edge curving
    # down the flanks, with a lit lip in the middle (row 16).
    belt = [(1.25, 14.05), (23.75, 14.05), (23.75, 19.6), (22.8, 17.9), (21.0, 17.0), (18.0, 16.6),
            (7.0, 16.6), (4.0, 17.0), (2.2, 17.9), (1.25, 19.6)]
    plate(bm, belt, BAY_Z, WAIST_Z + 0.025, 0.025, BELT)
    plate(bm, rect(8.6, 15.95, 16.4, 16.75), WAIST_Z - 0.02, WAIST_Z + 0.05, 0.02, PLATE)

    # Cowl: the bay's outer shell curving round the outside of each nacelle.
    for side in (1, -1):
        m = (lambda c: c) if side == 1 else (lambda c: 2 * AXIS - c)  # noqa: E731
        cowl = [(1.25, 17.0), (4.0, 17.0), (3.5, 18.0), (3.2, 19.3), (3.3, 20.6), (3.8, 21.6),
                (3.0, 21.6), (2.0, 20.6), (1.25, 19.8)]
        out = [(m(c), r) for c, r in cowl]
        if side == -1:
            out.reverse()
        plate(bm, out, BAY_Z - 0.05, 0.34, 0.03, (BELT, BELT, RIB, RIB))

    # Engines: two round ribbed nacelles pointing back (centres at cols 7.3 and 17.7).
    for c in (7.3, 17.7):
        nacelle(bm, c, POD, RIB, DARK)
    # Keel: two plates between the nacelles (cols 10-12 and 13-14.5, rows 16.6-24.9), the dark
    # groove between them the bay floor.
    plate(bm, [(10.0, 16.6), (12.05, 16.6), (12.05, 24.5), (11.7, 24.95), (10.3, 24.95), (10.0, 24.5)],
          BAY_Z - 0.05, 0.37, 0.03, (BELT, BELT, RIB, RIB))
    plate(bm, [(12.95, 16.6), (14.6, 16.6), (14.6, 24.5), (14.3, 24.95), (13.25, 24.95), (12.95, 24.5)],
          BAY_Z - 0.05, 0.37, 0.03, (BELT, BELT, RIB, RIB))

    for v in bm.verts:
        v.co.z += LIFT
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
