"""Grey rubble pile (newshj.shp frame 1): a 3D version of its sprite.

Seen in episode 2 (levels 2.2, 2.22 and 2.24). A heap of grey stone: a wide low mound with a
paler block rising out of its top and a light ridge down its left edge, a broken boulder with a
jagged spike standing behind it on a dark neck, and a smaller rock to the right. One frame.
The rocks are lumpy faceted domes (seeded jitter, so the build is repeatable) on the ground.

Run: blender --background --python assets/blender/enemies/newshj-1.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b109 as lib  # noqa: E402
from lib_b109 import PX, common  # noqa: E402

NAME = "newshj-1"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [pal(i, metallic=0.1, roughness=0.85) for i in (3, 5, 6, 7, 9, 10, 11, 8)]
    DARK, MOUND, LUMP, BLOCK, BOULDER, RIDGE, SPIKE, ROCK = range(8)
    bm = bmesh.new()

    def rock(c, r, rx, ry, h, seed, mat, **kw):
        lib.rock(bm, G.x(c), G.y(r), rx * PX, ry * PX, h, seed, mat=mat, **kw)

    # The wide mound (columns 2-19, rows 13-27) and the lumps on it.
    rock(10.6, 20.6, 8.4, 6.9, 0.24, 11, MOUND, sides=14, rings=4, jitter=0.08)
    rock(12.6, 16.2, 3.4, 3.0, 0.38, 12, BLOCK, sides=8, jitter=0.15)
    rock(4.8, 19.6, 2.5, 5.0, 0.3, 13, RIDGE, sides=9, jitter=0.12, tilt=(-0.03, 0.02))
    rock(8.0, 22.6, 3.2, 3.2, 0.3, 14, LUMP, sides=8)
    rock(15.6, 21.8, 3.6, 2.8, 0.28, 15, LUMP, sides=8)
    rock(12.6, 24.6, 1.8, 1.3, 0.26, 16, BOULDER, sides=7)
    rock(9.6, 18.4, 2.0, 2.0, 0.27, 17, DARK, sides=7)

    # A smaller rock to the right (columns 17-22, rows 12-18).
    rock(20.0, 15.6, 2.7, 3.5, 0.3, 21, ROCK, sides=9, tilt=(0.0, 0.03))

    # The broken boulder behind (columns 4-11, rows 5-10) on a dark neck, with its spike.
    rock(7.6, 11.6, 2.8, 2.2, 0.17, 31, DARK, sides=8)
    rock(8.0, 8.0, 4.1, 3.3, 0.32, 32, BOULDER, sides=10, jitter=0.12)
    rock(9.5, 5.2, 1.2, 1.9, 0.42, 33, SPIKE, sides=6, jitter=0.1, tilt=(0.0, 0.06))

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
