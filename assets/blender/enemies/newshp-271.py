"""Twin-cannon ground turret (newshp.shp frames 271, 273, 275, 277): a 3D version of its sprites.

Seen in episode 1 (level 1.21). A brown armoured housing on a stone tile, with a blue-grey slot
on top, red lamps on both sides and two blue-grey barrels pointing down the screen, each ending
in a brown muzzle with a glowing red bore. The four frames pull the muzzles back along the
barrels (the recoil after a shot), so each frame is its own shape: newshp-271 (barrels out),
newshp-271-f2, -f3 and -f4 (fully back).

Run: blender --background --python assets/blender/enemies/newshp-271.py [-- --preview out.png]
(the preview is the first frame; the other frames get <name>-f2.png ... beside it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b123 as lib  # noqa: E402

NAME = "newshp-271"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)
# Bottom edge (pixel row) of the muzzle in each frame: the barrels retract by 2, 2 and 1 px.
ENDS = [27, 25, 23, 22]
BARRELS = (4.5, 17.5)  # barrel centre columns (cols 1-8 and 14-21)


def build(sprite, name, end):
    coll = common.reset_collection(name)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.1, roughness=0.85),  # 0 stone tile
        pal(2, metallic=0.1, roughness=0.9),  # 1 dark shadow
        pal(167, metallic=0.35, roughness=0.45),  # 2 brown housing
        pal(171, metallic=0.4, roughness=0.35),  # 3 light brown ridges and rings
        pal(164, metallic=0.3, roughness=0.55),  # 4 dark brown
        pal(105, metallic=0.6, roughness=0.3),  # 5 blue-grey barrels
        pal(99, metallic=0.5, roughness=0.4),  # 6 dark blue slot
        pal(108, metallic=0.6, roughness=0.25),  # 7 barrel shine
        pal(116, emission_strength=3.0),  # 8 red lamps
        pal(114, emission_strength=2.5),  # 9 red bore glow
    ]
    STONE, SHADOW, BROWN, LBROWN, DBROWN, BLUE, SLOT, SHINE, LAMP, BORE = range(10)
    bm = bmesh.new()

    # Stone tile and the shadow between the barrels.
    lib.box(bm, G, 0, 0, 24, 28, 0.0, 0.08, mat=STONE)
    lib.box(bm, G, 9, 12, 14, end, 0.08, 0.085, mat=SHADOW)

    # Housing: an octagonal block across columns 3-19, rows 2-12, rounded at the back.
    lib.loft_y(bm, G, 11.0, [(1.6, 5.5, 0.26, 0.12), (2.3, 7.4, 0.33, 0.12), (3.3, 8.5, 0.36, 0.12),
                             (11.6, 8.5, 0.36, 0.12), (12.2, 7.8, 0.33, 0.12)], sides=8, mat=BROWN, smooth=False)
    top = 0.12 + 0.36 * 0.92
    # Light ridges along the top edges and the rim at the back.
    for c in (6.6, 15.4):
        lib.box(bm, G, c, 6, c + 1.2, 11.5, top - 0.03, top + 0.02, mat=LBROWN)
    lib.box(bm, G, 6, 2.2, 17, 3.2, top - 0.06, top + 0.01, mat=LBROWN)
    # Blue slot (columns 9-13, rows 6-8) and the dark block below it (rows 9-11).
    lib.box(bm, G, 9, 6, 14, 9, top - 0.02, top + 0.015, mat=SLOT)
    lib.bevel_box(bm, G, 9, 9, 15, 12, top - 0.04, top + 0.035, 0.015, mat=DBROWN)
    # Pipes out of the back (rows 0-1): two blue-grey stubs and a brown knob between them.
    for c0, c1 in ((5, 10), (13, 18)):
        lib.loft_y(bm, G, (c0 + c1 - 1) / 2, [(-0.4, 2.3, 0.1, 0.24), (2.5, 2.3, 0.1, 0.24)],
                   sides=8, mat=BLUE)
    lib.bevel_box(bm, G, 10, 0, 13, 2.5, 0.1, 0.36, 0.02, mat=LBROWN)

    # Red lamps on the sides (columns 1-2 and 20-21, rows 7-11).
    for c in (1.6, 20.4):
        lib.ellipsoid(bm, G, c, 9.0, 0.2, 1.6, 2.6, 0.13, mat=LAMP, segments=12, rings=6)

    # Barrels: a blue-grey sleeve with a brown ring, then the brown muzzle that slides along it.
    zc, hh = 0.26, 0.17
    muzzle = end - 7
    for c in BARRELS:
        lib.loft_y(bm, G, c, [(8.0, 3.6, hh * 0.9, zc), (muzzle + 0.2, 3.6, hh * 0.9, zc)], sides=10, mat=BLUE)
        lib.loft_y(bm, G, c - 0.6, [(11.5, 0.0, 0.0, zc + hh * 0.86), (12.0, 0.7, 0.02, zc + hh * 0.86),
                                    (muzzle - 0.2, 0.7, 0.02, zc + hh * 0.86), (muzzle + 0.3, 0.0, 0.0, zc + hh * 0.86)],
                   sides=6, mat=SHINE)
        ring = muzzle - 3.5
        lib.loft_y(bm, G, c, [(ring - 0.7, 3.9, hh, zc), (ring + 0.7, 3.9, hh, zc)], sides=10, mat=LBROWN)
        lib.loft_y(bm, G, c, [(muzzle - 0.5, 3.4, hh * 0.85, zc), (muzzle, 4.0, hh * 1.05, zc),
                              (end - 1.4, 4.0, hh * 1.05, zc), (end - 0.5, 3.6, hh * 0.92, zc),
                              (end - 0.3, 0.0, 0.0, zc)], sides=10, mat=BROWN)
        lib.box(bm, G, c - 4.0, muzzle, c + 4.0, muzzle + 1.0, zc - 0.05, zc + hh * 1.08, mat=LBROWN)
        # The glowing bore seen through the top of the muzzle.
        lib.ellipsoid(bm, G, c - 0.5, end - 2.6, zc + hh * 1.0, 1.7, 1.4, 0.035, mat=BORE, segments=10, rings=5)

    return lib.to_object(name, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    out = lib.preview_arg()
    for i, (frame, end) in enumerate(zip(sprite["frames"], ENDS)):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, name, end)
        sprites = [{**s, "frames": [frame["index"]]} for s in sprite["sprites"]]
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", sprites)
        if out:
            png = out if i == 0 else str(Path(out).with_name(f"{name}.png"))
            ref = ROOT / "reference" / "models" / NAME / frame["image"]
            common.render_preview([obj], png, ref, size=frame["size"])


if __name__ == "__main__":
    main()
