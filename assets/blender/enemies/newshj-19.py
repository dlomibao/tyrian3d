"""Fireball on the ground (newshj.shp frames 19, 38, 57, 76): a 3D version of its sprite.

Seen in episodes 1 and 2. A glowing oval of fire, dark red at its rim through orange and yellow
to a white-hot core, that turns on the spot: upright, leaning right, lying flat and leaning left.
Each frame is a different shape, so each gets its own model (newshj-19, -f2, -f3, -f4): nested
glowing domes, each smaller one rising higher through the one around it, so the colours step
inward like the sprite's rings.

Run: blender --background --python assets/blender/enemies/newshj-19.py [-- --preview out.png]
(the preview shows the first frame; the others go to <name>-f2.png etc. beside it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b096 as lib  # noqa: E402

NAME = "newshj-19"
ROOT = common.repo_root(__file__)
G = lib.Grid(12, 14)

# Per frame: (sprite frame, centre col, centre row, major radius px, minor radius px, angle deg)
# with the major axis along the angle (0 = across the screen, 90 = up the screen).
FRAMES = [
    (19, 5.5, 6.5, 7.1, 4.3, 90),
    (38, 5.6, 6.6, 6.9, 4.1, 61),
    (57, 5.5, 5.5, 6.2, 4.1, 0),
    (76, 5.4, 6.6, 6.9, 4.1, 119),
]
# Rings from the rim in: (palette index, scale of the radii, height, emission strength).
# Each sits on the one around it, its rim on that dome's surface, so they stack into a mound.
SHELLS = [(117, 1.0, 0.1, 2.0), (121, 0.86, 0.07, 3.0), (123, 0.7, 0.07, 3.5), (125, 0.5, 0.06, 4.5),
          (127, 0.27, 0.05, 6.0)]


def build(sprite, name, frame):
    coll = common.reset_collection(name)
    mats = [common.palette_material(sprite, i, NAME, metallic=0.0, roughness=0.6, emission_strength=e)
            for i, _, _, e in SHELLS]
    _, col, row, a, b, deg = frame
    bm = bmesh.new()
    z0, prev = 0.0, None
    for k, (_, s, h, _) in enumerate(SHELLS):
        if prev:
            ps, ph = prev
            z0 += ph * math.sqrt(1 - (s / ps) ** 2)
        lib.dome(bm, G, col, row, a * s, b * s, h, z0=z0, mat=k, segments=16, rings=4, angle=math.radians(deg))
        prev = (s, h)
    return lib.to_object(name, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    out = lib.preview_args()
    for k, frame in enumerate(FRAMES):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        obj = build(sprite, name, frame)
        sprites = [dict(s, frames=[frame[0]]) for s in sprite["sprites"]]
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", sprites)
        if out:
            img = ROOT / "reference" / "models" / NAME / f"frame-newshj-{frame[0]}.png"
            path = out if k == 0 else out.parent / f"{name}.png"
            common.render_preview([obj], str(path), img, size=1)


if __name__ == "__main__":
    main()
