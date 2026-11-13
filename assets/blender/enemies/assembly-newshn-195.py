"""Mouth boss (newshn.shp, assembly of 17 pieces): a 3D version of its sprites.

Seen in episode 2 (level 2.4). Seventeen 2x2 enemies side by side make one 120 x 95 px organic
head (sprite.json `assemblyLayout`; the top row is cut off by the screen edge, the boss carries
on above it): a dark blue-grey biomechanical skull with a lumpy purple brain on top, three
glowing red eyes down each side, tentacles hanging off its flanks, purple claws low on each
side and a bony chin spike. Most of the face is a huge round mouth: a ring of pink gums with
bone fangs pointing inward, and a throat of dark red ridges sinking to a glowing core.

The four pieces round the throat (newshn-119, -121, -157, -159) animate over five frames: the
teeth dim and draw back into the gums while a fire rises from the core, red, then orange, then
white-hot. Each keeps one model for its frames (DECISIONS.md D17). Every piece is cut from one
head mesh, painted and baked once (so the animated pieces' skin matches their neighbours'); only its
throat and gum faces inside the animated pieces take a colour per frame (palette materials with
`frames`), and the teeth and the fire are parts per frame (frame_part). The AO/roughness bake puts
each piece in its own 512 px tile, and each piece's glb carries only its tile.

The whole head is built once in assembly coordinates and cut into the pieces with
common.split_assembly. The head is a shell in polar rings round the mouth: from the outline in
to the gums, over the gums and down the throat to the core; its faces take the palette colour
of the sprite pixel under them, so the biomechanical texture, gums and throat ridges follow the
sprite. Brain, eyes, fangs, tentacles, claws and chin spike are modelled on top.

Back of the skull (the seven pieces newshn-3/5/7, -41/43/45 and -85, which the first version left as flat
sprites): the boss goes on above the top row of the head, two more rows of pieces, and newshn-85
is the missing fifth piece of the top row. The back of the skull (carapace, occipital condyles, the
spinal cord, hood lobes with their foramina, the brain in two lobes, side plates) is one closed
solid built on a 0.5 px grid from cross-section forms, its footprint the sprite's inner mask
(`GYGES_DATA` below: footprint fields and the pixel grid, made by prep.py there from the game's
data; the original pixels are never committed). Where it meets the head (row -0.5) it blends onto the
head's own surface. newshn-85 is the head's own mesh (the mirror of newshn-77). All 24 pieces are
baked together (AO and roughness, one tile each) and exported as before.

Run: blender --background --python assets/blender/enemies/assembly-newshn-195.py [-- --preview out.png]
(the preview is the whole head; each piece also gets <piece>.png next to it).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b024 as lib  # noqa: E402

NAME = "assembly-newshn-195"
ROOT = common.repo_root(__file__)
TAG = "nshn195"
PIECES = ["newshn-77", "newshn-79", "newshn-81", "newshn-83",
          "newshn-115", "newshn-117", "newshn-119", "newshn-121", "newshn-123",
          "newshn-153", "newshn-155", "newshn-157", "newshn-159", "newshn-161",
          "newshn-193", "newshn-195", "newshn-197"]
# Assembly pixel (0, 0) is screen (113, -31): the top-left corner of newshn-77. The head is mirror
# symmetric about pixel column 63 (screen x 176.5), which is Blender X = 0; pixel row 47.5
# (screen y 17) is Blender Y = 0.
SX0, SY0 = 113, -31
AXIS = 63
ROW0 = 47.5


def X(c):
    """Assembly pixel column (centre; fractions allowed) to Blender X."""
    return (c - AXIS) / 12


def Y(r):
    """Assembly pixel row (centre) to Blender Y: sprite up is +Y."""
    return (ROW0 - r) / 12


def to_px(x, y):
    return x * 12 + AXIS, ROW0 - y * 12


PX = 1 / 12

# --- outlines (assembly pixel centres, left half from the top down; mirrored about AXIS) -------

# The head without its tentacles, claws and chin spike; it runs on above the top of the sprite.
OUT_LEFT = [(63, -8), (13, -8), (13, 12), (15.5, 14), (14.3, 17), (14.3, 20.5), (16, 22.5), (15.5, 24.5),
            (13.8, 27), (12, 30), (10, 32), (9, 34), (9, 40), (9.5, 43.5), (13, 45), (17, 46.5),
            (20, 48.3), (24, 50), (25.2, 52), (25.5, 54.5), (27.2, 57.2), (29.5, 59.5), (30.2, 62),
            (29.5, 65), (28.5, 68), (27.6, 71), (28.2, 72.6), (31.0, 75.0), (31.5, 76.6), (31.6, 78.6),
            (32.6, 80.2), (34.4, 81.3), (34.4, 85.3), (35.5, 86.4), (36.4, 87.6), (37.4, 89.2), (38.6, 90.3),
            (40.5, 91.4), (42.6, 92.5), (52.5, 92.5), (53.3, 90.6), (60.5, 90.6)]
# Outer and inner edge of the gums.
GUM_OUT_LEFT = [(63, 35), (52, 35), (49, 36.8), (46, 38.8), (42, 41.5), (38.5, 44.2), (36.2, 47), (35.2, 50),
                (35.5, 56), (37.5, 58.5), (38.6, 61), (38.8, 64), (41, 66.5), (43.5, 68.2), (44.5, 71),
                (44.6, 74.5), (45, 77.5), (45.8, 80.8), (48.2, 82.3), (50.5, 83.6), (54, 84.6), (57.5, 85.2)]
GUM_IN_LEFT = [(63, 40.6), (52, 40.6), (48.5, 42.6), (46.2, 45), (44.3, 47.3), (43.2, 50.5), (43.4, 53.5),
               (44, 57.5), (46.2, 60), (47.6, 63), (47.6, 67), (47.2, 71.5), (48.2, 75), (50.8, 78.6),
               (54, 80.8), (58, 82.2)]
CENTRE = (63.0, 60.0)  # the polar rings' centre: the middle of the mouth
CORE = (63.0, 56.0)  # the glowing core deep in the throat

# Palette families: the shell's faces take the sprite's colour, snapped to these shades.
# The throat's near-black (index 1) is its own darkest "red", so the gaps between its ridges stay black.
FAMILIES = {
    "blue": [96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 107],
    "gum": [65, 67, 68, 71, 73, 75],
    "red": [1, 112, 113, 114, 115, 117, 120],
    "purple": [82, 83, 85, 87, 90],
    "tooth": [19, 163, 169],
}
FAMILY_OF = {rep: fam for fam, reps in FAMILIES.items() for rep in reps}
DARK = {"blue": 96, "gum": 65, "red": 1, "purple": 82, "tooth": 163}
# For the animated pieces the throat's reds keep the fire's bright shades apart (orange, yellow,
# white-hot), which the static paint lumps into 120.
FINE_FAMILIES = dict(FAMILIES, red=[1, 112, 113, 114, 115, 117, 120, 122, 124, 126])
FAMILY_OF.update({rep: "red" for rep in FINE_FAMILIES["red"]})
# How a part's colours follow the sprite's shades (Painter.shade): (how much of the step away from
# the part's mid-tone to keep, soft-average radius in px or 0 for none, leave outline black out).
# The throat keeps its dark rings half (they are its ledges' gaps), unsmoothed.
SOFT = {"blue": (0.32, 1.3, True), "gum": (0.25, 1.2, True), "red": (0.75, 0.0, False),
        "purple": (0.35, 1.0, True)}
LIGHTS = {117, 120, 122, 124, 126}  # the throat's glow and the fire: lights, not shading

# The animated pieces' frames, phase by phase (the layout above shows phase 2).
ANIM = {"newshn-119": [119, 229, 233, 237, 241], "newshn-121": [121, 231, 235, 239, 243],
        "newshn-157": [157, 267, 271, 275, 279], "newshn-159": [159, 269, 273, 277, 281]}
PHASES = 5
ANIM_COLOURS = 24  # most animated shell colours (each is a material, so a draw call per piece)
# Teeth per phase, measured along each fang in the sprite: (length against the modelled fang,
# which is phase 2's, and palette shade, every other one of the sprite's to save materials). The
# fangs as listed in build_parts, left then right, then the short dark tooth under the upper lip.
FANGS = {
    ("L", 0): [(1.1, 171), (1.1, 169), (1.0, 169), (0.85, 167), (0.45, 165)],
    ("L", 1): [(1.0, 171), (1.0, 169), (1.0, 169), (1.0, 167), (0.85, 165)],
    ("L", 2): [(1.25, 169), (1.1, 169), (1.0, 169), (1.0, 169), (1.0, 169)],
    ("L", 3): [(1.2, 169), (1.2, 169), (1.0, 169), (0.8, 167), (0.6, 167)],
    ("L", 4): [(1.0, 171), (1.0, 171), (1.0, 169), (1.0, 167), (0.65, 165)],
    ("L", 5): [(1.4, 169), (1.4, 167), (1.0, 169), (1.0, 167), (0.9, 167)],
    ("L", 6): [(1.35, 169), (1.35, 169), (1.0, 169), (0.85, 167), (0.85, 167)],
    ("R", 0): [(1.0, 171), (1.0, 169), (1.0, 169), (0.8, 167), (0.4, 165)],
    ("R", 1): [(1.0, 171), (1.0, 169), (1.0, 169), (1.0, 165), (0.85, 165)],
    ("R", 2): [(1.4, 169), (1.3, 169), (1.0, 169), (0.85, 167), (0.65, 167)],
    ("R", 3): [(1.2, 171), (1.2, 169), (1.0, 169), (0.8, 167), (0.4, 165)],
    ("R", 4): [(1.0, 171), (1.0, 169), (1.0, 169), (1.0, 165), (0.65, 163)],
    ("R", 5): [(1.4, 169), (1.4, 167), (1.0, 169), (1.0, 167), (0.9, 167)],
    ("R", 6): [(1.35, 169), (1.35, 169), (1.0, 169), (0.85, 167), (0.85, 167)],
    "knob": [(1.1, 163), (1.05, 163), (1.0, 163), (0.8, 161), (0.4, 161)],
}
# The fire in the throat per phase: (palette index, centre col, row, z, radii px x, y, z, emission).
# Phase 2 is the static model's core.
FIRE = [
    [],
    [(115, 63.0, 56.5, -0.1, 2.8, 2.4, 0.04, 1.5)],
    [(115, 63.0, 56.0, -0.1, 4.2, 3.6, 0.05, 0.0), (117, 63.1, 55.9, -0.08, 2.9, 2.6, 0.05, 1.5),
     (121, 63.3, 55.8, -0.07, 1.6, 1.5, 0.05, 4.0)],
    [(117, 63.0, 56.5, -0.09, 5.0, 4.2, 0.05, 1.5), (122, 63.0, 56.2, -0.06, 3.0, 2.6, 0.05, 4.0),
     (126, 63.0, 56.0, -0.035, 1.0, 1.0, 0.03, 6.0)],
    [(118, 63.5, 57.5, -0.08, 6.6, 5.6, 0.06, 2.0), (121, 63.5, 57.5, -0.05, 5.0, 3.9, 0.05, 3.0),
     (124, 62.8, 57.8, -0.03, 2.4, 3.2, 0.05, 4.5), (127, 62.6, 55.6, -0.005, 1.2, 1.2, 0.035, 6.0)],
]


def blur(a, sigma):
    import numpy as np
    k = np.arange(-int(3 * sigma), int(3 * sigma) + 1)
    w = np.exp(-k * k / (2 * sigma * sigma))
    w /= w.sum()
    a = np.apply_along_axis(lambda v: np.convolve(v, w, mode="same"), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(v, w, mode="same"), 1, a)


def sample_field(F, c, r):
    """Bilinear sample of a field indexed [row + 10, col]."""
    import math as _m
    y, x = r + 10, c
    x0, y0 = int(_m.floor(x)), int(_m.floor(y))
    fx, fy = x - x0, y - y0
    h, w = F.shape
    def at(yy, xx):
        return float(F[min(max(yy, 0), h - 1), min(max(xx, 0), w - 1)])
    return ((at(y0, x0) * (1 - fx) + at(y0, x0 + 1) * fx) * (1 - fy)
            + (at(y0 + 1, x0) * (1 - fx) + at(y0 + 1, x0 + 1) * fx) * fy)


RELIEF_AMP = 0.075  # the sprite's light plates stand ~1 px, its dark grooves sink ~1 px


def rep_of(idx, context, fine=False):
    """The shade (palette index) a sprite pixel stands for; outline black depends on where it is.
    `fine` keeps the fire's bright shades apart (FINE_FAMILIES)."""
    if idx < 0:
        return None
    if fine and 119 <= idx <= 127:
        return (120, 120, 122, 122, 124, 124, 126, 126, 126)[idx - 119]
    if idx <= 4 or idx == 48:
        return DARK[context]
    for lo, hi, rep in ((16, 27, 19), (64, 65, 65), (66, 67, 67), (68, 69, 68), (70, 71, 71), (72, 73, 73),
                        (74, 77, 75), (80, 82, 82), (83, 83, 83), (84, 85, 85), (86, 88, 87), (89, 93, 90),
                        (96, 96, 96), (97, 97, 97), (98, 98, 98), (99, 99, 99), (100, 100, 100), (101, 101, 101),
                        (102, 102, 102), (103, 103, 103), (104, 104, 104), (105, 106, 105), (107, 111, 107),
                        (255, 255, 107),
                        (112, 112, 112), (113, 113, 113), (114, 114, 114), (115, 115, 115), (116, 118, 117),
                        (119, 127, 120),
                        (160, 165, 163), (166, 174, 169)):
        if lo <= idx <= hi:
            return rep
    return None


