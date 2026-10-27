"""Hatch with a red pod (newshc.shp frames 1-13): 3D versions of its sprite.

Seen in episodes 1 (level 1.19), 3 (3.23) and 4 (4.12). A square steel deck tile with a framed
hatch in it. The hatch opens and a red pod on two grey legs rises out of it, glowing once it is
up. The frames change shape, so there is one model per stage:

- newshc-1 (frame 1): the hatch shut, a raised seam running diagonally across it.
- newshc-1-f2 (frame 3): the hatch cracking open, a brown dome showing in a dark gap.
- newshc-1-f3 (frames 5, 7): the hatch open, the pod (still dark red) half out with its legs
  folded beside it in a dark pit.
- newshc-1-f4 (frames 9, 11, 13): the pod up and glowing, its legs braced on the ground, the
  pit round it open (those pixels are transparent in the sprite, so there is no deck there).
  The three frames only brighten the glow.

The deck is built from the sprite's own pixels: deck-coloured pixels (palette 96-110 and
everything outside the hatch frame) make the raised deck, the dark pit pixels a low floor.

Run: blender --background --python assets/blender/enemies/newshc-1.py [-- --preview out.png]
(each model's preview is written next to out.png as <model>.png).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from lib_b097 import (PX, X, Y, YE, ellipsoid, frame_previews, frames_arg, mask_plate, preview_args,  # noqa: E402
                      subset, sweep, to_object)

NAME = "newshc-1"
ROOT = common.repo_root(__file__)
# model name -> sheet frames it covers
STAGES = {"newshc-1": [1], "newshc-1-f2": [3], "newshc-1-f3": [5, 7], "newshc-1-f4": [9, 11, 13]}

DECK_TOP = 0.06
AXIS = 11  # the pod and its legs are centred on pixel column 11


def materials(sprite, tag):
    specs = [
        (101, dict(metallic=0.35, roughness=0.55)),  # 0 deck
        (106, dict(metallic=0.6, roughness=0.3)),  # 1 lit rim (left and top of the hatch frame)
        (104, dict(metallic=0.6, roughness=0.35)),  # 2 rim (right and bottom)
        (97, dict(metallic=0.3, roughness=0.7)),  # 3 grooves
        (51, dict(metallic=0.3, roughness=0.6)),  # 4 dark blue pit edges
        (2, dict(metallic=0.2, roughness=0.8)),  # 5 dark pit
        (108, dict(metallic=0.6, roughness=0.3)),  # 6 hatch seam
        (7, dict(metallic=0.6, roughness=0.4)),  # 7 grey legs
        (10, dict(metallic=0.65, roughness=0.3)),  # 8 lit leg faces
        (116, dict(metallic=0.3, roughness=0.4, emission_strength=1.5)),  # 9 glowing red pod
        (125, dict(emission_strength=6.0)),  # 10 hot core rib
        (122, dict(emission_strength=4.0)),  # 11 side ribs
        (113, dict(metallic=0.3, roughness=0.5)),  # 12 dark red fangs
        (70, dict(metallic=0.35, roughness=0.45)),  # 13 dark red pod (rising)
        (73, dict(metallic=0.35, roughness=0.4)),  # 14 pod ribs (rising)
        (166, dict(metallic=0.3, roughness=0.5)),  # 15 brown dome (frame 3)
        (87, dict(metallic=0.3, roughness=0.4)),  # 16 purple glint (frame 3)
        (4, dict(metallic=0.4, roughness=0.6)),  # 17 dark grey gap edges
        (73, dict(metallic=0.35, roughness=0.4)),  # 18 left pod rib (rising)
        (123, dict(emission_strength=5.0)),  # 19 glow round the core rib (frame 13)
    ]
    anim = ANIM.get(tag, {})
    return [common.palette_material(sprite, i, f"{tag}-anim{slot}" if slot in anim else tag, frames=anim.get(slot), **kw)
            for slot, (i, kw) in enumerate(specs)]


DECK, RIM_HI, RIM, GROOVE, PIT_BLUE, PIT, SEAM, LEG, LEG_HI, POD, CORE, RIB, FANG, POD_DIM, RIB_DIM, BROWN, PURPLE, \
    GAP, RIB_DIM_L, GLOW = range(20)

# Palette changes per frame (palette_material frames=), by model and material slot.
# newshc-1-f3: on frame 7 the pod reddens as it rises: its ribs turn red (the left one orange,
# rows 8-9 at column 8), the shell between them darkens and the pit round it goes black.
# newshc-1-f4: the core rib down the pod's middle (column 11) is only red on frame 9, bright
# yellow on 11 and white-hot on 13.
ANIM = {
    "newshc-1-f3": {PIT: {7: 1}, POD_DIM: {7: 67}, RIB_DIM: {7: 116}, RIB_DIM_L: {7: 122}},
    "newshc-1-f4": {CORE: {9: 117, 13: 127}},
}


def is_deck(r, c, v):
    if v < 0:
        return False
    inside = 3 <= c <= 19 and 4 <= r <= 23
    return 96 <= v <= 110 or (not inside and not 48 <= v <= 52)


def deck(bm, pixels):
    """The deck tile, its hatch frame and grooves, and a low floor under everything that isn't deck."""
    mask_plate(bm, pixels, is_deck, 0.0, DECK_TOP, DECK)
    mask_plate(bm, pixels, lambda r, c, v: v >= 0 and not is_deck(r, c, v) and 48 <= v <= 52, 0.0, 0.012, PIT_BLUE)
    mask_plate(bm, pixels, lambda r, c, v: v >= 0 and not is_deck(r, c, v) and not 48 <= v <= 52, 0.0, 0.01, PIT)
    # Hatch frame: a raised lip, lit on its left and top edges.
    lit = lambda r, c, v: is_deck(r, c, v) and ((c == 2 and 3 <= r <= 24) or (r == 3 and 2 <= c <= 20))  # noqa: E731
    shade = lambda r, c, v: is_deck(r, c, v) and ((c == 20 and 4 <= r <= 24) or (r == 24 and 3 <= c <= 19))  # noqa: E731
    mask_plate(bm, pixels, lit, DECK_TOP, DECK_TOP + 0.03, RIM_HI)
    mask_plate(bm, pixels, shade, DECK_TOP, DECK_TOP + 0.025, RIM)
    # Grooves between the deck plates (column 21, rows 0 and 25, and seams at columns 4, 10, 18 up top).
    groove = lambda r, c, v: is_deck(r, c, v) and (  # noqa: E731
        (c == 21 and 4 <= r <= 24) or r in (0, 25) or (c in (4, 10, 18) and r <= 2))
    mask_plate(bm, pixels, groove, DECK_TOP, DECK_TOP + 0.003, GROOVE)


