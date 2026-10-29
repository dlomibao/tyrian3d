"""Horned boss head (newsh4.shp 81, 83, 85): a 3D version of its three-piece sprite.

Seen in one level of episode 4. Three 2x2 enemies side by side make the upper half of a boss
whose body and wings are assembly-newsh4-123, drawn 24 px lower: a pointed head with a grey face,
a bronze cap and a red crest, two red pincers hanging under it, and on each side a grey shoulder
cylinder with a red band, from which a long curved horn rises and a thin grey feeler curls in
towards the head. A grey arm joins each cylinder to a bronze block over the wing root. Each piece
has a single frame.

The head is built once in the frame shared with assembly-newsh4-123 (lib_b065) and cut into the
three pieces with common.split_assembly. Its parts are traced from the registered concept
(assets/blender/textures/assembly-newsh4-81/concept.png) and kept inside the sprite's outline, so
the texture baked from the concept (assets/blender/texture_bake.py) lands on the matching parts:
a faceted helm with a flat top panel carrying the glowing slit, a dark machinery block with a
raised spine, two red inverted-U pipes and a short pipe outside each; per side a red ribbed
collar, a hard grey housing round a red drum with a pointed blade under it, thin hard-edged
scythe horns and inner claws, a bronze shoulder plate, a grey arm housing over a dark lower frame,
and a chamfered bronze block with a slot in its lower edge, joined to the body by a dark coupling.
The concept is symmetric about column ~31 while the sprite's right side is drawn a little further
out, so each group of parts is mirrored about its own axis.

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

# Parts are traced from the registered concept (assets/blender/textures/assembly-newsh4-81/concept.png,
# 14 texels per sprite px, in this frame's columns and rows), kept inside the sprite's outline. The
# concept is symmetric about column ~31, the sprite about ~30-30.5 with its right side drawn a little
# further out, so each group of parts is built on the left and mirrored about its own axis.
PX = lib.PX
AX_CENTRE = 30.7  # helm, body, pipes
AX_POD = 30.75  # shoulder pods, horns, arms, shoulder plates
AX_CLAW = 30.5  # inner claws
AX_BLOCK = 31.0  # bronze armour blocks
POD_C = 11.0  # the left shoulder pod's centre column

# Left horn: (col, row, half width px), base in the pod's red collar, tip up and in. A thin blade.
HORN_PATH = [(11.8, 16.0, 2.25), (11.8, 13.0, 2.3), (11.9, 10.5, 2.3), (12.2, 8.5, 2.2), (12.9, 6.6, 2.0),
        (14.0, 5.0, 1.8), (15.5, 3.8, 1.45), (17.5, 2.9, 0.95), (19.8, 2.2, 0.0)]
# Left inner claw: from behind the shoulder plate, curling up and in towards the helm.
CLAW_PATH = [(15.7, 18.2, 1.35), (15.8, 16.0, 1.45), (16.3, 14.2, 1.45), (17.3, 12.6, 1.35), (19.0, 11.3, 1.15),
        (21.2, 10.6, 0.85), (23.7, 10.3, 0.0)]


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


def rect(c0, r0, c1, r1):
    return [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]


# The helm's cross-section: (across, up) as fractions of the half width and the height; a flat
# bottom, steep lower sides, sloping cheeks and a narrow flat top panel that carries the slit.
HELM_SECTION = [(-1.0, 0.0), (-0.95, 0.3), (-0.55, 0.78), (-0.22, 1.0), (0.22, 1.0), (0.55, 0.78),
                (0.95, 0.3), (1.0, 0.0)]
# (row, half width px, height units): a pointed cone traced from the concept, its tip held at the
# sprite's (row 9), widest at its rim (rows 15-16.4); its top panel slopes gently so the slit
# faces the game camera.
HELM = [(9.3, 0.0, 0.0), (10.0, 1.5, 0.2), (11.0, 2.5, 0.28), (12.0, 3.4, 0.33), (13.0, 4.2, 0.37),
        (14.0, 4.9, 0.4), (15.2, 5.8, 0.42), (15.5, 6.0, 0.41), (16.4, 6.0, 0.33)]
HELM_Z0 = -0.02


def helm_top(r):
    """Height of the helm's top panel at row r."""
    for (ra, _, ha), (rb, _, hb) in zip(HELM, HELM[1:]):
        if ra <= r <= rb:
            return HELM_Z0 + ha + (hb - ha) * (r - ra) / (rb - ra)
    return HELM_Z0


