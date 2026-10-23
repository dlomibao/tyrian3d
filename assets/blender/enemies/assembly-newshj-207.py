"""Green dome cannon (newshj.shp, assembly of 2 pieces): a 3D version of its sprites.

Seen in episode 2 (levels 2.2 and 2.21). Two 2x2 ground pieces side by side make one 48x28 px
machine (sprite.json `assemblyLayout`) lying across the screen: newshj-169 is its head, a green
block with one big pale glossy dome, a rounded pod down its left side, a red clamp on the top
corner, a red bracket with a yellow lamp hanging down the side and a dark louvred grille below;
newshj-207 is its body, which tapers to the right like the base of the dome generator
(assembly-newshj-51): a flat top with raised panels, a short ribbed collar where it meets the
head and a dark louvred skirt sloping down along the front.

The whole machine is built once in assembly coordinates, then cut in two with
common.split_assembly. It sits on the ground (base at z = 0).

Run: blender --background --python assets/blender/enemies/assembly-newshj-207.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b109 as lib  # noqa: E402
from lib_b109 import PX, common  # noqa: E402

NAME = "assembly-newshj-207"
ROOT = common.repo_root(__file__)
PIECES = ["newshj-169", "newshj-207"]
# Assembly pixel (0, 0) is the top-left of newshj-169; the 48x28 machine's centre is screen (142, 77).
CX0, CY0 = 142, 77
G = lib.Grid(48, 28)

# The front skirt's bottom edge: (column edge, row edge), left to right.
SKIRT = [(16.8, 24.0), (24.0, 24.0), (27.0, 24.0), (32.0, 23.0), (37.0, 22.0), (41.0, 21.0), (44.0, 20.0),
         (45.9, 19.0), (46.0, 18.9)]
SKIRT_TOP, Z_TOP, Z_BOT = 18.8, 0.175, 0.035


def skirt_bottom(c):
    """The skirt's bottom row at column edge c (interpolated)."""
    for (c0, r0), (c1, r1) in zip(SKIRT, SKIRT[1:]):
        if c0 <= c <= c1:
            return r0 + (r1 - r0) * (c - c0) / (c1 - c0)
    return SKIRT[-1][1]


