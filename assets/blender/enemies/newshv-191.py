"""Green crystal pod (newshv.shp frames 191, 193, 195): a 3D version of its sprite.

Seen in episode 2 (level section 15). A round, faceted green gem sitting on the ground: a pale,
almost white table in the middle, dark notches at the four compass points, bright facets on
the diagonals and a mid-green rim. The three frames only fade its greens darker (a pulse), so one
model covers them all: every pixel of frame 193 is two palette steps darker than on frame 191 and
on frame 195 four (down to the outline's 32), so every facet colour steps down the same way on
those frames (palette_material frames=).

Run: blender --background --python assets/blender/enemies/newshv-191.py [-- --preview out.png]
     [--frames frames.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b111 as lib  # noqa: E402

NAME = "newshv-191"
ROOT = common.repo_root(__file__)
P = 1 / 12
# How many palette steps the whole gem darkens on each later frame (32 is the darkest green).
FADE = {193: 2, 195: 4}


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(  # noqa: E731
        sprite, i, f"{NAME}-pulse", frames={f: max(i - d, 32) for f, d in FADE.items()}, **kw)
    mats = [
        pal(40, metallic=0.2, roughness=0.5),  # 0 rim green
        pal(42, metallic=0.3, roughness=0.35),  # 1 mid facets
        pal(38, metallic=0.3, roughness=0.4),  # 2 dark notches
        pal(45, metallic=0.4, roughness=0.25),  # 3 light facets
        pal(46, metallic=0.4, roughness=0.2, emission_strength=1.5),  # 4 bright diagonal facets
        pal(47, emission_strength=2.5),  # 5 glowing table
        pal(43, metallic=0.3, roughness=0.3),  # 6 upper mid facets
        pal(36, metallic=0.2, roughness=0.6),  # 7 dark base skirt
    ]
    RIM, MID, DARK, LIGHT, BRIGHT, TABLE, UPPER, SKIRT = range(8)
    bm = bmesh.new()

    # Sprite centre is (col 11.5, row 13.5) = the origin; the gem is 16 px across inside its outline.
    # Segment i of 16 faces direction i * 22.5 degrees (0 = east, 4 = north).
    def facet(ring, seg):
        cardinal = seg % 4 == 0
        diagonal = seg % 4 == 2
        if ring == 0:
            return SKIRT
        if ring == 1:
            return RIM
        if ring == 2:
            return LIGHT if diagonal else MID
        if ring == 3:
            return DARK if cardinal else (BRIGHT if diagonal else UPPER)
        if ring == 4:
            return LIGHT if not cardinal else UPPER
        return TABLE

    import math
    profile = [(8.3 * P, 0.0), (8.3 * P, 0.05), (8.2 * P, 0.12), (7.0 * P, 0.25), (4.4 * P, 0.39),
               (1.8 * P, 0.47), (0.0, 0.49)]
    lib.revolve(bm, profile, 16, facet, angle0=-math.pi / 16)

    return common.mesh_object(NAME, bm, mats, coll, smooth=False)


if __name__ == "__main__":
    lib.run(ROOT, NAME, build)
