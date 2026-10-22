"""Player ship: a low-poly swept-wing fighter. Builds into the `player_ship` collection and exports
public/models/player_ship.glb.

Blender axes: forward is +Y, up is +Z, 1 unit = 12 Tyrian pixels (about 2 units nose to tail).
Material names are stable so the game can find them (e.g. `engine_glow` to pulse the thrusters).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

NAME = "player_ship"

HULL, ACCENT, TRIM, CANOPY, GLOW = range(5)


def build():
    coll = common.reset_collection(NAME)
    mats = [
        common.material("hull", (0.55, 0.6, 0.68), metallic=0.6, roughness=0.35),
        common.material("accent", (0.75, 0.12, 0.05), metallic=0.3, roughness=0.4),
        common.material("trim", (0.08, 0.09, 0.11), metallic=0.5, roughness=0.5),
        common.material("canopy", (0.02, 0.06, 0.12), metallic=0.2, roughness=0.08,
                        emission=(0.1, 0.45, 1.0), emission_strength=0.6),
        common.material("engine_glow", (1.0, 0.45, 0.1), emission=(1.0, 0.5, 0.12),
                        emission_strength=6.0),
    ]

    bm = bmesh.new()

    # Fuselage: (y, half width, half height, z centre), tail to nose.
    common.loft(bm, [
        (-1.0, 0.22, 0.14, 0.0),
        (-0.75, 0.3, 0.2, 0.02),
        (-0.2, 0.3, 0.22, 0.04),
        (0.35, 0.22, 0.17, 0.03),
        (0.8, 0.11, 0.09, 0.0),
        (1.12, 0.0, 0.0, -0.02),
    ], sides=8, mat_index=HULL)

    # Canopy bubble on the spine.
    common.loft(bm, [
        (-0.05, 0.0, 0.0, 0.2),
        (0.1, 0.12, 0.1, 0.2),
        (0.4, 0.1, 0.08, 0.18),
        (0.62, 0.0, 0.0, 0.14),
    ], sides=6, mat_index=CANOPY)

    # Swept wings with a red leading-edge stripe, both sides.
    wing = [(0.2, 0.25), (0.2, -0.75), (1.0, -0.88), (1.05, -0.55)]
    stripe = [(0.24, 0.18), (1.03, -0.5), (1.06, -0.58), (0.24, 0.06)]
    for mirror in (False, True):
        common.slab(bm, wing, 0.06, z=-0.02, mat_index=HULL, mirror_x=mirror)
        common.slab(bm, stripe, 0.07, z=-0.02, mat_index=ACCENT, mirror_x=mirror)

    # Wingtip cannons, pointing forward.
    for side in (-1, 1):
        start = len(bm.verts)
        common.loft(bm, [
            (-0.75, 0.05, 0.05, -0.02),
            (0.05, 0.05, 0.05, -0.02),
            (0.15, 0.03, 0.03, -0.02),
        ], sides=6, mat_index=TRIM)
        common.shift_x(bm, start, side * 1.03)

    # Engine pods with glowing exhausts.
    for side in (-1, 1):
        start = len(bm.verts)
        common.loft(bm, [
            (-1.08, 0.12, 0.12, 0.0),
            (-0.9, 0.14, 0.14, 0.0),
            (-0.45, 0.13, 0.13, 0.0),
            (-0.3, 0.07, 0.07, 0.0),
        ], sides=8, mat_index=TRIM, cap_start=False)
        common.loft(bm, [(-1.08, 0.1, 0.1, 0.0), (-1.1, 0.0, 0.0, 0.0)], sides=8, mat_index=GLOW,
                    cap_start=False)
        common.shift_x(bm, start, side * 0.36)

    # Twin tail fins, canted outward.
    for side in (-1, 1):
        common.fin(bm, (side * 0.16, -0.5, 0.12), side * 0.12, 0.5, 0.32, 0.04, mat_index=ACCENT)

    obj = common.mesh_object(NAME, bm, mats, coll)
    return obj


def main():
    obj = build()
    out = common.repo_root(__file__) / "public" / "models" / f"{NAME}.glb"
    common.export_glb([obj], out)
    print(f"exported {out} ({out.stat().st_size} bytes, {len(obj.data.polygons)} faces)")


if __name__ == "__main__":
    main()
