"""Hooded ship (newshv.shp frame 159): a 3D version of its sprite.

Seen in episode 2 (level 2.17). Steel-blue, flying down the screen: a rounded hood at the top
(rows 3-16) with a glowing orange chevron over it (red edged) and a blue gem under the chevron's
apex; below the hood a lower body with a raised cone down its middle (outlined in dark grooves)
and a swept fin each side (columns 0-3 and 20-23). One frame, one model.

Run: blender --background --python assets/blender/enemies/newshv-159.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b043 as lib  # noqa: E402

NAME = "newshv-159"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid()
AXIS = 12.0  # the sprite is mirror symmetric about column edge 12

# Hood sections: (row edge, half width px, half height, z centre).
HOOD = [(2.9, 0.0, 0.0, 0.0), (3.1, 3.4, 0.08, 0.0), (4.0, 5.8, 0.15, 0.0), (5.0, 6.8, 0.19, 0.0),
        (7.0, 8.0, 0.23, 0.0), (9.9, 8.5, 0.25, 0.0), (10.3, 9.0, 0.25, 0.0), (14.0, 9.0, 0.24, 0.0), (16.0, 8.8, 0.21, 0.0),
        (17.0, 7.8, 0.15, 0.0), (17.4, 0.0, 0.0, 0.0)]


def hood_z(c, r):
    """Height of the hood's top surface over pixel-edge point (c, r)."""
    for (r0, w0, h0, z0), (r1, w1, h1, z1) in zip(HOOD, HOOD[1:]):
        if r0 <= r <= r1:
            t = (r - r0) / (r1 - r0)
            w, h, z = w0 + (w1 - w0) * t, h0 + (h1 - h0) * t, z0 + (z1 - z0) * t
            d = (c - AXIS) / w if w else 1.0
            return z + h * math.sqrt(max(0.0, 1 - d * d))
    return 0.0


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(59, metallic=0.5, roughness=0.35),  # 0 hood
        pal(57, metallic=0.5, roughness=0.4),  # 1 lower body
        pal(60, metallic=0.5, roughness=0.35),  # 2 fins and cone
        pal(52, metallic=0.3, roughness=0.6),  # 3 dark grooves
        pal(115, metallic=0.2, roughness=0.4, emission_strength=1.5),  # 4 red chevron edges
        pal(123, emission_strength=4.0),  # 5 orange chevron core
        pal(150, metallic=0.3, roughness=0.15, emission_strength=3.0),  # 6 blue gem
        pal(157, emission_strength=5.0),  # 7 gem highlight
    ]
    HOODM, BODY, FIN, GROOVE, RED, ORANGE, GEM, SPARK = range(8)
    bm = bmesh.new()

    # Hood.
    lib.loft_y(bm, G, AXIS, [(r, w, h, z) for r, w, h, z in HOOD], sides=16, mat=HOODM)

    # Chevron over the hood: left arm (mirrored below) from the hood's lower edge up to the apex.
    arm = [(4.3, 16.6), (5.5, 15.4), (6.5, 14.4), (7.4, 12.8), (7.6, 11.0), (8.3, 9.4), (9.4, 7.7),
           (10.6, 6.2), (11.4, 5.2), (12.0, 4.8)]
    faces = []
    path = [(c, r, hood_z(c, r) - 0.01, 1.7, 0.045) for c, r in arm]
    faces += lib.sweep(bm, G, path, sides=8, mat=RED)
    path = [(c, r, hood_z(c, r) - 0.005, 0.95, 0.06) for c, r in arm]
    faces += lib.sweep(bm, G, path, sides=8, mat=ORANGE)
    lib.mirror_faces(bm, faces, axis_x=G.X(AXIS))

    # Blue gem under the apex (columns 10-13, rows 9-12).
    lib.ellipsoid(bm, G, AXIS, 11.0, hood_z(AXIS, 11.0) - 0.03, 2.1, 2.1, 0.07, mat=GEM, segments=12, rings=6)
    lib.ellipsoid(bm, G, 11.6, 10.6, hood_z(AXIS, 11.0) + 0.025, 0.7, 0.7, 0.025, mat=SPARK, segments=8, rings=4)

    # Lower body under the hood (rows 16-27), narrowing at the bottom.
    lib.loft_y(bm, G, AXIS, [(14.5, 7.6, 0.15, -0.04), (20.0, 7.5, 0.15, -0.04), (24.0, 7.3, 0.14, -0.04),
                              (25.3, 6.4, 0.12, -0.04), (26.3, 5.2, 0.1, -0.04), (27.3, 4.0, 0.06, -0.04),
                              (28.0, 0.0, 0.0, -0.04)], sides=14, mat=BODY)
    # Raised cone down the middle (tip at row 18, columns 8-15 at the bottom), its dark groove round it.
    lib.loft_y(bm, G, AXIS, [(17.4, 0.0, 0.0, 0.06), (18.4, 1.6, 0.06, 0.06), (21.0, 4.4, 0.09, 0.05),
                              (26.0, 4.8, 0.08, 0.03), (27.6, 4.2, 0.04, 0.0), (28.0, 0.0, 0.0, 0.0)],
               sides=12, mat=GROOVE)
    lib.loft_y(bm, G, AXIS, [(18.0, 0.0, 0.0, 0.08), (19.0, 1.4, 0.07, 0.08), (21.5, 3.4, 0.1, 0.07),
                              (25.8, 3.9, 0.09, 0.05), (27.0, 3.4, 0.05, 0.03), (27.6, 0.0, 0.0, 0.02)],
               sides=12, mat=FIN)

    # Swept fins each side (columns 0-3, rows 17-26) with a dark groove (column 4) to the body.
    fin = [(3.0, 16.8), (4.6, 17.6), (4.6, 25.0), (5.0, 25.2), (5.0, 26.6), (4.2, 27.0), (2.0, 26.8),
           (1.0, 25.6), (0.0, 25.0), (0.0, 21.0), (1.2, 19.6), (2.2, 18.0), (3.0, 17.6)]
    faces = lib.plate(bm, G, fin, -0.12, 0.0, mat=FIN, smooth=False)
    faces += lib.plate(bm, G, [(4.0, 17.8), (5.2, 17.8), (5.2, 24.0), (4.0, 24.0)], -0.12, 0.03, mat=GROOVE)
    lib.mirror_faces(bm, faces, axis_x=G.X(AXIS))

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    lib.silhouette_report(obj, sprite["frames"][0]["pixels"], G)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = lib.preview_arg()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