def helm(bm, face_mat, cap_mat, rim_mat, cap_row, rim_row):
    """The pointed helm: a faceted loft down the centre, flat-shaded; faces above cap_row are the
    cap, faces below rim_row the rim band."""
    rings = []
    for r, w, h in HELM:
        if w == 0:
            rings.append([bm.verts.new((lib.X(AX_CENTRE), lib.Y(r), HELM_Z0 + 0.08))])
            continue
        rings.append([bm.verts.new((lib.X(AX_CENTRE + u * w), lib.Y(r), HELM_Z0 + v * h)) for u, v in HELM_SECTION])
    m = len(HELM_SECTION)
    for (ra, r0), (rb, r1) in zip(zip([s[0] for s in HELM], rings), zip([s[0] for s in HELM[1:]], rings[1:])):
        mat = cap_mat if rb <= cap_row + 0.01 else (rim_mat if ra >= rim_row - 0.01 else face_mat)
        for i in range(m - 1):
            f = bm.faces.new((r0[0], r1[i], r1[i + 1])) if len(r0) == 1 else bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
            f.material_index = mat
            f.smooth = False
        if len(r0) > 1:
            f = bm.faces.new((r0[0], r0[m - 1], r1[m - 1], r1[0]))  # flat bottom
            f.material_index = face_mat
            f.smooth = False
    f = bm.faces.new(rings[-1])
    f.material_index = rim_mat
    f.smooth = False


def u_pipe(bm, c0, c1, r_top, r_end, z, w, h, mat):
    """An inverted-U pipe of constant diameter: legs at columns c0 and c1 running from r_end up to
    a round bend whose top is at row r_top."""
    rad = (c1 - c0) / 2
    cc, rc = (c0 + c1) / 2, r_top + rad
    path = [(c0, r_end, z, w, h)]
    for i in range(9):
        a = math.pi - math.pi * i / 8
        path.append((cc + rad * math.cos(a), rc - rad * math.sin(a), z, w, h))
    path.append((c1, r_end, z, w, h))
    lib.sweep(bm, path, sides=8, mat=mat)


