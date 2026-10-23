"""Small grey probe (newsh5.shp frame 133): a 3D version of its sprite.

Seen in episode 4 (level 4.18). A one-tile (12x14 px) grey capsule lying along the screen with
a glowing red band round its middle, a slim waist below it and, past a thin dark neck, a small
flared grey base. The model is a body of revolution (flattened a little) following the sprite's
outline, with the red band as a glowing ring. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-133.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b042 as lib  # noqa: E402

NAME = "newsh5-133"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
COL = 5.5  # the probe's axis: between columns 5 and 6


def build(sprite):
    g = lib.Grid(12, 14)
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.7, roughness=0.35),  # 0 dark grey nose
        pal(9, metallic=0.75, roughness=0.25),  # 1 grey body
        pal(11, metallic=0.75, roughness=0.25),  # 2 light grey waist
        pal(3, metallic=0.6, roughness=0.5),  # 3 dark neck
        pal(8, metallic=0.7, roughness=0.3),  # 4 grey base
        pal(118, metallic=0.2, roughness=0.4, emission_strength=4.0),  # 5 red band
    ]
    NOSE, BODY, WAIST, NECK, BASE, BAND = range(6)
    bm = bmesh.new()
    k = 0.85  # half height as a share of the half width

    def part(sections, mat, **kw):
        """A loft down the sprite on the axis: sections are (row, half width px)."""
        lib.sweep(bm, g, [(COL, r, 0.0, w, k * w / 12) for r, w in sections], sides=14, mat=mat, **kw)

    part([(1.3, 0.0), (1.7, 0.7), (2.4, 1.1), (3.0, 1.8), (3.4, 2.05)], NOSE, cap_end=False)
    part([(3.4, 2.05), (4.0, 2.15), (6.4, 2.15), (7.0, 1.6), (7.3, 1.2)], BODY, cap_start=False)
    part([(7.2, 1.25), (8.6, 1.05), (9.1, 0.6)], WAIST)
    part([(8.9, 0.6), (9.8, 0.6)], NECK)
    part([(9.6, 0.9), (10.4, 1.1), (11.0, 1.9), (12.4, 2.1), (12.6, 1.7), (12.7, 0.0)], BASE)
    part([(4.45, 2.3), (5.55, 2.3)], BAND)
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
