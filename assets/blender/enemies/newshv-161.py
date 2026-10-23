"""Purple hooded gun emplacement (newshv.shp frame 161): a 3D version of its sprite.

Seen in episode 2 (level section 17). A ground structure facing down the screen: two purple
hood wings arch over the top, each with a red light strip along its outer edge, around a blue
teardrop crystal with a dark curled groove. Below sits a rounded grey gun housing with a raised
spine, a cyan glass dome and a red barrel pointing down, flanked by two purple claws.

Run: blender --background --python assets/blender/enemies/newshv-161.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b111 as lib  # noqa: E402

NAME = "newshv-161"
ROOT = common.repo_root(__file__)
P = 1 / 12
px, row = lib.px, lib.row


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(90, metallic=0.3, roughness=0.45),  # 0 purple hood
        pal(116, emission_strength=2.5),  # 1 red light strips
        pal(148, metallic=0.5, roughness=0.2),  # 2 blue crystal
        pal(145, metallic=0.3, roughness=0.5),  # 3 dark blue groove
        pal(155, metallic=0.5, roughness=0.15, emission_strength=1.5),  # 4 crystal highlight
        pal(106, metallic=0.6, roughness=0.35),  # 5 grey housing
        pal(108, metallic=0.6, roughness=0.3),  # 6 light grey spine
        pal(56, metallic=0.5, roughness=0.15),  # 7 cyan dome
        pal(115, metallic=0.5, roughness=0.4),  # 8 red barrel
        pal(120, emission_strength=4.0),  # 9 barrel glow
        pal(91, metallic=0.3, roughness=0.4),  # 10 light purple claws
        pal(100, metallic=0.4, roughness=0.6),  # 11 dark grey grooves
    ]
    HOOD, RED, BLUE, GROOVE, SHINE, GREY, SPINE, DOME, BARREL, GLOW, CLAW, DGREY = range(12)
    bm = bmesh.new()

    # Hood wings: a band swept from the leg (row 16) up and round to the top (row 4), higher on
    # the inner side (the sprite is lighter toward the middle).
    hood_path = [(2.0, 16.6), (1.9, 14.4), (3.3, 11.8), (4.4, 8.9), (6.2, 6.3), (8.3, 4.7), (10.1, 4.1)]
    hood_hw = [1.1, 2.0, 3.8, 3.8, 3.3, 2.6, 1.7]
    hood_h = [0.16, 0.22, 0.3, 0.34, 0.34, 0.32, 0.28]
    profile = [(1, 0), (1, 0.4), (0.6, 0.72), (0.0, 0.92), (-0.6, 1.0), (-1, 0.95), (-1, 0)]
    stripe = [(2.3, 12.0), (2.4, 10.0), (3.4, 8.0), (4.9, 6.2), (6.4, 4.9)]
    for side in (-1, 1):
        path = [(side * -px(c), row(r)) for c, r in hood_path]
        prof = profile if side < 0 else [(-u, v) for u, v in profile]
        lib.sweep_xy(bm, path, [w * P for w in hood_hw], hood_h, prof, mat_index=HOOD)
        lib.tube_path(bm, [(side * -px(c), row(r), 0.255) for c, r in stripe], 0.6 * P, sides=6,
                      mat_index=RED, flat=0.8)

    # Blue teardrop crystal between the wings (rows 4-15, columns 8-15).
    tear = [(15.9, 0.0, 0.0), (15.2, 2.4, 0.2), (14.2, 3.5, 0.26), (12.0, 4.1, 0.3), (10.0, 4.0, 0.32),
            (8.6, 2.9, 0.33), (7.2, 1.9, 0.33), (5.5, 1.1, 0.32), (4.0, 0.0, 0.0)]
    start = len(bm.verts)
    common.loft(bm, [(row(r), w * P, h, 0.0) for r, w, h in tear], sides=12, mat_index=BLUE)
    lib.clamp_z(bm, start)

    def tear_z(c, r, lift=0.012):
        # Height of the crystal's surface at sprite (c, r).
        rs = [t[0] for t in tear]
        for (r0, w0, h0), (r1, w1, h1) in zip(tear, tear[1:]):
            if r1 <= r <= r0:
                f = (r - r0) / (r1 - r0) if r1 != r0 else 0
                w, h = w0 + (w1 - w0) * f, h0 + (h1 - h0) * f
                break
        else:
            return 0.2
        x = abs(px(c)) / max(w * P, 1e-6)
        return h * math.sqrt(max(0.0, 1 - min(x, 1) ** 2)) + lift

    # The dark curled groove (the sprite's see-through pixels) and the bright facet beside it.
    groove = [(12.2, 7.4), (13.6, 8.6), (14.0, 10.4), (14.0, 12.6), (13.4, 14.0), (11.6, 14.3), (10.3, 13.4),
              (11.0, 11.8), (11.5, 10.6)]
    lib.tube_path(bm, [(px(c), row(r), tear_z(c, r)) for c, r in groove], 1.0 * P, sides=6,
                  mat_index=GROOVE, flat=0.5)
    shine = [(10.6, 8.2), (10.3, 9.4), (10.2, 11.0)]
    lib.tube_path(bm, [(px(c), row(r), tear_z(c, r)) for c, r in shine], [0.6 * P, 0.9 * P, 0.6 * P],
                  sides=6, mat_index=SHINE, flat=0.5)

    # Grey gun housing (rows 14-26, columns 3-20), flat on the ground.
    body = [(26.8, 5.0, 0.1), (25.8, 7.6, 0.22), (23.5, 8.6, 0.3), (20.0, 8.8, 0.32), (18.2, 7.8, 0.32),
            (16.6, 6.0, 0.29), (15.2, 4.6, 0.22), (14.2, 3.6, 0.12)]
    start = len(bm.verts)
    common.loft(bm, [(row(r), w * P, h, 0.0) for r, w, h in body], sides=14, mat_index=GREY)
    lib.clamp_z(bm, start)
    # Raised spine between two dark grooves (columns 10-13, rows 15-20).
    lib.box(bm, px(10.6), row(20.3), px(12.4), row(15.2), 0.2, 0.37, mat_index=SPINE)
    for c in (10.0, 13.0):
        lib.box(bm, px(c) - 0.4 * P, row(20.0), px(c) + 0.4 * P, row(15.6), 0.2, 0.335, mat_index=DGREY)

    # Cyan glass dome (rows 20-25, columns 7-16).
    lib.revolve(bm, [(4.8 * P, 0.2), (4.6 * P, 0.3), (3.6 * P, 0.38), (2.0 * P, 0.43), (0.0, 0.445)], 16,
                lambda k, i: DOME, cx=px(11.5), cy=row(22.6), sy=0.62)

    # Red barrel pointing down the screen (rows 24-27, columns 10-13), with a glowing breech.
    lib.tube_path(bm, [(0.0, row(23.8), 0.2), (0.0, row(25.0), 0.19), (0.0, row(26.6), 0.17), (0.0, row(27.7), 0.16)],
                  [1.5 * P, 2.0 * P, 1.8 * P, 1.1 * P], sides=10, mat_index=BARREL)
    lib.revolve(bm, [(1.3 * P, 0.25), (0.8 * P, 0.33), (0.0, 0.35)], 8, lambda k, i: GLOW, cx=0.0, cy=row(24.3))

    # Purple claws hugging the housing (rows 19-27, columns 1-4).
    claw = [(2.3, 18.8), (1.6, 20.5), (1.5, 23.0), (2.1, 25.4), (3.3, 26.6), (4.3, 27.3)]
    for side in (-1, 1):
        lib.tube_path(bm, [(side * -px(c), row(r), 0.1) for c, r in claw], [0.6 * P, 1.1 * P, 1.1 * P, 1.0 * P, 0.8 * P, 0.4 * P],
                      sides=8, mat_index=CLAW, flat=1.4)

    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


if __name__ == "__main__":
    lib.run(ROOT, NAME, build)
