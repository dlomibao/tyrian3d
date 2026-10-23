"""Green-eyed ground pod (newshj.shp frames 77, 79, 81): a 3D version of its sprite.

Seen in episode 2 (levels 2.2 and 2.24), set into the grass below a cliff. A squat grey puck
with a light bevelled rim, a dark socket on top and a green glass lens in it. The three frames
only brighten the lens (and nudge the sprite down a pixel), so one model covers them all; the
lens glows.

Run: blender --background --python assets/blender/enemies/newshj-77.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b109 as lib  # noqa: E402
from lib_b109 import PX, common  # noqa: E402

NAME = "newshj-77"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)


def ellipse(cx, cy, rx, ry, n=24):
    import math
    return [(G.x(cx) + rx * PX * math.cos(2 * math.pi * i / n), G.y(cy) + ry * PX * math.sin(2 * math.pi * i / n))
            for i in range(n)]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(6, metallic=0.6, roughness=0.45),  # 0 dark grey side
        pal(9, metallic=0.65, roughness=0.35),  # 1 grey top
        pal(11, metallic=0.7, roughness=0.3),  # 2 light rim
        pal(193, metallic=0.3, roughness=0.4),  # 3 dark green socket
        pal(201, metallic=0.2, roughness=0.15, emission_strength=3.0),  # 4 green lens
        pal(206, emission_strength=5.0),  # 5 lens highlight
        pal(3, metallic=0.5, roughness=0.6),  # 6 dark foot
    ]
    SIDE, TOP, RIM, SOCKET, LENS, HOT, FOOT = range(7)
    bm = bmesh.new()

    # The puck: a dark foot (columns 4-19, rows 17-26), its grey body with a light bevelled rim.
    lib.prism(bm, ellipse(11.9, 21.7, 8.6, 5.9), 0.0, 0.06, mat=FOOT)
    lib.prism(bm, ellipse(11.9, 21.4, 8.3, 5.6), 0.05, 0.19, mat=SIDE, bevel=0.04, side_mat=SIDE, top_mat=TOP)
    lib.prism(bm, ellipse(11.8, 21.0, 7.0, 4.3, n=20), 0.18, 0.205, mat=RIM, bevel=0.012, top_mat=TOP)
    # The socket and the green lens (columns 8-15, rows 18-22).
    lib.dome(bm, G.x(11.9), G.y(20.5), 5.0 * PX, 3.2 * PX, 0.035, z0=0.2, sides=20, rings=3, mat=SOCKET)
    lib.dome(bm, G.x(11.9), G.y(20.3), 4.3 * PX, 2.7 * PX, 0.08, z0=0.21, sides=20, rings=4, mat=LENS)
    lib.ellipsoid(bm, G.x(11.0), G.y(19.8), 0.275, 1.2 * PX, 0.8 * PX, 0.015, segments=10, rings=4, mat=HOT)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = lib.preview_arg()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], str(out), ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
