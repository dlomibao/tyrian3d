"""Long segmented pipe on a sled (newsh2.shp, assembly of 8 pieces): a 3D version of its sprites.

Seen in episode 1 (level 1.3) and episode 3. Eight 2x2 ground sprites in a row (sprite.json
`assemblyLayout`) make one 192x28 px pipe lying across the screen: a light grey bullet nose
(newsh2-7) on the left, six identical segments (newsh2-9, so one model serves all six) of grey
rings, narrow red collars and a big red flange with a bracket down to the ground, and an end
piece (newsh2-11) with a bigger flange and a long grey cylinder with a rounded cap. The dark band
under the pipe is what holds it a few px off the ground: a dark cradle block under each grey ring,
its south face sloping to the ground, a thin rail joining them, and under each flange a red
bracket frame with a see-through hole; under the red collars the ground shows through.

The pipe is built once in assembly coordinates (all six segments, so their joins are exact) and
cut into pieces with common.split_assembly; one of the middle segments is exported as newsh2-9.
Ground object: the sled's base is at z = 0.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-9.py [-- --preview out.png]
(the preview is the whole pipe; each piece also gets <piece>.png next to it).
"""

import math
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

ROW = 10.5  # the pipe's axis (sprite row centre): rings cover rows 7-14, the sprite's outline ring
ZC = 0.53  # the pipe's axis height: the pipe (radius 3.9 px) stands about 2.5 px off the ground
ZT = ZC - 0.21  # top of the cradles, just under the pipe's underside where it leaves the top view
SLOPE_END = 19.0  # pixel edge (row) where the cradles' sloping south faces meet the ground
EPS = 0.15  # px: tubes that meet at a piece boundary overlap it a little so the cut is clean
R_RING = 3.9  # grey rings (rows 7-14, outline included)
R_ROD = 2.4  # the red rods between rings (the concept's thin red couplings)
R_GROOVE = 3.0  # dark bolt rings and seams between parts
R_FLANGE = 4.85  # copper/red flange bands (rows 6-14)

# Remodelled on the concept (assets/blender/features/concepts/assembly-newsh2-9.jpg, registered in
# assets/blender/textures/assembly-newsh2-9/concept.png): each segment is a riveted grey ring, a
# thin red rod held by two tie rods, a dark bolt ring, a red rod, a broad riveted grey ring, a broad
# flat-faced flange band and a short grey ring. The parts stay on the sprite's columns; the concept
# maps were re-registered onto them (its segments drift up to 2 px against the sprite's).


def e(a):
    """Left edge of assembly pixel column a, as a fractional column for G.X."""
    return a - 0.5


def ring(bm, c0, c1, r, mat, bevel=(0.5, 0.5), sides=12, smooth=True, row=ROW, z=ZC):
    """A section of pipe from pixel edge c0 to c1 with radius r px, its ends chamfered by
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
    faces = lib.sweep(bm, G, path, sides=sides, mat=mat, smooth=smooth)
    # Crisp ring edges: the chamfers and end faces are flat-shaded, only the round side is smooth.
    for f in faces:
        f.normal_update()
        if abs(f.normal.x) > 0.3:
            f.smooth = False


def tie_rods(bm, c0, c1, mat):
    """The concept's two thin grey tie rods along the sides of a red rod, ring to ring."""
    for side in (-1, 1):
        lib.sweep(bm, G, [(e(c0) - 0.2, ROW + side * 2.55, ZC, 0.45, 0.45 / 12),
                          (e(c1) + 0.2, ROW + side * 2.55, ZC, 0.45, 0.45 / 12)],
                  sides=6, mat=mat, smooth=True)


def prism(bm, c0, c1, profile, mat):
    """A block from pixel edge c0 to c1 (columns) with a cross-section of (row edge, z) points."""
    xs = (G.X(e(c0)), G.X(e(c1)))
    rings = [[bm.verts.new((x, G.Y(r - 0.5), z)) for r, z in profile] for x in xs]
    n = len(profile)
    faces = [bm.faces.new(list(reversed(rings[0]))), bm.faces.new(rings[1])]
    for k in range(n):
        j = (k + 1) % n
        faces.append(bm.faces.new((rings[0][k], rings[0][j], rings[1][j], rings[1][k])))
    for f in faces:
        f.material_index = mat
        f.smooth = False


