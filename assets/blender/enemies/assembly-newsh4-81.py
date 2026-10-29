"""Horned boss head (newsh4.shp 81, 83, 85): a 3D version of its three-piece sprite.

Seen in one level of episode 4. Three 2x2 enemies side by side make the upper half of a boss
whose body and wings are assembly-newsh4-123, drawn 24 px lower: a pointed head with a grey face,
a bronze cap and a red crest, two red pincers hanging under it, and on each side a grey shoulder
cylinder with a red band, from which a long curved horn rises and a thin grey feeler curls in
towards the head. A grey arm joins each cylinder to a bronze block over the wing root. Each piece
has a single frame.

The head is built once in the frame shared with assembly-newsh4-123 (lib_b065) and cut into the
three pieces with common.split_assembly. The sprite's right side is drawn 1-2 px further out than
its left, so the side parts are placed per side from their own pixels; the head and pincers are
mirrored about the craft's axis.

Run: blender --background --python assets/blender/enemies/assembly-newsh4-81.py [-- --preview out.png]
(the preview is the whole head; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b065 as lib  # noqa: E402

NAME = "assembly-newsh4-81"
ROOT = common.repo_root(__file__)
PIECES = ["newsh4-81", "newsh4-83", "newsh4-85"]

# Per side: horn path (col, row, half width px), feeler path (col, row), shoulder cylinder column,
# grey arm (from col, to col), bronze block outline.
SIDES = [
    dict(horn=[(18.1, 2.6, 0.0), (17.0, 3.4, 1.1), (15.6, 4.4, 1.4), (14.3, 5.5, 1.5), (13.1, 6.5, 1.6),
               (12.3, 7.5, 1.6), (11.8, 8.6, 1.6), (11.6, 10.2, 1.6), (11.5, 13.0, 1.6)],
         feeler=[(22.6, 11.5), (21.2, 11.6), (19.2, 12.5), (17.6, 13.4), (16.4, 14.5), (15.6, 15.6), (15.4, 17.0),
                 (15.2, 18.6)],
         cyl=11.0, arm=(12.6, 18.6),
         block=[(19.0, 19.8), (22.2, 19.8), (23.2, 22.4), (23.2, 28.0), (19.8, 28.0), (17.0, 26.6), (17.0, 24.0),
                (18.6, 21.0)],
         plate=(12.8, 16.8, 16.4, 21.2)),
    dict(horn=[(43.8, 2.6, 0.0), (45.1, 3.4, 1.1), (46.5, 4.4, 1.4), (47.6, 5.5, 1.5), (48.6, 6.5, 1.6),
               (49.4, 7.5, 1.6), (49.9, 8.6, 1.6), (50.3, 10.2, 1.6), (50.5, 13.0, 1.6)],
         feeler=[(38.6, 11.5), (40.0, 11.6), (42.0, 12.5), (43.6, 13.4), (44.7, 14.5), (45.6, 15.6), (46.3, 16.8),
                 (46.6, 18.6)],
         cyl=50.5, arm=(42.8, 48.4),
         block=[(39.8, 19.8), (41.6, 19.8), (43.4, 21.2), (44.6, 24.2), (45.0, 26.4), (43.6, 28.0), (38.8, 28.0),
                (38.8, 21.6)],
         plate=(44.8, 17.8, 47.6, 20.6)),
]


PX = lib.PX


def chamfer_prism(bm, outline, z0, z1, ch_px, mat):
    """A hard plate from z0 to z1 with an outline of (col, row) edges (convex) whose top edge is
    chamfered: the top face is inset by ch_px and lowered sides meet it at 45 degrees."""
    n0 = len(bm.faces)
    k = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % k][1] - outline[(i + 1) % k][0] * outline[i][1] for i in range(k))
    sgn = 1 if area > 0 else -1

    def inward(i):
        (c0, r0), (c1, r1) = outline[i], outline[(i + 1) % k]
        dc, dr = c1 - c0, r1 - r0
        ln = math.hypot(dc, dr) or 1.0
        return (-dr / ln * sgn, dc / ln * sgn)

    inset = []
    for i in range(k):
        a, b = inward(i - 1), inward(i)
        dot = a[0] * b[0] + a[1] * b[1]
        s = ch_px / (1 + dot)
        inset.append((outline[i][0] + (a[0] + b[0]) * s, outline[i][1] + (a[1] + b[1]) * s))
    zc = z1 - ch_px * PX
    bot = [bm.verts.new((lib.X(c), lib.Y(r), z0)) for c, r in outline]
    mid = [bm.verts.new((lib.X(c), lib.Y(r), zc)) for c, r in outline]
    top = [bm.verts.new((lib.X(c), lib.Y(r), z1)) for c, r in inset]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((bot[i], bot[j], mid[j], mid[i]))
        bm.faces.new((mid[i], mid[j], top[j], top[i]))
    lib._faces_since(bm, n0, mat, False)


# The helm's cross-section: (across, up) as fractions of the half width and the height; a flat
# bottom, steep lower sides and a crisp ridge on the centre line.
HELM_SECTION = [(-1.0, 0.0), (-0.92, 0.35), (-0.45, 0.78), (0.0, 1.0), (0.45, 0.78), (0.92, 0.35), (1.0, 0.0)]
# (row, half width px, height units)
HELM = [(9.3, 0.0, 0.0), (10.1, 2.0, 0.17), (11.1, 3.1, 0.28), (12.2, 4.4, 0.38), (13.3, 5.5, 0.45),
        (15.6, 5.8, 0.47), (16.8, 4.6, 0.42), (17.9, 3.0, 0.34), (19.2, 2.6, 0.3)]
HELM_Z0 = -0.02


def helm_top(r):
    """Height of the helm's ridge at row r."""
    for (ra, _, ha), (rb, _, hb) in zip(HELM, HELM[1:]):
        if ra <= r <= rb:
            return HELM_Z0 + ha + (hb - ha) * (r - ra) / (rb - ra)
    return HELM_Z0


