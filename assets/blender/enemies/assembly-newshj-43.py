"""Jungle bunker (newshj.shp 5, 7, 43 and 45, a 2x2 block): a 3D version of its sprites.

Seen in episode 2 (levels 2.2 and 2.24), where two of them stand side by side in the jungle. Four
2x2 sprites make one 48 x 56 px block: a grey building sitting in jungle undergrowth that fills
the rest of the tiles, with its drop shadow falling to the right and below. The building has

- a low base slab across the bottom (rows 32-47) whose front edge slopes down to the ground, with
  two small posts on its left, a raised box and a dark trench on top;
- a tall tower (columns 13-25) with three glowing green windows in a light frame; the windows
  light up one after another (frames 5, 9, 11 of newshj-5 and 43, 47, 49 of newshj-43), which only
  changes their brightness, so each piece keeps one model for all its frames;
- a lean-to wing on the tower's left with a dark roof, its top-left corner cut by a lit chamfer
  and a lit ramp down to the base at its front;
- a ribbed grey drum lying down the screen on the tower's right (columns 26-38), with a wider
  fluted collar at its top end and a narrower block and a hatch where it meets the base;
- a low step in front of the tower with a pipe running down it.

The jungle is a low heightfield painted from the sprite (dark shadow pixels low and dark, bright
leaves higher), skipped under the building. Built whole in block coordinates, then cut into the
pieces (newshj-5 top left, newshj-7 top right, newshj-43 bottom left, newshj-45 bottom right).

Run: blender --background --python assets/blender/enemies/assembly-newshj-43.py [-- --preview out.png]
(the preview is the whole block; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b126 as lib  # noqa: E402

NAME = "assembly-newshj-43"
ROOT = common.repo_root(__file__)
# Pieces and the pixel (column, row) of their top-left corner in the 48 x 56 block.
PIECES = [("newshj-5", 0, 0), ("newshj-7", 24, 0), ("newshj-43", 0, 28), ("newshj-45", 24, 28)]
W, H = 48, 56
G = lib.Grid(W, H)

BASE_TOP = 0.2  # top of the base slab
WING_TOP = 0.5
TOWER_TOP = 0.6
STEP_TOP = 0.34


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nshj43"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(33, metallic=0.0, roughness=0.95),  # 0 shadowed ground
        pal(193, metallic=0.0, roughness=0.9),  # 1 dark leaves
        pal(194, metallic=0.0, roughness=0.85),  # 2 leaves
        pal(196, metallic=0.0, roughness=0.8),  # 3 bright leaves
        pal(198, metallic=0.0, roughness=0.75),  # 4 brightest leaves
        pal(3, metallic=0.3, roughness=0.7),  # 5 dark grooves and recesses
        pal(5, metallic=0.45, roughness=0.55),  # 6 dark panels (wing roof, base front)
        pal(7, metallic=0.5, roughness=0.5),  # 7 sloped faces
        pal(9, metallic=0.55, roughness=0.45),  # 8 grey body
        pal(10, metallic=0.6, roughness=0.4),  # 9 light frame
        pal(12, metallic=0.65, roughness=0.35),  # 10 bright ribs and rims
        pal(197, metallic=0.1, roughness=0.2, emission_strength=2.5),  # 11 green windows
        pal(4, metallic=0.4, roughness=0.6),  # 12 shadowed sides
    ]
    (SHADOW, LEAF1, LEAF2, LEAF3, LEAF4, GROOVE, PANEL, SLOPE, BODY, FRAME, RIB, GLASS,
     SIDE) = range(len(mats))
    bm = bmesh.new()

    # ---- jungle ground ----
    pixels = lib.composite_pixels(ROOT, PIECES, W, H)

    def height_of(i):
        if 32 <= i <= 36:
            return 0.006 + (i - 32) * 0.004
        if i >= 192:
            return min(0.085, 0.022 + (i - 192) * 0.009)
        return 0.008  # outline and building pixels at the ground's edge

    def slot_of(i):
        if i >= 198:
            return LEAF4
        if i >= 196:
            return LEAF3
        if i >= 194:
            return LEAF2
        if i >= 192:
            return LEAF1
        return SHADOW

    lib.ground(bm, G, pixels, height_of, slot_of, cell=2, skip=lambda idx: all(0 <= i < 32 for i in idx))

    # ---- base slab (columns 5-38, rows 31-47): flat top, front sloping to the ground ----
    lib.frustum(bm, G, [(5, 31), (38, 31), (38.5, 46), (37.5, 47), (5, 47)], 0.0,
                [(5, 31), (38, 31), (38, 43.5), (37.2, 44.2), (5, 44.2)], BASE_TOP,
                [BODY, SIDE, PANEL, PANEL, RIB], BODY)
    # Bright rim along its top-left edge and the top front edge (rows 37 and 43).
    lib.box(bm, G, 5, 37, 14, 37.8, BASE_TOP, BASE_TOP + 0.02, RIB)
    lib.box(bm, G, 5, 43.2, 37.5, 44.2, BASE_TOP, BASE_TOP + 0.015, FRAME)
    # Two small posts on the left (columns 7 and 9, rows 39-42).
    for c in (7, 9):
        lib.box(bm, G, c, 39, c + 1, 42, BASE_TOP, BASE_TOP + 0.06, RIB)
    # Dark trench under the step (rows 37-39) and down column 14.
    lib.box(bm, G, 14, 36.5, 25, 38.8, BASE_TOP, BASE_TOP + 0.008, GROOVE)
    lib.box(bm, G, 14, 36.5, 15, 42, BASE_TOP, BASE_TOP + 0.008, GROOVE)
    # Raised box (columns 18-24, rows 40-43) with a lit top edge.
    lib.box(bm, G, 18, 40, 24, 43, BASE_TOP, BASE_TOP + 0.07, BODY)
    lib.box(bm, G, 18, 40, 24, 40.8, BASE_TOP + 0.07, BASE_TOP + 0.08, RIB)
    # Small box with a post at the drum's lower left (columns 24-31, rows 37-42).
    lib.box(bm, G, 24, 38, 31, 42.5, BASE_TOP, BASE_TOP + 0.05, SLOPE)
    lib.box(bm, G, 25.6, 38, 26.8, 42.5, BASE_TOP + 0.05, BASE_TOP + 0.1, FRAME)

    # ---- lean-to wing (columns 5-13): dark roof, lit chamfer top left, lit ramp in front ----
    lib.frustum(bm, G, [(5, 13.5), (13, 5.2), (13, 37), (5, 37)], BASE_TOP - 0.05,
                [(6.8, 17.5), (12.6, 11.5), (12.6, 27.5), (6.8, 32.2)], WING_TOP,
                [SLOPE, SIDE, SLOPE, SLOPE], PANEL)
    # Light rim along the roof's left edge (column 6) and its shaded fold below the chamfer.
    lib.frustum(bm, G, [(6.0, 17.5), (6.8, 17.5), (6.8, 32.2), (6.0, 32.7)], WING_TOP - 0.03,
                [(6.0, 17.5), (6.8, 17.5), (6.8, 32.2), (6.0, 32.7)], WING_TOP + 0.012, FRAME, FRAME)

    # ---- window tower (columns 13-25, rows 5-31) ----
    lib.frustum(bm, G, [(13, 5.0), (25, 5.0), (25, 31), (13, 31)], 0.0,
                [(13.2, 5.4), (24.8, 5.4), (24.8, 30.6), (13.2, 30.6)], TOWER_TOP - 0.08,
                [SIDE, SIDE, BODY, SLOPE], BODY)
    ft = TOWER_TOP - 0.08
    # Frame round and between the windows (left 13-16, right 23-25, bars at rows 5-7, 14-15, 22-23).
    lib.box(bm, G, 13.2, 5.4, 14.0, 30.6, ft, TOWER_TOP, SLOPE)
    lib.box(bm, G, 14.0, 5.4, 16.0, 30.6, ft, TOWER_TOP, FRAME)
    lib.box(bm, G, 23.0, 5.4, 24.8, 30.6, ft, TOWER_TOP, BODY)
    lib.box(bm, G, 16.0, 5.4, 23.0, 7.0, ft, TOWER_TOP, FRAME)
    lib.box(bm, G, 14.0, 5.4, 23.0, 6.2, TOWER_TOP, TOWER_TOP + 0.015, RIB)
    for r0, r1 in ((14.0, 15.0), (22.0, 23.0), (30.0, 30.6)):
        lib.box(bm, G, 16.0, r0, 23.0, r1, ft, TOWER_TOP, FRAME)
    # Recess shading at the windows' upper and left inner edges, then the glowing panes.
    for r0, r1 in ((7.0, 14.0), (15.0, 22.0), (23.0, 30.0)):
        lib.box(bm, G, 16.0, r0, 23.0, r0 + 0.6, ft - 0.01, ft + 0.03, GROOVE)
        lib.box(bm, G, 16.0, r0, 16.8, r1, ft - 0.01, ft + 0.03, GROOVE)
        lib.box(bm, G, 16.8, r0 + 0.6, 23.0, r1, ft - 0.01, ft + 0.035, GLASS)

    # ---- low step in front of the tower (columns 13-25, rows 31-37) with a pipe down it ----
    lib.frustum(bm, G, [(13, 30.5), (25, 30.5), (25, 36.8), (13, 36.8)], BASE_TOP - 0.02,
                [(13, 30.5), (25, 30.5), (25, 36.0), (13, 36.0)], STEP_TOP,
                [BODY, SIDE, SIDE, SLOPE], PANEL)
    lib.box(bm, G, 20.8, 30.6, 24.8, 31.4, STEP_TOP, STEP_TOP + 0.012, FRAME)
    lib.loft_y(bm, G.E(18.9, 0)[0], [(G.E(0, 30.6)[1], 1.2 / 12, 0.05, STEP_TOP),
                                      (G.E(0, 36.6)[1], 1.2 / 12, 0.05, STEP_TOP - 0.03),
                                      (G.E(0, 37.6)[1], 1.0 / 12, 0.04, STEP_TOP - 0.12)],
               sides=8, mat=SLOPE)

    # ---- ribbed drum lying down the screen (columns 25.5-37.5, rows 8-32) ----
    dx = G.E(31.6, 0)[0]
    yr = lambda r: G.E(0, r)[1]  # noqa: E731
    a, c, zc = 6.0 / 12, 0.36, 0.2
    lib.loft_y(bm, dx, [(yr(32.5), a, c, zc), (yr(14.0), a, c, zc)], sides=16, mat=BODY)
    # Rings: bright ribs and dark grooves at the rows the sprite shows them.
    for r in (15, 18, 20, 25, 29, 31):
        lib.ring_y(bm, dx, yr(r + 0.85), yr(r + 0.15), a + 0.02, c + 0.02, zc, sides=16, mat=RIB)
    for r in (14, 16, 19, 24, 26, 30):
        lib.ring_y(bm, dx, yr(r + 0.8), yr(r + 0.2), a + 0.008, c + 0.008, zc, sides=16, mat=GROOVE)
    # Wider fluted collar at its top end (rows 8-14), with lengthwise flutes on top.
    ca, cc = 6.8 / 12, 0.4
    lib.loft_y(bm, dx + 0.04, [(yr(14.2), ca, cc, zc), (yr(9.0), ca, cc, zc), (yr(8.0), ca - 0.06, cc - 0.06, zc)],
               sides=16, mat=BODY)
    for col in (27.5, 30.6, 34.6):
        x = G.E(col, 0)[0]
        off = (x - dx - 0.04) / ca
        z = zc + cc * (max(0.0, 1 - off * off)) ** 0.5
        lib.loft_y(bm, x, [(yr(13.8), 0.45 / 12, 0.03, z), (yr(8.6), 0.45 / 12, 0.03, z - 0.02)],
                   sides=6, mat=RIB)
    # Narrower block where it meets the base (columns 30.5-37.5, rows 32-44), a lit end at its foot.
    lib.loft_y(bm, G.E(34.0, 0)[0], [(yr(44.0), 3.5 / 12, 0.32, 0.12), (yr(32.0), 3.5 / 12, 0.32, 0.12)],
               sides=12, mat=BODY)
    lib.loft_y(bm, G.E(34.0, 0)[0], [(yr(44.3), 3.6 / 12, 0.33, 0.12), (yr(43.3), 3.6 / 12, 0.33, 0.12)],
               sides=12, mat=RIB)
    # Hatch beside it (columns 26-31, rows 32-37): a box with a dark inset.
    lib.box(bm, G, 25.5, 31.5, 31, 37.5, BASE_TOP - 0.02, 0.36, PANEL)
    lib.box(bm, G, 26.8, 32.8, 30.2, 36.6, 0.36, 0.365, GROOVE)

    bm.verts.ensure_lookup_table()
    for v in bm.verts:  # nothing below the ground
        if v.co.z < 0.0:
            v.co.z = 0.0
    return lib.to_object(NAME, bm, mats, coll)


def main():
    names = [n for n, _, _ in PIECES]
    sprite = lib.merged_sprite(ROOT, names)
    obj = build(sprite)
    layout = [(n, c0 + 12 - W // 2, r0 + 14 - H // 2) for n, c0, r0 in PIECES]
    pieces = common.split_assembly(obj, layout)
    for name in names:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        pixels = lib.composite_pixels(ROOT, PIECES, W, H)
        ref = lib.composite_png(pixels, sprite["colors"], Path(tempfile.mkdtemp()) / "block.png", 48, 56)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in names:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
