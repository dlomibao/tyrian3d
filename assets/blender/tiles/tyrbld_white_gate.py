"""The white gates set into the edges of TYRIAN's rock islands (map 1-9, layer 2; 2x2 patterns
185/186/195/196 on an island's west edge and 187/188/197/198 on an east edge), after the concepts
assets/blender/features/concepts/tyr-white-gate-w.jpg and tyr-white-gate-e.jpg: three courses of
white marble blocks with chamfered, pillowed edges, held by two L-shaped riveted brass straps (a
Greek-key step inlaid along each), the lowest course's front face sloping down to the rock (on the
west gate with a dark doorway in it), set into the island's cobbled rock with the rim rock and the
dark gap at the island's edge. The east gate's courses are split into a big and a small block.

No enemies sit on them; they are drawn in the Background3Over pass (rows 199-324), so everything
stays under L2_OVER_MAX. They replace their tiles, so each model also carries its tiles' rock
(Structure.rock).

`--marble` (plain Python, after concept_maps and before the bake) redoes detail.png on the block
tops: concept_maps clips the bright marble to a flat 1.0 (its mid-tone term lifts anything brighter
than the concept's mean), which loses the veins. Here the concept's own veining is kept, normalised
inside each block top only. Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_white_gate.py
    python tools/concept_maps.py tile:shapesz-tyrbld-white-gate-w --concept tyr-white-gate-w --span 0,0,1,1 --px 32
    python tools/concept_maps.py tile:shapesz-tyrbld-white-gate-e --concept tyr-white-gate-e --span 0,0,1,1 --px 32
    python assets/blender/tiles/tyrbld_white_gate.py --marble
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-white-gate-w
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-white-gate-e
"""

import sys
from pathlib import Path

if "--marble" not in sys.argv:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import lib_tyrbld as tb  # noqa: E402

# Pattern pixels (1x, the 48x56 2x2 pattern) read from the tiles' art and the concepts.
# blocks: (x0, y0, x1, y1) of each block's top; the lowest course also has a front face sloping
# from its top's front edge (y1) down to `face` (the art's dark band under it).
# straps: the brass L's, as (x0, y0, x1, y1) rectangles; key: the inlaid step along each L, as a
# polyline of (px, py) points; door: the dark doorway in the lowest course's face (x0, x1).
GATES = {
    "white-gate-w": dict(
        blocks=[(11.6, 4.0, 29.6, 10.8), (11.6, 15.0, 29.2, 23.6), (11.6, 29.0, 29.4, 38.0)],
        face=44.0,
        straps=[(29.6, 3.8, 33.9, 11.2), (10.8, 11.0, 33.9, 15.0),
                (11.2, 24.8, 33.9, 29.0), (29.6, 29.0, 33.9, 44.6)],
        keys=[[(11.6, 13.6), (19.0, 13.6), (19.0, 12.4), (31.8, 12.4), (31.8, 4.6)],
              [(11.8, 27.4), (17.0, 27.4), (17.0, 26.2), (31.8, 26.2), (31.8, 43.6)]],
        door=(12.6, 18.6),
    ),
    "white-gate-e": dict(
        blocks=[(18.0, 7.0, 29.4, 12.6), (30.4, 7.0, 35.0, 12.6),
                (14.8, 18.0, 31.0, 25.6), (31.8, 18.0, 35.0, 25.6),
                (18.0, 31.0, 28.6, 39.0), (29.4, 31.0, 35.0, 39.0)],
        face=44.0,
        straps=[(14.0, 7.0, 18.2, 14.2), (14.0, 14.0, 35.4, 18.0),
                (14.0, 26.8, 35.4, 31.0), (14.0, 31.0, 18.2, 44.6)],
        keys=[[(15.6, 7.6), (15.6, 16.6), (25.4, 16.6), (25.4, 15.4), (34.6, 15.4)],
              [(16.4, 43.6), (16.4, 28.4), (24.0, 28.4), (24.0, 29.6), (34.6, 29.6)]],
        door=None,
    ),
}
BLOCK_TOP = 0.35  # the marble blocks' top (the art's front band is about 6 px; cap 0.38)
BLOCK_FOOT = -0.04  # sunk into the rock slab
STRAP_TOP = 0.17  # the brass straps' plates
KEY_TOP = 0.22  # the inlaid key step on the straps, a clear step above the plate
KEY_W = 1.0  # px, the key's width
RIVET_R = 0.55  # px
FACE_FOOT = 0.02  # the lowest course's front face meets the rock here


