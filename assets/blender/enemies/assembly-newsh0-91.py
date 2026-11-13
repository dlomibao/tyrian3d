"""Winged blue-steel crest (newsh0.shp frames 91 and 93, an assembly of two pieces): a 3D version
of its sprites.

Seen in episode 2 (level 2.12). Two 2x2 enemies side by side make one 48x28 px object, mirror
symmetric about pixel column 24 (newsh0-93's first column): a pale blue spine down the middle
flanked by two horns that curve up and out to points at the top, a grey blade standing beside
each horn, three grey feathers fanning out to each side (a swept blade with a bright leading
edge, a rounded bar, and a darker blade angled down), and the top of a mottled blue body across
the bottom, which runs off the bottom of the tile.

Built whole in assembly coordinates (left half, mirrored about column 24), then cut into the two
pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh0-91.py [-- --preview out.png]
(the preview is the whole object; each piece also gets <piece>.png next to it).
"""

import sys
import tempfile
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b025 as lib  # noqa: E402
from lib_b025 import common  # noqa: E402

NAME = "assembly-newsh0-91"
ROOT = common.repo_root(__file__)
PIECES = ["newsh0-91", "newsh0-93"]
G = lib.Grid(48, 28)  # assembly pixels: newsh0-91 is columns 0-23, newsh0-93 columns 24-47
AX = G.x(24)
CX0, CY0 = 126, -17  # the assembly's centre in screen pixels (between the two pieces)


P = 1 / 12  # one sprite pixel in units
BODY_FLOOR, BODY_TOP = 0.11, 0.26  # the body's slot floor and deck top


def _clamp01(t):
    return max(0.0, min(1.0, t))


def remap_z(bm, before, z0, fn):
    """Scale the height above z0 of everything added since lib.mark(bm) by fn(col, row)."""
    for v in bm.verts:
        if v not in before:
            v.co.z = z0 + (v.co.z - z0) * fn(G.col(v.co.x), G.row(v.co.y))


