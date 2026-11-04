"""Rock outcrop (newshe.shp frames 1, 3, 5, 39, 41, 43; an assembly of 6 pieces): a heap of
weathered boulders around one big fissured slab, built from cross-sections, a 3D version of its
sprites.

Seen in episode 1 (levels 1.28 and 1.3) and episode 3 (3.17). Six 2x2 ground enemies side by side
(three across, two down; sprite.json `assemblyLayout`) make one 72 x 56 px heap of grey boulders on
brown dirt, lit from the top left.

The heap is the sprite's rock mask, cut (a blueprint power diagram of named seeds) into cells whose
feet tile the mask, so the top view is the sprite's outline row by row. The cells are merged into
the sprite's few big masses (MASSES): the west boulder, the mid-west boulder with its bright face,
the dark middle mass, the tall NE slab (two blocks either side of its fissure), the east block and
the dark south-east rubble, with low shelves, skirts and shards at their feet. Every mass is lofted
from horizontal cross-sections between its foot (z = 0) and an inset top:

  - "round" masses get a domed crown (rings inset step by step, relaxed smooth) and a
    quarter-ellipse shoulder down to the foot: round where the sprite is round.
  - The NE slab keeps a hard chamfered break, battered walls (more on the shaded north / east) and
    a top that rises and falls along its outline, so it is a weathered block from the side and rear.
    The fissure (the sprite's diagonal seam) is a deep V between its two blocks.
  - Low shelves are convex slabs at their own tilts; the rubble is a low concave heap with wedge
    splinters (BLADES) standing out of it.
  - The sprite's black crevices (CREVICES) are cut as deep V valleys: each mass's top is pulled back
    from them and dropped, and the walls there take palette 3, 2 at the foot.

Each face takes its mass's palette index (median of the sprite pixels under it), one darker on
walls turned from the sun, the top's index on gentle slopes seen from above, and the sprite's own
index in its lit / dark regions (REGIONS); chamfers along the sprite's lit edges take palette 9.
Each mass is a closed shell, so the cut faces common.split_assembly fills are solid rock. The
underside is a plain flat closed base.

Texture: an occlusion / edge-wear / base-darkening colour multiplier and a roughness/metal map, baked once for the
whole heap (the ships' bake, PR #84) and shared by the pieces; no concept projection (maps.json says
"bake": "model"). Each piece gets an outline shell (D51). The sprite's dirt and shadow round the
rocks are not modelled (D86; they were a flat patch of 2 x 2 px cells): the game's HD ground shows
there, and the rocks' real shadow falls on it.

Run: blender --background --python assets/blender/enemies/assembly-newshe-39.py
     [-- --preview out.png] [--no-bake] [--render DIR] [--top-tris out.json]
     The shot-away pieces (frames 7, 9, 11, 45, 47, 49 -> newshe-<n>-f2; DECISIONS.md D81, read from
     the game data, so TYRIAN_DATA): blender --background --python <this> -- --damaged [--preview out.png]
     [--render DIR]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b134 as lib  # noqa: E402

NAME = "assembly-newshe-39"
ROOT = common.repo_root(__file__)
PIECES = ["newshe-1", "newshe-3", "newshe-5", "newshe-39", "newshe-41", "newshe-43"]
SX0, SY0 = 212, -32   # screen px of assembly pixel edge (0, 0)
CX0, CY0 = 248, -4    # heap centre (the Blender origin)
U = 1 / 12


def P(c, r, z=0.0):
    """Assembly px (col right, row down, z up; pixel-edge coordinates) -> Blender units."""
    return Vector(((c - 36) * U, (28 - r) * U, z * U))


# --- columns (blueprint cells): name, pal (shaft), palTop, chamfer px, foot [(c, r)], top [(c, r, z)] ---
COLUMNS = [
    ("block-w", 6, 7, 0.7,
     [(25.0, 14.0), (28.0, 12.0), (27.8, 4.1), (32.0, 4.2), (35.2, 3.15), (38.0, 2.25), (39.0, 2.0), (42.0, 13.0), (42.0, 16.0), (40.0, 18.0), (36.0, 20.0), (31.0, 20.0), (30.0, 18.0), (25.0, 16.0)],
     # One bold lit plateau (palette 7) from the north rim to the lit ridge (29.6,4.7)-(41.3,14.2),
     # tilted down to the north rim (one broad facet, the north wall leaning in);
     # the SW part of the foot falls away from the ridge as one steep dark face. Each foot vertex
     # maps to its own top vertex: the SW chain onto the ridge, the north rim and fissure side
     # onto the plateau's edge just inside them.
     [(32.9, 8.2, 14.6), (31.3, 6.6, 14.4), (29.5, 5.1, 14.0), (32.6, 5.5, 12.6), (35.3, 4.6, 12.4), (38.1, 3.8, 12.4), (39.5, 3.8, 12.7),
      (41.2, 12.4, 13.4), (41.3, 14.3, 13.6), (40.8, 14.5, 14.0), (39.4, 14.2, 14.3), (38.0, 13.3, 14.5), (36.6, 11.9, 14.6), (34.8, 10.1, 14.6)]),
    ("block-n", 7, 7, 0.6,
     [(37.0, 3.0), (39.0, 2.0), (42.4, 1.7), (43.0, 1.0), (46.6, 1.0), (48.0, 2.0), (50.0, 2.5), (51.0, 16.0), (41.0, 17.0), (39.0, 15.0)],
     # The plateau east of the fissure: its west edge is the fissure's east lip (col 40.6 at the
     # north rim to 43 at row 14); its west wall dives under block-w's plateau.
     [(40.8, 3.6, 13.5), (41.2, 3.1, 13.4), (42.8, 3.0, 13.4), (43.4, 2.4, 13.3), (46.4, 2.4, 13.3), (47.6, 3.2, 13.4), (49.0, 3.8, 13.6), (49.6, 15.0, 13.2), (43.2, 15.8, 13.2), (42.9, 14.0, 14.2)]),
    ("block-e", 6, 6, 0.9,
     [(49.0, 2.0), (52.0, 3.4), (56.0, 4.0), (59.5, 5.3), (63.0, 7.0), (64.0, 7.0), (64.0, 9.0), (57.0, 13.0), (55.0, 16.0), (49.0, 16.0)],
     None),
    ("block-se", 6, 6, 0.8,
     [(52.0, 14.0), (61.0, 7.0), (65.0, 8.0), (65.0, 21.0), (63.0, 22.0), (63.0, 24.0), (61.0, 23.0), (61.0, 26.0), (55.0, 24.0)],
     [(53.51, 13.99, 10.5), (59.45, 9.37, 10.5), (62.09, 10.03, 10.5), (62.09, 18.61, 10.5), (60.77, 19.27, 10.5), (60.77, 20.59, 10.5), (59.45, 19.93, 10.5), (59.45, 21.91, 10.5), (55.49, 20.59, 10.5)]),
    ("front-w", 5, 5, 0.8,
     [(33.0, 18.0), (38.0, 16.0), (39.0, 14.0), (47.0, 15.0), (47.0, 22.0), (44.0, 25.0), (36.0, 25.0), (33.0, 22.0)],
     [(35.38, 17.32, 9.63), (38.98, 15.88, 9.99), (39.7, 14.44, 10.35), (45.47, 15.16, 10.17), (45.47, 20.2, 8.91), (43.3, 22.36, 8.37), (37.55, 22.36, 8.37), (35.38, 20.2, 8.91)]),
    ("front-e", 6, 6, 0.8,
     [(44.0, 20.0), (45.0, 15.0), (54.0, 14.0), (57.0, 20.0), (57.0, 24.0), (46.0, 27.0), (44.0, 25.0)],
     [(45.41, 18.9, 8.37), (46.13, 15.3, 9.27), (52.61, 14.58, 9.45), (54.77, 18.9, 8.37), (54.77, 21.78, 7.64), (46.85, 23.94, 7.11), (45.41, 22.5, 7.46)]),
    ("between", 5, 5, 0.8,
     [(21.0, 14.0), (27.0, 13.0), (33.0, 18.0), (35.0, 18.0), (35.0, 21.0), (33.0, 21.0), (30.0, 24.0), (25.0, 24.0), (25.0, 22.0), (21.0, 18.0)],
     [(23.78, 15.05, 9.85), (27.74, 14.39, 9.92), (31.7, 17.69, 9.59), (33.02, 17.69, 9.59), (33.02, 19.67, 9.39), (31.7, 19.67, 9.39), (29.72, 21.65, 9.19), (26.42, 21.65, 9.19), (26.42, 20.33, 9.32), (23.78, 17.69, 9.59)]),
    ("upper-left", 5, 5, 0.8,
     [(10.0, 15.0), (15.0, 12.0), (22.0, 12.0), (24.0, 14.0), (23.0, 18.0), (17.0, 21.0), (13.0, 21.0), (10.0, 18.0)],
     [(12.36, 14.98, 8.63), (15.86, 12.88, 8.84), (20.76, 12.88, 8.84), (22.16, 14.28, 8.7), (21.46, 17.08, 8.42), (17.26, 19.18, 8.21), (14.46, 19.18, 8.21), (12.36, 17.08, 8.42)]),
    ("bright", 7, 7, 0.8,
     [(13.0, 19.0), (19.0, 16.0), (24.0, 16.0), (28.0, 22.0), (27.0, 28.0), (13.0, 28.0)],
     [(15.96, 19.26, 8.99), (20.16, 17.16, 9.3), (23.66, 17.16, 9.3), (26.46, 21.36, 8.68), (25.76, 25.56, 8.04), (15.96, 25.56, 8.04)]),
    ("left", 6, 6, 0.8,
     [(1.0, 23.0), (3.0, 18.0), (7.0, 18.0), (11.0, 14.0), (15.0, 18.0), (14.0, 28.0), (3.0, 29.0), (3.0, 27.0), (1.0, 28.0)],
     [(3.84, 22.07, 7.57), (5.28, 18.47, 8.11), (8.16, 18.47, 8.11), (11.04, 15.59, 8.54), (13.92, 18.47, 8.11), (13.2, 25.67, 7.03), (5.28, 26.39, 6.92), (5.28, 24.95, 7.14), (3.84, 25.67, 7.03)]),
    ("skirt-left", 4, 4, 0.6,
     [(3.0, 27.0), (15.0, 26.0), (14.0, 31.0), (12.0, 31.0), (12.0, 33.0), (9.0, 33.0), (9.0, 30.0), (3.0, 30.0)],
     [(5.59, 27.16, 3.35), (12.79, 26.55, 3.47), (12.19, 29.55, 2.87), (10.99, 29.55, 2.87), (10.99, 30.75, 2.63), (9.19, 30.75, 2.63), (9.19, 28.95, 2.99), (5.59, 28.95, 2.99)]),
    ("skirt-mid", 4, 4, 0.6,
     [(15.0, 27.0), (27.0, 26.0), (30.0, 31.0), (30.0, 35.0), (27.0, 34.0), (26.0, 39.0), (25.0, 37.0), (19.0, 34.0)],
     [(18.35, 27.99, 4.1), (25.55, 27.39, 4.22), (27.35, 30.39, 3.62), (27.35, 32.79, 3.14), (25.55, 32.19, 3.26), (24.95, 35.19, 2.66), (24.35, 33.99, 2.9), (20.75, 32.19, 3.26)]),
    ("slab", 4, 4, 0.7,
     [(25.0, 24.0), (31.0, 19.0), (35.0, 19.0), (38.0, 22.0), (38.0, 30.0), (34.0, 33.0), (28.0, 34.0), (25.0, 29.0)],
     [(27.58, 24.03, 5.98), (31.54, 20.73, 6.64), (34.18, 20.73, 6.64), (36.16, 22.71, 6.25), (36.16, 27.99, 5.19), (33.52, 29.97, 4.79), (29.56, 30.63, 4.66), (27.58, 27.33, 5.32)]),
    ("splinter", 5, 5, 0.5,
     [(27.0, 33.0), (34.0, 29.0), (42.0, 31.0), (42.0, 33.0), (40.0, 34.0), (41.0, 37.0), (39.0, 38.0), (37.0, 44.0), (34.0, 43.0), (34.0, 37.0), (32.0, 37.0), (32.0, 39.0), (28.0, 38.0)],
     [(30.11, 32.67, 5.25), (34.31, 30.27, 5.97), (39.11, 31.48, 5.61), (39.11, 32.67, 5.25), (37.91, 33.27, 5.07), (38.51, 35.08, 4.53), (37.31, 35.67, 4.35), (36.11, 39.27, 3.27), (34.31, 38.67, 3.45), (34.31, 35.08, 4.53), (33.11, 35.08, 4.53), (33.11, 36.27, 4.17), (30.71, 35.67, 4.35)]),
    ("shard-lit", 5, 5, 0.6,
     [(35.0, 28.0), (36.0, 23.0), (46.0, 22.0), (48.0, 24.0), (48.0, 30.0), (44.0, 29.0), (44.0, 31.0), (41.0, 34.0), (36.0, 32.0)],
     [(37.4, 26.94, 5.07), (38.02, 23.84, 5.69), (44.22, 23.22, 5.82), (45.46, 24.46, 5.57), (45.46, 28.18, 4.83), (42.98, 27.56, 4.95), (42.98, 28.8, 4.7), (41.12, 30.66, 4.33), (38.02, 29.42, 4.58)]),
    ("shard-r", 4, 4, 0.5,
     [(45.0, 28.0), (50.0, 28.0), (50.0, 30.0), (52.0, 31.0), (52.0, 37.0), (48.0, 41.0), (46.0, 41.0), (48.0, 31.0)],
     [(46.62, 29.74, 4.65), (49.62, 29.74, 4.65), (49.62, 30.94, 4.35), (50.82, 31.54, 4.2), (50.82, 35.14, 3.3), (48.42, 37.54, 2.7), (47.22, 37.54, 2.7), (48.42, 31.54, 4.2)]),
    ("front-boulder", 4, 4, 0.6,
     [(46.0, 25.0), (54.0, 22.0), (59.0, 22.0), (61.0, 24.0), (61.0, 27.0), (58.0, 32.0), (53.0, 34.0), (52.0, 26.0), (50.0, 29.0), (51.0, 31.0), (48.0, 31.0), (46.0, 30.0)],
     [(48.46, 24.96, 5.54), (53.58, 23.04, 6.02), (56.78, 23.04, 6.02), (58.06, 24.32, 5.7), (58.06, 26.24, 5.22), (56.14, 29.44, 4.42), (52.94, 30.72, 4.1), (52.3, 25.6, 5.38), (51.02, 27.52, 4.9), (51.66, 28.8, 4.58), (49.74, 28.8, 4.58), (48.46, 28.16, 4.74)]),
]

# block-n and block-e take design B's hand-adjusted feet (the block's north tip and the east
# block's upper right, closer to the sprite's rows 0-7). Their tops are the new feet under the same
# shrink and height the blueprint gave the old feet: the affine map old foot -> old top (col, row)
# and the plane of the old top heights, fitted by least squares.
_BLUEPRINT_TOPS = {
    "block-n": ([(37.0, 3.0), (43.0, 1.0), (50.0, 2.0), (51.0, 16.0), (41.0, 17.0), (39.0, 15.0)],
                [(38.46, 4.19, 15.0), (43.26, 2.59, 15.0), (48.86, 3.39, 15.0), (49.66, 14.59, 15.0), (41.66, 15.39, 15.0), (40.06, 13.79, 15.0)]),
    "block-e": ([(49.0, 2.0), (52.5, 3.2), (62.0, 6.0), (64.0, 7.0), (64.0, 9.0), (57.0, 13.0), (55.0, 16.0), (49.0, 16.0)],
                [(49.69, 3.53, 14.2), (51.91, 5.01, 13.95), (59.31, 6.49, 13.28), (60.79, 7.23, 13.12), (60.79, 8.71, 13.05), (55.61, 11.67, 13.32), (54.13, 13.89, 13.32), (49.69, 13.89, 13.68)]),
}


def _refit_tops():
    import numpy as np
    for i, (name, pal, pal_top, ch, foot, top) in enumerate(COLUMNS):
        if top is not None:
            continue
        f0, t0 = _BLUEPRINT_TOPS[name]
        A = np.array([[c, r, 1.0] for c, r in f0])
        mc = np.linalg.lstsq(A, np.array([t[0] for t in t0]), rcond=None)[0]
        mr = np.linalg.lstsq(A, np.array([t[1] for t in t0]), rcond=None)[0]
        B = np.array([[t[0], t[1], 1.0] for t in t0])
        mz = np.linalg.lstsq(B, np.array([t[2] for t in t0]), rcond=None)[0]
        new = []
        for c, r in foot:
            tc, tr = mc @ (c, r, 1.0), mr @ (c, r, 1.0)
            new.append((float(tc), float(tr), float(mz @ (tc, tr, 1.0))))
        COLUMNS[i] = (name, pal, pal_top, ch, foot, new)


_refit_tops()

# Sprite lit edges (bright diagonals): chamfers and crown faces along them take LIT.
LIT_EDGES = [((29.5, 5.1), (40.8, 14.5)),   # lit ridge of the big block
             ((2.5, 19.5), (3.5, 23.0)),     # lit edge of the west boulder
             ((50.0, 3.4), (62.0, 6.4))]     # lit north rim of the east block
LIT = 9

# The rock is a few big masses, as in the sprite: the west boulder, the mid-west boulder (with its
# bright south-west face), the dark middle mass, the tall NE slab (two blocks either side of its
# fissure), the east block and the dark splintered rubble in the south-east, with low shelves, skirts
# and shards at their feet. Each mass's foot is the union of the blueprint cells under it, so the
# feet still tile the sprite's mask. Modes: "round" (domed crown, quarter-ellipse shoulder, smooth),
# "slab" (hard chamfer, battered walls, joint groove), "low" (convex hull, mitred inset top),
# "rubble" (concave low heap, broken top).
# name, mode, pal (sides), pal_top, chamfer px, foot [(c, r)], top [(c, r, z)] or height samples
MASSES = [
    ("left", "round", 5, 6, 0.8, "left", "left"),
    ("midwest", "round", 5, 5, 0.8,
     [(10, 15), (15, 12), (22, 12), (23.57, 13.57), (27, 13), (29.5, 18), (30, 24), (27.67, 24), (27, 28), (15.0, 28.0), (15.0, 27.3), (14.0, 26.98), (13, 21), (10, 18)],
     ["upper-left", "bright", "between"]),
    ("mid", "round", 5, 5, 0.8,
     [(27, 13), (33, 18), (38, 16), (39, 14), (47, 15), (47, 22), (44, 25), (36, 25), (33, 22), (33, 21), (30, 24), (29.5, 18)],
     ["front-w", "between"]),
    ("block-w", "face", 6, 7, 0.7, "block-w", "block-w"),
    ("block-n", "face", 6, 7, 0.6, "block-n", "block-n"),
    ("east", "round", 5, 6, 0.9,
     [(49, 2), (52, 3.4), (56, 4), (59.5, 5.3), (63, 7), (64, 7), (65, 8), (65, 21), (63, 22), (63, 24), (61, 23), (61, 26), (57, 24.6), (46, 27), (44, 25), (44, 20), (45, 15), (49, 14.56)],
     ["block-e", "block-se", "front-e"]),
    ("slab-w", "low", 4, 4, 0.7, [(25, 24), (30, 19.83), (30, 33.67), (28, 34), (25, 29)], ["slab"]),
    ("slab-e", "low", 4, 4, 0.7, [(30, 19.83), (31, 19), (35, 19), (38, 22), (38, 30), (34, 33), (30, 33.67)], ["slab"]),
    ("rubble", "rubble", 3, 3, 0.5, "rubble",
     [(50, 22.5, 3.6), (60, 24, 3.2), (48, 40, 1.4), (57, 31, 2.2), (46, 29, 3.0)]),
    ("skirt-left", "lowc", 3, 4, 0.6, "skirt-left", "skirt-left"),
    ("skirt-mid", "lowc", 3, 4, 0.6, "skirt-mid", "skirt-mid"),
    ("splinter", "lowc", 4, 5, 0.5, "splinter", "splinter"),
    ("shard-lit", "low", 4, 5, 0.6, [(35, 28), (36, 23), (46, 22), (48, 24), (47.5, 28.6), (42, 31.4), (36, 32)], "shard-lit"),
]

# Faces (crown, shoulder and sun-side walls) of a mass whose centre lies in one of these sprite
# regions take its palette index instead (the sprite's own lit / dark faces).
REGIONS = [
    ("midwest", [(17, 18.5), (22, 17.6), (25.8, 19.5), (25.8, 27.6), (17, 27.6)], 7),   # bright SW face
    ("left", [(10.5, 19), (13.6, 19), (13.6, 27), (10.5, 26.5)], 7),                           # lit east shoulder
    ("block-n", [(40.5, 3.5), (48.5, 3.5), (49.5, 11.5), (41.5, 12.5)], 8),             # lit top
    ("east", [(49, 2.5), (58, 4.0), (58.5, 10.0), (49, 11.5)], 8),                     # lit top (the slab's)
]
REGION_KINDS = {"left": ("top", "side"), "midwest": ("top", "side"), "block-n": ("top",),
                "east": ("top",)}

# The sprite's black crevices (palette 2-3) between the masses: every mass's top is pulled back
# from them and dropped, so neighbours meet in a deep V whose walls take CREV_PAL (upper) and
# CREV_DEEP (at the foot).
CREVICES = [
    [(15.0, 18.0), (14.5, 22.0), (13.6, 26.0), (13.6, 29.5)],                              # west | mid-west
    [(28.6, 17.0), (29.5, 18.5), (30.3, 23.0), (30.2, 30.0), (29.5, 34.5)],   # mid-west | middle
    [(48.0, 21.0), (45.8, 25.0), (44.6, 29.0)],                                            # middle | east
    [(46.0, 26.6), (55.0, 24.4), (61.0, 25.2), (64.0, 22.6)],                              # east foot | rubble
    [(33.5, 22.0), (36.0, 25.6), (44.0, 25.6)],                                            # middle | shard
]
CREV_R = 2.2      # px from a crevice line within which tops are pulled back
CREV_PUSH = 1.1   # px pulled back on the line
CREV_DROP = 0.32  # fraction of the height dropped on the line (at most 2.6 px)
CREV_PAL, CREV_DEEP = 3, 2

CREASE_MIN = 7.0     # px: a slab's foot edges at least this long get a vertical joint crease
CREASE_IN = 0.45
JOINT_IN = 0.35
JOINT_HALF = 0.35
DOME = 0.3
DOME_R = 0.7
ROUND_PROFILE = [(math.sin(math.radians(t)), 1 - math.cos(math.radians(t))) for t in (22, 45, 65, 80, 90)]
SUN = (-6 / math.hypot(6, 8.4), 8.4 / math.hypot(6, 8.4))
# The NE slab: its walls lean in (more on the shaded north / east sides), its rim and top are
# broken at random heights, so it is a weathered block, not a box, from the side and rear.
BATTER, BATTER_AWAY = 0.16, 0.26
JAG = 0.45
TOP_WAVE = 0.6      # px: the slab top rises and falls smoothly along its outline (broken skyline)
FISSURE = [(39.0, 2.5), (42.0, 12.5), (45.5, 17.5)]
FISS_R = 3.0
FISS_PUSH = 0.7
FISS_DROP = 1.2
FISS_PAL = 5
# "face" masses (the NE slab's two plateaus): wall indices north, east, west, south (west / east of
# col 34.5), as the sprite paints the slab's rims.
# The two plateaus are one weathered rock mass, not two lids: their walls batter (lean in as they
# rise, more on the shaded north / east and none on the lit ridge or the fissure lips), each wall
# kinks at mid height into a flared foot, the rims are broken (FACE_STEP px spans, each vertex
# nudged in and down a little) and the plateau rises gently to a low crown.
FACE_STEP = 2.6
FACE_BATTER, FACE_BATTER_AWAY = 0.07, 0.11   # px of lean per px of height
FACE_SLUMP = 1.1     # px the rim drops on the shaded sides
FACE_RIM = (0.3, 0.55)   # random rim nudge (in, down), px
FACE_KINK = 0.35     # the mid-height ring pulled in by this fraction of the wall's lean (flared foot)
FACE_CROWN = 0.7     # px the plateau's inner ring rises
FACE_LIFT = []
RIDGE_W, RIDGE_DROP = 1.5, 0.7   # px: the lit ridge bevel's width and drop
FACE_WALLS = {"block-w": (6, FISS_PAL, 4, (4, 5)),
              "block-n": (7, 7, 4, (5, 5))}


def seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def poly_dist(p, line):
    return min(seg_dist(p, a, b) for a, b in zip(line, line[1:]))


def signed_area(poly):
    n = len(poly)
    return sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n)) / 2


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, co):
        return self.bm.verts.new(co)

    def f(self, verts, slot, smooth=False):
        try:
            face = self.bm.faces.new(verts)
        except ValueError:
            return None
        face.material_index = slot
        face.smooth = smooth
        return face


def hull2d(pts):
    """Convex hull of (col, row) points (monotone chain), same orientation as the input."""
    P_ = sorted(set(pts))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P_:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P_):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    h = lo[:-1] + up[:-1]
    if (signed_area(h) > 0) != (signed_area(pts) > 0):
        h.reverse()
    return h


def plane_fit(top):
    """z(c, r) of the least-squares plane through the points [(c, r, z)]."""
    import numpy as np
    A = np.array([[c, r, 1.0] for c, r, _ in top])
    z = np.array([t[2] for t in top])
    a, b, c0 = np.linalg.lstsq(A, z, rcond=None)[0]
    return lambda c, r: a * c + b * r + c0


def inset_top(foot, top, d_of_z):
    """A low slab's top: its foot moved d_of_z(z) px inwards along each corner's bisector (a mitred
    offset, limited to 1.8 d so thin fingers stay fingers), at the blueprint top's heights. The
    sides then follow the foot as one steep chamfered face instead of tapering to spikes."""
    n = len(foot)
    sgn = 1 if signed_area(foot) > 0 else -1
    out = []
    for i in range(n):
        (pc, pr), (c, r), (nc_, nr_) = foot[i - 1], foot[i], foot[(i + 1) % n]
        def inward(a, b):
            L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
            return (-sgn * (b[1] - a[1]) / L, sgn * (b[0] - a[0]) / L)
        n1, n2 = inward((pc, pr), (c, r)), inward((c, r), (nc_, nr_))
        bc, br = n1[0] + n2[0], n1[1] + n2[1]
        bl = math.hypot(bc, br) or 1
        bc, br = bc / bl, br / bl
        cosh = max(0.3, bc * n1[0] + br * n1[1])
        z = top[i][2]
        d = d_of_z(z)
        k = min(d / cosh, 1.8 * d)
        out.append((c + bc * k, r + br * k, z))
    return out



# Low pieces whose cell is concave are broken into convex shards (the sprite's dark splinters).
SHARDS = {
    "splinter": [[(28.0, 33.0), (34, 29), (41.98, 31.0), (41.98, 31.98), (40.98, 32.98), (40.98, 36.98), (32.0, 37.0),
                  (31.98, 38.98), (29.0, 38.98), (28.0, 37.7)],
                 [(33.98, 36.9), (39.98, 36.9), (39.98, 37.2), (38.98, 38.0), (38.98, 40.9), (37.98, 41.6), (37.98, 42.98),
                  (36.98, 43.6), (36.6, 43.98), (35.2, 43.98), (33.98, 42.9)]],
    "skirt-mid": [[(14.95, 27.0), (27, 26), (30, 31), (30, 33.95), (18.95, 33.95), (18.85, 32.0), (15.85, 29.0), (15.0, 28.95)],
                  [(19.9, 33.9), (26.98, 33.9), (26.98, 38.98), (26.3, 38.98), (25.98, 38.6), (25.98, 38.0), (25.3, 38.0),
                   (24.98, 37.6), (24.98, 37.0), (23.3, 37.0), (22.98, 36.6), (22.98, 36.0), (21.3, 36.0), (20.98, 35.6),
                   (20.98, 35.0), (20.3, 35.0), (19.9, 34.6)]],
    "skirt-left": [[(3, 27), (13.95, 26.0), (13.95, 30.98), (8.98, 30.98), (8.98, 29.98), (3, 29.98)],
                   [(5.98, 29.9), (7.98, 29.9), (7.98, 30.98), (5.98, 30.98)],
                   [(8.98, 30.9), (11.98, 30.9), (11.98, 32.98), (8.98, 32.98)]],
    "rubble": [[(45.5, 26), (46, 25), (52.4, 22.5), (52.0, 25.95), (50.95, 26.05), (50.95, 28.95), (49.95, 29.05),
                (49.95, 29.95), (50.95, 30.05), (51.95, 31.0), (51.95, 36.95), (50.95, 37.05), (50.9, 37.95),
                (49.9, 38.05), (49.9, 38.95), (48.9, 39.05), (47.95, 40.95), (46.05, 40.95), (46.05, 39.3),
                (47.05, 38.3), (47.05, 32.05), (47.95, 31.95), (47.95, 31.05), (47.0, 30.95), (47.0, 30.05),
                (46.0, 29.95), (45.0, 28.0)],
               [(52.1, 23.5), (54, 22), (59, 22), (61, 24), (61, 26.2), (60.1, 27.0), (60.0, 29.9), (59.0, 30.1),
                (58.0, 31.0), (57.3, 31.98), (55.98, 32.05), (55.6, 32.95), (53.98, 33.05), (53.9, 33.95),
                (53.1, 33.95), (53.05, 30.1), (52.05, 29.9), (52.05, 26.0)]],
}
BLUEPRINT = {c[0]: c for c in COLUMNS}


def point_in(p, poly):
    x, y = p
    inside = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def ray_room(p, d, poly):
    """Distance from p along d to the polygon's boundary (ignoring edges through p)."""
    best = 1e9
    n = len(poly)
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        den = d[0] * ey - d[1] * ex
        if abs(den) < 1e-9:
            continue
        t = ((ax - p[0]) * ey - (ay - p[1]) * ex) / den
        s = ((ax - p[0]) * d[1] - (ay - p[1]) * d[0]) / den
        if t > 1e-4 and -1e-6 <= s <= 1 + 1e-6:
            best = min(best, t)
    return best


