"""Fire star (newsh5.shp frames 278, 280, 282): a 3D version of its sprites.

Seen in episode 4 (levels 4.22 and 4.45) on the ground. A glowing red-orange crystal star: four
long points (up, down, left, right) and four short blocky lobes between them, its ridges running
hot yellow into a white-hot centre. The frames shrink it (the points go from 11 to 8 px long), so
each frame gets its own model sized to it: newsh5-278, newsh5-278-f2, newsh5-278-f3.

Run: blender --background --python assets/blender/enemies/newsh5-278.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b068 as L  # noqa: E402

common = L.common
NAME = "newsh5-278"
ROOT = common.repo_root(__file__)

# Per frame, in sprite px from the centre of pixel (12, 12): the four points' reach and the half
# size of the square body the points stand out of (its four quarters are rounded lumps).
SIZES = {278: (11.5, 7.0), 280: (9.5, 6.5), 282: (8.5, 5.5)}


def build(sprite, frame, tag):
    coll = common.reset_collection(tag)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(115, metallic=0.2, roughness=0.5),  # 0 dark red base between the lumps
        pal(119, roughness=0.4, emission_strength=2.0),  # 1 red lumps
        pal(121, roughness=0.4, emission_strength=2.5),  # 2 orange points
        pal(124, roughness=0.3, emission_strength=4.0),  # 3 hot ridges and spots
        pal(126, roughness=0.3, emission_strength=5.0),  # 4 white-hot core
    ]
    BASE, LUMP, POINT, HOT, CORE = range(5)
    tip, q = SIZES[frame["index"]]
    s = tip / 11.5  # heights scale with the star
    cx, cy = L.X(12), L.Y(12)
    P = L.PX
    bm = bmesh.new()

    # A low dark plate under everything, the square body's footprint.
    L.prism(bm, [(cx - (q - 0.6) * P, cy - (q - 0.6) * P), (cx + (q - 0.6) * P, cy - (q - 0.6) * P),
                 (cx + (q - 0.6) * P, cy + (q - 0.6) * P), (cx - (q - 0.6) * P, cy + (q - 0.6) * P)],
            0.0, 0.06 * s, mat=BASE)
    # Four rounded lumps, one per quarter, each with a hot spot on its outer shoulder.
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = (cx + sx * q * 0.52 * P, cy + sy * q * 0.52 * P, 0.0)
            L.blob(bm, c, (q * 0.54 * P, q * 0.54 * P, 0.2 * s), mat=LUMP, segments=12, rings=6,
                   power=0.35, floor=0.0)
            L.ellipsoid(bm, (cx + sx * q * 0.72 * P, cy + sy * q * 0.72 * P, 0.17 * s),
                        (1.2 * P * s, 1.2 * P * s, 0.04 * s), mat=HOT, segments=8, rings=4)
    # Four points, diamond in section (a ridge on top), from the centre out past the body, with
    # a hot streak along each ridge.
    for k in range(4):
        a = k * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        path = [(0.0, 2.2, 0.15), (q * 0.6, 2.4, 0.12), (q, tip - q - 0.6, 0.07), (tip - 0.2, 0.0, 0.0)]
        L.sweep(bm, [(cx + d * P * ca, cy + d * P * sa, h * s, w * P, h * s) for d, w, h in path],
                sides=4, mat=POINT, smooth=False, phase=0.0)
        L.sweep(bm, [(cx + d * P * ca, cy + d * P * sa, z * s + 0.01, 0.5 * P * s, 0.012)
                     for d, z in ((1.0, 0.3), (q * 0.6, 0.24), (q, 0.14), (tip - 1.5, 0.04))], sides=4, mat=HOT, smooth=False)
    # White-hot core.
    L.ellipsoid(bm, (cx, cy, 0.24 * s), (2.0 * P * s, 2.0 * P * s, 0.1 * s), mat=CORE, segments=12, rings=6)
    return L.to_object(tag, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    models = []
    for i, frame in enumerate(sprite["frames"]):
        tag = NAME if i == 0 else f"{NAME}-f{i + 1}"
        models.append((build(sprite, frame, tag), [frame["index"]]))
    L.export_frames(ROOT, NAME, sprite, models)


if __name__ == "__main__":
    main()
