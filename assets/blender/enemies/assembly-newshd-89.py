"""Big rock heap (newshd.shp 13, 49, 51, 53, 89, 91: an assembly of 6 pieces): a 3D version of its sprites.

Seen in level 1.1. Six 2x2 ground enemies make one 72 x 84 px heap of grey, faceted boulders with
its corners missing, lit from the upper left like the rock heap above it (assembly-newshd-39), whose
D116 construction (D65 standard, D50-D53) this follows. Design B (silhouette first) with the judge's
grafts.

Big, clearly separate boulders with deep V cracks between them, each a chunky solid of a few dozen
PLANAR fracture faces (a convex hull of its sections, chamfered), never a lumpy blob, and a
footprint that is the sprite's outline.

Construction:
  1. The sprite's inner mask (tools/sprite_mask.py, D74: the ink ring is the game's outline) is cut
     into 24 cells (PARTS: the blueprint's 22 with the lower lobe split into rock and toe;
     footprints from the blueprint, leftover pixels to the nearest peak). Each cell grows GROW px
     into its neighbours, so neighbouring boulders interpenetrate and meet in V cracks low down.
  2. Each boulder: its foot polygon (pixel outline through the pixel-edge midpoints: no staircase)
     at z 0, then sections stepped in towards the crown along a pchip profile per kind, jittered;
     the convex hull gives planar fracture faces; coplanar triangles merge; every edge gets a
     small chamfer. Kinds: dome / ridge / flat / crater as in PARTS. The crater ("dome") is 10.6 px
     high, like newshd-39's, and stays the highest lit mass as in the sprite.
  3. Each boulder is intersected with the outline clip: the union's top view is the sprite's inner
     mask row by row. The clip is vertical for 0.5 px, then leans in along CLIP_PROFILE (5 px at
     16 px up; leaning more than -39 because this heap's narrow arms must not stand as towers in the
     tilted view), so the outer flanks slope (no cliff walls). The V cracks are the only dark lines.
  4. Palette: each boulder takes the median of its cell's sprite pixels between the 15th and 85th
     luminance percentile (ink, deepest shading and brightest glints are lighting). DEVIATIONS from
     the blueprint's guess (shown as "pal (blueprint)" in PARTS): topright 7 (8), topleft 8 (9),
     crevice 7 (6), rightrock 6 (7), lowright 4 (5), bottomtoe 4 (5); the sprite's own pixels win.
     Rock: metallic 0, roughness 0.85. AO/edge colour multiplier + roughness bake per piece, no
     concept projection (--no-bake to skip).
  5. Outline shell (D51) of the whole heap cut open at the piece boxes, then common.split_assembly
     cuts newshd-13 / -49 / -51 / -53 / -89 / -91, one frame each.
  6. Underside (D122 audit: the heap floats in space, no flat base): one closed body under the
     boulders, D125's asteroid underside (lib_newshd_rock rock_body): the outline clip's foot is the
     waist, rings below it close in on the mask's centroid along a superellipse (UNDER_POW, full
     shoulders) to a pole UNDER_H px down, a few planar fracture cuts (lib_newshd_rock.cut_planes),
     each face the colour of the boulder above it. The whole heap is then sheared vertically by a
     low noise (WARP_PX; x and y untouched, so the top view is exact) so the waist never reads as a
     flat belt. Plain shape only, no detail.

Run: blender -b --factory-startup --python assets/blender/enemies/assembly-newshd-89.py -- [--no-bake]
     [--no-export] [--design-out whole.glb] [--render DIR]
"""

