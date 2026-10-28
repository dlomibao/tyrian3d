"""Jungle bunker (newshj.shp 5, 7, 43 and 45, a 2x2 block): a 3D version of its sprites.

Seen in episode 2 (levels 2.2 and 2.24), where two of them stand side by side in the jungle. Four
2x2 sprites make one 48 x 56 px block: a grey building sitting in jungle undergrowth that fills
the rest of the tiles, with its drop shadow falling to the right and below. The building has

- a low base slab across the bottom (rows 32-47) whose front edge slopes down to the ground, with
  two small posts on its left, a raised box and a dark trench on top;
- a tall tower (columns 13-25) with three glowing green windows in a light frame; the windows
  light up one after another (frames 5, 9, 11 of newshj-5 and 43, 47, 49 of newshj-43), which only
  changes their brightness, so each piece keeps one model for all its frames: each pane takes its
  shade on each frame (palette_material frames=), and newshj-5 has a part per frame
  (common.frame_part) with the lit window's bright glint, the dimmer ones' faint glints and the dark
  bands that hide a dim window's top rows;
- a wing on the tower's left with vertical walls and a low hipped roof: a dark top, its top-left
  corner cut by a lit chamfer face and a lit face down its front;
- a ribbed grey drum lying down the screen on the tower's right (columns 26-38), a round tank about
  as tall as it is wide in a dark cradle on its shadowed right, with a fluted collar at its top end
  and an elbow and a hatch where it meets the base;
- a low step in front of the tower with a pipe running down it.

The jungle is a low heightfield painted from the sprite, one quad per pixel in its own shade (dark
shadow pixels low, bright leaves higher), skipped under the building but for its dark outline.
Built whole in block coordinates, then cut into the pieces (newshj-5 top left, newshj-7 top right, newshj-43 bottom left, newshj-45 bottom right).

Run: blender --background --python assets/blender/enemies/assembly-newshj-43.py [-- --preview out.png]
(the preview is the whole block; each piece also gets <piece>.png next to it).
[-- --frames out.png] renders every frame of newshj-5 and newshj-43 to <piece>.png beside out.png.
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
WING_TOP = 0.66  # the wing's roof ridge; its walls stand vertical up to WING_EAVE
WING_EAVE = 0.5
TOWER_TOP = 0.8  # top of the window frame (about 10 px, level with the drum)
PANE_TOP = TOWER_TOP - 0.1  # the windows sit about 1.2 px down in the frame
STEP_TOP = 0.4
# The ribbed drum: a round tank about 10 px tall lying on the ground, centre column 31.6.
DRUM_Z, DRUM_A, DRUM_C = 0.36, 6.0 / 12, 0.44
# The three window panes, top to bottom: (palette index on newshj-5's first frame, {frame: index}).
# The lit one moves down a window each frame (5, 9, 11 on newshj-5; the bottom pane's last rows are
# on newshj-43, frames 43, 47, 49): lit, half-lit, dark.
PANES = [(198, {9: 196, 11: 193}), (196, {9: 198}), (192, {9: 194, 11: 199, 47: 194, 49: 199})]


def jungle_ground(bm, pixels, height_of, slot_of):
    """The jungle as a heightfield with one flat-shaded quad per sprite pixel in that pixel's own
    shade (each corner's height is height_of averaged over the pixels round it). Building pixels
    (index 0-31) are left out except the ring touching the jungle, so the dark outline at the
    building's foot is covered. Flat shading keeps the pieces' cut edges from showing."""
    h, w = len(pixels), len(pixels[0])
    verts = {}

    def at(c, r):
        return pixels[r][c] if 0 <= r < h and 0 <= c < w else None

    def vert(c, r):
        if (c, r) not in verts:
            vals = [height_of(at(cc, rr)) for rr in (r - 1, r) for cc in (c - 1, c) if at(cc, rr) is not None]
            verts[(c, r)] = bm.verts.new((*G.E(c, r), sum(vals) / len(vals)))
        return verts[(c, r)]

    def is_ground(i):
        return i is not None and (i >= 32 or i < 0)

    for r in range(h):
        for c in range(w):
            i = pixels[r][c]
            if not is_ground(i) and not any(is_ground(at(c + dc, r + dr)) for dr in (-1, 0, 1) for dc in (-1, 0, 1)):
                continue
            f = bm.faces.new([vert(c, r + 1), vert(c + 1, r + 1), vert(c + 1, r), vert(c, r)])
            f.material_index = slot_of(i)
            f.smooth = False
    # Close the sides down to z = 0 round the block's border so the pad reads as solid ground.
    border = [((c, h), (c + 1, h)) for c in range(w)] + [((w, r), (w, r - 1)) for r in range(h, 0, -1)]
    border += [((c, 0), (c - 1, 0)) for c in range(w, 0, -1)] + [((0, r), (0, r + 1)) for r in range(h)]
    for a, b in border:
        if a not in verts or b not in verts:
            continue
        va, vb = verts[a], verts[b]
        da = bm.verts.new((va.co.x, va.co.y, 0.0))
        db = bm.verts.new((vb.co.x, vb.co.y, 0.0))
        f = bm.faces.new((da, db, vb, va))
        f.material_index = slot_of(-1)
        f.smooth = False


def band(bm, x, y0, y1, a, c, z, mat, sides=16):
    """A rib round the drum: an open band (no end caps, which would be hidden inside the drum)."""
    n, start = len(bm.faces), len(bm.verts)
    common.loft(bm, [(y0, a, c, z), (y1, a, c, z)], sides=sides, mat_index=mat, cap_start=False, cap_end=False)
    common.shift_x(bm, start, x)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.material_index = mat
        f.smooth = True


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
        pal(3, metallic=0.2, roughness=0.7),  # 5 dark grooves and recesses
        pal(5, metallic=0.25, roughness=0.6),  # 6 dark panels (wing roof, base front)
        pal(7, metallic=0.25, roughness=0.55),  # 7 sloped faces
        pal(9, metallic=0.25, roughness=0.5),  # 8 grey body
        pal(10, metallic=0.3, roughness=0.45),  # 9 light frame
        pal(12, metallic=0.3, roughness=0.4),  # 10 bright ribs and rims
        pal(197, metallic=0.1, roughness=0.2, emission_strength=2.5),  # 11 green windows
        pal(4, metallic=0.2, roughness=0.65),  # 12 shadowed sides
        pal(35, metallic=0.0, roughness=0.95),  # 13 lit shadow on the ground
        pal(192, metallic=0.0, roughness=0.9),  # 14 darkest leaves
        pal(195, metallic=0.0, roughness=0.85),  # 15 mid leaves
        pal(1, metallic=0.0, roughness=0.9),  # 16 black outline at the building's foot
    ]
    (SHADOW, LEAF1, LEAF2, LEAF3, LEAF4, GROOVE, PANEL, SLOPE, BODY, FRAME, RIB, GLASS,
     SIDE, SHADOW2, LEAF0, LEAF25, OUTLINE) = range(len(mats))
    bm = bmesh.new()

    # ---- jungle ground: one flat-shaded quad per sprite pixel, in that pixel's own shade ----
    pixels = lib.composite_pixels(ROOT, PIECES, W, H)
    leaf_slot = {192: LEAF0, 193: LEAF1, 194: LEAF2, 195: LEAF25, 196: LEAF3}
    grey_slot = {1: OUTLINE, 2: OUTLINE, 3: GROOVE, 4: SIDE, 5: PANEL, 6: PANEL, 7: SLOPE, 8: SLOPE, 9: BODY,
                 10: FRAME, 11: FRAME}

    def height_of(i):
        # A low relief (under half a pixel): steeper per-pixel facets glint grey in the light.
        if 32 <= i <= 36:
            return 0.004 + (i - 32) * 0.002
        if i >= 192:
            return min(0.04, 0.014 + (i - 192) * 0.004)
        return 0.006  # outline and building pixels at the ground's edge

    def slot_of(i):
        if i >= 197:
            return LEAF4
        if i >= 192:
            return leaf_slot[i]
        if i >= 34:
            return SHADOW2
        if i >= 32 or i < 0:
            return SHADOW
        return grey_slot.get(i, RIB)

    jungle_ground(bm, pixels, height_of, slot_of)

    # ---- base slab (columns 4.5-39.5, rows 31-47): flat top, front sloping to the ground, a dark
    # shadowed right side down to column 39.5 and a small ledge at its lower right (row 48) ----
    lib.frustum(bm, G, [(4.6, 31), (39.6, 31), (39.6, 47.4), (39.0, 48), (33.4, 48), (32.8, 47.2), (4.6, 47.2)],
                0.0,
                [(5, 31), (38, 31), (38, 43.5), (37.2, 44.2), (34, 44.2), (33.6, 44.2), (5, 44.2)], BASE_TOP,
                [BODY, GROOVE, GROOVE, PANEL, PANEL, PANEL, RIB], BODY)
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

    # ---- lean-to wing (columns 5-13): vertical walls up to the eave, then a low hipped roof with a
    # dark top, a lit chamfer face at its top left and a lit face down its front ----
    wing = [(4.6, 13.6), (13, 5.2), (13, 37), (4.6, 37)]
    lib.prism(bm, G, wing, BASE_TOP - 0.05, WING_EAVE, SIDE)
    lib.frustum(bm, G, wing, WING_EAVE,
                [(6.8, 17.5), (12.6, 11.5), (12.6, 27.5), (6.8, 32.2)], WING_TOP,
                [SLOPE, SIDE, SLOPE, SLOPE], PANEL)
    # Light rim along the roof's left edge (column 6) and its shaded fold below the chamfer.
    lib.frustum(bm, G, [(6.0, 17.5), (6.8, 17.5), (6.8, 32.2), (6.0, 32.7)], WING_TOP - 0.03,
                [(6.0, 17.5), (6.8, 17.5), (6.8, 32.2), (6.0, 32.7)], WING_TOP + 0.012, FRAME, FRAME)

    # ---- window tower (columns 13-25, rows 5-31) ----
    ft = TOWER_TOP - 0.16  # the body's top, under the frame
    lib.frustum(bm, G, [(13, 5.0), (25.8, 5.0), (25.8, 31), (13, 31)], 0.0,
                [(13.2, 5.4), (25.8, 5.4), (25.8, 30.6), (13.2, 30.6)], ft,
                [SIDE, SIDE, BODY, SLOPE], BODY)
    # Frame round and between the windows (left 13-16, right 23-25, bars at rows 5-7, 14-15, 22-23).
    lib.box(bm, G, 13.2, 5.4, 14.0, 30.6, ft, TOWER_TOP, SLOPE)
    lib.box(bm, G, 14.0, 5.4, 16.0, 30.6, ft, TOWER_TOP, FRAME)
    lib.box(bm, G, 23.0, 5.4, 25.8, 30.6, ft, TOWER_TOP, BODY)
    lib.box(bm, G, 16.0, 5.4, 23.0, 7.0, ft, TOWER_TOP, FRAME)
    lib.box(bm, G, 14.0, 5.4, 23.0, 6.2, TOWER_TOP, TOWER_TOP + 0.015, RIB)
    for r0, r1 in ((14.0, 15.0), (22.0, 23.0), (30.0, 30.6)):
        lib.box(bm, G, 16.0, r0, 23.0, r1, ft, TOWER_TOP, FRAME)
    # Recess shading at the windows' left inner edges, then the glowing panes set about 1.2 px down
    # in the frame, each in its shade on each frame (the dark bands over a dim window's top rows
    # are in window_frames).
    for (r0, r1, g0), (base, frames) in zip(((7.0, 14.0, 7.0), (15.0, 22.0, 17.0), (23.0, 30.0, 25.0)), PANES):
        lib.box(bm, G, 16.0, g0, 16.8, r1, ft, PANE_TOP + 0.004, GROOVE)
        mats.append(common.palette_material(sprite, base, f"{tag}-pane{len(mats)}", metallic=0.1, roughness=0.2,
                                            emission_strength=2.5, frames=frames))
        lib.box(bm, G, 16.8, r0, 23.0, r1, ft, PANE_TOP, len(mats) - 1)

    # ---- low step in front of the tower (columns 13-25, rows 31-37) with a pipe down it ----
    lib.frustum(bm, G, [(13, 30.5), (25, 30.5), (25, 36.8), (13, 36.8)], BASE_TOP - 0.02,
                [(13, 30.5), (25, 30.5), (25, 36.0), (13, 36.0)], STEP_TOP,
                [BODY, SIDE, SIDE, SLOPE], PANEL)
    lib.box(bm, G, 20.8, 30.6, 24.8, 31.4, STEP_TOP, STEP_TOP + 0.012, FRAME)
    lib.loft_y(bm, G.E(18.9, 0)[0], [(G.E(0, 30.6)[1], 1.2 / 12, 0.05, STEP_TOP),
                                      (G.E(0, 36.6)[1], 1.2 / 12, 0.05, STEP_TOP - 0.03),
                                      (G.E(0, 37.6)[1], 1.0 / 12, 0.04, STEP_TOP - 0.12)],
               sides=8, mat=SLOPE)

    # ---- ribbed drum lying down the screen (columns 25.5-37.5, rows 8-32): a round tank about
    # 10 px tall (as tall as it is wide), sitting in a dark cradle on its shadowed right ----
    dx = G.E(31.6, 0)[0]
    yr = lambda r: G.E(0, r)[1]  # noqa: E731
    a, c, zc = DRUM_A, DRUM_C, DRUM_Z
    lib.loft_y(bm, dx, [(yr(32.5), a, c, zc), (yr(14.0), a, c, zc)], sides=16, mat=BODY)
    # Rings: bright ribs and dark grooves at the rows the sprite shows them.
    for r in (15, 18, 20, 25, 29, 31):
        band(bm, dx, yr(r + 0.85), yr(r + 0.15), a + 0.02, c + 0.02, zc, RIB)
    for r in (14, 16, 19, 24, 26, 30):
        band(bm, dx, yr(r + 0.8), yr(r + 0.2), a + 0.008, c + 0.008, zc, GROOVE)
    # The cradle: a dark sloping skirt from under the drum's right side out to column 40.
    lib.frustum(bm, G, [(36.0, 14.0), (40.2, 14.0), (40.2, 32.0), (36.0, 32.0)], 0.0,
                [(36.0, 14.0), (37.9, 14.0), (37.9, 32.0), (36.0, 32.0)], 0.3, GROOVE, GROOVE)
    # Fluted collar at its top end (rows 8-14), a little taller than the drum, with lengthwise
    # flutes on top; a dark notch (columns 37-39.5) is cut in beside its shadowed right end.
    cx, ca, cc = G.E(31.3, 0)[0], 5.9 / 12, 0.48
    lib.loft_y(bm, cx, [(yr(14.2), ca, cc, zc), (yr(9.0), ca, cc, zc), (yr(8.0), ca - 0.06, cc - 0.06, zc)],
               sides=16, mat=BODY)
    for col in (27.5, 30.6, 34.4):
        x = G.E(col, 0)[0]
        off = (x - cx) / ca
        z = zc + cc * (max(0.0, 1 - off * off)) ** 0.5
        lib.loft_y(bm, x, [(yr(13.8), 0.45 / 12, 0.03, z), (yr(8.6), 0.45 / 12, 0.03, z - 0.02)],
                   sides=6, mat=RIB)
    lib.frustum(bm, G, [(36.6, 8.6), (39.8, 8.6), (39.8, 14.0), (36.6, 14.0)], 0.0,
                [(36.6, 8.8), (39.2, 8.8), (39.2, 13.8), (36.6, 13.8)], 0.42, [SIDE, GROOVE, SIDE, SIDE], SIDE)
    # The elbow where it turns down into the base (columns 30.5-37.5, rows 32-44): the drum's end
    # narrowing and dropping to the base front, a lit end at its foot.
    ex = G.E(34.0, 0)[0]
    lib.loft_y(bm, ex, [(yr(44.0), 3.5 / 12, 0.3, 0.2), (yr(38.0), 3.5 / 12, 0.36, 0.28),
                        (yr(32.0), 3.6 / 12, 0.42, 0.36)], sides=12, mat=BODY)
    lib.loft_y(bm, ex, [(yr(44.3), 3.6 / 12, 0.31, 0.2), (yr(43.3), 3.6 / 12, 0.31, 0.2)],
               sides=12, mat=RIB)
    # Hatch beside it (columns 26-31, rows 32-37): a box with a dark inset.
    lib.box(bm, G, 25.5, 31.5, 31, 37.5, BASE_TOP - 0.02, 0.36, PANEL)
    lib.box(bm, G, 26.8, 32.8, 30.2, 36.6, 0.36, 0.365, GROOVE)

    bm.verts.ensure_lookup_table()
    for v in bm.verts:  # nothing below the ground
        if v.co.z < 0.0:
            v.co.z = 0.0
    return lib.to_object(NAME, bm, mats, coll)


def window_frames(sprite):
    """newshj-5's parts per frame (block coordinates): the dark bands over the top rows of the dim
    windows, the left recess's top corner (dark, or lit beside a lit window) and the glints, a
    bright one near the lit window's top left and faint ones on the half-lit windows."""
    tag = "nshj43"
    pal = lambda i, e=0.0: common.palette_material(sprite, i, tag, metallic=0.1, roughness=0.2,  # noqa: E731
                                                   emission_strength=e) if e else \
        common.palette_material(sprite, i, tag, metallic=0.3, roughness=0.7)
    mats = [pal(3), pal(197, 2.5), pal(198, 2.5), pal(199, 3.0), pal(200, 3.0), pal(204, 3.5), pal(205, 4.0),
            pal(206, 4.0), pal(207, 4.0)]
    slot = {i: k for k, i in enumerate((3, 197, 198, 199, 200, 204, 205, 206, 207))}
    # (frame, [(c0, r0, c1, r1, palette index, layer)]): layer 0 sits on the pane, 1 on top of it.
    parts = {
        5: [(16.8, 15, 23, 16, 3, 0), (16.8, 23, 23, 25, 3, 0), (16, 15, 16.8, 17, 3, 0), (16, 23, 16.8, 25, 3, 0),
            (16.8, 7.8, 20, 11, 204, 0), (17.4, 8.3, 19.2, 10, 206, 1), (16.8, 16, 19.5, 18, 198, 0)],
        9: [(16.8, 7, 23, 8, 3, 0), (16.8, 23, 23, 25, 3, 0), (16, 23, 16.8, 25, 3, 0), (16, 15, 16.8, 17, 198, 0),
            (16.8, 8, 19, 10, 199, 0), (16.8, 15, 20, 18.5, 204, 0), (17.4, 15.6, 19.2, 17.8, 205, 1)],
        11: [(16.8, 7, 23, 9, 3, 0), (16.8, 15, 23, 16, 3, 0), (16, 15, 16.8, 17, 3, 0), (16, 23, 16.8, 25, 197, 0),
             (16.8, 16, 19.5, 18, 200, 0), (16.8, 23.4, 20, 26.5, 204, 0), (17.4, 24.2, 19.2, 26, 207, 1)],
    }
    objs = {}
    for frame, boxes in parts.items():
        coll = common.reset_collection(f"{NAME}-f{frame}")
        bm = bmesh.new()
        for c0, r0, c1, r1, i, layer in boxes:
            lib.box(bm, G, c0, r0, c1, r1, PANE_TOP - 0.05, PANE_TOP + 0.005 + 0.005 * layer, slot[i])
        objs[frame] = lib.to_object(f"newshj-5-frame{frame}", bm, mats, coll)
    return objs


def main():
    names = [n for n, _, _ in PIECES]
    sprite = lib.merged_sprite(ROOT, names)
    obj = build(sprite)
    layout = [(n, c0 + 12 - W // 2, r0 + 14 - H // 2) for n, c0, r0 in PIECES]
    pieces = common.split_assembly(obj, layout)
    exported = {name: [pieces[name]] for name in names}
    for frame, part in window_frames(sprite).items():
        cut = common.split_assembly(part, [layout[0]])["newshj-5"]
        cut.name = f"newshj-5-frame{frame}"
        exported["newshj-5"].append(common.frame_part(cut, [frame]))
    for name in names:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, exported[name], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        pixels = lib.composite_pixels(ROOT, PIECES, W, H)
        ref = lib.composite_png(pixels, sprite["colors"], Path(tempfile.mkdtemp()) / "block.png", 48, 56)
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in names:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
    if "--frames" in sys.argv:  # every frame of the animated pieces, one row each
        out = Path(sys.argv[sys.argv.index("--frames") + 1])
        for name in ("newshj-5", "newshj-43"):
            common.render_frame_previews(exported[name], str(out.parent / f"{name}.png"),
                                         common.load_sprite(ROOT, name), ROOT)


if __name__ == "__main__":
    main()
