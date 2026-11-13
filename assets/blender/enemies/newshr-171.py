"""Small brown falling rock (newshr.shp frame 171, a 9 x 11 px rock in its 12x14 cell): design A, final.

What it is: a fist-sized chunk of brown stone that IXMUCANE and SAWBLADES rain down the screen as
their random rock shower (enemy type 660, falling 2-11 px a tick). It is airborne, so it is a
closed, roughly rounded chunk all over, not a ground outcrop.

Reading the sprite (light from the upper left, rubric "Reading a sprite"): a lumpy pentagon whose
tip points up-left (a small dark red-brown chip, 66/67, at that tip). Two lit lobes: the upper-left
one (170 at cols 2-3, rows 3-4) and the central one (171/169/168 at cols 4-6, rows 4-6), parted by
a darker crease (164/165 running from (5, 4) down-left to (2, 6)). The lower half is mid stone
(165-167) with one small lit spot low in the middle (168 at (5, 9)); the right and bottom edges are
the dark limb (162-163, the shadow side: lighting, not paint). So: a rounded fractured chunk whose
top carries the two lobes as lumps, each broken by fracture faces turned to the light (a highlight
on rock is a lit face), a crease groove between them, the lower right falling away into shadow,
and a plain closed underside with a few planes.

Built on lib_newshd_rock (D121/D122 loft + fracture faces, D175 facet ramp: each facet one shade of
the sprite's own 162-171 ramp, matched to the sprite's shade distribution; D90 outline shell from a
sealed pre-cull copy; AO/roughness bake only). The 67 chip at the tip is painted before the ramp so
it keeps its colour. Matte stone (metallic 0, roughness 0.9).

    blender -b --factory-startup -P assets/blender/enemies/newshr-171.py -- [--no-bake] [--out file.glb]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_newshd_rock as lib  # noqa: E402

NAME = "newshr-171"

# Sprite coordinates are pixel edges: pixel (c, r) spans c..c+1, r..r+1 (12x14 cell).
SPEC = {
    "metallic": 0.0,
    "roughness": 0.9,       # matte stone: its lit faces read by their angle, no glint
    "mid": 165,             # trimmed median of the rock pixels (162-171 ramp)
    # the facet ramp leans more on the sprite's brightness under each facet (0.6 default), so the
    # central lobe's 171 highlight lands there and not all on the upper-left lobe
    "ramp": {"sprite": 0.8},
    "h_top": 0.36,          # about 4.3 px above the waist (9 px wide rock)
    "h_bot": 0.30,
    "rise": 0.7,
    "top_pow": 0.8,         # rounder shoulders than the asteroids' 0.6: no standing barrel wall
    "bot_pow": 1.0,
    "fall": 0.8,            # a rounder underside, no flat base
    "summit": (5.5, 6.0),   # the central lobe, under the sprite's brightest pixel (171)
    "summit_gain": 0.05,
    "ridges": [],
    "bumps": [((3.4, 4.2), 0.34, 1.4),     # the lit upper-left lobe (170)
              ((5.9, 6.2), 0.36, 1.4),     # the lit central lobe (171 / 169 / 168)
              ((5.6, 9.4), 0.14, 1.2),     # the small lit spot low in the middle (168)
              ((8.4, 9.2), -0.22, 2.0),    # the shadowed lower right
              ((7.8, 3.8), -0.08, 1.4)],   # the upper-right shoulder in half shade
    "crests": [],
    # the darker crease between the lobes, from (5, 4) down-left to (2, 6)
    "valleys": [([(6.4, 3.6), (5.0, 4.8), (3.6, 5.9), (1.8, 6.6)], -0.16, 0.7)],
    "tilt": 0.08,           # the top falls away to the right (shadow side)
    "lumps": 0.04,
    "grow": 0.18,
    "waist": 0.07,
    "steps": 96,
    "smooth": 2,
    "sectors": 64,
    "rings_top": 16,
    "rings_bot": 8,
    "seed": 171,
    "fine": 14,
    "fine_depth": (0.03, 0.05),
    "rim_spalls": 9,
    "rim_depth": (0.02, 0.035),
    "cuts": [
        # the lit faces of the two lobes, turned to the light (left / upper-left / up)
        (150, 48, 0.09), (195, 46, 0.08), (125, 60, 0.07), (170, 64, 0.05),
        # the crown, broken into near-level faces
        (60, 80, 0.035), (230, 78, 0.035),
        # the shadowed right, lower-right and lower flanks
        (10, 44, 0.11), (330, 46, 0.11), (290, 58, 0.07), (250, 56, 0.06), (50, 58, 0.07),
        # shoulder spalls round the rim (shallow, so the outline holds)
        (140, 22, 0.03), (230, 24, 0.03), (320, 22, 0.03), (45, 24, 0.03),
        # broad side planes round the waist, so the flanks break into a few big faces, not strips
        (0, 6, 0.035), (60, 10, 0.03), (115, 2, 0.03), (175, 8, 0.035), (215, -4, 0.03),
        (270, 4, 0.035), (305, -6, 0.03),
        # underside: a few planes so it reads as stone, nothing more, and no flat base
        (30, -55, 0.06), (150, -50, 0.06), (260, -58, 0.06), (100, -64, 0.05),
        (200, -28, 0.04), (320, -26, 0.04),
    ],
    # a fine crack along the crease
    "cracks": [([(6.0, 3.9), (4.9, 4.9), (3.7, 5.8), (2.4, 6.4)], 0.028, 0.026)],
    # no impact pits: at 9 px a pit reads as a drilled hole, and the sprite draws none
    "pits": [],
}

#: The dark red-brown chip at the up-left tip (67 at (2, 2), 66 beside it on the rim).
TIP = (2.5, 2.4)
TIP_R = 0.85   # sprite px


def paint(sprite, g, obj):
    """The tip's chip in pal_67 (kept out of the facet ramp, which shades only material 0)."""
    me = obj.data
    me.materials.append(common.palette_material(sprite, 67, f"{NAME}-tip", metallic=0.0, roughness=0.9))
    slot = len(me.materials) - 1
    n = 0
    for p in me.polygons:
        c = p.center
        u, v = g.uv(c.x, c.y)
        if math.hypot(u - TIP[0], v - TIP[1]) < TIP_R and p.normal.z > 0.3:
            p.material_index = slot
            n += 1
    print(f"tip chip faces: {n}")


if __name__ == "__main__":
    lib.main(NAME, SPEC, paint=paint)