def seam(bm, pts):
    """The raised diagonal seam where the hatch's two leaves meet: (column, row) points."""
    sweep(bm, [(X(c), Y(r), DECK_TOP + 0.004, 0.9 * PX, 0.018) for c, r in pts], sides=6, mat=SEAM)


def legs(bm, low):
    """The pod's two grey legs: from its sides (rows 11-13, columns 4-5 / 17-18), out over the
    knee (rows 14-17) and down to a foot on the ground (rows 18-20, columns 6-7 / 15-16)."""
    lift = 0.6 if low else 1.0
    for side in (-1, 1):
        def P(c, r, z, w, h):
            return (X(AXIS + side * (AXIS - c)), Y(r), z, w * PX, h)
        sweep(bm, [P(5.0, 10.6, 0.2 * lift, 0.0, 0.0), P(4.9, 11.2, 0.22 * lift, 1.2, 0.05),
                   P(5.0, 13.4, 0.22 * lift, 1.3, 0.06), P(5.4, 15.4, 0.17 * lift, 2.0, 0.07),
                   P(6.0, 17.2, 0.11 * lift, 1.8, 0.06), P(6.6, 19.0, 0.05, 1.2, 0.04),
                   P(6.7, 20.4, 0.03, 1.0, 0.03), P(6.7, 20.8, 0.02, 0.0, 0.0)], sides=8, mat=LEG)
        # The lit outer face of the knee (the bright 10-12 pixels at column 4, rows 14-16).
        sweep(bm, [P(4.4, 13.8, 0.2 * lift, 0.0, 0.0), P(4.3, 14.4, 0.2 * lift, 0.6, 0.03),
                   P(4.5, 16.4, 0.15 * lift, 0.6, 0.03), P(4.8, 17.0, 0.12 * lift, 0.0, 0.0)], sides=6, mat=LEG_HI)


