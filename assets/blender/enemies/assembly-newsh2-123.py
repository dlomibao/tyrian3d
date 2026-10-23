"""Grey two-legged pylon with a blue tube (newsh2.shp frames 123 and 125, an assembly of 2 pieces):
a 3D version of its sprites.

Seen in episodes 1 and 3 (levels 1.25, 1.3, 1.36, 3.17), just below the blue-armed gun walker
(assembly-newsh2-87). Two 2x2 enemies side by side (newsh2-123 on the left, newsh2-125 on the
right, sprite.json `assemblyLayout`) make one 48x28 px structure, mirror symmetric about the
edge between pixel columns 22 and 23:

- a bright blue tube running down the middle from the top (rows 1-14), held in a grey cap with
  a collar across it (row 5) and sloping grey shoulders;
- two legs, each a grey hip block with a light ridge and a blue bar across it, a grey shin with a
  blue strip down its inside and a blue rail down its outside, standing in a blue boot;
- a low dark floor between the legs with a small grey pipe.

It stands on the ground. Built whole in assembly coordinates and cut into the two pieces with
common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-123.py [-- --preview out.png]
(the preview is the whole structure; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b083 as lib  # noqa: E402

NAME = "assembly-newsh2-123"
ROOT = common.repo_root(__file__)
PIECES = ["newsh2-123", "newsh2-125"]
# Screen pixel at the Blender origin: between the pieces' centres (cx 161 and 185, cy 51).
CX0, CY0 = 173, 51
G = lib.Grid(48, 28)  # both pieces, newsh2-123's left edge at u = 0
AXIS = 23.0  # mirror plane: the edge between columns 22 and 23


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nsh2_123", **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.55, roughness=0.4),  # 0 grey cap, shoulders, hips
        pal(11, metallic=0.6, roughness=0.3),  # 1 light grey ridges
        pal(9, metallic=0.3, roughness=0.45),  # 2 grey shins and hips
        pal(5, metallic=0.45, roughness=0.45),  # 3 dark grey shin bottoms
        pal(2, metallic=0.2, roughness=0.7),  # 4 dark floor
        pal(155, metallic=0.45, roughness=0.2),  # 5 bright blue tube
        pal(159, metallic=0.5, roughness=0.2),  # 6 blue highlight
        pal(132, metallic=0.45, roughness=0.3),  # 7 blue strips and bars
        pal(58, metallic=0.45, roughness=0.35),  # 8 blue outer rails
        pal(57, metallic=0.45, roughness=0.35),  # 9 blue boots
        pal(56, metallic=0.4, roughness=0.4),  # 10 dark end of the tube
    ]
    CAP, RIDGE, SHIN, SHINDARK, FLOOR, TUBE, TUBEHI, STRIP, RAIL, BOOT, TUBEEND = range(11)
    bm = bmesh.new()

    # ---- left half (mirrored) ----
    start = len(bm.faces)
    # Cap side beside the tube (columns 19-20, rows 1-4) and the shoulder sloping out (rows 5-6).
    lib.box(bm, G, 19.0, 0.8, 21.2, 5.2, 0.0, 0.37, mat=CAP, chamfer=0.04)
    lib.plate(bm, G, [(21.0, 4.8), (18.2, 4.8), (16.4, 7.2), (21.0, 7.2)], 0.0, 0.27, mat=CAP)
    # Hip block (columns 15-19, rows 9-12) with a light ridge (column 17) and the blue bar across
    # it out to the rail (row 11).
    lib.box(bm, G, 15.0, 8.8, 20.0, 13.4, 0.0, 0.3, mat=SHIN, chamfer=0.05)
    lib.sweep(bm, G, [(17.5, 8.9, 0.3, 0.0, 0.0), (17.5, 9.3, 0.3, 0.55, 0.035), (17.5, 14.6, 0.27, 0.55, 0.035),
                      (17.5, 15.0, 0.26, 0.0, 0.0)], sides=6, mat=RIDGE)
    lib.sweep(bm, G, [(12.8, 11.5, 0.22, 0.0, 0.0), (13.2, 11.5, 0.24, 0.6, 0.05), (16.0, 11.5, 0.3, 0.6, 0.05),
                      (19.4, 11.5, 0.3, 0.6, 0.05), (19.8, 11.5, 0.3, 0.0, 0.0)], sides=6, mat=STRIP)
    lib.dome(bm, G, 17.3, 11.5, 0.31, 1.1, 0.7, 0.05, mat=TUBEHI, segments=8, rings=2)
    # Shin (columns 15-17, rows 12-22), darker where it meets the boot, with a blue strip down
    # its inner side (column 17) and a blue rail down the outside (column 13, rows 11-19).
    lib.dloft(bm, G, 16.5, [(12.5, 1.5, 0.24), (19.6, 1.5, 0.22)], sides=8, mat=SHIN, power=3)
    lib.dloft(bm, G, 16.5, [(19.6, 1.5, 0.22), (23.2, 1.5, 0.19)], sides=8, mat=SHINDARK, power=3)
    lib.sweep(bm, G, [(17.6, 14.4, 0.22, 0.0, 0.0), (17.6, 14.9, 0.225, 0.55, 0.03), (17.6, 23.5, 0.19, 0.55, 0.03),
                      (17.6, 24.0, 0.18, 0.0, 0.0)], sides=6, mat=STRIP)
    lib.dloft(bm, G, 13.5, [(11.0, 0.7, 0.2), (19.5, 0.7, 0.15), (20.5, 0.7, 0.13)], sides=6, mat=RAIL, power=2.5)
    # Blue boot (columns 12-17, rows 20-26).
    lib.box(bm, G, 12.0, 19.6, 18.2, 26.0, 0.0, 0.15, mat=BOOT, chamfer=0.04)
    lib.box(bm, G, 13.0, 25.5, 18.0, 27.0, 0.0, 0.09, mat=RAIL, chamfer=0.03)
    lib.mirror_from(bm, start, G.x(AXIS))

    # ---- centre parts ----
    # The blue tube (columns 21-24, rows 1-14) and the grey collar across it (row 5).
    lib.sweep(bm, G, [(AXIS, 0.9, 0.22, 1.9, 0.13), (AXIS, 12.6, 0.22, 2.0, 0.13), (AXIS, 13.8, 0.2, 1.5, 0.1),
                      (AXIS, 14.8, 0.17, 0.9, 0.07)], sides=12, mat=TUBE)
    lib.sweep(bm, G, [(AXIS, 14.8, 0.17, 0.9, 0.07), (AXIS, 15.3, 0.16, 0.0, 0.0)], sides=12, mat=TUBEEND)
    lib.sweep(bm, G, [(22.4, 1.4, 0.34, 0.0, 0.0), (22.4, 1.8, 0.348, 0.5, 0.012), (22.4, 12.2, 0.348, 0.5, 0.012),
                      (22.4, 12.6, 0.34, 0.0, 0.0)], sides=6, mat=TUBEHI)
    lib.box(bm, G, 18.0, 4.9, 28.0, 6.1, 0.0, 0.38, mat=CAP, chamfer=0.04)
    # Low dark floor between the legs (rows 13-20) with a small grey pipe (column 23, rows 15-19).
    lib.box(bm, G, 18.5, 13.0, 27.5, 20.5, 0.0, 0.08, mat=FLOOR, chamfer=0.02)
    lib.sweep(bm, G, [(23.5, 15.0, 0.1, 0.6, 0.05), (23.5, 19.5, 0.1, 0.6, 0.05)], sides=6, mat=SHIN)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.assembly_main(ROOT, NAME, build, PIECES, CX0, CY0, preview_tiles=2)


if __name__ == "__main__":
    main()