def build(colors):
    coll = common.reset_collection(NAME)
    m = lib.Mats("nsh0_91", colors)
    # Blue steel (horns, spine, body) and grey steel feathers: polished metal, each part one
    # mid-tone colour. The sprite's drawn light (bright streaks, lit edges, darker right half and
    # lower flanks, black outline) is left to the game's lights, metal sheen and outline pass.
    HORN = m(58, metallic=0.75, roughness=0.3)
    SPINE = m(57, metallic=0.75, roughness=0.3)
    BODY = m(55, metallic=0.7, roughness=0.32)
    BLADE = m(9, metallic=0.8, roughness=0.28)
    FEATHER = m(11, metallic=0.8, roughness=0.28)
    BAR = m(10, metallic=0.8, roughness=0.28)
    LOWER = m(7, metallic=0.75, roughness=0.3)
    SLOT = m(49, metallic=0.1, roughness=0.7)
    SLOT_LO = m(50, metallic=0.1, roughness=0.7)
    BACK = m(4, metallic=0.4, roughness=0.5)
    bm = bmesh.new()

    # ---- left half, mirrored below ----
    # Dark grey backing under the feathers, so the gaps between them read as recesses. Its outline
    # is the wing's sprite outline (the black edge pixels included); the game draws the dark edge.
    left = {7: 6, 8: 6, 9: 7, 10: 9, 11: 10, 12: 9, 13: 8, 14: 7, 15: 6, 16: 6, 17: 7, 18: 7, 19: 8, 20: 9,
            21: 10, 22: 11, 23: 12, 24: 13}
    rim = [(6.05, 7.05)] + [(left[r] + 0.05, r + 0.5) for r in range(8, 25)]
    rim += [(13.05, 24.95), (21, 24.95), (21, 8), (15.0, 8), (15.0, 7.05)]
    lib.plate(bm, G, rim, -0.12, -0.02, mat=BACK)
    lib.pillow(bm, G, [(8, 12.5), (13, 8.6), (15, 7.9), (18, 7.9), (21, 9), (21, 22), (14, 22.5), (12, 22), (8, 17)],
               -0.1, 0.02, round_px=0.8, mat=BACK)
    # Upper feather: a bevelled swept plate (rows 7-12), about 4 px high at the root and thinning to
    # 2 px at its tip; its lower edge rests on the barrel. Its bright top edge is sheen on the bevel.
    before = lib.mark(bm)
    lib.pillow(bm, G, [(5.9, 7.8), (14.6, 7.7), (15.3, 8.5), (17.2, 9.5), (18.2, 10.5), (19.0, 11.4), (19.3, 12.6), (16, 12.2),
                       (12, 12.1), (10.5, 11), (8.5, 10), (6.4, 8.8)], -0.04, 4.3 * P, round_px=0.8,
               round_h=0.35, mat=FEATHER)
    remap_z(bm, before, -0.04, lambda c, r: 0.5 + 0.5 * _clamp01((c - 6) / 9))
    # Middle feather: a round barrel lying across the sprite (rows 12.5-17), about 6 px high,
    # ending beside the horn.
    zc, hh = 0.27, 0.27
    lib.sweep(bm, G, [(6.1, 14.8, zc, 0.0, 0.0), (6.6, 14.8, zc, 1.5, 0.18), (7.6, 14.8, zc, 2.1, 0.25),
                      (10.0, 14.8, zc, 2.25, hh), (16.0, 14.75, zc, 2.25, hh), (17.8, 14.7, zc, 2.0, 0.24),
                      (18.6, 14.7, zc, 1.3, 0.16), (18.9, 14.7, zc, 0.0, 0.0)], sides=12, mat=BAR)
    # Grey claw standing beside the horn (columns 20-22, rows 0-8): a round tapering spike about
    # 3 px across and 4 px high, its point at the sprite's top row.
    lib.sweep(bm, G, [(21.0, -0.45, 0.13, 0.0, 0.0), (21.0, 0.3, 0.15, 0.85, 0.09), (21.0, 1.8, 0.18, 1.35, 0.14),
                      (21.1, 3.6, 0.19, 1.45, 0.16), (21.4, 5.3, 0.19, 1.35, 0.16), (21.9, 7.4, 0.18, 1.0, 0.13),
                      (22.2, 8.9, 0.14, 0.5, 0.07), (22.3, 9.6, 0.11, 0.0, 0.0)], sides=10, mat=BLADE)
    # Horn: one smooth round arm from its point at the top (column 18, row 1) curving down and in to
    # the band beside the spine (column 21), which runs straight off the bottom. As in the sprite it
    # is widest (about 3.3 px) in its head (rows 4-8), tapers to its point, pinches to about 2 px
    # where it meets the spine's slot (rows 12-16) and widens again to 3 px down the body; a little
    # taller than wide; about 6 px high in the head, its underside sunk into the deck, and it sinks
    # into the body toward the front edge (rows 22-28), where the sprite fades it into the body.
    horn = [(18.2, 0.5, 0.0), (18.05, 1.4, 0.75), (17.7, 2.8, 1.25), (17.45, 4.4, 1.7), (17.75, 5.8, 1.8),
            (18.55, 7.2, 1.8), (19.5, 8.6, 1.7), (20.3, 10.0, 1.3), (20.9, 11.5, 1.1), (21.1, 13.0, 0.95),
            (21.1, 15.0, 0.95), (21.1, 17.0, 1.2), (21.1, 19.5, 1.4), (21.1, 23.0, 1.5), (21.15, 28.0, 1.5)]

    def horn_z(r):
        return 0.22 + 0.11 * _clamp01((r - 0.5) / 15.5) - 0.12 * _clamp01((r - 22.0) / 6.0)

    path = [(c, r, horn_z(r), w, 1.55 * min(w, 1.45) * P if w else 0.0) for c, r, w in horn]
    lib.sweep(bm, G, path, sides=12, mat=HORN)

    lib.mirror_x(bm, AX, set())

    # Lower feathers: round grey logs tucked under the barrels, lying across the sprite and
    # tapering to a point at their outer tips (left rows 18-24, its lower point at column 13; the
    # right one is shorter, rows 18-23). Each is about 5 px across and stands about 4.5 px high,
    # its centre sunk to 1.5 px, so it reads as a rounded lobe; the sprite's three bands (lit upper
    # flank, darker lower flank) are the game's light on that curve. Stations are
    # (column, top row, bottom row) in pixel edges; the inner end butts into the horn or the
    # backing.
    zc, hh = 1.5 * P, 3.0 * P
    for stations in (
            [(7.6, 17.9, 18.4), (8.4, 17.9, 19.0), (9.9, 17.9, 20.4), (11.4, 17.9, 22.0), (12.9, 17.9, 23.4),
              (13.9, 17.9, 23.6), (15.0, 17.9, 22.3), (17.5, 17.9, 22.0), (20.4, 17.8, 22.0)],
            [(41.2, 17.9, 18.4), (40.4, 17.9, 19.2), (39.0, 17.9, 20.7), (37.5, 17.9, 22.2), (36.0, 17.9, 23.1),
              (34.8, 17.9, 22.6), (33.6, 17.9, 21.0), (32.8, 17.9, 20.2)]):
        path = []
        for i, (c, r0, r1) in enumerate(stations):
            end = i in (0, len(stations) - 1)
            w = 0.0 if i == 0 else (r1 - r0) / 2
            k = 1.0 if 0 < i < len(stations) - 1 else 0.55
            path.append((c - 0.5, (r0 + r1) / 2 - 0.5, zc, w, (hh if not end else 0.0) if i == 0 else hh * k))
        lib.sweep(bm, G, path, sides=12, mat=LOWER)

    # ---- centre ----
    # Top of the blue body across the bottom (rows 17-28), one piece across the middle: a base
    # with a rounded deck on it, the deck notched for the two dark slots (left row 24, right rows
    # 22-26, right of the horn) and for the dark groove the spine stands in; about 3 px high in all.
    # The lit lip below each slot is the deck's own edge catching the light.
    base = [(12.05, 28), (12.05, 25), (13.6, 24.2), (14, 22.2), (17.5, 21.6), (19.8, 18.5), (20.5, 17)]
    base = base + [(49 - c, r) for c, r in reversed(base)]
    deck = [(12.6, 28), (12.6, 25.1), (17.2, 25.1), (17.2, 23.8), (13.9, 23.8), (14, 22.2), (17.5, 21.6),
            (19.8, 18.5), (20.5, 17), (22.6, 17), (22.6, 24), (26.4, 24), (26.4, 17), (28.5, 17), (29.2, 18.5), (29.4, 21.7),
            (29.4, 24.6), (31.0, 24.6), (31.0, 26.6), (36.4, 26.6), (36.4, 28)]
    lib.plate(bm, G, base, -0.12, BODY_FLOOR, mat=BODY)
    lib.pillow(bm, G, deck, BODY_FLOOR - 0.01, BODY_TOP, round_px=0.5, round_h=0.7, mat=BODY)
    for floor in ([(13.7, 23.8), (17.2, 23.8), (17.2, 25.1), (12.8, 25.1)],
                  [(29.3, 18.6), (31.4, 21.7), (35, 22.3), (35.4, 24.2), (36.2, 25.0), (36.2, 26.6), (31.0, 26.6),
                   (31.0, 24.6), (29.4, 24.6)],
                  [(22.6, 17), (26.4, 17), (26.4, 24), (22.6, 24)]):
        lib.plate(bm, G, floor, 0.08, BODY_FLOOR + 0.003, mat=SLOT_LO)
    # The spine down the middle (column 24, rows 5-28): a thin rib 4 px high standing in the dark
    # groove (the deck is notched for it, columns 23-25, down to row 24), widening into the round
    # neck (5 px high) where the groove ends.
    lib.loft_y(bm, G, 24, [(4.2, 0.0, 0.0, 0.2), (5.0, 0.8, 0.13, 0.17), (8.0, 0.9, 0.16, 0.16),
                           (13.0, 1.0, 0.17, 0.17), (16.0, 1.1, 0.19, 0.19), (17.2, 0.75, 0.2, 0.2), (22.6, 0.75, 0.2, 0.2),
                           (24.6, 2.4, 0.22, 0.21), (28.0, 2.6, 0.22, 0.21)], sides=10, mat=SPINE)
    # Dark slots either side of the spine, between it and the horns (columns 22-26, rows 3-18).
    lib.plate(bm, G, [(22, 3.5), (27, 3.5), (27, 18.5), (22, 18.5)], -0.1, -0.03, mat=SLOT)
    return lib.to_object(NAME, bm, m.list, coll)


def composite_png(out):
    """Both pieces' sprites as one image, padded to the 24:28 shape render_preview wants for
    size 4 (48 x 56 px, the object in the middle)."""
    import numpy as np
    img = np.zeros((56, 48, 4), dtype=np.float32)
    for k, name in enumerate(PIECES):
        data = common.load_sprite(ROOT, name)
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    img[14 + r, 24 * k + c] = [*(ch / 255 for ch in data["colors"][str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 48, 56, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    data = {name: common.load_sprite(ROOT, name) for name in PIECES}
    obj = build(lib.merged_colors(ROOT, PIECES))
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in data[PIECES[0]]["assemblyLayout"]]
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data[name]["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = composite_png(Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=4, view_px=480)
        for name in PIECES:
            img = ROOT / "reference" / "models" / name / data[name]["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
