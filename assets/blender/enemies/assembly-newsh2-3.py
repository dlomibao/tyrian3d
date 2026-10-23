"""Long pipe (newsh2.shp frames 1, 3 and 5): a 3D version of its sprites.

Seen in levels 1.3 and 3.17. Nine 2x2 enemies in a row make one 216 x 28 px pipe lying on the
ground (sprite.json `assemblyLayout`): newsh2-1 is its left end (a rounded grey cap, a red
coupling, a grey can and a big red end flange), newsh2-3 is the repeating section (seven of them:
a grey can, a red flange, a grey can, a thin red coupling, a grey can, a thin red coupling) and
newsh2-5 is the right end, a grey cone that tapers to a point. The thin red couplings rest on
dark saddles on the ground.

The pipe is built whole in assembly coordinates and cut into its pieces with
common.split_assembly; every newsh2-3 is the same, so the section is periodic and only one of
them is exported. The grey cans and red flanges take the sprite's colour under each upward
facet (lit on top, dark on the shadowed side); facets underneath stay dark.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-3.py [-- --preview out.png]
(the preview is the whole pipe; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b120 as lib  # noqa: E402

NAME = "assembly-newsh2-3"
ROOT = common.repo_root(__file__)
PIECES = ["newsh2-1", "newsh2-3", "newsh2-5"]
W, H = 216, 28  # the assembly grid in pixels; its centre is the Blender origin
PX = 1 / 12
AXIS = 13.0  # pixel-edge row of the pipe's axis
ZA = 0.39  # height of the pipe's axis
ZS = 0.055  # height per pixel of radius (the pipe is a little flatter than round)


def XE(e):
    """Grid pixel edge (column) to Blender X."""
    return (e - W / 2) / 12


def YE(e):
    """Grid pixel edge (row) to Blender Y."""
    return (H / 2 - e) / 12


# Palette slots: grey shades, red shades, the dark brown of the saddles.
GREYS = [2, 4, 6, 8, 10, 12]
REDS = [66, 69, 72, 75, 78]
BROWN = 16


def build(sprite, grid):
    coll = common.reset_collection(NAME)
    tag = "nsh2a3"
    mats = []
    slot = {}
    for i in GREYS:
        slot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, tag, metallic=0.35, roughness=0.4))
    for i in REDS:
        slot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, tag, metallic=0.25, roughness=0.45))
    slot[BROWN] = len(mats)
    mats.append(common.palette_material(sprite, BROWN, tag, metallic=0.2, roughness=0.8))
    DARK, RED_DARK, SADDLE = slot[2], slot[66], slot[BROWN]

    def slot_for(idx):
        if 1 <= idx <= 13:
            return slot[min(GREYS, key=lambda g: abs(g - max(idx, 2)))]
        if 64 <= idx <= 79:
            return slot[min(REDS, key=lambda g: abs(g - max(idx, 66)))]
        if 16 <= idx <= 21:
            return SADDLE
        return None

    def sample(x, y):
        c = math.floor(x * 12 + W / 2)
        r = math.floor(H / 2 - y * 12)
        if 0 <= r < H and 0 <= c < W:
            return grid[r][c]
        return None

    bm = bmesh.new()

    def tube(profile, mat, centre=AXIS, sides=16):
        """A tube along +X: profile is (column edge, radius px); painted from the sprite on top."""
        first = len(bm.faces)
        lib.sweep(bm, [(XE(e), YE(centre), ZA, r * PX, r * ZS) for e, r in profile],
                  sides=sides, mat=mat)
        lib.paint(bm, first, sample, slot_for)

    def can(e0, e1, r=5.3):
        tube([(e0, r * 0.7), (e0 + 0.35, r * 0.94), (e0 + 0.9, r), (e1 - 0.9, r), (e1 - 0.35, r * 0.94),
              (e1, r * 0.7)], DARK)

    def flange(e0, e1, r):
        tube([(e0, r * 0.9), (e0 + 0.3, r), (e1 - 0.3, r), (e1, r * 0.9)], RED_DARK, sides=18)

    def neck(e0, e1):
        tube([(e0, 2.6), (e1, 2.6)], RED_DARK, centre=11.8, sides=10)
        lib.box(bm, XE(e0 + 0.4), YE(17.0), XE(e1 - 0.4), YE(14.6), 0.0, ZA - 0.05, mat=SADDLE)

    # Left end (newsh2-1, columns 0-23): rounded cap and can, coupling, can, big end flange.
    tube([(0.9, 0.0), (1.2, 2.6), (1.8, 4.0), (2.6, 4.8), (3.6, 5.3), (9.9, 5.3), (10.6, 4.9),
          (11.0, 3.8)], DARK)
    neck(10.8, 14.2)
    can(14.0, 19.0)
    flange(19.0, 24.0, 7.0)

    # Seven repeating sections (newsh2-3): can, flange, can, coupling, can, coupling, can...
    for t in range(1, 8):
        o = 24 * t
        # The can across the section's left edge (its rim is the previous section's column 23;
        # the first one starts inside the end flange), so every section is cut alike.
        can(o - 0.8, o + 3.0)
        flange(o + 3.0, o + 7.0, 6.2)
        can(o + 7.0, o + 11.6)
        neck(o + 11.4, o + 15.2)
        can(o + 15.0, o + 19.5)
        neck(o + 19.3, o + 23.4)

    # Right end (newsh2-5, columns 192-215): a cone tapering to a point.
    o = 192
    tube([(o - 0.8, 5.0), (o - 0.4, 5.3), (o + 5, 5.0), (o + 9, 4.2), (o + 13, 3.2), (o + 16, 2.3), (o + 18.5, 1.4),
          (o + 20.2, 0.6), (o + 20.8, 0.0)], DARK)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    grid, colors, x0, y0, layout = lib.assembly_grid(ROOT, "newsh2-3")
    sprite = common.load_sprite(ROOT, "newsh2-3")
    sprite["colors"] = colors
    obj = build(sprite, grid)
    seen = set()
    pieces_layout = []
    for e in layout:  # newsh2-3 repeats; its first copy (left of the row) is the one exported
        if e["model"] in seen:
            continue
        if e["model"] == "newsh2-3" and e["cx"] != min(f["cx"] for f in layout if f["model"] == "newsh2-3"):
            continue
        seen.add(e["model"])
        pieces_layout.append((e["model"], e["cx"] - x0 - W / 2, e["cy"] - y0 - H / 2))
    out = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    lib.export_assembly(ROOT, obj, pieces_layout, out, grid, colors, None)


if __name__ == "__main__":
    main()
