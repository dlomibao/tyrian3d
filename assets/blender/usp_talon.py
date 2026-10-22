"""USP Talon, the starting ship: a 3D version of its sprite (ship sprite 233 in tyrian.shp).

The hull's outline follows the sprite row by row (tools/extract-sprites.mjs renders it); colours are
sampled from the sprite with palette 0. Exports public/models/usp_talon.glb.

Blender axes: forward is +Y, up is +Z, 1 unit = 12 Tyrian pixels. Sprite row r maps to
y = (14 - r) / 12, so the 24x28 sprite is centred on the origin.
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

NAME = "usp_talon"
SPRITE = "ship-usp-talon-top.png"

HULL, BAND, CANOPY, GLOW, SPINE = range(5)


def row(r):
    """Sprite row to Blender Y."""
    return (14 - r) / 12


# Hull: sprite width per row (outline included) -> half width; flatter toward the tail.
# (sprite row, sprite width px, half height as a fraction of half width, z centre)
OUTLINE = [
    (2, 2, 0.6, 0.0), (3, 4, 0.6, 0.01), (5, 6, 0.55, 0.02), (8, 8, 0.5, 0.03),
    (12, 10, 0.42, 0.03), (13, 12, 0.36, 0.02), (15, 14, 0.32, 0.01), (17, 16, 0.3, 0.0),
    (19, 18, 0.28, 0.0), (21, 18, 0.28, 0.0), (22, 16, 0.3, 0.0), (23, 14, 0.32, 0.0),
    (24, 12, 0.36, 0.0), (25, 10, 0.4, 0.0), (26, 6, 0.5, 0.0),
]


def hull_top(r):
    """Height of the hull's top surface on the centreline at sprite row r (linear between rows)."""
    tops = [(row_, w / 24 * hf + z) for row_, w, hf, z in OUTLINE]
    for (r0, t0), (r1, t1) in zip(tops, tops[1:]):
        if r0 <= r <= r1:
            return t0 + (t1 - t0) * (r - r0) / (r1 - r0)
    return tops[0][1] if r < tops[0][0] else tops[-1][1]


def build():
    coll = common.reset_collection(NAME)
    mats = [
        common.material("talon_hull", common.srgb(154, 130, 85), metallic=0.55, roughness=0.42),
        common.material("talon_band", common.srgb(101, 73, 32), metallic=0.3, roughness=0.65),
        common.material("talon_canopy", common.srgb(16, 8, 0), metallic=0.1, roughness=0.12),
        common.material("engine_glow", (1.0, 0.45, 0.1), emission=(1.0, 0.5, 0.12), emission_strength=6.0),
        common.material("talon_spine", common.srgb(207, 195, 158), metallic=0.5, roughness=0.3),
    ]

    bm = bmesh.new()

    sections = [(row(1.6), 0.0, 0.0, 0.0)]
    for r, w, hf, z in OUTLINE:
        half = w / 24
        sections.append((row(r), half, half * hf, z))
    sections.append((row(26.5), 0.0, 0.0, 0.0))
    common.loft(bm, list(reversed(sections)), sides=20, mat_index=HULL)

    # Side bulges (the highlighted lumps at rows 17-22, x 4-6 and 17-19): engine pods set into the hull.
    for side in (-1, 1):
        start = len(bm.verts)
        common.loft(bm, [
            (row(24.2), 0.0, 0.0, 0.03),
            (row(23.5), 0.14, 0.11, 0.04),
            (row(22), 0.23, 0.17, 0.05),
            (row(19.5), 0.25, 0.18, 0.05),
            (row(17), 0.2, 0.15, 0.05),
            (row(15), 0.11, 0.08, 0.04),
            (row(13.8), 0.0, 0.0, 0.03),
        ], sides=16, mat_index=HULL)
        common.shift_x(bm, start, side * 0.47)

    # Ribbed bands across the tail (rows 22-25).
    for r, w in ((17.6, 16.6), (22.4, 15.8), (24.6, 11.4)):
        half = w / 24 + 0.006
        y = row(r)
        common.loft(bm, [(y - 0.018, half, half * 0.33, 0.0), (y + 0.018, half, half * 0.33, 0.0)],
                    sides=20, mat_index=BAND)

    # Cockpit slit (dark pixels at rows 9-11, x 10-13).
    common.loft(bm, [
        (row(12.0), 0.0, 0.0, 0.17),
        (row(11.5), 0.11, 0.06, 0.18),
        (row(10.5), 0.14, 0.07, 0.19),
        (row(9.5), 0.11, 0.06, 0.18),
        (row(9.0), 0.0, 0.0, 0.17),
    ], sides=12, mat_index=CANOPY)

    # Bright spine down the centre (the highlight column in the sprite), broken by the cockpit.
    for r0, r1 in ((3, 8.8), (12.3, 25)):
        rows = [r1 - (r1 - r0) * i / 6 for i in range(7)]
        common.loft(bm, [(row(r), 0.05, 0.03, hull_top(r) - 0.012) for r in rows], sides=8, mat_index=SPINE)

    # Exhausts at the back of the pods: hidden from the top view, there for later effects.
    for side in (-1, 1):
        start = len(bm.verts)
        common.loft(bm, [(row(23.6), 0.08, 0.07, 0.03), (row(23.8), 0.0, 0.0, 0.03)], sides=10,
                    mat_index=GLOW, cap_start=False)
        common.shift_x(bm, start, side * 0.47)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return obj


def main():
    root = common.repo_root(__file__)
    common.reference_image(f"{NAME}_sprite", root / "reference" / "sprites" / SPRITE, 24 / 12, 28 / 12)
    obj = build()
    out = root / "public" / "models" / f"{NAME}.glb"
    common.export_glb([obj], out)
    print(f"exported {out} ({out.stat().st_size} bytes, {len(obj.data.polygons)} faces)")


if __name__ == "__main__":
    main()