class Palette:
    """Material slots by palette index, made on first use."""

    # (metallic, roughness) per family. The head is a creature: its blue-grey skull a hard, slightly
    # glossy carapace (not metal), the gums and throat wet flesh, the brain and claws matte-ish
    # organic, the fangs smooth bone. The lighting shades them; their colours are mid-tones.
    STYLE = {"blue": (0.1, 0.45), "gum": (0.0, 0.66), "red": (0.0, 0.78), "purple": (0.0, 0.6),
             "tooth": (0.0, 0.3)}

    def __init__(self, sprite):
        self.sprite = sprite
        self.mats = []
        self.slots = {}
        self.index = []  # palette index per slot (the first frame's, for animated ones)

    def __call__(self, idx, emission=0.0, fam=None):
        if idx not in self.slots:
            fam = fam or FAMILY_OF.get(idx, "blue")
            metallic, rough = self.STYLE[fam]
            if idx == 120:
                emission = emission or 2.5
            elif fam == "red" and idx >= 112 and not emission:
                emission = 0.25  # design B: the throat's flesh smoulders a little (an ember, D126)
            self.slots[idx] = len(self.mats)
            self.index.append(idx)
            self.mats.append(common.palette_material(self.sprite, idx, TAG, metallic=metallic, roughness=rough,
                                                     emission_strength=emission))
        return self.slots[idx]

    def animated(self, reps):
        """A slot whose colour follows the animated pieces' frames: reps[k] is the palette index on
        phase k (ANIM). A colour that never changes is a plain slot."""
        if len(set(reps)) == 1:
            return self(reps[0])
        key = tuple(reps)
        if key not in self.slots:
            metallic, rough = self.STYLE[FAMILY_OF.get(reps[0], "blue")]
            frames = {nums[k]: reps[k] for nums in ANIM.values() for k in range(1, PHASES) if reps[k] != reps[0]}
            self.slots[key] = len(self.mats)
            self.index.append(reps[0])
            self.mats.append(common.palette_material(
                self.sprite, reps[0], TAG + "f" + "-".join(map(str, reps[1:])), metallic=metallic, roughness=rough,
                emission_strength=2.5 if max(reps) >= 120 else (0.25 if FAMILY_OF.get(reps[0]) == "red" and reps[0] >= 112 else 0.0),
                frames=frames))
        return self.slots[key]

    def eye(self, idx, emission=0.0):
        """A slot for the eyes: wet, glossy balls, so the scene's lights put the sprite's highlight
        on them."""
        key = ("eye", idx)
        if key not in self.slots:
            self.slots[key] = len(self.mats)
            self.index.append(idx)
            self.mats.append(common.palette_material(self.sprite, idx, f"{TAG}eye", metallic=0.0, roughness=0.15,
                                                     emission_strength=emission))
        return self.slots[key]

    def bone(self, idx):
        """A slot for the skull's bone (orbit rims, nodules, vertebrae, snout plate): the skull's
        colour, but smooth, so it catches the light as the sprite's bony knobs do."""
        key = ("bone", idx)
        if key not in self.slots:
            self.slots[key] = len(self.mats)
            self.index.append(idx)
            self.mats.append(common.palette_material(self.sprite, idx, f"{TAG}bone", metallic=0.05, roughness=0.36))
        return self.slots[key]

    def glow(self, idx, emission):
        """A slot for the fire in the throat (its own name, so it can glow at its own strength)."""
        key = ("glow", idx, emission)
        if key not in self.slots:
            self.slots[key] = len(self.mats)
            self.index.append(idx)
            self.mats.append(common.palette_material(self.sprite, idx, f"{TAG}fire{round(emission * 10)}",
                                                     metallic=0.0, roughness=0.6, emission_strength=emission))
        return self.slots[key]


