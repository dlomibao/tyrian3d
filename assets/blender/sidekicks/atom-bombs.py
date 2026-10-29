"""Atom Bombs sidekick (items 7, 11, 13, 14, 15: Atom Bombs, Buster Rocket, MicroBomb, 8-Way
MicroBomb, Post-It Mine; tyrian.shp#8 frames 165, 184, 203): a 3D version of its sprite.

A brass bomb launcher seen from above, 12 px wide on its 12x14 block. A shroud ring (the sprite's
lit rim, columns 1 and 10, rows 4-12) encloses a dark chamber floor. At its back sits a rounded
domed hull (rows 8-12, a soft highlight band, so round). Out of a dark socket at the hull's front
(row 7) a bomb lies along the pod, nose forward: a 4 px body (rows 5-6), a groove where it passes
the ring's front (row 4), and a bulbous 6 px warhead (rows 1-3) with a rounded nose, poking out
past the ring. The near-white streak down its middle and the bright spot on the dome are sheen on
polished metal, not geometry (tools/calibration/rubric.md); the black outline is the game's own.

The three frames differ only in the bomb: after each shot it recoils back into the launcher, 1 px
(frame 184) and 2 px (frame 203), then returns. One model covers them: three copies of the bomb,
each shown on its own frame (common.frame_part, DECISIONS.md D17); the launcher always shows.

Run: blender --background --python assets/blender/sidekicks/atom-bombs.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "atom-bombs"
SPRITE = "sidekick-atom-bombs"
P = 1 / 12  # one sprite pixel
RECOIL = {165: 0.0, 184: -1.0, 203: -2.0}  # px the bomb sits back on each frame

# Shroud ring: a superellipse in plan (px), centre y, outer and inner half-axes, exponent.
RING_CY = -1.5
RING_OUT = (5.0, 4.5)
RING_IN = (3.75, 3.25)
RING_POW = 3.4
# Its cross-section: (s across the band 0 = inner .. 1 = outer, z px), with the hard corners.
# The outer wall steps in at a machined ledge and ends in a wide chamfer that catches the light.
RING_PROFILE = ((0.0, -1.5), (0.8, -1.5), (0.96, -1.0), (1.0, 0.0), (0.9, 0.3), (0.9, 0.75),
                (0.72, 1.85), (0.22, 1.85), (0.0, 1.1))
RING_RISE = 0.6  # px the top of the ring rises along its long sides (the sprite's lit columns 1 and 10)
FLOOR_Z = (-1.6, -1.0)

# Domed hull at the back: plan ellipse centre/half-axes px, and its height.
HULL_C = (0.0, -3.45)
HULL_R = (4.35, 2.75)
HULL_Z = (-1.5, 4.2)

# The bomb: lathe profile (y px from its frame-165 position, radius px) along an axis at BOMB_Z.
BOMB_Z = 1.8
BOMB = (
    (6.0, 0.0), (6.0, 1.0),  # a flat fuse face on the nose (the sprite's blunt 4 px row 1)
    (5.75, 1.35), (5.3, 1.75), (4.7, 2.15), (4.0, 2.5), (3.3, 2.7),  # an ogive nose, 4 px wide
    (2.75, 2.45),  # then a boat-tail cone back in to the groove: no overhang, no mushroom
    (2.45, 1.85), (2.15, 1.85),  # the groove (narrow)
    (1.95, 2.05), (-0.6, 2.05), (-1.6, 2.05), (-2.0, 1.0),  # the body, running back into the socket
)
BOMB_HARD = {1, 7, 8, 9, 10}  # profile points where the surface creases
SOCKET = ((-0.2, 2.15), (-0.45, 2.75), (-1.6, 2.75), (-2.6, 2.45))  # (y px, radius px) collar


def superellipse(rx, ry, power, n, cy=0.0):
    pts = []
    for i in range(n):
        t = 2 * math.pi * (i + 0.5) / n
        c, s = math.cos(t), math.sin(t)
        pts.append((rx * math.copysign(abs(c) ** (2 / power), c), cy + ry * math.copysign(abs(s) ** (2 / power), s)))
    return pts


def sweep_ring(bm, mat, n=32):
    """The shroud: RING_PROFILE swept between the inner and outer superellipse, crisp at its corners."""
    outer = superellipse(*RING_OUT, RING_POW, n, RING_CY)
    inner = superellipse(*RING_IN, RING_POW, n, RING_CY)
    rings = []
    for (xo, yo), (xi, yi) in zip(outer, inner):
        t = 2 * math.pi * (len(rings) + 0.5) / n
        rise = RING_RISE * abs(math.cos(t)) ** 1.5
        rings.append([bm.verts.new(((xi + (xo - xi) * s) * P, (yi + (yo - yi) * s) * P,
                                    (z + rise * max(0.0, z + 1.0) / 2.85) * P))
                      for s, z in RING_PROFILE])
    m = len(RING_PROFILE)
    for a in range(n):
        r0, r1 = rings[a], rings[(a + 1) % n]
        for k in range(m):
            j = (k + 1) % m
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = mat
            f.smooth = True
    for a in range(n):  # every profile corner is a hard edge
        r0, r1 = rings[a], rings[(a + 1) % n]
        for k in range(m):
            bm.edges.get((r0[k], r1[k])).smooth = False


def floor(bm, mat):
    """The dark chamber floor inside the ring (seen in the gaps beside the bomb)."""
    pts = superellipse(RING_IN[0] + 0.4, RING_IN[1] + 0.4, RING_POW, 24, RING_CY)
    top = [bm.verts.new((x * P, y * P, FLOOR_Z[1] * P)) for x, y in pts]
    bot = [bm.verts.new((x * P, y * P, FLOOR_Z[0] * P)) for x, y in pts]
    bm.faces.new(top).material_index = mat
    bm.faces.new(list(reversed(bot))).material_index = mat
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((bot[i], bot[j], top[j], top[i])).material_index = mat


def hull(bm, mat, seam_mat, n=20):
    """The rear hull, a machined part: a straight skirt, a crisp seam step, a smooth dome (the
    sprite's soft highlight band) turned off flat on top round a shallow recessed port (hull colour: the sprite
    shows no dark spot there)."""
    z0, z1 = HULL_Z
    # (plan scale, z px); the skirt and seam step, then the dome up to the flat top
    steps = [(1.0, z0), (1.0, 0.2), (0.93, 0.55), (0.93, 0.9)]
    zd, f_top = 0.9, 0.3
    t_end = math.acos(f_top / 0.93)
    for k in range(1, 7):
        t = t_end * k / 6
        steps.append((0.93 * math.cos(t), zd + (z1 - zd) * math.sin(t) / math.sin(t_end)))
    top = len(steps) - 1  # the dome's crisp top edge
    # a small raised lip round the port, then the port recessed into it (dark, cut in)
    steps += [(0.24, z1 + 0.3), (0.17, z1 + 0.3), (0.15, z1 - 0.35), (0.0, z1 - 0.35)]
    mat_of = {1: seam_mat, 2: seam_mat, top + 2: seam_mat, top + 3: seam_mat}
    rings = []
    for f, z in steps:
        if f == 0.0:
            rings.append([bm.verts.new((HULL_C[0] * P, HULL_C[1] * P, z * P))])
            continue
        rings.append([bm.verts.new(((HULL_C[0] + HULL_R[0] * f * math.cos(2 * math.pi * (i + 0.5) / n)) * P,
                                    (HULL_C[1] + HULL_R[1] * f * math.sin(2 * math.pi * (i + 0.5) / n)) * P, z * P))
                      for i in range(n)])
    for b, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            face = (r0[i], r0[j], r1[0]) if len(r1) == 1 else (r0[i], r0[j], r1[j], r1[i])
            f = bm.faces.new(face)
            f.material_index = mat_of.get(b, mat)
            f.smooth = 3 <= b < top
    for k in (1, 2, 3, top, top + 1, top + 2, top + 3):  # crisp edges: skirt, seam step, flat top, port
        for i in range(n):
            bm.edges.get((rings[k][i], rings[k][(i + 1) % n])).smooth = False
    f = bm.faces.new(list(reversed(rings[0])))
    f.material_index = mat


def lathe_y(bm, profile, z, mat_of, hard=(), n=14, dy=0.0, caps=True):
    """Revolve (y px, radius px) points around a Y axis at height z px; radius 0 is a pole."""
    rings = []
    for y, r in profile:
        if r == 0:
            rings.append([bm.verts.new((0.0, (y + dy) * P, z * P))])
            continue
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * (i + 0.5) / n) * P, (y + dy) * P,
                                    (z + r * math.sin(2 * math.pi * (i + 0.5) / n)) * P)) for i in range(n)])
    for b, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            if len(r0) == 1:
                face = (r0[0], r1[i], r1[j])
            else:
                face = (r0[i], r1[i], r1[j], r0[j])
            f = bm.faces.new(face)
            f.material_index = mat_of(b)
            f.smooth = True
    for k in hard:
        if len(rings[k]) > 1:
            for i in range(n):
                bm.edges.get((rings[k][i], rings[k][(i + 1) % n])).smooth = False
    if caps and len(rings[-1]) > 1:
        f = bm.faces.new(rings[-1])
        f.material_index = mat_of(len(rings) - 2)
        f.smooth = False
        if len(rings[0]) > 1:
            f = bm.faces.new(list(reversed(rings[0])))
            f.material_index = mat_of(0)
            f.smooth = False


def finish(name, bm, mats, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, part, **kw: common.palette_material(sprite, i, f"{NAME}-{part}", **kw)  # noqa: E731
    mats = [
        pal(27, "ring", metallic=0.5, roughness=0.26),  # 0 shroud ring: polished brass
        pal(16, "floor", metallic=0.2, roughness=0.75),  # 1 chamber floor: dark, cut in
        pal(28, "hull", metallic=0.5, roughness=0.28),  # 2 domed hull
        pal(22, "seam", metallic=0.5, roughness=0.4),  # 3 hull seam step, socket collar, port
    ]
    bm = bmesh.new()
    sweep_ring(bm, 0)
    floor(bm, 1)
    hull(bm, 2, 3)
    lathe_y(bm, SOCKET, BOMB_Z, lambda b: 3, hard=(1, 2), n=16)
    launcher = finish(NAME, bm, mats, coll)

    bomb_mats = [
        pal(28, "warhead", metallic=0.5, roughness=0.25),  # 0 warhead
        pal(19, "groove", metallic=0.5, roughness=0.5),  # 1 groove
        pal(27, "body", metallic=0.5, roughness=0.28),  # 2 body
    ]
    groove = (8, 9)
    objs = [launcher]
    for frame, dy in RECOIL.items():
        bm = bmesh.new()
        lathe_y(bm, BOMB, BOMB_Z, lambda b: 0 if b < 8 else (1 if b in groove else 2),
                hard=BOMB_HARD, n=14, dy=dy)
        obj = finish(f"{NAME}-bomb-{frame}", bm, bomb_mats, coll)
        common.frame_part(obj, [frame])
        objs.append(obj)
    return objs


def main():
    root = common.repo_root(__file__)
    sprite = common.load_sprite(root, SPRITE)
    objs = build(sprite)
    common.export_sprite_model(root, objs, f"sidekicks/{NAME}", sprite["sprites"])
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        common.render_frame_previews(objs, str(out), sprite, root)


if __name__ == "__main__":
    main()
