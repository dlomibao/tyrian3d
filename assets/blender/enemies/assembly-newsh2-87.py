"""Blue-armed gun walker (newsh2.shp frames 85 and 87, an assembly of 2 pieces): a 3D version of
its sprites.

Seen in episodes 1 and 3 (levels 1.25, 1.28, 1.3, 1.36, 3.17). Two 2x2 enemies side by side
(newsh2-85 on the left, newsh2-87 on the right, sprite.json `assemblyLayout`) make one 48x28 px
machine, mirror symmetric about the edge between pixel columns 22 and 23:

- a grey hull at the top with a glowing vent across its back end, light grey pods either side
  and a blue glass canopy in the middle;
- red blocks beside the hull, and bright blue arms that come out of its sides, reach outwards
  and drop down into blades;
- blue-steel legs down the outer edges, each a pair of rails joined at a foot;
- a grey stem down the middle to a round housing with a glowing red eye;
- small red indicator lights and grey knobs under the arms.

It stands on the ground. The whole machine is built once in assembly coordinates and cut into
the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-87.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b083 as lib  # noqa: E402

NAME = "assembly-newsh2-87"
ROOT = common.repo_root(__file__)
PIECES = ["newsh2-85", "newsh2-87"]
# Screen pixel at the Blender origin: between the pieces' centres (cx 194 and 218, cy 43).
CX0, CY0 = 206, 43
G = lib.Grid(48, 28)  # both pieces, newsh2-85's left edge at u = 0
AXIS = 23.0  # mirror plane: the edge between columns 22 and 23


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nsh2_87", **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.55, roughness=0.4),  # 0 grey hull
        pal(6, metallic=0.45, roughness=0.5),  # 1 dark grey lower hull
        pal(10, metallic=0.6, roughness=0.3),  # 2 light grey pods, pipe
        pal(59, metallic=0.6, roughness=0.12),  # 3 blue glass canopy
        pal(132, metallic=0.5, roughness=0.25),  # 4 light blue canopy rim
        pal(121, emission_strength=3.5),  # 5 vent glow
        pal(123, emission_strength=5.0),  # 6 vent hot core
        pal(2, metallic=0.2, roughness=0.7),  # 7 dark slots and sockets
        pal(120, metallic=0.3, roughness=0.4, emission_strength=1.2),  # 8 red blocks
        pal(155, metallic=0.4, roughness=0.3),  # 9 bright blue arms
        pal(159, metallic=0.45, roughness=0.25),  # 10 arm highlight
        pal(56, metallic=0.4, roughness=0.4),  # 11 dark blue blade tips, outer rails
        pal(57, metallic=0.45, roughness=0.35),  # 12 blue-steel legs
        pal(116, metallic=0.3, roughness=0.5),  # 13 dark red stem strips
        pal(118, emission_strength=3.0),  # 14 red eye
        pal(122, emission_strength=5.0),  # 15 eye core
        pal(9, metallic=0.55, roughness=0.35),  # 16 grey housing, knobs
        pal(120, emission_strength=3.0),  # 17 indicator lights
    ]
    (HULL, DARKHULL, POD, GLASS, RIM, VENT, VENTHOT, SLOT, REDBLOCK, ARM, ARMHI, TIP, LEG, STRIP,
     EYE, EYEHOT, HOUSING, LAMP) = range(18)
    bm = bmesh.new()

    # ---- left half (mirrored) ----
    start = len(bm.faces)
    # Light grey pod beside the canopy (columns 15-18, rows 0-7).
    lib.dloft(bm, G, 17.0, [(0.0, 1.5, 0.34, 0.2), (0.6, 2.0, 0.38, 0.2), (7.4, 2.0, 0.38, 0.2),
                            (8.2, 1.5, 0.33, 0.2)], sides=8, mat=POD, power=2.2)
    # Red block (columns 11-13, rows 2-6).
    lib.box(bm, G, 11.0, 2.0, 14.0, 7.0, 0.0, 0.34, mat=REDBLOCK, chamfer=0.04)
    # Blue arm: a bar out of the hull side (rows 5-6), the thick outer part (columns 10-14, rows
    # 7-9) and the blade dropping down from it (columns 13-14, rows 10-16).
    lib.box(bm, G, 13.0, 5.0, 17.5, 7.2, 0.1, 0.32, mat=ARM, chamfer=0.03)
    lib.box(bm, G, 9.8, 7.0, 15.0, 10.0, 0.05, 0.3, mat=ARM, chamfer=0.04)
    lib.sweep(bm, G, [(13.2, 5.4, 0.32, 0.0, 0.0), (13.6, 5.4, 0.32, 0.45, 0.02), (16.8, 5.4, 0.32, 0.45, 0.02),
                      (17.2, 5.4, 0.32, 0.0, 0.0)], sides=6, mat=ARMHI)
    lib.dloft(bm, G, 14.0, [(9.6, 1.1, 0.27), (13.2, 1.1, 0.21), (14.2, 1.05, 0.17)], sides=6, mat=ARM, power=5)
    lib.dloft(bm, G, 14.0, [(14.2, 1.05, 0.17), (16.0, 0.85, 0.1), (17.0, 0.4, 0.05)], sides=6, mat=TIP, power=5)
    # Indicator light (column 11, row 11) and grey knob (column 16, row 11) in dark sockets.
    lib.box(bm, G, 10.2, 10.0, 12.8, 13.0, 0.0, 0.09, mat=SLOT, chamfer=0.02)
    lib.dome(bm, G, 11.5, 11.5, 0.09, 0.7, 0.7, 0.05, mat=LAMP, segments=8, rings=2)
    lib.box(bm, G, 15.0, 10.0, 18.0, 13.0, 0.0, 0.09, mat=SLOT, chamfer=0.02)
    lib.dome(bm, G, 16.5, 11.5, 0.09, 0.8, 0.8, 0.06, mat=HOUSING, segments=8, rings=2)
    # Leg: an inner rail (columns 8-9, rows 4-19) and an outer rail (columns 5-6, rows 9-19),
    # joined at a foot (rows 20-24).
    lib.box(bm, G, 5.0, 9.0, 10.0, 21.0, 0.0, 0.12, mat=TIP, chamfer=0.03)
    lib.dloft(bm, G, 9.0, [(3.8, 0.6, 0.18), (4.8, 1.1, 0.23), (15.5, 1.1, 0.22), (19.8, 1.1, 0.18),
                           (21.0, 1.0, 0.15)], sides=6, mat=LEG, power=2.5)
    lib.dloft(bm, G, 6.0, [(8.8, 0.6, 0.12), (9.6, 1.1, 0.17), (20.0, 1.1, 0.16)], sides=6, mat=LEG, power=2.5)
    lib.dloft(bm, G, 7.5, [(19.6, 2.2, 0.16), (23.2, 2.0, 0.15), (24.8, 1.0, 0.08)], sides=8, mat=LEG, power=2.5)
    # Dark red strip down the side of the stem block (column 20, rows 11-13).
    lib.box(bm, G, 19.8, 10.6, 20.7, 14.0, 0.0, 0.19, mat=STRIP, chamfer=0.02)
    lib.mirror_from(bm, start, G.x(AXIS))

    # ---- centre parts ----
    # Hull (columns 15-30, rows 0-9), darker at its lower end (rows 8-9).
    lib.dloft(bm, G, AXIS, [(0.0, 7.2, 0.25), (0.6, 8.0, 0.3), (7.8, 8.0, 0.3)], sides=10, mat=HULL, power=3)
    lib.dloft(bm, G, AXIS, [(7.8, 8.0, 0.3), (9.4, 8.0, 0.28), (10.2, 7.0, 0.2)], sides=10, mat=DARKHULL, power=3)
    # Glowing vent across the back (row 0, columns 19-26) and the dark slot below it (row 1).
    lib.box(bm, G, 19.0, -0.2, 27.0, 1.0, 0.06, 0.31, mat=VENT, chamfer=0.02)
    lib.box(bm, G, 21.0, -0.25, 25.0, 0.9, 0.12, 0.315, mat=VENTHOT)
    lib.box(bm, G, 19.0, 1.0, 27.0, 2.0, 0.2, 0.31, mat=SLOT)
    # Blue glass canopy (columns 19-26, rows 2-7) with a light rim along its lower edge (row 7).
    lib.box(bm, G, 19.4, 1.9, 26.6, 7.4, 0.2, 0.41, mat=GLASS, chamfer=0.08)
    lib.sweep(bm, G, [(19.6, 7.6, 0.3, 0.0, 0.0), (20.0, 7.6, 0.3, 0.5, 0.035), (26.0, 7.6, 0.3, 0.5, 0.035),
                      (26.4, 7.6, 0.3, 0.0, 0.0)], sides=6, mat=RIM)
    # Stem block under the hull (columns 20-25, rows 10-13) and the pipe down to the eye (rows 14-17).
    lib.box(bm, G, 20.5, 9.8, 25.5, 14.0, 0.0, 0.2, mat=HOUSING, chamfer=0.03)
    lib.sweep(bm, G, [(AXIS, 13.5, 0.11, 1.0, 0.07), (AXIS, 19.0, 0.11, 1.0, 0.07)], sides=8, mat=POD)
    # Round housing with the red eye (columns 20-25, rows 18-25).
    lib.dome(bm, G, AXIS, 22.0, 0.0, 3.1, 4.0, 0.19, mat=HOUSING, segments=16, rings=4)
    lib.dome(bm, G, AXIS, 21.0, 0.12, 2.1, 2.1, 0.11, mat=EYE, segments=12, rings=3)
    lib.dome(bm, G, AXIS, 20.7, 0.2, 0.9, 0.9, 0.05, mat=EYEHOT, segments=8, rings=2)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.assembly_main(ROOT, NAME, build, PIECES, CX0, CY0, preview_tiles=2)


if __name__ == "__main__":
    main()
