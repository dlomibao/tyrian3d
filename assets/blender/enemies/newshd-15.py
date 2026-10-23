"""Rock edge, lower-left corner (newshd.shp frame 15): a 3D version of its sprite.

Seen in level 1.5. A 12x14 tile that is almost empty: only a dark sliver of rock in its
bottom-left corner (columns 0-2, rows 9-13), the edge of a rock that carries on past the tile.
It is built as the corner of a dark, partly buried boulder rising towards the tile's corner,
kept inside the sprite's silhouette and painted with the sprite's own greys (lib_b137).

Run: blender --background --python assets/blender/enemies/newshd-15.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b137 as lib  # noqa: E402

common = lib.common
NAME = "newshd-15"
MODEL = f"enemies/{NAME}"
ROOT = lib.ROOT
SHADES = [3, 4, 5, 6]

# (col, row, half-width px, half-length px, rotation deg, height units): centred past the corner.
BOULDERS = [(-1.5, 14.5, 4.0, 6.5, 0, 0.22, {"subdiv": 2})]


def main():
    g, sprite = lib.sprite_grid(NAME)
    obj = lib.rock_object(NAME, g, sprite, BOULDERS, SHADES, seed=15, tag=NAME,
                          apron_kw={"inset": 0.8, "height": 0.06})
    lib.cut_box(obj, -0.5, 0.5, -7 / 12, 7 / 12)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
