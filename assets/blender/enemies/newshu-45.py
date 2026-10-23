"""Purple pod with twin burners (newshu.shp frames 45, 47, 49, 51): a 3D version of its sprite.

Seen in episode 1 (level section 19) and episode 3. A rounded purple hull, broad in the middle
and coming to a point at the bottom of the sprite (its nose), with a pale dome on top, two glowing
red slits across its back, pink knobs at the shoulders and a groove with two red rails down the
nose. At the top a dark housing holds two burners whose flames rise out of it. The frames only
change the flames and the slits' glow, so one model covers them all.

Run: blender --background --python assets/blender/enemies/newshu-45.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshu-45"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def px(x):
    """Sprite column (pixel centre) to Blender X."""
    return (x + 0.5 - 12) / 12


def row(r):
    """Sprite row (pixel centre) to Blender Y."""
    return (14 - (r + 0.5)) / 12


def edge(r):
    """Sprite row boundary (r = top edge of row r) to Blender Y."""
    return (14 - r) / 12


# Hull, top of the sprite to the nose: (row boundary, half width px, half height, z centre).
HULL = [(10.6, 0.0, 0.0, 0.06), (10.9, 6.5, 0.1, 0.06), (11.6, 8.0, 0.15, 0.05), (13.0, 8.6, 0.2, 0.04),
        (14.0, 10.0, 0.27, 0.03), (15.0, 10.9, 0.3, 0.02), (17.0, 11.2, 0.31, 0.0), (19.5, 11.2, 0.3, 0.0),
        (21.0, 10.6, 0.27, 0.0), (22.0, 9.8, 0.24, 0.0), (23.0, 8.8, 0.2, 0.0), (24.0, 7.3, 0.16, 0.0),
        (25.0, 5.8, 0.13, 0.0), (26.0, 3.8, 0.1, 0.0), (27.0, 2.0, 0.07, 0.0), (27.9, 0.0, 0.0, 0.0)]


def hull_top(r, x=0.0):
    """Height of the hull's top surface at row boundary r and Blender X (elliptic across)."""
    import math
    for (r0, w0, h0, z0), (r1, w1, h1, z1) in zip(HULL, HULL[1:]):
        if r0 <= r <= r1:
            t = (r - r0) / (r1 - r0)
            w, h, z = (w0 + (w1 - w0) * t) / 12, h0 + (h1 - h0) * t, z0 + (z1 - z0) * t
            q = 1 - (x / w) ** 2 if w > 0 else 0
            return z + h * math.sqrt(max(q, 0.0))
    return 0.0


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(86, metallic=0.45, roughness=0.4),  # 0 hull purple
        pal(82, metallic=0.4, roughness=0.5),  # 1 dark burner housing
        pal(72, metallic=0.35, roughness=0.45),  # 2 pinkish-red band and knobs
        pal(93, metallic=0.3, roughness=0.15),  # 3 pale dome
        pal(116, emission_strength=3.5),  # 4 red slits and lamp
        pal(117, emission_strength=4.0),  # 5 flames
        pal(120, emission_strength=5.0),  # 6 flame cores
        pal(71, metallic=0.35, roughness=0.45),  # 7 nose rails
        pal(66, metallic=0.2, roughness=0.7),  # 8 dark groove
        pal(96, metallic=0.1, roughness=0.6),  # 9 nose slot
        pal(65, metallic=0.2, roughness=0.6),  # 10 dark centre of the band
    ]
    HULLM, HOUSING, BAND, DOME, SLIT, FLAME, CORE, RAIL, GROOVE, SLOT, BANDDARK = range(11)
    bm = bmesh.new()

    common.loft(bm, [(edge(r), w / 12, h, z) for r, w, h, z in HULL], sides=18, mat_index=HULLM)

    # Band across the top of the hull (rows 9-10), dark in the middle between the burners.
    common.loft(bm, [(edge(8.8), 4.9 / 12, 0.07, 0.1), (edge(9.2), 5.0 / 12, 0.09, 0.1),
                     (edge(10.6), 5.0 / 12, 0.1, 0.09), (edge(11.4), 4.6 / 12, 0.08, 0.08)],
                sides=12, mat_index=BAND)
    common.slab(bm, [(px(10.4), edge(10.0)), (px(12.6), edge(10.0)), (px(12.6), edge(8.9)), (px(10.4), edge(8.9))],
                0.04, z=0.19, mat_index=BANDDARK)

    # Burner housing: side walls (columns 7 and 16) and the divider between the burners (11-12).
    for c0, c1, r0 in ((7, 8, 4.9), (16, 17, 4.9), (11, 13, 4.9)):
        r1 = 9.2 if c0 != 11 else 7.2
        common.slab(bm, [(px(c0 - 0.5), edge(r1)), (px(c1 - 0.5), edge(r1)), (px(c1 - 0.5), edge(r0)),
                         (px(c0 - 0.5), edge(r0))], 0.26, z=0.08, mat_index=HOUSING)
    # Housing floor under the burners.
    common.slab(bm, [(px(6.6), edge(9.2)), (px(16.4), edge(9.2)), (px(16.4), edge(5.5)), (px(6.6), edge(5.5))],
                0.05, z=-0.04, mat_index=HOUSING)

    # Flames rising from the burners (columns 8-10 and 13-15) out past the top of the housing.
    for c in (9, 14):
        start = len(bm.verts)
        common.loft(bm, [(edge(9.0), 0.0, 0.0, 0.07), (edge(8.4), 1.4 / 12, 0.07, 0.08),
                         (edge(6.5), 1.5 / 12, 0.075, 0.09), (edge(4.5), 1.0 / 12, 0.055, 0.1),
                         (edge(2.6), 0.45 / 12, 0.03, 0.1), (edge(1.4), 0.0, 0.0, 0.1)],
                    sides=8, mat_index=FLAME)
        common.shift_x(bm, start, px(c))
        start = len(bm.verts)
        common.loft(bm, [(edge(8.6), 0.0, 0.0, 0.1), (edge(8.0), 0.7 / 12, 0.045, 0.11),
                         (edge(6.0), 0.6 / 12, 0.04, 0.12), (edge(4.6), 0.0, 0.0, 0.12)],
                    sides=6, mat_index=CORE)
        common.shift_x(bm, start, px(c))

    # Pink knobs at the shoulders (rows 11-13, columns 5-6 and 17-18).
    for side in (-1, 1):
        start = len(bm.verts)
        common.loft(bm, [(edge(13.4), 0.0, 0.0, 0.14), (edge(12.8), 1.0 / 12, 0.05, 0.15),
                         (edge(11.6), 1.1 / 12, 0.055, 0.15), (edge(11.0), 0.0, 0.0, 0.14)],
                    sides=8, mat_index=BAND)
        common.shift_x(bm, start, side * 6.6 / 12)

    # Pale dome on top (rows 11-13, columns 9-14) with a red lamp just below it.
    z = hull_top(12.5)
    common.loft(bm, [(edge(14.0), 0.0, 0.0, z - 0.02), (edge(13.5), 2.2 / 12, 0.07, z - 0.01),
                     (edge(12.5), 2.8 / 12, 0.09, z), (edge(11.4), 2.2 / 12, 0.07, z - 0.01),
                     (edge(10.9), 0.0, 0.0, z - 0.02)], sides=12, mat_index=DOME)
    z = hull_top(13.5)
    common.loft(bm, [(edge(14.0), 0.0, 0.0, z + 0.01), (edge(13.5), 0.9 / 12, 0.035, z + 0.02),
                     (edge(13.0), 0.0, 0.0, z + 0.01)], sides=8, mat_index=SLIT)

    # The two red slits across the back (row 15, columns 11-12; row 17, columns 10-13).
    for r, half in ((15, 1.0), (17, 2.0)):
        z = hull_top(r + 0.5)
        common.slab(bm, [(-half / 12, edge(r + 1)), (half / 12, edge(r + 1)), (half / 12, edge(r)), (-half / 12, edge(r))],
                    0.05, z=z, mat_index=SLIT)
        # Dark lips either side of each slit.
        for side in (-1, 1):
            x0, x1 = sorted((side * half / 12, side * (half + 1) / 12))
            common.slab(bm, [(x0, edge(r + 1)), (x1, edge(r + 1)), (x1, edge(r)), (x0, edge(r))], 0.04, z=z - 0.005,
                        mat_index=HOUSING)

    # Groove down the nose with two red rails (rows 19-25, columns 10-13).
    for side in (-1, 1):
        start = len(bm.verts)
        common.loft(bm, [(edge(24.2), 0.0, 0.0, hull_top(24.2, 1.5 / 12)),
                         (edge(23.0), 0.5 / 12, 0.03, hull_top(23.0, 1.5 / 12)),
                         (edge(20.0), 0.55 / 12, 0.035, hull_top(20.0, 1.5 / 12)),
                         (edge(19.6), 0.0, 0.0, hull_top(19.6, 1.5 / 12))], sides=6, mat_index=RAIL)
        common.shift_x(bm, start, side * 1.5 / 12)
    for r0, r1, mat, half in ((19.2, 24.0, GROOVE, 1.0), (23.8, 26.0, SLOT, 1.0)):
        zm = hull_top((r0 + r1) / 2)
        common.slab(bm, [(-half / 12, edge(r1)), (half / 12, edge(r1)), (half / 12, edge(r0)), (-half / 12, edge(r0))],
                    0.03, z=zm - 0.005, mat_index=mat)

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
