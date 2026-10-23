"""Red car (newshv.shp frame 163): a 3D version of its sprite.

Seen in episode 2 (level section 17). A small red car seen from above, nose up the screen: a
rounded body with yellow headlights at the front corners and two tail lights, a cabin with a
blue windscreen, side windows split by a red pillar, a blue rear window and a red roof, and
four grey wheels poking out at the sides.

Run: blender --background --python assets/blender/enemies/newshv-163.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b111 as lib  # noqa: E402

NAME = "newshv-163"
ROOT = common.repo_root(__file__)
P = 1 / 12
ex, ey, px, row = lib.ex, lib.ey, lib.px, lib.row


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(70, metallic=0.4, roughness=0.3),  # 0 red body
        pal(68, metallic=0.4, roughness=0.4),  # 1 darker lower sides
        pal(71, metallic=0.4, roughness=0.25),  # 2 red roof
        pal(147, metallic=0.6, roughness=0.1),  # 3 blue glass
        pal(70, metallic=0.4, roughness=0.35),  # 4 pillars
        pal(101, metallic=0.3, roughness=0.7),  # 5 grey tyres
        pal(123, emission_strength=3.0),  # 6 yellow lights
    ]
    BODY, LOWER, ROOF, GLASS, PILLAR, TYRE, LAMP = range(7)
    bm = bmesh.new()

    # Body outline (column/row pixel edges, the car spans rows 3-24 and columns 6-16).
    outline = [(9.2, 3.0), (13.8, 3.0), (15.6, 4.2), (16.7, 5.8), (17.0, 7.5), (17.0, 22.0), (16.4, 23.4),
               (14.8, 24.6), (13.6, 25.0), (9.4, 25.0), (8.2, 24.6), (6.6, 23.4), (6.0, 22.0), (6.0, 7.5),
               (6.3, 5.8), (7.4, 4.2)]
    pts = [(ex(c), ey(r)) for c, r in outline]
    pts.reverse()  # counter-clockwise seen from above
    lib.prism(bm, pts, 0.06, 0.2, mat_index=LOWER)
    inner = [(x * 0.94, y * 0.97) for x, y in pts]
    lib.prism(bm, inner, 0.2, 0.25, mat_index=BODY)

    # Cabin: a frustum from the deck (rows 8.6-21.2, columns 6.6-16.4) to the roof (rows
    # 11.8-18.8, columns 9-14). Its sides are the windows, with a red pillar at row 15.
    zb, zt = 0.25, 0.45
    bw, tw = 4.7 * P, 2.7 * P
    base_y = [ey(8.7), ey(15.0), ey(16.0), ey(21.2)]
    top_y = [ey(11.8), ey(15.0), ey(16.0), ey(18.8)]
    BL = [bm.verts.new((-bw, y, zb)) for y in base_y]
    BR = [bm.verts.new((bw, y, zb)) for y in base_y]
    TL = [bm.verts.new((-tw, y, zt)) for y in top_y]
    TR = [bm.verts.new((tw, y, zt)) for y in top_y]
    for i, mat in enumerate((GLASS, PILLAR, GLASS)):
        bm.faces.new((BL[i], BL[i + 1], TL[i + 1], TL[i])).material_index = mat
        bm.faces.new((BR[i + 1], BR[i], TR[i], TR[i + 1])).material_index = mat
    bm.faces.new((BR[0], BL[0], TL[0], TR[0])).material_index = GLASS  # windscreen
    bm.faces.new((BL[3], BR[3], TR[3], TL[3])).material_index = GLASS  # rear window
    bm.faces.new(TL[::-1] + TR).material_index = ROOF
    bm.faces.new(BL + BR[::-1]).material_index = BODY

    # Wheels: front at rows 9-11, back at rows 20-21, sticking out a pixel at columns 5 and 17.
    for y in (row(10), ey(21)):
        for s in (-1, 1):
            lib.tube_path(bm, [(s * 6.9 * P, y, 0.13), (s * 4.6 * P, y, 0.13)], 1.6 * P,
                          sides=10, mat_index=TYRE)

    # Headlights on the front corners and tail lights at the back.
    for s in (-1, 1):
        lib.tube_path(bm, [(s * 4.1 * P, ey(4.4), 0.2), (s * 5.3 * P, ey(5.9), 0.2)], 0.65 * P, sides=8,
                      mat_index=LAMP)
        lib.tube_path(bm, [(s * 2.0 * P, ey(24.6), 0.19), (s * 3.1 * P, ey(24.4), 0.19)], 0.6 * P, sides=8,
                      mat_index=LAMP)

    return common.mesh_object(NAME, bm, mats, coll, smooth=False)


if __name__ == "__main__":
    lib.run(ROOT, NAME, build)
