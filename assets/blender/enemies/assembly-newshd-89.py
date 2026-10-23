"""Big rock heap (newshd.shp, assembly of 6 pieces): a 3D version of its sprites.

Seen in level 1.5. Six 2x2 ground enemies (newshd-13, -49, -51, -53, -89, -91) make one grey
boulder heap, 72 x 84 px with its corners missing: a pointed rock on top (newshd-13), a wide band
of rocks across the middle with a big round rock ringed by bright edges at its centre, and a
lower right lobe of darker, smaller rocks. It is lit from the upper left like the rock heap
above it (assembly-newshd-39), whose method this follows.

The heap is built once in assembly coordinates (lib_b137): a low rubble apron that follows the
sprite's outline, with faceted, partly buried boulders on it where the sprite shows lumps, all
kept inside the silhouette. Each face takes the grey of the sprite pixels under it (palette
indices 4-14). Then common.split_assembly cuts it into the 6 pieces.

Run: blender --background --python assets/blender/enemies/assembly-newshd-89.py [-- --preview out.png]
(the preview is the whole heap; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b137 as lib  # noqa: E402

common = lib.common
NAME = "assembly-newshd-89"
ROOT = lib.ROOT
PIECES = ["newshd-13", "newshd-49", "newshd-51", "newshd-53", "newshd-89", "newshd-91"]
# The assembly is 72 x 84 px (pieces at screen cx 122-170, cy 85-141); its centre, screen
# (146, 113), is the Blender origin. Grid (0, 0) is its top-left pixel.
CX0, CY0 = 146, 113
W, H = 72, 84
SHADES = list(range(4, 15))

# Boulders: (col, row, half-width px, half-length px, rotation deg, height units).
BOULDERS = [
    # newshd-13: the pointed rock on top and the rocks under it
    (33.5, 11.5, 8.0, 7.5, 0, 0.66, {"peak": 1.6}),  # pointed top rock, bright peak
    (44.0, 12.5, 4.0, 7.0, 0, 0.38),  # dark rock sloping away on its right
    (28.0, 20.5, 4.5, 4.0, 0, 0.45),  # rock on the left under it
    (37.0, 20.5, 4.0, 3.6, 0, 0.4),  # middle rock with the dark cracks
    (44.0, 22.0, 4.0, 6.0, 0, 0.45),  # right rock, bright ridge down its left edge
    # the centre: the big round rock with the bright rim and its smaller twin
    (31.0, 30.0, 7.0, 6.0, 0, 0.72, {"peak": 0.6}),
    (41.0, 29.5, 4.5, 5.5, 0, 0.6),
    (33.0, 40.0, 7.0, 4.0, 0, 0.42),  # saddle under them
    # newshd-49: the left wing
    (12.0, 32.5, 7.0, 5.0, -10, 0.45),
    (12.0, 42.5, 9.0, 6.5, 0, 0.58),  # bright rock
    (5.0, 39.0, 3.0, 4.0, 0, 0.32),
    (16.0, 51.0, 7.0, 4.5, -10, 0.4),
    (22.5, 45.5, 3.5, 5.0, 0, 0.42),
    # newshd-51 / -53: the middle and right of the band
    (30.0, 48.0, 6.0, 7.0, 0, 0.58),  # bright rock under the saddle
    (39.5, 48.5, 4.0, 6.5, 0, 0.45),  # rock with the bright left edge
    (52.0, 31.5, 6.0, 4.5, 0, 0.45),
    (54.0, 40.0, 6.0, 4.5, 0, 0.42),
    (61.0, 41.5, 5.5, 5.0, 0, 0.4),
    (58.5, 50.0, 8.0, 6.5, 15, 0.62, {"peak": 0.6}),  # bright ringed rock
    (44.0, 40.0, 4.0, 5.5, 0, 0.3),  # low rock in the dark crevice
    (21.5, 38.5, 3.5, 3.5, 0, 0.36),  # fill between the left wing and the centre
    (46.5, 32.0, 3.0, 3.5, 0, 0.36),
    (24.0, 54.0, 4.0, 2.5, 0, 0.3),
    (47.5, 51.0, 3.5, 6.0, 0, 0.36),
    (46.0, 60.5, 3.0, 3.5, 0, 0.32),
    (23.5, 33.0, 3.0, 4.0, 0, 0.34),
    # newshd-89 / -91: the lower lobe
    (28.0, 60.0, 5.0, 5.0, 0, 0.5),  # bright rock
    (35.0, 64.0, 6.0, 5.0, 0, 0.42),  # dark rocks
    (41.5, 69.5, 5.0, 5.0, 0, 0.36),
    (29.0, 70.5, 5.0, 4.0, 0, 0.26),
    (52.5, 58.0, 5.0, 4.0, 0, 0.45),
    (55.5, 64.5, 5.0, 4.0, 0, 0.48),  # bright rock
    (64.0, 61.5, 6.0, 8.0, 0, 0.42),
    (50.0, 71.0, 6.0, 5.0, 0, 0.34),
    (62.5, 72.0, 6.0, 5.0, 0, 0.3),
]


def merged_sprite():
    """newshd-13's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, PIECES[0])
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def main():
    sprite = merged_sprite()
    g = lib.assembly_grid(PIECES, W, H, CX0, CY0)
    obj = lib.rock_object(NAME, g, sprite, BOULDERS, SHADES, seed=89, tag="nshd89",
                          apron_kw={"inset": 3.0, "height": 0.24})
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        # The 72 x 84 grid already has the 12:14 shape render_preview expects (size 6 = 72 px).
        ref = lib.grid_png(g, sprite["colors"], Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=6, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
