"""Mouth boss (newshn.shp, assembly of 17 pieces): a 3D version of its sprites.

Seen in episode 2 (level 2.4). Seventeen 2x2 enemies side by side make one 120 x 95 px organic
head (sprite.json `assemblyLayout`; the top row is cut off by the screen edge, the boss carries
on above it): a dark blue-grey biomechanical skull with a lumpy purple brain on top, three
glowing red eyes down each side, tentacles hanging off its flanks, purple claws low on each
side and a bony chin spike. Most of the face is a huge round mouth: a ring of pink gums with
bone fangs pointing inward, and a throat of dark red ridges sinking to a glowing core.

The four pieces round the throat (newshn-119, -121, -157, -159) animate over five frames: the
teeth dim and draw back into the gums while a fire rises from the core, red, then orange, then
white-hot. Each keeps one model for its frames (DECISIONS.md D17): their shell takes each frame's
colours from the sprite (palette materials with `frames`), and the teeth and the fire are parts
per frame (frame_part). The other pieces have one frame and are built as before.

The whole head is built once in assembly coordinates and cut into the pieces with
common.split_assembly. The head is a shell in polar rings round the mouth: from the outline in
to the gums, over the gums and down the throat to the core; its faces take the palette colour
of the sprite pixel under them, so the biomechanical texture, gums and throat ridges follow the
sprite. Brain, eyes, fangs, tentacles, claws and chin spike are modelled on top.

Run: blender --background --python assets/blender/enemies/assembly-newshn-195.py [-- --preview out.png]
(the preview is the whole head; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
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
    "gum": [65, 67, 69, 71, 73, 75],
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
SOFT = {"blue": (0.5, 0.8, True), "gum": (0.55, 0.7, True), "red": (0.75, 0.0, False),
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


def rep_of(idx, context, fine=False):
    """The shade (palette index) a sprite pixel stands for; outline black depends on where it is.
    `fine` keeps the fire's bright shades apart (FINE_FAMILIES)."""
    if idx < 0:
        return None
    if fine and 119 <= idx <= 127:
        return (120, 120, 122, 122, 124, 124, 126, 126, 126)[idx - 119]
    if idx <= 4 or idx == 48:
        return DARK[context]
    for lo, hi, rep in ((16, 27, 19), (64, 65, 65), (66, 67, 67), (68, 69, 69), (70, 71, 71), (72, 73, 73),
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
    STYLE = {"blue": (0.1, 0.4), "gum": (0.0, 0.4), "red": (0.0, 0.65), "purple": (0.0, 0.6),
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
                emission_strength=2.5 if max(reps) >= 120 else 0.0, frames=frames))
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
        v = self._lightness(c, r, "blue", 2.0)
        return 0.0 if v is None else max(-0.14, min(0.13, (v - 2.0) * 0.07))

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
            if self.phases is None:
                rep = self.shade(f, context, mid=default)
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
                f.material_index = self.pal(keep if rep is None else rep)
                continue
            reps = [self.shade(f, context, g, fine=True, mid=default) for g in self.phases]
            reps = [keep if r is None else r for r in reps]
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
SOCKET_R, SOCKET_DEPTH = 4.3, 0.17
# The throat: its rim below the gums' top, the floor it steps down to (in ledges) and the red
# mound round the glowing core that rises from it.
LIP_TOP = 0.72
THROAT_RIM, THROAT_FLOOR, MOUND_TOP = 0.42, -0.5, -0.16
FLOOR_AT = 0.55  # fraction of the way from the gums to the core where the mound starts
LEDGES = 6
BELLY = 0.62  # the underside's depth (it has to stay under the throat)
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
    return dz


