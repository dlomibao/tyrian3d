"""Twin red pods (newshf.shp frame 169): a 3D version of its sprite.

Seen in episodes 1-4. Two identical red-brown pods flying side by side, twelve pixels apart:
each a round tube with a forked tail (two short prongs at the top of the sprite), flat side fins
across its upper half, a purple band round its middle and a wider collar near the blunt nose.
One frame, one model.

Run: blender --background --python assets/blender/enemies/newshf-169.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b023 as lib  # noqa: E402
from lib_b023 import common, ey  # noqa: E402

NAME = "newshf-169"
P = 1 / 12  # one sprite pixel


def pod(bm, x0):
    """One pod centred on X = x0 (its columns 3-8 are the left pod's 2-9 relative to centre 6)."""
    BODY, LIGHT, DARK, BAND, COLLAR = range(5)
    # The tube, back (row 7) to nose (row 26.8); the purple band and the collar are their own bands.
    secs = [(ey(6.8), 1.0, 0.9), (ey(7.4), 1.8, 1.6), (ey(8.5), 2.0, 1.8), (ey(16.9), 2.0, 1.8),
            (ey(17.0), 2.2, 2.0), (ey(19.0), 2.2, 2.0), (ey(19.1), 2.0, 1.8), (ey(22.9), 2.0, 1.8),
            (ey(23.0), 2.9, 2.3), (ey(25.0), 2.9, 2.3), (ey(25.1), 2.0, 1.7), (ey(26.2), 1.1, 1.0),
            (ey(26.9), 0.0, 0.0)]
    mats = [BODY, BODY, BODY, BODY, BAND, BODY, BODY, BODY, COLLAR, BODY, BODY, BODY]
    lib.ellipse_loft(bm, x0, [(y, w * P, h * P, 0.0) for y, w, h in secs], sides=12, mats=mats)
    # Side fins across rows 9-15, columns 2-9: a thin plate under the tube.
    fin = [(-4, 9), (-2.4, 9), (-2.0, 10.2), (2.0, 10.2), (2.4, 9), (4, 9), (4, 15), (3, 16),
           (-3, 16), (-4, 15)]
    common.slab(bm, [(x0 + c * P, ey(r)) for c, r in reversed(fin)], 0.08, z=-0.01, mat_index=LIGHT)
    # The forked tail: two prongs at columns 4 and 7, rows 4-7, rising a little.
    for dc in (-1.5, 1.5):
        lib.polyline_tube(bm, [(x0 + dc * P, ey(8.0), 0.04), (x0 + dc * P, ey(6.0), 0.06),
                               (x0 + dc * P * 1.05, ey(4.2), 0.08)],
                          [0.75 * P, 0.65 * P, 0.0], sides=6, mat_index=BODY if dc < 0 else DARK)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lib.palette(sprite, NAME)
    mats = [
        pal(72, metallic=0.3, roughness=0.45),  # 0 red-brown body
        pal(74, metallic=0.3, roughness=0.5),  # 1 lighter fins
        pal(67, metallic=0.35, roughness=0.5),  # 2 dark red
        pal(88, metallic=0.5, roughness=0.3),  # 3 purple band
        pal(75, metallic=0.4, roughness=0.35),  # 4 pale collar
    ]
    bm = bmesh.new()
    for x0 in (-0.5, 0.5):  # pod centres: column edges 6 and 18
        pod(bm, x0)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
