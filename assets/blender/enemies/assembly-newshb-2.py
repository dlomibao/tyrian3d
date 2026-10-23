"""Twin pod housings (newshb.shp 2, 4, 6, 8): a 3D version of their sprites.

Seen in level 3.10. Four 2x2 ground pieces side by side make one 96 x 28 px row (sprite.json
`assemblyLayout`): the top ends of two big machines, mirror images of each other about pixel
column 46.5. Each is a grey housing with sloping sides, three red vents and grille slats on its
top, a purple cowl on its outer side and below the grille (a grey block with a knob on the left
machine, a knob in the purple on the right one), and a big glossy blue sphere pushing out at the
bottom, which carries on past the row's lower edge (it's cut there).

The row is built whole in assembly coordinates and cut into its four pieces with
common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshb-2.py [-- --preview out.png]
(the preview is the whole row; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b119 as lib  # noqa: E402

NAME = "assembly-newshb-2"
ROOT = common.repo_root(__file__)
PIECES = ["newshb-2", "newshb-4", "newshb-6", "newshb-8"]
AXIS = 46.5  # the two machines mirror each other about the centre of pixel column 46.5
TOP = 0.5  # housing top
COWL = 0.32  # cowl top


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshb2"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(6, metallic=0.4, roughness=0.5),  # 0 grey housing top
        pal(4, metallic=0.35, roughness=0.55),  # 1 lit side
        pal(2, metallic=0.3, roughness=0.65),  # 2 shaded side, dark slots
        pal(9, metallic=0.5, roughness=0.4),  # 3 bright dividers and slats
        pal(113, metallic=0.2, roughness=0.6),  # 4 dark red vent
        pal(114, emission_strength=2.0),  # 5 vent glow
        pal(86, metallic=0.3, roughness=0.45),  # 6 purple cowl
        pal(89, metallic=0.35, roughness=0.4),  # 7 light purple edge
        pal(55, metallic=0.4, roughness=0.12),  # 8 blue glass sphere
        pal(61, metallic=0.3, roughness=0.1),  # 9 sphere highlight
        pal(10, metallic=0.6, roughness=0.3),  # 10 knob
        pal(3, metallic=0.3, roughness=0.6),  # 11 step line
        pal(84, metallic=0.3, roughness=0.5),  # 12 dark purple outer side of the cowl
    ]
    GREY, LIT, SHADE, BRIGHT, VENT, GLOW, PURPLE, LILAC, GLASS, SHINE, KNOB, STEP, PURPLE_D = range(13)
    bm = bmesh.new()

    def side(nx, ny):
        return LIT if nx < 0.3 else SHADE

    def unit(mirrored, stub, knob_col):
        """One machine; geometry is given for the left one and mirrored for the right."""
        f = (lambda c: 2 * AXIS - c) if mirrored else (lambda c: c)  # noqa: E731
        P = lambda pts: [(f(c), r) for c, r in pts]  # noqa: E731

        def box(c0, r0, c1, r1, z0, z1, mat):
            a, b = sorted((f(c0 - 0.5), f(c1 + 0.5)))
            lib.plate(bm, [(a, r0 - 0.5), (b, r0 - 0.5), (b, r1 + 0.5), (a, r1 + 0.5)], z0, z1, mat)

        # Housing: a flat top over rows 1-13 with sides sloping out to the ground.
        lib.frustum(bm, P([(21.5, 0.5), (36, 0.5), (36, 13.5), (21.5, 13.5)]),
                    P([(20.5, 0.5), (37, 0.5), (42.5, 13.5), (14.5, 13.5)]), TOP, 0.0,
                    top_mat=GREY, side_mat=side)
        # Lower body under the grille: the cowl's top, wrapping round the sphere, purple on the
        # machine's outer side and grey on its inner side.
        def lower_side(nx, ny):
            outer = nx > 0.3 if mirrored else nx < -0.3
            return PURPLE_D if outer else side(nx, ny)
        lib.frustum(bm, P([(19.5, 13.4), (36, 13.4), (36, 18.5), (23, 20), (20, 30), (10, 30)]),
                    P([(14.5, 13.4), (42.5, 13.4), (42.5, 18.5), (30, 22), (22, 30), (7.5, 30)]),
                    COWL, 0.0, top_mat=PURPLE, side_mat=lower_side)
        box(22, 13, 35, 13, COWL, TOP - 0.01, STEP)  # the step down from the housing
        lib.tube_x(bm, 14.2, [(min(f(19.8), f(29.5)), 0.9, 0.035, COWL),
                              (max(f(19.8), f(29.5)), 0.9, 0.035, COWL)], sides=8, mat=LILAC)

        # Three red vents (columns 23-25, 27-29, 31-33, rows 1-5) between bright dividers.
        for c in (23, 27, 31):
            box(c, 1, c + 2, 5, TOP - 0.02, TOP + 0.012, VENT)
            box(c + 1, 1.5, c + 1, 4.5, TOP, TOP + 0.02, GLOW)
        for c in (22, 26, 30, 34):
            box(c, 1, c, 5.4, TOP - 0.02, TOP + 0.03, BRIGHT)
        # Grille: dark slots (rows 7, 9) between bright slats (rows 6, 8, 10).
        for r in (7, 9):
            box(22, r, 34, r, TOP - 0.02, TOP + 0.005, SHADE)
        for r in (6, 8, 10):
            box(22, r, 34, r, TOP - 0.02, TOP + 0.025, BRIGHT)
        for c in (25, 29):  # grooves in the plate below the grille
            box(c, 11, c, 12, TOP - 0.02, TOP + 0.005, LIT)

        # The block under the grille's inner end (left machine) and the knob.
        if stub:
            box(30, 14, 35, 18, 0.0, COWL + 0.04, GREY)
        z = COWL + (0.04 if stub else 0.0)
        lib.ellipsoid(bm, f(knob_col), 17, z, 2.0, 1.6, 0.06, mat=KNOB, segments=10, rings=5)

        # The glass sphere (centre column 30.5, row 30.5) and its highlight, both lit from the left.
        cc = f(30.5)
        lib.ellipsoid(bm, cc, 30.5, 0.0, 11, 11, 0.44, mat=GLASS, segments=20, rings=10, z_min=0.0)
        lib.ellipsoid(bm, cc - 5.0, 24.6, 0.3, 2.6, 1.6, 0.04, mat=SHINE, segments=10, rings=5)

    unit(False, True, 31.5)
    unit(True, False, 2 * AXIS - 64.5)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    lib.export_assembly(ROOT, obj, sprite, PIECES)


if __name__ == "__main__":
    main()