def pod(bm, raised):
    """The red pod (columns 7-15, rows 7-14): a ribbed dome, glowing when raised, with three
    fangs hanging off its front (rows 12-14)."""
    z, rz = (0.12, 0.2) if raised else (0.0, 0.2)
    body, core, rib, rib_l = (POD, CORE, RIB, RIB) if raised else (POD_DIM, RIB_DIM, RIB_DIM, RIB_DIM_L)
    cx = X(AXIS)
    ellipsoid(bm, cx, Y(9.4), z, 4.6 * PX, 3.0 * PX, rz, body, segments=16, rings=8, dome=not raised)
    top = z + rz
    # Ribs over the top: the bright column 11 (core) and columns 8 and 14.
    for dc, mat, w in ((0, core, 1.3), (-3, rib_l, 0.8), (3, rib, 0.8)):
        x = X(AXIS + dc)
        k = (1 - (dc / 4.6) ** 2) ** 0.5
        sweep(bm, [(x, Y(7.0), top - rz * 0.6 * k, 0.0, 0.0), (x, Y(7.6), top - rz * 0.2 - (1 - k) * rz, w * PX, 0.02),
                   (x, Y(9.4), top * 1.0 - (1 - k) * rz * 0.9 + 0.005, w * PX, 0.025),
                   (x, Y(11.2), top - rz * 0.25 - (1 - k) * rz, w * PX, 0.02),
                   (x, Y(11.8), top - rz * 0.6 * k, 0.0, 0.0)], sides=6, mat=mat)
    if raised:
        # Fangs hanging off the front (columns 7-8, 10-12 and 14, rows 12-14).
        for c, w, r1 in ((7.5, 1.0, 14.2), (11.0, 1.5, 13.6), (14.4, 0.8, 13.8)):
            sweep(bm, [(X(c), Y(11.0), z + 0.06, w * PX, 0.06), (X(c), Y(12.6), z + 0.02, w * 0.8 * PX, 0.045),
                       (X(c), Y(r1), z - 0.04, 0.0, 0.0)], sides=6, mat=FANG)


def glow(bm):
    """Frame 13's glow round the core rib: the raised pod's columns 10-12 (rows 7-12) turn yellow.
    A wide band along the core rib's path, just under it."""
    z, rz = 0.12, 0.2
    top = z + rz
    x = X(AXIS)
    sweep(bm, [(x, Y(7.0), top - rz * 0.6 - 0.008, 0.0, 0.0), (x, Y(7.6), top - rz * 0.2 - 0.008, 1.7 * PX, 0.025),
               (x, Y(9.4), top - 0.004, 1.7 * PX, 0.03), (x, Y(11.2), top - rz * 0.25 - 0.008, 1.7 * PX, 0.025),
               (x, Y(11.8), top - rz * 0.6 - 0.008, 0.0, 0.0)], sides=8, mat=GLOW)


def build(name, sprite, frame):
    coll = common.reset_collection(name)
    mats = materials(sprite, name)
    pixels = frame["pixels"]
    bm = bmesh.new()
    deck(bm, pixels)
    if name == "newshc-1":
        seam(bm, [(6.0, 9.0), (8.5, 10.0), (10.6, 11.0), (12.0, 13.0), (12.4, 14.6), (14.0, 16.4),
                  (16.0, 18.4), (17.8, 20.2), (19.4, 22.8)])
    elif name == "newshc-1-f2":
        seam(bm, [(13.6, 14.6), (14.5, 16.4), (16.0, 18.4), (17.8, 20.2), (19.4, 22.8)])
        # A brown dome showing in the gap (columns 7-12, rows 7-11) with a purple glint.
        ellipsoid(bm, X(9.8), Y(9.4), 0.0, 3.6 * PX, 2.6 * PX, 0.055, BROWN, segments=12, rings=6, dome=True)
        ellipsoid(bm, X(11.2), Y(10.2), 0.04, 1.2 * PX, 1.0 * PX, 0.02, PURPLE, segments=8, rings=4)
    elif name == "newshc-1-f3":
        pod(bm, raised=False)
        legs(bm, low=True)
    else:
        pod(bm, raised=True)
        legs(bm, low=False)
    objs = [to_object(name, bm, mats, coll)]
    if name == "newshc-1-f4":
        gbm = bmesh.new()
        glow(gbm)
        objs.append(common.frame_part(to_object(f"{name}-glow-13", gbm, mats, coll), [13]))
    return objs


def main():
    sprite = common.load_sprite(ROOT, NAME)
    by_index = {f["index"]: f for f in sprite["frames"]}
    out = preview_args()
    frames_out = frames_arg()
    for name, frames in STAGES.items():
        frame = by_index[frames[0]]
        objs = build(name, sprite, frame)
        common.export_sprite_model(ROOT, objs, f"enemies/{name}", subset(sprite, frames))
        if out:
            ref = ROOT / "reference" / "models" / NAME / frame["image"]
            common.render_preview(objs, str(out.with_name(f"{name}.png")), ref, size=frame["size"], frame=frames[0])
        if frames_out:
            frame_previews(ROOT, objs, frames_out.with_name(f"{name}.png"), sprite, frames)


if __name__ == "__main__":
    main()
