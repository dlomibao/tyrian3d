"""Red bomber's nose (newshi.shp frame 278): a 3D version of its sprite.

Seen in episode 1 (levels 1.10, 1.29) and episode 3 (3.21), flying just below the red bomber
(assembly-newshi-243) as its own enemy, so it continues that plane's fuselage: a red cone tapering
from the full fuselage width to a point, with a light red ridge down its back, two lighter bands
across it (rows 13 and 19) and a narrow flange on each side of its root, split off by a dark
groove. It is symmetric about pixel column 12.

Run: blender --background --python assets/blender/enemies/newshi-278.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b047 as lib  # noqa: E402

NAME = "newshi-278"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(axis=11.5, mid=14)  # the usual 24x28 block: column c's centre is (c + 0.5 - 12) / 12

# The cone, root (top of the sprite, where the bomber's fuselage ends) to tip: (row, half width px,
# half height, z). The root matches the bomber's fuselage (9.6 px wide each side, 0.22 high).
CONE = [(-0.6, 9.6, 0.22, 0.0), (1.5, 9.0, 0.21, 0.0), (3.0, 7.0, 0.2, 0.0), (9.0, 6.8, 0.19, 0.0),
        (14.5, 6.4, 0.17, 0.0), (17.5, 5.2, 0.14, 0.0), (19.5, 4.3, 0.12, 0.0), (21.5, 3.3, 0.09, 0.0),
        (23.5, 2.3, 0.06, 0.0), (25.0, 1.0, 0.03, 0.0), (25.8, 0.0, 0.0, 0.0)]


def cone_at(r):
    """The cone's (half width px, half height) at row r, interpolated."""
    for (r0, w0, h0, _), (r1, w1, h1, _) in zip(CONE, CONE[1:]):
        if r0 <= r <= r1:
            t = (r - r0) / (r1 - r0)
            return w0 + (w1 - w0) * t, h0 + (h1 - h0) * t
    return 0.0, 0.0


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(70, metallic=0.3, roughness=0.45),  # 0 red cone
        pal(68, metallic=0.25, roughness=0.55),  # 1 darker red flanges
        pal(75, metallic=0.35, roughness=0.35),  # 2 light red ridge
        pal(73, metallic=0.3, roughness=0.4),  # 3 lighter bands
    ]
    RED, FLANGE, RIDGE, BAND = range(4)
    bm = bmesh.new()

    # Flanges at the root's sides (columns 3-4, rows 0-8), then mirrored about column 12.
    lib.loft_y(bm, G, 3.6, [(-0.6, 1.3, 0.09, -0.02), (7.4, 1.3, 0.09, -0.02), (8.6, 0.8, 0.06, -0.02),
                            (9.0, 0.0, 0.0, -0.02)], sides=8, mat=FLANGE)
    lib.mirror_all(bm, axis_x=G.X(12))

    lib.loft_y(bm, G, 12, CONE, sides=16, mat=RED)
    # Light ridge down the back (columns 10-13), fading out by row 12.
    lib.loft_y(bm, G, 11.8, [(-0.6, 1.9, 0.04, 0.2), (9.0, 1.7, 0.04, 0.18), (11.0, 1.2, 0.03, 0.175),
                             (12.4, 0.0, 0.0, 0.17)], sides=8, mat=RIDGE)
    # Lighter bands across the cone.
    for r in (13.0, 19.0):
        w, h = cone_at(r)
        lib.loft_y(bm, G, 12, [(r - 0.5, w + 0.25, h + 0.012, 0.0), (r + 0.5, w + 0.15, h + 0.01, 0.0)],
                   sides=16, mat=BAND)

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
