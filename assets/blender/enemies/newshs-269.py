"""Red dome turret (newshs.shp frame 269): a 3D version of its sprite.

A ground turret (levels 1.21, 1.23, 1.25, 2.6, 3.15): an egg-shaped grey housing with a bright
rim, a big glossy red glass dome in its upper part with a grey ball (the gun, with a seam down
its middle) pushing out of the dome's front, and a dark ribbed hatch at the bottom of the egg.

Run: blender --background --python assets/blender/enemies/newshs-269.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b080 as L  # noqa: E402
import common  # noqa: E402

NAME = "newshs-269"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
g = L.Grid(24, 28)
U = L.U


def build(sprite):
    coll = common.reset_collection(NAME)
    m = L.Mats(NAME, sprite["colors"])
    HOUSING = m(5, metallic=0.55, roughness=0.5)
    RIM = m(10, metallic=0.75, roughness=0.3)
    DARK = m(3, metallic=0.4, roughness=0.6)
    SLOT = m(2, metallic=0.2, roughness=0.8)
    GLASS = m(116, metallic=0.2, roughness=0.12, emission_strength=2.0)
    GLOW = m(121, metallic=0.1, roughness=0.15, emission_strength=4.0)
    BALL = m(7, metallic=0.7, roughness=0.3)
    SHINE = m(12, metallic=0.8, roughness=0.2)
    bm = bmesh.new()

    # The egg-shaped housing: a low block with a chamfered, bright rim.
    # Its outline: a rounded oval through the sprite's edge (columns 1-23, rows 0-26).
    outline = [(v.x, v.y) for v in L.ellipse_ring((g.x(12.0), g.y(13.0), 0), (11.6 * U, 0, 0),
                                                   (0, 13.6 * U, 0), 32, phase=0.0, power=0.8)]
    L.bevel_prism(bm, outline, 0.0, 0.12, 0.04, mat=RIM)
    L.prism(bm, L.inset_polygon(outline, 0.1), 0.1, 0.17, mat=HOUSING)

    # The dark hatch at the bottom of the egg (rows 19-26, columns 7-16) with its ribs.
    hatch = [(g.x(7.5), g.y(26.3)), (g.x(16.5), g.y(26.3)), (g.x(17.5), g.y(19)), (g.x(6.5), g.y(19))]
    L.bevel_prism(bm, hatch, 0.1, 0.2, 0.025, mat=DARK)
    for c in (8, 10.5, 13.5, 15):
        L.box(bm, g.x(c - 0.3), g.y(25.6), g.x(c + 0.3), g.y(20.2), 0.19, 0.215, mat=SLOT)
    L.box(bm, g.x(10.8), g.y(25.0), g.x(13.2), g.y(21.0), 0.19, 0.24, mat=HOUSING)

    # Notch at the top of the rim (rows 0-1, columns 10-13).
    L.box(bm, g.x(10.5), g.y(1.6), g.x(13.5), g.y(-0.3), 0.1, 0.19, mat=DARK)

    # Dark well round the dome, then the red glass dome (columns 4-20, rows 2-19).
    cx, cy = g.x(12.0), g.y(10.6)
    L.prism(bm, L.ellipse_outline(cx, cy, 9.4 * U, 9.4 * U, 24), 0.15, 0.19, mat=SLOT)
    L.dome(bm, (cx, cy, 0.17), (8.6 * U, 8.7 * U, 0.34), mat=GLASS, segments=24, rings=6)
    # Hot spot glowing inside the glass, upper left (rows 3-8, columns 8-12).
    L.ellipsoid(bm, (g.x(9.6), g.y(5.6), 0.395), (3.2 * U, 3.0 * U, 0.07), mat=GLOW, segments=12, rings=6)

    # The grey ball pushing out of the dome's front (columns 8-16, rows 9-15) with its seam.
    bx, by = g.x(12.0), g.y(12.3)
    L.ellipsoid(bm, (bx, by, 0.36), (4.6 * U, 3.8 * U, 0.17), mat=BALL, segments=18, rings=9)
    L.box(bm, bx - 0.4 * U, by - 3.2 * U, bx + 0.4 * U, by + 3.2 * U, 0.46, 0.535, mat=SLOT)
    for dx in (-1.1, 1.1):
        L.ellipsoid(bm, (bx + dx * U, g.y(11.2), 0.51), (0.7 * U, 0.9 * U, 0.025), mat=SHINE, segments=8, rings=4)

    return L.to_object(NAME, bm, m.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    L.preview([obj], ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
