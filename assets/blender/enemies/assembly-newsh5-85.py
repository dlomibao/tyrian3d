"""Grey twin-walker gate (newsh5.shp frames 85 and 87): a 3D version of their sprites.

Seen in episode 4 (levels 22 and 47), on the ground. Two 2x2 pieces side by side make one 48x28
px machine, nearly mirror symmetric: on each side a hunched grey walker with a heavy head plate,
two red eyes under a bright brow, a pair of legs on clawed brown feet; a shoulder reaches in to a
blue-capped pillar from which a pink claw hangs on a thin grey rod, and the two rods are joined
low down by a brown U-shaped band, leaving the middle open.

The left half is built in assembly coordinates and mirrored, every face takes the palette colour
of the pixel under it (each side from its own piece), then common.split_assembly cuts it into
newsh5-85 (left) and newsh5-87 (right). The column of red canisters listed with this assembly
(newsh5-168) is a separate object and has its own script. One frame each.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-85.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b051 as lib  # noqa: E402

NAME = "assembly-newsh5-85"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-85", "newsh5-87"]
AXIS = 23.5  # mirror line (pixel column of the composed 48x28 sprite)


def build(g, sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh5_85"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(2, metallic=0.2, roughness=0.6),  # 0 near-black grey
        pal(4, metallic=0.2, roughness=0.55),  # 1 dark grey
        pal(6, metallic=0.2, roughness=0.5),  # 2 grey
        pal(8, metallic=0.2, roughness=0.45),  # 3 light grey
        pal(11, metallic=0.2, roughness=0.4),  # 4 bright grey edges
        pal(98, metallic=0.2, roughness=0.5),  # 5 dark blue-grey
        pal(104, metallic=0.2, roughness=0.45),  # 6 blue-grey
        pal(67, metallic=0.2, roughness=0.7),  # 7 dark rust
        pal(69, metallic=0.2, roughness=0.65),  # 8 rust
        pal(72, metallic=0.15, roughness=0.5),  # 9 pink claws
        pal(75, metallic=0.1, roughness=0.45),  # 10 pale pink
        pal(162, metallic=0.1, roughness=0.8),  # 11 dark brown feet
        common.palette_material(sprite, 74, tag + "_eye", emission_strength=4.0),  # 12 red eyes
    ]
    G2, G4, G6, G8, G11, B98, B104, R67, R69, R72, R75, BROWN, EYE = range(13)

    def slot(i):
        if 0 <= i <= 2:
            return G2
        if 3 <= i <= 4:
            return G4
        if 5 <= i <= 6:
            return G6
        if 7 <= i <= 9:
            return G8
        if 10 <= i <= 15:
            return G11
        if 96 <= i <= 100:
            return B98
        if 101 <= i <= 111:
            return B104
        if 64 <= i <= 67:
            return R67
        if 68 <= i <= 70:
            return R69
        if 71 <= i <= 73:
            return R72
        if 74 <= i <= 79:
            return R75
        if i == 162:
            return BROWN
        return None

    bm = bmesh.new()
    rows = lambda a, b, n: [a + (b - a) * k / n for k in range(n + 1)]  # noqa: E731

    # ---- left half (mirrored below) ----

    # Head plate (columns 3-12, rows 2-10): a tall rounded block standing on the ground.
    head = []
    for r in rows(1.6, 10.9, 9):
        w = 4.2 if r < 2.6 else 4.8 if r < 3.6 else 5.0
        c = 8.6 if r < 2.6 else 8.2 if r < 3.6 else 8.0
        head.append((c, r, 0.25, w, 0.25))
    lib.sweep(bm, g, head, sides=12, mat=G6, power=0.45)
    # Bright brow along row 10 and the crest down column 9 (rows 2-6).
    lib.sweep(bm, g, [(3.4, 10.0, 0.47, 0.0, 0.0), (3.8, 10.0, 0.47, 0.7, 0.04), (12.6, 10.0, 0.47, 0.7, 0.04),
                      (13.0, 10.0, 0.47, 0.0, 0.0)], sides=6, mat=G11)
    lib.sweep(bm, g, [(9.3, 1.6, 0.5, 0.0, 0.0), (9.3, 2.2, 0.5, 1.0, 0.05), (9.3, 6.2, 0.5, 1.0, 0.05),
                      (9.3, 6.8, 0.5, 0.0, 0.0)], sides=6, mat=G11)
    eyes_from = len(bm.faces)
    for c in (7.0, 10.0):
        lib.ellipsoid(bm, (g.X(c), g.Y(8.0), 0.49), (0.8 * lib.PX, 0.75 * lib.PX, 0.035), segments=8, rings=4,
                      mat=EYE)
    eyes_to = len(bm.faces)

    # Legs (rows 11-19): the outer one (columns 4-8) and the inner one (columns 10-13), split by a
    # dark groove at column 9.
    lib.sweep(bm, g, [(6.5, r, 0.17, 2.6, 0.17) for r in rows(10.5, 19.8, 6)], sides=10, mat=G6, power=0.7)
    lib.sweep(bm, g, [(11.2, r, 0.15, 1.9 if r < 16.5 else 2.4, 0.15) for r in rows(10.5, 20.6, 6)], sides=10,
              mat=G6, power=0.7)
    # Clawed brown foot (rows 20-24, columns 5-10).
    lib.sweep(bm, g, [(7.4, 19.7, 0.07, 2.2, 0.07), (7.2, 20.8, 0.07, 2.6, 0.08), (7.4, 22.2, 0.06, 2.4, 0.07),
                      (7.9, 22.8, 0.05, 1.4, 0.05)], sides=8, mat=R69)
    lib.sweep(bm, g, [(8.2, 22.3, 0.06, 1.3, 0.06), (8.9, 23.4, 0.05, 1.4, 0.05), (9.8, 24.3, 0.04, 1.0, 0.04),
                      (10.6, 24.8, 0.03, 0.0, 0.0)], sides=8, mat=R69)

    # Shoulder reaching in to the pillar (columns 12-17, rows 3-7).
    lib.sweep(bm, g, [(11.5, 5.0, 0.21, 2.2, 0.21), (17.5, 5.0, 0.21, 2.2, 0.21)], sides=10, mat=G6, power=0.6)
    # Inner pillar with its blue-grey cap (columns 16-21, rows 1-7).
    lib.sweep(bm, g, [(18.8, r, 0.23, 2.5, 0.23) for r in rows(0.8, 7.6, 5)], sides=10, mat=G8, power=0.6)
    # Pink claw hanging from it (columns 18-20, rows 8-13), then the thin grey rod down to a knuckle.
    lib.sweep(bm, g, [(19.2, 7.0, 0.3, 1.6, 0.1), (19.2, 9.0, 0.3, 1.7, 0.1), (19.3, 11.5, 0.28, 1.5, 0.09),
                      (19.6, 13.2, 0.25, 0.9, 0.06), (19.9, 14.0, 0.22, 0.0, 0.0)], sides=8, mat=R72)
    lib.sweep(bm, g, [(20.0, 13.5, 0.22, 0.7, 0.05), (20.0, 16.0, 0.2, 0.7, 0.05), (19.8, 18.2, 0.17, 0.8, 0.05)],
              sides=6, mat=G8)
    lib.ellipsoid(bm, (g.X(19.2), g.Y(19.0), 0.14), (1.6 * lib.PX, 1.4 * lib.PX, 0.08), segments=10, rings=5, mat=G6)
    # Brown U-shaped band joining the two rods (rows 21-24).
    lib.sweep(bm, g, [(19.8, 19.8, 0.1, 1.1, 0.06), (20.3, 21.2, 0.08, 1.2, 0.06), (21.3, 22.5, 0.07, 1.3, 0.06),
                      (22.6, 23.1, 0.06, 1.4, 0.06), (AXIS + 0.3, 23.2, 0.06, 1.4, 0.06)], sides=8, mat=R69)

    lib.mirror(bm, g.X(AXIS))

    # The small red hinge between the pillars' tops (column 24, rows 3-4; only on the right piece).
    lib.ellipsoid(bm, (g.X(24.0), g.Y(3.5), 0.33), (1.0 * lib.PX, 1.2 * lib.PX, 0.06), segments=8, rings=4, mat=R72)

    # Colours from the sprite (each side from its own piece), eyes kept.
    eye_faces = set(lib.faces_from(bm, 0)[eyes_from:eyes_to])
    lib.paint(bm, g, slot, under=G2, keep={EYE}, average=False)
    for f in eye_faces:
        f.material_index = EYE
    return lib.to_object(NAME, bm, mats, coll)


def main():
    g, layout, sprite = lib.assembly(ROOT, PIECES)
    obj = build(g, sprite)
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    lib.preview_assembly(ROOT, obj, pieces, g, sprite, size=4)


if __name__ == "__main__":
    main()
