"""Vent block (newshc.shp frames 39, 41, 43): a 3D version of its sprite.

Seen in episode 1 (level 1.19) and 3 (3.23), on the same blue tiled floor as the twin-pillar
machine (assembly-newshc-283). A heavy grey block with chamfered back corners fills its tile: a
raised plate on top cut by two slots, a light ridge down its left side and a front that slopes
down to the floor in five ribs like claws. The three frames only make the slots glow brighter
(dark red to orange), so one model covers them: the glow rises from the front of each slot, a
strip of light per pixel row, and each frame has its own set of strips (common.frame_part). On
frame 39 only the upper slot glows, a dark red line; on 41 the upper slot has an orange line
under a red one and the lower slot a red line; on 43 the upper slot glows over three rows and
the lower one over two.

Run: blender --background --python assets/blender/enemies/newshc-39.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b110 as lib  # noqa: E402

NAME = "newshc-39"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
FR = lib.Frame()
PX = lib.PX


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(5, metallic=0.55, roughness=0.4),  # 0 grey block
        pal(7, metallic=0.6, roughness=0.35),  # 1 top plate
        pal(9, metallic=0.6, roughness=0.3),  # 2 light ridges and ribs
        pal(3, metallic=0.3, roughness=0.6),  # 3 slot floors, grooves
        pal(117, emission_strength=4.0),  # 4 slot glow
        pal(98, metallic=0.1, roughness=0.8),  # 5 floor
        pal(101, metallic=0.15, roughness=0.7),  # 6 floor tiles
        pal(102, metallic=0.15, roughness=0.7),  # 7 light floor tiles
        pal(4, metallic=0.5, roughness=0.45),  # 8 dark right flank
        pal(114, emission_strength=2.5),  # 9 dark red glow
        pal(115, emission_strength=3.0),  # 10 red glow
        pal(121, emission_strength=5.0),  # 11 orange glow
    ]
    BLOCK, PLATE, RIDGE, DARK, GLOW, FLOOR, TILE, TILE_HI, FLANK = range(9)
    GLOWS = {114: 9, 115: 10, 117: GLOW, 121: 11}
    bm = bmesh.new()
    E = lambda c, r: (FR.xe(c), FR.ye(r))  # noqa: E731

    lib.floor_tiles(bm, FR, sprite["frames"][0]["pixels"], FLOOR, {101: TILE, 102: TILE_HI})

    # The block (cols 2-19, rows 2-14) with chamfered back corners.
    top = 0.45
    lib.prism(bm, [E(c, r) for c, r in [(5, 2), (17, 2), (19, 4), (20, 5), (20, 14.5), (2, 14.5),
                                         (2, 5), (3, 4)]], 0.0, top, BLOCK)
    # Its front, sloping down to the floor (rows 14-24).
    zf = 0.16
    x0, x1 = FR.xe(2), FR.xe(20)
    yb, yf = FR.ye(14.5), FR.ye(24)
    before = set(bm.faces)
    v = [bm.verts.new(p) for p in ((x0, yb, 0), (x1, yb, 0), (x1, yf, 0), (x0, yf, 0),
                                   (x0, yb, top), (x1, yb, top), (x1, yf, zf), (x0, yf, zf))]
    for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([v[i] for i in f])
    lib.tag(bm, before, BLOCK, False)
    # Dark right flank (cols 17-19).
    lib.prism(bm, [E(c, r) for c, r in [(18, 3.2), (19, 4), (20, 5), (20, 18), (18, 18)]], 0.0, top + 0.01, FLANK)

    # Raised top plate (cols 6-17, rows 2-14) cut by two slots (cols 8-15, rows 4-7 and 11-14).
    zp = top + 0.07
    for c0, r0, c1, r1 in ((6, 2.2, 17, 4), (6, 4, 8, 7), (15, 4, 17, 7), (6, 7, 17, 11), (6, 11, 8, 14),
                           (15, 11, 17, 14), (6, 14, 17, 14.6)):
        xa, ya = E(c0, r1)
        xb, yb2 = E(c1, r0)
        lib.box(bm, xa, ya, xb, yb2, top - 0.01, zp, PLATE)
    for r0 in (4, 11):
        xa, ya = E(8, r0 + 3)
        xb, yb2 = E(15, r0)
        lib.box(bm, xa, ya, xb, yb2, top - 0.01, top + 0.02, DARK)

    # Light ridge down the left side (col 6) and the ribs down the sloping front.
    lib.tube(bm, [(FR.x(6.3), FR.ye(2.6), top, 0.0, 0.0), (FR.x(6.3), FR.ye(3.4), top, 0.8 * PX, 0.04),
                  (FR.x(6.3), FR.ye(14.5), top, 0.8 * PX, 0.04)], sides=6, mat=RIDGE)
    for c in (6.5, 9.0, 11.5, 14.5, 16.5):
        lib.tube(bm, [(FR.x(c), FR.ye(14.0), top + 0.01, 0.8 * PX, 0.04),
                      (FR.x(c), FR.ye(23.6), zf + 0.01, 0.8 * PX, 0.04)], sides=6, mat=RIDGE)
    for c in (10.5, 13.4):  # dark grooves between the claws
        lib.box(bm, FR.xe(c - 0.4), FR.ye(24), FR.xe(c + 0.4), FR.ye(18), 0.0, zf + 0.06, DARK)

    parts = [lib.to_object(NAME, bm, mats, coll)]

    # The glow in the slots, per frame: for each slot (its top pixel edge), the palette index of
    # each glowing row counted up from the slot's front row.
    glow = {
        39: {4: [114], 11: []},
        41: {4: [121, 114], 11: [115]},
        43: {4: [117, 121, 114], 11: [121, 115]},
    }
    for frame, slots in glow.items():
        gbm = bmesh.new()
        for r0, rows in slots.items():
            for k, index in enumerate(rows):
                xa, ya = E(8.3, r0 + 3 - k)
                xb, yb2 = E(14.7, r0 + 2 - k)
                lib.box(gbm, xa, ya, xb, yb2, top, top + 0.035, GLOWS[index])
        parts.append(common.frame_part(lib.to_object(f"{NAME}-glow-{frame}", gbm, mats, coll), [frame]))
    return parts


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objects = build(sprite)
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    out = lib.preview_arg()
    if out:
        common.render_preview(objects, out, lib.sprite_png(ROOT, NAME, sprite, 2), size=2, frame=sprite["frames"][2]["index"])
    if "--frame-previews" in sys.argv:
        common.render_frame_previews(objects, sys.argv[sys.argv.index("--frame-previews") + 1], sprite, ROOT)


if __name__ == "__main__":
    main()
