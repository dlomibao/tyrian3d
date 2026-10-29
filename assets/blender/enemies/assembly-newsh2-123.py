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
        pal(8, metallic=0.55, roughness=0.4),  # 0 grey head housing and shoulders
        pal(9, metallic=0.55, roughness=0.35),  # 1 grey hips
        pal(7, metallic=0.5, roughness=0.4),  # 2 grey shins
        pal(4, metallic=0.45, roughness=0.5),  # 3 dark grey feet
        pal(2, metallic=0.2, roughness=0.7),  # 4 dark channel and bay floor
        pal(155, metallic=0.1, roughness=0.08, emission_strength=0.35),  # 5 glowing glass tube
        pal(156, metallic=0.1, roughness=0.08, emission_strength=0.3),  # 6 square head light
        pal(132, metallic=0.5, roughness=0.3),  # 7 blue hip bands, pipes and inner strips
        pal(58, metallic=0.5, roughness=0.35),  # 8 blue outer pipes and foot rims
        pal(159, metallic=0.1, roughness=0.1, emission_strength=1.0),  # 9 blue lights on the hips
        pal(56, metallic=0.4, roughness=0.3),  # 10 dark end of the tube
        pal(3, metallic=0.5, roughness=0.45),  # 11 dark gear in the bay
    ]
    CAP, HIP, SHIN, FOOT, FLOOR, TUBE, LIGHT, STRIP, RAIL, HIPLIGHT, TUBEEND, GEAR = range(12)
    bm = bmesh.new()

    # ---- left half (mirrored) ----
    start = len(bm.faces)
    # Shoulder sloping out from the head housing (rows 5-8), over a dark band in its shadow.
    lib.plate(bm, G, [(23.0, 5.6), (19.0, 5.6), (17.0, 6.1), (16.0, 7.0), (16.0, 8.2), (23.0, 8.2)],
              0.0, 0.36, mat=CAP)
    lib.box(bm, G, 14.2, 7.0, 23.0, 9.4, 0.0, 0.18, mat=FLOOR)
    # Hip (columns 15-19, rows 9-13): the round top of the leg, with a blue band round it (row 11)
    # carrying a small light where the pipe leaves it.
    lib.dloft(bm, G, 17.4, [(8.8, 1.6, 0.36), (9.3, 2.4, 0.44), (12.6, 2.4, 0.44), (13.6, 2.0, 0.4)],
              sides=8, mat=HIP, power=2.2)
    lib.dloft(bm, G, 17.4, [(10.9, 2.6, 0.465), (12.1, 2.6, 0.465)], sides=8, mat=STRIP, power=2.2)
    lib.dome(bm, G, 16.9, 11.5, 0.42, 0.9, 0.6, 0.06, mat=HIPLIGHT, segments=8, rings=2)
    # Shin (columns 15-17, rows 12-21): a round column sloping down to the foot, with a blue
    # strip down its inner side (column 17, rows 15-23).
    lib.dloft(bm, G, 16.6, [(12.8, 1.8, 0.38), (16.5, 1.8, 0.33), (21.5, 1.8, 0.25)], sides=8, mat=SHIN,
              power=2.2)
    lib.sweep(bm, G, [(17.6, 14.4, 0.28, 0.0, 0.0), (17.6, 14.9, 0.285, 0.55, 0.04), (17.6, 21.0, 0.21, 0.55, 0.04),
                      (17.6, 24.2, 0.17, 0.55, 0.04), (17.6, 24.7, 0.165, 0.0, 0.0)], sides=6, mat=STRIP)
    # Blue pipe from the hip band out to column 13 and down the outside of the leg (rows 11-16),
    # then back into the shin: one constant diameter, round bends.
    lib.sweep(bm, G, [(16.4, 11.5, 0.36, 0.6, 0.05), (14.4, 11.5, 0.33, 0.6, 0.05), (13.75, 11.7, 0.31, 0.6, 0.05),
                      (13.5, 12.3, 0.29, 0.6, 0.05)], sides=6, mat=STRIP)
    lib.sweep(bm, G, [(13.5, 12.0, 0.295, 0.6, 0.05), (13.5, 16.0, 0.24, 0.6, 0.05), (13.75, 16.8, 0.23, 0.6, 0.05),
                      (14.6, 17.1, 0.23, 0.6, 0.05), (15.6, 17.1, 0.23, 0.6, 0.05)], sides=6, mat=RAIL)
    # Foot (columns 12-17, rows 19-26): a low dark blade flaring out, with a raised blue rim round
    # its outer and bottom edge.
    lib.plate(bm, G, [(13.2, 19.2), (18.3, 19.2), (18.3, 26.8), (14.2, 26.8), (12.9, 25.9), (12.1, 24.2),
                      (12.0, 20.2)], 0.0, 0.17, mat=FOOT)
    lib.sweep(bm, G, [(12.6, 19.9, 0.17, 0.0, 0.0), (12.65, 20.3, 0.17, 0.6, 0.045), (12.7, 23.6, 0.17, 0.6, 0.045),
                      (13.4, 25.0, 0.17, 0.6, 0.045), (14.6, 25.5, 0.17, 0.6, 0.045), (18.0, 25.5, 0.17, 0.6, 0.045),
                      (18.3, 25.5, 0.17, 0.0, 0.0)], sides=6, mat=RAIL)
    lib.mirror_from(bm, start, G.x(AXIS))

    # ---- centre parts ----
    # Head housing (columns 19-26, rows 1-5), the tallest part, with the square blue light set in
    # it (columns 21-24, rows 1-4) and the grey collar band across its foot (row 5).
    lib.box(bm, G, 18.6, 0.5, 27.4, 5.2, 0.0, 0.56, mat=CAP, chamfer=0.06)
    lib.box(bm, G, 20.4, 0.7, 25.6, 4.9, 0.4, 0.575, mat=FLOOR, chamfer=0.02)
    lib.box(bm, G, 20.9, 1.0, 25.1, 4.6, 0.4, 0.6, mat=LIGHT, chamfer=0.03)
    lib.sweep(bm, G, [(17.9, 5.4, 0.42, 0.0, 0.0), (18.2, 5.4, 0.42, 0.7, 0.07), (27.8, 5.4, 0.42, 0.7, 0.07),
                      (28.1, 5.4, 0.42, 0.0, 0.0)], sides=6, mat=CAP)
    # Dark channel down the middle (columns 20-25, rows 5-14) holding the glowing glass tube
    # (columns 21-24, rows 6-14), round and as tall as it is wide.
    lib.box(bm, G, 20.2, 5.0, 25.8, 13.6, 0.0, 0.2, mat=FLOOR, chamfer=0.02)
    lib.sweep(bm, G, [(AXIS, 5.6, 0.31, 1.9, 0.15), (AXIS, 12.8, 0.31, 1.9, 0.15), (AXIS, 13.8, 0.3, 1.5, 0.12),
                      (AXIS, 14.5, 0.29, 0.9, 0.07)], sides=10, mat=TUBE)
    lib.sweep(bm, G, [(AXIS, 14.5, 0.29, 0.9, 0.07), (AXIS, 15.0, 0.28, 0.0, 0.0)], sides=10, mat=TUBEEND)
    # Machinery bay between the legs (rows 13-20): a low dark floor holding a gear and a short
    # grey shaft (column 23, rows 15-19).
    lib.box(bm, G, 18.4, 12.5, 27.6, 20.4, 0.0, 0.06, mat=FLOOR, chamfer=0.015)
    lib.cylinder(bm, G, 21.0, 16.8, 0.06, 0.13, 1.9, mat=GEAR, sides=10)
    lib.cylinder(bm, G, 25.2, 16.2, 0.06, 0.11, 1.2, mat=GEAR, sides=8)
    lib.sweep(bm, G, [(23.5, 14.6, 0.17, 0.6, 0.05), (23.5, 19.3, 0.12, 0.6, 0.05)], sides=8, mat=SHIN)
    lib.cylinder(bm, G, 23.5, 15.2, 0.06, 0.2, 0.9, mat=SHIN, sides=8)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.assembly_main(ROOT, NAME, build, PIECES, CX0, CY0, preview_tiles=2)


if __name__ == "__main__":
    main()
