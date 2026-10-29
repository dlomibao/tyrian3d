"""Companion Ship Gerund (sidekick 21, two-player only; tyrian.shp#9 frame 49, 2x2): a 3D version of
its sprite as a small escort fighter.

Reading the sprite (pixel columns 3-21, rows 7-19, symmetric about column 12):
- a round blue-steel pod down the middle (columns 9-15, rows 7-17), its lit rim (pale 61-63
  pixels) round a dark grey canopy (rows 10-13) with a near-white glint (sheen, not geometry);
- a narrow grey dorsal ridge behind the canopy (column 12, rows 14-17, darkening backwards: it
  slopes down) between two short brown engines (columns 10-14, rows 16-18) whose dark nozzles
  end at row 19;
- either side a dark recessed neck (column 8 / 16) out to a bright gun rail (column 7 / 17: a
  bright streak down a narrow part is a cylinder) with purple housings at its front (rows 9-10)
  and back (row 15);
- outside the rail a short swept wing (columns 4-6 / 18-20, rows 11-15), lit on its outer half.
Hard where the sprite is hard (the wings and ridge are chamfered plates), round where it is
round (the pod, the canopy dome, the rails and the engines). No glowing parts.

Run: blender --background --python assets/blender/sidekicks/companion-ship-gerund.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402

import common  # noqa: E402

NAME = "sidekick-companion-ship-gerund"
MODEL = "sidekicks/companion-ship-gerund"
ROOT = common.repo_root(__file__)
W, H = 24, 28
AXIS = 12.5  # the middle of column 12 (pixel edges)
SHARP = math.radians(36)


def X(c):
    return (c - W / 2) / 12


def Y(r):
    return (H / 2 - r) / 12


def P(px):
    return px / 12


def V(bm, c, r, z):
    return bm.verts.new((X(c), Y(r), P(z)))


def bridge(bm, loops, mats, cap_start=True, cap_end=True, closed=True):
    """Quads between consecutive loops (equal length); mats: one per segment or one int."""
    if isinstance(mats, int):
        mats = [mats] * (len(loops) - 1)
    n = len(loops[0])
    for k, (a, b) in enumerate(zip(loops, loops[1:])):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mats[k]
    if cap_start:
        bm.faces.new(list(reversed(loops[0]))).material_index = mats[0]
    if cap_end:
        bm.faces.new(loops[-1]).material_index = mats[-1]


def sp(t, e):
    """Superellipse component: sign(t) * |t|^(2/e)."""
    return math.copysign(abs(t) ** (2 / e), t)


# The pod: (row, half width, height above the axis, depth below), px. An egg, a little boxy (the
# superellipse exponent), flatter underneath.
POD = [(7.05, 0.7, 0.5, 0.4), (7.4, 1.55, 1.15, 0.85), (8.0, 2.35, 1.75, 1.25), (8.8, 3.0, 2.25, 1.6),
       (9.8, 3.4, 2.55, 1.8), (11.5, 3.55, 2.75, 1.95), (13.5, 3.55, 2.65, 1.95), (15.0, 3.4, 2.35, 1.8),
       (16.3, 3.05, 1.95, 1.6), (17.3, 2.55, 1.5, 1.35)]
POD_E = 2.5


def pod_dims(row):
    for a, b in zip(POD, POD[1:]):
        if a[0] <= row <= b[0]:
            t = (row - a[0]) / (b[0] - a[0])
            return tuple(a[i] + (b[i] - a[i]) * t for i in range(1, 4))
    return 0.0, 0.0, 0.0


def pod_top(dx, row):
    w, h, _ = pod_dims(row)
    if w <= 0 or abs(dx) >= w:
        return 0.0
    return h * (1 - abs(dx / w) ** POD_E) ** (1 / POD_E)


def build_pod(bm, HULL):
    n = 24
    loops = []
    for r, w, ht, hb in POD:
        loop = []
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            c, s = math.cos(a), math.sin(a)
            loop.append(V(bm, AXIS + w * sp(c, POD_E), r, (ht if s > 0 else hb) * sp(s, POD_E)))
        loops.append(loop)
    tip = V(bm, AXIS, POD[0][0] - 0.12, 0.05)
    for i in range(n):
        bm.faces.new((tip, loops[0][(i + 1) % n], loops[0][i])).material_index = HULL
    bridge(bm, loops, HULL, cap_start=False)


def build_canopy(bm, GLASS, FRAME):
    """A dark glass dome on the pod's top (rows 9.8-13.7) in a raised grey frame."""
    cr, rx, ry = 11.75, 2.0, 1.9  # glass centre row and radii, px
    fw = 0.5  # frame width
    n = 20

    def at(dx, dr, dz):
        return V(bm, AXIS + dx, cr + dr, pod_top(dx, cr + dr) + dz)

    # Frame: outer foot, outer top, inner top, inner foot (under the glass edge).
    rings = []
    for k in range(n):
        a = 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        rings.append([at((rx + fw) * c, (ry + fw) * s, -0.3), at((rx + fw * 0.8) * c, (ry + fw * 0.8) * s, 0.35),
                      at((rx + 0.05) * c, (ry + 0.05) * s, 0.4), at(rx * c, ry * s, 0.0)])
    for k in range(n):
        a, b = rings[k], rings[(k + 1) % n]
        for i in range(3):
            bm.faces.new((a[i], a[i + 1], b[i + 1], b[i])).material_index = FRAME
    # Glass dome: rings from the frame's inner edge up to the crown.
    domes = []
    steps = 4
    for j in range(steps):
        t = j / steps  # 0 at the edge
        rr = math.cos(t * math.pi / 2)
        lift = 0.3 + 1.25 * math.sin(t * math.pi / 2)
        domes.append([at(rx * rr * math.cos(2 * math.pi * k / n), ry * rr * math.sin(2 * math.pi * k / n), lift)
                      for k in range(n)])
    crown = at(0, 0, 1.55)
    for l0, l1 in zip(domes, domes[1:]):
        for k in range(n):
            m = (k + 1) % n
            bm.faces.new((l0[k], l0[m], l1[m], l1[k])).material_index = GLASS
    for k in range(n):
        bm.faces.new((domes[-1][k], domes[-1][(k + 1) % n], crown)).material_index = GLASS


