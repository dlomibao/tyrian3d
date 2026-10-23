"""Grey dart (newshh.shp frame 155): a 3D version of its sprite.

Seen in episode 2 (level 2.2). A steel arrowhead pointing up the screen: a long sharp nose
widening into a broad, rounded body with two short lobes at the back, a raised spine down the
nose and four bright ribs across the middle. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshh-155.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b056 as lib  # noqa: E402

NAME = "newshh-155"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)
AXIS = 12  # the sprite is symmetric about pixel column 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(105, metallic=0.55, roughness=0.35),  # 0 steel hull
        pal(107, metallic=0.6, roughness=0.3),  # 1 light spine
        pal(109, metallic=0.7, roughness=0.2),  # 2 bright ribs
        pal(102, metallic=0.5, roughness=0.45),  # 3 dark rear lobes
    ]
    HULL, SPINE, RIB, DARK = range(4)
    bm = bmesh.new()

    # Hull, nose (top of the sprite) to tail: (row, half width px, half height, z).
    hull = [(0.2, 0.0, 0.0, 0.0), (1.0, 0.6, 0.03, 0.0), (3.0, 1.5, 0.06, 0.0), (6.0, 2.5, 0.09, 0.0),
            (9.0, 3.5, 0.12, 0.0), (11.0, 4.5, 0.14, 0.0), (13.0, 5.5, 0.16, 0.0), (15.0, 6.6, 0.18, 0.0),
            (16.6, 7.8, 0.2, 0.0), (18.4, 8.5, 0.21, 0.0), (23.0, 8.5, 0.21, 0.0), (24.3, 7.8, 0.18, 0.0),
            (25.2, 6.0, 0.12, 0.0), (25.6, 3.5, 0.06, 0.0)]
    lib.loft_y(bm, G, AXIS, hull, sides=12, mat=HULL)

    # Spine down the nose, riding on the hull's top.
    lib.loft_y(bm, G, AXIS, [(r, 0.0 if i in (0, 5) else 0.7, 0.0 if i in (0, 5) else 0.04, h * 0.92)
                             for i, (r, h) in enumerate([(1.2, 0.03), (3.0, 0.06), (6.0, 0.09), (9.0, 0.12),
                                                         (12.0, 0.15), (13.8, 0.165)])],
               sides=6, mat=SPINE)

    # Four bright ribs across the middle (rows 14, 16, 18 and 21).
    for r, half in ((14, 1.4), (16, 2.3), (18, 2.3), (21, 2.3)):
        lib.loft_x(bm, G, r, [(AXIS - half - 0.3, 0.0, 0.0, 0.19), (AXIS - half, 0.75, 0.04, 0.19),
                              (AXIS + half - 0.6, 0.75, 0.04, 0.19), (AXIS + half - 0.3, 0.0, 0.0, 0.19)],
                   sides=6, mat=RIB)

    # Two lobes at the back, either side of the notch.
    for c in (8.0, 16.0):
        lib.ellipsoid(bm, G, c, 25.0, -0.01, 2.3, 1.9, 0.1, mat=DARK, segments=12, rings=6)

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