def resample(foot, top, step):
    """Split foot edges longer than step (tops interpolated with them)."""
    F, T = [], []
    n = len(foot)
    for i in range(n):
        j = (i + 1) % n
        L = math.hypot(foot[j][0] - foot[i][0], foot[j][1] - foot[i][1])
        k = max(1, math.ceil(L / step))
        for s in range(k):
            t = s / k
            F.append((foot[i][0] + (foot[j][0] - foot[i][0]) * t, foot[i][1] + (foot[j][1] - foot[i][1]) * t))
            if top is not None:
                T.append(tuple(a + (b - a) * t for a, b in zip(top[i], top[j])))
    return F, (T if top is not None else None)


def bisectors(foot):
    """Inward unit bisector and the room along it, per foot vertex."""
    n = len(foot)
    sgn = 1 if signed_area(foot) > 0 else -1
    out = []
    for i in range(n):
        a, p, b = foot[i - 1], foot[i], foot[(i + 1) % n]

        def inward(u, v):
            L = math.hypot(v[0] - u[0], v[1] - u[1]) or 1
            return (-sgn * (v[1] - u[1]) / L, sgn * (v[0] - u[0]) / L)
        n1, n2 = inward(a, p), inward(p, b)
        bc, br = n1[0] + n2[0], n1[1] + n2[1]
        bl = math.hypot(bc, br)
        if bl < 1e-6:
            bc, br, bl = n1[0], n1[1], 1.0
        bc, br = bc / bl, br / bl
        cosh = max(0.3, bc * n1[0] + br * n1[1])
        out.append(((bc, br), cosh, ray_room(p, (bc, br), foot)))
    return out


