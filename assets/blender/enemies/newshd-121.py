"""Grey claw walker (newshd.shp frame 121): a 3D version of its sprite.

Seen in levels 1.5, 1.6 and 3.2. A rounded grey pod with a glowing red visor slit across its
top, a short neck, and two thick curved prongs reaching down the screen like a pincer, their
inner faces notched where they grip. Mirror symmetric about pixel edge 11. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-121.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b075 as L  # noqa: E402

NAME = "newshd-121"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 11.0  # pixel edge the sprite mirrors about
P = L.PX


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(10, metallic=0.55, roughness=0.35),  # 0 light grey pod and prongs
        pal(8, metallic=0.5, roughness=0.45),  # 1 mid grey neck, hinges
        pal(4, metallic=0.3, roughness=0.6),  # 2 dark visor frame, grip notches
        pal(119, emission_strength=4.0),  # 3 red visor light
        pal(121, emission_strength=5.0),  # 4 hot orange end of the visor
        pal(12, metallic=0.6, roughness=0.3),  # 5 bright highlights
    ]
    GREY, MID, DARK, RED, HOT, BRIGHT = range(6)
    ax = L.XE(AXIS)
    bm = bmesh.new()

    # --- left half (mirrored below) ---
    start = len(bm.verts)
    # The prong: from the shoulder (row 9) bowing out to columns 4-6 and in again to its tip (row 24).
    path = [(6.8, 8.4, 0.27, 2.0, 0.12), (6.3, 10.6, 0.28, 2.6, 0.14), (6.0, 13.4, 0.26, 2.7, 0.14),
            (5.4, 15.8, 0.23, 2.1, 0.13), (5.0, 17.8, 0.2, 1.8, 0.12), (5.1, 20.2, 0.17, 1.7, 0.11),
            (5.5, 22.2, 0.13, 1.3, 0.09), (6.0, 24.0, 0.1, 0.8, 0.06), (6.1, 25.3, 0.08, 0.0, 0.0)]
    L.sweep(bm, [(L.X(c), L.Y(r), z, w * P, h) for c, r, z, w, h in path], sides=8, mat=GREY)
    # A bright ridge along the prong's outer top (the 11-12 pixels at columns 5-6).
    ridge = [(6.0, 10.5, 0.4, 0.6, 0.03), (5.5, 13.5, 0.38, 0.7, 0.03), (5.0, 16.5, 0.33, 0.6, 0.03),
             (4.9, 19.0, 0.28, 0.5, 0.025), (5.1, 20.5, 0.25, 0.0, 0.0)]
    L.sweep(bm, [(L.X(c), L.Y(r), z, w * P, h) for c, r, z, w, h in ridge], sides=6, mat=BRIGHT)
    # The grip notch on its inner side (rows 14-15, columns 7-8).
    L.box(bm, 7.4, 13.6, 8.8, 15.8, 0.12, 0.3, mat=DARK)
    # Hinge where the prong meets the pod (rows 3-5, columns 5-6).
    L.cylinder(bm, L.XE(6.3), L.YE(4.6), 0.08, 0.36, 1.4 * P, 1.6 * P, sides=10, mat=MID)
    L.mirror_x(bm, start, ax)

    # --- centre ---
    # The pod: columns 5-16, rows 0-8.
    L.ellipsoid(bm, ax, L.YE(4.3), 0.22, 4.7 * P, 4.2 * P, 0.2, mat=GREY, segments=18, rings=9, zmin=0.0)
    # Neck under it (columns 8-13, rows 6-8) and the dark stub between the prongs.
    L.bevel_box(bm, L.XE(8.0), L.YE(9.0), L.XE(14.0), L.YE(5.5), 0.0, 0.32, 0.03, mat=MID)
    L.box(bm, 10.0, 8.5, 12.0, 10.0, 0.0, 0.12, mat=DARK)
    # Visor slit across the top of the pod (row 4): dark frame, red light, hot orange left end.
    L.bevel_box(bm, L.XE(7.4), L.YE(5.9), L.XE(14.6), L.YE(3.1), 0.25, 0.44, 0.02, mat=DARK)
    L.box(bm, 8.0, 3.8, 14.0, 5.2, 0.3, 0.465, mat=RED)
    L.box(bm, 8.0, 3.8, 9.2, 5.2, 0.3, 0.47, mat=HOT)
    # A bright cap over the top of the pod (row 2).
    L.ellipsoid(bm, ax - 0.4 * P, L.YE(2.6), 0.36, 2.6 * P, 1.2 * P, 0.06, mat=BRIGHT, segments=12, rings=6)

    return L.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = L.preview_arg()
    if out:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], str(out), ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