def build(name):
    d = GATES[name]
    s = tb.Structure(name)
    # Marble: light grey (palette 12, 186) so the game light shades it and the baked veins show;
    # the lowest course's sloped face is the same marble at about 70% (palette 10, 142).
    white, white_shade = s.m(12, roughness=0.4), s.m(10, roughness=0.5)
    # Brass less metallic than the drums': the straps are flat plates seen from above, and the
    # concept paints them a bright worn gold.
    brass, brass_light = s.m("brass", metallic=0.35, roughness=0.45), s.m("brass_light", metallic=0.35, roughness=0.4)
    key_brass = s.m(26, metallic=0.35, roughness=0.35)  # the key strip, lighter than the plates
    dark = s.m("dark")

    # The brass straps: plates under the blocks' tops, with a bevelled edge.
    for x0, y0, x1, y1 in d["straps"]:
        s.wall_block(x0, y0, x1, y1, BLOCK_FOOT, STRAP_TOP, brass, bevel=0.25)
    # The inlaid key step along each strap, a raised lighter bar following the L.
    for key in d["keys"]:
        for (ax, ay), (bx, by) in zip(key, key[1:]):
            h = KEY_W / 2
            s.wall_block(min(ax, bx) - h, min(ay, by) - h, max(ax, bx) + h, max(ay, by) + h,
                         STRAP_TOP - 0.02, KEY_TOP, key_brass, bevel=0.3)
    # Rivets at the straps' ends and corners.
    for x0, y0, x1, y1 in d["straps"]:
        long_x = (x1 - x0) >= (y1 - y0)
        n = max(2, int(round(max(x1 - x0, y1 - y0) / 7.0)) + 1)
        for i in range(n):
            t = (i + 0.5) / n
            if long_x:
                pts = [(x0 + (x1 - x0) * t, y0 + 1.0)] if i % 2 == 0 else [(x0 + (x1 - x0) * t, y1 - 1.0)]
            else:
                pts = [(x0 + 1.0, y0 + (y1 - y0) * t)] if i % 2 == 0 else [(x1 - 1.0, y0 + (y1 - y0) * t)]
            for px, py in pts:
                s.dome(px, py, RIVET_R, RIVET_R, STRAP_TOP - 0.005, 0.025, brass_light, sides=8, rings=2)

    # The marble blocks: pillowed (chamfered) boxes.
    blocks = d["blocks"]
    low_y1 = max(b[3] for b in blocks)
    for x0, y0, x1, y1 in blocks:
        s.wall_block(x0, y0, x1, y1, BLOCK_FOOT, BLOCK_TOP, white, bevel=0.45)
        if y1 == low_y1:
            # The lowest course's front face: from the top's front edge down to the rock.
            # Rounded where the top turns down into the slope, and at the slope's foot.
            fx0, fx1 = x0, x1
            f = d["face"]
            prof = [(y1 - 0.6, BLOCK_FOOT), (y1 - 0.6, BLOCK_TOP - 0.03), (y1 + 0.3, BLOCK_TOP - 0.045),
                    (y1 + 1.0, BLOCK_TOP - 0.085), (y1 + 1.6, BLOCK_TOP - 0.14),
                    (f - 0.9, FACE_FOOT + 0.08), (f - 0.2, FACE_FOOT + 0.035), (f + 0.6, FACE_FOOT),
                    (f + 0.6, BLOCK_FOOT)]
            mats = [white, white, white, white_shade, white_shade, white_shade, white_shade, white_shade, white_shade]
            s.prism(prof, fx0 + 0.3, fx1 - 0.3, mat=white_shade, mats=mats)
    if d["door"]:
        # The dark doorway in the face: a dark recess with a lintel.
        dx0, dx1 = d["door"]
        fy0, fy1 = low_y1 + 2.2, d["face"] - 0.2

        def face_z(py):
            z0, z1 = BLOCK_TOP - 0.14, FACE_FOOT + 0.08
            return z0 + (z1 - z0) * (py - (low_y1 + 1.6)) / ((d["face"] - 0.9) - (low_y1 + 1.6))
        prof = [(fy0, BLOCK_FOOT), (fy0, face_z(fy0) + 0.012), (fy1, face_z(fy1) + 0.012), (fy1, BLOCK_FOOT)]
        s.prism(prof, dx0, dx1, mat=dark)

    # The island's rock: slab under everything, boulders where the art has stones (none under
    # the gate's own parts).
    keep_out = s.box_mask(0, 0, 0, 0)
    for x0, y0, x1, y1 in blocks + d["straps"]:
        keep_out |= s.box_mask(x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5)
    for x0, y0, x1, y1 in blocks:
        if y1 == low_y1:
            keep_out |= s.box_mask(x0 - 0.5, y1, x1 + 0.5, d["face"] + 1.0)
    s.rock(exclude=keep_out)

    objects = s.objects()
    s.check(objects)
    s.export(objects)


