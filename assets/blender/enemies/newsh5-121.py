"""Red curled pod (newsh5.shp frames 121, 123, 125): a 3D version of its sprites.

Seen in episode 4 (levels 4.22 and 4.25), lying on the ground. A glossy red egg-shaped pod with a
glowing yellow nub near its top left, tucked into a dark crease, and two raised folds curling
round it like a shell. The three frames show it turning (the egg goes from a wide, tilted oval to
a tall narrow one), so each frame gets its own model: newsh5-121, newsh5-121-f2, newsh5-121-f3.
The body of each is fitted to that frame's silhouette (its pixel moments); the details are
placed by hand from the frame's pixels.

Run: blender --background --python assets/blender/enemies/newsh5-121.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b068 as L  # noqa: E402

common = L.common
NAME = "newsh5-121"
ROOT = common.repo_root(__file__)
HEIGHT = 0.46

# Per frame (sprite pixel coordinates, column/row of pixel centres): the glowing nub, the dark
# crease beside it and the two folds (the lighter bands of indices 116/117).
DETAILS = {
    121: dict(nub=(8.0, 8.2), core=(7.6, 7.9),
              crease=[(11.0, 6.7), (12.3, 7.6), (12.9, 9.2), (12.4, 11.0), (11.0, 12.2), (8.4, 12.4)],
              fold=[(14.2, 6.6), (14.9, 9.0), (14.7, 11.5), (13.6, 13.5), (11.6, 15.3), (9.0, 16.6)],
              rim=[(19.3, 9.6), (19.1, 12.5), (18.1, 14.8), (16.6, 16.8), (14.6, 18.4)]),
    123: dict(nub=(7.9, 7.1), core=(7.6, 6.9),
              crease=[(11.0, 5.8), (12.0, 7.0), (12.3, 9.5), (12.0, 11.2), (10.9, 12.5), (8.4, 13.0)],
              fold=[(13.6, 5.7), (14.3, 8.5), (14.3, 11.0), (13.5, 13.3), (12.0, 15.0), (10.0, 16.4)],
              rim=[(18.2, 9.0), (18.3, 12.0), (17.8, 14.6), (16.5, 16.5), (14.8, 18.1)]),
    125: dict(nub=(8.0, 6.2), core=(7.6, 5.9),
              crease=[(11.0, 4.8), (11.4, 7.0), (11.5, 9.5), (11.2, 11.8), (9.8, 13.0)],
              fold=[(13.1, 4.6), (13.3, 8.0), (13.6, 11.5), (13.1, 14.0), (12.0, 16.0), (10.0, 17.3)],
              rim=[(17.3, 8.5), (17.3, 12.0), (17.0, 14.8), (16.0, 16.8), (14.5, 18.4)]),
}


def fit(frame):
    """Centre (units), semi-axes (units) and angle (radians, Blender) of the frame's silhouette."""
    pts = [(c, r) for r, row in enumerate(frame["pixels"]) for c, v in enumerate(row) if v >= 0]
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts) / n
    syy = sum((p[1] - my) ** 2 for p in pts) / n
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts) / n
    t = 0.5 * math.atan2(2 * sxy, sxx - syy)
    a, b = (sxx + syy) / 2, math.sqrt(((sxx - syy) / 2) ** 2 + sxy ** 2)
    return (L.X(mx), L.Y(my)), (2 * math.sqrt(a + b) / 12, 2 * math.sqrt(a - b) / 12), -t


def build(sprite, frame, tag):
    coll = common.reset_collection(tag)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(116, metallic=0.2, roughness=0.3),  # 0 red shell
        pal(117, metallic=0.2, roughness=0.3),  # 1 lighter folds
        pal(113, metallic=0.1, roughness=0.6),  # 2 dark crease
        pal(121, emission_strength=2.5),  # 3 glowing nub
        pal(124, emission_strength=5.0),  # 4 its hot core
    ]
    SHELL, FOLD, CREASE, NUB, CORE = range(5)
    d = DETAILS[frame["index"]]
    (cx, cy), (ra, rb), ang = fit(frame)
    body_c = (cx, cy, 0.0)
    body_r = (ra, rb, HEIGHT)
    bm = bmesh.new()
    L.ellipsoid(bm, body_c, body_r, mat=SHELL, segments=22, rings=10, angle=ang, floor=0.0)

    def on_body(c, r, lift):
        x, y = L.X(c), L.Y(r)
        return x, y, L.ellipsoid_z(body_c, body_r, ang, x, y) + lift

    # Dark crease round the nub, then the two folds curling round it (raised bands).
    L.sweep(bm, [(*on_body(c, r, -0.006), 0.6 * L.PX, 0.022) for c, r in d["crease"]], sides=6, mat=CREASE)
    L.sweep(bm, [(*on_body(c, r, 0.0), 0.85 * L.PX, 0.035) for c, r in d["fold"]], sides=8, mat=FOLD)
    L.sweep(bm, [(*on_body(c, r, 0.0), 0.8 * L.PX, 0.03) for c, r in d["rim"]], sides=8, mat=FOLD)

    # The glowing nub and its hot core.
    x, y, z = on_body(*d["nub"], 0.0)
    L.ellipsoid(bm, (x, y, z - 0.015), (1.8 * L.PX, 1.7 * L.PX, 0.06), mat=NUB, segments=12, rings=6)
    x, y, z = on_body(*d["core"], 0.0)
    L.ellipsoid(bm, (x, y, z + 0.02), (1.2 * L.PX, 1.05 * L.PX, 0.045), mat=CORE, segments=10, rings=5)

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
