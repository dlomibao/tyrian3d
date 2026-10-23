"""Lava egg cluster (newshe.shp frames 155-165): a 3D version of its sprite.

Seen in episode 1 (level 1.16), on the ground. Seven glossy red balls of different sizes heaped
together, each with a hot glint on its upper right. The six frames keep the same shape and only
shift the whole cluster from dark red to yellow (it heats up and glows), so one model covers them,
coloured with the first frame's palette indices.

Run: blender --background --python assets/blender/enemies/newshe-155.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b114 as lib  # noqa: E402

NAME = "newshe-155"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = lib.PX


def X(c):
    """Sprite column (pixel centre; fractions allowed) to Blender X."""
    return (c + 0.5 - 12) / 12


def Y(r):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (14 - (r + 0.5)) / 12


# Balls: (centre column, centre row, x radius px, y radius px, glint column, glint row).
BALLS = [
    (6.0, 7.8, 5.6, 5.0, 8.6, 6.6),  # big one, top left
    (18.2, 6.2, 3.9, 3.7, 19.0, 5.0),  # top right
    (14.0, 11.6, 4.2, 3.9, 14.6, 11.2),  # middle, partly under the others
    (20.8, 12.2, 2.6, 2.2, 21.0, 12.0),  # small one, right
    (5.0, 18.6, 4.4, 4.3, 6.4, 16.6),  # bottom left
    (16.2, 17.6, 3.2, 2.8, 17.0, 17.0),  # bottom, right of centre
    (13.2, 22.3, 3.6, 3.6, 14.0, 21.0),  # bottom tip
]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(117, metallic=0.2, roughness=0.25),  # 0 red shell
        pal(115, metallic=0.2, roughness=0.5),  # 1 dark base where the balls meet the ground
        pal(123, emission_strength=3.0),  # 2 hot glints
    ]
    SHELL, BASE, GLINT = range(3)
    bm = bmesh.new()

    # A low dark mound the balls sit in, filling the gaps between them in the middle.
    lib.dome(bm, X(11.5), Y(14.0), 7.0 * PX, 8.0 * PX, 0.08, mat=BASE, segments=14, rings=2, sink=0)

    for c, r, rx_px, ry_px, gc, gr in BALLS:
        rx, ry = (rx_px + 0.5) * PX, (ry_px + 0.5) * PX
        rz = min(rx, ry) * 0.72
        zc = lib.dome(bm, X(c), Y(r), rx, ry, rz, mat=SHELL, segments=16, rings=5, sink=30)
        # The glint sits on the ball's surface above the sprite's highlight pixel.
        u = max(-0.85, min(0.85, (gc - c) / rx_px))
        v = max(-0.85, min(0.85, (r - gr) / ry_px))
        w = math.sqrt(max(0.05, 1 - u * u - v * v))
        z = zc + rz * w
        size = max(0.9, rx_px * 0.28) * PX
        lib.ellipsoid(bm, X(c) + u * rx, Y(r) + v * ry, z - 0.01, size * 1.3, size, 0.03,
                      mat=GLINT, segments=10, rings=4)

    return lib.to_object(NAME, bm, mats, coll)


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