def marble():
    """Redo the block tops' detail in assets/blender/textures/<entry>/detail.png from the
    registered concept (see the module doc)."""
    import json

    import numpy as np
    from PIL import Image
    from scipy import ndimage

    root = Path(__file__).resolve().parents[3]
    for name, d in GATES.items():
        out = root / "assets" / "blender" / "textures" / f"shapesz-tyrbld-{name}"
        k = json.loads((out / "maps.json").read_text())["texels_per_px"]
        lum = np.asarray(Image.open(out / "concept.png").convert("L"), float) / 255.0
        detail = np.asarray(Image.open(out / "detail.png").convert("L"), float) / 255.0
        h, w = lum.shape
        tops = np.zeros((h, w), bool)
        for x0, y0, x1, y1 in d["blocks"]:
            tops[int((y0 + 0.5) * k):int((y1 - 0.5) * k), int((x0 + 0.5) * k):int((x1 - 0.5) * k)] = True
        # Blur inside the tops only, so the dark gaps round them don't lift the ratio at the edges.
        sig = 1.2 * k
        wsum = ndimage.gaussian_filter(tops.astype(float), sig)
        base = ndimage.gaussian_filter(np.where(tops, lum, 0.0), sig) / np.maximum(wsum, 1e-3)
        mean = lum[tops].mean()
        ratio = lum / np.maximum(base, 0.03)
        # Veins: the ratio, exaggerated; tone: a little of the concept's falloff across each block.
        mid = np.clip(base / mean, 0.8, 1.15) ** 0.6
        marble = np.clip(0.93 * ratio ** 2.5 * mid, 0.55, 1.0)
        feather = np.clip(ndimage.gaussian_filter(tops.astype(float), 0.15 * k) * 2 - 0.5, 0, 1)
        new = detail * (1 - feather) + marble * feather
        Image.fromarray((new * 255).round().astype(np.uint8)).save(out / "detail.png")
        sel = tops
        print(f"{name}: block-top detail mean {new[sel].mean():.3f}, p5 {np.percentile(new[sel], 5):.3f}, "
              f"p95 {np.percentile(new[sel], 95):.3f} (was {detail[sel].mean():.3f})")


if "--marble" in sys.argv:
    marble()
else:
    for name in GATES:
        build(name)