def blade(bm, pts, z_base, z_tip, thick, mat):
    """A thin, hard-edged curved blade: a flat-shaded hexagonal sweep (ridges on top and bottom)
    along (col, row, half width px), rising from z_base to z_tip."""
    n = len(pts)
    path = []
    for i, (c, r, w) in enumerate(pts):
        t = i / (n - 1)
        path.append((c, r, z_base + (z_tip - z_base) * t ** 1.4, w, w * PX * thick))
    lib.sweep(bm, path, sides=6, mat=mat, smooth=False)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh4h"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(166, metallic=0.3, roughness=0.5),  # 0 horns
        pal(5, metallic=0.55, roughness=0.4),  # 1 grey collar rings, pod housings
        pal(7, metallic=0.55, roughness=0.4),  # 2 grey arm housings
        pal(8, metallic=0.55, roughness=0.4),  # 3 grey claws
        pal(70, metallic=0.35, roughness=0.4),  # 4 red pods and collars
        pal(24, metallic=0.25, roughness=0.55),  # 5 bronze plates and blocks
        pal(6, metallic=0.4, roughness=0.4),  # 6 grey helm
        pal(22, metallic=0.3, roughness=0.45),  # 7 bronze helm tip
        common.palette_material(sprite, 72, tag + "_slit", metallic=0.0, roughness=0.75, emission_strength=2.2),  # 8 red slit
        pal(2, metallic=0.35, roughness=0.6),  # 9 dark body block, notch floors
        pal(72, metallic=0.45, roughness=0.3),  # 10 red pipes
        pal(3, metallic=0.4, roughness=0.5),  # 11 neck, spine
        pal(4, metallic=0.5, roughness=0.45),  # 12 pod blades, helm rim
    ]
    HORN, COLLAR, ARM, CLAW, RED, BRONZE, FACE, CAP, SLIT, DARK, PIPE, SPINE, BLADE = range(13)
    bm = bmesh.new()

    # ---- shoulder pods, horns, shoulder plates and arms (left, mirrored about AX_POD) ----
    start = len(bm.verts)
    c = POD_C
    # Red ribbed collar at the horn's foot, a grey ring under it.
    lib.loft_y(bm, c, [(15.5, 1.8, 0.14, 0.21), (15.8, 2.3, 0.19, 0.21), (17.9, 2.3, 0.19, 0.21),
                       (18.2, 1.9, 0.15, 0.21)], sides=12, mat=RED, smooth=False)
    lib.loft_y(bm, c, [(18.0, 2.05, 0.16, 0.2), (19.7, 2.05, 0.16, 0.2)], sides=12, mat=COLLAR, smooth=False)
    # Hard grey housing with flat side plates, the red pod drum set in it.
    chamfer_prism(bm, [(8.0, 20.1), (8.8, 19.4), (13.7, 19.4), (14.3, 20.0), (14.3, 24.0), (13.7, 24.7),
                       (8.8, 24.7), (8.0, 24.0)], -0.02, 0.27, 0.5, COLLAR)
    lib.loft_y(bm, c + 0.4, [(19.8, 1.5, 0.15, 0.2), (20.1, 1.85, 0.2, 0.2), (24.1, 1.85, 0.2, 0.2),
                             (24.4, 1.5, 0.15, 0.2)], sides=12, mat=RED, smooth=False)
    # The pointed blade hanging under the pod.
    chamfer_prism(bm, [(9.4, 24.6), (13.9, 24.6), (13.9, 27.9), (12.6, 28.0), (9.6, 26.6)], -0.02, 0.22, 0.45, BLADE)
    # The horn: a thin scythe blade rising from the collar to its tip.
    blade(bm, HORN_PATH, 0.24, 0.5, 0.8, HORN)
    # Bronze shoulder plate running from the horn's foot down to the arm.
    chamfer_prism(bm, [(13.3, 15.3), (15.0, 15.3), (17.6, 17.8), (17.6, 19.7), (13.3, 19.7)], -0.02, 0.29, 0.5, BRONZE)
    # The grey arm housing from the pod to the armour block.
    chamfer_prism(bm, rect(13.6, 19.7, 18.8, 23.7), -0.02, 0.25, 0.45, ARM)
    # Dark lower frame under the arm, between the pod's blade and the armour block.
    chamfer_prism(bm, [(13.5, 23.4), (18.2, 23.4), (18.2, 27.4), (15.2, 27.4), (13.5, 26.2)], -0.04, 0.15, 0.4, SPINE)
    lib.mirror_since(bm, start, AX_POD)

    # ---- inner claws (mirrored about AX_CLAW) ----
    start = len(bm.verts)
    blade(bm, CLAW_PATH, 0.2, 0.32, 0.7, CLAW)
    lib.mirror_since(bm, start, AX_CLAW)

    # ---- bronze armour blocks over the wing roots, with the slot in their lower edge ----
    start = len(bm.verts)
    chamfer_prism(bm, [(19.6, 18.9), (22.2, 18.9), (23.1, 19.9), (23.1, 23.2), (17.7, 23.2), (17.7, 20.6),
                       (19.1, 19.2)], -0.04, 0.32, 0.6, BRONZE)
    chamfer_prism(bm, [(17.7, 23.2), (20.6, 23.2), (20.6, 27.0), (18.3, 27.0), (17.7, 26.3)], -0.04, 0.3, 0.5, BRONZE)
    chamfer_prism(bm, [(22.4, 23.2), (23.8, 23.2), (23.8, 25.7), (23.0, 26.7), (22.4, 26.7)], -0.04, 0.3, 0.45, BRONZE)
    lib.box(bm, 20.6, 23.2, 22.4, 26.7, -0.04, 0.1, mat=DARK)
    lib.mirror_since(bm, start, AX_BLOCK)

    # ---- helm, down the middle, with the glowing red slit along its top panel ----
    helm(bm, FACE, CAP, BLADE, 10.95, 15.45)
    rows = [10.9 + 0.4 * i for i in range(10)]
    lib.sweep(bm, [(AX_CENTRE, r, helm_top(r) + 0.022, 0.0 if i in (0, len(rows) - 1) else 0.75, 0.035)
                   for i, r in enumerate(rows)], sides=6, mat=SLIT, smooth=False)
    # Neck under the helm, then the dark machinery block with a raised spine down its middle and
    # the red pipes on it: an inverted U each side and a short pipe outside it (left, mirrored).
    chamfer_prism(bm, rect(28.2, 16.0, 33.2, 19.2), -0.04, 0.27, 0.45, SPINE)
    chamfer_prism(bm, [(26.6, 17.0), (34.8, 17.0), (35.9, 18.4), (35.9, 25.4), (35.2, 28.0), (26.2, 28.0),
                       (25.5, 25.4), (25.5, 18.4)], -0.04, 0.2, 0.5, DARK)
    chamfer_prism(bm, rect(30.05, 19.0, 31.35, 27.7), -0.04, 0.29, 0.35, SPINE)
    start = len(bm.verts)
    # Dark couplings joining the body to the armour blocks.
    chamfer_prism(bm, rect(23.3, 21.0, 25.8, 27.8), -0.04, 0.13, 0.35, SPINE)
    u_pipe(bm, 27.4, 29.3, 19.5, 26.4, 0.245, 0.5, 0.042, PIPE)
    lib.sweep(bm, [(26.2, 20.1, 0.24, 0.0, 0.0), (26.2, 20.4, 0.24, 0.45, 0.037), (26.2, 22.6, 0.24, 0.45, 0.037),
                   (26.5, 23.0, 0.24, 0.45, 0.037), (27.0, 23.1, 0.24, 0.45, 0.037)], sides=8, mat=PIPE)
    lib.mirror_since(bm, start, AX_CENTRE)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    lib.export_assembly(ROOT, obj, PIECES, sys.argv)


if __name__ == "__main__":
    main()
