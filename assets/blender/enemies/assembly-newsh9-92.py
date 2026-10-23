"""Grey shield ship (newsh9.shp, assembly of 4 pieces): a 3D version of its sprites.

Seen in episode 4 (level 4.40). Four 2x2 enemies make one 48x56 px craft (sprite.json
`assemblyLayout`): a grey shield-shaped hull, square at the top and rounding to a point at the
bottom, with a raised cabin carrying a gridded blue window, blue glass on both shoulders, two
blue lamps and a glowing blue channel down the keel to the tip. newsh9-92 and newsh9-94 (the
lower pieces) have three frames that only change the channel's colours, so one model covers them.

The craft is built whole in assembly coordinates (left half mirrored about its axis, the edge
between pixel columns 23 and 24), then cut into the four pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-92.py [-- --preview out.png]
(the preview is the whole craft; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b019 as lib  # noqa: E402

NAME = "assembly-newsh9-92"
ROOT = common.repo_root(__file__)
PIECES = ["newsh9-92", "newsh9-94", "newsh9-244", "newsh9-246"]
# Assembly pixel (0, 0) is screen (135, -23); the 48 x 56 px craft's centre (screen 159, 5) is
# the Blender origin.
CENTRE = (159, 5)
G = lib.Grid(48, 56)
AXIS = 24  # pixel edge of the mirror axis


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh9a"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.5, roughness=0.45),  # 0 hull grey
        pal(4, metallic=0.5, roughness=0.45),  # 1 keel and cabin, darker grey
        pal(7, metallic=0.55, roughness=0.35),  # 2 light grey sill, plate, ribs
        pal(2, metallic=0.2, roughness=0.8),  # 3 dark vents
        pal(149, metallic=0.6, roughness=0.15),  # 4 blue shoulder glass
        pal(147, metallic=0.5, roughness=0.2),  # 5 window grid
        pal(150, metallic=0.3, roughness=0.2, emission_strength=1.2),  # 6 window panes
        pal(156, emission_strength=4.0),  # 7 lamps
        pal(151, emission_strength=3.0),  # 8 glowing channel
        pal(9, metallic=0.6, roughness=0.3),  # 9 bright ridges and rim
        pal(6, metallic=0.5, roughness=0.4),  # 10 shoulder pods
    ]
    HULL, KEEL, LIGHT, DARK, GLASS, GRID, PANE, LAMP, CHANNEL, BRIGHT, POD = range(11)
    bm = bmesh.new()

    # ---- left half (mirrored below) ----

    # Shoulder pod under the glass (columns 0-11, rows 0-20), its lower edge sloping down and in.
    lib.slab(bm, G, [(0.4, -0.5), (12, -0.5), (12, 20.5), (8, 20.5), (5, 18.5), (2, 15.5), (0.4, 13)],
             -0.05, 0.19, mat=POD, bevel=0.8)
    # The blue glass on it (columns 1-10, rows 0-14).
    lib.slab(bm, G, [(0.8, -0.5), (9.6, -0.5), (11, 1.2), (11, 15), (9, 15), (7, 14), (5, 12), (4, 10),
                     (3, 8), (2, 5), (1, 4)], 0.16, 0.215, mat=GLASS, bevel=0.3)
    # Bright ridge along the pod's lower edge and the lip that runs in to the keel (rows 13-20).
    lib.tube(bm, G, [(1.2, 14.4, 0.0, 0.0, 0.17), (2.2, 15.6, 0.7, 0.03, 0.175), (5, 18.4, 0.7, 0.03, 0.18),
                     (8, 20.3, 0.7, 0.03, 0.18), (12.5, 20.6, 0.7, 0.03, 0.18), (13.4, 20.6, 0.0, 0.0, 0.18)],
             sides=6, mat=BRIGHT)
    # Raised rim round the lower edge of the hull (rows 36-55).
    lib.tube(bm, G, [(1.8, 34.0, 0.0, 0.0, 0.09), (2.2, 36.0, 1.2, 0.04, 0.09), (3.4, 40.0, 1.2, 0.04, 0.09),
                     (5.0, 43.0, 1.2, 0.04, 0.085), (7.2, 45.6, 1.2, 0.04, 0.08), (9.6, 48.0, 1.2, 0.04, 0.075),
                     (12.2, 50.2, 1.2, 0.04, 0.07), (14.8, 52.0, 1.2, 0.04, 0.065), (17.6, 53.6, 1.2, 0.04, 0.06),
                     (20.5, 54.6, 1.2, 0.04, 0.055), (AXIS, 55.0, 1.2, 0.04, 0.05)],
             sides=6, mat=BRIGHT, cap_end=False)
    # Panel ribs across the keel's sides (rows 31 and 36) and a dark vent at its shoulder (rows 27-30).
    for r in (31, 36):
        lib.box(bm, G, 12.6, r, 19.6, r + 1, 0.19, 0.235, mat=LIGHT)
    lib.box(bm, G, 12.2, 27, 16, 30.6, 0.2, 0.232, mat=DARK)
    # Small plate either side of the top plate (columns 11-17, rows 0-2).
    lib.box(bm, G, 12.5, -0.5, 17.5, 2.6, 0.18, 0.225, mat=KEEL)

    lib.mirror_all(bm, G.x(AXIS))

    # ---- centre parts ----

    # Hull: a flat, rounded-box shield, square at the top and rounding to the tip (rows 0-55).
    hull = [(-0.5, 23.6, 0.14), (35, 23.6, 0.14), (36.2, 23.1, 0.14), (38.5, 22.3, 0.14), (41, 21.2, 0.135),
            (42.5, 20.4, 0.13), (44, 19.4, 0.13), (45, 18.4, 0.125), (46, 17.4, 0.12), (47, 16.4, 0.12),
            (48, 15.4, 0.115), (49, 14.4, 0.11), (50, 13.4, 0.105), (51, 12.4, 0.1), (52, 10.8, 0.095),
            (53, 9.4, 0.09), (54, 7.6, 0.085), (55, 5.0, 0.07), (55.6, 2.0, 0.04)]
    lib.tube(bm, G, [(AXIS, r, w, h, 0.0) for r, w, h in hull], sides=16, mat=HULL, power=0.55)
    # Keel down the middle (columns 12-35, rows 17-55), standing above the hull.
    keel = [(16.6, 11.6, 0.2), (17.6, 12.0, 0.22), (46, 12.0, 0.22), (48, 11.6, 0.21), (50, 10.8, 0.2),
            (51.5, 9.8, 0.185), (53, 8.0, 0.165), (54.4, 5.6, 0.13), (55.3, 2.5, 0.07)]
    lib.tube(bm, G, [(AXIS, r, w, h, 0.0) for r, w, h in keel], sides=16, mat=KEEL, power=0.5)
    # The glowing channel down the keel to the tip (columns 20-27, rows 28-54).
    lib.tube(bm, G, [(AXIS, 27.6, 0.0, 0.0, 0.2), (AXIS, 28.2, 4.0, 0.06, 0.2), (AXIS, 52.5, 4.0, 0.06, 0.19),
                     (AXIS, 54.6, 3.6, 0.06, 0.15), (AXIS, 55.3, 2.5, 0.04, 0.1)],
             sides=12, mat=CHANNEL, power=0.7)
    # Two lamps across the keel (rows 18-20 and 23-25), each over a light lip.
    for r in (19.5, 24.5):
        lib.tube(bm, G, [(19.6, r, 0.0, 0.0, 0.225), (20.4, r, 1.5, 0.045, 0.225), (27.6, r, 1.5, 0.045, 0.225),
                         (28.4, r, 0.0, 0.0, 0.225)], sides=8, mat=LAMP)
        lib.box(bm, G, 19.5, r + 1.4, 28.5, r + 2.2, 0.19, 0.24, mat=LIGHT)
    # Cabin (columns 11-36, rows 0-16) with the window set into it.
    lib.slab(bm, G, [(11, -0.5), (37, -0.5), (37, 16.5), (35.5, 17.5), (12.5, 17.5), (11, 16.5)],
             -0.06, 0.2, mat=KEEL, bevel=0.4)
    lib.box(bm, G, 18, -0.5, 30, 2.6, 0.18, 0.24, mat=HULL)  # plate over the window
    lib.box(bm, G, 15, 2.6, 34, 16, 0.18, 0.205, mat=GRID)  # window: dark grid ...
    for r0, r1 in ((3.6, 8), (8.6, 10), (10.6, 12), (12.6, 16)):  # ... and its panes
        for c0, c1 in ((15.2, 22), (22.6, 26), (26.6, 30), (30.6, 33.8)):
            lib.box(bm, G, c0, r0, c1, r1, 0.2, 0.215, mat=PANE)
    lib.box(bm, G, 13.6, 2.6, 15, 16, 0.18, 0.235, mat=KEEL)  # frame either side
    lib.box(bm, G, 34, 2.6, 35.4, 16, 0.18, 0.235, mat=KEEL)
    lib.box(bm, G, 13.6, 16, 35.4, 17.2, 0.18, 0.235, mat=LIGHT)  # sill

    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.run_assembly(ROOT, NAME, PIECES, CENTRE, build, size=4, grid_w=48, grid_h=56)


if __name__ == "__main__":
    main()
