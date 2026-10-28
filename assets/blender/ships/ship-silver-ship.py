"""Silver Ship (player ship, tyrian.shp#8 frame 81 and its banking frames 77-85): a 3D version of
its sprite.

A grey fighter, nose up the screen, built around column 11 of the sprite: a pointed fuselage with
a dark canopy, small swept fins beside the canopy, two side pods hugging the rear fuselage with
red striped engines at their backs, and three ribs on the tail. The banking frames show the pods
sit low beside a raised fuselage.

The ship is polished silver metal, so the sprite's drawn light is left to the game: the fuselage
is one mid-light grey (the sprite's white strip down column 9 and its dark right flank are the
sheen and shadow of a lit metal cylinder), the pods one mid grey on both sides, and no part paints
the sprite's dark outline ring (the game draws it). The canopy is dark glass with no modelled
glint. Real markings stay: the red engine stripes and the light and dark bands between them, and
the dark recess between the exhaust pipes.

Run: blender --background --python assets/blender/ships/ship-silver-ship.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import math  # noqa: E402

import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b002 import H, W, P, X, Y, _ring_point, loft, mirror, slab  # noqa: E402

NAME = "ship-silver-ship"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 11.5  # the ship's centreline: the middle of sprite column 11


def ridge(bm, sections, sides, mat, power, dark=None, dark_mat=0, rim=None, nose=None, paint=None):
    """loft() for the fuselage, with a cut-in canopy: dark = (row0, row1, half_width, depth) in px.
    Ring vertices on top within half_width of the axis, between those rows, sink by depth, and the
    faces between them take dark_mat, so the canopy is a dark well in the nose, not a dome.
    rim = (mat, side): faces on the side's flank (+1 right, -1 left, 0 both) take that darker
    material. nose = (mat, row): faces ahead of that row take mat. paint(col, row, cu, cv) returns
    a material (or None to keep it) for a face from where it is seen from above (col, row of its
    centre in sprite px) and which way it faces (cu, cv: cosine and sine of its angle round the
    ring), so the faces follow the sprite's shading."""
    rings = []
    for r, c, hw, hh, z in sections:
        y, x = Y(r), X(c)
        if hw == 0 and hh == 0:
            rings.append((r, [bm.verts.new((x, y, P(z)))]))
            continue
        sink = dark and dark[0] < r < dark[1]
        ring = []
        for i in range(sides):
            u, v = _ring_point(2 * math.pi * (i + 0.5) / sides, power)
            vz = z + hh * v
            if sink and v > 0 and abs(hw * u) < dark[2]:
                vz -= dark[3]
            ring.append(bm.verts.new((x + P(hw) * u, y, P(vz))))
        rings.append((r, ring))
    for (ra, r0), (rb, r1) in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            if len(r0) == 1:
                face = (r0[0], r1[j], r1[i])
            elif len(r1) == 1:
                face = (r0[i], r0[j], r1[0])
            else:
                face = (r0[i], r0[j], r1[j], r1[i])
            f = bm.faces.new(face)
            f.material_index = mat
            a = 2 * math.pi * (i + 1) / sides
            cu = math.cos(a)
            if rim and (abs(cu) if rim[1] == 0 else rim[1] * cu) > rim[2]:
                f.material_index = rim[0]
            if nose and rb <= nose[1] + 0.01:
                f.material_index = nose[0]
            ctr = f.calc_center_median()
            if paint:
                m = paint(ctr.x * 12 + W / 2, H / 2 - ctr.y * 12, cu, math.sin(a))
                if m is not None:
                    f.material_index = m
            if dark and dark[0] - 0.01 <= ra and rb <= dark[1] + 0.01:
                if ctr.z > 0 and abs(ctr.x - X(sections[0][1])) < P(dark[2] + 0.9):
                    f.material_index = dark_mat
    if len(rings[-1][1]) > 1:
        bm.faces.new(rings[-1][1]).material_index = mat


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(12, metallic=0.8, roughness=0.28),  # 0 fuselage, polished silver, one mid-light grey
        pal(6, metallic=0.75, roughness=0.3),  # 1 side pods, polished, mid grey
        pal(6, metallic=0.7, roughness=0.32),  # 2 canards
        pal(2, metallic=0.05, roughness=0.08),  # 3 canopy glass
        pal(115, metallic=0.3, roughness=0.4, emission_strength=2.0),  # 4 red engines
        pal(10, metallic=0.75, roughness=0.3),  # 5 light grey band between the red stripes (row 19)
        pal(2, metallic=0.4, roughness=0.6),  # 6 dark recess between the exhaust pipes
        pal(8, metallic=0.85, roughness=0.25),  # 7 exhaust pipes
        pal(6, metallic=0.75, roughness=0.3),  # 8 dark grey band between the red stripes (row 21)
    ]
    HULL, POD, FIN, GLASS, RED, BAND, DARK, PIPE, BAND_DK = range(9)
    bm = bmesh.new()

    # Fuselage, nose (row 0) to the tail (row 22): a rounded ridge about 7.5 px tall at its widest
    # (+5.1/-2.7), (row, half width, half height, z) in px. The sprite's 1 px dark outline is inside it.
    hull = [(-0.1, 0, 0, 0.5), (0.7, 1.5, 1.2, 0.6), (1.6, 2.3, 2.0, 0.9), (3.4, 3.2, 2.9, 1.1),
            (5.0, 3.5, 3.4, 1.2), (5.7, 3.5, 3.5, 1.2), (8.5, 3.6, 3.7, 1.2), (9.2, 3.6, 3.8, 1.2),
            (13.0, 3.6, 3.9, 1.2), (16.5, 3.6, 3.9, 1.2), (18.0, 3.6, 3.8, 1.2), (21.0, 3.5, 3.2, 0.9),
            (22.2, 3.3, 1.8, 0.4)]
    # The canopy: a dark slot about 3 px wide sunk into the nose (rows 5-9, columns 10-12).
    ridge(bm, [(r, AXIS, w, h, z) for r, w, h, z in hull], 18, HULL, 0.85,
          dark=(5.0, 9.2, 1.0, 0.9), dark_mat=GLASS)
    # The light pixel in the canopy (column 11, row 6) is the glass's shine: no geometry for it.

    # The tail (rows 21-26): a dark block sunk below three round exhaust pipes (columns 9, 11, 13).
    loft(bm, [(20.5, AXIS, 3.3, 1.6, -0.2), (26.0, AXIS, 3.2, 1.5, -0.2), (26.8, AXIS, 3.15, 1.0, -0.2)],
         sides=12, mat=DARK, power=0.6)
    for c in (9.5, 11.5, 13.5):
        loft(bm, [(19.5, c, 0.95, 0.95, 1.3), (25.8, c, 0.95, 0.95, 1.3), (26.4, c, 0.6, 0.6, 1.3)],
             sides=8, mat=PIPE)

    # Canards beside the canopy (rows 5-10, out to columns 4 and 19), dark grey.
    fin = [(9.0, 4.3), (4.2, 8.0), (4.2, 9.8), (8.8, 10.0)]
    for side in (1, -1):
        pts = fin if side == 1 else [(mirror(AXIS, c), r) for c, r in fin]
        slab(bm, pts, -0.3, 0.9, mat=FIN, bevel=0.2)

    # Side pods (rows 10-23, out to columns 2 and 21): round bodies about 4.5 px tall, lower than the
    # ridge, (row, centre col, half width, half height, z) for the left one.
    pod = [(9.9, 7.6, 0, 0, -0.2), (10.5, 7.3, 1.2, 1.1, -0.2), (12.0, 7.0, 1.7, 1.6, -0.3),
           (13.0, 6.6, 2.4, 2.0, -0.35), (14.0, 6.0, 2.8, 2.3, -0.4), (15.0, 5.6, 3.4, 2.5, -0.4),
           (20.4, 5.6, 3.4, 2.5, -0.4), (21.2, 5.9, 3.0, 2.3, -0.4), (22.2, 6.5, 2.6, 1.9, -0.4),
           (22.9, 6.7, 1.9, 1.3, -0.4)]
    # Red engines set into the pods' backs (columns 5-7, rows 18-25), tapering in toward the tail.
    engine = [(17.6, 6.5, 1.5, 2.8, -0.2), (23.8, 6.6, 1.45, 2.4, -0.3), (24.8, 7.2, 0.9, 1.6, -0.3),
              (25.8, 7.7, 0.35, 0.8, -0.3)]
    for side in (1, -1):
        m = (lambda c: c) if side == 1 else (lambda c: mirror(AXIS, c))
        # One grey all round: the sprite's lighter left pod, darker right one and near-black outer
        # edge are its light and outline, which the game makes.
        ridge(bm, [(r, m(c), w, h, z) for r, c, w, h, z in pod], 12, POD, 0.85)
        loft(bm, [(r, m(c), w, h, z) for r, c, w, h, z in engine], sides=10, mat=RED, power=0.6)
        # Grey bands between the red stripes (rows 19 and 21).
        for r, band in ((19.0, BAND), (21.0, BAND_DK)):  # light grey, then mid-dark grey
            loft(bm, [(r, m(6.5), 1.65, 2.95, -0.2), (r + 1.0, m(6.5), 1.65, 2.9, -0.25)],
                 sides=10, mat=band, power=0.6)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        level = sprite["frames"][len(sprite["frames"]) // 2]
        ref = ROOT / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], out, ref, size=level["size"])


if __name__ == "__main__":
    main()