def helm(bm, face_mat, cap_mat, cap_row):
    """The pointed helm: a faceted loft down the centre, flat-shaded; faces above cap_row are the cap."""
    n0 = len(bm.faces)
    rings = []
    for r, w, h in HELM:
        if w == 0:
            rings.append([bm.verts.new((lib.X(lib.AXIS), lib.Y(r), HELM_Z0 + 0.04))])
            continue
        rings.append([bm.verts.new((lib.X(lib.AXIS + u * w), lib.Y(r), HELM_Z0 + v * h)) for u, v in HELM_SECTION])
    m = len(HELM_SECTION)
    for (ra, r0), (rb, r1) in zip(zip([s[0] for s in HELM], rings), zip([s[0] for s in HELM[1:]], rings[1:])):
        mat = cap_mat if rb <= cap_row + 0.01 else face_mat
        for i in range(m - 1):
            f = bm.faces.new((r0[0], r1[i], r1[i + 1])) if len(r0) == 1 else bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
            f.material_index = mat
            f.smooth = False
        if len(r0) > 1:
            f = bm.faces.new((r0[0], r0[m - 1], r1[m - 1], r1[0]))  # flat bottom
            f.material_index = face_mat
            f.smooth = False
    f = bm.faces.new(rings[-1])
    f.material_index = face_mat
    f.smooth = False


