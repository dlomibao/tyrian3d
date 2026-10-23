"""Long segmented pipe on a sled (newsh2.shp, assembly of 8 pieces): a 3D version of its sprites.

Seen in episode 1 (level 1.3) and episode 3. Eight 2x2 ground sprites in a row (sprite.json
`assemblyLayout`) make one 192x28 px pipe lying across the screen: a light grey bullet nose
(newsh2-7) on the left, six identical segments (newsh2-9, so one model serves all six) of grey
rings, narrow red collars and a big red flange with a bracket down to the ground, and an end
piece (newsh2-11) with a bigger flange and a long grey cylinder with a rounded cap. The pipe
rests on a low dark sled that shows as the dark band under it.

The pipe is built once in assembly coordinates (all six segments, so their joins are exact) and
cut into pieces with common.split_assembly; one of the middle segments is exported as newsh2-9.
Ground object: the sled's base is at z = 0.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-9.py [-- --preview out.png]
(the preview is the whole pipe; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b129 as lib  # noqa: E402

NAME = "assembly-newsh2-9"
ROOT = common.repo_root(__file__)
PIECES = ["newsh2-7", "newsh2-9", "newsh2-11"]
# Assembly pixel (0, 0) is the top-left corner of newsh2-7 (screen cx 130 - 12, cy -17 - 14);
# the assembly is 192 x 28 px and its centre (screen 214, -17) is the Blender origin.
CX0, CY0 = 214, -17
W, H = 192, 28
G = lib.Grid(W, H)
SEGMENTS = [24 + 24 * k for k in range(6)]  # left edges of the six newsh2-9 pieces
EXPORT_9 = 226  # screen cx of the newsh2-9 copy that is exported (a middle one)

ROW = 11.0  # the pipe's axis (sprite row)
ZC = 0.31  # the pipe's axis height
EPS = 0.15  # px: tubes that meet at a piece boundary overlap it a little so the cut is clean


def e(a):
    """Left edge of assembly pixel column a, as a fractional column for G.X."""
    return a - 0.5


def ring(bm, c0, c1, r, mat, bevel=(0.5, 0.5), sides=12, smooth=True, row=ROW, z=ZC):
    """A section of pipe from pixel edge c0 to c1 with radius r px, its ends rounded off by
    `bevel` (left, right) px."""
    path = []
    bl, br = bevel
    if bl:
        path += [(e(c0), row, z, r - bl, (r - bl) / 12), (e(c0) + bl, row, z, r, r / 12)]
    else:
        path += [(e(c0), row, z, r, r / 12)]
    if br:
        path += [(e(c1) - br, row, z, r, r / 12), (e(c1), row, z, r - br, (r - br) / 12)]
    else:
        path += [(e(c1), row, z, r, r / 12)]
    lib.sweep(bm, G, path, sides=sides, mat=mat, smooth=smooth)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh2_9"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.5, roughness=0.35),  # 0 grey rings
        pal(11, metallic=0.6, roughness=0.25),  # 1 light grey nose
        pal(3, metallic=0.4, roughness=0.5),  # 2 dark grooves, sled feet
        pal(72, metallic=0.3, roughness=0.4),  # 3 red collars
        pal(73, metallic=0.3, roughness=0.4),  # 4 red flanges
        pal(77, metallic=0.3, roughness=0.35),  # 5 flanges' lit rims
        pal(67, metallic=0.2, roughness=0.6),  # 6 dark red brackets
        pal(70, metallic=0.2, roughness=0.5),  # 7 bracket feet
        pal(2, metallic=0.1, roughness=0.8),  # 8 dark sled
    ]
    GREY, NOSE, GROOVE, COLLAR, FLANGE, FLANGE_LIT, BRACKET, FOOT, SLED = range(9)
    bm = bmesh.new()

    # The sled under the pipe's south side (rows 15-18), tapering in under the nose.
    lib.plate(bm, G, [(6, 14.5), (W, 14.5), (W, 19), (17, 19), (13, 18), (9, 17), (6, 16)], 0.0, 0.05, mat=SLED)

    def flange(c0, r, foot_row):
        """A big red flange 4 px wide from pixel edge c0, lit on its left rim, with a bracket from
        its bottom down to a foot on the sled."""
        ring(bm, c0, c0 + 0.6, r, FLANGE_LIT, bevel=(0.6, 0.0), sides=14)
        ring(bm, c0 + 0.6, c0 + 4, r, FLANGE, bevel=(0.0, 0.5), sides=14)
        lib.sweep(bm, G, [(c0 + 0.5, ROW + 2.5, ZC - 0.12, 0.6, 0.05), (c0 + 0.5, foot_row - 0.3, 0.09, 0.6, 0.04)],
                  sides=4, mat=BRACKET, smooth=False)
        lib.plate(bm, G, [(c0, foot_row - 0.5), (c0 + 4, foot_row - 0.5), (c0 + 4, foot_row + 0.5),
                          (c0, foot_row + 0.5)], 0.0, 0.1, mat=FOOT)

    def foot(c0, c1):
        """A grey foot under a ring, on the sled (row 17)."""
        lib.plate(bm, G, [(c0, 16.5), (c1, 16.5), (c1, 17.5), (c0, 17.5)], 0.05, 0.09, mat=GROOVE)

    # Nose (newsh2-7): a light grey ogive from its tip at column 3, drooping to the ground, to the
    # first segment.
    nose = [(2.4, 12.6, 0.0), (3.2, 12.5, 0.5), (5.0, 12.4, 1.1), (8.0, 12.0, 1.8), (11.0, 11.6, 2.4),
            (14.0, 11.3, 2.9), (17.0, 11.1, 3.3), (20.0, 11.0, 3.5), (e(24) + EPS, 11.0, 3.5)]
    lib.sweep(bm, G, [(c, r, 0.05 + rad / 12 + (ZC - 0.05 - 3.5 / 12) * rad / 3.5, rad, rad / 12)
                      for c, r, rad in nose], sides=12, mat=NOSE)
    foot(21, 24)

    # Six identical segments (newsh2-9): groove, collar, ring, groove, collar, ring, flange, ring.
    for a0 in SEGMENTS:
        lib.sweep(bm, G, [(e(a0) - EPS, ROW, ZC, 2.8, 2.8 / 12), (e(a0 + 1), ROW, ZC, 2.8, 2.8 / 12)],
                  sides=12, mat=GROOVE)
        ring(bm, a0 + 1, a0 + 4, 2.5, COLLAR, bevel=(0.0, 0.0))
        ring(bm, a0 + 4, a0 + 8, 3.5, GREY)
        ring(bm, a0 + 8, a0 + 9, 2.8, GROOVE, bevel=(0.0, 0.0))
        ring(bm, a0 + 9, a0 + 12, 2.5, COLLAR, bevel=(0.0, 0.0))
        ring(bm, a0 + 12, a0 + 17, 3.5, GREY)
        flange(a0 + 17, 4.0, 18)
        # The last ring runs on into the next piece (the next segment's groove, or the end piece).
        ring(bm, a0 + 21, a0 + 24 + EPS, 3.5, GREY, bevel=(0.5, 0.0))
        foot(a0 + 5, a0 + 7)
        foot(a0 + 14, a0 + 16)
        foot(a0 + 22, a0 + 24)

    # End piece (newsh2-11): the end of the last ring, a bigger flange, a ring, a groove, a collar
    # and a long cylinder with a rounded cap.
    a0 = 168
    ring(bm, a0 - EPS, a0 + 2, 3.5, GREY, bevel=(0.0, 0.5))
    flange(a0 + 2, 5.2, 19)
    ring(bm, a0 + 6, a0 + 10, 3.5, GREY)
    ring(bm, a0 + 10, a0 + 11, 2.8, GROOVE, bevel=(0.0, 0.0))
    ring(bm, a0 + 11, a0 + 14, 2.5, COLLAR, bevel=(0.0, 0.0))
    cap = [(e(a0 + 14), 3.0), (e(a0 + 14) + 0.5, 3.5), (e(a0 + 20), 3.5), (e(a0 + 21.5), 3.2),
           (e(a0 + 22.6), 2.4), (e(a0 + 23.4), 1.3), (e(a0 + 23.8), 0.0)]
    lib.sweep(bm, G, [(c, ROW, ZC, r, r / 12) for c, r in cap], sides=12, mat=GREY)
    foot(a0 + 7, a0 + 9)
    foot(a0 + 16, a0 + 20)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e_["model"], e_["cx"] - CX0, e_["cy"] - CY0) for e_ in sprite["assemblyLayout"]
              if e_["model"] != "newsh2-9" or e_["cx"] == EXPORT_9]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        tiles = [(e_["model"], e_["cx"] - CX0 + W // 2 - 12, e_["cy"] - CY0 + H // 2 - 14)
                 for e_ in sprite["assemblyLayout"]]
        ref, size = lib.composite_png(ROOT, tiles, W, H, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=size, view_px=900)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