def throat_z(s, rim_z=THROAT_RIM):
    """Throat height at fraction s of the way from the gums (0) to the core (1): down in ledges to
    the floor, then up over the mound. `rim_z`: the throat's rim height on this ray."""
    if s <= FLOOR_AT:
        t = s / FLOOR_AT
        q = t * LEDGES
        k = min(math.floor(q), LEDGES - 1)
        f = q - k
        stair = (k + f * f * (3 - 2 * f)) / LEDGES
        g = 0.35 * t + 0.65 * stair
        return rim_z + (THROAT_FLOOR - rim_z) * g ** 0.9
    m = (s - FLOOR_AT) / (1 - FLOOR_AT)
    return THROAT_FLOOR + (MOUND_TOP - THROAT_FLOOR) * math.sin(0.5 * math.pi * m) ** 1.5


def build_shell(bm, painter):
    out = lib.mirror_poly(OUT_LEFT, AXIS)
    gum_out = lib.mirror_poly(GUM_OUT_LEFT, AXIS)
    gum_in = lib.mirror_poly(GUM_IN_LEFT, AXIS)
    N, M, K = 384, 192, 96  # ring resolution: skin, gums, throat
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
    us = [0.02, 0.045, 0.075, 0.11] + [0.15 + 0.85 * i / 22 for i in range(23)]
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
        zs = [z + lift(c, r) + painter.gum_relief(c, r) * math.sin(math.pi * v) for c, r in pts]
        ring = verts(pts, zs)
        gums += connect(bm, prev, ring)
        prev = ring

    # The throat: a tapered bowl stepping down in ledges (the sprite's dark red rings) to its floor,
    # then a red mound round the glowing core.
    rim_pts = ring_points(gum_in, gum_in, 0.0, K)
    rim_zs = [THROAT_RIM + lift(c, r) for c, r in rim_pts]
    throat = []
    ss = [FLOOR_AT * i / 22 for i in range(1, 23)] + [FLOOR_AT + (1 - FLOOR_AT) * i / 10 for i in range(1, 10)]
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
        zs = [edge_z - (0.15 + (BELLY - 0.15) * min(1.0, max(0.0, (34 - math.hypot(c - CENTRE[0], r - CENTRE[1])) / 10)))
              * rim(math.hypot(c - ec, r - er), 16.0) for (c, r), (ec, er) in zip(pts, rim_ref)]
        ring = verts(pts, zs)
        belly += connect(bm, prev, ring)
        prev = ring
    belly += connect(bm, prev, [bm.verts.new((X(CENTRE[0]), Y(CENTRE[1]), edge_z - BELLY - 0.02))])

    for f in skin + gums + throat + belly:
        f.smooth = True
    painter.paint(skin, "blue", default=98)
    painter.paint(gums, "gum", default=69)
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
    """Everything on the shell. `phase` None: all of it, as the static pieces have it; "base": all
    but the teeth and the fire (the animated pieces' always-shown part); 0-4: only the teeth and the
    fire as on that phase (FANGS, FIRE)."""
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
        # Folds: a few crossing ripples, strongest on top, like the sprite's lumpy purple mass.
        return 1 + (0.07 * math.sin(14 * dx + 1.3) * math.sin(12 * dy + 0.4)
                    + 0.04 * math.sin(23 * dx + 7 * dy) + 0.03 * math.sin(19 * dy - 9 * dx)) * (0.3 + max(dz, 0))
    if body:
        # A round dome about 8 px above the armour (its lower half, inside the skull, left out).
        # Its base sits a little into the skull's dome, so it stands about 8 px above it.
        faces = half_blob(bm, P(AXIS, 4.0, skull_top(AXIS, 4.0) - 0.12), (13.6 * PX, 17.0 * PX, 0.8), segments=36,
                          rings=10, mat=pal(87), bump=bump)

        painter.paint(faces, "purple", default=87, min_nz=0.0)
        # Bony snout plate between the brain and the upper lip (rows 19-27).
        faces = lib.blob(bm, P(AXIS, 23.8, skull_top(AXIS, 23.8) - 0.1), (7.5 * PX, 4.2 * PX, 0.26), segments=16,
                         rings=8, mat=pal(103))
        painter.paint(faces, "blue", default=103, min_nz=0.0)

        # The central lobe of the upper lip, hanging from the gums' ridge over the throat and ending
        # in a short dark tooth (column 63, rows 37-49).
        faces = lib.tube(bm, [P(AXIS, r, z + lift(AXIS, r)) for r, z in
                              ((36.5, LIP_TOP - 0.06), (40.0, LIP_TOP - 0.1), (43.2, 0.5), (44.6, 0.42))], [2.2 * PX, 2.3 * PX, 1.9 * PX, 1.0 * PX], sides=10,
                         mat=pal(69), flat=0.8)
        painter.paint(faces, "gum", default=69, min_nz=0.0)
    if teeth:
        k, mat = fang("knob", pal(163) if not anim else None)
        z0 = 0.44 + lift(AXIS, 44.0)
        lib.tube(bm, [P(AXIS, 44.0, z0), P(AXIS, 44.0 + 2.5 * k, z0 - 0.12 * k),
                      P(AXIS, 44.0 + 5.5 * k, z0 - 0.32 * k)],
                 [1.5 * PX, 1.1 * PX, 0.0], sides=8, mat=mat)

    def side(m):
        if body:
            # Eyes: a red ball with a glowing centre, half sunk in its dark socket (three down each side).
            for c, r in EYES:
                z = surf.z(m(c), r)
                lib.blob(bm, P(m(c), r, z), (3.0 * PX, 3.0 * PX, 0.2), segments=14, rings=7, mat=pal.eye(113))
                lib.blob(bm, P(m(c), r - 0.1, z + 0.06), (2.1 * PX, 2.1 * PX, 0.165), segments=12, rings=6,
                         mat=pal.eye(117))
                lib.blob(bm, P(m(c), r - 0.2, z + 0.13), (1.2 * PX, 1.2 * PX, 0.11), segments=10, rings=5,
                         mat=pal.eye(121, emission=4.0))

        # Fangs round the gums, pointing in and down into the throat: (base, tip, radius px).
        for i, ((bc, br), (tc, tr), rad) in enumerate((
                ((56.4, 41.0), (57.8, 49.6), 1.5), ((44.0, 47.6), (50.6, 49.3), 1.6),
                ((40.6, 54.6), (48.6, 56.6), 1.6), ((44.6, 63.6), (49.6, 63.2), 1.3),
                ((46.6, 71.4), (51.6, 70.6), 1.2), ((52.8, 79.6), (54.6, 75.8), 1.1),
                ((60.0, 82.4), (60.3, 77.0), 1.1))):
            if not teeth:
                break
            k, mat = fang(("L" if m(0) == 0 else "R", i), pal(169) if not anim else None)
            if k != 1.0:
                tc, tr = bc + (tc - bc) * k, br + (tr - br) * k
            # Rooted in the gums' inner slope, hanging down over the throat.
            zb = surf.z(m(bc), br) - 0.04
            mc, mr = bc + (tc - bc) * 0.45, br + (tr - br) * 0.45
            lib.tube(bm, [P(m(bc), br, zb), P(m(mc), mr, zb - 0.1 * k), P(m(tc), tr, zb - 0.3 * k)],
                     [(rad + 0.35) * PX, (rad + 0.35) * 0.7 * PX, 0.0], sides=8, mat=mat)

        if not body:
            return
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
            pts = [P(m(c), r, 0.08 - 0.08 * i / (n - 1)) for i, (c, r, _) in enumerate(path)]
            faces = lib.tube(bm, pts, [rr * PX for _, _, rr in path], sides=10, mat=pal(101))
            painter.paint(faces, "blue", default=101, min_nz=-0.2)

        # Purple claw low on each side, sweeping down and out (columns 27-38, rows 64-77).
        # Centres and half-widths measured on the sprite's purple, row by row.
        path = [(35.5, 65.2, 0.3, 2.8), (33.0, 68.5, 0.24, 3.6), (31.5, 71.5, 0.15, 3.5), (30.0, 73.5, 0.08, 2.6),
                (28.6, 75.0, 0.04, 1.6), (27.6, 76.0, 0.03, 0.0)]
        # A round, tapering horn standing on the cheek pad: about 5 px tall at its root.
        faces = lib.tube(bm, [P(m(c), r, max(z, surf.z(m(c), r, z) - 0.03 + 0.55 * w * PX)) for c, r, z, w in path],
                         [w * PX for *_, w in path], sides=10, mat=pal(87), flat=1.0)
        painter.paint(faces, "purple", default=87, min_nz=-0.2)

    mirrored(side)

    if body:
        # Chin spike (column 63, rows 89-94).
        faces = lib.tube(bm, [P(AXIS, 88.0, 0.2), P(AXIS, 91.0, 0.12), P(AXIS, 93.0, 0.06), P(AXIS, 94.2, 0.02),
                              P(AXIS, 95.0, 0.0)],
                         [2.2 * PX, 2.5 * PX, 2.3 * PX, 1.4 * PX, 0.0], sides=8, mat=pal(103))
        painter.paint(faces, "blue", default=103, min_nz=-0.2)

    if phase is None:
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
    coll = common.reset_collection(NAME)
    pal = Palette(sprite)
    painter = Painter(load_grid(), pal)
    bm = bmesh.new()
    build_shell(bm, painter)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    surf = Surface(bm)
    build_parts(bm, painter, surf)
    return lib.to_object(NAME, bm, pal.mats, coll)


