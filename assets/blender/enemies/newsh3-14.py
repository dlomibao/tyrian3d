"""Tan forklift tank (newsh3.shp frames 14, 16, 54, 90, 92): a 3D version of its sprites.

Seen in episode 4 (level 4.2). A squat tan vehicle: two track pods side by side with a light
front edge, a raised hood with a chevron of light edges between them, a darker sloping rear,
and two flat fork prongs sticking out of the front. The frames show it turned to face up,
up-right, right, down and down-right, so each heading gets its own model (newsh3-14, -f2 .. -f5):
the same vehicle, turned and placed where the frame draws it.

Run: blender --background --python assets/blender/enemies/newsh3-14.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b115 as lib  # noqa: E402

NAME = "newsh3-14"
ROOT = common.repo_root(__file__)

# Frame -> heading (degrees, counter-clockwise from facing up the screen).
HEADINGS = {14: 0, 16: -45, 54: -90, 90: 180, 92: -135}


def U(c):
    """Pixel-edge column of frame 14 (facing up) to local X about the body centre."""
    return (c - 13) / 12


def V(r):
    return (13.5 - r) / 12


def rect(c0, r0, c1, r1, z):
    return [(U(c0), V(r1), z), (U(c1), V(r1), z), (U(c1), V(r0), z), (U(c0), V(r0), z)]


def build_parts(bm):
    """The vehicle facing up, in local coordinates. Returns nothing; material slots below."""
    BODY, LIGHT, DARK, HOOD, HOOD_TOP, FORK, REAR, DECK = range(8)
    # Track pods: flat tops sloping down at the rear (rows 17-20 are darker in the sprite).
    for c0, c1 in ((6.6, 11.0), (15.0, 19.4)):
        lib.frustum(bm, rect(c0, 6.6, c1, 20.4, 0.0), rect(c0 + 0.25, 6.9, c1 - 0.25, 17.4, 0.2), mat=BODY)
        lib.box(bm, U(c0 + 0.3), V(8.0), U(c1 - 0.3), V(7.0), 0.17, 0.215, mat=LIGHT)  # light front edge
        # Rear slope colour.
        lib.frustum(bm, rect(c0 + 0.1, 17.3, c1 - 0.1, 20.3, 0.0), rect(c0 + 0.3, 17.5, c1 - 0.3, 17.8, 0.195),
                    mat=REAR)
    # Darker side of the right pod (col 18 is shaded).
    lib.box(bm, U(18.2), V(17.0), U(19.2), V(8.0), 0.1, 0.205, mat=DARK)
    # Deck between the pods, recessed at the front (the dark gap at row 7).
    lib.box(bm, U(10.8), V(20.2), U(15.2), V(8.0), 0.0, 0.13, mat=DECK)
    # Raised hood with sloped sides whose light edges make the chevron.
    lib.frustum(bm, rect(11.1, 8.4, 14.9, 17.0, 0.12), rect(12.0, 10.6, 14.0, 14.8, 0.24), mat=HOOD)
    lib.box(bm, U(12.1), V(13.6), U(13.9), V(11.6), 0.235, 0.25, mat=HOOD_TOP)
    # Fork prongs out of the front of the pods.
    for c0 in (8.0, 16.0):
        lib.box(bm, U(c0), V(7.0), U(c0 + 2), V(1.6), 0.03, 0.085, mat=FORK)
        lib.box(bm, U(c0 + 0.1), V(2.6), U(c0 + 1.9), V(1.6), 0.04, 0.09, mat=LIGHT)
        lib.box(bm, U(c0 - 0.2), V(7.6), U(c0 + 2.2), V(5.8), 0.0, 0.17, mat=BODY)  # fork mount


def build(sprite, name, frame):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(168, metallic=0.2, roughness=0.6),  # 0 body
        pal(173, metallic=0.25, roughness=0.45),  # 1 light edges and fork tips
        pal(166, metallic=0.2, roughness=0.65),  # 2 shaded side
        pal(169, metallic=0.2, roughness=0.55),  # 3 hood
        pal(171, metallic=0.25, roughness=0.5),  # 4 hood top
        pal(167, metallic=0.4, roughness=0.45),  # 5 forks
        pal(165, metallic=0.2, roughness=0.75),  # 6 rear slope
        pal(164, metallic=0.2, roughness=0.7),  # 7 deck
    ]
    bm = bmesh.new()
    build_parts(bm)
    angle = math.radians(HEADINGS[frame["index"]])
    lib.transform_since(bm, 0, Matrix.Rotation(angle, 4, "Z"))
    # Place it where the frame draws it: match the centre of its opaque pixels.
    rows = [r for r, row in enumerate(frame["pixels"]) if any(v >= 0 for v in row)]
    cols = [c for c in range(24) if any(row[c] >= 0 for row in frame["pixels"])]
    cx, cy = lib.ex((cols[0] + cols[-1] + 1) / 2), lib.ey((rows[0] + rows[-1] + 1) / 2)
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    shift = Vector((cx - (min(xs) + max(xs)) / 2, cy - (min(ys) + max(ys)) / 2, 0))
    for v in bm.verts:
        v.co += shift
    return lib.to_object(name, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    shown = []
    for i, frame in enumerate(sprite["frames"]):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, name, frame)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", lib.frame_subset(sprite, [frame["index"]]))
        shown.append((frame["index"], [obj]))
    lib.preview_frames(ROOT, NAME, sprite, shown, sys.argv)


if __name__ == "__main__":
    main()
