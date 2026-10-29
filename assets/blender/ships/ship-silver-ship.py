"""Silver Ship (player ship, tyrian.shp#8 frame 81 and its banking frames 77-85): a 3D version of
its sprite.

A grey fighter, nose up the screen, built around column 11 of the sprite: a pointed fuselage with
a dark canopy, small swept fins beside the canopy, two side pods hugging the rear fuselage with
red striped engines at their backs, and three ribs on the tail. The banking frames show the pods
sit low beside a raised fuselage.

Built as the concept reads it: the fuselage is a hard, faceted hull (a ridged nose that tapers to a
point, flat flanks) with a separate raised spine deck on top, a flat plate with chamfered edges
from behind the canopy to the tail; the canopy is a glossy dark glass bubble set in a raised frame;
the fins are thin plates; the side pods are faceted armour shells sitting lower than the fuselage;
the tail carries three straight box ribs over a dark recessed block. Hard parts are flat-shaded
so their edges stay crisp; only the round parts (canopy glass, engines and their bands) are smooth.

The ship is polished silver metal, so the sprite's drawn light is left to the game: each part is
one mid-tone grey (the white spots on the deck and the nose ridge are sheen, the dark right flank
is shadow), and no part paints the sprite's dark outline ring (the game draws it). Real markings
stay: the red engine stripes and the grey bands between them, and the dark slots between the ribs.

Run: blender --background --python assets/blender/ships/ship-silver-ship.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b002 import P, X, Y, dome, loft, mirror, slab  # noqa: E402

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
# chamfered top edges; an octagonal armour shell; a box rib with a chamfered top.
RIDGE = [(1, 0), (1, 0.45), (0.5, 0.82), (0, 1), (-0.5, 0.82), (-1, 0.45), (-1, 0)]
PLATE = [(1, 0), (1, 0.55), (0.72, 1), (-0.72, 1), (-1, 0.55), (-1, 0)]
SHELL = [(1, 0.3), (1, 0.68), (0.62, 1), (-0.62, 1), (-1, 0.68), (-1, 0.3), (-0.62, 0), (0.62, 0)]
RIB = [(1, 0), (1, 0.75), (0.55, 1), (-0.55, 1), (-1, 0.75), (-1, 0)]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(11, metallic=0.8, roughness=0.28),  # 0 fuselage hull and nose, polished silver
        pal(13, metallic=0.8, roughness=0.24),  # 1 bright spine deck, polished
        pal(7, metallic=0.75, roughness=0.3),  # 2 side pods
        pal(6, metallic=0.75, roughness=0.3),  # 3 fins; also the dark grey band (row 21)
        pal(2, metallic=0.05, roughness=0.06),  # 4 canopy glass, dark and glossy
        pal(117, metallic=0.3, roughness=0.4, emission_strength=2.0),  # 5 red engines
        pal(10, metallic=0.75, roughness=0.3),  # 6 light grey band between the red stripes (row 19)
        pal(3, metallic=0.4, roughness=0.6),  # 7 dark recessed tail block between the ribs
        pal(9, metallic=0.85, roughness=0.25),  # 8 tail ribs
    ]
    HULL, DECK, POD, FIN, GLASS, RED, BAND, DARK, RIBM = range(9)
    BAND_DK = FIN
    bm = bmesh.new()
    smooth = []  # faces of the round parts; everything else stays flat-shaded and crisp

    # Fuselage, nose (row 0) to the tail (row 21): a hard hull with flat flanks and a ridge down
    # column 11 that the nose tapers to a point along. (row, half width, z0, z1) in px.
    hull = [(-0.1, 0, 0, 0.9), (0.7, 1.5, -0.1, 1.5), (1.6, 2.3, -0.3, 2.1), (3.4, 3.2, -0.6, 2.9),
            (5.0, 3.5, -0.7, 3.3), (9.2, 3.6, -0.8, 3.6), (20.6, 3.5, -0.8, 3.6), (21.4, 3.3, -0.8, 3.0)]
    prism(bm, [(r, AXIS, w, z0, z1) for r, w, z0, z1 in hull], RIDGE, HULL)

    # The canopy: a raised frame (columns 9-13, rows 5-9) holding a glossy dark glass bubble
    # (columns 10-13). The light pixel at column 11, row 6 is its glint: the glass makes it.
    prism(bm, [(4.6, AXIS, 1.3, 2.4, 3.5), (5.3, AXIS, 2.0, 2.4, 3.85), (9.0, AXIS, 2.15, 2.4, 3.95),
               (9.5, AXIS, 2.0, 2.4, 3.85)], PLATE, HULL)
    n = len(bm.faces)
    dome(bm, AXIS, 7.1, 1.65, 2.05, 1.25, z=3.7, rings=4, sides=16, mat=GLASS)
    smooth += list(bm.faces)[n:]

    # The spine deck (columns 9-13, rows 9-21): a flat bright plate raised above the hull, straight
    # sides and chamfered edges, its ends bevelled down.
    prism(bm, [(8.9, AXIS, 1.7, 3.0, 4.0), (9.6, AXIS, 2.45, 3.0, 4.55), (20.2, AXIS, 2.45, 3.0, 4.55),
               (21.1, AXIS, 1.9, 3.0, 3.9)], PLATE, DECK)

    # The tail (rows 21-26): a dark block, recessed, under three straight box ribs (columns 9, 11
    # and 13) with dark slots between them.
    prism(bm, [(20.5, AXIS, 3.3, -0.6, 2.0), (26.0, AXIS, 3.2, -0.6, 1.9), (26.8, AXIS, 2.9, -0.4, 1.4)],
          PLATE, DARK)
    for c in (9.5, 11.5, 13.5):
        prism(bm, [(20.4, c, 0.45, 1.5, 3.5), (25.4, c, 0.45, 1.5, 3.2), (26.4, c, 0.45, 1.5, 2.2)],
              RIB, RIBM)

    # Swept fins beside the canopy (rows 5-10, out to columns 4 and 19): thin flat plates.
    fin = [(9.0, 4.3), (4.2, 8.0), (4.2, 9.8), (8.8, 10.0)]
    for side in (1, -1):
        pts = fin if side == 1 else [(mirror(AXIS, c), r) for c, r in fin]
        slab(bm, pts, 0.25, 0.95, mat=FIN, bevel=0.15)

    # Side pods (rows 10-23, out to columns 2 and 21): faceted armour shells lower than the fuselage,
    # their fronts angled back from the hull. (row, centre col, half width, z0, z1) for the left one.
    pod = [(10.0, 7.6, 0.3, 0.2, 0.9), (10.8, 7.3, 1.1, -0.5, 1.4), (12.4, 6.8, 1.9, -0.9, 2.0),
           (14.0, 6.0, 2.8, -1.2, 2.5), (15.2, 5.6, 3.4, -1.3, 2.75), (20.4, 5.6, 3.4, -1.3, 2.75),
           (21.3, 5.9, 3.0, -1.2, 2.45), (22.6, 6.6, 2.0, -0.9, 1.7)]
    # Red engines set into the pods' backs (columns 5-7, rows 18-25), tapering in toward the tail.
    engine = [(17.6, 6.5, 1.5, 2.8, 0.6), (23.8, 6.6, 1.45, 2.5, 0.3), (24.8, 7.2, 0.9, 1.7, 0.2),
              (25.8, 7.7, 0.35, 0.8, 0.1)]
    for side in (1, -1):
        m = (lambda c: c) if side == 1 else (lambda c: mirror(AXIS, c))
        prism(bm, [(r, m(c), w, z0, z1) for r, c, w, z0, z1 in pod], SHELL, POD)
        n = len(bm.faces)
        loft(bm, [(r, m(c), w, h, z) for r, c, w, h, z in engine], sides=12, mat=RED, power=0.6)
        # Raised grey rings between the red stripes (rows 19 and 21).
        for r, band in ((19.0, BAND), (21.0, BAND_DK)):  # light grey, then mid-dark grey
            loft(bm, [(r, m(6.5), 1.68, 2.98, 0.6), (r + 1.0, m(6.5), 1.68, 2.95, 0.55)],
                 sides=12, mat=band, power=0.6)
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
