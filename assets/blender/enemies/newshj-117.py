"""Green pod crawler (newshj.shp frame 117): a 3D version of its sprite.

Seen in episode 2 (level 2.2), on the ground. A green armoured body shaped like a T seen from
above: a rounded crossbar across the top (rows 2-9), and a keel-shaped hull below it that tapers
to a point at the bottom (rows 8-26) with a light spine down its middle. Two red pods hang on
either side of the hull, each with a glowing orange-yellow core and a hot spot near its top, and a
small red cap behind the crossbar carries two glowing vents. Mirror symmetric about column 12.
One frame.

Run: blender --background --python assets/blender/enemies/newshj-117.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b126 as lib  # noqa: E402

NAME = "newshj-117"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)
AXIS = G.X(12)  # the sprite's mirror axis: the centre of pixel column 12


def ex(c):
    return G.E(c, 0)[0]


def ey(r):
    return G.E(0, r)[1]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(39, metallic=0.25, roughness=0.5),  # 0 green armour
        pal(36, metallic=0.2, roughness=0.6),  # 1 dark green underside and keel tip
        pal(43, metallic=0.3, roughness=0.4),  # 2 light spine
        pal(117, metallic=0.3, roughness=0.45),  # 3 red pods and cap
        pal(114, metallic=0.25, roughness=0.55),  # 4 dark red pod ends
        pal(122, emission_strength=3.0),  # 5 orange glowing cores
        pal(124, emission_strength=5.0),  # 6 yellow hot spots
        pal(240, metallic=0.2, roughness=0.6),  # 7 dark seams
    ]
    HULL, DARK, SPINE, RED, DRED, GLOW, HOT, SEAM = range(len(mats))
    bm = bmesh.new()

    # ---- left half (mirrored below) ----
    # Red pod on the hull's side (columns 4-7, rows 8-21), its lower end tucked toward the keel.
    pod_x, pz, ph = ex(6.0), 0.13, 0.12
    lib.loft_y(bm, pod_x, [(ey(22.2), 0.0, 0.0, pz - 0.03), (ey(21.2), 1.1 / 12, 0.07, pz - 0.02),
                           (ey(19.8), 1.9 / 12, ph * 0.95, pz), (ey(16.0), 2.05 / 12, ph, pz),
                           (ey(11.0), 2.05 / 12, ph, pz), (ey(9.0), 1.9 / 12, ph * 0.9, pz),
                           (ey(7.9), 0.0, 0.0, pz - 0.01)], sides=10, mat=RED)
    bm.verts.ensure_lookup_table()
    # Darker red ends (rows 8-9 and 19-21).
    lib.loft_y(bm, pod_x, [(ey(21.4), 1.0 / 12, 0.068, pz - 0.02), (ey(20.0), 1.95 / 12, ph * 0.97, pz),
                           (ey(19.3), 2.1 / 12, ph + 0.004, pz)], sides=10, mat=DRED)
    # Glowing core (column 6, rows 13-18) with its hot spot, and the spot near the top (row 10).
    lib.ellipsoid(bm, ex(6.2), G.Y(15.6), pz + ph - 0.035, 1.5 / 12, 3.1 / 12, 0.055, segments=10, rings=6, mat=GLOW)
    lib.ellipsoid(bm, ex(6.3), G.Y(16.0), pz + ph - 0.002, 0.8 / 12, 1.5 / 12, 0.04, segments=8, rings=4, mat=HOT)
    lib.ellipsoid(bm, ex(5.6), G.Y(10.2), pz + ph - 0.03, 0.8 / 12, 0.8 / 12, 0.04, segments=8, rings=4, mat=GLOW)
    # Dark seam between the pod and the hull (column 7).
    lib.box(bm, G, 7.6, 9.0, 8.2, 20.5, 0.02, pz + 0.06, SEAM)
    # Glowing vent on the red cap behind the crossbar (column 9, row 1).
    lib.ellipsoid(bm, G.X(9.2), G.Y(1.1), 0.17, 1.4 / 12, 0.9 / 12, 0.05, segments=8, rings=4, mat=GLOW)
    lib.ellipsoid(bm, G.X(9.4), G.Y(1.2), 0.2, 0.6 / 12, 0.5 / 12, 0.03, segments=6, rings=3, mat=HOT)

    lib.mirror_x(bm, AXIS)

    # ---- centre parts ----
    # Red cap behind the crossbar (columns 6-17, rows 0-2).
    lib.loft_x(bm, ey(1.4), [(ex(6.0), 0.0, 0.0, 0.1), (ex(6.6), 1.0 / 12, 0.08, 0.11),
                             (ex(8.0), 1.4 / 12, 0.11, 0.12), (ex(17.0), 1.4 / 12, 0.11, 0.12),
                             (ex(18.4), 1.0 / 12, 0.08, 0.11), (ex(19.0), 0.0, 0.0, 0.1)], sides=10, mat=RED)
    # Crossbar (columns 2-22, rows 2-9): a rounded bar across the top.
    bz, bh = 0.17, 0.15
    lib.loft_x(bm, ey(5.6), [(ex(1.9), 0.0, 0.0, bz), (ex(2.2), 2.4 / 12, bh * 0.75, bz),
                             (ex(3.2), 3.5 / 12, bh, bz), (ex(21.8), 3.5 / 12, bh, bz),
                             (ex(22.8), 2.4 / 12, bh * 0.75, bz), (ex(23.1), 0.0, 0.0, bz)], sides=12, mat=HULL)
    # Keel-shaped hull (columns 8-16, rows 7-27), tapering to a point at the bottom.
    hz = 0.15
    lib.loft_y(bm, AXIS, [(ey(27.0), 0.0, 0.0, hz - 0.06), (ey(26.4), 1.5 / 12, 0.07, hz - 0.04),
                          (ey(25.4), 2.5 / 12, 0.1, hz - 0.02), (ey(24.2), 3.5 / 12, 0.12, hz),
                          (ey(22.6), 4.4 / 12, 0.14, hz), (ey(14.0), 4.6 / 12, 0.15, hz),
                          (ey(7.5), 4.6 / 12, 0.15, hz), (ey(6.5), 3.5 / 12, 0.12, hz)], sides=12, mat=HULL)
    # Dark keel tip (rows 24-27).
    lib.loft_y(bm, AXIS, [(ey(27.1), 0.0, 0.0, hz - 0.06), (ey(26.4), 1.6 / 12, 0.075, hz - 0.04),
                          (ey(25.4), 2.6 / 12, 0.105, hz - 0.02), (ey(24.6), 3.2 / 12, 0.118, hz - 0.01)],
               sides=12, mat=DARK)
    # Light spine down the middle, from the crossbar's top to the keel (column 12, rows 4-23).
    lib.loft_y(bm, AXIS, [(ey(23.5), 0.0, 0.0, hz + 0.13), (ey(22.0), 0.7 / 12, 0.035, hz + 0.14),
                          (ey(10.0), 0.8 / 12, 0.04, hz + 0.15), (ey(8.0), 0.8 / 12, 0.04, bz + bh - 0.005),
                          (ey(4.5), 0.8 / 12, 0.04, bz + bh - 0.005), (ey(3.8), 0.0, 0.0, bz + bh - 0.02)],
               sides=8, mat=SPINE)
    # Two side ridges flanking the spine on the hull (columns 11 and 13, rows 10-22).
    for c in (10.9, 13.1):
        lib.loft_y(bm, G.X(c), [(ey(22.5), 0.0, 0.0, hz + 0.1), (ey(21.5), 0.45 / 12, 0.025, hz + 0.115),
                                (ey(10.5), 0.45 / 12, 0.025, hz + 0.13), (ey(9.6), 0.0, 0.0, hz + 0.12)],
                   sides=6, mat=HULL)

    bm.verts.ensure_lookup_table()
    for v in bm.verts:  # base on the ground
        if v.co.z < 0.0:
            v.co.z = 0.0
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