def zs(r, end=SLOPE_END):
    """Height of the cradles' sloping south face at row edge r (14 = under the pipe's edge)."""
    return max(0.0, ZT * (end - r) / (end - 14.0))


def slope_bar(bm, c0, c1, r0, r1, mat, end=SLOPE_END, t=0.07):
    """A bar t thick lying on the sloping face between row edges r0 and r1."""
    prism(bm, c0, c1, [(r0, max(0.0, zs(r0, end) - t)), (r0, zs(r0, end) + 0.01),
                       (r1, zs(r1, end) + 0.01), (r1, max(0.0, zs(r1, end) - t))], mat)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh2_9"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(8, metallic=0.55, roughness=0.4),  # 0 grey rings (riveted steel)
        pal(11, metallic=0.25, roughness=0.55),  # 1 light grey nose (soft sheen)
        pal(3, metallic=0.4, roughness=0.5),  # 2 dark bolt rings, seams
        pal(72, metallic=0.3, roughness=0.35),  # 3 red rods
        pal(71, metallic=0.25, roughness=0.65),  # 4 flange bands: mid red, matte faces
        pal(77, metallic=0.45, roughness=0.35),  # 5 flanges' lit left chamfer
        pal(67, metallic=0.2, roughness=0.6),  # 6 dark red brackets
        pal(70, metallic=0.2, roughness=0.5),  # 7 bracket feet
        pal(1, metallic=0.1, roughness=0.85),  # 8 dark cradles (the sprite draws them in index 1)
        pal(66, metallic=0.1, roughness=0.8),  # 9 darkest red bracket bars
        pal(16, metallic=0.1, roughness=0.85),  # 10 the rail
        pal(6, metallic=0.5, roughness=0.45),  # 11 tie rods
    ]
    GREY, NOSE, GROOVE, COLLAR, FLANGE, FLANGE_LIT, BRACKET, FOOT, SLED, BAR, RAIL, TIE = range(12)
    bm = bmesh.new()

    # A thin rail along the pipe's south side (rows 15-16) joining the cradles, low on the ground.
    prism(bm, 13, W, [(15.2, 0.0), (15.2, zs(15.2) * 0.45), (16.8, zs(16.8) * 0.45), (16.8, 0.0)], RAIL)

    def flange(c0, r, foot_row):
        """A broad flange band 4 px wide from pixel edge c0: flat faces, a crisp lit chamfer on its
        left edge, held by a red bracket frame: a post on its left, a top bar, a hole, a lower bar
        and a lit foot on the ground at foot_row."""
        ring(bm, c0, c0 + 0.5, r, FLANGE_LIT, bevel=(0.5, 0.0), sides=16)
        ring(bm, c0 + 0.5, c0 + 4, r, FLANGE, bevel=(0.0, 0.35), sides=16)
        end = foot_row + 1.0
        prism(bm, c0, c0 + 1, [(9.0, 0.0), (10.0, ZT), (14.0, ZT), (end, 0.0)], BRACKET)
        prism(bm, c0 + 1, c0 + 4, [(9.0, 0.0), (10.0, ZT), (14.0, ZT), (15.0, zs(15.0, end)), (15.0, 0.0)], BRACKET)
        slope_bar(bm, c0 + 1, c0 + 4, 15.0, foot_row - 2.0, BAR, end)
        slope_bar(bm, c0 + 1, c0 + 4, foot_row - 1.0, foot_row, BAR, end)
        prism(bm, c0, c0 + 4, [(foot_row, 0.0), (foot_row, zs(foot_row, end) + 0.02), (end, 0.04), (end, 0.0)], FOOT)

    def foot(c0, c1):
        """A dark cradle under a grey ring: hidden under the pipe on top, its south face sloping to
        the ground (rows 15-18), with a ridge across it at row 17."""
        prism(bm, c0, c1, [(8.5, 0.0), (10.0, ZT), (14.0, ZT), (SLOPE_END, 0.0)], SLED)
        slope_bar(bm, c0 + 0.3, c1 - 0.3, 17.0, 18.0, GROOVE, t=0.05)

    # Nose (newsh2-7): the concept's long light grey ogive from its tip at column 2, dipping a
    # little (the sprite's tip sits at rows 12-13), to the first segment's full ring radius.
    nose = [(2.3, 12.5, 0.0), (3.2, 12.4, 0.6), (5.0, 12.1, 1.3), (8.0, 11.6, 2.1), (11.0, 11.2, 2.8),
            (14.0, 10.9, 3.3), (17.0, 10.7, 3.65), (20.0, 10.5, 3.85), (23.0, 10.5, 3.9), (e(24) + EPS, 10.5, 3.9)]
    lib.sweep(bm, G, [(c, r, ZC - 0.22 * (1 - rad / 3.9), rad, rad / 12) for c, r, rad in nose],
              sides=14, mat=NOSE)
    foot(19, 24)

    # Six identical segments (newsh2-9), on the sprite's columns: bolt ring, red rod, riveted ring,
    # bolt ring, red rod, broad riveted ring, flange band, short ring.
    for a0 in SEGMENTS:
        ring(bm, a0 - EPS, a0 + 1, R_GROOVE, GROOVE, bevel=(0.0, 0.0))
        ring(bm, a0 + 1, a0 + 4, R_ROD, COLLAR, bevel=(0.0, 0.0))
        tie_rods(bm, a0 + 1, a0 + 4, TIE)
        ring(bm, a0 + 4, a0 + 8, R_RING, GREY, bevel=(0.45, 0.45))
        ring(bm, a0 + 8, a0 + 9, R_GROOVE, GROOVE, bevel=(0.0, 0.0))
        ring(bm, a0 + 9, a0 + 12, R_ROD, COLLAR, bevel=(0.0, 0.0))
        ring(bm, a0 + 12, a0 + 17, R_RING, GREY, bevel=(0.45, 0.3))
        flange(a0 + 17, R_FLANGE, 18)
        # The last ring runs on into the next piece (the next segment's bolt ring, or the end).
        ring(bm, a0 + 21, a0 + 24 + EPS, R_RING, GREY, bevel=(0.3, 0.0))
        foot(a0 + 4, a0 + 8)
        foot(a0 + 12, a0 + 17)
        foot(a0 + 21, a0 + 25)

    # End piece (newsh2-11): the end of the last ring, a bigger flange, a ring, a bolt ring, a red
    # rod, and the concept's plain cylinder ending in a rounded dome cap.
    a0 = 168
    ring(bm, a0 - EPS, a0 + 2, R_RING, GREY, bevel=(0.0, 0.3))
    flange(a0 + 2, 5.2, 19)
    ring(bm, a0 + 6, a0 + 10, R_RING, GREY, bevel=(0.3, 0.45))
    ring(bm, a0 + 10, a0 + 11, R_GROOVE, GROOVE, bevel=(0.0, 0.0))
    ring(bm, a0 + 11, a0 + 14, R_ROD, COLLAR, bevel=(0.0, 0.0))
    tie_rods(bm, a0 + 11, a0 + 14, TIE)
    ring(bm, a0 + 14, a0 + 15, 3.2, GROOVE, bevel=(0.0, 0.0))
    # The plain cylinder (rings' radius, chamfered only at its left joint) ending in a rounded
    # hemispherical dome whose tip reaches the sprite's last column.
    tip = e(W) + 0.05
    x0 = tip - R_RING
    lib.sweep(bm, G, [(e(a0 + 15), ROW, ZC, R_RING - 0.3, (R_RING - 0.3) / 12),
                      (e(a0 + 15) + 0.3, ROW, ZC, R_RING, R_RING / 12)]
              + [(x0 + R_RING * math.sin(t), ROW, ZC, max(R_RING * math.cos(t), 0.0), max(R_RING * math.cos(t), 0.0) / 12)
                 for t in [k * math.pi / 2 / 8 for k in range(9)]],
              sides=12, mat=GREY)
    foot(a0 + 6, a0 + 10)
    foot(a0 + 15, a0 + 23)

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
