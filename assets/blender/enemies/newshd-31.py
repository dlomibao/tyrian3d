"""Rock edge, lower-right slope (newshd.shp frame 31): a 3D version of its sprite.

Seen in level 1.5. A 12x14 tile with the edge of a grey rock filling its lower-right half
behind a diagonal outline: dark at the edge, lighter (a lit lump at columns 8-9, rows 8-10, and
a lit ledge along the bottom) where it rises towards the tile's bottom-right corner, where the
rock carries on past the tile. Built as faceted, partly buried boulders rising towards that
corner, kept inside the silhouette and painted with the sprite's own greys (lib_b137).

Run: blender --background --python assets/blender/enemies/newshd-31.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b137 as lib  # noqa: E402

common = lib.common
NAME = "newshd-31"
MODEL = f"enemies/{NAME}"
ROOT = lib.ROOT
SHADES = [3, 4, 5, 6, 7, 8, 9, 10]

# (col, row, half-width px, half-length px, rotation deg, height units)
BOULDERS = [
    (12.0, 14.0, 7.5, 9.0, 0, 0.42, {"subdiv": 3}),  # the rock's shoulder, rising to the corner
    (8.8, 9.0, 2.0, 2.2, 0, 0.32),  # lit lump
    (5.5, 13.5, 3.5, 2.0, 0, 0.22),  # lit ledge along the bottom
]


def main():
    g, sprite = lib.sprite_grid(NAME)
    obj = lib.rock_object(NAME, g, sprite, BOULDERS, SHADES, seed=31, tag=NAME,
                          apron_kw={"inset": 1.5, "height": 0.08})
    lib.cut_box(obj, -0.5, 0.5, -7 / 12, 7 / 12)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
