"""Grey dome base (newshb.shp 154, 156, 158, 160): a 3D version of its sprites.

Seen in level 3.10. Four 2x2 ground pieces side by side make one 96 x 28 px row (sprite.json
`assemblyLayout`): the bottom edge of a big round grey structure. A flat top with ribbed side
panels, a raised block in the middle, two pipes running down channels either side of it into
framed red lights, a bright lip at the front, and a wide bevelled rim (lit on the left, in shadow
on the right and below) sloping down to the ground. The pieces' extra frames (newshb-156 and
newshb-158: 191/229/267 and 193/231/269) only flicker the red lights, so one model each covers them.

The row is built whole in assembly coordinates (left half, mirrored about pixel column 47) and cut
into its four pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshb-154.py [-- --preview out.png]
(the preview is the whole row; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b119 as lib  # noqa: E402

NAME = "assembly-newshb-154"
ROOT = common.repo_root(__file__)
PIECES = ["newshb-154", "newshb-156", "newshb-158", "newshb-160"]
AXIS = 47  # the row is (nearly) mirror symmetric about the centre of pixel column 47
TOP = 0.32  # height of the flat top


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshb154"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(6, metallic=0.35, roughness=0.55),  # 0 grey top
        pal(9, metallic=0.4, roughness=0.45),  # 1 lit rim (left)
        pal(7, metallic=0.35, roughness=0.5),  # 2 rim (right), raised parts
        pal(5, metallic=0.3, roughness=0.6),  # 3 front bevel
        pal(4, metallic=0.25, roughness=0.7),  # 4 grooves, seams
        pal(2, metallic=0.2, roughness=0.8),  # 5 dark channels
        pal(10, metallic=0.5, roughness=0.35),  # 6 bright edges, pipe ends
        pal(8, metallic=0.4, roughness=0.45),  # 7 light frames
        pal(117, emission_strength=3.5),  # 8 red light
        pal(119, emission_strength=5.0),  # 9 hot core
    ]
    GREY, RIM_LIT, RIM, BEVEL, GROOVE, CHANNEL, BRIGHT, FRAME, RED, HOT = range(10)
    bm = bmesh.new()

    def rim_mat(nx, ny):
        if nx < -0.55:
            return RIM_LIT
        if nx > 0.55:
            return RIM
        return BEVEL if ny < 0 else GREY

    # The body: a flat top (inner outline) and the bevelled rim down to the ground (outer
    # outline), left half from above the row's top edge (it's cut there) round to the middle.
    inner_l = [(21.5, -2), (21.5, 3), (21.0, 8), (21.0, 12), (22.5, 14.5), (25, 16), (28, 17),
               (30, 18), (32, 19), (35, 19.5)]
    outer_l = [(7.0, -2), (7.5, 3), (10.5, 7), (13, 10.5), (15.5, 13.5), (18, 16), (21, 18.5),
               (24.5, 21), (29, 23.3), (35, 24.5)]
    mirror = lambda pts: [(2 * AXIS - c, r) for c, r in reversed(pts)]  # noqa: E731
    inner = inner_l + [(AXIS, 19.5)] + mirror(inner_l)
    outer = outer_l + [(AXIS, 24.5)] + mirror(outer_l)
    # A rounded rim: it drops slowly at first, then steeper towards the ground.
    lib.stack(bm, [(inner, TOP), (lib.blend(inner, outer, 0.35), TOP * 0.86),
                   (lib.blend(inner, outer, 0.7), TOP * 0.55), (outer, 0.0)],
              top_mat=GREY, side_mat=rim_mat)

    start = len(bm.verts)  # ---- left half details (mirrored below) ----

    # Ribbed side panel: dark grooves (rows 7, 10, 13) each with a lit slat below it.
    for r in (7, 10, 13):
        lib.box(bm, 22, r, 35, r, TOP - 0.01, TOP + 0.006, GROOVE)
        lib.box(bm, 22, r + 1, 35, r + 1, TOP - 0.01, TOP + 0.018, RIM)
    lib.box(bm, 29, 8, 29, 16, TOP - 0.01, TOP + 0.006, GROOVE)  # seam down the panel

    # Channel (columns 36-41) with a pipe running down it to a bright end.
    lib.box(bm, 36, -2, 41, 10, TOP - 0.01, TOP + 0.008, CHANNEL)
    lib.tube_y(bm, 38.5, [(-2.5, 1.7, 0.07, TOP + 0.02), (7.6, 1.7, 0.07, TOP + 0.02)], sides=10, mat=GREY)
    lib.tube_y(bm, 38.5, [(7.5, 1.9, 0.08, TOP + 0.02), (9.4, 1.9, 0.08, TOP + 0.02),
                          (10.0, 1.2, 0.05, TOP + 0.02)], sides=10, mat=BRIGHT)

    # Framed red light at the bottom of the channel (rows 11-14, columns 38-40).
    lib.box(bm, 37, 10.5, 41, 15, TOP - 0.01, TOP + 0.05, FRAME)
    lib.box(bm, 38, 11, 40, 14, TOP + 0.05, TOP + 0.065, RED)
    lib.ellipsoid(bm, 39, 13.2, TOP + 0.065, 1.3, 1.4, 0.025, mat=HOT, segments=10, rings=5)

    lib.mirror_cols(bm, AXIS, start)

    # ---- middle ----
    # Raised block between the channels with a rounded, lit front edge and a low step below it.
    lib.box(bm, 43, -2, 51, 4, TOP - 0.01, TOP + 0.07, RIM)
    lib.tube_x(bm, 6.0, [(42.5, 2.0, 0.045, TOP + 0.03), (51.5, 2.0, 0.045, TOP + 0.03)], sides=8, mat=BRIGHT)
    lib.box(bm, 43, 7, 51, 9, TOP - 0.01, TOP + 0.035, RIM)

    # Bright lip along the front with two seams in it.
    lib.plate(bm, [(30, 16.6), (64, 16.6), (61, 19.4), (33, 19.4)], TOP - 0.01, TOP + 0.014, mat=RIM)
    for c in (46, 51):
        lib.box(bm, c, 17, c, 19, TOP, TOP + 0.02, GROOVE)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    lib.export_assembly(ROOT, obj, sprite, PIECES)


if __name__ == "__main__":
    main()
