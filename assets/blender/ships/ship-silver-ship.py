"""Silver Ship (player ship, tyrian.shp#8 frame 81 and its banking frames 77-85): a 3D version of
its sprite.

A grey fighter, nose up the screen, built around column 11 of the sprite: a pointed fuselage with
a dark canopy, small swept fins beside the canopy, two side pods hugging the rear fuselage with
red striped engines at their backs, and three ribs on the tail. The banking frames show the pods
sit low beside a raised fuselage.

Built part by part where the concept (assets/blender/features/concepts/ship-silver-ship.jpg,
registered to the sprite in assets/blender/textures/ship-silver-ship/concept.png) draws it, so the
baked concept detail (texture_bake.py) lands on the matching part, inside the sprite's outline: a
hard, faceted fuselage with a pointed nose and dark slatted vents behind the wings; a dark glass
window with chamfered edges in a raised frame; thin swept wings with straight trailing edges; a
raised bright spine deck with a narrow keel down its middle; rounded, faceted armour pods lower
than the fuselage, each cut by a dark bay holding two glowing red light tubes across it (rows 18
and 20) with a grey strut between; angular red engine nozzles behind the pods; and a dark exhaust
block under three straight box ribs at the tail. Hard parts are flat-shaded so their edges stay
crisp; only the round parts (light tubes and nozzles) are smooth.

The ship is polished silver metal, so the sprite's drawn light is left to the game: each part is
one mid-tone grey (the white spots on the deck and the nose ridge are sheen, the dark right flank
is shadow), and no part paints the sprite's dark outline ring (the game draws it). Real markings
stay: the red light tubes and the grey strut between them, and the dark slots between the ribs.

Run: blender --background --python assets/blender/ships/ship-silver-ship.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b002 import P, X, Y, loft, mirror, slab, tube  # noqa: E402

NAME = "ship-silver-ship"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 11.5  # the ship's centreline: the middle of sprite column 11


def prism(bm, sections, profile, mat):
    """Loft a hard-edged cross-section along the sprite's rows. Each section is (row, col, half_w,
    z0, z1) in px; profile is a closed list of (u, v) with u in -1..1 across and v in 0..1 from z0 to
    z1. A section with zero half width is a point at z1 (a tip). Returns the new faces."""
    rings, faces = [], []
    for r, c, hw, z0, z1 in sections:
        y, x = Y(r), X(c)
        if hw == 0:
            rings.append([bm.verts.new((x, y, P(z1)))])
            continue
        rings.append([bm.verts.new((x + P(hw) * u, y, P(z0 + (z1 - z0) * v))) for u, v in profile])
    n = len(profile)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            faces.append(bm.faces.new(face))
    for ring in (rings[0], rings[-1]):
        if len(ring) > 1:
            faces.append(bm.faces.new(ring))
    for f in faces:
        f.material_index = mat
    return faces


# Cross-sections (u across, v up). A hull with flat flanks and a ridge down the middle; a plate with
# chamfered top edges; a rounded, faceted armour shell (the concept's pods); a box rib.
RIDGE = [(1, 0), (1, 0.45), (0.5, 0.82), (0, 1), (-0.5, 0.82), (-1, 0.45), (-1, 0)]
PLATE = [(1, 0), (1, 0.55), (0.72, 1), (-0.72, 1), (-1, 0.55), (-1, 0)]
SHELL = [(1, 0.25), (0.96, 0.62), (0.78, 0.88), (0.42, 1), (-0.42, 1), (-0.78, 0.88), (-0.96, 0.62),
         (-1, 0.25), (-0.7, 0), (0.7, 0)]
RIB = [(1, 0), (1, 0.75), (0.55, 1), (-0.55, 1), (-1, 0.75), (-1, 0)]


def span(sections):
    """(row, outer col, inner col, z0, z1) for the left side to prism sections (row, centre, half)."""
    return [(r, (o + i) / 2, (i - o) / 2, z0, z1) for r, o, i, z0, z1 in sections]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(10, metallic=0.75, roughness=0.32),  # 0 fuselage hull and nose, gunmetal silver
        pal(13, metallic=0.75, roughness=0.28),  # 1 bright spine deck, polished
        pal(7, metallic=0.7, roughness=0.36),  # 2 side pods, dark gunmetal armour
        pal(7, metallic=0.7, roughness=0.34),  # 3 swept wings
        pal(2, metallic=0.05, roughness=0.06),  # 4 canopy glass, dark and glossy
        pal(117, metallic=0.2, roughness=0.4, emission_strength=2.5),  # 5 red light tubes, glowing
        pal(10, metallic=0.75, roughness=0.32),  # 6 light grey strut between the red tubes (row 19)
        pal(3, metallic=0.4, roughness=0.6),  # 7 dark recesses: tail block, light bays, vents
        pal(9, metallic=0.8, roughness=0.28),  # 8 tail ribs
        pal(12, metallic=0.75, roughness=0.28),  # 9 keel down the middle of the deck
        pal(115, metallic=0.25, roughness=0.45, emission_strength=1.2),  # 10 red engine nozzles
    ]
    HULL, DECK, POD, FIN, GLASS, RED, BAND, DARK, RIBM, KEEL, NOZ = range(11)
    bm = bmesh.new()
    smooth = []  # faces of the round parts; everything else stays flat-shaded and crisp

    # Fuselage, nose (row 0) to the tail (row 24), traced from the concept: a pointed nose that
    # widens to the canopy, a narrow neck behind the wings (rows 9-12) and a wider body between the
    # pods. A hard hull with flat flanks and a ridge down column 11. (row, half width, z0, z1) px.
    hull = [(-0.05, 0, 0.2, 1.0), (0.4, 1.3, -0.1, 1.6), (1.4, 2.2, -0.3, 2.3), (3.2, 3.0, -0.5, 2.9),
            (4.6, 3.3, -0.7, 3.3), (9.0, 3.3, -0.8, 3.5), (10.0, 3.6, -0.8, 3.6), (16.0, 3.7, -0.8, 3.6),
            (21.0, 3.6, -0.8, 3.5), (23.0, 3.3, -0.8, 3.0), (24.2, 3.0, -0.7, 2.4)]
    prism(bm, [(r, AXIS, w, z0, z1) for r, w, z0, z1 in hull], RIDGE, HULL)

    # Dark vents in the flanks behind the wings (concept: slatted intakes, columns 8 and 15).
    for side in (1, -1):
        m = (lambda c: c) if side == 1 else (lambda c: mirror(AXIS, c))
        slab(bm, [(m(c), r) for c, r in [(7.85, 9.8), (8.6, 9.8), (8.6, 15.5), (7.85, 15.5)]],
             1.0, 2.6, mat=DARK)

    # The canopy (concept: columns 10.7-12.7, rows 4.8-8.1): a raised frame holding a glossy dark
    # glass window. The light pixel at column 11, row 6 is its glint: the glass makes it.
    prism(bm, [(4.6, AXIS, 1.2, 2.6, 3.6), (5.2, AXIS, 1.75, 2.6, 4.0), (8.3, AXIS, 1.8, 2.6, 4.1),
               (8.9, AXIS, 1.5, 2.6, 3.9)], PLATE, HULL)
    # The glass is a rounded-off rectangular window (concept), raised in the frame with a crisp
    # chamfered top, not a ball.
    glass = [(10.6, 5.6), (11.0, 5.15), (12.0, 5.15), (12.4, 5.6), (12.45, 7.7), (12.1, 8.05),
             (10.9, 8.05), (10.55, 7.7)]
    slab(bm, glass, 3.8, 4.75, mat=GLASS, bevel=0.35)

    # The spine deck (columns 9-14, rows 8.6-22): a flat bright plate raised above the hull, straight
    # sides, chamfered edges, its back end narrowing where the concept's side plates converge.
    prism(bm, [(8.6, AXIS, 1.6, 3.0, 4.1), (9.4, AXIS, 2.4, 3.0, 4.6), (19.5, AXIS, 2.5, 3.0, 4.6),
               (22.2, AXIS, 1.9, 3.0, 4.2)], PLATE, DECK)
    # A narrow raised keel down the middle of the deck (concept: columns 11-12.3, rows 10-22).
    prism(bm, [(9.8, AXIS, 0.3, 4.4, 4.9), (10.8, AXIS, 0.7, 4.4, 5.2), (21.2, AXIS, 0.7, 4.4, 5.2),
               (22.0, AXIS, 0.4, 4.4, 4.8)], PLATE, KEEL)

    # The tail (rows 21-26.9): a dark exhaust block, recessed, under three straight box ribs
    # (columns 9, 11 and 13) with dark slots between them.
    prism(bm, [(21.0, AXIS, 3.45, -0.6, 2.2), (26.2, AXIS, 3.4, -0.6, 2.0), (26.95, AXIS, 3.0, -0.4, 1.4)],
          PLATE, DARK)
    for c in (9.5, 11.5, 13.5):
        prism(bm, [(21.4, c, 0.45, 1.8, 3.4), (25.4, c, 0.45, 1.8, 3.1), (26.5, c, 0.45, 1.8, 2.2)],
              RIB, RIBM)

    # Swept wings beside the canopy (concept: root at column 9 row 4.5, tip at column 4.3 rows
    # 7.4-9.4, straight trailing edge at row 9.4): thin flat plates with crisp edges.
    fin = [(8.8, 3.8), (5.2, 6.9), (4.05, 7.95), (4.05, 9.95), (7.2, 9.95), (9.6, 10.6)]
    for side in (1, -1):
        pts = fin if side == 1 else [(mirror(AXIS, c), r) for c, r in fin]
        slab(bm, pts, 0.7, 1.25, mat=FIN, bevel=0.12)

    # Side pods (concept: rounded armour shells, rows 12-22.5, out to columns 2 and 21), lower than
    # the fuselage and tucked under its flanks. Each is cut by a dark bay (rows 17.7-21) holding two
    # glowing red light tubes, leaving a front shell, an outer rim and a back cowl over the nozzle.
    # (row, outer col, inner col, z0, z1) for the left one.
    pod_front = [(11.9, 6.6, 8.6, 0.2, 1.4), (12.6, 4.9, 8.8, -0.4, 2.2), (13.6, 3.7, 8.9, -0.9, 2.6),
                 (14.8, 2.75, 8.9, -1.2, 2.85), (16.0, 2.15, 8.9, -1.3, 2.95), (17.9, 2.0, 8.9, -1.3, 2.95)]
    pod_rim = [(17.6, 2.0, 5.1, -1.3, 2.95), (21.2, 2.15, 5.1, -1.3, 2.9)]
    pod_back = [(20.9, 2.15, 8.9, -1.3, 2.9), (21.9, 3.0, 8.9, -1.2, 2.6), (22.6, 4.0, 8.9, -1.0, 2.2)]
    for side in (1, -1):
        m = (lambda c: c) if side == 1 else (lambda c: mirror(AXIS, c))
        for part in (pod_front, pod_rim, pod_back):
            prism(bm, [(r, m(c), w, z0, z1) for r, c, w, z0, z1 in span(part)], SHELL, POD)
        # The bay floor, sunk into the pod, and the light grey strut across it at row 19.
        slab(bm, [(m(c), r) for c, r in [(5.0, 17.8), (9.0, 17.8), (9.0, 21.0), (5.0, 21.0)]],
             -0.8, 1.3, mat=DARK)
        slab(bm, [(m(c), r) for c, r in [(5.0, 19.0), (8.9, 19.0), (8.9, 19.95), (5.0, 19.95)]],
             1.2, 1.95, mat=BAND)
        n = len(bm.faces)
        # Two red light tubes lying across the bay (rows 18.4 and 20.4, columns 5.1-8.2).
        for r in (18.45, 20.45):
            tube(bm, [(m(5.1), r, 0.45, 0.45, 2.0), (m(8.4), r, 0.45, 0.45, 2.0)], sides=8, mat=RED)
        # Red engine nozzles behind the pods (rows 22-25.6), tapering in toward the tail.
        nozzle = [(21.8, 6.4, 2.0, 1.5, 0.9), (23.0, 6.5, 1.95, 1.45, 0.8), (24.4, 6.95, 1.45, 1.15, 0.6),
                  (25.6, 7.45, 0.75, 0.7, 0.5)]
        loft(bm, [(r, m(c), w, h, z) for r, c, w, h, z in nozzle], sides=12, mat=NOZ, power=0.55)
        smooth += list(bm.faces)[n:]

    bm.faces.index_update()
    round_faces = {f.index for f in smooth}
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    for poly in obj.data.polygons:
        poly.use_smooth = poly.index in round_faces
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        level = sprite["frames"][len(sprite["frames"]) // 2]
        ref = ROOT / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], out, ref, size=level["size"])


if __name__ == "__main__":
    main()