def crevice_w(p):
    d = min(poly_dist(p, line) for line in CREVICES)
    return max(0.0, 1.0 - d / CREV_R)


def heights_of(spec):
    if isinstance(spec, str):
        spec = [spec]
    pts = []
    for s in spec:
        if isinstance(s, str):
            pts += BLUEPRINT[s][5]
        else:
            pts.append(s)
    return plane_fit(pts)


def mass(M, mats, name, mode, pal, pal_top, ch, foot, top, rnd):
    """Loft one rock mass from cross-sections (see the module docstring)."""
    if isinstance(foot, str) and foot in SHARDS:
        zf = heights_of(top)
        for k, sub in enumerate(SHARDS[foot]):
            sub_top = top if mode == "rubble" else [(c, r, zf(c, r)) for c, r in sub]
            mass(M, mats, f"{name}.{k}", mode, pal, pal_top, ch, sub, sub_top, rnd)
        return
    concave = mode == "lowc"
    if concave:
        mode = "low"
    if isinstance(foot, str):
        foot = BLUEPRINT[foot][4]
    if isinstance(top, str):
        top = BLUEPRINT[top][5]
    if top is not None and (mode == "rubble" or not (isinstance(top, list) and top and isinstance(top[0], tuple) and len(top) == len(foot) and len(top[0]) == 3)):
        # height samples (the rubble's are always samples): a plane through them
        zf = heights_of(top)
        top = None
    else:
        zf = None
    if mode == "low":
        if top is not None:
            zf = plane_fit(top)
        if not concave:
            foot = hull2d(foot)
        top = None
    step = {"round": 2.0, "slab": 3.2, "rubble": 2.4, "low": 99, "face": FACE_STEP}[mode]
    foot, top = resample(foot, top, step)
    n = len(foot)
    sgn = 1 if signed_area(foot) > 0 else -1
    bis = bisectors(foot)
    if top is None:
        k_of = {"round": lambda z: 0.3 * z + 0.6, "rubble": lambda z: 0.3 * z + 0.3,
                "low": lambda z: 0.22 * z + 0.35, "slab": lambda z: 0.2 * z}[mode]
        top = []
        for i, (c, r) in enumerate(foot):
            (bc, br), cosh, room = bis[i]
            z = zf(c, r)
            k = min(k_of(z) / cosh, 1.8 * k_of(z), 0.42 * room)
            top.append((c + bc * k, r + br * k, z))
    T = list(top)
    F = list(foot)
    zpl = zf if zf is not None else plane_fit(T)
    # (a tall slab's walls are one face from rim to foot: only its foot band darkens at a crevice)
    cw = [crevice_w(f) for f in F]
    pull = [0.0 if mode in ("slab", "face") else w for w in cw]
    # Crevices: the top pulled back from the crevice line and dropped (a deep V with the neighbour).
    for k in range(n):
        if pull[k] > 0:
            (bc, br), cosh, room = bis[k]
            used = math.hypot(T[k][0] - F[k][0], T[k][1] - F[k][1])
            push = min(CREV_PUSH * pull[k], max(0.0, 0.45 * room - used))
            drop = min(2.6, CREV_DROP * T[k][2]) * pull[k]
            T[k] = (T[k][0] + bc * push, T[k][1] + br * push, T[k][2] - drop)
    fcc, fcr = sum(f[0] for f in F) / n, sum(f[1] for f in F) / n

    def away(k):
        dc, dr = F[k][0] - fcc, F[k][1] - fcr
        L = math.hypot(dc, dr) or 1.0
        return -(dc * SUN[0] + dr * SUN[1]) / L

    fiss = [False] * n
    fiss_east = fcc > 42.0
    crease = [False] * n
    if mode == "slab":
        phase = rnd.uniform(0, 2 * math.pi)
        for k in range(n):
            (bc, br), cosh, room = bis[k]
            b = (BATTER + BATTER_AWAY * max(0.0, away(k))) * T[k][2]
            used = math.hypot(T[k][0] - F[k][0], T[k][1] - F[k][1])
            b = max(0.0, min(b, 0.45 * room - used))
            wave = TOP_WAVE * math.sin(2 * math.pi * 2.0 * k / n + phase)
            T[k] = (T[k][0] + bc * b, T[k][1] + br * b, T[k][2] + wave - 0.9 * max(0.0, away(k)))
        for k in range(n):
            d = poly_dist(T[k][:2], FISSURE)
            if d < FISS_R:
                w = 1.0 - d / FISS_R
                (bc, br), cosh, room = bis[k]
                used = math.hypot(T[k][0] - F[k][0], T[k][1] - F[k][1])
                push = min(FISS_PUSH * (1.0 if fiss_east else 1.5) * w, max(0.0, 0.5 * room - used))
                T[k] = (T[k][0] + bc * push, T[k][1] + br * push, T[k][2] - FISS_DROP * w)
                fiss[k] = True
        crease = [math.hypot(F[(k + 1) % n][0] - F[k][0], F[(k + 1) % n][1] - F[k][1]) >= 2.5 and k % 3 == 1 for k in range(n)]
    if mode == "face":
        for k in range(n):
            (bc, br), cosh, room = bis[k]
            dr_ = min(seg_dist(T[k][:2], *e) for e in LIT_EDGES)
            ridge = dr_ < 0.6
            lip = poly_dist(T[k][:2], FISSURE) < 1.8
            aw = max(0.0, away(k))
            # (eased in away from the ridge, so the rim never folds over it at the NW corner)
            ease = max(0.0, min(1.0, (dr_ - 0.6) / 3.0))
            b = 0.0 if (ridge or lip) else (FACE_BATTER + FACE_BATTER_AWAY * aw) * T[k][2] * ease
            if not ridge:
                b += rnd.uniform(0.0, FACE_RIM[0]) * ease
            used = math.hypot(T[k][0] - F[k][0], T[k][1] - F[k][1])
            b = max(0.0, min(b, 0.45 * room - used))
            dz = FACE_SLUMP * aw + (0.0 if ridge else rnd.uniform(0.0, FACE_RIM[1]))
            T[k] = (T[k][0] + bc * b, T[k][1] + br * b, T[k][2] - dz)
    if mode == "rubble":
        T = [(c, r, max(0.6, z + rnd.uniform(-0.4, 0.4))) for c, r, z in T]
    if mode == "low":
        # each low block settles at its own tilt, so neighbouring shelves are not one paved level
        tc, tr = rnd.uniform(-0.16, 0.16), rnd.uniform(-0.1, 0.16)
        T = [(c, r, max(0.6, z + (c - fcc) * tc + (r - fcr) * tr)) for c, r, z in T]
        zpl = plane_fit(T)

    def lerp_ring(xyf, zf_):
        return [(T[k][0] + (F[k][0] - T[k][0]) * xyf, T[k][1] + (F[k][1] - T[k][1]) * xyf, T[k][2] * (1 - zf_)) for k in range(n)]

    round_ = mode == "round"
    rings = [list(T)]
    if round_:
        for xyf, zf_ in ROUND_PROFILE:
            rings.append(lerp_ring(xyf, zf_))
        kinds = ["top", "top", "side", "side", "deep"]
    else:
        R = []
        for k in range(n):
            tc, tr, tz = T[k]
            dc, dr = F[k][0] - tc, F[k][1] - tr
            d = math.hypot(dc, dr) or 1.0
            w = min(ch, 0.6 * d)
            jz = rnd.uniform(-JAG, JAG) * {"slab": 1.0, "face": 0.6}.get(mode, 0.25)
            drop = ch * 1.1
            if fiss[k] and not fiss_east:
                w, drop, jz = min(2.2 * ch, 0.7 * d), ch * 1.1 + 1.4, 0.0
            if mode == "face" and seg_dist((tc, tr), *LIT_EDGES[0]) < 0.6:
                # the lit ridge: a broad, gently falling bevel (the sprite's 2-px 9-b-9 band)
                w, drop, jz = min(RIDGE_W, 0.6 * d), RIDGE_DROP, 0.0
            R.append((tc + dc / d * w, tr + dr / d * w, max(0.4, tz - drop + jz)))

        def shaft(s, inset=0.0, jz=None):
            ring = []
            for k in range(n):
                c = R[k][0] + (F[k][0] - R[k][0]) * s
                r = R[k][1] + (F[k][1] - R[k][1]) * s
                z = R[k][2] * (1 - s) + (jz[k] if jz else 0.0)
                if inset or crease[k]:
                    (bc, br), _, _ = bis[k]
                    q = inset + (CREASE_IN * (1 - 0.6 * s) if crease[k] else 0.0)
                    c += bc * q
                    r += br * q
                ring.append((c, r, z))
            return ring
        rings.append(R)
        kinds = ["chamfer"]
        if mode == "slab":
            zr = min(r[2] for r in R)
            sj = 1 - (min(t[2] for t in T) * 0.48) / zr
            dz = JOINT_HALF / zr
            jz = [rnd.uniform(-1.6 * JAG, 1.6 * JAG) for _ in range(n)]
            rings += [shaft(sj - dz, jz=jz), shaft(sj, JOINT_IN, jz=jz), shaft(sj + dz, jz=jz)]
            kinds += ["side", "groove", "groove", "deep"]
        elif mode == "face":
            # the wall kinks at mid height: steep above, a flared (battered) foot below
            mid = []
            for k in range(n):
                c, r, z = shaft(0.5)[k]
                lean = math.hypot(R[k][0] - F[k][0], R[k][1] - F[k][1])
                (bc, br), _, _ = bis[k]
                q = FACE_KINK * lean * rnd.uniform(0.6, 1.2)
                mid.append((c + bc * q, r + br * q, z + rnd.uniform(-0.6, 0.6)))
            rings.append(mid)
            kinds += ["side", "deep"]
        else:
            rings.append(shaft(0.55))
            kinds += ["side", "deep"]
        rings.append(shaft(1.0))
    V = [[M.v(P(*p)) for p in ring] for ring in rings]
    regions = [(poly, rp) for nm, poly, rp in REGIONS if nm == name]
    rkinds = REGION_KINDS.get(name, ())

    def region_pal(c, r, kind):
        if kind in rkinds or (kind == "deep" and "side" in rkinds):
            for poly, rp in regions:
                if point_in((c, r), poly):
                    return rp
        return None

    def face_slot(k, q, kind, mc):
        """The NE slab's faces as the sprite paints them: the plateau and its rim chamfer at the
        top's index (the ridge chamfer lit), the steep SW face 4 (5 east of col 34.5), the walls
        to the north 6 (the sprite's lit rim), the fissure side a single crevice at 5."""
        if kind == "chamfer":
            return mats(LIT) if any(seg_dist(mc, *e) < 1.4 for e in LIT_EDGES) else mats(pal_top)
        ec, er = F[q][0] - F[k][0], F[q][1] - F[k][1]
        L = math.hypot(ec, er) or 1.0
        oc, orr = sgn * er / L, -sgn * ec / L   # outward normal of the foot edge
        wn, we, ww, sw = FACE_WALLS[name]
        if oc > 0.6:
            return mats(we)
        if oc < -0.6:
            return mats(ww)
        if orr < -0.5:
            return mats(wn)
        return mats(sw[0] if mc[0] < 34.5 else sw[1])

    cc = sum(t[0] for t in T) / n
    cr = sum(t[1] for t in T) / n
    sl_top = mats(pal_top)
    # Top: rings inset step by step (mitred, limited by the room inside, so concave masses stay
    # inside their outline) rising to a dome, closed by a flat cap; no hub fan.
    lift = {"round": [0.45, 0.8, 1.0], "slab": [0.6, 1.0], "rubble": [1.0], "low": [1.0], "face": FACE_LIFT}[mode]
    dome = {"round": DOME_R, "slab": DOME, "rubble": 0.25, "low": 0.15, "face": FACE_CROWN}[mode]
    step = {"round": 1.5, "slab": 1.6, "rubble": 1.0, "low": 0.8, "face": 1.8}[mode]
    prev, prev_v = list(T), V[0]
    inner_all = []
    for li, lf in enumerate(lift):
        prev2 = [(t[0], t[1]) for t in prev]
        b2 = bisectors(prev2)
        ring = []
        for k in range(n):
            (bc, br), cosh, room = b2[k]
            a = min(step / cosh, 0.28 * room)
            c, r = prev[k][0] + bc * a, prev[k][1] + br * a
            if room > 1e8 or not point_in((c, r), prev2):
                # a folded or reflex spot: step towards the ring's centre instead, or stay
                gc, gr = sum(p_[0] for p_ in prev2) / n, sum(p_[1] for p_ in prev2) / n
                dc, dr = gc - prev[k][0], gr - prev[k][1]
                L = math.hypot(dc, dr) or 1.0
                a = min(step * 0.6, 0.25 * L)
                c, r = prev[k][0] + dc / L * a, prev[k][1] + dr / L * a
                if not point_in((c, r), prev2):
                    c, r = prev[k][0], prev[k][1]
            zt = zpl(c, r) + dome * lf
            # blend from the (crevice-dropped, waved) outline towards the smooth dome
            z = prev[k][2] + (zt - prev[k][2]) * (0.6 if li == 0 else 1.0)
            ring.append((c, r, z))
        rv = [M.v(P(*p_)) for p_ in ring]
        inner_all += rv
        for k in range(n):
            q = (k + 1) % n
            rp = region_pal((prev[k][0] + ring[q][0]) / 2, (prev[k][1] + ring[q][1]) / 2, "top")
            a_, b_ = prev_v, rv
            M.f((a_[k], a_[q], b_[q], b_[k]) if sgn > 0 else (a_[k], b_[k], b_[q], a_[q]), mats(rp) if rp else sl_top, round_ or mode == "slab")
        prev, prev_v = ring, rv
    rp = region_pal(cc, cr, "top") if round_ else None
    cap = M.f(list(prev_v) if sgn > 0 else list(reversed(prev_v)), mats(rp) if rp else sl_top, round_ or mode == "slab")
    if cap is not None:
        bmesh.ops.triangulate(M.bm, faces=[cap], quad_method="BEAUTY", ngon_method="BEAUTY")
    for bi, (a, b, kind) in enumerate(zip(V, V[1:], kinds)):
        for k in range(n):
            q = (k + 1) % n
            quad = (a[k], a[q], b[q], b[k]) if sgn > 0 else (a[k], b[k], b[q], a[q])
            ring_a, ring_b = rings[bi], rings[bi + 1]
            mc = ((ring_a[k][0] + ring_a[q][0] + ring_b[k][0] + ring_b[q][0]) / 4,
                  (ring_a[k][1] + ring_a[q][1] + ring_b[k][1] + ring_b[q][1]) / 4)
            w = (cw[k] + cw[q]) / 2
            aw = (away(k) + away(q)) / 2
            if mode == "face":
                M.f(quad, face_slot(k, q, kind, mc), False)
                continue
            if kind in ("chamfer", "top"):
                slot = sl_top
                if kind == "chamfer" and fiss[k] and fiss[q]:
                    slot = mats(LIT) if fiss_east else mats(FISS_PAL)
                elif any(seg_dist(mc, *e) < 1.4 for e in LIT_EDGES) and (kind == "chamfer" or bi == 0):
                    slot = mats(LIT)
                elif w > 0.45 and bi > 0 and mode != "slab":
                    slot = mats(CREV_PAL)
                else:
                    rp = region_pal(mc[0], mc[1], "top")
                    if rp:
                        slot = mats(rp)
                    elif kind == "top" and bi > 0 and aw > 0.5:
                        slot = mats(max(3, pal_top - 1))
            else:
                p_ = pal if aw < 0.3 else max(3, pal - 1)
                # a gentle slope (seen from above, as the sprite sees it) takes the top's index
                ux, uy, uz = (ring_a[q][0] - ring_a[k][0], ring_a[q][1] - ring_a[k][1], ring_a[q][2] - ring_a[k][2])
                vx, vy, vz = (ring_b[k][0] - ring_a[k][0], ring_b[k][1] - ring_a[k][1], ring_b[k][2] - ring_a[k][2])
                nx_, ny_, nz_ = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
                nl = math.sqrt(nx_ * nx_ + ny_ * ny_ + nz_ * nz_) or 1.0
                if abs(nz_) / nl > (0.35 if mode == "slab" else 0.6) and kind != "deep":
                    p_ = max(p_, pal_top - 1)
                if kind == "deep":
                    p_ = max(CREV_PAL, p_ - 1)
                rp = region_pal(mc[0], mc[1], kind)
                if rp and aw < 0.6:
                    p_ = rp
                if w > 0.3 and (mode != "slab" or kind == "deep"):
                    p_ = CREV_DEEP if (kind == "deep" or w > 0.55) else CREV_PAL
                if bi == 1 and fiss[k] and fiss[q] and not fiss_east:
                    p_ = FISS_PAL
                slot = mats(p_)
            M.f(quad, slot, round_)
    M.f(list(reversed(V[-1])) if sgn > 0 else list(V[-1]), mats(3))
    bmesh.ops.remove_doubles(M.bm, verts=[v for ring in V for v in ring] + inner_all, dist=1e-5)
    if round_ or mode == "rubble":
        # relax the crown and shoulder (the foot ring stays put, so the silhouette is the sprite's)
        soft = [v for v in inner_all + V[0] + V[1] if v.is_valid]
        for _ in range(8):
            bmesh.ops.smooth_vert(M.bm, verts=soft, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)