def skirt_z(c, r):
    rb = skirt_bottom(c)
    return Z_TOP + (Z_BOT - Z_TOP) * (r - SKIRT_TOP) / max(rb - SKIRT_TOP, 1e-3)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshj207"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(40, metallic=0.3, roughness=0.5),  # 0 body green
        pal(42, metallic=0.35, roughness=0.4),  # 1 light green (pod, collar)
        pal(43, metallic=0.35, roughness=0.4),  # 2 pale green ridges and panels
        pal(45, metallic=0.2, roughness=0.2),  # 3 pale glossy dome
        pal(47, metallic=0.3, roughness=0.25),  # 4 bright stripe
        pal(46, metallic=0.3, roughness=0.3),  # 5 pale stripe
        pal(33, metallic=0.2, roughness=0.7),  # 6 dark grille / skirt
        pal(36, metallic=0.25, roughness=0.6),  # 7 louvre slats
        pal(115, metallic=0.4, roughness=0.45),  # 8 red clamps
        pal(118, metallic=0.4, roughness=0.4),  # 9 bright red tops
        pal(124, emission_strength=4.0),  # 10 yellow lamp
        pal(120, emission_strength=3.0),  # 11 orange lamp
        pal(39, metallic=0.25, roughness=0.55),  # 12 funnel green
    ]
    BODY, LIGHT, PALE, DOME, BRIGHT, STRIPE, GRILLE, SLAT, RED, REDTOP, LAMP, LAMP2, FUNNEL = range(13)
    bm = bmesh.new()
    x, y = G.x, G.y

    # ---- head (columns 2-23) ----
    head = [(24.3, 19.2), (24.3, 6.0), (20.5, 6.0), (20.0, 5.0), (9.0, 5.0), (8.0, 5.6), (5.0, 6.0), (4.4, 8.0),
            (3.4, 9.0), (2.9, 10.0), (2.9, 15.0), (3.6, 16.0), (9.0, 16.0), (9.6, 19.2)]
    lib.prism(bm, G.pts(head), 0.0, 0.28, mat=BODY, bevel=0.04)
    funnel = [(24.0, 16.5), (9.0, 16.5), (9.0, 21.2), (11.0, 21.8), (13.0, 23.0), (14.2, 24.2), (15.0, 25.2),
              (15.0, 27.6), (17.2, 27.6), (17.2, 19.0), (24.0, 19.0)]
    lib.prism(bm, G.pts(funnel), 0.0, 0.22, mat=FUNNEL, bevel=0.03)
    lib.sweep(bm, [(x(16.0), y(17.0), 0.21, 0.0, 0.0), (x(16.0), y(17.8), 0.21, 0.8 * PX, 0.04),
                   (x(16.0), y(26.8), 0.21, 0.8 * PX, 0.04), (x(16.0), y(27.5), 0.21, 0.0, 0.0)],
              sides=6, mat=PALE)

    # One big dome (columns 9-21, rows 5-14).
    lib.dome(bm, x(15.7), y(10.1), 6.3 * PX, 5.0 * PX, 0.31, z0=0.22, sides=20, rings=5, mat=DOME,
             power=0.8, square=0.6)

    # Rounded pod down the side (columns 3-5, rows 8-14) and the ridge beside it (columns 7-8).
    lib.sweep(bm, [(x(4.6), y(7.6), 0.25, 0.0, 0.0), (x(4.6), y(8.3), 0.25, 1.5 * PX, 0.08),
                   (x(4.6), y(9.3), 0.25, 1.8 * PX, 0.1), (x(4.6), y(14.4), 0.25, 1.8 * PX, 0.1),
                   (x(4.6), y(15.3), 0.25, 0.0, 0.0)], sides=10, mat=LIGHT)
    lib.box(bm, x(7.0), y(15.0), x(9.0), y(8.0), 0.2, 0.31, mat=LIGHT, bevel=0.02)

    # Red clamp on the top corner, the red bracket with its lamp, and the red tab under the head.
    lib.prism(bm, [(x(4.9), y(8.3)), (x(8.1), y(8.3)), (x(8.1), y(5.8)), (x(4.9), y(5.8))], 0.0, 0.36,
              mat=RED, bevel=0.03, top_mat=REDTOP)
    lib.prism(bm, [(x(3.9), y(17.2)), (x(9.2), y(17.2)), (x(9.2), y(15.8)), (x(3.9), y(15.8))], 0.0, 0.26,
              mat=RED, bevel=0.02, top_mat=REDTOP)
    lib.sweep(bm, [(x(6.5), y(16.5), 0.13, 1.7 * PX, 0.11), (x(6.5), y(21.0), 0.13, 1.7 * PX, 0.11),
                   (x(7.6), y(22.4), 0.12, 1.5 * PX, 0.1), (x(9.6), y(23.1), 0.11, 1.3 * PX, 0.09),
                   (x(12.0), y(23.6), 0.1, 1.0 * PX, 0.08), (x(12.4), y(23.6), 0.1, 0.0, 0.0)],
              sides=8, mat=RED)
    lib.ellipsoid(bm, x(6.5), y(19.4), 0.235, 0.9 * PX, 1.3 * PX, 0.035, mat=LAMP)
    lib.ellipsoid(bm, x(6.5), y(18.2), 0.23, 0.9 * PX, 0.8 * PX, 0.03, mat=LAMP2)
    lib.prism(bm, G.pts([(17.8, 25.0), (17.8, 24.0), (23.2, 24.0), (23.2, 25.0), (21.2, 25.2), (21.2, 27.0),
                         (18.8, 27.0), (18.8, 25.0)]), 0.0, 0.12, mat=RED, bevel=0.015, top_mat=REDTOP)

    # ---- body (columns 24-45) ----
    top = [(24.0, 6.0), (25.5, 6.2), (31.0, 7.0), (36.0, 8.0), (40.0, 9.0), (44.0, 10.0), (46.0, 11.0),
           (46.0, 18.9), (24.0, 18.9)]
    lib.prism(bm, G.pts(top), 0.0, 0.18, mat=BODY, bevel=0.025)
    # Raised panels: a block, two ribs, a strip and the light rim at the right end.
    lib.box(bm, x(28.0), y(18.3), x(31.0), y(13.6), 0.17, 0.235, mat=PALE, bevel=0.015)
    lib.box(bm, x(34.0), y(18.4), x(35.0), y(9.0), 0.17, 0.205, mat=PALE)
    lib.box(bm, x(36.1), y(18.4), x(38.0), y(10.0), 0.17, 0.21, mat=PALE)
    lib.box(bm, x(38.0), y(15.4), x(45.4), y(13.6), 0.17, 0.205, mat=PALE)
    lib.box(bm, x(44.2), y(16.0), x(45.7), y(11.2), 0.17, 0.2, mat=PALE)
    # Short ribbed collar where the body meets the head (columns 24-27, rows 9-12).
    start = len(bm.verts)
    common.loft(bm, [(y(8.4), 0.0, 0.0, 0.2), (y(8.8), 2.0 * PX, 0.07, 0.2), (y(12.6), 2.0 * PX, 0.07, 0.2),
                     (y(13.0), 0.0, 0.0, 0.2)], sides=10, mat_index=LIGHT)
    common.shift_x(bm, start, x(26.0))
    lib.sweep(bm, [(x(25.5), y(9.0), 0.262, 0.4 * PX, 0.02), (x(25.5), y(12.4), 0.262, 0.4 * PX, 0.02)],
              sides=6, mat=BRIGHT)
    lib.sweep(bm, [(x(27.4), y(9.6), 0.245, 0.4 * PX, 0.02), (x(27.4), y(11.8), 0.245, 0.4 * PX, 0.02)],
              sides=6, mat=STRIPE)

    # Dark louvred skirt sloping down along the front, from under the head to the tapered end.
    rings = []
    for c, r in SKIRT:
        yt, yb = y(SKIRT_TOP - 0.1), y(r)
        rings.append([(x(c), yt, 0.0), (x(c), yt, Z_TOP), (x(c), yb, Z_BOT), (x(c), yb, 0.0)])
    lib.skin(bm, rings, mat=GRILLE)
    for r, c1 in ((20.0, 41.5), (22.0, 33.5)):
        cs = [17.0 + k * (c1 - 17.0) / 6 for k in range(7)]
        lib.sweep(bm, [(x(c), y(r + 0.5), skirt_z(c, r + 0.5) + 0.004, 0.45 * PX, 0.012) for c in cs],
                  sides=4, mat=SLAT, smooth=False)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    entries = [e for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in entries]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        places = [(e["model"], e["cx"] - CX0 + 24 - 12, e["cy"] - CY0 + 14 - 14) for e in entries]
        ref = lib.composite_png(ROOT, places, 48, 28, Path(tempfile.mkdtemp()) / "assembly.png", pad_to=(48, 56))
        common.render_preview([obj], str(out), str(ref), size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
