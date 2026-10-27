"""Black glass orb on brown claws (newshs.shp frames 39, 41 over 77, 79): a 3D version of its
sprites.

Seen in episodes 1-3 (levels 1.21, 1.6, 2.8, 3.15). Four 2x2 pieces make one 48 x 56 px
machine on the stone floor: a big glossy black orb with a bright glint, two brown legs at its
flanks, two curved horns sweeping down from under it to a brown yoke, and in front of the yoke
a small black hatch. In frames 81/85 (newshs-77) and 83/87 (newshs-79) a pink ball rises out
of the hatch, so those frames get their own models (newshs-77-f2, newshs-79-f2) with the ball
in place of the hatch: dim on 81/83, bright and a pixel lower on 85/87 (frame_part).

Built whole and cut into the pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshs-39.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "assembly-newshs-39"
PIECES = [["newshs-39", "newshs-41"], ["newshs-77", "newshs-79"]]
ROOT = common.repo_root(__file__)


def machine(sprite, g, m, name, ball):
    coll = common.reset_collection(name)
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"])
    BROWN, HORN = m.metal(21), m.metal(167)

    # Brown legs at the flanks (columns 1-6 and 37-42, rows 22-37).
    L.loft_y(bm, g.x(3.6), [(g.ey(21.5), 0.0, 0.0, 0.1), (g.ey(23.0), 2.4 * L.U, 0.14, 0.1),
                            (g.ey(31.0), 2.8 * L.U, 0.16, 0.1), (g.ey(35.0), 1.8 * L.U, 0.1, 0.08),
                            (g.ey(36.0), 0.0, 0.0, 0.06)], sides=10, mat=BROWN)
    L.loft_y(bm, g.x(40.0), [(g.ey(21.5), 0.0, 0.0, 0.1), (g.ey(23.0), 2.4 * L.U, 0.14, 0.1),
                             (g.ey(32.0), 2.8 * L.U, 0.16, 0.1), (g.ey(36.5), 1.8 * L.U, 0.1, 0.08),
                             (g.ey(37.5), 0.0, 0.0, 0.06)], sides=10, mat=BROWN)
    # The horns, curving down and out from under the orb.
    L.tube(bm, [(g.x(12.0), g.y(29.0), 0.2), (g.x(9.0), g.y(32.5), 0.2), (g.x(7.0), g.y(37.0), 0.17),
                (g.x(6.6), g.y(43.0), 0.1)], [2.6 * L.U, 2.6 * L.U, 2.0 * L.U, 0.8 * L.U], sides=8, mat=HORN)
    L.tube(bm, [(g.x(30.5), g.y(29.0), 0.2), (g.x(33.5), g.y(32.5), 0.2), (g.x(35.5), g.y(37.0), 0.17),
                (g.x(36.0), g.y(42.5), 0.1)], [2.6 * L.U, 2.6 * L.U, 2.0 * L.U, 0.8 * L.U], sides=8, mat=HORN)
    # The yoke across the front (columns 10-32, rows 35-39) with its grille.
    L.pillow(bm, L.rect(g, 9.5, 34.6, 33, 39.6), 0.0, 0.2, 0.6 * L.U, mat=m.metal(18), top_mat=m.metal(20))
    for c in (19.6, 21.0, 22.4, 23.8):
        L.box(bm, g.ex(c), g.ey(38.4), g.ex(c + 0.6), g.ey(36.0), 0.18, 0.21, mat=m.metal(22))

    # The black glass orb (columns 5-38, rows 4-34) and its glint.
    cx, cy, rx, ry, h = g.x(21.5), g.y(18.8), 16.6 * L.U, 15.0 * L.U, 0.56
    L.dome(bm, cx, cy, rx, ry, h, z0=0.0, sides=28, rings=7, mat=m(2, metallic=0.6, roughness=0.15))
    zf = L.dome_z(cx, cy, rx, ry, h, z0=0.0, lift=0.0)
    gx, gy = g.x(13.4), g.y(13.4)
    L.ellipsoid(bm, gx, gy, zf(gx, gy) - 0.015, 3.6 * L.U, 3.2 * L.U, 0.05, sides=12, rings=6,
                mat=m(12, metallic=0.2, roughness=0.2))
    L.ellipsoid(bm, gx, gy, zf(gx, gy) + 0.0, 2.2 * L.U, 2.0 * L.U, 0.04, sides=12, rings=6,
                mat=m(15, metallic=0.1, roughness=0.2))
    # Dim reflections in the glass (the grey flecks at the top right and middle).
    for c, r, s in ((27.5, 9.5, 1.6), (20.5, 21.0, 2.0), (31.0, 17.0, 1.2), (24.0, 13.0, 1.0)):
        x, y = g.x(c), g.y(r)
        L.ellipsoid(bm, x, y, zf(x, y) - 0.012, s * L.U, s * 0.8 * L.U, 0.025, sides=8, rings=4,
                    mat=m(5, metallic=0.5, roughness=0.3))

    if not ball:  # the risen ball is built apart (balls)
        # The black hatch (columns 18-26, rows 40-47) with a white glint.
        L.dome(bm, g.x(21.8), g.y(43.6), 4.6 * L.U, 4.0 * L.U, 0.12, z0=0.0, sides=16, rings=3,
               mat=m(2, metallic=0.6, roughness=0.15))
        L.ellipsoid(bm, g.x(20.3), g.y(43.0), 0.125, 1.3 * L.U, 1.2 * L.U, 0.02, sides=8, rings=4,
                    mat=m(14, metallic=0.2, roughness=0.2))
    return L.finish(name, bm, m, coll)


def balls(g, m, coll):
    """The pink ball risen out of the hatch (columns 16-29, rows 38-52): dim on frames 81/83,
    bright and a pixel lower on 85/87."""
    out = []
    for look, frames, c, r, index in (("dim", [81, 83], 22.6, 45.0, 74), ("bright", [85, 87], 23.0, 46.0, 78)):
        bm = bmesh.new()
        L.ellipsoid(bm, g.x(c), g.y(r), 0.2, 6.6 * L.U, 6.6 * L.U, 0.2, sides=18, rings=9,
                    mat=m(index, metallic=0.2, roughness=0.45))
        out.append(L.part(f"ball-{look}", bm, m, coll, frames))
    return out


def build(sprite, g):
    m = L.Mats("nshs39", sprite["colors"])
    whole = machine(sprite, g, m, NAME, ball=False)
    risen = machine(sprite, g, m, NAME + "-ball", ball=True)
    layout = [e for e in L.layout_of(PIECES, 2, 2) if e[0] in ("newshs-77", "newshs-79")]
    cut = common.split_assembly(risen, layout)
    for ball in balls(g, m, risen.users_collection[0]):
        for n, piece in L.cut_parts(ball, layout).items():
            cut.setdefault(n + "-parts", []).append(piece)
    extra = [("newshs-77-f2", [cut["newshs-77"], *cut["newshs-77-parts"]], L.sprites_with(ROOT, "newshs-77", [81, 85])),
             ("newshs-79-f2", [cut["newshs-79"], *cut["newshs-79-parts"]], L.sprites_with(ROOT, "newshs-79", [83, 87]))]
    risen.hide_render = True
    return whole, extra


if __name__ == "__main__":
    L.run_assembly(NAME, PIECES, build, __file__, 2, 2, frames_of={"newshs-77": [77], "newshs-79": [79]})