# Splinters standing out of the rubble (the sprite's grey streaks in the dark south-east): wedge
# hulls with a sharp ridge, leaning out of the heap. foot [(c, r)] at z 0, ridge [(c, r, z)], pal.
BLADES = [
    ([(47.4, 29.2), (49.9, 29.3), (50.8, 30.6), (50.4, 34.2), (48.2, 34.6), (47.95, 31.0)], [(48.2, 29.9, 4.6), (49.8, 30.4, 4.2), (48.9, 33.6, 2.8)], 5),
    ([(52.4, 23.0), (57.4, 22.4), (56.2, 26.4), (52.8, 27.0)], [(53.6, 23.4, 4.4), (56.4, 23.2, 4.0), (55.0, 25.0, 3.6)], 4),
    ([(44.05, 30.9), (45.9, 31.0), (45.7, 33.1), (44.05, 33.1)], [(44.8, 31.6, 4.0), (45.0, 32.6, 3.7)], 4),
    ([(43.05, 32.95), (45.0, 33.0), (44.95, 34.95), (43.05, 35.0)], [(44.0, 33.6, 3.4), (44.2, 34.4, 3.1)], 4),
    ([(43.05, 34.9), (43.95, 34.9), (43.9, 38.9), (43.1, 38.9)], [(43.5, 35.6, 2.8), (43.5, 38.0, 1.8)], 4),
    ([(55.6, 27.6), (59.6, 25.6), (58.0, 30.0), (56.0, 30.6)], [(57.0, 27.4, 3.4), (58.6, 26.6, 3.2)], 4),
    ([(49.2, 35.0), (51.6, 34.4), (51.5, 36.9), (48.4, 39.9), (48.3, 38.0)], [(50.0, 35.2, 2.8), (50.6, 36.6, 2.4)], 4),
]


