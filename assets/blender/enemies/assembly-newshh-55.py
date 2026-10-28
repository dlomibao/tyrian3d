"""Bronze drill missile (newshh.shp, assembly of newshh-17 and newshh-55): a 3D version of its sprites.

Seen in episode 2 (level 2.4). Two 2x2 enemies stacked make one 24x56 px object: a faceted
bronze shell lying along the screen, nose up. The nose (newshh-17) is a long cone; the body
(newshh-55) is three overlapping skirts that widen towards the back, each with a chevron rim,
and a round, bulging tail. The sprite lights it from the left (light left of the centre line, dark
right of it, a bright line down the top and a hot spot on the tail): that is shine on polished
bronze, so the shell is one closed, smooth-shaded 24-sided loft, round in section (as tall as it is
wide), in one mid-tone metallic material that the game's lights shade. Each skirt's rim stands
~1 px proud and overhangs the next skirt, and the tail closes in a rounded bottom.

Built once in assembly coordinates (24x56 px, centre at the origin) and cut into the two pieces
with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshh-55.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b057 as lib  # noqa: E402

NAME = "assembly-newshh-55"
ROOT = common.repo_root(__file__)
PIECES = ["newshh-55", "newshh-17"]
CX0, CY0 = 143, -4  # screen centre of the 24x56 assembly (newshh-17 above newshh-55)
G = lib.Grid(24, 56)
PX = lib.PX
AXIS = 12  # the shell's centre column (its ridge)
ROUND = 0.95  # half height / half width of the shell's section: the sprite draws it round
GROW = 0.9  # px added to every half width so the shell covers the sprite's dark outline


SIDES = 24  # round enough to shade evenly; phase 0 keeps a vertex on the ridge


# The shell as one closed loft, tip to tail. Rings are (row, half width px, sweep px, band): the
# band names the strip from this ring to the next one. "body" strips shade smooth in the sprite's
# bronze ramp, a "rim" strip is the light leading edge of a tier, a "step" strip is the underside
# of the tier's overhang (dark), "tail" the rounded bottom narrowing into its short tail point.
# A tier's rim stands ~1 px proud (RIM_H) and the next tier starts ~1 px narrower under it, so each
# tier overhangs the next one. Sweep pulls the sides back down the sprite (a chevron seen from
# above); a ring's flank row is row + sweep, and the flank rows must keep increasing down the shell.
RIM_H = 1.12
G1 = GROW
RINGS = [
    # Nose (newshh-17): a long round cone from its tip at row 13.6 out to the first rim.
    (13.6, 0.0, 0.0, "body"), (14.6, 0.6 + G1, 0.0, "body"), (16.5, 1.0 + G1, 0.0, "body"),
    (18.5, 2.2 + G1, 0.0, "body"), (21.0, 2.8 + G1, 0.0, "body"), (23.0, 3.6 + G1, 0.0, "body"),
    (26.0, 4.5 + G1, 0.0, "body"), (29.5, 4.6 + G1, 0.6, "body"),
    (30.3, 4.7 + G1, 3.2, "rim"), (31.0, 4.8 + G1, 3.6, "step"),
    # Second skirt: starts under the nose's rim and widens to 6.6 px, rim at row 37.
    (31.05, 3.9 + G1, 3.6, "body"), (32.4, 5.1 + G1, 3.0, "body"), (34.0, 6.0 + G1, 2.4, "body"),
    (35.5, 6.4 + G1, 3.0, "body"), (36.3, 6.5 + G1, 4.0, "rim"), (37.0, 6.6 + G1, 4.4, "step"),
    # Third skirt: widens to 8.7 px with its rim at row 42.
    (37.05, 5.6 + G1, 4.4, "body"), (38.4, 7.4 + G1, 3.8, "body"), (39.8, 8.4 + G1, 3.4, "body"),
    (41.3, 8.7 + G1, 3.9, "rim"), (42.0, 8.7 + G1, 4.2, "step"),
    # Tail section: full width to row 50 under the third rim, then a rounded bottom that narrows
    # into the short tail point (rows 52-54).
    (42.05, 7.8 + G1, 4.2, "body"), (44.0, 9.3, 2.9, "body"), (46.0, 9.5, 1.6, "body"),
    (48.0, 9.5, 0.6, "body"), (50.0, 9.6, 0.0, "tail"), (50.8, 9.5, 0.0, "tail"),
    (51.4, 8.6, 0.0, "tail"), (52.0, 6.8, 0.0, "tail"), (52.8, 5.6, 0.0, "tail"),
    (53.4, 4.8, 0.0, "tail"), (54.0, 4.0, 0.0, "tail"), (54.35, 2.4, 0.0, "tail"),
    (54.5, 0.0, 0.0, None),
]

# Polished bronze: the sprite's ramp (light left of the ridge, dark
# right of it, the dark flank, the near-white centre column and the bright spot on the tail) is its
# drawn lighting on a shiny round shell, not paint and not geometry. The whole shell takes the
# ramp's mid-tone and a metallic, smooth material so the game's lights shade it and make the
# shine; the tiers' rims, real raised beads, are a shade lighter. The game draws the outline.
BODY = 22
RIM = 24
METALLIC, ROUGHNESS = 0.85, 0.25


def ring_h(i):
    """Half height (units) of ring i: round (ROUND x its half width), rims standing proud."""
    r, w, s, band = RINGS[i]
    h = ROUND * w / 12
    if i > 0 and RINGS[i - 1][3] == "rim":
        h *= RIM_H
    elif band == "rim":
        h *= 1.0 + (RIM_H - 1.0) * 0.6
    return h


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nshh55", **kw)  # noqa: E731
    used = sorted({BODY, RIM})
    mats = [pal(i, metallic=METALLIC, roughness=ROUGHNESS) for i in used]
    slot = {i: k for k, i in enumerate(used)}
    bm = bmesh.new()

    secs = [(r, w, ring_h(i), 0.0, s) for i, (r, w, s, _b) in enumerate(RINGS)]
    faces = lib.loft(bm, G, AXIS, secs, sides=SIDES, mat=0, smooth=True, phase=0.0)
    sharp = set()
    for k, (_r, _w, _s, band) in enumerate(RINGS[:-1]):
        for f in faces[k * SIDES:(k + 1) * SIDES]:
            f.material_index = slot[RIM if band == "rim" else BODY]
            if band in ("rim", "step"):
                f.smooth = False
                sharp.update(f.edges)
    for e in sharp:
        e.smooth = False

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        lib.assembly_previews(ROOT, obj, pieces, layout, 4, out)


if __name__ == "__main__":
    main()
