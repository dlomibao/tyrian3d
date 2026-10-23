"""Grey dome (newshh.shp frame 79): a 3D version of its sprite.

Seen in episode 2 (level 2.4). The sprite is only the bottom half of its tile: the rounded top
of a smooth grey shell, 24 px wide, cut off flat by the tile's lower edge. It is lit from the top
left (a white highlight in the middle of the upper rows) with a pale glint down the right edge.
The model is a lofted shell that follows the sprite's width row by row, swelling from a thin
top edge to its full thickness at the cut, with its facets coloured by the grey under them.
One frame.

Run: blender --background --python assets/blender/enemies/newshh-79.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b063 as lib  # noqa: E402

NAME = "newshh-79"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
HMAX = 0.28  # half thickness at the cut


def build(sprite):
    coll = common.reset_collection(NAME)
    pixels = sprite["frames"][0]["pixels"]
    ramp = sorted(int(k) for k in sprite["colors"])
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [pal(i, metallic=0.15, roughness=0.25 if i > 107 else 0.4) for i in ramp]

    def slot_of(i):
        return ramp.index(i) if i in ramp else None

    ext = lib.extents(pixels)
    rows = sorted(ext)
    wmax = max((b - a + 1) / 2 for a, b in ext.values())
    sections = []
    inset = 0.35

    def section(y, r):
        a, b = ext[r]
        w = (b - a + 1) / 2 - inset
        # A rounded top: the thickness follows how far the row has widened.
        t = (w / (wmax - inset)) ** 1.6
        return (y, (lib.px(a) + lib.px(b)) / 2, w / 12, max(0.04, HMAX * t), 0.0)

    top = rows[0]
    y0, xc, w, h, z = section(lib.row(top), top)
    sections.append((lib.row(top - 0.5), xc, w * 0.85, h * 0.4, z))
    for r in rows:
        sections.append(section(lib.row(r), r))
    # The cut along the tile's bottom edge.
    y, xc, w, h, z = section(lib.row(rows[-1]), rows[-1])
    sections.append((lib.row(rows[-1] + 0.48), xc, w, h, z))

    bm = bmesh.new()
    lib.loft_x(bm, sections, sides=32, phase=0.5)
    lib.paint(bm, pixels, slot_of, under_slot=ramp.index(100), min_nz=-0.3)
    # The flat cut at the bottom edge shows the shell's darkest grey.
    for f in bm.faces:
        if f.normal.y < -0.9:
            f.material_index = 0
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