import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, noise

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
WT = ROOT
sys.path.insert(0, str(ROOT / "tools"))
import sprite_mask as SM  # noqa: E402
import usp_talon as T  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newshd_rock as ROCK  # noqa: E402
PARTS = [
    {"name": "peak", "pal": 8, "h": 11.5, "kind": "ridge", "peak": [-1.11, 30.2], "footprint": [[7, 31.5], [6.75, 34.25], [6.5, 37], [4.5, 37], [3.5, 38], [1.17, 38], [-1.17, 38], [-3.5, 38], [-5, 36.5], [-6.5, 35], [-8, 33.5], [-8.5, 32], [-9, 30.5], [-7.75, 29.25], [-6.5, 28], [-5.5, 28], [-4.5, 26], [-1.5, 26], [-0.5, 27], [2.5, 27], [4, 28.5], [5.5, 30]], "crest": [[-2.5, 33.5], [0, 25.5]]},  # pal 8 (blueprint 8)
    {"name": "topright", "pal": 8, "h": 7.6, "kind": "flat", "peak": [8.39, 25.43], "footprint": [[12, 18.5], [12, 21.17], [12, 23.83], [12, 26.5], [12, 29.17], [12, 31.83], [12, 34.5], [10.5, 36], [7.5, 36], [7.25, 33.75], [7, 31.5], [5, 29.5], [3, 27.5], [4, 26.5], [4, 23.5], [5, 22.5], [4, 21.5], [4, 19.5], [6.5, 19], [7.5, 20], [8.5, 19], [10.5, 19], [11.5, 18]]},  # pal 7 (blueprint 8)
    {"name": "topleft", "pal": 9, "h": 8.4, "kind": "dome", "peak": [-7.66, 22.78], "footprint": [[-4, 20.5], [-4, 23], [-4, 25.5], [-5, 27.5], [-7.25, 29.25], [-9.5, 31], [-10.75, 29.25], [-12, 27.5], [-12, 24.75], [-12, 22], [-12, 19.25], [-12, 16.5], [-10.5, 16], [-8.5, 17], [-6.5, 18], [-5.25, 19.25]]},  # pal 8 (blueprint 9)
    {"name": "crackrock", "pal": 9, "h": 9.2, "kind": "ridge", "peak": [-0.08, 22.91], "footprint": [[5, 22.5], [4, 23.5], [3.75, 25.25], [3.5, 27], [1.5, 27], [-0.5, 27], [-2.25, 26.25], [-4, 25.5], [-4, 23], [-4, 20.5], [-2.25, 18.75], [-0.5, 17], [1, 17.5], [2.5, 18], [4, 19.5], [4, 21.5]], "crest": [[-4, 23.5], [3.5, 24]]},  # pal 9 (blueprint 9)
    {"name": "dome", "pal": 10, "h": 12.8, "kind": "crater", "peak": [-7.49, 12.1], "footprint": [[1, 9.5], [1, 11.5], [0, 12.5], [0, 14.5], [0, 16.5], [-1.75, 18.25], [-3.5, 20], [-6.17, 18.67], [-8.83, 17.33], [-11.5, 16], [-12.5, 14], [-15, 13.5], [-14, 11.5], [-13, 9.5], [-13, 6.5], [-11.5, 5], [-9.17, 5.33], [-6.83, 5.67], [-4.5, 6], [-3.5, 7.5], [-2.5, 9], [-1.5, 8]]},  # pal 10 (blueprint 10)
    {"name": "twin", "pal": 9, "h": 11.2, "kind": "ridge", "peak": [4.95, 11.71], "footprint": [[12, 17.5], [10.5, 19], [8.5, 19], [7.5, 20], [6.5, 19], [3.5, 19], [1.75, 17.75], [0, 16.5], [0.33, 13.83], [0.67, 11.17], [1, 8.5], [2, 7.5], [2, 5.5], [3.5, 4], [6.5, 4], [7.5, 3], [9, 3.5], [10, 5.5], [10, 8.5], [10, 11.5], [11, 12.5], [10.5, 14], [10, 15.5]], "crest": [[3.5, 15.5], [4, 8]]},  # pal 9 (blueprint 9)
    {"name": "wingtop", "pal": 8, "h": 7.8, "kind": "dome", "peak": [-20.42, 9.44], "footprint": [[-12, 5.5], [-13, 6.5], [-13.33, 8.5], [-13.67, 10.5], [-14, 12.5], [-15.5, 14], [-18.1, 14], [-20.7, 14], [-23.3, 14], [-25.9, 14], [-28.5, 14], [-29.67, 11.83], [-30.83, 9.67], [-32, 7.5], [-31.5, 5], [-29, 5], [-26.5, 5], [-24.5, 6], [-22.5, 7], [-20.5, 6.5], [-18.5, 6], [-16.5, 4], [-15.5, 5], [-13.75, 5.25]]},  # pal 8 (blueprint 8)
    {"name": "wingrock", "pal": 7, "h": 10.4, "kind": "dome", "peak": [-21.72, 0.02], "footprint": [[-12, -1.5], [-13, -0.5], [-13, 2.5], [-12, 3.5], [-12.5, 5], [-15.5, 5], [-16.5, 4], [-18.5, 6], [-20.5, 6], [-21.5, 7], [-23.5, 6.5], [-25.5, 6], [-26.5, 5], [-29.5, 5], [-32.5, 5], [-34, 2.5], [-34, -0.5], [-32.5, -2.33], [-31, -4.17], [-29.5, -6], [-28.5, -5], [-26.5, -5.5], [-24.5, -6], [-23.5, -5], [-20.5, -5], [-18.5, -4], [-16.5, -3], [-15.5, -4], [-13.5, -4]]},  # pal 7 (blueprint 7)
    {"name": "wingfoot", "pal": 6, "h": 6.6, "kind": "flat", "peak": [-18.39, -9.26], "footprint": [[-12, -9.5], [-13, -8.5], [-13.5, -6.5], [-14, -4.5], [-16.5, -3], [-17.5, -4], [-19.5, -4.33], [-21.5, -4.67], [-23.5, -5], [-24.5, -6], [-26.5, -5], [-29, -5.5], [-29, -7.5], [-27.33, -9.17], [-25.67, -10.83], [-24, -12.5], [-23.5, -14], [-20.5, -14], [-17.5, -14], [-14.5, -14], [-13.25, -11.75]]},  # pal 6 (blueprint 6)
    {"name": "saddle", "pal": 7, "h": 6, "kind": "flat", "peak": [-1.31, 5.31], "footprint": [[7, 2.5], [6.5, 4], [3.5, 4], [2, 6.5], [0.5, 9], [-1.5, 8], [-2.5, 9], [-3.5, 7.5], [-4.5, 6], [-6.83, 5.67], [-9.17, 5.33], [-11.5, 5], [-13, 2.5], [-10.25, 2.25], [-7.5, 2], [-5.17, 0.33], [-2.83, -1.33], [-0.5, -3], [1.5, -2], [3.5, -1], [5.25, 0.75]]},  # pal 7 (blueprint 7)
    {"name": "lowcentre", "pal": 9, "h": 10.6, "kind": "dome", "peak": [-6.44, -6.63], "footprint": [[0, -14.5], [0, -11.75], [0, -9], [0, -6.25], [0, -3.5], [-1.88, -2.13], [-3.75, -0.75], [-5.63, 0.63], [-7.5, 2], [-10, 2], [-12.5, 2], [-13, -0.5], [-12, -1.5], [-13, -3], [-14, -4.5], [-13.5, -6.5], [-13, -8.5], [-11.25, -10.25], [-9.5, -12], [-7.5, -12], [-5.5, -12], [-3.5, -13.5], [-1.5, -15]]},  # pal 9 (blueprint 9)
    {"name": "crevice", "pal": 6, "h": 8.6, "kind": "ridge", "peak": [5.47, -8.05], "footprint": [[15, -2.5], [13.25, -0.25], [11.5, 2], [9.5, 2.5], [7.5, 3], [5.63, 1.38], [3.75, -0.25], [1.88, -1.88], [0, -3.5], [0, -6], [0, -8.5], [0, -11], [0, -13.5], [1.5, -15], [3.5, -15.5], [5.5, -16], [6.5, -17], [7.5, -16], [10, -15.5], [12.5, -15], [12.75, -13.25], [13, -11.5], [12, -10.5], [12, -7.5], [13, -6.5], [13, -4.5]], "crest": [[2.5, -2.5], [2.8, -11.5]]},  # pal 7 (blueprint 6)
    {"name": "shoulder", "pal": 7, "h": 7.8, "kind": "dome", "peak": [14.54, 10.41], "footprint": [[23, 9.5], [22, 10.5], [22, 12.5], [20.5, 14], [17.83, 14], [15.17, 14], [12.5, 14], [12, 15.5], [11.5, 17], [10, 15.5], [10.5, 14], [11, 12.5], [10, 11.5], [10, 8.5], [10, 5.5], [9, 3.5], [10.5, 2], [13.5, 2], [15.5, 4], [17.5, 6], [19, 6.5], [20.5, 7], [21.75, 8.25]]},  # pal 7 (blueprint 7)
    {"name": "rightrock", "pal": 7, "h": 7.8, "kind": "flat", "peak": [20.94, 1.73], "footprint": [[31, -0.5], [31, 2.5], [29.13, 4.13], [27.25, 5.75], [25.38, 7.38], [23.5, 9], [21.5, 8], [19.5, 7], [17.5, 6], [15.5, 4], [13.5, 2], [12, 1.5], [13.75, -0.75], [15.5, -3], [16.5, -2], [18.5, -2], [19.5, -3], [21.5, -3], [23.5, -3], [24.5, -2], [27.5, -2], [29.25, -1.25]]},  # pal 6 (blueprint 7)
    {"name": "ringrock", "pal": 9, "h": 10.4, "kind": "crater", "peak": [19.78, -9.03], "footprint": [[25, -9.5], [24.83, -7], [24.67, -4.5], [24.5, -2], [23.5, -3], [21.5, -3], [19.5, -3], [18.5, -2], [16.5, -2], [14.75, -3.25], [13, -4.5], [13, -6.5], [12, -7.5], [12.33, -9.5], [12.67, -11.5], [13, -13.5], [15.25, -15.25], [17.5, -17], [19.5, -16.5], [21.5, -16], [23, -14.5], [23.5, -12.5], [24, -10.5]]},  # pal 9 (blueprint 9)
    {"name": "rightedge", "pal": 7, "h": 6.6, "kind": "flat", "peak": [26.98, -9.49], "footprint": [[32, -15.5], [32, -12.5], [32, -9.5], [32, -6.5], [31, -5.5], [31, -3.5], [31, -1.5], [28.5, -1], [27.5, -2], [25.5, -2], [25.33, -4.5], [25.17, -7], [25, -9.5], [24, -11.83], [23, -14.17], [22, -16.5], [24.5, -18], [27.5, -18], [28.5, -17], [30.5, -17]]},  # pal 7 (blueprint 7)
    {"name": "brightfoot", "pal": 9, "h": 8.6, "kind": "dome", "peak": [-8.66, -16.1], "footprint": [[1, -15.5], [0.5, -14], [-1.5, -15], [-3.5, -13.5], [-5.5, -12], [-7.5, -12], [-9.5, -12], [-11.5, -10], [-12.5, -10], [-14, -12.5], [-14, -13.5], [-12, -14.5], [-11.83, -17], [-11.67, -19.5], [-11.5, -22], [-9.5, -21], [-7, -21], [-4.5, -21], [-2.67, -19.17], [-0.83, -17.33]]},  # pal 9 (blueprint 9)
    {"name": "bottomleft", "pal": 4, "h": 6.4, "kind": "dome", "peak": [-6.32, -25.3], "footprint": [[1, -31.5], [1, -29], [1, -26.5], [0, -25.5], [-0.5, -23.33], [-1, -21.17], [-1.5, -19], [-2.5, -19], [-4.5, -21], [-7, -21], [-9.5, -21], [-12, -22.5], [-12, -24.83], [-12, -27.17], [-12, -29.5], [-10.5, -30], [-9.5, -29], [-9.25, -30.75], [-9, -32.5], [-7.5, -34], [-5, -34], [-2.5, -34], [-0.75, -32.75]]},  # pal 4 (blueprint 4)
    {"name": "bottommid", "pal": 5, "h": 6.8, "kind": "flat", "peak": [7.43, -22.71], "footprint": [[14, -21.5], [13, -19.5], [13, -16.5], [14, -15.5], [13.5, -14], [11.17, -15], [8.83, -16], [6.5, -17], [5.5, -16], [3.5, -15.5], [1.5, -15], [-0.25, -16.75], [-2, -18.5], [-1, -19.5], [-1, -22.5], [0, -24.5], [1, -26.5], [1, -29.5], [1, -32.5], [3.25, -33.75], [5.5, -35], [7.5, -35], [8.75, -33.25], [10, -31.5], [10, -28.5], [11, -26.5], [13, -25.5], [13, -22.5]]},  # pal 5 (blueprint 5)
    {"name": "knob", "pal": 8, "h": 8.8, "kind": "dome", "peak": [17.76, -20.94], "footprint": [[25, -18.5], [23.25, -17.25], [21.5, -16], [19.5, -16.5], [17.5, -17], [16, -16], [14.5, -15], [13, -16.5], [13, -19.5], [14, -20.5], [13, -22.5], [13, -25.5], [15.25, -25.75], [17.5, -26], [18.5, -27], [20.5, -27], [22.5, -27], [23, -24.5], [22, -23.5], [23.5, -21]]},  # pal 8 (blueprint 8)
    {"name": "lowright", "pal": 5, "h": 7.2, "kind": "flat", "peak": [26.87, -24.97], "footprint": [[35, -30.5], [35, -28], [35, -25.5], [34, -24.5], [34, -21.5], [33, -20.5], [33, -18.5], [33, -16.5], [31.5, -16], [30.5, -17], [28, -17.5], [25.5, -18], [24.33, -19.83], [23.17, -21.67], [22, -23.5], [23, -24.5], [23, -26.5], [23, -28.5], [24.5, -30], [26, -31.5], [27, -34], [28, -36.5], [29.75, -36.75], [31.5, -37], [33, -35.5], [33.5, -33.5], [34, -31.5]]},  # pal 4 (blueprint 5)
    {"name": "bottomright", "pal": 5, "h": 5.8, "kind": "dome", "peak": [18.02, -30.1], "footprint": [[28, -36.5], [27, -34], [26, -31.5], [24.5, -30], [23, -28.5], [23, -27.5], [20.75, -27.25], [18.5, -27], [17.5, -26], [14.5, -26], [11.5, -26], [10, -28.5], [10, -31.5], [9, -33], [8, -34.5], [9.75, -34.75], [11.5, -35], [12, -33.5], [13.5, -33], [15, -34], [16.5, -35], [19.5, -35], [20.5, -36], [23.5, -36], [24.5, -37], [26.25, -36.75]]},  # pal 5 (blueprint 5)
]

