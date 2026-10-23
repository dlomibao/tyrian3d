"""Silver Ship (player ship, tyrian.shp#8 frame 81 and its banking frames 77-85): a 3D version of
its sprite.

A grey fighter, nose up the screen, built around column 11 of the sprite: a pointed fuselage with
a dark canopy, small swept fins beside the canopy, two side pods hugging the rear fuselage with
red striped engines at their backs, and three ribs on the tail. The banking frames show the pods
sit low beside a raised fuselage.

Run: blender --background --python assets/blender/ships/ship-silver-ship.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b002 import dome, loft, mirror, slab  # noqa: E402

NAME = "ship-silver-ship"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 11.5  # the ship's centreline: the middle of sprite column 11


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(11, metallic=0.6, roughness=0.35),  # 0 fuselage
        pal(13, metallic=0.6, roughness=0.3),  # 1 bright spine
        pal(8, metallic=0.55, roughness=0.4),  # 2 pods
        pal(7, metallic=0.5, roughness=0.45),  # 3 fins
        pal(2, metallic=0.1, roughness=0.1),  # 4 canopy glass
        pal(117, metallic=0.3, roughness=0.4, emission_strength=2.0),  # 5 red engines
        pal(10, metallic=0.6, roughness=0.35),  # 6 engine bands, tail ribs
        pal(3, metallic=0.4, roughness=0.6),  # 7 dark tail
    ]
    HULL, SPINE, POD, FIN, GLASS, RED, BAND, DARK = range(8)
    bm = bmesh.new()

    # Fuselage, nose (row 0) to the start of the tail (row 21): (row, half width, half height, z) in px.
    hull = [(0.3, 0, 0, 0.6), (1.2, 1.3, 1.0, 0.6), (3.0, 2.1, 1.6, 0.7), (5.0, 2.9, 2.0, 0.7),
            (8.0, 3.4, 2.3, 0.6), (12.0, 3.5, 2.5, 0.4), (17.0, 3.5, 2.5, 0.3), (21.0, 3.5, 2.3, 0.2)]
    loft(bm, [(r, AXIS, w, h, z) for r, w, h, z in hull], sides=14, mat=HULL, power=0.85)
    # The tail (rows 21-26), darker, with three ribs on top (columns 9, 11 and 13).
    loft(bm, [(21.0, AXIS, 3.4, 2.2, 0.2), (25.0, AXIS, 3.2, 1.8, 0.1), (26.0, AXIS, 2.6, 1.2, 0.1)],
         sides=14, mat=DARK, power=0.7)
    for c, top in ((9.5, 1.9), (11.5, 2.3), (13.5, 1.9)):
        loft(bm, [(20.0, c, 0.55, 0.6, top), (25.6, c, 0.5, 0.5, top - 0.3), (26.0, c, 0, 0, top - 0.4)],
             sides=6, mat=BAND)
    # The bright spine down the middle (columns 9-13, rows 9-20).
    loft(bm, [(8.6, AXIS, 0, 0, 2.6), (9.6, AXIS, 2.3, 0.45, 2.75), (19.0, AXIS, 2.6, 0.45, 2.6),
              (20.6, AXIS, 1.6, 0.4, 2.3)], sides=8, mat=SPINE, power=0.6)

    # Dark canopy (rows 5-8, columns 10-13).
    dome(bm, AXIS + 0.2, 7.0, 2.0, 2.2, 0.9, z=2.5, rings=3, sides=12, mat=GLASS)

    # Swept fins beside the canopy (rows 5-9, out to columns 5 and 17).
    fin = [(9.0, 4.8), (4.6, 8.0), (4.5, 9.0), (9.5, 9.4)]
    for side in (1, -1):
        pts = fin if side == 1 else [(mirror(AXIS, c), r) for c, r in fin]
        slab(bm, pts, -0.2, 0.7, mat=FIN, bevel=0.15)

    # Side pods (rows 12-21, out to columns 3 and 19): (row, centre col, half width) for the left one.
    pod = [(11.8, 7.4, 0, 0, 0), (13.0, 7.0, 2.0, 1.5, -0.2), (14.0, 6.5, 2.5, 1.9, -0.3),
           (15.2, 6.0, 3.0, 2.1, -0.3), (20.0, 6.0, 3.0, 2.1, -0.3), (21.0, 6.3, 2.7, 1.8, -0.3),
           (21.6, 6.5, 1.8, 1.0, -0.3)]
    # Red engines behind them (columns 5-7, rows 18-25), tapering in toward the tail.
    engine = [(17.6, 6.5, 1.6, 2.7, -0.2), (24.0, 6.5, 1.6, 2.2, -0.3), (25.0, 7.0, 1.1, 1.6, -0.3),
              (26.0, 7.5, 0.6, 1.0, -0.3)]
    for side in (1, -1):
        m = (lambda c: c) if side == 1 else (lambda c: mirror(AXIS, c))
        loft(bm, [(r, m(c), w, h, z) for r, c, w, h, z in pod], sides=12, mat=POD, power=0.7)
        loft(bm, [(r, m(c), w, h, z) for r, c, w, h, z in engine], sides=10, mat=RED, power=0.6)
        # Grey bands between the red stripes (rows 19 and 21).
        for r in (19.0, 21.0):
            loft(bm, [(r, m(6.5), 1.75, 2.85, -0.2), (r + 1.0, m(6.5), 1.75, 2.75, -0.25)],
                 sides=10, mat=BAND, power=0.6)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


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
