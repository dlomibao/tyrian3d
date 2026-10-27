"""Glowing fire crescent (newshk.shp frames 115, 117, 119): a 3D version of its sprite.

Seen in episode 3 (level 12) as a ground object. A crescent of fire in the lower half of its
block, horns curling up at the left and right edges, thickest and hottest at the bottom centre.
The three frames only brighten it, so one model covers them all: a rounded red ridge lying
along the arc, a brighter orange core line along its crest and a yellow-hot swell at the centre,
each stepping up through the palette with the frames (palette_material frames=).

Run: blender --background --python assets/blender/enemies/newshk-115.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from lib_b074 import dome, ex, ey, sweep  # noqa: E402

NAME = "newshk-115"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# The arc's centre line, left horn tip to the bottom centre, in sprite pixel edges:
# (column, row, half width px, height units).
HALF = [(1.4, 12.3, 0.5, 0.04), (1.5, 14.3, 1.4, 0.07), (2.3, 16.7, 1.7, 0.09), (3.6, 18.7, 1.9, 0.11),
        (5.3, 20.1, 2.1, 0.12), (7.3, 21.0, 2.5, 0.14), (9.6, 21.45, 3.1, 0.16), (12.0, 21.6, 3.4, 0.17)]


def catmull(points, steps=3):
    """Smooth a polyline of tuples with Catmull-Rom (all components), keeping the end points."""
    out = []
    n = len(points)
    for i in range(n - 1):
        p0, p1, p2, p3 = points[max(i - 1, 0)], points[i], points[i + 1], points[min(i + 2, n - 1)]
        for s in range(steps):
            t = s / steps
            out.append(tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t
                                    + (-a + 3 * b - 3 * c + d) * t ** 3) for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(points[-1])
    return out


def build(sprite):
    coll = common.reset_collection(NAME)
    # Every pixel steps up two palette shades on frame 117 and four on 119; the ridge and core
    # (which mostly show their shaded sides) step a little less: {sprite frame: palette index}.
    pal = lambda i, part, frames, **kw: common.palette_material(  # noqa: E731
        sprite, i, f"{NAME}-{part}", frames=frames, **kw)
    mats = [
        pal(119, "fire", {117: 120, 119: 121}, metallic=0.0, roughness=0.6, emission_strength=2.5),  # 0 red fire
        pal(123, "core", {117: 124, 119: 125}, metallic=0.0, roughness=0.5, emission_strength=3.5),  # 1 orange core
        pal(125, "hot", {117: 126, 119: 127}, metallic=0.0, roughness=0.4, emission_strength=5.0),  # 2 yellow-hot centre
    ]
    FIRE, CORE, HOT = range(3)
    bm = bmesh.new()

    full = HALF + [(24 - c, r, w, h) for c, r, w, h in reversed(HALF[:-1])]
    path = catmull(full, steps=3)
    sweep(bm, [(ex(c), ey(r), w / 12, h) for c, r, w, h in path], segs=6, mat_index=FIRE)
    # The brighter line along the crest, lifted so it shows through the top.
    core = [(c, r + 0.2, w * 0.62, h * 1.15) for c, r, w, h in path[1:-1]]
    sweep(bm, [(ex(c), ey(r), w / 12, h) for c, r, w, h in core], segs=6, mat_index=CORE)
    # The hottest swell at the bottom centre (columns 7-16, rows 20-22).
    dome(bm, ex(12), ey(21.7), 0.0, 4.5 / 12, 1.6 / 12, 0.235, sides=14, rings=4, mat_index=HOT)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])
    if "--frames" in sys.argv:
        common.render_frame_previews([obj], sys.argv[sys.argv.index("--frames") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
