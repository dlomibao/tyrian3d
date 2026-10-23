"""Green dome generator (newshj.shp, assembly of 4 pieces): a 3D version of its sprites.

Seen in episode 2 (levels 2.2, 2.6 and 2.21). Four 2x2 ground pieces make one 48x56 px machine
(sprite.json `assemblyLayout`): newshj-13 and newshj-15 are its head, a green block with three
pale glossy domes in a row, a rounded pod down each side, a red clamp at each top corner and a
red bracket with a yellow lamp hanging down each side, and a dark louvred grille under the domes;
newshj-51 and newshj-53 are its base, a wide lens-shaped platform with raised panels and a dark
sloping front skirt, joined to the head by a ribbed pale column.

The whole machine is built once in assembly coordinates (mirror symmetric about pixel column 24),
then cut into the four pieces with common.split_assembly. It sits on the ground (base at z = 0).

Run: blender --background --python assets/blender/enemies/assembly-newshj-51.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b109 as lib  # noqa: E402
from lib_b109 import PX, common, sym  # noqa: E402

NAME = "assembly-newshj-51"
ROOT = common.repo_root(__file__)
PIECES = ["newshj-13", "newshj-15", "newshj-51", "newshj-53"]
# Assembly pixel (0, 0) is the top-left of newshj-13; the 48x56 machine's centre is screen (168, 104).
CX0, CY0 = 168, 104
G = lib.Grid(48, 56)
AXE = 24.5  # mirror axis: the centre of pixel column 24 (as an edge coordinate)
AX = G.x(AXE)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshj51"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(40, metallic=0.3, roughness=0.5),  # 0 body green
        pal(38, metallic=0.25, roughness=0.55),  # 1 darker green (lower body)
        pal(42, metallic=0.35, roughness=0.4),  # 2 light green (pods, column)
        pal(43, metallic=0.35, roughness=0.4),  # 3 pale green ridges and panels
        pal(45, metallic=0.2, roughness=0.2),  # 4 pale glossy domes
        pal(47, metallic=0.3, roughness=0.25),  # 5 bright stripes
        pal(33, metallic=0.2, roughness=0.7),  # 6 dark grille / skirt
        pal(36, metallic=0.25, roughness=0.6),  # 7 grille slats
        pal(115, metallic=0.4, roughness=0.45),  # 8 red clamps
        pal(118, metallic=0.4, roughness=0.4),  # 9 bright red tops
        pal(124, emission_strength=4.0),  # 10 yellow lamp
        pal(120, emission_strength=3.0),  # 11 orange lamp
        pal(46, metallic=0.3, roughness=0.3),  # 12 pale stripes
        pal(34, metallic=0.2, roughness=0.65),  # 13 dark skirt
        pal(39, metallic=0.25, roughness=0.55),  # 14 funnel green
    ]
    (BODY, DARK, LIGHT, PALE, DOME, BRIGHT, GRILLE, SLAT, RED, REDTOP, LAMP, LAMP2, STRIPE,
     SKIRT, FUNNEL) = range(15)
    bm = bmesh.new()
    x, y = G.x, G.y

    # ---- head (rows 4-27) ----
    body = sym([(AXE, 6.0), (20.5, 6.0), (20.0, 5.0), (9.0, 5.0), (8.0, 5.6), (5.0, 6.0), (4.4, 8.0),
                (3.4, 9.0), (2.9, 10.0), (2.9, 15.0), (3.6, 16.0), (9.0, 16.0), (9.6, 19.2), (AXE, 19.2)], AXE)
    lib.prism(bm, G.pts(body), 0.0, 0.28, mat=BODY, bevel=0.04)

    # Funnel under the body down to the column (rows 16-27), a U round the grille.
    funnel = sym([(AXE, 16.5), (9.0, 16.5), (9.0, 21.2), (11.0, 21.8), (13.0, 23.0), (14.2, 24.2),
                  (15.0, 25.2), (15.0, 27.6), (17.2, 27.6), (17.2, 19.0), (AXE, 19.0)], AXE)
    lib.prism(bm, G.pts(funnel), 0.0, 0.22, mat=FUNNEL, bevel=0.03, top_mat=FUNNEL)

    # Dark louvred grille under the domes (rows 19-23, columns 17-31) with two slats.
    lib.box(bm, x(17.0), y(23.8), x(32.0), y(19.0), 0.0, 0.12, mat=GRILLE)
    for r in (20.0, 22.0):
        lib.box(bm, x(17.0), y(r + 1.0), x(32.0), y(r), 0.1, 0.145, mat=SLAT)

    # Domes: a big one each side (columns 9-19, rows 5-14) and a narrower one in the middle.
    v0 = len(bm.verts)
    lib.dome(bm, x(14.6), y(10.1), 5.5 * PX, 5.0 * PX, 0.3, z0=0.22, sides=20, rings=5, mat=DOME, power=0.8, square=0.6)

    # Rounded pod down each side (columns 3-5, rows 8-14) and the ridge beside it (columns 7-8).
    lib.sweep(bm, [(x(4.6), y(7.6), 0.25, 0.0, 0.0), (x(4.6), y(8.3), 0.25, 1.5 * PX, 0.08),
                   (x(4.6), y(9.3), 0.25, 1.8 * PX, 0.1), (x(4.6), y(14.4), 0.25, 1.8 * PX, 0.1),
                   (x(4.6), y(15.3), 0.25, 0.0, 0.0)], sides=10, mat=LIGHT)
    lib.box(bm, x(7.0), y(15.0), x(9.0), y(8.0), 0.2, 0.31, mat=LIGHT, bevel=0.02)

    # Red clamp on the top corner (columns 5-7, rows 6-7).
    lib.prism(bm, [(x(4.9), y(8.3)), (x(8.1), y(8.3)), (x(8.1), y(5.8)), (x(4.9), y(5.8))], 0.0, 0.36,
              mat=RED, bevel=0.03, top_mat=REDTOP)

    # Red bracket hanging down the side (rows 16-23) and curling in under the body, with its lamp.
    lib.prism(bm, [(x(3.9), y(17.2)), (x(9.2), y(17.2)), (x(9.2), y(15.8)), (x(3.9), y(15.8))], 0.0, 0.26,
              mat=RED, bevel=0.02, top_mat=REDTOP)
    lib.sweep(bm, [(x(6.5), y(16.5), 0.13, 1.7 * PX, 0.11), (x(6.5), y(21.0), 0.13, 1.7 * PX, 0.11),
                   (x(7.6), y(22.4), 0.12, 1.5 * PX, 0.1), (x(9.6), y(23.1), 0.11, 1.3 * PX, 0.09),
                   (x(12.0), y(23.6), 0.1, 1.0 * PX, 0.08), (x(12.4), y(23.6), 0.1, 0.0, 0.0)],
              sides=8, mat=RED)
    lib.ellipsoid(bm, x(6.5), y(19.4), 0.235, 0.9 * PX, 1.3 * PX, 0.035, mat=LAMP)
    lib.ellipsoid(bm, x(6.5), y(18.2), 0.23, 0.9 * PX, 0.8 * PX, 0.03, mat=LAMP2)
    # Small red tab beside the column (columns 18-19, rows 24-26).
    lib.prism(bm, [(x(17.8), y(27.2)), (x(20.2), y(27.2)), (x(20.2), y(24.0)), (x(17.8), y(24.0))], 0.0, 0.13,
              mat=RED, bevel=0.015, top_mat=REDTOP)
    # Pale ridge down the funnel (columns 15-16, rows 19-26).
    lib.sweep(bm, [(x(16.0), y(17.0), 0.21, 0.0, 0.0), (x(16.0), y(17.8), 0.21, 0.8 * PX, 0.04),
                   (x(16.0), y(26.8), 0.21, 0.8 * PX, 0.04), (x(16.0), y(27.5), 0.21, 0.0, 0.0)],
              sides=6, mat=PALE)

    # ---- base (rows 34-52), left half ----
    # Raised panels on the platform: a pale strip, two ribs, a block, the light outer rim.
    lib.box(bm, x(3.6), y(43.4), x(11.0), y(41.6), 0.17, 0.205, mat=PALE)
    lib.box(bm, x(11.0), y(46.4), x(12.9), y(38.0), 0.17, 0.21, mat=PALE)
    lib.box(bm, x(14.0), y(46.4), x(15.0), y(37.0), 0.17, 0.205, mat=PALE)
    lib.box(bm, x(18.0), y(46.3), x(21.0), y(41.6), 0.17, 0.235, mat=PALE, bevel=0.015)
    lib.box(bm, x(3.3), y(44.0), x(4.8), y(39.2), 0.17, 0.2, mat=PALE)

    lib.mirror_since(bm, v0, AX)

    # ---- centre parts ----
    lib.dome(bm, x(AXE), y(10.6), 4.2 * PX, 4.5 * PX, 0.28, z0=0.22, sides=20, rings=5, mat=DOME, power=0.8, square=0.6)

    # Ribbed column from under the grille down into the base (columns 20-28, rows 22-39).
    col = [(21.5, 3.6, 0.12, 0.14), (27.5, 3.6, 0.12, 0.14), (28.3, 2.8, 0.1, 0.14), (32.4, 2.8, 0.1, 0.14),
           (33.2, 4.4, 0.12, 0.14), (40.2, 4.4, 0.12, 0.14)]
    start = len(bm.verts)
    common.loft(bm, [(y(r), w * PX, h, z) for r, w, h, z in col], sides=12, mat_index=LIGHT)
    common.shift_x(bm, start, AX)
    for dc in (-1.0, 1.0):
        lib.sweep(bm, [(AX + dc * PX, y(22.0), 0.25, 0.4 * PX, 0.025), (AX + dc * PX, y(27.6), 0.25, 0.4 * PX, 0.025),
                       (AX + dc * PX, y(28.2), 0.235, 0.4 * PX, 0.025), (AX + dc * PX, y(32.5), 0.235, 0.4 * PX, 0.025),
                       (AX + dc * PX, y(33.2), 0.25, 0.4 * PX, 0.025), (AX + dc * PX, y(40.0), 0.25, 0.4 * PX, 0.025)],
                  sides=6, mat=BRIGHT)
    for dc in (-3.0, 3.0):
        lib.sweep(bm, [(AX + dc * PX, y(33.4), 0.225, 0.45 * PX, 0.02), (AX + dc * PX, y(39.8), 0.225, 0.45 * PX, 0.02)],
                  sides=6, mat=STRIPE)

    # Lens-shaped platform: its flat top (rows 34-46) and the dark skirt sloping down at the front.
    top = sym([(AXE, 34.6), (18.0, 34.8), (13.0, 35.8), (9.0, 36.8), (5.0, 37.8), (2.8, 39.2), (2.8, 46.8),
               (AXE, 46.8)], AXE)
    lib.prism(bm, G.pts(top), 0.0, 0.18, mat=BODY, bevel=0.025)
    edge = [(2.9, 46.9), (3.2, 47.1), (5.0, 48.0), (8.0, 49.0), (12.0, 50.0), (17.0, 51.0), (22.0, 52.0), (AXE, 52.2)]
    edge = edge + [(2 * AXE - c, r) for c, r in reversed(edge[:-1])]
    rings = []
    for c, r in edge:
        yt, yb = y(46.7), y(r)
        rings.append([(x(c), yt, 0.0), (x(c), yt, 0.175), (x(c), yb, 0.035), (x(c), yb, 0.0)])
    lib.skin(bm, rings, mat=SKIRT)
    # Pale vent down the middle of the skirt (columns 23-25, rows 47-51) and two light slats.
    lib.sweep(bm, [(AX, y(46.6), 0.17, 1.4 * PX, 0.035), (AX, y(52.0), 0.05, 1.4 * PX, 0.035),
                   (AX, y(52.3), 0.045, 0.0, 0.0)], sides=8, mat=LIGHT)
    for r, z in ((48.4, 0.125), (50.4, 0.08)):
        lib.box(bm, x(17.5), y(r + 0.6), x(31.5), y(r), z - 0.012, z + 0.012, mat=FUNNEL)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    out = lib.preview_arg()
    if out:
        places = [(n, cx - CX0 + 24 - 12, cy - CY0 + 28 - 14) for n, cx, cy in
                  [(e["model"], e["cx"], e["cy"]) for e in sprite["assemblyLayout"] if e["model"] in PIECES]]
        ref = lib.composite_png(ROOT, places, 48, 56, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
