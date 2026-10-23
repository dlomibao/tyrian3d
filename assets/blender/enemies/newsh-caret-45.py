"""Grey gun emplacement (newsh^.shp frame 45): a 3D version of its sprite.

Seen in episode 4 (level 4.14), set in rows of up to seven along a dark brick wall (it is listed
with the crab of assembly-newsh-caret-45.py, but each copy is its own enemy). The sprite fills its
tile: a dark floor with bricks, and on it a grey machine: a ribbed housing at the back with a
glowing red eye at its front, a big rounded dome in front of it, a low plinth with two blocks
either side of a cannon that points down the screen. One frame.

Run: blender --background --python assets/blender/enemies/newsh-caret-45.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from lib_b072 import Grid, loft_y, plate, ellipsoid, dome, floor_bricks, to_object  # noqa: E402

NAME = "newsh-caret-45"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = Grid(24, 28)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(2, metallic=0.1, roughness=0.9),  # 0 floor
        pal(3, metallic=0.2, roughness=0.8),  # 1 dark bricks, plinth, recesses
        pal(5, metallic=0.5, roughness=0.5),  # 2 light bricks, housing, cannon
        pal(6, metallic=0.6, roughness=0.4),  # 3 housing ribs
        pal(7, metallic=0.6, roughness=0.4),  # 4 left panel, blocks
        pal(8, metallic=0.65, roughness=0.3),  # 5 dome
        pal(9, metallic=0.7, roughness=0.3),  # 6 block fronts
        pal(10, metallic=0.7, roughness=0.3),  # 7 bright rib
        pal(11, metallic=0.75, roughness=0.25),  # 8 top box edge
        pal(119, emission_strength=4.0),  # 9 red eye
        pal(125, emission_strength=5.0),  # 10 eye core
        pal(116, metallic=0.3, roughness=0.4),  # 11 eye's dark red rim
    ]
    FLOOR, DARK, MID, RIB, PANEL, DOME, FRONT, BRIGHT, EDGE, EYE, CORE, RIM = range(12)
    bm = bmesh.new()

    # Housing at the back (rows 2-10): a block with bevelled top corners, a raised lighter panel
    # on its lit left side with a bright rib (column 6) and ribs on its shaded right (14, 16).
    plate(bm, G, [(5, 2), (19, 2), (21, 4), (21, 11), (2, 11), (2, 5), (4, 3)], 0.03, 0.28, mat=MID)
    plate(bm, G, [(4, 3), (7, 3), (7, 10), (3, 10), (3, 5)], 0.28, 0.3, mat=PANEL)
    plate(bm, G, [(6, 2), (7, 2), (7, 10), (6, 10)], 0.28, 0.32, mat=BRIGHT)
    plate(bm, G, [(8, 3), (9, 3), (9, 9), (8, 9)], 0.28, 0.295, mat=RIB)
    for c in (14, 16):
        plate(bm, G, [(c, 2.5), (c + 1, 2.5), (c + 1, 9), (c, 9)], 0.28, 0.3, mat=RIB)
    # Small box on top in the middle (columns 10-12, rows 2-5) with a bright top edge.
    plate(bm, G, [(10, 2), (13, 2), (13, 6), (10, 6)], 0.28, 0.34, mat=PANEL)
    plate(bm, G, [(10, 2), (13, 2), (13, 3), (10, 3)], 0.34, 0.35, mat=EDGE)

    # The red eye at the front of the housing (columns 10-12, rows 7-11) in a dark socket.
    plate(bm, G, [(9, 6), (14, 6), (14, 11), (9, 11)], 0.28, 0.3, mat=DARK)
    ellipsoid(bm, G, 11.0, 9.2, 0.3, 1.6, 2.4, 0.06, mat=RIM)
    ellipsoid(bm, G, 11.0, 8.9, 0.31, 1.25, 1.8, 0.07, mat=EYE)
    ellipsoid(bm, G, 11.0, 8.2, 0.34, 0.7, 0.8, 0.05, mat=CORE)

    # Big rounded dome (columns 2-20, rows 10-18), lit from the upper left in the sprite.
    dome(bm, G, 11.0, 14.0, 0.03, 9.4, 4.4, 0.36, mat=DOME, segments=20, rings=10)

    # Low plinth in front (rows 17-23) with a block either side of the cannon (rows 18-20).
    plate(bm, G, [(2, 17), (21, 17), (21, 23), (3, 23), (2, 22)], 0.03, 0.09, mat=DARK)
    for c0, c1 in ((3, 10), (14, 20)):
        plate(bm, G, [(c0, 17.5), (c1, 17.5), (c1, 20), (c0, 20)], 0.09, 0.21, mat=PANEL)
        plate(bm, G, [(c0, 20), (c1, 20), (c1, 21), (c0, 21)], 0.09, 0.17, mat=FRONT)

    # The cannon out of the dome, pointing down the screen (columns 11-13, rows 15-23).
    loft_y(bm, G, 12.0, [(14.5, 1.7, 0.08, 0.17), (21.8, 1.6, 0.075, 0.17)], sides=10, mat=MID)
    loft_y(bm, G, 12.0, [(21.6, 1.9, 0.09, 0.17), (23.0, 1.9, 0.09, 0.17), (23.2, 1.0, 0.05, 0.17)],
           sides=10, mat=RIB)

    floor_bricks(bm, G, sprite["frames"][0]["pixels"], FLOOR, DARK, MID)
    return to_object(NAME, bm, mats, coll)


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