def u_pipe(bm, c0, c1, r_top, r_end, z, w, h, mat):
    """An inverted-U pipe of constant diameter: legs at column edges c0 and c1 running from r_end
    up to a round bend whose top is at row r_top."""
    rad = (c1 - c0) / 2
    cc, rc = (c0 + c1) / 2, r_top + rad
    path = [(c0, r_end, z, w, h)]
    for i in range(9):
        a = math.pi - math.pi * i / 8
        path.append((cc + rad * math.cos(a), rc - rad * math.sin(a), z, w, h))
    path.append((c1, r_end, z, w, h))
    lib.sweep(bm, path, sides=8, mat=mat)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh4h"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(166, metallic=0.25, roughness=0.5),  # 0 horns
        pal(167, metallic=0.3, roughness=0.45),  # 1 horn ridge
        pal(5, metallic=0.6, roughness=0.4),  # 2 grey collars
        pal(7, metallic=0.65, roughness=0.35),  # 3 grey cylinders and arms
        pal(8, metallic=0.7, roughness=0.3),  # 4 grey claws
        pal(70, metallic=0.35, roughness=0.4),  # 5 red bands
        pal(24, metallic=0.45, roughness=0.4),  # 6 bronze blocks
        pal(6, metallic=0.6, roughness=0.4),  # 7 grey helm
        pal(22, metallic=0.45, roughness=0.4),  # 8 bronze cap
        common.palette_material(sprite, 72, tag + "_slit", metallic=0.1, roughness=0.3, emission_strength=1.5),  # 9 red slit
        pal(2, metallic=0.3, roughness=0.7),  # 10 dark body block
        pal(72, metallic=0.4, roughness=0.35),  # 11 red pipes
    ]
    HORN, HRIDGE, COLLAR, CYL, CLAW, RED, BLOCK, FACE, CAP, SLIT, DARK, PIPE = range(12)
    bm = bmesh.new()

    for s in SIDES:
        # Curved horn rising from the shoulder pod's collar to a sharp tip, round in section, with
        # a lighter ridge along its top.
        n = len(s["horn"])
        hz = [0.22 + 0.3 * ((n - 1 - i) / (n - 1)) ** 1.4 for i in range(n)]
        lib.sweep(bm, [(c, r, hz[i], w, w * PX * 0.95) for i, (c, r, w) in enumerate(s["horn"])], sides=10, mat=HORN)
        lib.sweep(bm, [(c, r, hz[i] + w * PX * 0.72, w * 0.45, w * PX * 0.3)
                       for i, (c, r, w) in enumerate(s["horn"][1:-1], 1)], sides=6, mat=HRIDGE)
        # Grey collar at the horn's foot, then the upright shoulder cylinder with its red band.
        c = s["horn"][-1][0]
        lib.loft_y(bm, c, [(12.5, 1.5, 0.12, 0.2), (12.9, 1.95, 0.165, 0.2), (15.9, 1.95, 0.165, 0.2),
                           (16.3, 1.6, 0.13, 0.2)], sides=12, mat=COLLAR)
        lib.loft_y(bm, s["cyl"], [(15.8, 0.0, 0.0, 0.19), (16.2, 1.7, 0.14, 0.19), (17.0, 2.25, 0.19, 0.19),
                                  (26.8, 2.25, 0.19, 0.19), (27.6, 1.7, 0.14, 0.19), (28.0, 0.0, 0.0, 0.19)],
                   sides=14, mat=CYL)
        lib.loft_y(bm, s["cyl"], [(21.6, 2.45, 0.205, 0.19), (25.4, 2.45, 0.205, 0.19)], sides=14, mat=RED)
        # Bronze plate behind the pod, the round grey arm and the bronze armour block over the wing root.
        c0, r0, c1, r1 = s["plate"]
        chamfer_prism(bm, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], -0.02, 0.24, 0.6, BLOCK)
        a0, a1 = s["arm"]
        lib.sweep(bm, [(a0, 23.2, 0.17, 1.7, 0.14), (a1, 23.2, 0.17, 1.7, 0.14)], sides=12, mat=CYL)
        chamfer_prism(bm, s["block"], -0.04, 0.31, 0.9, BLOCK)
        # Thin grey claw curling in towards the helm: pointed at its inner tip, rising towards it.
        k = len(s["feeler"])
        path = []
        for i, (c, r) in enumerate(s["feeler"]):
            t = i / (k - 1)
            w = 0.0 if i == 0 else 0.35 + 0.8 * t
            path.append((c, r, 0.16 + 0.18 * (1 - t), w, w * PX * 0.75))
        lib.sweep(bm, path, sides=8, mat=CLAW)

    # ---- helm, down the middle, with the glowing red slit along its ridge ----
    helm(bm, FACE, CAP, 12.2)
    rows = [10.9 + 0.5 * i for i in range(12)]
    lib.sweep(bm, [(lib.AXIS, r, helm_top(r) + 0.012, 0.0 if i in (0, len(rows) - 1) else 1.1, 0.045)
                   for i, r in enumerate(rows)], sides=6, mat=SLIT)
    # Dark machinery block under the helm, split by a seam down the middle, with the two red
    # inverted-U pipes on it (left half built, then mirrored).
    lib.box(bm, 26.0, 18.6, 34.0, 27.8, -0.04, 0.2, mat=DARK)
    start = len(bm.verts)
    chamfer_prism(bm, [(24.6, 18.6), (29.7, 18.6), (29.7, 28.0), (24.6, 28.0)], -0.04, 0.29, 0.5, DARK)
    u_pipe(bm, 25.6, 28.1, 21.9, 28.0, 0.33, 0.78, 0.068, PIPE)
    lib.mirror_since(bm, start)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    lib.export_assembly(ROOT, obj, PIECES, sys.argv)


if __name__ == "__main__":
    main()
