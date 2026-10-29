"""The brass drums lying on TYRIAN's islands (map 1-9, layer 2; tiles 189 pointing east and 199
pointing west, one tile each), after the concepts assets/blender/features/concepts/tyr-drum-e.jpg and
tyr-drum-w.jpg: a brass housing with a rounded lid banded by straps, its front face (toward the
camera) slatted with dark grilles, and a nose on the pointed end, a ringed cone (east) or a ribbed
ogive (west), lying on the island's rock. No enemies sit on them; they are drawn in the
Background3Over pass (rows 199-324), so everything stays under L2_OVER_MAX.

The worked example for lib_tyrbld.py. The drums replace their tiles, so each model also carries the
tile's rock (Structure.rock), and its export removes the per-tile models shapesz-t189 / -t199.
Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_drum.py
    python tools/concept_maps.py tile:shapesz-tyrbld-drum-e --concept tyr-drum-e --span 0,0,0,0
    python tools/concept_maps.py tile:shapesz-tyrbld-drum-w --concept tyr-drum-w --span 0,0,0,0
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-drum-e
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-drum-w
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_tyrbld as tb  # noqa: E402

# Each drum in its tile's pixels (from the art: tiles 189 and 199 at 1x).
DRUMS = {
    "drum-e": dict(body=(2.0, 13.0), nose=(13.0, 20.5), point=+1, nose_kind="cone"),
    "drum-w": dict(body=(7.5, 19.0), nose=(7.5, 1.0), point=-1, nose_kind="ogive"),
}
BACK, LID_FRONT, FRONT = 4.5, 12.5, 21.5  # pixel rows: the lid's back edge, the lid/face edge, the face's foot
AXIS_Y = 13.0  # the nose's axis (pixel row)
SINK = -0.05  # the housing's foot, sunk into the rock
# The housing's profile across (pixel row, z): lid from the back up to the ridge, down to the front
# edge, then the slatted front face sloping to the foot.
LID = [(BACK, SINK), (BACK, 0.16), (5.5, 0.25), (7.0, 0.31), (8.7, 0.34), (10.5, 0.33), (LID_FRONT, 0.29)]
FACE = [(FRONT, 0.05), (FRONT, SINK)]
STRAP_OUT = 0.02  # straps stand this much proud of the housing
NOSE_R = 4.6  # px
NOSE_SQUASH = 0.5  # vertical radius / horizontal
NOSE_Z = 0.12  # the nose's axis height


def strap_profile():
    """The housing's profile grown by STRAP_OUT (a strap round it)."""
    out = [(BACK - 0.35, SINK)]
    out += [(b, z + STRAP_OUT) for b, z in LID[1:]]
    out += [(FRONT + 0.35, FACE[0][1] + STRAP_OUT), (FRONT + 0.35, SINK)]
    out[1] = (BACK - 0.35, LID[1][1] + STRAP_OUT)
    return out


def face_z(py):
    """The front face's height at pixel row py (between LID_FRONT and FRONT)."""
    z0, z1 = LID[-1][1], FACE[0][1]
    return z0 + (z1 - z0) * (py - LID_FRONT) / (FRONT - LID_FRONT)


def build(name):
    d = DRUMS[name]
    s = tb.Structure(name)
    x0, x1 = d["body"]
    brass, dark_brass, light_brass = s.m("brass"), s.m("brass_dark"), s.m("brass_light")
    grille = s.m("dark")

    # The housing: lid in brass, the front face dark (the grilles' backing; slats go on it).
    profile = LID + FACE
    mats = [dark_brass] + [brass] * (len(LID) - 2) + [grille, dark_brass, dark_brass]
    s.prism(profile, x0, x1, mat=dark_brass, mats=mats)
    # The lid's lighter middle band (the art's tan stripe along the top).
    mid = (x0 + x1) / 2
    band = [(b, z + 0.006) for b, z in LID[2:]]
    s.prism([(LID[2][0], LID[1][1])] + band + [(LID_FRONT, LID[1][1])], mid - 1.6, mid + 1.6, mat=light_brass)
    # Straps round the housing: at both ends and the middle.
    for sx in (x0 + 0.2, mid - 0.5, x1 - 1.2):
        s.prism(strap_profile(), sx, sx + 1.0, mat=light_brass)
    # Grille slats on the front face: vertical brass bars over the dark backing, two panels
    # either side of the middle strap, as in the concept.
    for lo, hi in ((x0 + 1.6, mid - 0.9), (mid + 0.9, x1 - 1.6)):
        n = 3
        for i in range(n):
            bx = lo + (hi - lo) * (i + 0.5) / n
            top, foot = LID_FRONT + 1.2, FRONT - 0.6
            s.prism([(top, face_z(top) - 0.01), (top, face_z(top) + 0.025), (foot, face_z(foot) + 0.025), (foot, face_z(foot) - 0.01)],
                    bx - 0.45, bx + 0.45, mat=brass)
    # A horizontal rib between the lid and the face.
    s.prism([(LID_FRONT - 0.6, LID[-1][1] - 0.01), (LID_FRONT - 0.6, LID[-1][1] + 0.025), (LID_FRONT + 0.8, face_z(LID_FRONT + 0.8) + 0.025),
             (LID_FRONT + 0.8, face_z(LID_FRONT + 0.8) - 0.01)], x0 + 0.2, x1 - 0.2, mat=light_brass)

    # The nose on the pointed end, along X from the housing.
    n0, n1 = d["nose"]
    sign = d["point"]
    length = abs(n1 - n0)
    if d["nose_kind"] == "cone":
        # A collar, then a cone with two rings, to a blunt tip.
        prof = [(0.0, NOSE_R * 0.95), (1.2, NOSE_R), (1.6, NOSE_R * 0.9), (length * 0.45, NOSE_R * 0.55),
                (length * 0.5, NOSE_R * 0.6), (length * 0.8, NOSE_R * 0.25), (length, 0.4)]
        ring_mats = [light_brass, brass, brass, light_brass, brass, brass]
    else:
        # A ribbed ogive: rounded, its ribs as alternating shades.
        prof = [(0.0, NOSE_R)]
        steps = 8
        for i in range(1, steps + 1):
            t = i / steps
            prof.append((length * t, NOSE_R * max(0.08, (1 - t ** 2) ** 0.5)))
        ring_mats = [light_brass if i % 2 else brass for i in range(steps)]
    prof = [(sign * t, r) for t, r in prof]
    s.lathe(prof, n0, AXIS_Y, axis="x", z=NOSE_Z, squash=NOSE_SQUASH, mats=ring_mats, sides=16)

    # The island's rock round it: slab under everything, boulders where the art has stones.
    # (Stones mostly under the housing or the nose are left out.)
    keep_out = s.box_mask(x0 - 0.5, BACK - 0.5, x1 + 0.5, FRONT + 0.5)
    keep_out |= s.ellipse_mask((n0 + n1) / 2, AXIS_Y, length / 2 + 0.5, NOSE_R + 0.5)
    s.rock(exclude=keep_out)

    objects = s.objects()  # no terraced deck: all parts
    s.check(objects)
    s.export(objects)


for name in DRUMS:
    build(name)
