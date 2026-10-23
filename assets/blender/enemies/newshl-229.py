"""Furnace walker (newshl.shp 229): a 3D version of its sprite.

Seen in episode 4 (level 45). A squat grey machine filling its 24x28 block: a broad ribbed steel
hood (rows 4-15) with a block on its back (rows 1-3), grooves down it splitting it into panels and
a grille of slats on its centre panel; under the hood's front edge a dark red mouth glows. Below
the hood a bar (row 16), a dark deck and a chute down the middle whose channel glows red to
yellow, ending in a rounded nozzle (rows 22-24); two forked legs come down either side (columns
1-4 and 20-23) to the bottom of the block, braced to the deck by struts at row 20.

The hood is a loft of flat-bottomed rounded sections (lib_b098.shell_loft); the grooves, slats and
the mouth follow its surface. It stands on z = 0 and rises to about 0.45.

Run: blender --background --python assets/blender/enemies/newshl-229.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b098 as lib  # noqa: E402

NAME = "newshl-229"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U
G = lib.Grid(24, 28)
POWER = 3.0
Z0 = 0.05  # the hood's underside
XC = G.x(11.5) + 0.5 * U  # the hood spans columns 1-23 (centre between columns 11 and 12, nudged right)

# Hood sections, back to front: (sprite row, half width px, height above Z0).
HOOD = [(4.3, 6.8, 0.27), (5.0, 7.7, 0.32), (6.0, 8.7, 0.36), (7.0, 9.7, 0.385), (8.0, 10.7, 0.395),
        (9.0, 11.6, 0.40), (11.0, 11.7, 0.40), (12.5, 11.7, 0.385), (13.8, 11.7, 0.35), (14.8, 11.6, 0.29),
        (15.6, 11.4, 0.21)]


def hood_at(rw):
    """Half width (units) and height of the hood at a sprite row, interpolated."""
    rw = max(HOOD[0][0], min(HOOD[-1][0], rw))
    for (r0, w0, h0), (r1, w1, h1) in zip(HOOD, HOOD[1:]):
        if r0 <= rw <= r1:
            t = (rw - r0) / (r1 - r0)
            return (w0 + (w1 - w0) * t) * U, h0 + (h1 - h0) * t
    return HOOD[-1][1] * U, HOOD[-1][2]


def hood_z(x, y):
    """Height of the hood's surface above (x, y)."""
    w, h = hood_at(G.row(y))
    k = min(1.0, abs(x - XC) / w)
    return Z0 + h * max(0.0, 1 - k ** POWER) ** (1 / POWER)


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = lib.Mats(NAME, sprite["colors"])
    steel = mats(11, metallic=0.7, roughness=0.35)
    block = mats(9, metallic=0.6, roughness=0.4)
    groove = mats(4, metallic=0.4, roughness=0.6)
    slat = mats(13, metallic=0.7, roughness=0.3)
    shadow = mats(6, metallic=0.5, roughness=0.5)
    deck = mats(2, metallic=0.3, roughness=0.7)
    leg = mats(10, metallic=0.7, roughness=0.35)
    leg_in = mats(8, metallic=0.6, roughness=0.4)
    bar = mats(12, metallic=0.7, roughness=0.3)
    maw = mats(113, metallic=0.2, roughness=0.6)
    ember = mats(116, metallic=0.1, roughness=0.5, emission_strength=1.5)
    glow_low = mats(114, metallic=0.1, roughness=0.5, emission_strength=1.5)
    glow_mid = mats(119, metallic=0.0, roughness=0.4, emission_strength=3.0)
    glow_hot = mats(121, metallic=0.0, roughness=0.4, emission_strength=3.5)
    glow_tip = mats(124, metallic=0.0, roughness=0.3, emission_strength=5.0)
    glow_side = mats(118, metallic=0.0, roughness=0.4, emission_strength=3.0)

    bm = bmesh.new()  # rounded parts, smooth shaded
    bf = bmesh.new()  # boxes, flat shaded

    # The block on the hood's back: rows 1.5-4.5, columns 7-17.
    lib.shell_loft(bm, [(G.y(1.0), 5.0 * U, 0.24, Z0, G.x(12)), (G.y(1.4), 5.5 * U, 0.29, Z0, G.x(12)),
                        (G.y(4.6), 5.6 * U, 0.30, Z0, G.x(12))], sides=12, power=4.0, mat_index=block)
    # The hood.
    lib.shell_loft(bm, [(G.y(r), w * U, h, Z0, XC) for r, w, h in HOOD], sides=20, power=POWER, mat_index=steel)

    def along(col, r0, r1, lift, n=8):
        x = G.x(col)
        pts = []
        for i in range(n + 1):
            rw = r0 + (r1 - r0) * i / n
            y = G.y(rw)
            pts.append((x, y, hood_z(x, y) + lift))
        return pts

    # Grooves between the panels (columns 6, 9, 15 and 18): dark ridges just proud of the hood.
    for col, r0, r1 in ((9, 4.8, 15.2), (15, 4.8, 15.2), (6, 6.0, 15.2), (18, 6.0, 15.2)):
        lib.tube(bm, [(p, 0.6 * U) for p in along(col, r0, r1, -0.004)], sides=6, mat_index=groove)
    # Bright ribs at the panel edges (columns 3, 7, 17 and 19).
    for col, r0, r1 in ((7, 5.5, 15.0), (17, 5.5, 15.0), (3, 7.5, 14.5), (19.5, 6.5, 14.5)):
        lib.tube(bm, [(p, 0.55 * U) for p in along(col, r0, r1, -0.006)], sides=6, mat_index=slat)

    # The grille on the centre panel (rows 9-12, columns 10-14): a dark plate with three slats.
    top = hood_z(G.x(12), G.y(10.5))
    lib.box(bf, G.x(9.6), G.y(12.5), G.x(14.4), G.y(8.5), top - 0.04, top + 0.012, mat_index=shadow)
    for col in (10, 12, 14):
        lib.box(bf, G.x(col) - 0.42 * U, G.y(12.4), G.x(col) + 0.42 * U, G.y(8.6), top - 0.03, top + 0.03,
                mat_index=slat)

    # The glowing mouth under the hood's front edge (rows 13-15, columns 9-15).
    lib.surface_cap(bm, (G.x(12), G.y(14.1)), (3.9 * U, 1.8 * U), hood_z,
                    [(1.15, -0.015, maw), (1.0, 0.016, maw), (0.8, 0.012, maw), (0.0, 0.008, maw)], sides=14)
    lib.surface_cap(bm, (G.x(12), G.y(14.8)), (1.9 * U, 0.9 * U), hood_z,
                    [(1.0, 0.016, ember), (0.6, 0.03, glow_mid), (0.0, 0.035, glow_mid)], sides=10)

    # The bar along the hood's front (row 16, columns 5-20).
    lib.cylinder_x(bm, G.x(4.6), G.x(20.4), G.y(16.1), 0.12, 0.8 * U, 0.8 * U, sides=8, mat_index=bar)
    # The cross beam (row 17, columns 2-22) and the dark deck behind the chute (rows 17-21).
    lib.box(bf, G.x(3.5), G.y(17.5), G.x(21.5), G.y(16.5), 0.0, 0.09, mat_index=shadow)
    lib.box(bf, G.x(4.5), G.y(21.5), G.x(19.5), G.y(16.6), 0.0, 0.045, mat_index=deck)

    # The chute: walls (columns 9-10 and 14-15) either side of the glowing channel (columns 11-13).
    lib.box(bf, G.x(8.6), G.y(22.0), G.x(10.45), G.y(17.4), 0.0, 0.13, mat_index=shadow)
    lib.box(bf, G.x(13.55), G.y(22.0), G.x(15.4), G.y(17.4), 0.0, 0.13, mat_index=shadow)
    cx0, cx1 = G.x(10.5), G.x(13.5)
    for r0, r1, mat in ((17.5, 19.5, glow_low), (19.5, 20.5, glow_mid), (20.5, 21.5, glow_hot)):
        lib.box(bf, cx0, G.y(r1), cx1, G.y(r0), 0.0, 0.085, mat_index=mat)
    # The nozzle the chute ends in (rows 22-24, columns 7-17), its mouth glowing yellow.
    lib.shell_loft(bm, [(G.y(21.4), 5.3 * U, 0.10, 0.0, G.x(12)), (G.y(23.0), 5.0 * U, 0.10, 0.0, G.x(12)),
                        (G.y(24.0), 4.1 * U, 0.085, 0.0, G.x(12)), (G.y(24.7), 2.6 * U, 0.05, 0.0, G.x(12))],
                   sides=10, power=2.5, mat_index=shadow)
    lib.box(bf, G.x(10.5), G.y(22.6), G.x(13.5), G.y(21.5), 0.06, 0.112, mat_index=glow_side)
    lib.box(bf, G.x(11.5), G.y(22.6), G.x(12.5), G.y(21.5), 0.06, 0.116, mat_index=glow_tip)

    # The legs: an outer limb from under the hood to the bottom of the block and an inner one that
    # joins it at row 24, braced to the deck by a strut at row 20.
    def p(col, rw, z):
        return (G.x(col), G.y(rw), z)

    for outer, inner, strut in (
            ([(2.4, 16.0, 0.17, 1.45), (2.3, 19.5, 0.16, 1.4), (2.1, 23.5, 0.11, 1.15), (1.8, 25.5, 0.075, 0.8),
              (2.0, 27.95, 0.06, 0.7)],
             [(4.3, 17.5, 0.15, 0.95), (4.2, 23.0, 0.1, 0.9), (2.6, 24.6, 0.075, 0.7)],
             [(2.5, 20.1), (7.6, 20.1)]),
            ([(21.6, 16.0, 0.17, 1.45), (21.7, 19.5, 0.16, 1.4), (22.1, 23.5, 0.11, 1.15), (22.5, 25.2, 0.075, 0.8),
              (22.1, 27.95, 0.06, 0.7)],
             [(19.9, 17.8, 0.15, 0.95), (20.0, 23.0, 0.1, 0.9), (21.6, 24.6, 0.075, 0.7)],
             [(21.5, 20.1), (16.6, 20.1)])):
        lib.tube(bm, [(p(c, r, z), w * U) for c, r, z, w in outer], sides=8, mat_index=leg)
        lib.tube(bm, [(p(c, r, z), w * U) for c, r, z, w in inner], sides=8, mat_index=leg_in)
        lib.tube(bm, [(p(c, r, 0.12), 0.75 * U) for c, r in strut], sides=6, mat_index=leg)
    return [common.mesh_object(NAME, bm, mats.list, coll, smooth=True),
            common.mesh_object(f"{NAME}_flat", bf, mats.list, coll)]


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objs = build(sprite)
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, objs, sprite)


if __name__ == "__main__":
    main()
