"""Big blue gun (newshc.shp frames 269, 271 and 273, three pieces): a 3D version of its sprites.

Seen in episode 1 (level 1.19) and 3 (level 3.23). Three 2x2 enemies side by side make one
72x28 px gun pointing right (sprite.json `assemblyLayout`): a stock at the left (newshc-269, the
same tank-and-fins shape as the green bar newshc-197, here a grey tank on a blue bar), a receiver
in the middle (newshc-271) with a raised sight block on top and a grip hanging below, mounted on
a purple backing plate that fills the rest of that piece, and a ringed barrel at the right
(newshc-273) with a frame under it and a red glow under the muzzle. Each piece has one frame.

The whole gun is built once in assembly coordinates and cut into the pieces with
common.split_assembly. The muzzle's end cap is a separate sprite, newshc-275.

Run: blender --background --python assets/blender/enemies/assembly-newshc-271.py [-- --preview out.png]
(the preview is the whole gun; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b031 as lib  # noqa: E402

NAME = "assembly-newshc-271"
ROOT = common.repo_root(__file__)
PIECES = ["newshc-269", "newshc-271", "newshc-273"]
# Assembly image: 72 x 28 px, newshc-269 in columns 0-23, newshc-271 in 24-47 and newshc-273 in
# 48-71; its centre (screen x 122, y -18) is the Blender origin.
CX0, CY0 = 122, -18
WIDTH = 72
XY = (WIDTH, lib.H)
DZ = -0.5


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshc271"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.6, roughness=0.35),  # 0 grey tank
        pal(4, metallic=0.5, roughness=0.5),  # 1 dark grey rings
        pal(56, metallic=0.45, roughness=0.4),  # 2 blue bar, barrel
        pal(61, metallic=0.5, roughness=0.3),  # 3 pale blue edges
        pal(49, metallic=0.3, roughness=0.6),  # 4 dark fin block
        pal(52, metallic=0.4, roughness=0.5),  # 5 fins, grip
        pal(54, metallic=0.4, roughness=0.45),  # 6 lighter fins, frame
        pal(57, metallic=0.45, roughness=0.4),  # 7 spine, sight block
        pal(53, metallic=0.4, roughness=0.45),  # 8 receiver
        pal(58, metallic=0.45, roughness=0.35),  # 9 light plates
        pal(50, metallic=0.3, roughness=0.55),  # 10 dark magazine
        pal(55, metallic=0.4, roughness=0.4),  # 11 grip edge
        pal(86, metallic=0.2, roughness=0.65),  # 12 purple backing plate
        pal(81, metallic=0.2, roughness=0.7),  # 13 dark slot in the plate
        pal(120, emission_strength=4.0),  # 14 red glow
        pal(125, emission_strength=6.0),  # 15 hot centre of the glow
    ]
    (TANK, RING, BAR, PALE, FIN_BASE, FIN, FIN_HI, SPINE, RECEIVER, PLATE, MAG, EDGE, PURPLE, SLOT,
     GLOW, HOT) = range(16)
    slots = {"tank": TANK, "ring": RING, "bar": BAR, "bar_hi": PALE, "fin_base": FIN_BASE, "fin": FIN,
             "fin_hi": FIN_HI, "spine": SPINE}
    bm = bmesh.new()

    # Stock (newshc-269): the shared tank-and-fins half; nothing under the spine there.
    lib.stock_half(bm, slots, c0=0, w=WIDTH, dz=DZ, fin_end=21.2)
    lib.box(bm, 24.0, 1.6, 26.2, 12.6, -1.4 + DZ, 3.8 + DZ, mat=SPINE, xy=XY)

    # Receiver (columns 26-33, rows 3-14) with a light plate on its top.
    lib.box(bm, 25.8, 2.8, 34.2, 14.4, -1.8 + DZ, 2.8 + DZ, mat=RECEIVER, bevel=0.5, xy=XY)
    lib.box(bm, 29.6, 3.0, 33.4, 7.4, 2.0 + DZ, 3.3 + DZ, mat=PLATE, bevel=0.3, xy=XY)
    # Sight block on top (columns 34-41, rows 1-8) with a pale front edge.
    lib.box(bm, 33.8, 1.0, 42.2, 9.0, -1.0 + DZ, 3.4 + DZ, mat=SPINE, bevel=0.6, xy=XY)
    lib.loft_x(bm, 2.3, [(34.6, 0.0, 0.0, 3.0 + DZ), (35.2, 0.6, 0.4, 3.1 + DZ), (40.8, 0.6, 0.4, 3.1 + DZ),
                         (41.4, 0.0, 0.0, 3.0 + DZ)], sides=6, mat=PALE, xy=XY)
    # Grip hanging below (columns 29-42, rows 13-24): a dark block with a light L-shaped edge, a
    # darker magazine in the middle and a strip down its right side.
    lib.box(bm, 29.6, 12.8, 42.4, 24.2, -2.6 + DZ, 0.6 + DZ, mat=FIN, bevel=0.4, xy=XY)
    lib.box(bm, 30.0, 15.0, 33.0, 23.6, -1.0 + DZ, 1.3 + DZ, mat=EDGE, bevel=0.25, xy=XY)
    lib.box(bm, 30.0, 21.0, 42.0, 23.8, -1.0 + DZ, 1.1 + DZ, mat=FIN_HI, bevel=0.25, xy=XY)
    lib.box(bm, 34.0, 12.8, 39.0, 20.6, -1.0 + DZ, 1.5 + DZ, mat=MAG, bevel=0.3, xy=XY)
    lib.box(bm, 40.0, 15.0, 42.0, 22.8, -1.0 + DZ, 1.0 + DZ, mat=FIN, bevel=0.2, xy=XY)
    # Purple backing plate filling the rest of newshc-271, with a dark slot on its right.
    lib.box(bm, 24.05, 0.05, 47.95, 27.95, -3.6 + DZ, -2.8 + DZ, mat=PURPLE, xy=XY)
    lib.box(bm, 44.0, 15.4, 46.0, 24.6, -2.8 + DZ, -2.6 + DZ, mat=SLOT, xy=XY)

    # Barrel along the sprite (row 5.5): thick from the sight block to column 52, then thin with
    # two rings, ending in the muzzle block (columns 67-71).
    lib.loft_x(bm, 5.5, [(41.0, 2.9, 2.4, 1.0 + DZ), (52.2, 2.9, 2.4, 1.0 + DZ), (52.2, 1.7, 1.5, 1.0 + DZ),
                         (56.8, 1.7, 1.5, 1.0 + DZ), (56.8, 2.4, 2.0, 1.0 + DZ), (59.0, 2.4, 2.0, 1.0 + DZ),
                         (59.0, 1.7, 1.5, 1.0 + DZ), (63.8, 1.7, 1.5, 1.0 + DZ), (63.8, 2.3, 1.9, 1.0 + DZ),
                         (67.0, 2.3, 1.9, 1.0 + DZ)], sides=12, mat=BAR, xy=XY)
    lib.loft_x(bm, 5.2, [(66.8, 3.4, 2.4, 1.0 + DZ), (72.0, 3.4, 2.4, 1.0 + DZ)],
               sides=12, mat=SPINE, power=0.6, xy=XY)
    # Lower rail under the receiver's front (columns 39-50, rows 9-13).
    lib.loft_x(bm, 11.4, [(38.8, 2.2, 1.6, 0.0 + DZ), (50.0, 2.2, 1.6, 0.0 + DZ), (50.8, 1.2, 0.9, 0.0 + DZ)],
               sides=10, mat=BAR, power=0.7, xy=XY)
    # Frame under the barrel (columns 55-65, rows 7-12): two posts and a bottom rail.
    lib.box(bm, 54.8, 6.6, 57.0, 12.8, -1.2 + DZ, 1.0 + DZ, mat=FIN_HI, bevel=0.2, xy=XY)
    lib.box(bm, 62.0, 6.6, 66.0, 12.8, -1.2 + DZ, 1.0 + DZ, mat=FIN_HI, bevel=0.2, xy=XY)
    lib.box(bm, 54.8, 10.8, 66.0, 12.8, -1.2 + DZ, 0.6 + DZ, mat=FIN, xy=XY)
    # Red glow under the muzzle (columns 66-71, rows 8-10), hottest at its back.
    lib.ellipsoid(bm, 69.2, 9.6, -0.2 + DZ, 3.0, 1.6, 1.4, mat=GLOW, segments=12, rings=6, xy=XY)
    lib.ellipsoid(bm, 67.8, 9.5, 0.2 + DZ, 1.2, 1.0, 1.2, mat=HOT, segments=10, rings=5, xy=XY)

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
        # The gun in the middle of a 72 x 84 image (the 24:28 shape render_preview expects).
        ref = lib.composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 72, 84, 36, 42)
        common.render_preview([obj], str(out), ref, size=6, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
