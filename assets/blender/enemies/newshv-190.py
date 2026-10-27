"""Red slashed ring (newshv.shp frames 190, 209, 228): a 3D version of its sprite.

Seen in episode 2 (level 17). A small dark-red ring, open in the middle, crossed by a diagonal
bar from its lower left to a bright knob at its upper right. The three frames only pulse its
colours brighter (palette_material frames=), so one model covers them all: a rounded ring whose faces take the sprite's
shade under them (lit on the right), the bar across it and the glowing knob.

Run: blender --background --python assets/blender/enemies/newshv-190.py [-- --preview out.png] [--frame-previews frames.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b054 as lib  # noqa: E402

NAME = "newshv-190"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
S = 1  # size-1 sprite: a 12x14 tile


def P(c, r, z=0.0):
    return lib.P(c, r, z, size=S)


def build(sprite):
    coll = common.reset_collection(NAME)
    # Every colour brightens on frames 209 and 228 (the shades the sprite's pixels step to).
    f1, f2 = (f["index"] for f in sprite["frames"][1:3])

    def pal(i, b1, b2, **kw):
        return common.palette_material(sprite, i, f"{NAME}-pulse", frames={f1: b1, f2: b2}, **kw)

    mats = [
        pal(66, 67, 68, metallic=0.3, roughness=0.5, emission_strength=0.6),  # 0 dark red
        pal(67, 68, 70, metallic=0.3, roughness=0.45, emission_strength=0.8),  # 1 red ring
        pal(69, 70, 72, metallic=0.35, roughness=0.4, emission_strength=1.0),  # 2 lit red
        pal(71, 73, 75, metallic=0.3, roughness=0.3, emission_strength=3.0),  # 3 glowing knob
    ]
    DARK, RED, LIT, KNOB = range(4)
    pixels = sprite["frames"][0]["pixels"]
    shade = lib.ramp([(65, 66, DARK), (67, 68, RED), (69, 75, LIT)])
    bm = bmesh.new()

    # The ring: pixels in columns 2-9 and rows 3-10, one pixel thick (centre column 5.5, row 6.5).
    lib.torus(bm, P(5.5, 6.5), 3.45 / 12, 0.75 / 12, minor_z=0.07, major=24, sides=8, mat_index=RED)
    lib.paint(bm, bm.faces[:], pixels, shade, size=S, under_slot=DARK)

    # The bar across it, from the lower left (column 4, row 8) to the knob (column 7, row 5).
    lib.tube(bm, [P(3.4, 8.9, 0.0), P(4.5, 7.8, 0.02), P(6.0, 6.2, 0.03), P(7.0, 5.2, 0.03)],
             [0.6 / 12, 0.7 / 12, 0.7 / 12, 0.6 / 12], sides=8, mat_index=RED)
    lib.ellipsoid(bm, P(7.0, 5.1, 0.03), (0.9 / 12, 0.9 / 12, 0.07), segments=10, rings=6, mat_index=KNOB)
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)
    if "--frame-previews" in sys.argv:
        common.render_frame_previews([obj], sys.argv[sys.argv.index("--frame-previews") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