def blades(M, mats):
    for foot, ridge, pal in BLADES:
        verts = [M.v(P(c, r, 0.0)) for c, r in foot] + [M.v(P(*p)) for p in ridge]
        before = set(M.bm.faces)
        hull = bmesh.ops.convex_hull(M.bm, input=verts)
        junk = list({v for v in hull["geom_unused"] + hull["geom_interior"] if isinstance(v, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(M.bm, geom=junk, context="VERTS")
        new = [f for f in M.bm.faces if f not in before]
        bmesh.ops.recalc_face_normals(M.bm, faces=new)
        for f in new:
            f.normal_update()
            no = f.normal
            # the up / sun-facing faces take the blade's index, the shaded ones darker
            lit = no.z > 0.5 or (no.x * SUN[0] - no.y * SUN[1]) > 0.3
            f.material_index = mats(pal if lit else max(3, pal - 1))
            f.smooth = False


def scree(M, mats):
    """Loose chunks in the crevices at the feet (inside the sprite mask, in its dark pixels)."""
    import random
    rnd = random.Random(39)
    spots = [(21.5, 34.5, 1.4, 3), (30.5, 34.6, 1.2, 4),
             (40.2, 35.9, 1.0, 4), (44.0, 33.9, 0.9, 3), (50.6, 35.6, 0.9, 3), (56.0, 30.8, 1.1, 4),
             (58.8, 28.3, 1.0, 3), (24.6, 25.0, 1.0, 4), (44.4, 26.8, 0.9, 3),
             (60.4, 24.6, 0.9, 4)]
    for c, r, s, pal in spots:
        pts = []
        for _ in range(9):
            a = rnd.uniform(0, 2 * math.pi)
            rad = s * rnd.uniform(0.6, 1.0)
            pts.append(P(c + rad * math.cos(a), r + rad * 0.8 * math.sin(a), rnd.uniform(0.0, 0.2)))
        for _ in range(4):
            a = rnd.uniform(0, 2 * math.pi)
            rad = s * rnd.uniform(0.2, 0.55)
            pts.append(P(c + rad * math.cos(a), r + rad * math.sin(a), s * rnd.uniform(0.7, 1.15)))
        verts = [M.v(p) for p in pts]
        before = set(M.bm.faces)
        hull = bmesh.ops.convex_hull(M.bm, input=verts)
        junk = list({v for v in hull["geom_unused"] + hull["geom_interior"] if isinstance(v, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(M.bm, geom=junk, context="VERTS")
        new = [f for f in M.bm.faces if f not in before]
        bmesh.ops.recalc_face_normals(M.bm, faces=new)
        for f in new:
            f.material_index = mats(pal)
            f.smooth = False


def build(colors):
    coll = common.reset_collection(NAME)
    mats = lib.Mats("nshe39", colors)
    rock = lambda i: mats(i, metallic=0.05, roughness=0.78)  # noqa: E731
    M = Mesh()
    import random
    rnd = random.Random(39)
    for spec in MASSES:
        mass(M, rock, *spec, rnd)
    scree(M, rock)
    blades(M, rock)
    bm = M.bm
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats.list:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj, mats


def top_mask(obj, out_json):
    """Top-view coverage of the rocks (no ground) in assembly px, rasterised from the triangles:
    written as triangles in (col, row) for the measuring script."""
    tris = []
    me = obj.data
    me.calc_loop_triangles()
    for t in me.loop_triangles:
        pts = [me.vertices[i].co for i in t.vertices]
        tris.append([(p.x / U + 36, 28 - p.y / U, p.z / U) for p in pts])
    Path(out_json).write_text(json.dumps(tris))


def split_open(obj, layout, coll):
    """common.split_assembly without filling the cuts, for the outline shells: a capped cut would
    stroke an ink line along every seam between two pieces."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        s = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(s)
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        out[name] = s
    return out


NEUTRAL_UV = None  # set by bake_maps: a texel of the colour map kept at a plain multiplier


def cap_uvs(piece):
    """Point the cut caps (faces split_assembly filled, lying on the piece's box) at the plain
    texel, so a cap seen when a neighbour is destroyed is plain rock in its palette colour."""
    me = piece.data
    if NEUTRAL_UV is None or "bake" not in me.uv_layers:
        return
    uv = me.uv_layers["bake"].data
    hx, hy = 1.0, 14 / 12
    n = 0
    for f in me.polygons:
        xs = [me.vertices[i].co for i in f.vertices]
        if (all(abs(abs(v.x) - hx) < 1e-4 for v in xs) and len({round(v.x, 4) for v in xs}) == 1) or \
                (all(abs(abs(v.y) - hy) < 1e-4 for v in xs) and len({round(v.y, 4) for v in xs}) == 1):
            for li in f.loop_indices:
                uv[li].uv = NEUTRAL_UV
            n += 1
    return n


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import tempfile
    first = common.load_sprite(ROOT, PIECES[0])
    layout = [(e["model"], e["cx"], e["cy"]) for e in first["assemblyLayout"]]
    corners = [(n, cx - 12 - SX0, cy - 14 - SY0) for n, cx, cy in layout]
    pixels, w, h, colors = lib.assembly_pixels(ROOT, corners)
    obj, mats = build(colors)
    coll = obj.users_collection[0]
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"rock triangles {tris}")
    if "--top-tris" in argv:
        top_mask(obj, argv[argv.index("--top-tris") + 1])
    # Baked occlusion and edge wear only, as a multiplier over the palette colours (the ships' bake,
    # PR #84); no concept projection: maps.json says "bake": "model", so texture_bake.py skips it.
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, mats, Path(tempfile.mkdtemp(prefix="nshe39_bake_")))
        fmt = "WEBP"
    # The ink outline (D51) from a smooth closed copy of the rock (not the ground patch); made after
    # the bake so it never occludes the bake's rays.
    shell = common.outline_shell(obj, coll, voxel=0.02, faces=3000, smooth=6)
    rel = [(n, cx - CX0, cy - CY0) for n, cx, cy in layout]
    pieces = common.split_assembly(obj, rel)
    shells = split_open(shell, rel, coll)
    for p in pieces.values():
        cap_uvs(p)
    total = 0
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        p = pieces[name]
        n = sum(len(q.vertices) - 2 for q in p.data.polygons)
        total += n
        print(f"{name}: {len(p.data.polygons)} faces, {n} triangles")
        common.export_sprite_model(ROOT, [p, shells[name]], f"enemies/{name}", data["sprites"], image_format=fmt)
    print(f"total triangles {total}")
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        ref = lib.pixels_png(pixels, colors, Path(tempfile.mkdtemp()) / "assembly.png", pad_to=(72, 84))
        whole = []
        for name, ox, oy in corners:
            p = pieces[name]
            p.location = ((ox + 12 - w / 2) / 12, (h / 2 - oy - 14) / 12, 0)
            whole.append(p)
        bpy.context.view_layer.update()
        common.render_preview(whole, str(out), ref, size=6, view_px=640)
        for p in whole:
            p.location = (0, 0, 0)
    if "--render" in argv:
        for name, cx, cy in layout:
            pieces[name].location = ((cx - CX0) * U, -(cy - CY0) * U, 0)
        for o in bpy.data.objects:
            if o.type == "MESH" and o not in pieces.values():
                o.hide_render = True
        bpy.context.view_layer.update()
        render_views([pieces[n] for n in PIECES], Path(argv[argv.index("--render") + 1]))


# --- texture: baked occlusion and edge wear only (no concept projection) -------------------------

def bake_maps(obj, mats, out_dir, size=1024, samples=64):
    """As usp_talon.bake_maps: UV the rock, bake a grey colour multiplier (occlusion at two scales:
    the joints and crevices darken, plus a slight lift on the chamfered edges) and a
    roughness/metalness map, with a temporary ground plane as occluder; then wire them into the
    rock's palette materials (Base Color = map x palette colour). The ground stays untextured."""
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:  # noqa: BLE001
        print("no GPU bake", err)
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0.02 * U * 12 / 12))
    plane = bpy.context.active_object
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(50), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new("nshe39_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("nshe39_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mlist = list(me.materials)
    saved = {}
    for m in mlist:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        L = nt.links.new
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    L(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.06
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.35
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.012
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 6.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.9),
                     math_("ADD", 0.55, math_("MULTIPLY", ao_l.outputs["AO"], 0.45)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.42, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.14)), 1.0)
            # Base darkening: an uneven gradient over the lowest 1.2-3 px (earth stain and damp at
            # the foot), so the rocks part at the base without a level painted band.
            noise = node("ShaderNodeTexNoise")
            noise.inputs["Scale"].default_value = 5.0
            noise.inputs["Detail"].default_value = 3.0
            L(geo.outputs["Position"], noise.inputs["Vector"])
            hgt = math_("MULTIPLY", math_("ADD", 1.2, math_("MULTIPLY",
                        math_("MAXIMUM", math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", noise.outputs["Fac"], 0.3), 2.5), 1.0), 0.0), 1.8)), U)
            sep = node("ShaderNodeSeparateXYZ")
            L(geo.outputs["Position"], sep.inputs[0])
            g = math_("MAXIMUM", math_("MINIMUM", math_("DIVIDE", sep.outputs["Z"], hgt), 1.0), 0.0)
            v = math_("MULTIPLY", v, math_("ADD", 0.66, math_("MULTIPLY", g, 0.34)))
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                L(v, comb.inputs[k])
            L(comb.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.2),
                                          math_("MULTIPLY", edge, 0.15)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mlist}
        bpy.ops.object.bake(type="EMIT", margin=8, use_clear=True)
        for m in mlist:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(out_dir / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
    bpy.data.objects.remove(plane, do_unlink=True)
    # A 2 x 2 texel corner (outside the packed islands' margin) kept at a plain multiplier for the
    # cut caps (cap_uvs).
    global NEUTRAL_UV
    for img, val in ((col_img, (0.9, 0.9, 0.9, 1.0)), (rm_img, (1.0, 0.85, 0.05, 1.0))):
        px = list(img.pixels)
        iw = img.size[0]
        for y in range(2):
            for x in range(2):
                px[(y * iw + x) * 4:(y * iw + x) * 4 + 4] = val
        img.pixels[:] = px
        img.pack()
    NEUTRAL_UV = (1.0 / col_img.size[0], 1.0 / col_img.size[1])
    for m in mlist:
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


# --- renders -------------------------------------------------------------------------------------

def render_views(objs, out_dir, px=520):
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x = scene.render.resolution_y = px
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.28, 0.32, 0.42, 1)
    bg.inputs[1].default_value = 0.55
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4.0
    scene.collection.objects.link(sun)
    # three.js sun at (-6, 20, 8.4) (y up, +z towards the screen bottom) -> Blender (-6, -8.4, 20)
    sun.rotation_euler = Vector((-6, -8.4, 20)).to_track_quat("Z", "Y").to_euler()
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    D = 12.0

    def shot(name, direction, ortho=7.0, up="Z"):
        d = Vector(direction).normalized()
        cam.location = d * D
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        if d.z > 0.999:
            cam.rotation_euler = (0, 0, 0)
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho
        scene.render.filepath = str(out_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    t = math.radians(32)
    shot("top", (0, -0.0001, 1), ortho=6.6)  # rotation fixed in shot()
    shot("game", (0, -math.sin(t), math.cos(t)), ortho=6.6, up="Y")
    shot("front", (0, -1, 0.0001))
    shot("rear", (0, 1, 0.0001))
    shot("left", (-1, 0, 0.0001))
    shot("right", (1, 0, 0.0001))
    shot("q34_fl", (-0.6, -0.7, 0.65))
    shot("q34_rr", (0.65, 0.6, 0.6))
    shot("under", (0.2, -0.3, -1))


# --- the shot-away state (frames 7, 9, 11, 45, 47, 49) -------------------------------------------
#
# Each piece, shot hard enough, turns into its damaged enemy (types 522-527), drawn with the frame
# six after its own: the rock is gone and a crater shows a pool of blue beneath, ringed by a dark
# scorch with loose stones and a few broken shards on its south side. Those frames are not in the
# catalogue (only an enemy's own frames are), so they are read from the game data here (newshe.shp,
# palette 5); nothing of it is written to the repo but the models.
#
# Built like D63's island rock: the sprite's pixels are smoothed into fields and cut along their
# iso-lines, so the crater's and the pool's edges and the pool's colour bands are smooth curves at
# any resolution, still in the sprite's palette indices:
#   - no ground patch: the sprite's dirt round the crater is not modelled (as on the undamaged pieces,
#     D86); the game's HD ground shows there;
#   - the scorch: a thin slab cut from the blurred mask of the crater's dark pixels (index 32 and the
#     brown-black 160-163), and the lone dark specks as small round flecks;
#   - the pool: a slab cut from the blurred mask of the blue and its dark rim (80-83), its top split
#     into isobands of the bilinear sprite (the blue ramp 144-159 is ordered dark to bright), glossy and
#     glowing a little; the bright spots are its sheen, kept as colour, not relief;
#   - the stones: each 4-connected group of grey pixels (2-11) is a convex stone on its own pixels,
#     taller the bigger it is (the south shards up to ~4 px), lit faces in its brightest index;
# and an ink outline shell of the stones and pool (D51). No bake: plain palette materials.

DAMAGED = {"newshe-1": 7, "newshe-3": 9, "newshe-5": 11, "newshe-39": 45, "newshe-41": 47, "newshe-43": 49}
BLUE = set(range(144, 160))
BLUE_RIM = {80, 81, 82, 83}
SCORCH = {32, 160, 161, 162, 163}
GREY = set(range(2, 12))
Z_SCORCH, Z_POOL = 0.36, 0.62   # px above the ground


def data_file(name):
    import os
    for d in (os.environ.get("TYRIAN_DATA"), ROOT / "data"):
        if d and (Path(d) / name).exists():
            return Path(d) / name
    raise FileNotFoundError(f"{name}: set TYRIAN_DATA to the Tyrian 2.1 data")


def sprite2(sheet, index):
    """src/data/sprites.ts decodeSprite2: Sprite2 #index (1-based) as rows of 12 (-1 transparent)."""
    rows, row = [], [-1] * 12
    p = sheet[(index - 1) * 2] | (sheet[(index - 1) * 2 + 1] << 8)
    x = 0
    while p < len(sheet) and sheet[p] != 0x0F:
        x += sheet[p] & 0x0F
        n = sheet[p] >> 4
        if n == 0:
            rows.append(row)
            row, x = [-1] * 12, 0
        else:
            for _ in range(n):
                p += 1
                if x < 12:
                    row[x] = sheet[p]
                x += 1
        p += 1
    if any(v >= 0 for v in row):
        rows.append(row)
    return rows


def damaged_pixels(corners):
    """The damaged frames on the assembly grid (as lib.assembly_pixels) and palette 5's colours."""
    sheet = data_file("newshe.shp").read_bytes()
    pal = data_file("palette.dat").read_bytes()[5 * 768:6 * 768]
    w, h = 72, 56
    pixels = [[-1] * w for _ in range(h)]
    for name, c0, r0 in corners:
        f = DAMAGED[name]
        for (dc, dr), off in (((0, 0), 0), ((12, 0), 1), ((0, 14), 19), ((12, 14), 20)):
            for r, row in enumerate(sprite2(sheet, f + off)[:14]):
                for c, v in enumerate(row):
                    pixels[r0 + dr + r][c0 + dc + c] = v
    used = {v for row in pixels for v in row if v >= 0}
    eight = lambda v: (v << 2) | (v >> 4)  # noqa: E731
    colors = {str(i): [eight(pal[i * 3]), eight(pal[i * 3 + 1]), eight(pal[i * 3 + 2])] for i in used | {17}}
    return pixels, w, h, colors


def blurred(pixels, keep, sigma):
    import numpy as np
    m = np.array([[1.0 if v in keep else 0.0 for v in row] for row in pixels])
    r = int(math.ceil(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    m = np.apply_along_axis(lambda a: np.convolve(np.pad(a, r, mode="edge"), k, mode="valid"), 0, m)
    m = np.apply_along_axis(lambda a: np.convolve(np.pad(a, r, mode="edge"), k, mode="valid"), 1, m)
    return m


def bilinear(field, c, r):
    """field sampled at pixel centres; (c, r) in pixel-edge coordinates."""
    h, w = field.shape
    x, y = min(max(c - 0.5, 0), w - 1), min(max(r - 0.5, 0), h - 1)
    x0, y0 = min(int(x), w - 2), min(int(y), h - 2)
    fx, fy = x - x0, y - y0
    return ((1 - fx) * (1 - fy) * field[y0, x0] + fx * (1 - fy) * field[y0, x0 + 1]
            + (1 - fx) * fy * field[y0 + 1, x0] + fx * fy * field[y0 + 1, x0 + 1])


def clip(poly, keep_above, t):
    """Sutherland-Hodgman against a level of the field: poly is [(c, r, value)], values linear
    along the edges; keeps value >= t (keep_above) or value < t."""
    inside = (lambda v: v >= t) if keep_above else (lambda v: v < t)
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        if inside(a[2]):
            out.append(a)
        if inside(a[2]) != inside(b[2]):
            f = (t - a[2]) / (b[2] - a[2])
            out.append((a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]), t))
    return out


def iso_cells(mask, value, t, bands, c0, r0, c1, r1, step):
    """Cells of `step` px over [c0, c1) x [r0, r1), clipped to mask >= t, then split by `value` into
    bands [(lo, hi, tag)]. Yields (tag, [(c, r)])."""
    n = 0
    r = r0
    while r < r1 - 1e-9:
        c = c0
        while c < c1 - 1e-9:
            sq = [(c, r), (c + step, r), (c + step, r + step), (c, r + step)]
            mv = [bilinear(mask, *q) for q in sq]
            if max(mv) >= t:
                poly = [(q[0], q[1], m) for q, m in zip(sq, mv)]
                if min(mv) < t:
                    poly = clip(poly, True, t)
                if len(poly) >= 3:
                    if value is None:
                        yield bands[0][2], [(q[0], q[1]) for q in poly]
                    else:
                        vp = [(q[0], q[1], bilinear(value, q[0], q[1])) for q in poly]
                        for lo, hi, tag in bands:
                            b = clip(clip(vp, True, lo), False, hi) if lo is not None else clip(vp, False, hi)
                            if len(b) >= 3:
                                yield tag, [(q[0], q[1]) for q in b]
            c += step
        r += step


def slab(M, cells, z, wall_slot, tidy=True):
    """A closed slab from z = 0 to z (px) whose top is the given cells [(slot, [(c, r)])]: the top
    welded and flat faces of one slot merged, walls down its outline, a flat bottom."""
    bm = bmesh.new()
    for slot, poly in cells:
        vs = [bm.verts.new(P(c, r, z)) for c, r in poly]
        try:
            f = bm.faces.new(vs)
            f.material_index = slot
        except ValueError:
            pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.faces.ensure_lookup_table()
    for f in [f for f in bm.faces if f.calc_area() < 1e-9]:
        bm.faces.remove(f)
    if tidy:
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=bm.verts[:], edges=bm.edges[:],
                                 delimit={"MATERIAL"})
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < 0:
            f.normal_flip()
    # walls: extrude the boundary down to the foot, then cap
    edges = [e for e in bm.edges if e.is_boundary]
    ext = bmesh.ops.extrude_edge_only(bm, edges=edges)
    low = [v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)]
    for v in low:
        v.co.z = 0.0
    for f in [f for f in ext["geom"] if isinstance(f, bmesh.types.BMFace)]:
        f.material_index = wall_slot
    bottom = [e for e in bm.edges if e.is_boundary]
    if bottom:
        filled = bmesh.ops.holes_fill(bm, edges=bottom, sides=0)
        for f in filled["faces"]:
            f.material_index = wall_slot
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("slab")
    bm.to_mesh(me)
    bm.free()
    M.bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def stones(M, pixels, mats, rnd):
    """Each 4-connected group of grey pixels a convex stone on its own pixels."""
    h, w = len(pixels), len(pixels[0])
    seen = set()
    for r0 in range(h):
        for c0 in range(w):
            if (r0, c0) in seen or pixels[r0][c0] not in GREY:
                continue
            comp, todo = [], [(r0, c0)]
            seen.add((r0, c0))
            while todo:
                r, c = todo.pop()
                comp.append((r, c))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    q = (r + dr, c + dc)
                    if 0 <= q[0] < h and 0 <= q[1] < w and q not in seen and pixels[q[0]][q[1]] in GREY:
                        seen.add(q)
                        todo.append(q)
            vals = sorted(pixels[r][c] for r, c in comp)
            n, top_i = len(comp), vals[-1]
            lit_i = vals[len(vals) * 3 // 4]
            ht = min(4.6, 0.55 + 0.42 * math.sqrt(n)) * (1.0 if top_i >= 4 else 0.55)
            cx = sum(c for r, c in comp) / n + 0.5
            cy = sum(r for r, c in comp) / n + 0.5
            foot, top = [], []
            for r, c in comp:
                for dc, dr in ((0.12, 0.12), (0.88, 0.12), (0.88, 0.88), (0.12, 0.88)):
                    foot.append((c + dc + rnd.uniform(-0.1, 0.1), r + dr + rnd.uniform(-0.1, 0.1)))
            bright = [(r, c) for r, c in comp if pixels[r][c] >= lit_i] or comp
            for r, c in bright:
                # the crown: brighter pixels high, drawn in towards the stone's centre
                k = 0.35 if n > 2 else 0.6
                tc, tr = c + 0.5 + (cx - c - 0.5) * k, r + 0.5 + (cy - r - 0.5) * k
                top.append((tc + rnd.uniform(-0.15, 0.15), tr + rnd.uniform(-0.15, 0.15),
                            ht * rnd.uniform(0.7, 1.0)))
            if n <= 2:
                top.append((cx, cy, ht))
            verts = [M.v(P(c, r, Z_SCORCH * 0.5)) for c, r in foot] + [M.v(P(*t)) for t in top]
            before = set(M.bm.faces)
            hull = bmesh.ops.convex_hull(M.bm, input=verts)
            junk = list({v for v in hull["geom_unused"] + hull["geom_interior"] if isinstance(v, bmesh.types.BMVert)})
            if junk:
                bmesh.ops.delete(M.bm, geom=junk, context="VERTS")
            new = [f for f in M.bm.faces if f not in before]
            bmesh.ops.recalc_face_normals(M.bm, faces=new)
            for f in new:
                f.normal_update()
                no = f.normal
                sun = no.x * SUN[0] - no.y * SUN[1]
                if no.z < -0.5:
                    i = 2
                elif no.z > 0.75:
                    i = lit_i
                elif sun > 0.2:
                    i = top_i
                else:
                    i = max(2, vals[0] if n > 2 else lit_i - 2)
                f.material_index = mats(i)
                f.smooth = False


def flecks(M, pixels, scorch_mask, slot):
    """Lone dark pixels outside the scorch: small round flecks instead of square pixels."""
    for r, row in enumerate(pixels):
        for c, v in enumerate(row):
            if v not in SCORCH or bilinear(scorch_mask, c + 0.5, r + 0.5) >= 0.5:
                continue
            ring = [(c + 0.5 + 0.55 * math.cos(a * math.pi / 4), r + 0.5 + 0.55 * math.sin(a * math.pi / 4))
                    for a in range(8)]
            slab(M, [(slot, ring)], Z_SCORCH, slot, tidy=False)


def build_damaged(pixels, colors):
    import random
    import numpy as np
    coll = common.reset_collection(NAME + "-damaged")
    mats = lib.Mats("nshe39d", colors)
    rock = lambda i: mats(i, metallic=0.05, roughness=0.78)  # noqa: E731
    M = Mesh()
    w, h = len(pixels[0]), len(pixels)
    # scorch
    scorch = blurred(pixels, SCORCH | GREY | BLUE | BLUE_RIM, 0.9)
    s32 = mats(32, metallic=0.0, roughness=0.95)
    slab(M, [(s32, poly) for _, poly in iso_cells(scorch, None, 0.5, [(None, None, 0)], 0, 0, w, h, 1.0)],
         Z_SCORCH, s32)
    flecks(M, pixels, scorch, s32)
    # pool: value = the blue ramp (rim and outside one below the darkest blue)
    pool = blurred(pixels, BLUE | BLUE_RIM, 0.8)
    val = np.array([[float(v) if v in BLUE else 143.0 for v in row] for row in pixels])
    val = 0.65 * val + 0.35 * blurred_values(val, 0.7)
    used = sorted({v for row in pixels for v in row if v in BLUE})
    # every other index of the ramp (the brightest kept): half the materials, so half the draw calls
    used = sorted(set(used[::-2]))

    def pool_mat(i):
        if i == 82:
            return mats(82, metallic=0.2, roughness=0.3)
        glow = 0.1 + 0.5 * max(0, i - 147) / 12
        return mats(i, metallic=0.2, roughness=0.3, emission_strength=round(glow, 2))
    bands = [(None, used[0] - 0.5, pool_mat(82))]
    for k, i in enumerate(used):
        hi = used[k + 1] - 0.5 if k + 1 < len(used) else None
        bands.append((i - 0.5, hi if hi is not None else 999.0, pool_mat(i)))
    cells = list(iso_cells(pool, val, 0.45, bands, 0, 10, w, 36, 0.5))
    slab(M, cells, Z_POOL, pool_mat(82))
    stones(M, pixels, rock, random.Random(45))
    bm = M.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    mesh = bpy.data.meshes.new(NAME + "-damaged")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats.list:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME + "-damaged", mesh)
    coll.objects.link(obj)
    return obj, mats


def blurred_values(val, sigma):
    import numpy as np
    r = int(math.ceil(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    m = np.apply_along_axis(lambda a: np.convolve(np.pad(a, r, mode="edge"), k, mode="valid"), 0, val)
    return np.apply_along_axis(lambda a: np.convolve(np.pad(a, r, mode="edge"), k, mode="valid"), 1, m)


def main_damaged(argv):
    """Build and export the damaged pieces, <piece>-f2 (one model per damaged frame)."""
    import tempfile
    first = common.load_sprite(ROOT, PIECES[0])
    layout = [(e["model"], e["cx"], e["cy"]) for e in first["assemblyLayout"]]
    corners = [(n, cx - 12 - SX0, cy - 14 - SY0) for n, cx, cy in layout]
    pixels, w, h, colors = damaged_pixels(corners)
    obj, mats = build_damaged(pixels, colors)
    coll = obj.users_collection[0]
    print(f"damaged triangles {sum(len(p.vertices) - 2 for p in obj.data.polygons)}")
    # the outline from the stones and the pool only (not the scorch, which is ground)
    raised = obj.copy()
    raised.data = obj.data.copy()
    coll.objects.link(raised)
    bm = bmesh.new()
    bm.from_mesh(raised.data)
    flat = mats.slots[32]
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == flat], context="FACES")
    bm.to_mesh(raised.data)
    bm.free()
    shell = common.outline_shell(raised, coll, voxel=0.02, faces=2500, smooth=4)
    bpy.data.objects.remove(raised)
    rel = [(n, cx - CX0, cy - CY0) for n, cx, cy in layout]
    pieces = common.split_assembly(obj, rel)
    shells = split_open(shell, rel, coll)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        p = pieces[name]
        sprites = [{**s, "frames": [DAMAGED[name]]} for s in data["sprites"]]
        print(f"{name}-f2: {len(p.data.polygons)} faces")
        common.export_sprite_model(ROOT, [p, shells[name]], f"enemies/{name}-f2", sprites)
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        ref = lib.pixels_png(pixels, colors, Path(tempfile.mkdtemp()) / "assembly.png", pad_to=(72, 84))
        whole = []
        for name, ox, oy in corners:
            p = pieces[name]
            p.location = ((ox + 12 - w / 2) / 12, (h / 2 - oy - 14) / 12, 0)
            whole.append(p)
        bpy.context.view_layer.update()
        common.render_preview(whole, str(out), ref, size=6, view_px=640)
        for p in whole:
            p.location = (0, 0, 0)
    if "--render" in argv:
        for name, cx, cy in layout:
            pieces[name].location = ((cx - CX0) * U, -(cy - CY0) * U, 0)
        for o in bpy.data.objects:
            if o.type == "MESH" and o not in pieces.values():
                o.hide_render = True
        bpy.context.view_layer.update()
        render_views([pieces[n] for n in PIECES], Path(argv[argv.index("--render") + 1]))


if __name__ == "__main__":
    _argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--damaged" in _argv:
        main_damaged(_argv)
    else:
        main()