def load_grid(phase=None):
    """The whole assembly's pixels (each piece's frame as laid out, or with `phase` the animated
    pieces' frame of that phase) as {(col, row): index}."""
    lay = common.load_sprite(ROOT, PIECES[0])["assemblyLayout"]
    grid = {}
    for e in lay:
        data = common.load_sprite(ROOT, e["model"])
        num = int(e["frame"].split("|")[2])
        if phase is not None and e["model"] in ANIM:
            num = ANIM[e["model"]][phase]
        frame = next(f for f in data["frames"] if f["index"] == num)
        x0, y0 = e["cx"] - 12 - SX0, e["cy"] - 14 - SY0
        for r, row in enumerate(frame["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[(x0 + c, y0 + r)] = v
    return grid


class Painter:
    def __init__(self, grid, pal, phases=None, boxes=()):
        """`phases`: a grid per animation phase (load_grid(phase)); faces in `boxes` (the animated
        pieces, (col0, row0, col1, row1) in assembly px) then take a colour per phase, set by
        resolve() once everything is painted. Shapes (relief) always follow `grid`."""
        self.grid, self.pal, self.phases, self.boxes = grid, pal, phases, boxes
        self.pending = []
        self.adjust = None  # adjust(face, context, rep) -> rep: a shade the model's forms ask for

    def pixel(self, x, y, grid=None):
        c, r = to_px(x, y)
        return (self.grid if grid is None else grid).get((math.floor(c + 0.5), math.floor(r + 0.5)), -1)

    def _lightness(self, c, r, fam, neutral, spread=1.2):
        """The sprite's shade round a point on a 0-6 scale within one palette family (a soft
        average over a few pixels, so it follows the ribs and lumps rather than single pixels);
        pixels of other families count as `neutral`."""
        total = wsum = 0.0
        c0, r0 = math.floor(c + 0.5), math.floor(r + 0.5)
        order = FAMILIES[fam]
        for dc in (-2, -1, 0, 1, 2):
            for dr in (-2, -1, 0, 1, 2):
                rep = rep_of(self.grid.get((c0 + dc, r0 + dr), -1), fam)
                if rep is None:
                    continue
                w = math.exp(-((c0 + dc - c) ** 2 + (r0 + dr - r) ** 2) / spread)
                total += w * (6 * order.index(rep) / (len(order) - 1) if FAMILY_OF.get(rep) == fam else neutral)
                wsum += w
        return total / wsum if wsum else None

    def relief(self, c, r):
        """Height offset from the sprite's shading round a point: its light ribs and knobs stand
        up about 1.5 px, its dark grooves, gaps and sockets sink up to 1.7 px."""
        return RELIEF_AMP * sample_field(self.field(), c, r)

    def field(self):
        """The skull's broad relief from the sprite (design B): the blue family's shade on a 0-6
        scale, other colours neutral, blurred over ~1.6 px so it follows the plates and ribs, not
        single pixels; centred on its mean and clamped to +-1."""
        if getattr(self, "_field", None) is None:
            import numpy as np
            F = np.full((130, 140), np.nan)
            order = FAMILIES["blue"]
            for (c, r), v in self.grid.items():
                rep = rep_of(v, "blue")
                if rep is None or not (0 <= c < 140 and 0 <= r + 10 < 130):
                    continue
                F[r + 10, c] = 6 * order.index(rep) / (len(order) - 1) if FAMILY_OF.get(rep) == "blue" else np.nan
            known = ~np.isnan(F)
            mean = float(np.nanmean(F))
            G = np.where(known, F - mean, 0.0)
            Wt = known.astype(float)
            G, Wt = blur(G, 1.6), blur(Wt, 1.6)
            out = np.where(Wt > 0.2, G / np.maximum(Wt, 1e-6), 0.0) / 1.6
            self._field = np.clip(out, -1.0, 1.0)
        return self._field

    def gum_relief(self, c, r):
        """The gums' lumps: their light pink highlights stand up to 1.2 px, the dark gaps between
        them sink."""
        v = self._lightness(c, r, "gum", 1.5, spread=2.0)
        return 0.0 if v is None else max(-0.06, min(0.1, (v - 2.4) * 0.04))

    def shade(self, f, context, grid=None, fine=False, mid=None):
        """The colour of a face from the sprite pixels under it (a vote over a few points), or None.

        The sprite draws its light into its pixels (dark outline, dark grooves, lit ribs); the game
        lights the model and draws its own outline. So, with `mid` (the part's mid-tone), a face
        takes a soft average of the sprite's shade round it, with outline black left out, pulled
        most of the way to the part's mid-tone (SOFT): the sprite's markings and lighter or darker
        plates still show, its shading and pixel patchwork don't. Lights (the throat's glow and
        fire, LIGHTS) keep their colour."""
        families = FINE_FAMILIES if fine else FAMILIES
        cen = f.calc_center_median()
        reps = [rep_of(self.pixel(p.x, p.y, grid), context, fine)
                for p in [cen] + [cen.lerp(v.co, 0.55) for v in f.verts]]
        reps = [r for r in reps if r is not None]
        if context == "gum" and any(r != DARK["gum"] for r in reps):
            reps = [r for r in reps if r != DARK["gum"]]  # the gums' dark cracks are teeth roots
        if context in ("red", "gum", "blue"):
            # Design B: the throat and gums take their own family only; the fangs drawn over them in
            # the sprite are modelled, so their bone pixels must not paint the flesh.
            reps = [r for r in reps if FAMILY_OF[r] == context]
        if not reps:
            return None
        fams = [FAMILY_OF[r] for r in reps]
        fam = max(set(fams), key=lambda k: (fams.count(k), k == context))
        order = families[fam]
        pos = sorted(order.index(r) for r in reps if FAMILY_OF[r] == fam)
        rep = order[pos[len(pos) // 2]]  # the median shade: no greying mix of light and dark
        if mid is None or fam not in SOFT or rep in LIGHTS or FAMILY_OF.get(mid) != fam:
            return rep
        keep, sigma, skip_outline = SOFT[fam]
        p = float(order.index(rep))
        if sigma > 0:
            c, r = to_px(cen.x, cen.y)
            total = wsum = 0.0
            for dc in (-2, -1, 0, 1, 2):
                for dr in (-2, -1, 0, 1, 2):
                    raw = (self.grid if grid is None else grid).get((math.floor(c + 0.5) + dc,
                                                                     math.floor(r + 0.5) + dr), -1)
                    if raw < 0 or (skip_outline and (raw <= 4 or raw == 48)):
                        continue
                    q = rep_of(raw, fam, fine)
                    if q is None or FAMILY_OF.get(q) != fam or q in LIGHTS:
                        continue
                    w = math.exp(-((math.floor(c + 0.5) + dc - c) ** 2 + (math.floor(r + 0.5) + dr - r) ** 2)
                                 / (2 * sigma * sigma))
                    total += w * order.index(q)
                    wsum += w
            if wsum:
                p = total / wsum
            elif skip_outline:
                p = float(order.index(mid))
        m = order.index(mid)
        return order[max(0, min(len(order) - 1, math.floor(m + (p - m) * keep + 0.5)))]

    def paint(self, faces, context, default=None, min_nz=None):
        """Give each face the shade of the sprite pixels under it (with `phases`, per phase)."""
        for f in faces:
            if min_nz is not None:
                f.normal_update()
                if f.normal.z < min_nz:
                    continue
            # Only the throat and gums change colour with the frames; the skull, brain and claws
            # take one paint everywhere, so the animated pieces' skin matches their neighbours'.
            if self.phases is None or context not in ("red", "gum"):
                rep = self.shade(f, context, mid=default)
                if rep is not None and self.adjust:
                    rep = self.adjust(f, context, rep)
                if rep is None:
                    if default is not None:
                        f.material_index = self.pal(default)
                    continue
                f.material_index = self.pal(rep)
                continue
            keep = self.pal.index[f.material_index] if default is None else default
            c, r = to_px(*f.calc_center_median().xy)
            if not any(c0 <= c <= c1 and r0 <= r <= r1 for c0, r0, c1, r1 in self.boxes):
                rep = self.shade(f, context, mid=default)  # outside the animated pieces: as the static paint
                if rep is not None and self.adjust:
                    rep = self.adjust(f, context, rep)
                f.material_index = self.pal(keep if rep is None else rep)
                continue
            reps = [self.shade(f, context, g, fine=True, mid=default) for g in self.phases]
            reps = [keep if r is None else (self.adjust(f, context, r) if self.adjust else r) for r in reps]
            for k in range(1, PHASES - 1):  # a shade that flickers for one frame (pixel noise)
                if reps[k - 1] == reps[k + 1] != reps[k]:
                    reps[k] = reps[k - 1]
            self.pending.append((f, tuple(reps)))

    def resolve(self):
        """Give the animated faces their colours: the ANIM_COLOURS most used ways of changing
        colour keep their own material, every other face takes the closest of those or of a
        steady colour (by RGB over all phases)."""
        from collections import Counter
        rgb = {int(i): v for i, v in self.pal.sprite["colors"].items()}

        def dist(a, b):
            return sum((x - y) ** 2 for i, j in zip(a, b) for x, y in zip(rgb[i], rgb[j]))
        uses = Counter(reps for _, reps in self.pending if len(set(reps)) > 1)
        kept = [reps for reps, _ in uses.most_common(ANIM_COLOURS)]
        for f, reps in self.pending:
            if len(set(reps)) > 1 and reps not in kept:
                reps = min(kept + [(i,) * PHASES for i in set(reps)], key=lambda t: dist(t, reps))
            f.material_index = self.pal.animated(reps)
        self.pending = []


# --- the shell -----------------------------------------------------------------------------------

def ring_points(poly_a, poly_b, t, n):
    """n points between two outlines (lerp t) along rays from CENTRE."""
    pts = []
    for j in range(n):
        th = 2 * math.pi * (j + 0.5) / n
        d = (math.cos(th), math.sin(th))
        ra, rb = lib.ray_radius(poly_a, CENTRE, th), lib.ray_radius(poly_b, CENTRE, th)
        rr = ra + (rb - ra) * t
        pts.append((CENTRE[0] + d[0] * rr, CENTRE[1] + d[1] * rr))
    return pts


def connect(bm, a, b):
    """Faces between two rings of verts (same count, or a twice as many as b)."""
    faces = []
    if len(b) == 1:
        for j in range(len(a)):
            faces.append(bm.faces.new((a[j], a[(j + 1) % len(a)], b[0])))
    elif len(a) == len(b):
        n = len(a)
        for j in range(n):
            faces.append(bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j])))
    else:
        n = len(b)
        for k in range(n):
            faces.append(bm.faces.new((a[2 * k], a[2 * k + 1], b[k])))
            faces.append(bm.faces.new((a[2 * k + 1], a[(2 * k + 2) % (2 * n)], b[(k + 1) % n], b[k])))
    return faces


def rim(d, depth=6.0):
    """0 at the outline, rising like a quarter ellipse to 1 at `depth` px in."""
    d = min(max(d, 0.0), depth) / depth
    return math.sqrt(max(0.0, 1 - (1 - d) ** 2))


# Raised forms on the skull (left side; mirrored): (col, row, sigma col, sigma row px, height).
KNOBS = [
    (33.5, 44.8, 3.0, 3.0, 0.3),  # the round grey knob below the lowest eye (r30)
    (38.6, 42.6, 2.0, 2.0, 0.22),  # the small knob at the gums' corner (r35)
    (32.5, 61.5, 4.0, 6.0, 0.26),  # the cheek pad beside the lower mouth, under the claw (r49)
    (47.0, 18.5, 3.5, 3.0, 0.12),  # the ribbed brow arcs round the upper eye
]
# Dark pits cut into the armour (left side; mirrored): (col, row, radius px, depth).
PITS = [
    (43.5, 7.4, 3.0, 0.12),  # beside the brain (r9)
    (30.5, 10.4, 3.2, 0.12),  # (r12)
    (52.8, 18.5, 3.5, 0.14),  # the V between the brain and the eye clusters (r16)
    (23.8, 42.8, 4.0, 0.12),  # behind the tentacle roots (r29)
]
EYES = [(37.5, 24.8), (32.3, 32.2), (29.6, 40.6)]  # the glowing eyes, each in a dark socket
SOCKET_R, SOCKET_DEPTH = 4.3, 0.2
# The sockets as modelled (px): the eyeball, the dark cup it sits half sunk in, and the bony rim
# round the cup (its centre line and tube radius).
EYE_R, CUP_R, ORBIT_R, ORBIT_TUBE = 2.3, 3.3, 3.75, 0.85
# Bone nodules: the sprite's light knobs over the brow and cheeks (local maxima of the skull's blue
# shades, left side; mirrored): (col, row, radius px).
NODULES = [(31.0, 2.0, 1.4), (44.0, 14.0, 1.1), (29.0, 16.0, 1.3), (31.0, 18.5, 1.2), (39.5, 19.0, 1.4),
           (47.0, 19.0, 1.0), (45.0, 21.3, 1.2), (42.0, 22.0, 1.0), (48.0, 24.0, 1.0), (31.0, 28.0, 1.3),
           (45.0, 37.0, 1.0), (29.0, 46.0, 1.1), (27.0, 51.0, 1.1), (50.0, 32.3, 1.2), (55.0, 32.3, 1.1)]
# A vertebra-like chain of bone knobs across the cheek above the gums (the sprite's row of light
# knobs at rows 27-31), left side; mirrored, meeting at the centre.
VERTEBRAE = [(41.0, 30.5), (44.3, 27.6), (47.5, 27.3), (50.5, 27.2), (53.6, 28.6), (56.8, 29.9), (60.0, 30.4)]
# The fangs' roots in the gums (left side; mirrored); with the upper lip's lobe at the top centre
# they split the gum ring into lobes (gum_lobe).
FANG_BASES = [(56.4, 41.0), (44.0, 47.6), (40.6, 54.6), (44.6, 63.6), (46.6, 71.4), (52.8, 79.6), (60.0, 82.4)]
# The throat: its rim below the gums' top, the floor it steps down to (in ledges) and the red
# mound round the glowing core that rises from it.
LIP_TOP = 0.72
THROAT_RIM, THROAT_FLOOR, MOUND_TOP = 0.42, -0.5, -0.16
FLOOR_AT = 0.55  # fraction of the way from the gums to the core where the mound starts
LEDGES = 6
LEDGE_NOSE = 0.045  # the rounded lip standing at the front of each ledge
BELLY = 1.45  # the underside's depth (it has to stay under the throat)
# The skull is a domed mass: about 12-13 px high over the brow and the eye ridges, falling to
# about 4 px at the shoulder plates and the lower jaw.
H_LOW, H_HIGH = 0.33, 1.05
OLD_TOP = 0.3  # the skull height the gums' and lip's heights below were set against
RIM_DEPTH = 11.0  # how far in (px) the skull rolls over from its outline


def skull_top(c, r):
    """The skull's dome height (before its relief) at assembly pixel (c, r)."""
    dc = abs(c - AXIS)
    brow = math.exp(-(dc ** 2 / (2 * 26 ** 2) + (r - 14) ** 2 / (2 * 21 ** 2)))
    cheek = 0.85 * math.exp(-((dc - 30) ** 2 / (2 * 9 ** 2) + (r - 38) ** 2 / (2 * 13 ** 2)))
    f = 1 - (1 - brow) * (1 - cheek)
    return H_LOW + (H_HIGH - H_LOW) * f


def lift(c, r):
    """How much higher the skull is at (c, r) than it was: the gums, lip and throat rim rise with it."""
    return skull_top(c, r) - OLD_TOP


def features(c, r):
    """Height added to the skull at assembly pixel (c, r): knobs and cheek pads raised, eye
    sockets and the dark pits between the armour plates cut in."""
    cm = AXIS - abs(c - AXIS)  # left-side column (the head is symmetric)
    dz = 0.0
    for kc, kr, sc, sr, h in KNOBS:
        if kc > AXIS:
            continue
        dz += h * math.exp(-((cm - kc) ** 2 / (2 * sc * sc) + (r - kr) ** 2 / (2 * sr * sr)))
    for pc, pr, rad, depth in PITS:
        d = math.hypot(cm - pc, r - pr) / rad
        if d < 1:
            dz -= depth * (1 - d * d) ** 1.5
    for ec, er in EYES:
        d = math.hypot(cm - ec, r - er) / SOCKET_R
        if d < 1:
            dz -= SOCKET_DEPTH * (1 - d ** 4)
        # A raised rim of bone round each socket, so the eyes sit in hooded orbits.
        dz += 0.07 * math.exp(-((d - 1.15) / 0.22) ** 2)
    # Gill ribs: the sprite's row of vertical light ribs on the flank behind the eyes
    # (columns 18-27, rows 21-38): rounded fins about 1 px proud with dark gaps.
    # (modelled as rib tubes in build_parts; here only the shallow trough they sit in)
    gc, gr = (cm - 22.5) / 5.5, (r - 29.5) / 8.5
    if gc * gc + gr * gr < 1:
        dz -= 0.05 * (1 - gc * gc - gr * gr)
    # Ridges of the carapace (design B: big readable plates): a brow ridge arcing over the eyes from
    # the brain's flank down the outside of the eye column, and a cheek ridge under the lowest eye.
    for path, h, w in ((((50.5, 10.0), (44.0, 15.5), (38.5, 18.8), (33.0, 23.0), (28.5, 29.0), (26.0, 36.0)), 0.13, 1.4),
                       (((36.0, 45.5), (31.5, 48.5), (28.5, 53.5)), 0.1, 1.6),
                       (((45.5, 2.5), (38.0, 3.5), (30.0, 6.5), (22.0, 11.5), (17.5, 16.0)), 0.16, 2.2)):
        dist = min(seg_dist(cm, r, a_, b_) for a_, b_ in zip(path, path[1:]))
        dz += h * math.exp(-(dist / w) ** 2)
    return dz


def seg_dist(c, r, a, b):
    ax, ay = a
    bx, by = b
    ex, ey = bx - ax, by - ay
    t = max(0.0, min(1.0, ((c - ax) * ex + (r - ay) * ey) / (ex * ex + ey * ey)))
    return math.hypot(c - ax - ex * t, r - ay - ey * t)


def throat_z(s, rim_z=THROAT_RIM):
    """Throat height at fraction s of the way from the gums (0) to the core (1): down in ledges to
    the floor, then up over the mound. `rim_z`: the throat's rim height on this ray."""
    if s <= FLOOR_AT:
        t = s / FLOOR_AT
        q = t * LEDGES
        k = min(math.floor(q), LEDGES - 1)
        f = q - k
        # Each ledge: a near-flat tread, a rounded nose, then a steep riser down to the next (the
        # sprite's strong dark ring is the riser in shadow).
        e = min(1.0, max(0.0, (f - 0.55) / 0.4))
        stair = (k + e * e * (3 - 2 * e)) / LEDGES
        g = 0.06 * t + 0.94 * stair
        nose = LEDGE_NOSE * math.exp(-((f - 0.45) / 0.14) ** 2) * (1 - 0.4 * t)
        return rim_z + (THROAT_FLOOR - rim_z) * g + nose
    m = (s - FLOOR_AT) / (1 - FLOOR_AT)
    return THROAT_FLOOR + (MOUND_TOP - THROAT_FLOOR) * math.sin(0.5 * math.pi * m) ** 1.5


def _angles():
    """The fangs' angles round CENTRE (and the upper lip's lobe at the top), and the gaps between."""
    roots = FANG_BASES + [(2 * AXIS - c, r) for c, r in FANG_BASES] + [(AXIS, 40.0)]
    fangs = sorted(math.atan2(r - CENTRE[1], c - CENTRE[0]) for c, r in roots)
    gaps = []  # (middle, half width)
    for a, b in zip(fangs, fangs[1:] + [fangs[0] + 2 * math.pi]):
        gaps.append((0.5 * (a + b), 0.5 * (b - a)))
    return fangs, gaps


FANG_ANGLES, GAP_ANGLES = _angles()


def _adiff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


GUM_SWELL = 10.0  # px of inward swell per unit of gum_lobe at the gums' inner edge


def gum_lobe(c, r):
    """The gums' lobes: a fleshy swelling in each gap between two fangs, a dip at each fang's root."""
    th = math.atan2(r - CENTRE[1], c - CENTRE[0])
    up = sum(math.exp(-(_adiff(th, g) / (0.6 * half)) ** 2) for g, half in GAP_ANGLES)
    down = sum(math.exp(-(_adiff(th, f) / 0.07) ** 2) for f in FANG_ANGLES)
    return 0.22 * up - 0.1 * down


OUT_INSET = 0.8  # px: the outline sits on the inner edge of the sprite's ink ring (D74)


def offset_poly(poly, d):
    """The closed polygon moved `d` px inward (mitred vertex offset, capped at 2.5 d)."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sgn = 1.0 if area > 0 else -1.0
    out = []
    for i in range(n):
        (x0, y0), (x1, y1), (x2, y2) = poly[i - 1], poly[i], poly[(i + 1) % n]
        normals = []
        for ax, ay, bx, by in ((x0, y0, x1, y1), (x1, y1, x2, y2)):
            ex, ey = bx - ax, by - ay
            L = math.hypot(ex, ey) or 1.0
            normals.append((-ey / L * sgn, ex / L * sgn))  # inward (left of a CCW edge)
        mx, my = normals[0][0] + normals[1][0], normals[0][1] + normals[1][1]
        L = math.hypot(mx, my)
        if L < 1e-6:
            mx, my, L = normals[1][0], normals[1][1], 1.0
        mx, my = mx / L, my / L
        cosh = max(0.4, mx * normals[1][0] + my * normals[1][1])
        out.append((x1 + mx * d / cosh, y1 + my * d / cosh))
    return out


def build_shell(bm, painter):
    out = offset_poly(lib.mirror_poly(OUT_LEFT, AXIS), OUT_INSET)
    gum_out = lib.mirror_poly(GUM_OUT_LEFT, AXIS)
    gum_in = lib.mirror_poly(GUM_IN_LEFT, AXIS)
    N, M, K = 192, 96, 48  # ring resolution: skin, gums, throat
    edge_z = -0.03

    def verts(pts, zs):
        return [bm.verts.new((X(c), Y(r), z)) for (c, r), z in zip(pts, zs)]

    dome = skull_top

    edge = ring_points(out, out, 0.0, N)
    edge_v = verts(edge, [edge_z] * N)

    # Top: from the outline in to the gums, with the sprite's light ribs raised and its dark
    # grooves, pits and the eye sockets cut in, and the knobs and cheek pads raised.
    skin = []
    prev = edge_v
    us = [0.02, 0.05, 0.09] + [0.14 + 0.86 * i / 14 for i in range(15)]
    for u in us:
        pts = ring_points(out, gum_out, u, N)
        zs = []
        for (c, r), (ec, er) in zip(pts, edge):
            # The top edge (beyond the screen) is cut off by the pieces, so the dome runs on there.
            k = 1.0 if er < -7.5 else rim(math.hypot(c - ec, r - er), RIM_DEPTH)
            zs.append(edge_z + (dome(c, r) + features(c, r) - edge_z) * k
                      + painter.relief(c, r) * k * (1 - u ** 4))
        ring = verts(pts, zs)
        skin += connect(bm, prev, ring)
        prev = ring

    # The gums: a rounded ridge of fleshy lumps standing well above the armour, rolling over
    # into the throat.
    gums = []
    for v, z in ((0.08, 0.5), (0.22, 0.64), (0.38, LIP_TOP), (0.55, 0.71), (0.72, 0.64), (0.87, 0.54),
                 (1.0, THROAT_RIM)):
        pts = ring_points(gum_out, gum_in, v, M)
        # Each lobe also swells in over the throat a little, so the gums' inner edge is scalloped.
        pts = [(c + (CENTRE[0] - c) * k, r + (CENTRE[1] - r) * k) for c, r in pts
               for k in [GUM_SWELL * gum_lobe(c, r) * v * v / max(1.0, math.hypot(c - CENTRE[0], r - CENTRE[1]))]]
        zs = [z + lift(c, r) + (painter.gum_relief(c, r) + gum_lobe(c, r)) * math.sin(math.pi * v) ** 0.7
              for c, r in pts]
        ring = verts(pts, zs)
        gums += connect(bm, prev, ring)
        prev = ring

    # The throat: a tapered bowl stepping down in ledges (the sprite's dark red rings) to its floor,
    # then a red mound round the glowing core.
    rim_pts = ring_points(gum_in, gum_in, 0.0, K)
    rim_pts = [(c + (CENTRE[0] - c) * k, r + (CENTRE[1] - r) * k) for c, r in rim_pts
               for k in [GUM_SWELL * gum_lobe(c, r) / max(1.0, math.hypot(c - CENTRE[0], r - CENTRE[1]))]]
    rim_zs = [THROAT_RIM + lift(c, r) for c, r in rim_pts]
    throat = []
    ss = [FLOOR_AT * i / 30 for i in range(1, 31)] + [FLOOR_AT + (1 - FLOOR_AT) * i / 7 for i in range(1, 7)]
    for s in ss:
        pts = [(c + (CORE[0] - c) * s, r + (CORE[1] - r) * s) for c, r in rim_pts]
        ring = verts(pts, [throat_z(s, rz) for rz in rim_zs])
        throat += connect(bm, prev, ring)
        prev = ring
    tip = [bm.verts.new((X(CORE[0]), Y(CORE[1]), MOUND_TOP))]
    throat += connect(bm, prev, tip)

    # Underside: a rounded belly, deep enough to close under the throat.
    belly = []
    prev = edge_v
    for u, n in ((0.03, M), (0.1, K), (0.25, K // 2), (0.5, K // 2), (0.75, K // 2)):
        pts = ring_points(out, out, 0.0, n)
        rim_ref = pts
        pts = [(CENTRE[0] + (c - CENTRE[0]) * (1 - u), CENTRE[1] + (r - CENTRE[1]) * (1 - u)) for c, r in pts]
        # Deep only under the throat; elsewhere (the cut edges at the top of the screen) shallow.
        # Design B: one round, closed belly under the whole head (a skull's underside), no detail.
        zs = [edge_z - BELLY * rim(math.hypot(c - ec, r - er), 26.0) for (c, r), (ec, er) in zip(pts, rim_ref)]
        ring = verts(pts, zs)
        belly += connect(bm, prev, ring)
        prev = ring
    belly += connect(bm, prev, [bm.verts.new((X(CENTRE[0]), Y(CENTRE[1]), edge_z - BELLY - 0.02))])

    for f in skin + gums + throat + belly:
        f.smooth = True

    def adjust(f, context, rep):
        # The gum lobes take the sprite's light pink lumps (68 at least), the fangs' roots its darker
        # pink, so each lobe reads between its two fangs.
        if context != "gum":
            return rep
        c, r = to_px(*f.calc_center_median().xy)
        lobe = gum_lobe(c, r)
        order = FAMILIES["gum"]
        if lobe > 0.08:
            return 68 if order.index(rep) <= order.index(68) else rep  # the lobe: light pink
        if lobe < 0.0:
            return 65  # the crease at each fang's root
        return 67  # the lobe's flanks
        return rep
    painter.adjust = adjust
    painter.paint(skin, "blue", default=99)
    # The eye sockets: dark cups (the bone rim and the eye are modelled on top in build_parts).
    for f in skin:
        c, r = to_px(*f.calc_center_median().xy)
        cm = AXIS - abs(c - AXIS)
        if any(math.hypot(cm - ec, r - er) < SOCKET_R * 0.85 for ec, er in EYES):
            f.material_index = painter.pal(96)
    painter.paint(gums, "gum", default=68)
    painter.paint(throat, "red", default=113)
    for f in belly:
        f.material_index = painter.pal(97)


# --- parts on the shell ---------------------------------------------------------------------------

class Surface:
    def __init__(self, bm):
        self.tree = BVHTree.FromBMesh(bm)

    def z(self, c, r, default=0.0):
        hit = self.tree.ray_cast(Vector((X(c), Y(r), 3.0)), Vector((0, 0, -1)))
        return hit[0].z if hit[0] is not None else default


def P(c, r, z):
    return (X(c), Y(r), z)


def mirrored(fn):
    """Call fn(sign, mirror) for the left part and its mirror image on the right."""
    fn(lambda c: c)
    fn(lambda c: 2 * AXIS - c)


def build_parts(bm, painter, surf, phase=None):
    """Everything on the shell. `phase` None: all of it; "base": all but the teeth and the fire (the
    head every piece shares); "teeth": only the teeth and the fire as the static pieces show them;
    0-4: only the teeth and the fire as on that phase (FANGS, FIRE)."""
    pal = painter.pal
    body = phase is None or phase == "base"
    teeth = phase != "base"
    anim = isinstance(phase, int)

    def fang(key, default_mat):
        """(length factor, material slot) of a tooth on this phase."""
        if not anim:
            return 1.0, default_mat
        k, shade = FANGS[key][phase]
        return k, pal(shade, fam="tooth")

    # Brain: a lumpy purple dome on top of the skull (columns 50-76, rows 0-20 and on above).
    def bump(dx, dy, dz):
        # Design B: a brain, read at a glance: two lobes with a groove down the middle and rounded
        # gyri (|sin| folds, so the creases are sharp and the folds round).
        fold = abs(math.sin(9 * dx + 2.0 * math.sin(7 * dy))) + abs(math.sin(8 * dy + 1.5 * math.sin(6 * dx)))
        groove = 0.10 * math.exp(-(dx / 0.08) ** 2) * max(dz, 0) ** 0.5
        return 1 + (0.05 * (fold - 1.2)) * (0.3 + max(dz, 0)) - groove
    if body:
        # A round dome about 8 px above the armour (its lower half, inside the skull, left out).
        # Its base sits a little into the skull's dome, so it stands about 8 px above it.
        faces = half_blob(bm, P(AXIS, 4.0, skull_top(AXIS, 4.0) - 0.12), (13.6 * PX, 17.0 * PX, 0.8), segments=36,
                          rings=10, mat=pal(83), bump=bump)

        painter.paint(faces, "purple", default=83, min_nz=0.0)
        # Bony snout plate between the brain and the upper lip (rows 19-27): a light grey plate of
        # two rounded lobes with a groove down the middle (the sprite's two bright pads), on a
        # lower bridge running up under the brain.
        faces = lib.blob(bm, P(AXIS, 22.6, skull_top(AXIS, 22.6) - 0.06), (6.4 * PX, 2.8 * PX, 0.22), segments=16,
                         rings=6, mat=pal(102))
        for c in (AXIS - 2.8, AXIS + 2.8):
            faces += lib.blob(bm, P(c, 25.0, skull_top(c, 25.0) - 0.04), (3.5 * PX, 3.1 * PX, 0.22),
                              segments=14, rings=6, mat=pal(102))
        for f in faces:
            f.material_index = pal.bone(102)

        # The central lobe of the upper lip, hanging from the gums' ridge over the throat and ending
        # in a short dark tooth (column 63, rows 37-49).
        faces = lib.tube(bm, [P(AXIS, r, z + lift(AXIS, r)) for r, z in
                              ((36.5, LIP_TOP - 0.06), (40.0, LIP_TOP - 0.1), (43.2, 0.5), (44.6, 0.42))], [2.2 * PX, 2.3 * PX, 1.9 * PX, 1.0 * PX], sides=10,
                         mat=pal(68), flat=0.8)
        painter.paint(faces, "gum", default=68, min_nz=0.0)
    if teeth:
        k, mat = fang("knob", pal(163, fam="tooth") if not anim else None)
        z0 = 0.44 + lift(AXIS, 44.0)
        lib.tube(bm, [P(AXIS, 44.0, z0), P(AXIS, 44.0 + 2.5 * k, z0 - 0.12 * k),
                      P(AXIS, 44.0 + 5.5 * k, z0 - 0.32 * k)],
                 [1.5 * PX, 1.1 * PX, 0.0], sides=8, mat=mat)

    def side(m):
        if body:
            # Eyes: a red ball with a glowing centre, half sunk in a dark cup ringed by a raised bony
            # orbit (three down each side).
            for c, r in EYES:
                z = surf.z(m(c), r)
                lib.blob(bm, P(m(c), r, z - 0.02), (CUP_R * PX, CUP_R * PX, 0.07), segments=10, rings=4,
                         mat=pal.bone(96))
                orbit = []
                for j in range(13):
                    a = 2 * math.pi * j / 12
                    oc, orr = c + ORBIT_R * math.cos(a), r + ORBIT_R * math.sin(a)
                    orbit.append(P(m(oc), orr, surf.z(m(oc), orr) + 0.02 + 0.03 * max(0.0, -math.sin(a))))
                lib.tube(bm, orbit, [ORBIT_TUBE * PX] * len(orbit), sides=6, mat=pal.bone(101), flat=0.9)
                lib.blob(bm, P(m(c), r, z + 0.02), (EYE_R * PX, EYE_R * PX, 0.15), segments=10, rings=5,
                         mat=pal.eye(114))
                lib.blob(bm, P(m(c), r - 0.1, z + 0.07), (1.6 * PX, 1.6 * PX, 0.125), segments=8, rings=4,
                         mat=pal.eye(117))
                lib.blob(bm, P(m(c), r - 0.2, z + 0.12), (0.95 * PX, 0.95 * PX, 0.085), segments=6, rings=3,
                         mat=pal.eye(121, emission=4.0))
            # Bone nodules over the brow and cheeks, and the vertebra chain above the gums.
            for c, r, rad in NODULES:
                z = surf.z(m(c), r)
                lib.blob(bm, P(m(c), r, z - 0.04), (1.3 * rad * PX, 1.2 * rad * PX, 0.05 + 0.03 * rad), segments=8, rings=3,
                         mat=pal.bone(101 if rad < 1.2 else 102))
            for i, (c, r) in enumerate(VERTEBRAE):
                z = surf.z(m(c), r)
                big = i % 2 == 0
                lib.blob(bm, P(m(c), r, z - 0.03), ((1.5 if big else 1.15) * PX, (1.25 if big else 1.0) * PX,
                                                    0.13 if big else 0.09),
                         segments=8, rings=4, mat=pal.bone(102 if big else 101))

        # Fangs round the gums, pointing in and down into the throat: (base, tip, radius px).
        for i, ((bc, br), (tc, tr), rad) in enumerate(zip(FANG_BASES, (
                (57.8, 49.6), (50.6, 49.3), (48.6, 56.6), (49.6, 63.2), (51.6, 70.6), (54.6, 75.8), (60.3, 77.0)),
                (1.5, 1.6, 1.6, 1.3, 1.2, 1.1, 1.1))):
            if not teeth:
                break
            k, mat = fang(("L" if m(0) == 0 else "R", i), pal(165, fam="tooth") if not anim else None)
            if k != 1.0:
                tc, tr = bc + (tc - bc) * k, br + (tr - br) * k
            # Rooted in the gums' inner slope, hanging down over the throat.
            zb = surf.z(m(bc), br) - 0.04
            mc, mr = bc + (tc - bc) * 0.45, br + (tr - br) * 0.45
            lib.tube(bm, [P(m(bc), br, zb), P(m(mc), mr, zb - 0.1 * k), P(m(tc), tr, zb - 0.3 * k)],
                     [(1.3 * rad + 0.6) * PX, (1.3 * rad + 0.6) * 0.72 * PX, 0.0], sides=8, mat=mat)

        if not body:
            return
        # Gill ribs: four curved bone fins in a trough on the flank behind the eyes (the sprite's
        # light vertical ribs, columns 18-27, rows 21-38).
        for i, gc in enumerate((19.2, 21.6, 24.0, 26.4)):
            half = 7.5 - 1.2 * abs(i - 1.5)
            rows = [29.5 - half + 2 * half * t / 5 for t in range(6)]
            pts = [P(m(gc + 0.6 * math.sin(math.pi * t / 5)), rr, surf.z(m(gc), rr) - 0.02 + 0.03 * math.sin(math.pi * t / 5))
                   for t, rr in enumerate(rows)]
            faces = lib.tube(bm, pts, [0.3 * PX, 0.75 * PX, 0.85 * PX, 0.85 * PX, 0.75 * PX, 0.3 * PX], sides=6,
                             mat=pal(101), flat=1.1)

        # Tentacles hanging off the flanks, round and swelling to a ball at their tips: (col, row,
        # radius px), measured on the sprite with its dark outline.
        for path in ([(11.5, 39.5, 1.8), (9.5, 41.5, 1.8), (8.5, 43.5, 2.0), (8.5, 45.0, 1.5), (8.5, 45.8, 0.0)],
                     [(15.5, 44.0, 1.8), (13.0, 46.5, 2.2), (11.5, 48.8, 2.3), (10.8, 51.0, 2.2), (10.5, 52.8, 1.6),
                      (10.5, 53.8, 0.0)],
                     [(21.5, 46.5, 1.9), (18.5, 49.0, 1.9), (16.8, 51.5, 1.9), (16.0, 54.0, 2.2), (16.0, 56.2, 2.5),
                      (16.2, 58.0, 1.6), (16.2, 58.9, 0.0)],
                     [(26.5, 53.0, 2.0), (23.0, 56.5, 1.8), (21.0, 59.5, 1.9), (20.6, 62.0, 2.0), (21.4, 64.8, 2.8),
                      (21.4, 66.8, 2.4), (21.2, 68.2, 1.2), (21.2, 68.8, 0.0)]):
            n = len(path)
            # Rooted in the skull's flank, arching out and drooping past its rim (design B: they hang).
            z0 = surf.z(m(path[0][0]), path[0][1], 0.1) - 0.1
            pts = [P(m(c), r, z0 + 0.06 * math.sin(math.pi * min(1, 2 * i / (n - 1))) - (z0 + 0.32) * (i / (n - 1)) ** 1.6)
                   for i, (c, r, _) in enumerate(path)]
            faces = lib.tube(bm, pts, [max(0.0, rr - 0.85) * PX if rr else 0.0 for _, _, rr in path], sides=10,
                             mat=pal(99))
            painter.paint(faces, "blue", default=99, min_nz=-0.2)

        # Purple claw low on each side, sweeping down and out (columns 27-38, rows 64-77).
        # Centres and half-widths measured on the sprite's purple, row by row.
        path = [(35.5, 65.2, 0.3, 2.8), (33.0, 68.5, 0.24, 3.3), (30.8, 71.5, 0.15, 2.6), (28.8, 74.0, 0.08, 2.0),
                (27.6, 76.0, 0.04, 1.3), (27.0, 77.8, 0.03, 0.0)]
        # A round, tapering horn standing on the cheek pad: about 5 px tall at its root.
        faces = lib.tube(bm, [P(m(c), r, max(z, surf.z(m(c), r, z) - 0.03 + 0.55 * w * PX)) for c, r, z, w in path],
                         [w * PX for *_, w in path], sides=10, mat=pal(84, fam="purple"), flat=1.0)
        pass  # design B: the claw one flat colour (84), lit by the game

    mirrored(side)

    if body:
        # Chin spike (column 63, rows 89-94).
        faces = lib.tube(bm, [P(AXIS, 88.0, 0.2), P(AXIS, 91.0, 0.12), P(AXIS, 93.0, 0.06), P(AXIS, 94.2, 0.02),
                              P(AXIS, 95.0, 0.0)],
                         [2.2 * PX, 2.5 * PX, 2.3 * PX, 1.4 * PX, 0.0], sides=8, mat=pal(103))
        painter.paint(faces, "blue", default=103, min_nz=-0.2)

    if phase is None or phase == "teeth":
        # The glowing core on its mound at the bottom of the throat (as phase 2's fire).
        fire(bm, FIRE[2], lambda idx, emission: pal(idx, emission=emission) if emission else pal(idx))
    elif anim:
        # The fire rising from the core on this phase, from its red outside in to its hottest heart.
        fire(bm, FIRE[phase], pal.glow)


def fire(bm, blobs, mat):
    """The core's fire: round orbs on the mound at the bottom of the throat, each smaller one
    standing a little proud of the one round it, so the hottest heart shows on top."""
    for i, (idx, c, r, _z, rx, ry, _rz, emission) in enumerate(blobs):
        rz = 0.6 * min(rx, ry) * PX
        top = MOUND_TOP + 0.1 + 0.05 * i
        lib.blob(bm, P(c, r, top - rz), (rx * PX, ry * PX, rz), segments=14, rings=7, mat=mat(idx, emission))


def half_blob(bm, centre, radii, segments=16, rings=8, mat=0, bump=None):
    """The upper half of an ellipsoid (rx, ry, rz) at centre, closed by a flat base; bump(dx, dy, dz)
    -> radius scale makes it lumpy. Returns its faces."""
    cx, cy, cz = centre
    rx, ry, rz = radii

    def vert(d):
        k = bump(*d) if bump else 1.0
        return bm.verts.new((cx + rx * d[0] * k, cy + ry * d[1] * k, cz + rz * d[2] * k))
    top = vert((0, 0, 1))
    ring_verts = []
    for i in range(1, rings + 1):
        phi = 0.5 * math.pi * i / rings
        ring_verts.append([vert((math.sin(phi) * math.cos(2 * math.pi * j / segments),
                                 math.sin(phi) * math.sin(2 * math.pi * j / segments), math.cos(phi)))
                           for j in range(segments)])
    faces = []
    for j in range(segments):
        faces.append(bm.faces.new((top, ring_verts[0][j], ring_verts[0][(j + 1) % segments])))
    for a, b in zip(ring_verts, ring_verts[1:]):
        for j in range(segments):
            k = (j + 1) % segments
            faces.append(bm.faces.new((a[j], b[j], b[k], a[k])))
    faces.append(bm.faces.new(list(reversed(ring_verts[-1]))))
    for f in faces:
        f.material_index = mat
        f.smooth = True
    return faces


def build(sprite):
    """The whole head as one mesh (shell, brain, eyes, tentacles, claws; no teeth, no fire), painted
    once: every piece is cut from it, so the animated pieces' skin is the static pieces' skin. Only
    the throat's and gums' faces inside the animated pieces take a colour per phase. The teeth and
    the fire are separate: as the static pieces show them, and per phase for the animated pieces.
    Returns (head, static teeth, [teeth per phase])."""
    coll = common.reset_collection(NAME)
    global LAST_PAL
    pal = LAST_PAL = Palette(sprite)
    boxes = [(e["cx"] - 12 - SX0 - 0.5, e["cy"] - 14 - SY0 - 0.5, e["cx"] + 12 - SX0 - 0.5, e["cy"] + 14 - SY0 - 0.5)
             for e in sprite["assemblyLayout"] if e["model"] in ANIM]
    painter = Painter(load_grid(), pal, phases=[load_grid(k) for k in range(PHASES)], boxes=boxes)
    bm = bmesh.new()
    build_shell(bm, painter)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    surf = Surface(bm)
    build_parts(bm, painter, surf, phase="base")
    painter.resolve()
    head = lib.to_object(NAME, bm, pal.mats, coll)
    tbm = bmesh.new()
    build_parts(tbm, Painter(painter.grid, pal), surf, phase="teeth")
    teeth = lib.to_object(f"{NAME}-teeth", tbm, pal.mats, coll)
    parts = []
    for k in range(PHASES):
        pbm = bmesh.new()
        build_parts(pbm, Painter(painter.grid, pal), surf, phase=k)
        parts.append(lib.to_object(f"{NAME}-phase{k}", pbm, pal.mats, coll))
    # Every object gets the full material list (later ones were made after the head).
    for o in (head, teeth, *parts):
        while len(o.data.materials) < len(pal.mats):
            o.data.materials.append(pal.mats[len(o.data.materials)])
    return head, teeth, parts


def merged_sprite():
    data = common.load_sprite(ROOT, PIECES[0])
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def composite_png(out):
    """The whole head's sprite as one image, 2 image px per sprite px, padded to the 240 x 280
    (size 10) frame render_preview expects, with Blender's origin in the middle."""
    import numpy as np
    sprite = merged_sprite()
    img = np.zeros((280, 240, 4), dtype=np.float32)
    for (c, r), v in load_grid().items():
        x, y = 2 * c - 7, 2 * (r + 22)  # column 63's centre and row 47.5 land on the image centre
        if 0 <= x and x + 2 <= 240 and 0 <= y and y + 2 <= 280:
            img[y:y + 2, x:x + 2] = [*(ch / 255 for ch in sprite["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 240, 280, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def flat_cuts(obj):
    """Shade the faces that close a piece where split_assembly cut it flat, with sharp edges, so the
    smooth skin's normals next to a cut aren't bent sideways (which drew a dark crack along every
    seam between pieces)."""
    hw, hh, eps = 1.0, 14 / 12, 1e-4
    me = obj.data
    dark = next((i for i, m in enumerate(me.materials) if m.name.startswith("pal_96_")), None)
    sharp = set()
    for poly in me.polygons:
        cos = [me.vertices[i].co for i in poly.vertices]
        if any(all(abs(abs(co[a]) - h) < eps for co in cos) for a, h in ((0, hw), (1, hh))):
            poly.use_smooth = False
            if dark is not None:
                poly.material_index = dark  # in shadow where the head runs on past the screen edge
            sharp.update(poly.edge_keys)
    for e in me.edges:
        if e.key in sharp:
            e.use_edge_sharp = True
    me.update()




# --- texture: AO / roughness bake (no concept projection; D65) -------------------------------------

TILE = 512  # px of baked colour map per piece (the roughness map is half that)
TILES_X, TILES_Y = 6, 4  # the bake atlas: one tile per piece (24 pieces)
TILE_PAD = 6  # px kept clear round each tile's islands


def bake_maps(objs, out_dir, samples=48):
    """A Cycles bake of two maps into one atlas (each piece in its own tile, see unwrap_tiles): a grey
    colour multiplier (occlusion at two scales) and roughness/metallic; wired into every non-glowing
    palette material (Base Color = map x palette colour), as usp_talon.bake_maps does. `objs` are
    baked together, as they stand in the scene (only they render, so nothing else occludes them).
    Returns (colour atlas, roughness atlas, [(colour node, roughness node)])."""
    size = (TILES_X * TILE, TILES_Y * TILE)
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
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
    except Exception as err:
        print(f"{NAME}: no GPU bake", err)
    hidden = {}
    for o in bpy.context.scene.objects:
        hidden[o.name] = o.hide_render
        o.hide_render = o.type == "MESH" and o not in objs
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.hide_render = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    col_img = bpy.data.images.new(f"{TAG}_colour", size[0], size[1], alpha=False)
    rm_img = bpy.data.images.new(f"{TAG}_rm", size[0] // 2, size[1] // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = []
    for o in objs:
        for m in o.data.materials:
            if m not in mats:
                mats.append(m)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
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
        ao_s.inputs["Distance"].default_value = 0.06
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 16
        ao_l.inputs["Distance"].default_value = 0.4
        # No bevel edge lift: the pieces are baked cut, and their cut caps would light a line
        # along every seam. The head is organic; its forms carry it.
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.6, math_("MULTIPLY", ao_l.outputs["AO"], 0.4)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", 0.45, math_("MULTIPLY", occl, 0.62)), 1.0)
            nt.links.new(v, em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3))
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
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
    for name, h in hidden.items():
        o = bpy.context.scene.objects.get(name)
        if o is not None:
            o.hide_render = h
    nodes = []
    for m in mats:
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        if bsdf.inputs["Emission Strength"].default_value > 0:
            continue  # glows keep their flat palette colour
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
        nodes.append((ct, rt))
    return col_img, rm_img, nodes


def unwrap_tiles(groups):
    """UVs ("bake") for each piece's objects together, packed into that piece's tile of the atlas:
    groups is [[objects of a piece]] in tile order."""
    W, H = TILES_X * TILE, TILES_Y * TILE
    for i, objs in enumerate(groups):
        tx, ty = i % TILES_X, i // TILES_X
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in objs:
            uv = o.data.uv_layers.get("bake") or o.data.uv_layers.new(name="bake")
            o.data.uv_layers.active = uv
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, scale_to_bounds=False)
        try:
            bpy.ops.uv.pack_islands(margin_method="FRACTION", margin=0.012)
        except TypeError:
            bpy.ops.uv.pack_islands(margin=0.012)
        bpy.ops.object.mode_set(mode="OBJECT")
        inner = TILE - 2 * TILE_PAD
        for o in objs:
            for d in o.data.uv_layers["bake"].data:
                u, v = d.uv
                d.uv = ((tx * TILE + TILE_PAD + u * inner) / W, (ty * TILE + TILE_PAD + v * inner) / H)


def crop_tile(img, i, scale, out_dir, name):
    """Tile i of an atlas as its own image (saved, so the exporter can read it)."""
    import numpy as np
    W, H = img.size
    arr = np.empty(W * H * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    arr = arr.reshape(H, W, 4)
    t = TILE // scale
    tx, ty = i % TILES_X, i // TILES_X
    tile = np.ascontiguousarray(arr[ty * t:(ty + 1) * t, tx * t:(tx + 1) * t])
    out = bpy.data.images.new(name, t, t, alpha=False)
    if img.colorspace_settings.name == "Non-Color":
        out.colorspace_settings.name = "Non-Color"
    out.pixels.foreach_set(tile.ravel())
    out.filepath_raw = str(Path(out_dir) / f"{name}.png")
    out.file_format = "PNG"
    out.save()
    return out


def tile_uvs(objs, i, to_tile):
    """Move the objects' bake UVs from the atlas into tile i's own 0-1 square (or back)."""
    W, H = TILES_X * TILE, TILES_Y * TILE
    tx, ty = i % TILES_X, i // TILES_X
    for o in objs:
        lay = o.data.uv_layers.get("bake")
        if lay is None:
            continue
        for d in lay.data:
            u, v = d.uv
            if to_tile:
                d.uv = ((u * W - tx * TILE) / TILE, (v * H - ty * TILE) / TILE)
            else:
                d.uv = ((tx * TILE + u * TILE) / W, (ty * TILE + v * TILE) / H)


def combine(objs, offsets, name, coll):
    """One mesh of `objs`, each moved by its X offset (so they bake into one atlas without
    shading each other), with the union of their materials."""
    mats, slot = [], {}
    for o in objs:
        for m in o.data.materials:
            if m.name not in slot:
                slot[m.name] = len(mats)
                mats.append(m)
    bm = bmesh.new()
    for o, dx in zip(objs, offsets):
        tmp = bmesh.new()
        tmp.from_mesh(o.data)
        remap = [slot[m.name] for m in o.data.materials]
        for f in tmp.faces:
            f.material_index = remap[f.material_index] if remap else 0
        bmesh.ops.translate(tmp, vec=(dx, 0, 0), verts=tmp.verts)
        me = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def split_open(obj, layout, coll, suffix):
    """split_assembly without capping the cuts (for the outline shells)."""
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


def densify(obj, min_len):
    """Split the piece's edges longer than `min_len` (units) once: newshn-85 is the head's own mesh
    cut out, only a fifth of the way as dense as the pieces beside it, so its rim showed facets."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    edges = [e for e in bm.edges if e.calc_length() > min_len]
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)



# --- the back of the skull (design A + judge's grafts) ---------------------------------------------

import os  # noqa: E402
from collections import Counter  # noqa: E402

GYGES_DATA = Path(os.environ.get("GYGES_DATA", "/Users/dlomibao/projects/tyrian-scratch/gyges-back"))
GRID = json.loads((GYGES_DATA / "grid.json").read_text())
FIELDS = np.load(GYGES_DATA / "fields.npz")
NEW = ["newshn-3", "newshn-5", "newshn-7", "newshn-41", "newshn-43", "newshn-45"]
ALL_NEW = NEW + ["newshn-85"]
DAMAGE = {"newshn-85": 18, "newshn-41": 51, "newshn-43": 53, "newshn-45": 55}
ALL_PIECES = PIECES + ALL_NEW  # bake tile order
LAST_PAL = None
G = 0.5  # grid step, px
EDGE_Z = -0.03
SEAM = -0.5  # the boundary row (pixel-centre coords) between rows -1 and 0
BLEND_FROM = -3.0  # the back's own forms give way to the shipped surface from here to the seam
RIM_OUT, RIM_HOLE = 7.5, 1.4  # px: the carapace rolls over at its outline; slots cut steep
SMAX_K = 0.75  # px: the crease width where two forms meet
BACK_BELLY = 1.0  # units: depth of the underside


# --- the fields from prep.py -------------------------------------------------------------------

def _sample(a, c, r):
    s = int(FIELDS["S"])
    u = (c - int(FIELDS["col0"])) * s + (s - 1) / 2
    v = (r - int(FIELDS["row0"])) * s + (s - 1) / 2
    h, w = a.shape
    x0, y0 = int(math.floor(u)), int(math.floor(v))
    fx, fy = u - x0, v - y0

    def at(y, x):
        return float(a[min(max(y, 0), h - 1), min(max(x, 0), w - 1)])
    return ((at(y0, x0) * (1 - fx) + at(y0, x0 + 1) * fx) * (1 - fy)
            + (at(y0 + 1, x0) * (1 - fx) + at(y0 + 1, x0 + 1) * fx) * fy)


PHI_CUT, PHI_EXT = FIELDS["phi_cut"], FIELDS["phi_ext"]


def phi_cut(c, r):
    return _sample(PHI_CUT, c, r)


def phi_ext(c, r):
    return _sample(PHI_EXT, c, r)


# --- the forms (px; left half, mirrored about col 63) --------------------------------------------

def dome(cm, r, cx, cy, rx, ry, top, p=2.0):
    """An elliptic dome `top` px high: a superellipse cross-section (p > 2 flattens the crown)."""
    q2 = ((cm - cx) / rx) ** 2 + ((r - cy) / ry) ** 2
    if q2 >= 1.0:
        return -99.0
    return top * (1.0 - q2 ** (p / 2)) ** 0.5


# Domes: (part, cx, cy, rx, ry, top px, superellipse p). Measured on the sprite (A/work/sprite_zoom.png).
DOMES = [
    ("crown", 63.0, -36.0, 33.0, 15.0, 7.4, 2.0),       # the carapace over the back of the skull
    ("cap", 63.0, -50.8, 13.5, 4.6, 6.6, 2.4),          # the condyles' cap at the top edge
    ("condyle", 58.0, -51.2, 5.2, 4.3, 9.2, 2.0),       # twin occipital condyles (neck joint)
    ("hood", 51.4, -38.6, 6.6, 7.6, 11.6, 2.4),         # the hood lobe beside the cord
    ("knob", 31.8, -33.6, 3.9, 3.4, 8.2, 2.0),          # the shoulder knob outside the foramen
    ("plate_up", 31.6, -22.6, 11.2, 7.4, 10.6, 2.6),    # upper side plate
    ("plate_low", 36.2, -6.6, 12.6, 7.4, 11.4, 2.6),    # lower side plate
    ("strip", 45.6, -23.0, 3.2, 7.2, 9.0, 2.6),         # the narrow plate between the upper plate and the brain
]
BRAIN = [("brain_up", 63.0, -21.8, 16.6, 7.8, 15.5), ("brain_low", 63.0, -7.6, 13.2, 8.4, 16.5)]
CORD = (63.0, -47.5, -27.0)  # col, top row, bottom row (it dives into the upper lobe)
FORAMEN = (41.8, -35.4, 4.1, 1.5, 9.8)  # centre col, row, ring radius, tube radius, top px
# Grooves: (path, width px, depth px), left side.
GROOVES = [
    (((24.0, -15.6), (31.0, -16.0), (38.0, -15.8), (44.5, -15.2)), 0.9, 2.2),  # between the side plates
    (((29.0, -30.8), (36.0, -31.2), (41.0, -31.4), (47.0, -30.8)), 0.8, 2.0),  # under the foramen
    (((57.6, -46.0), (58.2, -38.0), (58.6, -31.0)), 0.8, 1.8),                  # beside the cord
    (((47.0, -47.4), (55.0, -47.2), (61.0, -47.4)), 0.7, 1.6),                  # under the condyle cap
    (((62.6, -54.0), (62.6, -48.0)), 0.6, 3.2),                                # between the condyles
]
PURPLE_PARTS = {"brain_up", "brain_low", "cord", "rim", "membrane"}


def cord_z(cm, r):
    top, bot = CORD[1], CORD[2]
    if not (top - 1.2 <= r <= bot + 3.0):
        return -99.0
    t = min(1.0, max(0.0, (r - top) / (bot - top)))
    R = 3.4 + 1.2 * t ** 0.6
    # Ringed: a vertebral band every 3 px, the bands' creases sunk into the tube.
    R *= 1.0 + 0.075 * math.cos(2 * math.pi * (r - top) / 3.0)
    zc = 6.4 + 1.8 * t
    dx = cm - CORD[0]
    if r < top:  # round end at the condyles
        R *= math.sqrt(max(0.0, 1 - ((top - r) / 1.2) ** 2))
    if abs(dx) >= R:
        return -99.0
    return zc + math.sqrt(R * R - dx * dx) * 0.95


def brain_z(cm, r):
    """The two lobes, round domes (the judge's graft: a smooth dome in side and rear views); the upper
    one pear-shaped (narrower towards the cord). The gyri are low relief on the dome, not height."""
    best, part = -99.0, None
    for name, cx, cy, rx, ry, top in BRAIN:
        if name == "brain_up":
            rx *= 1.0 - 0.18 * min(1.0, max(0.0, (cy - r) / ry))
        else:
            # The lower lobe runs on into the head's own brain: it widens and its footprint goes on past the seam.
            ry *= 1.0 + 0.9 * smoothstep((r - cy) / 7.0)
            rx *= 1.0 + 0.12 * smoothstep((r - cy) / 7.0)
        q = (abs((cm - cx) / rx) ** 2.4 + abs((r - cy) / ry) ** 2.4) ** (1 / 2.4)
        if q >= 1:
            continue
        dz = (1 - q ** 2) ** 0.62
        # Gyri: the sprite's lumps are round nodules about 3.5 px across in staggered rows, with
        # dark creases between them; |cos| products give round knobs and creases.
        u = 2 * math.pi * (cm - cx) / 3.6
        v = 2 * math.pi * (r - cy) / 3.4
        knob = abs(math.cos(0.5 * u + 0.5 * math.pi * (math.floor((r - cy) / 1.7) % 2))) * abs(math.cos(0.5 * v))
        z = top * dz + 0.9 * (knob ** 0.7 - 0.55) * min(1.0, 0.2 + 1.6 * dz)
        if z > best:
            best, part = z, name
    return best, part


def foramen(cm, r):
    """(ring z, inside fraction): the purple rim's torus profile and how far inside its pit."""
    cx, cy, R, t, top = FORAMEN
    d = math.hypot(cm - cx, (r - cy) * 1.08)
    ring = -99.0
    if abs(d - R) < t:
        ring = top - t + math.sqrt(t * t - (d - R) ** 2)
    return ring, d / (R - 0.6)


def forms(c, r):
    """{part: height px} of every form at assembly pixel (c, r)."""
    cm = AXIS - abs(c - AXIS)
    out = {"base": skull_top(c, r) * 12}
    for name, cx, cy, rx, ry, top, p in DOMES:
        out[name] = dome(cm, r, cx, cy, rx, ry, top, p)
    out["cord"] = cord_z(cm, r)
    bz, bpart = brain_z(cm, r)
    if bpart:
        out[bpart] = bz
    ring, _ = foramen(cm, r)
    out["rim"] = ring
    return out


def height(c, r):
    """(top height in px before the rim and the seam, winning part)."""
    f = forms(c, r)
    zs = [z for z in f.values() if z > -50]
    m = max(zs)
    z = m + SMAX_K * math.log(sum(math.exp((v - m) / SMAX_K) for v in zs))
    z -= SMAX_K * math.log(1.0 + 0.0)  # (kept for clarity: a lone form keeps its height)
    part = max(f, key=f.get)
    cm = AXIS - abs(c - AXIS)
    # The foramen's pit: a dark membrane sunk inside the rim.
    _, inside = foramen(cm, r)
    if inside < 1.0:
        pit = 2.8 + 2.4 * inside ** 2
        k = 0.5
        z = -k * math.log(math.exp(-z / k) + math.exp(-pit / k))  # smooth min
        if inside < 0.85:
            part = "membrane"
    # Grooves.
    for path, w, depth in GROOVES:
        d = min(seg_dist(cm, r, a, b) for a, b in zip(path, path[1:]))
        z -= depth * math.exp(-(d / w) ** 2)
    # The waist crease where the lobes meet (row -14.5) and where the lower lobe meets the shipped
    # brain (row -1.5).
    if abs(cm - AXIS) < 14:
        for rr, dep in ((-14.6, 1.6),):
            z -= dep * math.exp(-((r - rr) / 0.8) ** 2) * (1 - (abs(cm - AXIS) / 14) ** 2)
    return z, part


def smoothstep(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


# --- the solid -----------------------------------------------------------------------------------

class Shipped:
    """The shipped head's surface (top and bottom), by ray casts."""

    def __init__(self, obj):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        self.tree = BVHTree.FromBMesh(bm)
        bm.free()

    def top(self, c, r):
        hit = self.tree.ray_cast(Vector((X(c), Y(r), 5.0)), Vector((0, 0, -1)))
        return hit[0].z if hit[0] is not None else None

    def bottom(self, c, r):
        hit = self.tree.ray_cast(Vector((X(c), Y(r), -5.0)), Vector((0, 0, 1)))
        return hit[0].z if hit[0] is not None else None


def top_z(c, r, ship):
    h, part = height(c, r)
    d_out = -phi_ext(c, r)
    k = rim(d_out, RIM_OUT)
    k_hole = rim(-phi_cut(c, r) + 0.0, RIM_HOLE) if phi_ext(c, r) > -RIM_OUT * 2 or True else 1.0
    # Near the box side cuts phi_cut is small but phi_ext is not: only the true outline and the
    # holes roll over (phi_ext carries both), the cuts stay square.
    k_hole = rim(-phi_ext(c, r), RIM_HOLE)
    z = EDGE_Z + 0.01 + (h * PX - EDGE_Z) * k * k_hole
    # The brain gives way to the head's own brain over a longer run (no pinch where they meet).
    bw = 1.0 - smoothstep((abs(c - AXIS) - 12.0) / 4.0)
    frm = BLEND_FROM + (-10.0 - BLEND_FROM) * bw
    w = smoothstep((r - frm) / (SEAM - frm))
    if w > 0:
        zs = ship.top(c, r)
        if zs is not None:
            z = z + (zs - z) * w
    return z, part


def bottom_z(c, r, ship):
    d_out = max(0.0, -phi_ext(c, r))
    z = EDGE_Z - 0.01 - BACK_BELLY * rim(d_out, 22.0)
    w = smoothstep((r - BLEND_FROM) / (SEAM - BLEND_FROM))
    if w > 0:
        zb = ship.bottom(c, r)
        if zb is not None:
            z = z + (zb - z) * w
    return z


def build_back(painter, ship, coll):
    """The back of the skull as one closed solid (top height field, walls, belly)."""
    c0, c1, r0, r1 = 23.0, 97.0, -57.0, 2.5
    nc, nr = int(round((c1 - c0) / G)), int(round((r1 - r0) / G))
    node = lambda i, j: (c0 + i * G, r0 + j * G)  # noqa: E731
    keep = set()
    for i in range(nc):
        for j in range(nr):
            cc, rr = c0 + (i + 0.5) * G, r0 + (j + 0.5) * G
            if phi_cut(cc, rr) < 0 and rr < r1:
                keep.add((i, j))
    # Boundary edges (used by one kept cell) and their nodes.
    from collections import Counter
    edges = Counter()
    for i, j in keep:
        for e in (((i, j), (i + 1, j)), ((i + 1, j), (i + 1, j + 1)), ((i + 1, j + 1), (i, j + 1)), ((i, j + 1), (i, j))):
            edges[tuple(sorted(e))] += 1
    bnd_edges = [e for e, n in edges.items() if n == 1]
    bnd_nodes = {n for e in bnd_edges for n in e}
    pos = {}
    for i, j in keep:
        for n in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
            if n not in pos:
                pos[n] = node(*n)
    # Snap the boundary nodes onto the footprint's contour (two Newton steps along the gradient).
    for n in bnd_nodes:
        c, r = pos[n]
        if r >= r1 - 1e-6:
            continue  # the straight cut south of the seam
        for _ in range(3):
            f = phi_cut(c, r)
            gx = (phi_cut(c + 0.2, r) - phi_cut(c - 0.2, r)) / 0.4
            gy = (phi_cut(c, r + 0.2) - phi_cut(c, r - 0.2)) / 0.4
            g2 = gx * gx + gy * gy
            if g2 < 1e-6:
                break
            step = min(1.0, max(-1.0, f / g2))
            c, r = c - gx * step, r - gy * step
        pos[n] = (c, r)
    bm = bmesh.new()
    top_v, bot_v, parts = {}, {}, {}
    for n, (c, r) in pos.items():
        z, part = top_z(c, r, ship)
        top_v[n] = bm.verts.new((X(c), Y(r), z))
        parts[n] = part
        if n in bnd_nodes:
            bot_v[n] = bm.verts.new((X(c), Y(r), bottom_z(c, r, ship)))
    # The belly: interior nodes get their own bottom verts too.
    for n, (c, r) in pos.items():
        if n not in bot_v:
            bot_v[n] = bm.verts.new((X(c), Y(r), bottom_z(c, r, ship)))
    tops, bots, walls = [], [], []
    for i, j in keep:
        q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        tops.append(bm.faces.new([top_v[n] for n in q]))
        bots.append(bm.faces.new([bot_v[n] for n in reversed(q)]))
    for a, b in bnd_edges:
        walls.append(bm.faces.new((top_v[a], top_v[b], bot_v[b], bot_v[a])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in tops + bots:
        f.smooth = True
    # Paint: the top takes the sprite's colour under it, per part (its mid-tone the part's own
    # trimmed median); walls and belly the shipped belly's 97; walls at the box cuts in shadow (96).
    pal = painter.pal
    mids = part_mids(painter)
    by_part = {}
    for f in tops:
        c, r = to_px(*f.calc_center_median().xy)
        _, part = height(c, r)
        by_part.setdefault(part, []).append(f)
    for part, faces in by_part.items():
        ctx = "purple" if part in PURPLE_PARTS else "blue"
        mid = mids.get(part, 85 if ctx == "purple" else 99)
        painter.paint(faces, ctx, default=mid)
        if part == "condyle":
            for f in faces:
                f.material_index = pal.bone(pal.index[f.material_index])
    for f in bots:
        f.material_index = pal(97)
    for f in walls:
        c, r = to_px(*f.calc_center_median().xy)
        cut = phi_ext(c, r) < -2.0
        f.material_index = pal(96 if cut else 97)
        f.smooth = not cut
    me = bpy.data.meshes.new(f"{NAME}-back")
    bm.to_mesh(me)
    bm.free()
    for m in pal.mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(f"{NAME}-back", me)
    coll.objects.link(ob)
    return ob


class BackPainter(Painter):
    """The shipped Painter, with the brain's purple kept to its own family too (no blue faces on
    the brain where the sprite's lobes are a pixel narrower)."""

    def shade(self, f, context, grid=None, fine=False, mid=None):
        if context != "purple":
            return super().shade(f, context, grid, fine, mid)
        return self._purple(f, mid)

    def _purple(self, f, mid):
        cen = f.calc_center_median()
        reps = [rep_of(self.pixel(p.x, p.y), "purple") for p in [cen] + [cen.lerp(v.co, 0.55) for v in f.verts]]
        reps = [r for r in reps if r is not None and FAMILY_OF.get(r) == "purple"]
        order = FAMILIES["purple"]
        if not reps:
            return mid
        pos = sorted(order.index(r) for r in reps)
        p = float(pos[len(pos) // 2])
        keep, sigma, _ = SOFT["purple"]
        c, r = to_px(cen.x, cen.y)
        total = wsum = 0.0
        for dc in (-2, -1, 0, 1, 2):
            for dr in (-2, -1, 0, 1, 2):
                raw = self.grid.get((math.floor(c + 0.5) + dc, math.floor(r + 0.5) + dr), -1)
                if raw < 0 or raw <= 4:
                    continue
                q = rep_of(raw, "purple")
                if q is None or FAMILY_OF.get(q) != "purple":
                    continue
                w = math.exp(-((math.floor(c + 0.5) + dc - c) ** 2 + (math.floor(r + 0.5) + dr - r) ** 2) / (2 * sigma * sigma))
                total += w * order.index(q)
                wsum += w
        if wsum:
            p = total / wsum
        m = order.index(mid)
        return order[max(0, min(len(order) - 1, math.floor(m + (p - m) * keep + 0.5)))]


def part_mids(painter):
    """Each part's mid-tone: the trimmed median palette index of the sprite pixels it covers
    (ink and the brightest highlights left out: they are lighting)."""
    acc = {}
    for (c, r), v in painter.grid.items():
        if r >= 0 or v <= 4:
            continue
        _, part = height(c, r)
        acc.setdefault(part, []).append(v)
    mids = {}
    for part, vals in acc.items():
        fam_lo, fam_hi = (80, 95) if part in PURPLE_PARTS else (96, 111)
        vals = sorted(v for v in vals if fam_lo <= v <= fam_hi)
        if len(vals) < 6:
            continue
        lo, hi = int(len(vals) * 0.15), int(len(vals) * 0.85)
        v = int(np.median(vals[lo:max(hi, lo + 1)]))
        rep = rep_of(v, "purple" if part in PURPLE_PARTS else "blue")
        mids[part] = rep
    # The sprite's brain sits on 83/84 (between the purple family's 83 and 85): 83, as the shipped
    # brain, so the two meet in one colour at the seam.
    for part in ("brain_up", "brain_low", "cord"):
        mids[part] = 83
    print("PART MIDS", mids)
    return mids


# --- assembly ------------------------------------------------------------------------------------

def full_grid():
    """{(col, row): palette index} of the whole head with the new pieces (prep.py's composite)."""
    A = GRID["grid"]
    R0 = GRID["R0"]
    return {(c, y + R0): v for y, row in enumerate(A) for c, v in enumerate(row) if v >= 0}


def sprite_with_colours():
    sprite = merged_sprite()
    for k, v in GRID["colors"].items():
        sprite["colors"].setdefault(k, v)
    return sprite


def layout_of(names):
    lay = GRID["layout"]
    return [(n, lay[n][1] - (SX0 + AXIS + 0.5), lay[n][2] - (SY0 + ROW0 + 0.5)) for n in names]


DECIMATE = 0.3  # of the 0.5 px grid's triangles: flat belly and plate flanks go, creases and gyri stay


def decimate(obj, ratio):
    mod = obj.modifiers.new("decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.view_layer.objects:
        o.select_set(o == obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)


def warp_85(obj, offset):
    """newshn-85 is the shipped head's mesh (the mirror of newshn-77), but its own sprite differs a
    little: its top row right of col 101 is the shoulder's ink edge (the model stops a pixel short
    there) and its right edge sits about half a pixel further out. Move its vertices so (piece
    local coords; `offset` is the piece centre in assembly px)."""
    oc, orow = offset
    for v in obj.data.vertices:
        c = v.co.x * 12 + oc
        r = orow - v.co.y * 12
        wc = smoothstep((c - 100.5) / 1.5)
        if r < 3.5 and wc > 0:
            r2 = 0.5 + (r + 0.5) * 0.75
            r = r + (r2 - r) * wc
        c = c + 0.6 * smoothstep((c - 106.0) / 6.0)
        v.co.x = (c - oc) / 12
        v.co.y = (orow - r) / 12
    obj.data.update()



def open_brain_shell(shell):
    """The head's brain no longer ends at row 0: the back's lower lobe runs on from it, so the hull
    round the brain's north end (an ink arc across the brain) goes; the back carries its own shell."""
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    gone = []
    for f in bm.faces:
        c, r = to_px(*f.calc_center_median().xy)
        if abs(c - AXIS) <= BRAIN_SHELL_HALF and r < BRAIN_SHELL_ROW:
            gone.append(f)
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    bm.to_mesh(shell.data)
    bm.free()
    print(f"{NAME}: head shell, {len(gone)} faces opened at the brain's north end")


BRAIN_SHELL_HALF, BRAIN_SHELL_ROW = 15.0, 12.0


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = sprite_with_colours()
    head, teeth, phases = build(sprite)
    coll = bpy.data.collections[NAME]
    # The whole static head (for the outline shell, the region colours and the preview).
    obj = combine([head, teeth], [0.0, 0.0], f"{NAME}-whole", coll)
    print(f"{NAME}: head {tris(head)} tris, static teeth {tris(teeth)}, phases {[tris(p) for p in phases]}")
    # The outline shell (D51) from the closed static head.
    # Its source leaves out the small bone details on the skull (orbits, sockets, eyes, nodules,
    # vertebrae, snout lobes): the decimated shell's faces are bigger than they are, bridged the
    # creases round them and drew black slivers there. The details stand above the shell instead.
    src = obj.copy()
    src.data = obj.data.copy()
    coll.objects.link(src)
    sbm = bmesh.new()
    sbm.from_mesh(src.data)
    mats = src.data.materials
    bmesh.ops.delete(sbm, geom=[f for f in sbm.faces if f.material_index < len(mats)
                                and any(k in mats[f.material_index].name for k in ("bone", "eye"))],
                     context="FACES")
    sbm.to_mesh(src.data)
    sbm.free()
    shell = common.outline_shell(src, coll, voxel=0.03, faces=3500, inside=0.006)
    bpy.data.objects.remove(src)
    open_brain_shell(shell)
    layout = [(e["model"], e["cx"] - (SX0 + AXIS + 0.5), e["cy"] - (SY0 + ROW0 + 0.5))
              for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    lay85 = layout_of(["newshn-85"])
    lay_new = layout_of(NEW)
    # --- the back of the skull: one closed solid blended onto the head at the seam.
    painter = BackPainter(full_grid(), LAST_PAL)
    ship = Shipped(head)
    back = build_back(painter, ship, coll)
    print(f"{NAME}: back {tris(back)} tris")
    back_shell = common.outline_shell(back, coll, voxel=0.03, faces=3000, inside=0.006)
    decimate(back, DECIMATE)
    print(f"{NAME}: back decimated to {tris(back)} tris")
    where = {name: (cx / 12, -cy / 12, 0.0) for name, cx, cy in layout + lay85 + lay_new}
    pieces = common.split_assembly(head, layout + lay85)
    pieces.update(common.split_assembly(back, lay_new))
    tpieces = common.split_assembly(teeth, layout + lay85)
    models = {}
    for name in ALL_PIECES:
        models[name] = [pieces[name]]
        if name in tpieces:
            t = tpieces[name]
            if name not in ANIM and len(t.data.polygons):
                t.name = f"{name}-teeth"
                models[name].append(t)
            else:
                bpy.data.objects.remove(t)
    anim_layout = [e for e in layout if e[0] in ANIM]
    for k, part in enumerate(phases):
        for name, piece in common.split_assembly(part, anim_layout).items():
            piece.name = f"{name}-f{ANIM[name][k]}"
            if len(piece.data.polygons):
                models[name].append(common.frame_part(piece, [ANIM[name][k]]))
            else:
                bpy.data.objects.remove(piece)
    shells = split_open(shell, layout + lay85, coll, "_outline")
    shells.update(split_open(back_shell, lay_new, coll, "_outline"))
    c85 = (AXIS + lay85[0][1], ROW0 + lay85[0][2])  # assembly px of newshn-85's centre
    densify(pieces["newshn-85"], 0.12)
    warp_85(pieces["newshn-85"], c85)
    warp_85(shells["newshn-85"], c85)
    for objs in models.values():
        for o in objs:
            flat_cuts(o)
    tiles = {}
    if "--no-bake" not in argv:
        import tempfile
        tmp = tempfile.mkdtemp(prefix=f"{TAG}_bake_")
        unwrap_tiles([models[name] for name in ALL_PIECES])
        # Bake in place: the head's pieces side by side (so they shade each other as one head), each
        # phase's teeth and fire well off to one side on their own.
        bake_objs = []
        for name in ALL_PIECES:
            for o in models[name]:
                fr = o.get("tyrian_frames")
                k = next((k for k in range(PHASES) if fr is not None and name in ANIM and ANIM[name][k] in fr), None)
                x, y, z = where[name]
                o.location = (x + (0 if k is None else 40.0 * (k + 1)), y, z)
                bake_objs.append(o)
        col_img, rm_img, nodes = bake_maps(bake_objs, tmp)
        for o in bake_objs:
            o.location = (0, 0, 0)
        for i, name in enumerate(ALL_PIECES):
            tiles[name] = (crop_tile(col_img, i, 1, tmp, f"{TAG}_{name}_colour"),
                           crop_tile(rm_img, i, 2, tmp, f"{TAG}_{name}_rm"))
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    fmt = "AUTO" if "--no-bake" in argv else "WEBP"
    total = 0
    for name in ALL_PIECES:
        s = shells[name]
        s.name = f"{name}_outline"
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        n = sum(tris(o) for o in models[name])
        total += n
        print(f"{NAME}: piece {name}: {n} tris, shell {tris(s)}")
        if name in ALL_NEW:
            # No catalogue entry for these (they were plain sprites): the frame, and the damaged
            # picture the game swaps in, drawn from this intact model (D173).
            num = int(name.split("-")[1])
            sprites = [{"sheet": "newshn.shp", "size": 2, "frames": [num] + ([DAMAGE[name]] if name in DAMAGE else [])}]
            models[name][0]["tyrian_piece"] = name
        else:
            sprites = common.load_sprite(ROOT, name)["sprites"]
        if tiles:
            # Each piece carries only its own tile of the bake.
            i = ALL_PIECES.index(name)
            tile_uvs(models[name], i, True)
            for ct, rt in nodes:
                ct.image, rt.image = tiles[name]
        common.export_sprite_model(ROOT, models[name] + [s], f"enemies/{name}", sprites, image_format=fmt)
        if tiles:
            tile_uvs(models[name], i, False)
    if tiles:
        for ct, rt in nodes:
            ct.image, rt.image = col_img, rm_img
    print(f"{NAME}: total {total} tris (static head {tris(obj)})")
    if "--views" in argv:
        sys.path.insert(0, str(GYGES_DATA))
        import gyges_views
        for name in ALL_PIECES:
            x, y, z = where[name]
            for o in models[name] + [shells[name]]:
                o.location = (x, y, z)  # in place, for the review views
        gyges_views.run(sys.modules[__name__], models, shells, argv)
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(Path(tempfile.mkdtemp()) / "assembly.png")
        shown = []
        for name in PIECES:
            for o in models[name]:
                fr = o.get("tyrian_frames")
                if fr is None or ANIM[name][2] in fr:
                    o.location = where[name]
                    shown.append(o)
        common.render_preview(shown, str(out), ref, size=10, view_px=640)


if __name__ == "__main__":
    main()