def plate(bm, outline, z0, z1, bevel, mat):
    """A plate from an outline of (col, row) px: flat bottom at z0, sides up to z1 - bevel, then a
    chamfer in by `bevel` to a flat top at z1. The outline must be convex."""
    cx = sum(p[0] for p in outline) / len(outline)
    cy = sum(p[1] for p in outline) / len(outline)

    def inset(p, d):
        dx, dy = p[0] - cx, p[1] - cy
        L = math.hypot(dx, dy) or 1
        return p[0] - dx / L * d, p[1] - dy / L * d
    bot = [V(bm, c, r, z0) for c, r in outline]
    mid = [V(bm, c, r, z1 - bevel) for c, r in outline]
    top = [V(bm, *inset(p, bevel * 1.2), z1) for p in outline]
    bridge(bm, [bot, mid, top], mat)


def tube(bm, col, z, sections, mat_per_seg, n=12, cap_start=True, cap_end=True):
    """A round part along Y at column `col`, height z: sections (row, radius)."""
    loops = [[V(bm, col + rad * math.cos(2 * math.pi * k / n), r, z + rad * math.sin(2 * math.pi * k / n))
              for k in range(n)] for r, rad in sections]
    bridge(bm, loops, mat_per_seg, cap_start=cap_start, cap_end=cap_end)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(59, metallic=0.6, roughness=0.35),  # 0 pod hull, blue steel
        pal(102, metallic=0.2, roughness=0.06),  # 1 canopy glass
        pal(61, metallic=0.8, roughness=0.28),  # 2 canopy frame, polished
        pal(58, metallic=0.6, roughness=0.38),  # 3 wings
        pal(53, metallic=0.55, roughness=0.45),  # 4 recessed neck
        pal(60, metallic=0.75, roughness=0.3),  # 5 gun rails
        pal(89, metallic=0.5, roughness=0.4),  # 6 front housings
        pal(91, metallic=0.5, roughness=0.4),  # 7 back caps
        pal(85, metallic=0.5, roughness=0.4),  # 8 muzzles
        pal(107, metallic=0.7, roughness=0.32),  # 9 dorsal ridge
        pal(164, metallic=0.5, roughness=0.42),  # 10 engines
        pal(163, metallic=0.5, roughness=0.45),  # 11 engine bands
        pal(162, metallic=0.45, roughness=0.5),  # 12 nozzles
        pal(161, metallic=0.1, roughness=0.8),  # 13 inside the nozzles
        pal(52, metallic=0.5, roughness=0.5),  # 14 wing underside trim / wing roots
    ]
    (HULL, GLASS, FRAME, WING, NECK, RAIL, FRONT, BACK, MUZZLE, RIDGE, ENG, BAND, NOZ, NOZ_IN,
     ROOT_M) = range(len(mats))

    bm = bmesh.new()
    build_pod(bm, HULL)
    build_canopy(bm, GLASS, FRAME)

    # The dorsal ridge behind the canopy: a chamfered wedge sloping down to the engines.
    def ridge_sec(r, top):
        return [V(bm, AXIS + dx, r, z) for dx, z in
                ((0.45, 0.0), (0.45, top - 0.3), (0.2, top), (-0.2, top), (-0.45, top - 0.3), (-0.45, 0.0))]
    bridge(bm, [ridge_sec(13.6, pod_top(0, 13.6) + 0.1), ridge_sec(14.4, pod_top(0, 14.4) + 0.75),
                ridge_sec(17.9, 1.1)], RIDGE)

    for s in (-1, 1):
        def m(c):
            return AXIS + s * (AXIS - c)  # mirror a left-side column to side s (-1 = right)
        def outline(pts):
            pts = [(m(c), r) for c, r in pts]
            return pts if s == 1 else list(reversed(pts))

        # Wing: a swept plate outside the rail, its root under the rail.
        plate(bm, outline([(7.6, 10.4), (7.6, 15.6), (4.3, 15.25), (3.3, 14.5), (3.3, 12.3), (4.5, 11.15)]),
              -0.9, 0.7, 0.5, WING)
        # A thin darker lip under the wing's edge (a second, slightly larger plate below).
        plate(bm, outline([(7.4, 10.8), (7.4, 15.4), (4.4, 15.0), (3.55, 14.3), (3.55, 12.5), (4.6, 11.5)]),
              -1.45, -0.85, 0.2, ROOT_M)
        # The recessed neck between rail and pod.
        plate(bm, outline([(10.2, 10.6), (10.2, 15.3), (7.5, 15.3), (7.5, 10.6)]), -1.3, -0.15, 0.25, NECK)
        # The gun rail: a bright cylinder with a purple housing and muzzle in front, a cap behind.
        col, z = m(7.5), 0.85
        tube(bm, col, z, [(9.8, 0.62), (15.3, 0.62)], RAIL)
        tube(bm, col, z, [(8.65, 0.55), (8.85, 0.82), (10.5, 0.82), (10.7, 0.6)], FRONT)
        tube(bm, col, z, [(8.0, 0.32), (8.7, 0.48)], MUZZLE, cap_start=False)
        tube(bm, col, z, [(8.02, 0.18), (8.25, 0.18)], NOZ_IN, cap_end=False)
        tube(bm, col, z, [(14.9, 0.72), (15.1, 0.8), (15.9, 0.75), (16.35, 0.45)], BACK)
        # A strut from the rail's housing down into the wing root.
        plate(bm, outline([(8.1, 12.2), (8.1, 13.8), (7.0, 13.8), (7.0, 12.2)]), -0.5, 0.6, 0.15, NECK)

        # Engine: a short brown cylinder with a band, a flared dark nozzle and a dark inside.
        ec, ez = m(11.15), -0.15
        tube(bm, ec, ez, [(14.8, 1.0), (16.2, 1.05), (16.2, 1.15), (16.6, 1.15), (16.6, 1.05), (17.9, 1.0)],
             [ENG, BAND, BAND, BAND, ENG], cap_start=False, cap_end=False)
        tube(bm, ec, ez, [(17.9, 1.0), (17.9, 0.85), (18.85, 1.05), (18.85, 0.8)], NOZ, cap_start=False,
             cap_end=False)
        tube(bm, ec, ez, [(18.85, 0.8), (18.35, 0.72)], NOZ_IN, cap_start=False)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > SHARP:
            e.smooth = False
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        frame = sprite["frames"][0]
        ref = ROOT / "reference" / "models" / NAME / frame["image"]
        common.render_preview([obj], out, ref, size=frame["size"])


if __name__ == "__main__":
    main()
