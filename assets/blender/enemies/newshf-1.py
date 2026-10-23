"""Green fighter (newshf.shp frames 1, 3, 5): a 3D version of its sprite.

Seen in episode 1 (from level section 10) and episode 4. It flies nose down the screen: a
pointed hull with swept wings at the back, two yellow eyes and a spike behind. The three frames
only blink the orange wing lights, so one model covers them all.

Run: blender --background --python assets/blender/enemies/newshf-1.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshf-1"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def px(x):
    """Sprite column (pixel centre) to Blender X."""
    return (x + 0.5 - 12) / 12


def row(r):
    """Sprite row (pixel centre) to Blender Y: sprite up is +Y."""
    return (14 - (r + 0.5)) / 12


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(40, metallic=0.25, roughness=0.45),  # 0 hull green
        pal(37, metallic=0.2, roughness=0.6),  # 1 dark green underside and wing roots
        pal(43, metallic=0.3, roughness=0.35),  # 2 light green ridges
        pal(26, metallic=0.5, roughness=0.4),  # 3 brown horns
        pal(125, emission_strength=3.0),  # 4 yellow eyes
        pal(122, emission_strength=2.5),  # 5 orange wing lights
        pal(44, metallic=0.4, roughness=0.3),  # 6 pale spike
    ]
    HULL, DARK, RIDGE, HORN, EYE, LIGHT, SPIKE = range(7)
    bm = bmesh.new()

    # Hull, back (top of the sprite) to nose (bottom): (sprite row, half width px, half height px).
    hull = [(4.5, 2.0, 1.5), (7, 2.6, 2.0), (10, 3.5, 2.6), (12, 6.5, 2.8), (14, 6.0, 2.6),
            (17, 5.0, 2.3), (20, 3.4, 1.9), (23, 2.2, 1.4), (25.2, 0.0, 0.0)]
    common.loft(bm, [(row(r), w / 12, h / 12, 0.0) for r, w, h in hull], sides=10, mat_index=HULL)
    # A light ridge down the spine.
    common.loft(bm, [(row(r), 0.6 / 12, 0.6 / 12, h / 12 * 0.85) for r, _, h in hull[1:-1]], sides=6, mat_index=RIDGE)

    # Swept wings from the hull's widest point back to the tips at rows 6-11, columns 5-6.
    wing = [(px(8.5), row(14.5)), (px(10.5), row(9.5)), (px(8.0), row(7.5)), (px(5.6), row(5.8)),
            (px(5.0), row(11.5)), (px(6.6), row(14.0))]
    common.slab(bm, wing, 0.07, z=-0.02, mat_index=DARK)
    common.slab(bm, wing, 0.07, z=-0.02, mat_index=DARK, mirror_x=True)
    # Wing-tip pods with the blinking lights.
    for side in (-1, 1):
        start = len(bm.verts)
        common.loft(bm, [(row(5.6), 0.0, 0.0, 0.0), (row(6.8), 0.06, 0.06, 0.0), (row(11.5), 0.07, 0.07, 0.0),
                         (row(12.5), 0.0, 0.0, 0.0)], sides=8, mat_index=RIDGE)
        common.shift_x(bm, start, side * (12 - 5.6 - 0.5) / 12)
        start = len(bm.verts)
        common.loft(bm, [(row(9.4), 0.0, 0.0, 0.05), (row(9.9), 0.035, 0.035, 0.05), (row(10.4), 0.0, 0.0, 0.05)],
                    sides=8, mat_index=LIGHT)
        common.shift_x(bm, start, side * 0.32)

    # Brown horns beside the spike (rows 3-5, columns 10 and 16).
    for side in (-1, 1):
        start = len(bm.verts)
        common.loft(bm, [(row(6.0), 0.05, 0.04, 0.05), (row(4.5), 0.04, 0.03, 0.07), (row(3.0), 0.0, 0.0, 0.08)],
                    sides=6, mat_index=HORN)
        common.shift_x(bm, start, side * 2.6 / 12)

    # The spike behind (rows 1-5, column 13).
    start = len(bm.verts)
    common.loft(bm, [(row(6.0), 0.05, 0.05, 0.06), (row(3.0), 0.035, 0.035, 0.07), (row(0.8), 0.0, 0.0, 0.07)],
                sides=6, mat_index=SPIKE)
    common.shift_x(bm, start, px(13))

    # Yellow eyes (row 11-12, columns 12 and 14).
    for x in (12, 14):
        start = len(bm.verts)
        common.loft(bm, [(row(10.7), 0.0, 0.0, 0.2), (row(11.5), 0.06, 0.045, 0.22), (row(12.3), 0.0, 0.0, 0.2)],
                    sides=8, mat_index=EYE)
        common.shift_x(bm, start, px(x))

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


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
