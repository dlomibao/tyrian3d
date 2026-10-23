"""Snapping skull head (newsh0.shp frames 119, 121, 123, 129): a 3D version of its sprite.

Seen in episode 2 (level 2.12). A blue-steel demon skull seen from above, hanging off something
above it (its top row runs off the tile): a broad brow plate with a raised pale crest down the
middle, slanted glowing red eyes under swept brow ridges, cheekbones that curve down to the
corners of the mouth, two fangs hanging from the crest, and a dark open mouth with a lower jaw
(a V-shaped chin with three teeth and two side arms ending in fangs) that slides up and down.

The four frames only move the jaw: 123 closed (jaw 4 px up), 121 (2 px up), 119, 129 wide open
(2 px down). Each jaw position is its own model: newsh0-119 (frame 119), newsh0-119-f2 (121),
newsh0-119-f3 (123), newsh0-119-f4 (129).

Run: blender --background --python assets/blender/enemies/newsh0-119.py [-- --preview out.png]
(the preview is frame 119; the other jaw positions go to <out>-f2.png ... next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b025 as lib  # noqa: E402
from lib_b025 import common  # noqa: E402

NAME = "newsh0-119"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)
AX = G.x(11)  # the skull is mirror symmetric about the centre of column 11
# (model name, frame, jaw offset in px down from frame 119's position)
MODELS = [(NAME, 119, 0), (f"{NAME}-f2", 121, -2), (f"{NAME}-f3", 123, -4), (f"{NAME}-f4", 129, 2)]


def mirror_pts(pts):
    """Pixel-edge points of a left half, mirrored to the right (edge c -> 23 - c), reversed."""
    return [(23 - c, r) for c, r in reversed(pts)]


def build(sprite, name, off):
    coll = common.reset_collection(name)
    m = lib.Mats(name, sprite["colors"])
    SKULL = m(54, metallic=0.45, roughness=0.4)
    CREST = m(59, metallic=0.5, roughness=0.3)
    BROW = m(56, metallic=0.45, roughness=0.4)
    HIGH = m(61, metallic=0.5, roughness=0.25)
    FANG = m(58, metallic=0.5, roughness=0.3)
    TOOTH = m(57, metallic=0.5, roughness=0.3)
    DARK = m(50, metallic=0.4, roughness=0.5)
    CAVITY = m(48, metallic=0.1, roughness=0.85)
    SOCKET = m(113, metallic=0.2, roughness=0.6)
    EYE = m(117, emission_strength=4.0)
    CORE = m(119, emission_strength=6.0)
    bm = bmesh.new()

    # Brow plate across the top (rows 0-8), notched up under each eye where the mouth reaches.
    left = [(0, 0), (0, 5), (1, 5), (1, 8.5), (4.5, 8.5), (5, 7), (6, 6), (8.5, 6), (9, 7)]
    lib.pillow(bm, G, left + mirror_pts(left), -0.1, 0.12, round_px=1.6, round_h=0.55, mat=SKULL)

    v_half = lib.mark(bm)
    # ---- left half, mirrored below ----
    # Cheekbone from under the eye down to the corner of the mouth (rows 7-13).
    cheek = [(1, 7), (5, 7.2), (5.2, 8), (8.8, 8.2), (8, 9.2), (7.2, 10), (7, 12), (8, 13), (8, 14),
             (5, 14), (4, 13), (3, 12), (3, 9.6), (1.6, 9), (1, 8.5)]
    lib.pillow(bm, G, cheek, -0.08, 0.1, round_px=0.9, round_h=0.6, mat=SKULL)
    lib.sweep(bm, G, [(2.0, 8.2, 0.095, 0.0, 0.0), (2.8, 8.4, 0.1, 0.9, 0.03), (5.5, 8.9, 0.1, 0.9, 0.03),
                      (6.6, 9.4, 0.095, 0.0, 0.0)], sides=8, mat=FANG)  # its pale top edge
    # Dark lip at the corner of the mouth (row 13) and the stub below it (column 6).
    lib.sweep(bm, G, [(4.6, 13.5, 0.06, 0.0, 0.0), (5.0, 13.5, 0.06, 0.6, 0.05), (7.6, 13.5, 0.06, 0.6, 0.05),
                      (8.0, 13.5, 0.06, 0.0, 0.0)], sides=8, mat=DARK)
    lib.sweep(bm, G, [(6, 13.2, 0.0, 0.7, 0.05), (6, 15.6, -0.01, 0.6, 0.04), (6, 16.0, -0.01, 0.0, 0.0)],
              sides=8, mat=DARK)
    # Brow ridge sweeping out over the eye (rows 1-2).
    lib.sweep(bm, G, [(8.8, 2.3, 0.12, 0.0, 0.0), (8.0, 2.2, 0.13, 1.0, 0.04), (5.5, 1.5, 0.13, 1.0, 0.04),
                      (3.0, 1.6, 0.12, 0.8, 0.03), (2.2, 1.8, 0.11, 0.0, 0.0)], sides=8, mat=FANG)
    # Slanted eye (rows 3-6, columns 3-5): a dark red socket with the glowing eye in it.
    ang = -math.radians(50)
    lib.ellipsoid(bm, G.x(4.1), G.y(4.6), 0.1, 2.4 / 12, 1.3 / 12, 0.045, mat=SOCKET, angle=ang,
                  segments=10, rings=5)
    lib.ellipsoid(bm, G.x(4.2), G.y(4.7), 0.115, 1.9 / 12, 0.9 / 12, 0.05, mat=EYE, angle=ang,
                  segments=12, rings=6)
    lib.ellipsoid(bm, G.x(4.6), G.y(5.1), 0.15, 0.8 / 12, 0.55 / 12, 0.025, mat=CORE, angle=ang,
                  segments=8, rings=4)
    # Fang hanging from the crest (column 9, rows 8-12).
    lib.sweep(bm, G, [(9, 7.6, 0.05, 0.9, 0.05), (9, 10.0, 0.03, 0.7, 0.04), (9, 12.4, 0.0, 0.0, 0.0)],
              sides=8, mat=FANG)

    # Lower jaw (moves with the frame): side arm (column 6) with a fang at its top, and teeth.
    v_jaw = lib.mark(bm)
    lib.sweep(bm, G, [(6, 10.0, -0.06, 0.7, 0.035), (6, 17.2, -0.05, 0.75, 0.04), (6.8, 18.3, -0.05, 0.7, 0.035),
                      (7.4, 18.6, -0.05, 0.0, 0.0)], sides=8, mat=DARK)
    lib.sweep(bm, G, [(7, 16.4, -0.02, 0.0, 0.0), (7, 16.0, -0.02, 0.7, 0.045), (7, 13.7, 0.0, 0.0, 0.0)],
              sides=8, mat=TOOTH)
    lib.sweep(bm, G, [(9, 19.2, -0.01, 0.8, 0.05), (9, 17.5, 0.01, 0.6, 0.04), (9, 15.6, 0.02, 0.0, 0.0)],
              sides=8, mat=TOOTH)
    lib.move(bm, v_jaw, dy=-off / 12)

    lib.mirror_x(bm, AX, v_half)

    # ---- centre parts ----
    # Pale crest down the middle (columns 9-13, rows 0-9) with a highlight along its top.
    lib.loft_y(bm, G, 11, [(-0.5, 2.6, 0.1, 0.11), (2.0, 3.0, 0.12, 0.11), (5.0, 3.0, 0.12, 0.11),
                           (7.0, 2.7, 0.1, 0.09), (8.6, 2.3, 0.07, 0.07), (9.3, 0.0, 0.0, 0.06)],
               sides=12, mat=CREST)
    lib.loft_y(bm, G, 11, [(-0.5, 0.9, 0.03, 0.215), (1.0, 1.0, 0.035, 0.225), (5.5, 0.9, 0.03, 0.22),
                           (7.0, 0.0, 0.0, 0.19)], sides=8, mat=HIGH)
    # Forehead rising toward the crest (the paler blue at columns 5-17, rows 0-6).
    lib.loft_y(bm, G, 11, [(-0.5, 6.5, 0.07, 0.1), (3.0, 6.8, 0.07, 0.1), (5.5, 5.5, 0.06, 0.1),
                           (6.8, 3.5, 0.04, 0.1), (7.2, 0.0, 0.0, 0.1)], sides=12, mat=BROW)
    # The dark inside of the mouth, under everything, down to behind the chin.
    b = 19.5 + off
    lib.plate(bm, G, [(5.5, 6), (17.5, 6), (17.5, 13), (17, b - 1), (16, b), (7, b), (6, b - 1), (5.5, 13)],
              -0.14, -0.1, mat=CAVITY)

    # Chin (rows 18-23) with a pale ridge and the middle tooth.
    v_jaw = lib.mark(bm)
    lib.loft_y(bm, G, 11, [(17.8, 4.4, 0.04, -0.03), (18.5, 5.2, 0.07, -0.02), (19.6, 4.9, 0.085, -0.01),
                           (21.0, 3.7, 0.08, -0.01), (22.3, 2.6, 0.06, -0.02), (22.9, 1.3, 0.035, -0.03),
                           (23.1, 0.0, 0.0, -0.03)], sides=12, mat=SKULL)
    lib.loft_y(bm, G, 11, [(18.0, 0.0, 0.0, 0.05), (18.6, 1.0, 0.03, 0.065), (20.5, 1.1, 0.03, 0.06),
                           (21.6, 0.0, 0.0, 0.05)], sides=8, mat=FANG)
    lib.sweep(bm, G, [(11, 19.0, 0.0, 0.8, 0.05), (11, 18.0, 0.02, 0.6, 0.04), (11, 16.6, 0.03, 0.0, 0.0)],
              sides=8, mat=TOOTH)
    lib.move(bm, v_jaw, dy=-off / 12)

    return lib.to_object(name, bm, m.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objs = {}
    for name, frame, off in MODELS:
        obj = build(sprite, name, off)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", lib.subset(sprite["sprites"], [frame]))
        objs[name] = (obj, frame)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        for name, (obj, frame) in objs.items():
            path = out if name == NAME else out.with_name(f"{out.stem}{name[len(NAME):]}.png")
            ref = ROOT / "reference" / "models" / NAME / f"frame-newsh0-{frame}.png"
            common.render_preview([obj], str(path), ref, size=2)


if __name__ == "__main__":
    main()