def build_animated(sprite):
    """The head as the animated pieces show it: a base with each phase's colours (shown on every
    frame) and, per phase, the teeth and the fire. Returns (base, [part per phase])."""
    coll = bpy.data.collections[NAME]
    pal = Palette(sprite)
    boxes = [(e["cx"] - 12 - SX0 - 0.5, e["cy"] - 14 - SY0 - 0.5, e["cx"] + 12 - SX0 - 0.5, e["cy"] + 14 - SY0 - 0.5)
             for e in sprite["assemblyLayout"] if e["model"] in ANIM]
    painter = Painter(load_grid(), pal, phases=[load_grid(k) for k in range(PHASES)], boxes=boxes)
    bm = bmesh.new()
    build_shell(bm, painter)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    surf = Surface(bm)
    build_parts(bm, painter, surf, phase="base")
    painter.resolve()
    base = lib.to_object(f"{NAME}-anim", bm, pal.mats, coll)
    parts = []
    for k in range(PHASES):
        pbm = bmesh.new()
        build_parts(pbm, Painter(painter.grid, pal), surf, phase=k)
        parts.append(lib.to_object(f"{NAME}-phase{k}", pbm, pal.mats, coll))
    return base, parts


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


def main():
    sprite = merged_sprite()
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - (SX0 + AXIS + 0.5), e["cy"] - (SY0 + ROW0 + 0.5))
              for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    models = {name: [pieces[name]] for name in PIECES}
    # The animated pieces: their cut of the animated base, plus each phase's teeth and fire tagged
    # with that phase's frame.
    base, phases = build_animated(sprite)
    anim_layout = [e for e in layout if e[0] in ANIM]
    for name in ANIM:
        bpy.data.objects.remove(pieces[name])
    cut = common.split_assembly(base, anim_layout)
    for name in ANIM:
        models[name] = [cut[name]]
    for k, part in enumerate(phases):
        for name, piece in common.split_assembly(part, anim_layout).items():
            piece.name = f"{name}-f{ANIM[name][k]}"
            if len(piece.data.polygons):
                models[name].append(common.frame_part(piece, [ANIM[name][k]]))
    for objs in models.values():
        for o in objs:
            flat_cuts(o)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, models[name], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=10, view_px=640)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview(models[name], str(out.parent / f"{name}.png"), img, size=2,
                                  frame=data["frames"][0]["index"])
            if "--frames" in sys.argv and name in ANIM:
                common.render_frame_previews(models[name], str(out.parent / f"{name}-frames.png"), data, ROOT)


if __name__ == "__main__":
    main()
