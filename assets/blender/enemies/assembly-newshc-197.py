"""Green tank bar (newshc.shp frames 197/201/205 and 199/203/207, two pieces): a 3D version of
its sprites.

Seen in episode 1 (level 1.19) and 3 (levels 3.6 and 3.23), at the tail of a column of enemies.
Two 2x2 enemies side by side make one 48x28 px bar (sprite.json `assemblyLayout`; the other
pieces in that layout are separate enemies with their own models): two green tanks lying across
the screen either side of a pink spine block, a pink bar beneath them with a bulb at each end,
dark purple fins hanging below, and a red light between the fins. The three frames of each piece
only brighten the red light, so one model per piece covers them.

The bar is mirror symmetric about the seam between the pieces, so the left half is built
(lib_b031.stock_half, shared with the big gun's stock newshc-269) and mirrored, then cut into
the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshc-197.py [-- --preview out.png]
(the preview is the whole bar; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b031 as lib  # noqa: E402

NAME = "assembly-newshc-197"
ROOT = common.repo_root(__file__)
PIECES = ["newshc-197", "newshc-199"]
# Assembly image: 48 x 28 px, newshc-197 in columns 0-23 and newshc-199 in 24-47; its centre
# (the seam, screen x 69, y 123) is the Blender origin.
CX0, CY0 = 69, 123
WIDTH = 48
DZ = -0.6


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshc197"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(40, metallic=0.3, roughness=0.45),  # 0 green tanks
        pal(36, metallic=0.3, roughness=0.55),  # 1 dark green rings
        pal(89, metallic=0.35, roughness=0.45),  # 2 pink bar
        pal(92, metallic=0.4, roughness=0.35),  # 3 pale pink edge
        pal(81, metallic=0.2, roughness=0.7),  # 4 dark fin block
        pal(85, metallic=0.3, roughness=0.55),  # 5 fins
        pal(87, metallic=0.3, roughness=0.5),  # 6 lighter fins
        pal(90, metallic=0.35, roughness=0.4),  # 7 pink spine
        pal(119, emission_strength=4.0),  # 8 red light
    ]
    slots = {"tank": 0, "ring": 1, "bar": 2, "bar_hi": 3, "fin_base": 4, "fin": 5, "fin_hi": 6, "spine": 7}
    bm = bmesh.new()
    lib.stock_half(bm, slots, c0=0, w=WIDTH, dz=DZ)
    # Red light between the fins (columns 21-26, rows 14-17).
    lib.box(bm, 21.0, 13.8, 24.0, 18.2, -2.4 + DZ, 0.2 + DZ, mat=8, xy=(WIDTH, lib.H))
    lib.mirror_x(bm, 24.0, xy=(WIDTH, lib.H))
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        out = Path(out)
        # The bar in the middle of a 48 x 56 image (the 24:28 shape render_preview expects).
        ref = lib.composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56, 24, 28)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
