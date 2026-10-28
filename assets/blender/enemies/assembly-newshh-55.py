"""Bronze drill missile (newshh.shp, assembly of newshh-17 and newshh-55): a 3D version of its sprites.

Seen in episode 2 (level 2.4). Two 2x2 enemies stacked make one 24x56 px object: a faceted
bronze shell lying along the screen, nose up. The nose (newshh-17) is a long cone; the body
(newshh-55) is three overlapping skirts that widen towards the back, each with a chevron rim,
and a rounded knob near the blunt tail. The sprite lights it from the left, with a sharp ridge
down the middle (light left of it, dark right of it), so the shell is one closed, smooth-shaded
24-sided loft, round in section (as tall as it is wide), with a vertex on top carrying a raised
spine. Each skirt's rim stands ~1 px proud and overhangs the next skirt, and the tail closes in a
rounded bottom. Faces take the sprite's shades by where they fall seen from above.

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

# Palette indices of the shell as the sprite shades it seen from above, by a face's distance from
# the ridge (px) and from the silhouette's edge: lit left of the ridge (24, 23, 22), dark right of it
# (17, 18, 19), a lighter edge column on each side (20 left, 22 right: the sprite's rim light) and
# the outline-dark flank. The underside (unseen from above) is mid bronze, so it reads as brass
# from the side.
LIT = [(1.5, 24), (3.0, 23), (99, 22)]
DARK = [(1.5, 17), (3.0, 18), (99, 19)]
EDGE_L, EDGE_R, FLANK = 20, 22, 16
RIM_L, RIM_R = 27, 24  # a tier's light leading edge
STEP = 17  # the shadow under a tier's overhang
UNDER_L, UNDER_R = 21, 20
# The spine along the ridge: the sprite's centre column, near-white at the chevrons' peaks.
SPINE = [(18.5, 23), (21.5, 27), (23.5, 30), (26.5, 28), (30.5, 25), (32.5, 30), (34.5, 28),
         (36.5, 25), (39.5, 30), (40.5, 24), (44.5, 28), (99, 25)]


def lookup(table, v):
    return next(i for lim, i in table if v < lim)


def ring_h(i):
    """Half height (units) of ring i: round (ROUND x its half width), rims standing proud."""
    r, w, s, band = RINGS[i]
    h = ROUND * w / 12
    if i > 0 and RINGS[i - 1][3] == "rim":
        h *= RIM_H
    elif band == "rim":
        h *= 1.0 + (RIM_H - 1.0) * 0.6
    return h


def ridge_top(row):
    """The shell's top on its centreline at `row`."""
    pts = [(r, ring_h(i)) for i, (r, *_rest) in enumerate(RINGS)]
    for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
        if r0 <= row <= r1 and r1 > r0:
            return z0 + (z1 - z0) * (row - r0) / (r1 - r0)
    return 0.0


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, "nshh55", **kw)  # noqa: E731
    used = sorted({i for t in (LIT, DARK, SPINE) for _l, i in t}
                  | {EDGE_L, EDGE_R, FLANK, RIM_L, RIM_R, STEP, UNDER_L, UNDER_R, 29, 30})
    mats = [pal(i, metallic=0.0, roughness=0.8) for i in used]
    slot = {i: k for k, i in enumerate(used)}
    bm = bmesh.new()
    ax = G.X(AXIS)

    secs = [(r, w, ring_h(i), 0.0, s) for i, (r, w, s, _b) in enumerate(RINGS)]
    faces = lib.loft(bm, G, AXIS, secs, sides=SIDES, mat=0, smooth=True, phase=0.0)
    half = SIDES // 2
    sharp = set()
    for k, (_r, w0, _s, band) in enumerate(RINGS[:-1]):
        width = (w0 + RINGS[k + 1][1]) / 2
        strip = faces[k * SIDES:(k + 1) * SIDES]
        for j, f in enumerate(strip):
            # Face j runs from the ridge down the left side (j < half), then up the right side.
            left = j < half
            under = (j if left else SIDES - 1 - j) >= half // 2
            dx = abs(f.calc_center_median().x - ax) / PX
            edge = width - dx
            if band == "step":
                idx = STEP
            elif under:
                idx = UNDER_L if left else UNDER_R
            elif edge < 1.0:
                idx = FLANK
            elif band == "rim":
                idx = RIM_L if left else RIM_R
            elif edge < 2.0:
                idx = EDGE_L if left else EDGE_R
            else:
                idx = lookup(LIT if left else DARK, dx)
            f.material_index = slot[idx]
            if band in ("rim", "step"):
                f.smooth = False
                sharp.update(f.edges)
    for e in sharp:
        e.smooth = False

    # A raised spine down the ridge, from the tip to the knob, in the sprite's centre-column shades.
    path = []
    row = 15.0
    while row <= 46.5:
        path.append((AXIS, row, ridge_top(row) - 0.25 * PX, 0.6, 1.2 * PX))
        row += 0.5
    for f in lib.sweep(bm, G, path, sides=4, mat=0, smooth=False):
        row = G.h / 2 - 0.5 - f.calc_center_median().y * 12
        f.material_index = slot[lookup(SPINE, row)]
    # Bright round knob on the tail section (rows 46-50, just left of the ridge): a sphere half
    # standing out of the shell.
    knob = lib.ellipsoid(bm, G, 11.8, 48.2, ridge_top(48.2), 2.5, 2.5, 2.5 * PX, mat=0, segments=12, rings=6)
    for f in knob:
        f.normal_update()
        f.material_index = slot[30 if f.normal.z > 0.75 else 29 if f.normal.z > 0.35 else 27]

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
