"""Grey carapace bunker with a pyramid roof (newsh2.shp, assembly of 4 pieces): a 3D version of
its sprites.

Seen in episode 1 (levels 1.28 and 1.3) and episode 3. Four 2x2 ground sprites (newsh2-81 and
newsh2-83 on top, newsh2-119 and newsh2-121 below; sprite.json `assemblyLayout`) make one 48x56
px tile of dirt with a structure on it: a dark grey carapace, rounded at the back (top of the
screen) and splitting into two prongs at the front, with a brown pyramid roof on top, two thin
brown legs on each side reaching into the dirt, a tan rod between the prongs and a long cast
shadow to the lower right. The newsh2-229 piece listed below it in the layout is a separate
object (another batch), so it isn't built here.

The sprites fill their tiles with dirt, so the model is a thin dirt platform (base at z = 0)
with the structure on it, built once in assembly coordinates and cut into the four pieces with
common.split_assembly. The structure is mirror symmetric about pixel column 20; the right prong
is mostly in shadow in the sprite, so its back half is dark.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-119.py [-- --preview out.png]
(the preview is the whole tile; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b129 as lib  # noqa: E402

NAME = "assembly-newsh2-119"
ROOT = common.repo_root(__file__)
PIECES = ["newsh2-81", "newsh2-83", "newsh2-119", "newsh2-121"]
# Assembly pixel (0, 0) is the top-left corner of newsh2-81 (screen cx 248 - 12, cy 139 - 14);
# the assembly is 48 x 56 px and its centre (screen 260, 153) is the Blender origin.
CX0, CY0 = 260, 153
W, H = 48, 56
G = lib.Grid(W, H)
AXIS = 20  # the structure is symmetric about the centre of pixel column 20

SHELL_H = 0.25


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh2_119"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(19, metallic=0.0, roughness=0.95),  # 0 dirt, pyramid's shaded lower right face
        pal(2, metallic=0.0, roughness=1.0),  # 1 cast shadow, shadowed prong
        pal(5, metallic=0.3, roughness=0.4),  # 2 carapace
        pal(6, metallic=0.3, roughness=0.35),  # 3 raised centre band
        pal(25, metallic=0.1, roughness=0.7),  # 4 lit legs, rod
        pal(23, metallic=0.1, roughness=0.7),  # 5 shaded legs
        pal(24, metallic=0.05, roughness=0.75),  # 6 pyramid upper left face
        pal(20, metallic=0.05, roughness=0.75),  # 7 pyramid upper right face
        pal(22, metallic=0.05, roughness=0.75),  # 8 pyramid lower left face, pebbles
        pal(26, metallic=0.1, roughness=0.6),  # 9 pyramid ridge
    ]
    DIRT, SHADOW, SHELL, BAND, LEG_L, LEG_R, P_UL, P_UR, P_LL, RIDGE = range(10)
    bm = bmesh.new()
    X, Y = G.X, G.Y

    # Dirt platform over the whole tile, and the cast shadow on it.
    lib.plate(bm, G, [(0, 0), (W, 0), (W, H), (0, H)], 0.0, 0.03, mat=DIRT)
    lib.plate(bm, G, [(17, 27), (36, 27), (40.5, 30), (41.5, 36), (41, 44), (36, 46.5), (33, 51),
                      (29, 52.5), (22, 51.5), (17, 50), (14, 47.5), (17.5, 45)],
              0.03, 0.036, mat=SHADOW)

    # Carapace: a low plated shell (flat top, bevelled sides) down the axis, from its round back
    # (row 3) to row 28.
    shell = [(2.8, 3.6, 0.07), (3.3, 5.6, 0.13), (4.2, 7.4, 0.18), (5.3, 8.7, 0.21), (6.5, 9.7, 0.235),
             (8.0, 10.4, SHELL_H), (14.0, 10.5, SHELL_H), (17.0, 10.5, 0.2), (27.0, 10.4, 0.2),
             (28.6, 10.0, 0.18)]
    lib.sweep(bm, G, [(AXIS, r, 0.03, w, h) for r, w, h in shell], mat=SHELL, smooth=False,
              profile=lib.CHAMFER)
    # Raised band down its middle (the strip between the grooves at columns 17 and 24).
    band = [(3.3, 2.0, 0.15), (4.0, 3.0, 0.21), (5.5, 3.4, SHELL_H + 0.01), (7.5, 3.4, SHELL_H + 0.03),
            (15.0, 3.4, SHELL_H + 0.03)]
    lib.sweep(bm, G, [(AXIS + 0.5, r, 0.03, w, h) for r, w, h in band], mat=BAND, smooth=False,
              profile=lib.CHAMFER)

    # Prongs: the shell's front splits into two plated rails (columns 10-17 and 23-28).
    left = [(26.0, 13.6, 4.0, 0.2), (41.0, 13.6, 4.0, 0.19), (42.0, 14.0, 3.6, 0.17), (43.0, 14.5, 3.1, 0.15),
            (44.0, 15.0, 2.6, 0.12), (45.0, 15.5, 2.0, 0.09), (45.9, 16.0, 1.2, 0.05)]
    lib.sweep(bm, G, [(c, r, 0.03, w, h) for r, c, w, h in left], mat=SHELL, smooth=False,
              profile=lib.CHAMFER)
    # The right prong's back half lies in the pyramid's shadow.
    lib.sweep(bm, G, [(25.8, 26.0, 0.03, 3.2, 0.17), (25.6, 34.6, 0.03, 3.1, 0.17)], mat=SHADOW,
              smooth=False, profile=lib.CHAMFER, cap_end=False)
    right = [(34.6, 25.6, 3.1, 0.17), (41.5, 25.6, 3.1, 0.16), (42.5, 25.4, 2.9, 0.15), (43.5, 25.0, 2.5, 0.12),
             (44.5, 24.5, 2.0, 0.09), (45.6, 24.0, 1.2, 0.05)]
    lib.sweep(bm, G, [(c, r, 0.03, w, h) for r, c, w, h in right], mat=SHELL, smooth=False,
              profile=lib.CHAMFER, cap_start=False)

    # Tan rod between the prongs, under the pyramid's ridge (rows 29-34).
    lib.sweep(bm, G, [(19.6, 27.0, 0.1, 1.0, 0.06), (19.6, 34.3, 0.06, 1.0, 0.05), (19.6, 35.2, 0.05, 0.0, 0.0)],
              sides=8, mat=LEG_L)

    # Thin legs from the shell's sides down into the dirt, two a side.
    for dr in (0.0, 4.9):
        lib.sweep(bm, G, [(10.6, 8.6 + dr, 0.14, 0.0, 0.0), (10.0, 9.0 + dr, 0.13, 1.0, 0.06),
                          (7.0, 11.4 + dr, 0.09, 1.0, 0.06), (4.0, 14.3 + dr, 0.03, 0.9, 0.05),
                          (3.4, 14.8 + dr, 0.03, 0.0, 0.0)], sides=6, mat=LEG_L)
        lib.sweep(bm, G, [(29.4, 9.6 + dr, 0.14, 0.0, 0.0), (30.0, 10.0 + dr, 0.13, 1.0, 0.06),
                          (33.0, 12.4 + dr, 0.09, 1.0, 0.06), (36.0, 15.3 + dr, 0.03, 0.9, 0.05),
                          (36.6, 15.8 + dr, 0.03, 0.0, 0.0)], sides=6, mat=LEG_R)

    # Pyramid roof on top: its point at the back (row 13), its peak over row 21, its base along
    # row 27 from column 5 to 35. Four faces, lit like the sprite's (upper left brightest).
    A = (X(AXIS), Y(12.6), 0.4)
    BL = (X(4.8), Y(27.6), 0.12)
    BR = (X(35.2), Y(27.6), 0.12)
    BM = (X(AXIS), Y(28.4), 0.12)
    P = (X(AXIS), Y(21.0), 0.66)
    lib.poly(bm, [A, BL, P], mat=P_UL)
    lib.poly(bm, [A, P, BR], mat=P_UR)
    lib.poly(bm, [BL, BM, P], mat=P_LL)
    lib.poly(bm, [P, BM, BR], mat=DIRT)
    lib.poly(bm, [A, BR, BM, BL], mat=P_LL)
    # The light ridge from the point up to the peak.
    lib.sweep(bm, G, [(AXIS, 12.9, 0.41, 0.0, 0.0), (AXIS, 13.4, 0.43, 0.45, 0.02),
                      (AXIS, 20.6, 0.665, 0.45, 0.02), (AXIS, 21.0, 0.675, 0.0, 0.0)], sides=6, mat=RIDGE)

    # Light pebbles in the dirt.
    for c, r, s in [(37, 6.4, 1.0), (45.4, 6.2, 1.0), (45.4, 20.2, 1.0), (45.4, 34.2, 1.0), (10, 45.4, 1.0),
                    (1, 48.4, 1.0), (45.4, 48.2, 1.0), (43.5, 24, 0.9), (5, 41.5, 0.8), (8, 38, 0.7),
                    (43, 38, 0.7), (43, 10, 0.7), (8, 52, 0.7), (32, 52, 0.7)]:
        lib.ellipsoid(bm, G, c, r, 0.03, s, s, 0.035 * s, mat=P_LL, segments=6, rings=3)

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
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        tiles = [(n, cx + W // 2 - 12, cy + H // 2 - 14) for n, cx, cy in layout]
        ref, size = lib.composite_png(ROOT, tiles, W, H, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=size, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
