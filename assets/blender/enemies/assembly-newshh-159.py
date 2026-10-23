"""Grey spider (newshh.shp frames 159, 161 and 163, three pieces): a 3D version of its sprites.

Seen in episode 2 (level 2.2). Three 2x2 enemies side by side make one 72 x 28 px machine
(sprite.json `assemblyLayout`): a round grey body with a big glass lens in its middle, two
antennae on top, green glass pods on its flanks, a curved bumper under it with a green chevron,
and on each side a thin arm arching up and out and a thick leg arching out from under the pod over
a knee and down off the bottom of the sprite.

Built whole in assembly coordinates (the left half, mirrored about pixel column 36, which is the
sprite's axis), then cut into the three pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshh-159.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b056 as lib  # noqa: E402

NAME = "assembly-newshh-159"
ROOT = common.repo_root(__file__)
PIECES = ["newshh-159", "newshh-161", "newshh-163"]
CX0, CY0 = 120, -17  # screen position of the machine's 72 x 28 px block centre (the Blender origin)
G = lib.Grid(72, 28)
AXIS = 36  # mirror symmetric about assembly pixel column 36


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshh159"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(103, metallic=0.5, roughness=0.45),  # 0 dark grey body
        pal(105, metallic=0.55, roughness=0.4),  # 1 grey arms, legs, band and bumper
        pal(107, metallic=0.6, roughness=0.3),  # 2 light grey antennae and hips
        pal(109, metallic=0.75, roughness=0.12),  # 3 bright glass lens
        pal(107, metallic=0.7, roughness=0.15),  # 4 lens core
        pal(42, metallic=0.3, roughness=0.2),  # 5 green glass pods
        pal(43, metallic=0.2, roughness=0.4),  # 6 green chevron
        pal(110, metallic=0.8, roughness=0.2),  # 7 bright studs
    ]
    BODY, GREY, LIGHT, LENS, CORE, POD, CHEVRON, STUD = range(8)
    bm = bmesh.new()

    # ---- left side (mirrored below) ----

    # Thin arm arching from the shoulder up and out to a point (rows 2-11, columns 7-30).
    lib.sweep(bm, G, [(31.0, 10.6, 0.07, 0.0, 0.0), (30.2, 10.2, 0.07, 2.0, 0.1), (28.4, 9.0, 0.07, 2.4, 0.11), (26.8, 7.8, 0.07, 2.3, 0.11),
                      (24.8, 6.2, 0.07, 2.1, 0.1), (23.0, 4.9, 0.07, 1.8, 0.09), (20.5, 3.8, 0.07, 1.2, 0.07),
                      (16.0, 3.3, 0.07, 1.0, 0.06), (12.0, 3.4, 0.06, 0.9, 0.05), (9.8, 4.1, 0.05, 0.7, 0.045),
                      (8.4, 5.2, 0.04, 0.6, 0.04), (7.6, 6.2, 0.03, 0.0, 0.0)], sides=8, mat=GREY)

    # Thick leg: out of the body's flank under the pod, arching up to a knee (columns 10-22,
    # rows 9-16) and down and out off the bottom of the sprite.
    lib.sweep(bm, G, [(23.5, 17.0, 0.0, 2.4, 0.12), (22.0, 14.2, 0.0, 2.8, 0.14), (19.8, 12.6, 0.0, 3.0, 0.15),
                      (17.0, 12.2, 0.0, 3.1, 0.16), (14.6, 13.0, 0.0, 3.0, 0.15), (12.8, 14.9, 0.0, 2.8, 0.14),
                      (11.4, 17.6, -0.01, 2.4, 0.12), (10.1, 20.2, -0.03, 1.9, 0.1), (9.0, 22.2, -0.04, 1.6, 0.09),
                      (7.9, 24.2, -0.05, 1.6, 0.09), (6.6, 26.2, -0.06, 1.9, 0.1), (5.6, 28.2, -0.07, 2.0, 0.1),
                      (5.2, 29.2, -0.07, 2.0, 0.1)], sides=10, mat=GREY)
    # A light ridge over the knee and down the leg, and a bright stud on the knee.
    lib.sweep(bm, G, [(19.5, 10.9, 0.1, 0.0, 0.0), (18.5, 10.8, 0.1, 0.6, 0.035), (15.5, 11.2, 0.12, 0.7, 0.04),
                      (13.4, 12.6, 0.12, 0.7, 0.04), (11.9, 15.0, 0.1, 0.6, 0.035), (10.5, 18.2, 0.08, 0.5, 0.03),
                      (8.8, 21.8, 0.05, 0.5, 0.025), (7.4, 25.0, 0.03, 0.5, 0.025), (6.9, 26.0, 0.03, 0.0, 0.0)],
              sides=6, mat=LIGHT)
    lib.ellipsoid(bm, G, 14.6, 11.6, 0.13, 1.4, 0.9, 0.04, mat=STUD, segments=8, rings=4)

    # Green glass pod on the flank (columns 22-28, rows 12-21).
    lib.ellipsoid(bm, G, 25.2, 16.5, 0.02, 3.9, 4.8, 0.19, mat=POD, segments=16, rings=8)

    # Antenna from the top of the body up and out (columns 29-34, rows 1-8).
    lib.sweep(bm, G, [(34.0, 8.6, 0.12, 0.0, 0.0), (33.6, 8.0, 0.12, 0.9, 0.05), (33.0, 6.0, 0.13, 0.6, 0.035),
                      (31.0, 3.0, 0.15, 0.55, 0.03), (29.4, 1.2, 0.16, 0.45, 0.025), (29.0, 0.7, 0.16, 0.0, 0.0)],
              sides=6, mat=LIGHT)
    # Bright stud on the band over the body.
    lib.ellipsoid(bm, G, 32.5, 10.4, 0.15, 1.2, 0.9, 0.04, mat=STUD, segments=8, rings=4)

    lib.mirror_all(bm, G.X(AXIS))

    # ---- centre parts ----

    # Round body (columns 27-45, rows 8-22) with a band across its top (rows 8-12).
    lib.ellipsoid(bm, G, AXIS, 15.4, 0.0, 9.6, 6.8, 0.2, mat=BODY, segments=20, rings=10, squash_bottom=0.6)
    lib.loft_x(bm, G, 10.3, [(25.5, 0.0, 0.0, 0.07), (26.0, 1.6, 0.08, 0.07), (27.5, 2.1, 0.11, 0.08),
                             (31.0, 2.1, 0.13, 0.08), (41.0, 2.1, 0.13, 0.08), (44.5, 2.1, 0.11, 0.08),
                             (46.0, 1.6, 0.08, 0.07), (46.5, 0.0, 0.0, 0.07)], sides=10, mat=GREY)
    # The big glass lens (columns 31-41, rows 13-21) and its darker core.
    lib.ellipsoid(bm, G, AXIS, 16.9, 0.1, 6.0, 5.0, 0.18, mat=LENS, segments=18, rings=9)
    lib.ellipsoid(bm, G, AXIS + 0.5, 16.8, 0.16, 3.4, 3.0, 0.135, mat=CORE, segments=14, rings=7)

    # Curved bumper under the body (columns 23-49, rows 22-27, running on off the sprite's bottom).
    lib.loft_x(bm, G, 25.6, [(22.6, 0.0, 0.0, 0.0), (23.2, 2.6, 0.07, 0.0), (24.5, 3.6, 0.1, 0.0),
                             (47.5, 3.6, 0.1, 0.0), (48.8, 2.6, 0.07, 0.0), (49.4, 0.0, 0.0, 0.0)],
               sides=10, mat=GREY)
    # Green chevron on the bumper, pointing down (columns 32-38, rows 23-27; one pixel left of the axis).
    lib.pillow(bm, G, [(32, 23), (34, 23), (35, 24), (36, 24), (37, 23), (39, 23), (38.5, 24.5), (37, 26),
                       (36, 27), (36, 28), (35, 28), (35, 27), (34, 26), (32.5, 24.5)],
               0.02, 0.13, insets=((0.4, 0.03),), mat=CHEVRON)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    lib.export_assembly(ROOT, obj, PIECES, CX0, CY0, sprite["assemblyLayout"], 6)


if __name__ == "__main__":
    main()
