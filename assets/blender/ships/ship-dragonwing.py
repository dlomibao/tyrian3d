"""Dragonwing (player 2's ship in a two-player game: tyrian.shp#8 frames 13 and 51 drawn side by
side as one 48x28 object, and their banking frames 9-17 / 47-55): a 3D version of its sprite.

A broad bronze craft, nose up the screen. A boxy central hull carries a dark sunken cockpit
framed by two bright ridges; low wings run out from it to a pointed fin at each side, and on each
wing sits a tall rounded nacelle with a bright highlight along its top. Behind the hull a red,
striped engine block glows. Symmetric about column 24.5 (pixel edges); the origin is the middle
of the 48x28 block. The banking frames only move the highlights, so the model rolls instead
(src/render/spriteModels.ts `group`).

Run: blender --background --python assets/blender/ships/ship-dragonwing.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b141 import dome, loft, slab, tube  # noqa: E402

NAME = "ship-dragonwing"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 24.5  # the centreline (pixel edges): the cockpit, the engine block and the two nacelles


def mir(c):
    return 2 * AXIS - c


# Left wing outline, tip to centre, (col, row) pixel edges; mirrored for the right wing.
WING_FRONT = [(1.0, 15.6), (3.0, 13.2), (5.0, 12.0), (13.0, 10.2), (17.0, 9.6), (AXIS, 9.6)]
WING_BACK = [(AXIS, 19.8), (16.0, 19.8), (13.5, 19.4), (5.0, 19.2), (3.0, 18.0), (1.0, 16.8)]

# Nacelle loft along the rows: (row, half width, half height) in pixels, centred on column 9.
NACELLE = [(6.2, 0, 0), (6.6, 1.8, 1.2), (7.6, 3.0, 2.0), (9.5, 3.8, 2.5), (13.0, 4.2, 2.7), (17.0, 4.1, 2.6),
           (19.6, 3.6, 2.3), (21.2, 2.6, 1.7), (21.8, 0, 0)]
NACELLE_COL = 9.0

# Central hull, along the rows: (row, half width, half height, z).
HULL = [(7.2, 0, 0, 1.8), (7.6, 4.8, 1.6, 1.8), (9.0, 6.6, 2.0, 1.8), (12.0, 7.4, 2.1, 1.8), (16.5, 7.6, 2.1, 1.8),
        (19.5, 7.2, 1.9, 1.6), (20.8, 6.0, 1.5, 1.4), (21.2, 0, 0, 1.4)]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(25, metallic=0.55, roughness=0.4),  # 0 wings
        pal(27, metallic=0.6, roughness=0.35),  # 1 hull
        pal(27, metallic=0.6, roughness=0.3),  # 2 nacelles
        pal(31, metallic=0.6, roughness=0.25),  # 3 bright ridges and highlights
        pal(17, metallic=0.2, roughness=0.15),  # 4 cockpit glass
        pal(116, metallic=0.2, roughness=0.4, emission_strength=2.5),  # 5 red engine block
        pal(122, metallic=0.1, roughness=0.4, emission_strength=3.5),  # 6 orange engine stripes
        pal(19, metallic=0.4, roughness=0.6),  # 7 dark seams and wing edges
        pal(21, metallic=0.5, roughness=0.45),  # 8 wing fins
    ]
    WINGM, HULLM, NAC, BRIGHT, GLASS, RED, ORANGE, DARK, FIN = range(9)
    bm = bmesh.new()

    # Wings: one flat bevelled slab across the whole span, under the hull and nacelles.
    outline = (WING_FRONT + [(mir(c), r) for c, r in reversed(WING_FRONT[:-1])]
               + [(mir(c), r) for c, r in reversed(WING_BACK[1:])] + WING_BACK)
    slab(bm, outline, -0.2, 2.4, mat=WINGM, bevel=0.9)

    # Outboard fins: a darker ridge from each nacelle out to the wing tip.
    for cc in (lambda c: c, mir):
        tube(bm, [(cc(5.2), 13.6, 1.4, 0.6, 1.3), (cc(3.0), 15.4, 1.0, 0.45, 1.0), (cc(1.4), 16.2, 0, 0, 0.8)],
             sides=6, mat=FIN, power=0.7)

    # Central hull: a squared-off loft, flat on top, from the nose bumps to the engine block.
    loft(bm, [(r, AXIS, w, h, z) for r, w, h, z in HULL], sides=16, mat=HULLM, power=0.55)

    # Two bright ridges flanking the cockpit (columns 20 and 29, rows 7-15).
    for c in (20.4, mir(20.4)):
        tube(bm, [(c, 7.3, 0, 0, 3.1), (c, 7.9, 1.1, 0.9, 3.3), (c, 12.0, 1.1, 0.9, 3.5), (c, 15.5, 0.9, 0.7, 3.2),
                  (c, 16.4, 0, 0, 3.0)], sides=8, mat=BRIGHT, power=0.8)

    # Cockpit: a dark glass dome sunk into the hull top (columns 21-27, rows 11-14).
    dome(bm, AXIS, 12.6, 3.2, 1.8, 0.9, z=3.3, rings=4, sides=16, mat=GLASS)
    # Its bright frame along the front edge (row 11, columns 22-25).
    tube(bm, [(AXIS - 2.6, 10.9, 0.4, 0.35, 3.75), (AXIS, 10.6, 0.45, 0.4, 3.85), (AXIS + 2.6, 10.9, 0.4, 0.35, 3.75)],
         sides=6, mat=BRIGHT)
    # A dark seam across the hull's rear (row 19), where the engine block starts.
    tube(bm, [(AXIS - 6.5, 19.2, 0.4, 0.3, 3.0), (AXIS + 6.5, 19.2, 0.4, 0.3, 3.0)], sides=4, mat=DARK)

    # Nacelles on the wings, with a bright highlight along the top of each (columns 7-8).
    for cc in (lambda c: c, mir):
        loft(bm, [(r, cc(NACELLE_COL), w, h, 2.4) for r, w, h in NACELLE], sides=16, mat=NAC, power=0.85)
        tube(bm, [(cc(8.0), 6.9, 0, 0, 4.6), (cc(8.0), 7.8, 0.7, 0.4, 5.2), (cc(8.0), 11.5, 0.7, 0.4, 5.6),
                  (cc(8.0), 15.0, 0.5, 0.3, 5.5), (cc(8.0), 16.0, 0, 0, 5.3)], sides=6, mat=BRIGHT)
        # The dark notch between the nacelle's tail and the hull (rows 19-21, columns 13-16).
        tube(bm, [(cc(14.6), 19.0, 1.0, 0.4, 1.5), (cc(14.6), 21.0, 1.0, 0.4, 1.5)], sides=4, mat=DARK, power=0.6)

    # Engine block behind the hull (columns 19-30, rows 20-25): red, with three orange stripes.
    loft(bm, [(20.0, AXIS, 5.6, 1.8, 1.2), (24.6, AXIS, 5.2, 1.6, 1.0), (25.4, AXIS, 4.4, 1.2, 1.0),
              (25.6, AXIS, 0, 0, 1.0)], sides=12, mat=RED, power=0.5)
    for c in (AXIS - 2.0, AXIS, AXIS + 2.0):
        tube(bm, [(c, 21.0, 0.45, 0.35, 2.75), (c, 24.8, 0.45, 0.3, 2.45)], sides=6, mat=ORANGE)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = next(f for f in sprite["frames"] if f["image"].endswith("-13.png"))
        ref = ROOT / "reference" / "models" / NAME / frame["image"]
        common.render_preview([obj], out, ref, size=(frame["width"], frame["height"]))


if __name__ == "__main__":
    main()
