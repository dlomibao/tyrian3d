"""Eye hatch (newsh5.shp frames 160, 162, 164): a 3D version of its sprites.

Seen in episode 4 (level 4.22) set into the ground. It fills its whole tile: a purple stone
block, octagonal with arms running out to the tile's edges (seams down their middles), on a dark
teal floor. In its middle is a round pit, and in the pit a glowing red eye that two shutters slide
over: a narrow one down from the top and a wider one up from the bottom. The frames close the
shutters (open, half shut, shut), so each frame gets its own model: newsh5-160, newsh5-160-f2,
newsh5-160-f3.

Run: blender --background --python assets/blender/enemies/newsh5-160.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b068 as L  # noqa: E402

common = L.common
NAME = "newsh5-160"
ROOT = common.repo_root(__file__)

# The block's outline in pixel edges (column, row): an octagon whose four arms reach the tile edges.
BLOCK = [(7, 0), (17, 0), (17, 1.5), (22.5, 7), (24, 7), (24, 21), (22.5, 21), (17, 26.5), (17, 28),
         (7, 28), (7, 26.5), (1.5, 21), (0, 21), (0, 7), (1.5, 7), (7, 1.5)]
PIT = (12.0, 13.5, 9.0, 9.5)  # pit centre (pixel edges) and radii (px)
# Per frame: the row of the top shutter's lit lip and of the bottom shutter's lit lip.
SHUTTERS = {160: (7, 18), 162: (9, 16), 164: (11, 14)}

TOP_Z = 0.2  # top of the block
FLOOR_Z = 0.07  # floor of the pit


def build(sprite, frame, tag):
    coll = common.reset_collection(tag)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(102, metallic=0.1, roughness=0.8),  # 0 teal floor
        pal(86, metallic=0.15, roughness=0.6),  # 1 purple stone
        pal(88, metallic=0.15, roughness=0.55),  # 2 lit bevel
        pal(83, metallic=0.1, roughness=0.7),  # 3 dark pit wall
        pal(81, metallic=0.1, roughness=0.8),  # 4 pit floor
        pal(82, metallic=0.1, roughness=0.7),  # 5 seams, bottom shutter
        pal(84, metallic=0.2, roughness=0.5),  # 6 top shutter
        pal(87, metallic=0.2, roughness=0.5),  # 7 shutter lips
        pal(117, roughness=0.3, emission_strength=2.5),  # 8 red eye
        pal(121, roughness=0.3, emission_strength=3.5),  # 9 orange band
        pal(126, roughness=0.3, emission_strength=5.0),  # 10 white-hot band
        pal(114, roughness=0.4, emission_strength=1.5),  # 11 eye's dark rim
        pal(119, roughness=0.3, emission_strength=3.0),  # 12 red-orange band (half shut)
        pal(113, roughness=0.4, emission_strength=1.0),  # 13 dull eye (shut)
    ]
    FLOOR, STONE, BEVEL, WALL, PITF, SEAM, TOPSH, LIP, EYE, ORANGE, HOT, RIM, WARM, DULL = range(14)
    EYES = {160: (EYE, (HOT, ORANGE)), 162: (EYE, (ORANGE, WARM)), 164: (DULL, ())}
    top_lip, bottom_lip = SHUTTERS[frame["index"]]
    ex, ey = L.EX, L.EY
    bm = bmesh.new()

    # Floor: the whole tile.
    L.box(bm, ex(0), ey(28), ex(24), ey(0), 0.0, 0.03, mat=FLOOR)

    # The block with a bevelled top edge and the pit sunk into it.
    cx, cy, rx, ry = ex(PIT[0]), ey(PIT[1]), PIT[2] * L.PX, PIT[3] * L.PX
    outer = L.resample([(ex(c), ey(r)) for c, r in BLOCK], 1.6 * L.PX)
    loops = [
        L.at_z(outer, 0.03),
        L.at_z(outer, TOP_Z - 0.03),
        L.at_z(L.pull(outer, cx, cy, 0.7 * L.PX), TOP_Z),
        L.at_z(L.toward_ellipse(outer, cx, cy, rx, ry), TOP_Z),
        L.at_z(L.toward_ellipse(outer, cx, cy, rx, ry, 0.9), TOP_Z - 0.04),
        L.at_z(L.toward_ellipse(outer, cx, cy, rx, ry, 0.62), FLOOR_Z),
    ]
    L.terraces(bm, loops, [STONE, BEVEL, STONE, WALL, WALL], cap_bottom=STONE, cap_top=PITF)

    # Seams down the middle of each arm.
    s = 0.004
    L.box(bm, ex(11.2), ey(4.6), ex(12.0), ey(0), TOP_Z - s, TOP_Z + s, mat=SEAM)
    L.box(bm, ex(11.2), ey(28), ex(12.0), ey(22.8), TOP_Z - s, TOP_Z + s, mat=SEAM)
    L.box(bm, ex(0), ey(14), ex(3.4), ey(13.2), TOP_Z - s, TOP_Z + s, mat=SEAM)
    L.box(bm, ex(20.7), ey(14), ex(24), ey(13.2), TOP_Z - s, TOP_Z + s, mat=SEAM)

    # The eye: a red lens with bands of light across it, in a dark rim. It dims as the shutters
    # close (frame 162 has no white-hot band, frame 164 only a dull red glow).
    ecy = ey(13.5)
    lens, bands = EYES[frame["index"]]
    L.ellipsoid(bm, (0.0, ecy, FLOOR_Z), (5.4 * L.PX, 3.9 * L.PX, 0.045), mat=RIM, segments=16, rings=6)
    L.ellipsoid(bm, (0.0, ecy + 0.1 * L.PX, FLOOR_Z + 0.005), (4.8 * L.PX, 3.3 * L.PX, 0.06), mat=lens,
                segments=16, rings=8)
    for row, mat in zip((12.4, 14.6), bands):
        L.ellipsoid(bm, (0.0, ey(row), FLOOR_Z + 0.05), (3.4 * L.PX, 0.9 * L.PX, 0.025), mat=mat,
                    segments=12, rings=4)

    # Top shutter: a narrow bar sliding down from the pit's top edge, its lit lip at `top_lip`.
    L.box(bm, ex(10), ey(top_lip), ex(14), ey(3.5), FLOOR_Z, 0.18, mat=TOPSH)
    L.box(bm, ex(10), ey(top_lip + 1), ex(14), ey(top_lip), FLOOR_Z, 0.185, mat=LIP)
    L.box(bm, ex(11.2), ey(top_lip), ex(12.0), ey(3.5), 0.18, 0.184, mat=SEAM)
    # Bottom shutter: a wider plate sliding up, its lit lip at `bottom_lip`.
    L.box(bm, ex(9), ey(23.5), ex(16), ey(bottom_lip + 1), FLOOR_Z, 0.165, mat=SEAM)
    L.box(bm, ex(9), ey(bottom_lip + 1), ex(16), ey(bottom_lip), FLOOR_Z, 0.175, mat=LIP)

    return L.to_object(tag, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    models = []
    for i, frame in enumerate(sprite["frames"]):
        tag = NAME if i == 0 else f"{NAME}-f{i + 1}"
        models.append((build(sprite, frame, tag), [frame["index"]]))
    L.export_frames(ROOT, NAME, sprite, models)


if __name__ == "__main__":
    main()
