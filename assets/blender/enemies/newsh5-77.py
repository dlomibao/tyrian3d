"""Grey bomb (newsh5.shp frame 77): a 3D version of its sprite.

Seen in episode 4 (levels 4.18, 4.22 and 4.47). A round steel bomb falling nose first down the
screen: a flat disc tail plate at the back, a thin neck between two collars, a round body (a
shoulder, a red strap round it and a fat bulb) that rounds down to a short blunt stub at the tip.
One body of revolution turned round its long axis (which lies in the screen plane): every part is
as tall as it is wide in the sprite, and its outline is the sprite's, dark outline pixels included.

The sprite's lighting is not paint: its dark outline ring, the darker lower rows and right side
and the near-white streaks are the light on polished steel. The game lights the model and draws
its own outline, so the steel takes one mid-tone grey all over (metallic and smooth, so the sun and
environment make the streaks) and only the red strap is painted. The dark row across the tail
plate (row 2) is a groove cut between its two lit rims.

Run: blender --background --python assets/blender/enemies/newsh5-77.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b013 as lib  # noqa: E402

NAME = "newsh5-77"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U
SIDES = 20  # a face on top (centred on the axis) and one either side every 18 degrees

# The profile, from the back (row edge 0, the top edge of sprite row 0) to the nose tip: (row
# edge, radius px). Radii are the sprite's half widths, outline included: rows 0-3 13 px wide, row 4
# 11, rows 5-6 7, rows 7-8 5, rows 9-13 7, rows 14-17 11, rows 18-21 13, then 11, 9, 7, 5, 3.
PROFILE = [
    # Tail plate: a flat disc (rows 0-3) with a bevel at the back, a groove round it (row 2) and a
    # sloped underside (row 4).
    (0.0, 5.7), (0.45, 6.5), (2.0, 6.5), (2.15, 6.2), (2.85, 6.2), (3.0, 6.5), (3.55, 6.5),
    (4.1, 5.9), (4.6, 5.2), (4.95, 4.2),
    # Upper collar (rows 5-6), neck rod (rows 7-8), lower collar (rows 9-13).
    (5.0, 3.5), (6.8, 3.5), (7.0, 2.9), (7.1, 2.5), (8.9, 2.5), (9.0, 3.1), (9.15, 3.5),
    (13.9, 3.5),
    # The body's rounded shoulder (row 14) and its upper part (rows 15-16).
    (14.0, 4.2), (14.3, 5.0), (14.6, 5.35), (15.0, 5.5), (16.85, 5.5),
    # The red strap (rows 17-18): wrapped round the body where it widens, 0.3 px proud.
    (16.9, 5.8), (17.8, 5.95), (18.2, 6.65), (19.0, 6.75), (19.05, 6.5),
    # The bulb (rows 19-21), rounding down over rows 22-24 to the blunt stub (rows 25-26).
    (21.6, 6.5), (22.0, 6.35), (22.5, 5.9), (23.0, 5.4), (23.5, 4.85), (24.0, 4.3), (24.5, 3.7),
    (25.0, 3.0), (25.05, 2.45), (25.9, 2.3), (26.3, 1.9), (26.7, 1.35), (26.95, 0.7), (27.0, 0.0),
]
STEEP = 1.5  # px of radius per px of length: steeper rings are crisp steps, shaded flat
STRAP = (16.85, 19.05)  # the red strap's span of row edges (rows 17-18 and its two steps)

# Materials: the steel's mid-tone grey (the sprite's grey pixels inside the outline average about
# index 6-7; the game's outline and lighting darken it) and the strap's mid red. Polished steel
# is metallic and smooth; the strap is painted.
STEEL = 7
RED = 117


def rings_of(profile):
    """The profile with a ring added at every whole row edge inside a longer span, so each face
    covers one sprite row and can take that row's shade."""
    out = [profile[0]]
    for (e0, r0), (e1, r1) in zip(profile, profile[1:]):
        for e in range(math.floor(e0) + 1, math.ceil(e1)):
            if e - e0 > 0.2 and e1 - e > 0.2:
                out.append((float(e), r0 + (r1 - r0) * (e - e0) / (e1 - e0)))
        out.append((e1, r1))
    return out


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = [common.palette_material(sprite, STEEL, NAME, metallic=0.9, roughness=0.2),
            common.palette_material(sprite, RED, NAME, metallic=0.4, roughness=0.4)]
    px = sprite["frames"][0]["pixels"]
    g = lib.Grid(24, 28, px)
    ax = g.x(12)
    bm = bmesh.new()

    profile = rings_of(PROFILE)
    rings = []
    for e, r in profile:
        y = g.y(e - 0.5)
        if r == 0.0:
            rings.append([bm.verts.new((ax, y, 0.0))])
            continue
        rings.append([bm.verts.new((ax + r * U * math.cos(a), y, r * U * math.sin(a)))
                      for a in (2 * math.pi * (i + 0.5) / SIDES for i in range(SIDES))])
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        (e0, w0), (e1, w1) = profile[k], profile[k + 1]
        smooth = abs(w1 - w0) <= STEEP * (e1 - e0)
        red = STRAP[0] - 1e-6 <= e0 and e1 <= STRAP[1] + 1e-6
        for i in range(SIDES):
            j = (i + 1) % SIDES
            f = bm.faces.new((r0[i], r0[j], r1[0]) if len(r1) == 1 else (r0[i], r0[j], r1[j], r1[i]))
            f.smooth = smooth
            f.material_index = 1 if red else 0
    back = bm.faces.new(list(reversed(rings[0])))  # the flat back of the tail plate
    back.smooth = False
    back.material_index = 0

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, [obj], sprite)


if __name__ == "__main__":
    main()
