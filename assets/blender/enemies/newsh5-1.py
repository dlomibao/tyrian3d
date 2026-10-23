"""Purple crystal arrowhead (newsh5.shp frame 1): a 3D version of its sprite.

Seen in episode 4 (level 4.12). A faceted purple arrowhead pointing up the screen, with barbed
shoulders and a ridge down its middle (the sprite's light left and dark right facets), cradled
from below by a dark red U-shaped collar whose lowest curve carries a glowing gold bead. One
frame, one model.

Run: blender --background --python assets/blender/enemies/newsh5-1.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b037 as L  # noqa: E402

NAME = "newsh5-1"
PX = 1 / 12
AX = L.EX(12.5)  # the sprite is mirror symmetric about pixel edge 12.5 (the middle of column 12)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(88, metallic=0.35, roughness=0.3),  # 0 purple crystal
        pal(243, metallic=0.3, roughness=0.45),  # 1 dark red collar
        pal(250, metallic=0.5, roughness=0.3, emission_strength=2.0),  # 2 gold bead
        pal(91, metallic=0.4, roughness=0.25),  # 3 pale ridge
        pal(245, metallic=0.3, roughness=0.5),  # 4 red collar floor
    ]
    CRYSTAL, COLLAR, GOLD, RIDGE, FLOOR = range(5)
    R = L.EY
    bm = bmesh.new()

    # The arrowhead: diamond sections down the screen (row edge, half width px, ridge z, keel z).
    secs = [(0.4, 0.0, 0.06, 0.0), (2.0, 1.4, 0.12, -0.04), (4.0, 3.4, 0.18, -0.08), (5.2, 4.8, 0.22, -0.1),
            (6.1, 6.8, 0.25, -0.11), (10.9, 7.6, 0.28, -0.12), (11.05, 4.6, 0.28, -0.12),
            (14.6, 4.5, 0.25, -0.11), (16.8, 2.4, 0.19, -0.08), (18.6, 0.6, 0.11, -0.04), (19.2, 0.0, 0.08, -0.02)]
    L.diamond_loft(bm, AX, [(R(r), w * PX, top, bot) for r, w, top, bot in secs], mat=CRYSTAL)
    # A pale crest along the ridge (the brightest pixels down the middle).
    L.loft_y(bm, AX, [(R(1.4), 0.0, 0.0, 0.1), (R(2.0), 0.35 * PX, 0.02, 0.12), (R(10.9), 0.35 * PX, 0.02, 0.28),
                      (R(14.6), 0.35 * PX, 0.02, 0.25), (R(17.5), 0.0, 0.0, 0.16)], sides=6, mat=RIDGE, smooth=False)

    # Left half of the collar: up the side (columns 6-7) and round the bottom to the axis (rows 19-22).
    start = len(bm.verts)
    path = [(6.6, 11.4, 0.0, 0.0), (6.8, 12.0, 0.8, 0.07), (6.9, 15.5, 1.1, 0.08), (7.8, 18.0, 1.4, 0.09),
            (9.6, 19.9, 1.6, 0.1), (12.5, 21.0, 1.7, 0.1)]
    L.sweep(bm, [(L.EX(c), R(r), -0.03, w * PX, h) for c, r, w, h in path], sides=10, mat=COLLAR, cap_end=False)
    # The gold bead along the bottom of the collar (columns 7-12, rows 17-20).
    bead = [(7.9, 17.4, 0.0, 0.0), (8.3, 18.0, 0.45, 0.03), (9.8, 19.6, 0.55, 0.035), (12.5, 20.6, 0.6, 0.035)]
    L.sweep(bm, [(L.EX(c), R(r), 0.055, w * PX, h) for c, r, w, h in bead], sides=8, mat=GOLD, cap_end=False)
    L.mirror_since(bm, start, AX)
    # The collar's floor, filling the U between the arms and under the blade.
    half = [(5.8, 11.8), (6.0, 16.5), (7.2, 19.0), (9.2, 21.0), (11.0, 22.0)]
    outline = [(L.EX(c), R(r)) for c, r in half] + [(L.EX(25 - c), R(r)) for c, r in reversed(half)]
    L.plate(bm, outline, -0.1, -0.02, mat=FLOOR)

    return L.to_object(NAME, bm, mats, coll)


if __name__ == "__main__":
    L.run(__file__, NAME, build)
