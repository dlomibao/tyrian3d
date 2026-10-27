"""Small pyramid (newsh3.shp frames 3, 4, 5): a 3D version of its sprite.

Seen in episode 4 (level 4.2), in the desert beside the stepped pyramids. A 12x14 px sandstone
pyramid on a low plinth, drawn in the game's oblique view: its point leans to the top of the
screen, the lit west face is a long triangle down the left, the shaded east face a narrow strip
on the right and the south face the big dark triangle between them. The three frames only
brighten the same picture (each colour two shades lighter), so one model covers them all and
its colours brighten with them (palette_material frames=).

Run: blender --background --python assets/blender/enemies/newsh3-3.py [-- --preview out.png] [--frames dir]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b076 as lib  # noqa: E402

NAME = "newsh3-3"
ROOT = common.repo_root(__file__)
F = lib.Frame(12, 14)


def build(sprite):
    coll = common.reset_collection(NAME)
    # Every colour is two shades lighter on frame 4 and four on frame 5.
    pal = lambda i, **kw: common.palette_material(sprite, i, f"{NAME}-lit", metallic=0.0,  # noqa: E731
                                                  frames={4: i + 2, 5: i + 4}, **kw)
    mats = [
        pal(25, roughness=0.75),  # 0 lit west face
        pal(20, roughness=0.85),  # 1 south face
        pal(21, roughness=0.85),  # 2 east face
        pal(19, roughness=0.9),  # 3 north face and plinth
        pal(27, roughness=0.7),  # 4 highlight down the south-west edge and on the point
        pal(22, roughness=0.8),  # 5 the east face's upper edge
    ]
    WEST, SOUTH, EAST, DARK, LIT, EDGE = range(6)
    bm = bmesh.new()

    # Low plinth, its south face the dark bottom row.
    zb = 0.05
    lib.quad(bm, [F.p(0, 13, zb), F.p(12, 13, zb), F.p(12, 1.5, zb), F.p(0, 1.5, zb)], DARK)
    lib.quad(bm, [F.p(0, 14, 0), F.p(12, 14, 0), F.p(12, 13, zb), F.p(0, 13, zb)], DARK)
    lib.quad(bm, [F.p(0, 1.5, zb), F.p(0, 1.5, 0), F.p(0, 14, 0), F.p(0, 13, zb)], DARK)
    lib.quad(bm, [F.p(12, 13, zb), F.p(12, 14, 0), F.p(12, 1.5, 0), F.p(12, 1.5, zb)], DARK)
    lib.quad(bm, [F.p(12, 1.5, zb), F.p(12, 1.5, 0), F.p(0, 1.5, 0), F.p(0, 1.5, zb)], DARK)

    # The pyramid: a short ridge at the top of the sprite, its feet at the plinth's corners.
    zt = 0.5
    tw, te = F.p(4.8, 0.2, zt), F.p(6.6, 0.2, zt)
    nw, ne = F.p(0, 1.6, zb), F.p(12, 1.6, zb)
    sw_w, sw, se_s, se = F.p(0, 10.5, zb), F.p(0, 12.9, zb), F.p(10, 12.9, zb), F.p(12, 12.9, zb)
    lib.quad(bm, [tw, nw, sw_w], WEST)
    lib.quad(bm, [te, se_s, se], EAST)
    lib.quad(bm, [te, se, ne], EAST)
    lib.quad(bm, [tw, sw_w, sw], SOUTH)
    lib.quad(bm, [tw, sw, se_s], SOUTH)
    lib.quad(bm, [tw, se_s, te], SOUTH)
    lib.quad(bm, [te, ne, nw, tw], DARK)

    # Thin raised strips: the lit edge from the point down the south-west ridge, and the paler
    # band down the upper part of the east face (pixels 27 and 22).
    from mathutils import Vector
    TW, SW, NW = Vector(tw), Vector(sw_w), Vector(nw)
    lift = (NW - TW).cross(SW - TW).normalized() * 0.004
    edge = [TW + lift, TW + (NW - TW) * 0.3 + lift, TW + (SW - TW) * 0.8 + (NW - SW) * 0.12 + lift,
            TW + (SW - TW) * 0.8 + lift]
    lib.quad(bm, [tuple(p) for p in edge], LIT)
    TE, SE, NE = Vector(te), Vector(se), Vector(ne)
    lift = (SE - TE).cross(NE - TE).normalized() * 0.004
    band = [TE + lift, TE + (SE - TE) * 0.6 + lift, TE + (SE - TE) * 0.6 + (NE - SE) * 0.3 + lift,
            TE + (NE - TE) * 0.35 + lift]
    lib.quad(bm, [tuple(p) for p in band], EDGE)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.run(ROOT, NAME, lambda sprite: [(NAME, [build(sprite)], sprite["sprites"])], __file__)


if __name__ == "__main__":
    main()