NAME = "assembly-newshd-89"
TAG = "nshd89"
PIECES = ["newshd-13", "newshd-49", "newshd-51", "newshd-53", "newshd-89", "newshd-91"]
CX0, CY0 = 146, 113
W, H = 72, 84
PX = 1 / 12
GROW = 1          # px each cell grows into its neighbours (interpenetration -> V cracks)
HSCALE = 1.0      # height scale on the blueprint heights
CHAMFER = 0.28    # px, edge chamfer
SEED = 89
PIT_DEPTH = 2.6  # px, the crater's dish (1.1 vanished at the game's 32 degree tilt)
# The sprite's four bright elliptical rings (centre x, y, semi-axes rx, ry in px frame, measured on the
# composite sprite): each is a crater, a raised lit lip round a deep faceted dish.
RINGS = {
    "dome": (-5.0, 11.9, 5.8, 5.6),      # the big ring, top centre
    "twin": (5.0, 12.3, 3.9, 5.3),       # its partner right beside it
    "crevice": (4.5, -8.4, 3.7, 5.6),    # the lower oval, left of ringrock (sprite ~(40, 49))
    "ringrock": (19.6, -8.1, 4.6, 5.5),
}
RIM_W = 1.15     # px, width of the flat lip between the rim's outer edge and the dish
LIP_DROP = 0.14  # share of h the shoulder sits below the lip: the lip stands up as a ring
LIP_SCALE = 0.93  # the lip's outer edge on the sprite's ring (its outer ink is shading)
WALL_FALL = 0.60  # share of h the crater's flank falls per unit of elliptical radius past the shoulder
PEBBLES = False  # rubble at the crack ends (hidden under the boulders' feet: off)
# The outline clip: (height px, inset px) stations. Vertical only for its first 0.5 px, then the
# outer flanks lean in visibly (no cliff walls where a boulder's hull bridges an outline notch).
CLIP_PROFILE = [(-0.2, 0.0), (0.5, 0.05), (3.0, 1.0), (8.0, 2.8), (16.0, 5.0)]  # leans more than -39: the
# heap's narrow arms (24 px) must not stand as towers in the tilted view
CLIP_TOL = 0.6    # px, Douglas-Peucker tolerance of the clip outline (0.3 left a sawtooth foot)
FOOT_TOL = 0.5    # px, the same for each boulder's foot
# Light comes from the upper left: "flat" fracture faces fall away to the lower right.
AWAY = Vector((0.8, -0.6)).normalized()

# Per-cell overrides on the blueprint (height px, kind) where B reads the sprite differently.
OVERRIDE = {
    "dome": {"h": 10.6},      # the big ringed rock: as high as newshd-39's crater (12.8 is a chimney)
    "ringrock": {"h": 9.4},
    "twin": {"h": 9.6, "kind": "crater"},
    "crevice": {"kind": "crater"},
    "peak": {"h": 9.0},
    "crackrock": {"h": 8.4},
    "wingrock": {"h": 9.0},
    "lowcentre": {"h": 9.2},
}
BLUNT = {}      # ridge crown: share of the height the top stations keep (flat, rounded)
SHELL_FACES = 4000
SEAM_BAND = 0.02  # units either side of a piece-box cut where the baked edge term is off
REFLEX_LEAN = 1.0  # share of the clip lean kept at concave outline vertices (0 left a V slot at the
# heap's concave corners; with the corners cut and a mitred offset the fold leans with the walls)
TAPER_PX = 1.5              # px they lean in at the first station
# The round underside (D125's asteroid: no base). Depth below the waist (px), the superellipse power
# of its plan (< 1: full shoulders), the height profile exponent, number of rings.
UNDER_H = 18.0
UNDER_POW = 0.85
UNDER_FALL = 0.8
UNDER_RINGS = 7
UNDER_CAP = 0.35   # px: the body's top cap, hidden under the boulders' feet (floor of the V cracks)
# Underside fracture faces (azimuth deg, elevation deg < 0, depth fraction), as lib_newshd_rock cuts.
UNDER_CUTS = [(20, -55, 0.06), (110, -40, 0.05), (200, -60, 0.07), (290, -45, 0.05),
              (65, -75, 0.05), (245, -30, 0.04), (155, -70, 0.05), (330, -65, 0.06)]
WARP_PX = 1.6      # amplitude of the vertical shear noise (px); its wavelength WARP_WAVE px
WARP_WAVE = 26.0
ROUGHNESS = 0.9    # D125: matte rock, metallic 0



# --- sprite ---------------------------------------------------------------------------------------

def sprite_data():
    idx, colors = SM.load(NAME)
    m = SM.masks(idx, colors)
    return idx, colors, m


def luma(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def inside(poly, x, y):
    n, c = len(poly), False
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def cells(m, parts):
    """label[y][x] = part index for every inner-mask pixel (-1 outside)."""
    inner = m["inner"]
    label = [[-1] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if not inner[y][x]:
                continue
            px, py = x + 0.5 - W / 2, H / 2 - y - 0.5
            hit = [i for i, p in enumerate(parts) if inside(p["footprint"], px, py)]
            if hit:
                label[y][x] = hit[0]
            else:
                label[y][x] = min(range(len(parts)), key=lambda i: (parts[i]["peak"][0] - px) ** 2
                                  + (parts[i]["peak"][1] - py) ** 2)
    return label


# The lower lobe's two big blueprint cells hold two rocks each in the sprite (the lobe is a pile of
# smaller, darker rocks): each splits at a row (px frame Y) into its upper rock and a lower toe rock.
SPLITS = {
    "bottommid": (-24.5, {"peak": [5.0, -19.5]},
                  {"name": "bottomtoe", "pal": 5, "h": 5.8, "kind": "dome", "peak": [6.0, -29.5]}),
    "lowright": (-26.5, {"peak": [27.5, -21.5]},
                 {"name": "lowtoe", "pal": 5, "h": 5.6, "kind": "dome", "peak": [26.5, -31.0]}),
}


def split_cells(label, parts):
    for name, (ycut, upd, new) in SPLITS.items():
        i = next(k for k, p in enumerate(parts) if p["name"] == name)
        parts[i].update(upd)
        parts.append(dict(new))
        j = len(parts) - 1
        for y in range(H):
            for x in range(W):
                if label[y][x] == i and H / 2 - y - 0.5 < ycut:
                    label[y][x] = j
    return label


# Concave outline corners where a piece is missing (sprite col, row, side of the empty piece in x and
# y: -1 = less than, +1 = greater). A convex boulder whose cell wraps such a corner would bridge it
# and the outline clip would cut a vertical slot into its flank, so the wrapped arm of the cell goes
# to its neighbours: each boulder stays on one side of the corner.
CORNERS = [(24, 28, -1, -1), (48, 28, 1, -1), (24, 56, -1, 1)]


def unwrap_corners(label, parts):
    for cx, cy, sx, sy in CORNERS:
        def arm_a(x, y):   # beside the empty piece in y (same columns as the empty piece's side)
            return (x < cx if sx < 0 else x >= cx) and (y >= cy if sy < 0 else y < cy)

        def arm_b(x, y):   # beside it in x
            return (x >= cx if sx < 0 else x < cx) and (y < cy if sy < 0 else y >= cy)
        for i in range(len(parts)):
            a = [(x, y) for y in range(H) for x in range(W) if label[y][x] == i and arm_a(x, y)]
            b = [(x, y) for y in range(H) for x in range(W) if label[y][x] == i and arm_b(x, y)]
            if not a or not b:
                continue
            move = a if len(a) < len(b) else b
            for _ in range(8):  # hand the smaller arm to its neighbours, ring by ring
                left = []
                for x, y in move:
                    nb = [label[y + dy][x + dx] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
                          if 0 <= y + dy < H and 0 <= x + dx < W and label[y + dy][x + dx] not in (-1, i)]
                    if nb:
                        label[y][x] = max(set(nb), key=nb.count)
                    else:
                        left.append((x, y))
                move = left
                if not move:
                    break
            print(f"B: corner ({cx},{cy}) cell {parts[i]['name']}: {len(a)}/{len(b)} px, moved the smaller arm")
    return label


def cell_colour(idx, colors, label, i):
    vals = sorted((luma(colors[idx[y][x]]), idx[y][x]) for y in range(H) for x in range(W)
                  if label[y][x] == i and idx[y][x] in colors)
    lo, hi = int(len(vals) * 0.15), max(int(len(vals) * 0.85), int(len(vals) * 0.15) + 1)
    band = vals[lo:hi]
    return band[len(band) // 2][1]


def trace(mask):
    """Outer boundary of a pixel region along pixel corners (x right, y down), as a loop."""
    edges = {}
    for y in range(H):
        for x in range(W):
            if not mask[y][x]:
                continue
            def on(yy, xx):
                return 0 <= yy < H and 0 <= xx < W and mask[yy][xx]
            if not on(y - 1, x):
                edges[(x + 1, y)] = (x, y)
            if not on(y, x - 1):
                edges[(x, y)] = (x, y + 1)
            if not on(y + 1, x):
                edges[(x, y + 1)] = (x + 1, y + 1)
            if not on(y, x + 1):
                edges[(x + 1, y + 1)] = (x + 1, y)
    best, seen = [], set()
    for s in list(edges):
        if s in seen:
            continue
        loop, p = [], s
        while p not in seen and p in edges:
            seen.add(p)
            loop.append(p)
            p = edges[p]
        if len(loop) > len(best):
            best = loop
    return best


def midpoints(loop):
    """Corner loop -> polygon through the pixel-edge midpoints, in px frame (X right, Y up)."""
    out = []
    n = len(loop)
    for i in range(n):
        (x1, y1), (x2, y2) = loop[i], loop[(i + 1) % n]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        out.append((mx - W / 2, H / 2 - my))
    return out


def simplify(pts, tol):
    """Douglas-Peucker on a closed loop."""
    def dp(seq):
        if len(seq) < 3:
            return seq
        a, b = Vector(seq[0]), Vector(seq[-1])
        ab = b - a
        L = ab.length or 1e-9
        best, bi = 0, 0
        for i in range(1, len(seq) - 1):
            p = Vector(seq[i])
            d = abs(ab.x * (a.y - p.y) - ab.y * (a.x - p.x)) / L
            if d > best:
                best, bi = d, i
        if best <= tol:
            return [seq[0], seq[-1]]
        return dp(seq[:bi + 1])[:-1] + dp(seq[bi:])
    k = max(range(len(pts)), key=lambda i: pts[i][0] + 0.37 * pts[i][1])
    seq = pts[k:] + pts[:k]
    a = Vector(seq[0])
    j = max(range(len(seq)), key=lambda i: (Vector(seq[i]) - a).length)
    return dp(seq[:j + 1])[:-1] + dp(seq[j:] + [seq[0]])[:-1]


def dilate(mask, inner, n):
    for _ in range(n):
        out = [row[:] for row in mask]
        for y in range(H):
            for x in range(W):
                if mask[y][x] or not inner[y][x]:
                    continue
                if any(0 <= y + dy < H and 0 <= x + dx < W and mask[y + dy][x + dx]
                       for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                    out[y][x] = True
        mask = out
    return mask


# --- geometry --------------------------------------------------------------------------------------

def nearest_on_seg(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return a + ab * t


def boulder_points(foot, part, rng):
    """Section points (px) of one boulder; the hull of these is the rock."""
    h = part["h"] * HSCALE
    kind = part["kind"]
    peak = Vector(part["peak"])
    crest = [Vector(c) for c in part["crest"]] if part.get("crest") else None
    pts = [(x, y, 0.0) for x, y in foot]
    if kind == "crater":
        rx0, ry0 = RINGS[part["name"]][:2]
        peak = Vector((rx0, ry0))
        crest = None
    # (inset fraction towards the crown, height fraction); a pchip profile through these stations
    if kind == "flat":
        prof = [(0.0, 0.0), (0.12, 0.42), (0.3, 0.78), (0.5, 0.95)]
    else:
        prof = [(0.0, 0.0), (0.24, 0.36), (0.46, 0.72), (0.66, 0.92), (0.8, 0.99)]
    zf = T.pchip([s for s, _ in prof], [z for _, z in prof])
    stations = [0.14, 0.34, 0.56, 0.74] if kind != "flat" else [0.1, 0.24, 0.38, 0.5]
    for k, s in enumerate(stations):
        # thin the rings out as they rise (fewer, bigger facets near the crown)
        step = 1 if k == 0 else 2 + k // 2
        for j in range(0, len(foot), step):
            p = Vector(foot[j])
            c = nearest_on_seg(p, crest[0], crest[1]) if crest else peak
            q = p + (c - p) * (s + rng.uniform(-0.04, 0.04))
            if k == 0:  # the foot leans in: no cliff wall at the outline, deeper V cracks between cells
                d = (c - p).length
                if d > 1e-6:
                    q = q + (c - p) / d * min(TAPER_PX, 0.4 * d)
            z = h * zf(s) * (1 + rng.uniform(-0.06, 0.04))
            if kind == "crater":
                # outside the lip the rock rolls down: the lip stays the highest ring
                e = ring_e(part, q)
                z = min(z, h * (1 - LIP_DROP - WALL_FALL * max(0.0, e - 1.3)))
            if part["name"] in BLUNT:
                z = min(z, h * BLUNT[part["name"]] + (h * 0.2) * max(0.0, s - 0.56) / 0.18)
            if kind == "flat":
                # the fracture plane: falls away from the light across the cell
                d = (q - peak).dot(AWAY)
                z = min(z, h - 0.32 * max(d, -3) + rng.uniform(-0.3, 0.3))
            pts.append((q.x, q.y, max(z, 0.4)))
    # crown
    if kind == "crater":
        # the lip: a flat ring at full height on the sprite's ellipse, then a shoulder ring well
        # below it (a lit raised lip with an outer bevel, no chimney walls); the pit cuts the dish
        cx, cy, rx, ry = ring(part)
        for k in range(14):
            a = 2 * math.pi * k / 14 + rng.uniform(-0.08, 0.08)
            pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a), h * rng.uniform(0.985, 1.0)))
        for k in range(12):
            a = 2 * math.pi * (k + 0.5) / 12 + rng.uniform(-0.1, 0.1)
            pts.append((cx + rx * 1.3 * math.cos(a), cy + ry * 1.3 * math.sin(a),
                        h * (1 - LIP_DROP) * rng.uniform(0.98, 1.0)))
        # the flank: a third ring rolls the shoulder down into the boulder's foot (a cone, not a
        # cylinder), where it lies over the boulder's own foot
        for k in range(12):
            a = 2 * math.pi * k / 12 + rng.uniform(-0.1, 0.1)
            x, y = cx + rx * 1.7 * math.cos(a), cy + ry * 1.7 * math.sin(a)
            if inside(foot, x, y):
                pts.append((x, y, h * (1 - LIP_DROP - WALL_FALL * 0.4) * rng.uniform(0.97, 1.0)))
    elif crest and part["name"] in BLUNT:
        # rounded crown: the crest line sags at both ends and the top is a wide pad, not an arris
        a, b = crest
        nrm = Vector((-(b - a).y, (b - a).x)).normalized()
        for t, f in ((0.12, 0.90), (0.35, 0.995), (0.65, 0.99), (0.88, 0.88)):
            c = a + (b - a) * t
            for off, ff in ((0.0, 1.0), (-2.2, 0.93), (2.2, 0.93)):
                q = c + nrm * off
                pts.append((q.x, q.y, h * f * ff))
    elif crest:
        a, b = crest
        for t, f in ((0.0, 0.93), (0.35, 1.0), (0.65, 0.99), (1.0, 0.9)):
            c = a + (b - a) * t
            pts.append((c.x, c.y, h * f))
    elif kind == "flat":
        # a low dome on the tilted fracture plane, not a table top
        def plane(q):
            return h - 0.32 * max((q - peak).dot(AWAY), -3)
        pts.append((peak.x, peak.y, plane(peak) + 0.9))
        for k in range(6):
            a = 2 * math.pi * k / 6 + rng.uniform(-0.2, 0.2)
            q = peak + Vector((math.cos(a), math.sin(a))) * rng.uniform(2.2, 2.8)
            pts.append((q.x, q.y, plane(q) + 0.55))
    else:
        r = 1.2
        for k in range(5):
            a = 2 * math.pi * k / 5 + rng.uniform(0, 1)
            pts.append((peak.x + r * math.cos(a), peak.y + r * math.sin(a), h * rng.uniform(0.96, 1.0)))
    return pts


def keep_off_corners(pts, margin=0.25):
    """Hull points inside the empty quarter beyond a concave outline corner (CORNERS) move to the
    nearer side of it: a convex boulder that bridged the corner was clipped there into a vertical
    notch at its foot."""
    out = []
    for x, y, z in pts:
        for col, row, sx, sy in CORNERS:
            X, Y = col - W / 2, H / 2 - row     # the corner in px frame (Y up; sprite rows grow down)
            ex, ey = (x - X) * sx, (Y - y) * sy  # > 0: on the empty piece's side in that axis
            if ex > 0 and ey > 0:
                if ex < ey:
                    x = X - sx * margin
                else:
                    y = Y + sy * margin
        out.append((x, y, z))
    return out


def hull_object(name, pts, mat_index, mats, coll):
    bm = bmesh.new()
    verts = [bm.verts.new(Vector(p) * PX) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    drop = [v for v in res["geom_interior"] + res["geom_unused"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.delete(bm, geom=list(set(drop)), context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(6.0), verts=bm.verts[:], edges=bm.edges[:])
    for f in bm.faces:
        f.material_index = mat_index
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def offset_poly(poly, d):
    """Move each vertex of a CCW (Y up) polygon inwards by d along its averaged edge normal."""
    n = len(poly)
    out = []
    for i in range(n):
        a, b, c = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        def nrm(p, q):
            t = (q - p).normalized()
            return Vector((-t.y, t.x))  # left of the edge = inside for CCW
        m = nrm(a, b) + nrm(b, c)
        m = m.normalized() if m.length > 1e-6 else nrm(a, b)
        # reflex (concave) vertex: no lean there, so the leaning walls meet in a soft twist, not a
        # V slot cut into the boulder behind the corner
        turn = (b - a).x * (c - b).y - (b - a).y * (c - b).x
        miter = 1.0 / max(m.dot(nrm(a, b)), 0.7) if turn < -1e-6 else 1.0  # concave: a true offset
        out.append(tuple(b + m * d * miter * (REFLEX_LEAN if turn < -1e-6 else 1.0)))
    return out


CORNER_CUT = 1.6  # px, each sharp concave outline corner of the clip is cut back this far along both edges


def chamfer_reflex(poly, cut=CORNER_CUT):
    """Cut every sharp concave corner of a CCW polygon diagonally: where the clip's two walls met in a
    reflex edge, the boulder sitting in the corner showed a narrow vertical slot at its foot. The cut
    adds at most cut^2/2 px outside the mask per corner."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b, c = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        u, v = b - a, c - b
        turn = u.x * v.y - u.y * v.x
        ang = u.angle(v) if u.length > 1e-6 and v.length > 1e-6 else 0.0
        if turn < -1e-6 and ang > math.radians(50) and u.length > 2 * cut and v.length > 2 * cut:
            out.append(tuple(b - u.normalized() * cut))
            out.append(tuple(b + v.normalized() * cut))
        else:
            out.append(tuple(b))
    print(f"B: clip outline {n} -> {len(out)} vertices (concave corners cut)")
    return out


def prism_object(name, poly, coll, profile=CLIP_PROFILE):
    """The outline clip: the outline at the ground, leaning in along `profile` (z px, inset px)."""
    area = sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))
    if area < 0:
        poly = poly[::-1]
    poly = chamfer_reflex(poly)
    bm = bmesh.new()
    rings = [[bm.verts.new((x * PX, y * PX, z * PX)) for x, y in offset_poly(poly, d)] for z, d in profile]
    n = len(poly)
    for lo, hi in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def apply_mods(obj):
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def boolean(obj, other, op):
    """EXACT boolean; if it empties the mesh (it fails on some hulls), retry MANIFOLD, then FLOAT."""
    keep = obj.data.copy()
    for solver in ("EXACT", "MANIFOLD", "FLOAT"):
        mod = obj.modifiers.new(op, "BOOLEAN")
        mod.operation = op
        mod.solver = solver
        mod.object = other
        apply_mods(obj)
        if len(obj.data.polygons) > 0:
            if solver != "EXACT":
                print(f"B: {obj.name} boolean {op} fell back to {solver}")
            break
        obj.data = keep.copy()


def ring(part):
    """(cx, cy, rx, ry) of the part's lip, px."""
    cx, cy, rx, ry = RINGS[part["name"]]
    return cx, cy, rx * LIP_SCALE, ry * LIP_SCALE


def ring_e(part, q):
    """Elliptical radius of point q (px) relative to the part's ring (1 = on the lip)."""
    cx, cy, rx, ry = ring(part)
    return math.hypot((q.x - cx) / rx, (q.y - cy) / ry)


def pit_object(name, part, coll, rng):
    """The crater's faceted dish: a low-poly ellipsoid sunk into the lip ring, PIT_DEPTH deep, its
    edge RIM_W inside the lip's outer edge (the sprite's bright ring)."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    h = part["h"] * HSCALE
    cx, cy, rx, ry = ring(part)
    c = PIT_DEPTH * 1.7                       # vertical semi-axis
    f = math.sqrt(1 - ((c - PIT_DEPTH) / c) ** 2)  # cross-section at the lip / equator
    ax, ay = (rx - RIM_W) / f, (ry - RIM_W) / f
    for v in bm.verts:
        k = 1 + rng.uniform(-0.03, 0.03)
        v.co = Vector(((cx + v.co.x * ax * k) * PX, (cy + v.co.y * ay * k) * PX,
                       (h - PIT_DEPTH + c + v.co.z * c) * PX))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def chamfer(obj, width=CHAMFER):
    """A small chamfer on every fracture edge sharper than 15 degrees (bevel modifier, applied)."""
    mod = obj.modifiers.new("chamfer", "BEVEL")
    mod.width = width * PX
    mod.segments = 1
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(15)
    mod.use_clamp_overlap = True
    mod.harden_normals = False
    apply_mods(obj)


def crack_ends(label, inner):
    """Outline pixels (col, row) where two cells meet, one per crack, pulled 1.5 px inside."""
    out = []
    for y in range(H):
        for x in range(W):
            if not inner[y][x]:
                continue
            edge = any(not (0 <= y + dy < H and 0 <= x + dx < W and inner[y + dy][x + dx])
                       for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if not edge:
                continue
            nb = {label[y + dy][x + dx] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if 0 <= y + dy < H and 0 <= x + dx < W and label[y + dy][x + dx] >= 0}
            if len(nb) >= 2:
                out.append((x, y))
    # one per cluster, moved towards the heap's centre
    picked = []
    for x, y in out:
        if all((x - a) ** 2 + (y - b) ** 2 > 16 for a, b in picked):
            picked.append((x, y))
    res = []
    for x, y in picked:
        dx, dy = W / 2 - x, H / 2 - y
        L = math.hypot(dx, dy) or 1
        res.append((round(x + 1.5 * dx / L), round(y + 1.5 * dy / L)))
    return res


def build(coll, idx, colors, m):
    parts = [dict(p) for p in PARTS]
    for p in parts:
        if p["name"] in OVERRIDE:
            p.update(OVERRIDE[p["name"]])
    label = cells(m, parts)
    label = split_cells(label, parts)
    label = unwrap_corners(label, parts)
    sprite = {"name": NAME, "colors": {str(k): list(v) for k, v in colors.items()}}
    pal = [cell_colour(idx, colors, label, i) for i in range(len(parts))]
    used = sorted(set(pal) | {4})
    mats = [common.palette_material(sprite, i, TAG, metallic=0.0, roughness=ROUGHNESS) for i in used]
    rng = random.Random(SEED)
    outline = simplify(midpoints(trace(m["inner"])), CLIP_TOL)
    prism = prism_object("clip", outline, coll)
    rocks = []
    info = []
    for i, part in enumerate(parts):
        cell = [[label[y][x] == i for x in range(W)] for y in range(H)]
        grown = dilate(cell, m["inner"], GROW)
        foot = simplify(midpoints(trace(grown)), FOOT_TOL)
        pts = keep_off_corners(boulder_points(foot, part, rng))
        o = hull_object(f"rock_{part['name']}", pts, used.index(pal[i]), mats, coll)
        chamfer(o, 0.9 if part["name"] in BLUNT else CHAMFER)
        if part["kind"] == "crater":
            pit = pit_object("pit", part, coll, rng)
            boolean(o, pit, "DIFFERENCE")
            bpy.data.objects.remove(pit, do_unlink=True)
        boolean(o, prism, "INTERSECT")
        for f in o.data.polygons:  # faces the cutters made take slot 0: give them the rock's colour
            f.material_index = used.index(pal[i])
        rocks.append(o)
        info.append({"name": part["name"], "pal": pal[i], "blueprint_pal": part["pal"], "h": part["h"] * HSCALE,
                     "kind": part["kind"], "pixels": sum(map(sum, cell))})
    # Pebbles where a crack between two boulders runs out at the outline: rubble at the foot.
    for k, (c, r) in enumerate(crack_ends(label, m["inner"]) if PEBBLES else []):
        x, y = c + 0.5 - W / 2, H / 2 - r - 0.5
        vals = sorted((luma(colors[idx[yy][xx]]), idx[yy][xx]) for yy in range(r - 1, r + 2)
                      for xx in range(c - 1, c + 2) if 0 <= yy < H and 0 <= xx < W and m["inner"][yy][xx])
        pi = vals[len(vals) // 2][1] if vals else 5
        pi = pi if pi in used else min(used, key=lambda u: abs(u - pi))
        rad = rng.uniform(1.6, 2.3)
        pts = []
        for j in range(9):
            a = 2 * math.pi * j / 9 + rng.uniform(-0.2, 0.2)
            rr = rad * rng.uniform(0.8, 1.1)
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a), 0.0))
            pts.append((x + 0.6 * rr * math.cos(a + 0.3), y + 0.6 * rr * math.sin(a + 0.3), rad * rng.uniform(0.9, 1.3)))
        pts.append((x, y, rad * 1.5))
        o = hull_object(f"pebble_{k}", pts, used.index(pi), mats, coll)
        chamfer(o, 0.2)
        boolean(o, prism, "INTERSECT")
        for f in o.data.polygons:
            f.material_index = used.index(pi)
        rocks.append(o)
    bpy.data.objects.remove(prism, do_unlink=True)
    rocks.append(underside_object("underside", outline, m["inner"], label, pal, used, mats, coll))
    # one mesh
    bm = bmesh.new()
    for o in rocks:
        b1 = bmesh.new()
        b1.from_mesh(o.data)
        bmesh.ops.remove_doubles(b1, verts=b1.verts[:], dist=1e-5)
        bmesh.ops.dissolve_degenerate(b1, dist=1e-5, edges=b1.edges[:])
        bmesh.ops.recalc_face_normals(b1, faces=b1.faces[:])
        nm = sum(1 for e in b1.edges if not e.is_manifold)
        print(f"B: {o.name} faces {len(b1.faces)} non-manifold edges {nm}")
        b1.to_mesh(o.data)
        b1.free()
        bm.from_mesh(o.data)
    for o in rocks:
        bpy.data.objects.remove(o, do_unlink=True)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    for poly in me.polygons:
        poly.use_smooth = False
    warp(me)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    return obj, mats, info, label, parts


def warp(me):
    """Vertical shear by a low noise of (x, y): the waist and the crowns rise and sink a little, the
    top view stays exact."""
    off = Vector((SEED * 0.37, SEED * 0.11, 5.3))
    for v in me.vertices:
        x, y = v.co.x / PX, v.co.y / PX
        v.co.z += WARP_PX * PX * noise.noise(Vector((x / WARP_WAVE, y / WARP_WAVE, 0)) + off)


def underside_object(name, outline, inner, label, pal, used, mats, coll):
    """The heap's round underside: a closed body whose waist is the outline clip's foot, closing in
    below on the mask's centroid (D125's rock_body underside), cut by a few fracture planes."""
    poly = list(outline)
    area = sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1] for i in range(len(poly)))
    if area < 0:
        poly = poly[::-1]
    poly = chamfer_reflex(poly)
    waist = offset_poly(poly, 0.03)
    px = [(x + 0.5 - W / 2, H / 2 - y - 0.5) for y in range(H) for x in range(W) if inner[y][x]]
    c = Vector((sum(p[0] for p in px) / len(px), sum(p[1] for p in px) / len(px)))

    def pull_in(q, p):
        """q on the ray from c to p, moved towards c until it lies inside the waist polygon."""
        t = 1.0
        while not inside(waist, q.x, q.y) and t > 0.05:
            t *= 0.92
            q = c + (q - c) * 0.92
        return q
    bm = bmesh.new()
    rings = [[bm.verts.new((x * PX, y * PX, UNDER_CAP * PX)) for x, y in offset_poly(poly, 0.12)],
             [bm.verts.new((x * PX, y * PX, 0.0)) for x, y in waist]]
    for k in range(1, UNDER_RINGS):
        phi = (math.pi / 2) * k / UNDER_RINGS          # 0 at the waist, pi/2 at the pole
        s = math.cos(phi) ** UNDER_POW
        z = -UNDER_H * math.sin(phi) ** UNDER_FALL
        ring = []
        for x, y in waist:
            p = Vector((x, y))
            q = pull_in(c + (p - c) * s, p)
            ring.append(bm.verts.new((q.x * PX, q.y * PX, z * PX)))
        rings.append(ring)
    pole = bm.verts.new((c.x * PX, c.y * PX, -UNDER_H * PX))
    n = len(waist)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    for i in range(n):
        bm.faces.new((rings[-1][i], rings[-1][(i + 1) % n], pole))
    cap = bm.faces.new(rings[0])
    bmesh.ops.triangulate(bm, faces=[cap])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ROCK.cut_planes(bm, UNDER_CUTS)
    # each face takes the colour of the boulder above it (the band seen at the tilted camera)
    for f in bm.faces:
        q = f.calc_center_median() / PX
        col, row = int(q.x + W / 2), int(H / 2 - q.y)
        best = None
        for rr in range(0, 6):
            for yy in range(row - rr, row + rr + 1):
                for xx in range(col - rr, col + rr + 1):
                    if 0 <= yy < H and 0 <= xx < W and label[yy][xx] >= 0:
                        best = label[yy][xx]
                        break
                if best is not None:
                    break
            if best is not None:
                break
        f.material_index = used.index(pal[best if best is not None else 0])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    print(f"B: underside {len(o.data.polygons)} faces, {UNDER_H} px deep")
    return o


# --- copied helpers (assembly-newsh4-124.py; candidates for common.py) -----------------------------

def whole_shell(obj, coll, voxel=0.016, faces=2400, smooth=4):
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    coll.objects.link(shell)
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    apply_mods(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    seen, islands = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            isl.append(x)
            stack.extend(e.other_vert(x) for e in x.link_edges)
        islands.append(isl)

    def volume(isl):
        ids = {v.index for v in isl}
        fs = {f for v in isl for f in v.link_faces}
        vol = 0.0
        for f in fs:
            if f.verts[0].index not in ids:
                continue
            p0 = f.verts[0].co
            for k in range(1, len(f.verts) - 1):
                vol += p0.dot(f.verts[k].co.cross(f.verts[k + 1].co)) / 6.0
        return vol
    drop = set()
    for isl in islands:
        if len(isl) < 12 or volume(isl) < 1e-4:
            drop.update(v.index for v in isl)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index in drop], context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    print(f"shell before decimate: {n} faces")
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    apply_mods(shell)
    return shell


def split_open(obj, layout, coll, suffix):
    """split_assembly without capping the cuts (for the outline shells: no seams outlined)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    return out


def bake_piece(obj, out_dir, size=512, samples=48):
    """AO/edge colour multiplier + roughness/metallic bake into the piece's own palette material copies
    (assembly-newsh4-124.py bake_piece, trimmed). No concept projection."""
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # the cut caps (inside the heap, never seen) get no UV island: their dark AO, packed next to the
    # rock faces they border, bled across the cut as a dashed seam
    caps = cap_faces(obj)
    for poly in me.polygons:
        poly.select = poly.index not in caps
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    uvd = me.uv_layers["bake"].data  # re-fetched: edit mode rebuilt the layer
    for poly in me.polygons:
        if poly.index in caps:
            for li in poly.loop_indices:
                uvd[li].uv = (0.0, 0.0)
    used = sorted({p.material_index for p in me.polygons})
    for k in used:
        mt = me.materials[k]
        c = mt.copy()
        c.name = f"{mt.name}-{obj.name}"
        me.materials[k] = c
    mats = [me.materials[k] for k in used]
    col_img = bpy.data.images.new(f"{obj.name}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{obj.name}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    saved = {}
    for mt in mats:
        out = next(n for n in mt.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[mt.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(mt, mode):
        nt = mt.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, bb=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, bb)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 16
        ao_s.inputs["Distance"].default_value = 0.05
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 16
        ao_l.inputs["Distance"].default_value = 0.3
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        # no edge term along the piece box: the Bevel node only sees this piece, so the cut's cap made
        # an "edge" there that baked as a dashed seam across the boulders the box cuts
        tc = node("ShaderNodeTexCoord")
        sxyz = node("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sxyz.inputs[0])
        inx = math_("LESS_THAN", math_("ABSOLUTE", sxyz.outputs["X"]), 1.0 - SEAM_BAND)
        iny = math_("LESS_THAN", math_("ABSOLUTE", sxyz.outputs["Y"]), 14 / 12 - SEAM_BAND)
        edge = math_("MULTIPLY", edge, math_("MULTIPLY", inx, iny))
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.6, math_("MULTIPLY", ao_l.outputs["AO"], 0.4)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.42, math_("MULTIPLY", occl, 0.66)),
                                       math_("MULTIPLY", edge, 0.18)), 1.0)
            nt.links.new(v, em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.15),
                                          math_("MULTIPLY", edge, 0.12)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {mt.name: bake_shader(mt, mode) for mt in mats}
        bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
        for mt in mats:
            nt = mt.node_tree
            for n in tmps[mt.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[mt.name] is not None:
                nt.links.new(saved[mt.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
    for mt in mats:
        nt = mt.node_tree
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


def is_cap(f, hw=1.0, hh=14 / 12, tol=1e-4):
    """A face split_assembly filled on a cut of the piece box (bmesh face, piece-local coords)."""
    return (all(abs(abs(v.co.x) - hw) < tol for v in f.verts) and abs(abs(f.normal.x) - 1) < 1e-3) or \
           (all(abs(abs(v.co.y) - hh) < tol for v in f.verts) and abs(abs(f.normal.y) - 1) < 1e-3)


def cap_faces(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    out = {f.index for f in bm.faces if is_cap(f)}
    bm.free()
    return out


def recolour_caps(obj):
    """split_assembly fills each cut with material slot 0 (the darkest rock): where two pieces meet,
    a hairline between them showed that dark cap as a dashed seam across the boulder. Each cap face
    takes the material of the rock face it borders."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    caps = {f for f in bm.faces if is_cap(f)}
    todo = set(caps)
    for _ in range(50):
        done = set()
        for f in todo:
            nb = [g.material_index for e in f.edges for g in e.link_faces if g is not f and g not in todo]
            if nb:
                f.material_index = max(set(nb), key=nb.count)
                done.add(f)
        todo -= done
        if not todo or not done:
            break
    bm.to_mesh(obj.data)
    bm.free()
    print(f"B: {obj.name} cap faces recoloured {len(caps) - len(todo)}/{len(caps)}")


# --- review renders --------------------------------------------------------------------------------

def set_engine(name):
    scene = bpy.context.scene
    try:
        scene.render.engine = name
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if name in e)


def setup_workbench(flat):
    scene = bpy.context.scene
    set_engine("BLENDER_WORKBENCH")
    sh = scene.display.shading
    sh.light = "FLAT" if flat else "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_cavity = not flat
    sh.show_object_outline = not flat
    sh.show_shadows = False
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def setup_game():
    scene = bpy.context.scene
    set_engine("BLENDER_EEVEE")
    world = scene.world or bpy.data.worlds.new("game")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.42, 0.45, 0.55, 1.0)
    bg.inputs[1].default_value = 1.0
    sd = bpy.data.lights.new("game_sun", "SUN")
    sd.energy = 3.0
    sun = bpy.data.objects.new("game_sun", sd)
    bpy.context.scene.collection.objects.link(sun)
    d = Vector((-6, -8.4, 20)).normalized()
    sun.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    return sun


def camera(location, look_at, ortho=None, fov=None, top=False):
    data = bpy.data.cameras.new("cam")
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    elif fov:
        data.sensor_fit = "VERTICAL"
        data.angle_y = math.radians(fov)
    cam = bpy.data.objects.new("cam", data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    cam.rotation_euler = (0, 0, 0) if top else (Vector(look_at) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    return cam


def render(cam, path, rx, ry):
    scene = bpy.context.scene
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    data = cam.data
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(data)


def render_views(objs, hide, out, k=8, panel=520):
    out.mkdir(parents=True, exist_ok=True)
    for o in hide:
        o.hide_render = True
    for o in objs:  # Workbench shows diffuse_color
        for mt in o.data.materials:
            bsdf = next((n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            base = bsdf.inputs["Base Color"]
            col = base.links[0].from_node.inputs[7].default_value if base.is_linked else base.default_value
            mt.diffuse_color = tuple(col)
    ext = max(W, H) * PX
    setup_workbench(True)
    render(camera((0, 0, 20), (0, 0, 0), ortho=H * PX, top=True), out / "top_flat.png", W * k, H * k)
    setup_workbench(False)
    render(camera((0, 0, 20), (0, 0, 0), ortho=H * PX, top=True), out / "top.png", W * k, H * k)
    span = ext * 1.3
    zc = span * 0.02  # the underside in frame too
    render(camera((-30, 0, zc), (0, 0, zc), ortho=span), out / "left.png", 2 * panel, panel)
    render(camera((0, 30, zc), (0, 0, zc), ortho=span), out / "front.png", 2 * panel, panel)
    render(camera((0, -30, zc), (0, 0, zc), ortho=span), out / "rear.png", 2 * panel, panel)
    render(camera((0, 0, -20), (0, 0, 0), ortho=ext * 1.15), out / "under.png", panel, panel)
    d = ext * 1.45 + 1.5
    setup_workbench(False)
    sun = setup_game()
    render(camera((-d * 0.6, d * 0.55, d * 0.75), (0, 0, 0.2), fov=35), out / "q34_fl.png", panel, panel)
    render(camera((d * 0.6, -d * 0.55, d * 0.75), (0, 0, 0.2), fov=35), out / "q34_rr.png", panel, panel)
    render(camera((d * 0.25, d * 0.15, d * 1.05), (0, 0, 0.1), fov=35), out / "high.png", panel, panel)
    render(camera((-d * 0.6, d * 0.55, d * 0.75), (0, 0.3, 0.2), fov=17), out / "zoom_fl.png", 900, 900)
    tilt = math.radians(32)
    render(camera((0, -d * math.sin(tilt), d * math.cos(tilt)), (0, 0, 0), fov=35), out / "game.png", panel, panel)
    # the same tilt at the game's own size (48 px wide object -> ~64 px tall panel), then scaled
    render(camera((0, -d * math.sin(tilt), d * math.cos(tilt)), (0, 0, 0), fov=35), out / "game_small.png", 96, 96)
    render(camera((0, 0, 20), (0, 0, 0), ortho=H * PX, top=True), out / "top_game.png", W * k, H * k)
    bpy.data.objects.remove(sun, do_unlink=True)
    # top mask: pure silhouette
    setup_workbench(True)
    saved = [tuple(mt.diffuse_color) for o in objs for mt in o.data.materials]
    for o in objs:
        for mt in o.data.materials:
            mt.diffuse_color = (1, 1, 1, 1)
    render(camera((0, 0, 20), (0, 0, 0), ortho=H * PX, top=True), out / "top_mask.png", W * k, H * k)
    i = 0
    for o in objs:
        for mt in o.data.materials:
            mt.diffuse_color = saved[i]
            i += 1
    for o in hide:
        o.hide_render = False


# --- main ------------------------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    idx, colors, m = sprite_data()
    obj, mats, info, label, parts = build(coll, idx, colors, m)
    shell = whole_shell(obj, coll, faces=SHELL_FACES)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in common.load_sprite(ROOT, "newshd-13")["assemblyLayout"]
              if e["model"] in PIECES]
    shells = split_open(shell, layout, coll, "_outline")
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    for sh in shells.values():
        sh["tyrian_outline"] = True
        sh.data.materials.append(outline_mat)
        sh.data.shade_smooth()
    bpy.data.objects.remove(shell, do_unlink=True)
    pieces = common.split_assembly(obj, layout)
    for p in pieces.values():
        recolour_caps(p)
    obj.hide_render = True
    tri = 0
    for p in pieces.values():
        p.data.calc_loop_triangles()
        tri += len(p.data.loop_triangles)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        scene = bpy.context.scene
        set_engine("CYCLES")
        scene.cycles.samples = 48
        scene.cycles.device = "CPU"
        tmp = tempfile.mkdtemp(prefix="nshd89_bake_")
        for sh in shells.values():
            sh.hide_render = True
        for name, cx, cy in layout:  # each piece baked with its neighbours in place round it
            pieces[name].location = (cx / 12, -cy / 12, 0)
        for name in PIECES:
            bake_piece(pieces[name], tmp)
        for p in pieces.values():
            p.location = (0, 0, 0)
        fmt = "WEBP"
    print(f"{NAME}: rock triangles {tri}, outline shell faces {sum(len(sh.data.polygons) for sh in shells.values())}")
    print("pal:", [(i["name"], i["pal"], i["blueprint_pal"]) for i in info])
    if "--render" in argv:
        for name, cx, cy in layout:
            pieces[name].location = (cx / 12, -cy / 12, 0)
        render_views(list(pieces.values()), [obj] + list(shells.values()), Path(argv[argv.index("--render") + 1]))
        for p in pieces.values():
            p.location = (0, 0, 0)
    if "--no-export" not in argv:
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"],
                                       image_format=fmt)
    if "--design-out" in argv:
        export = []
        for name, cx, cy in layout:
            for o in (pieces[name], shells[name]):
                o.location = (cx / 12, -cy / 12, 0)
                o["tyrian_piece"] = name
                export.append(o)
        common.export_glb(export, Path(argv[argv.index("--design-out") + 1]), image_format=fmt)


if __name__ == "__main__":
    main()
