"""U-Ship (player ship, tyrian.shp#8 frame 271 and its banking frames 267-275): a 3D version of
its sprite, shaped after its concept (assets/blender/features/concepts/ship-u-ship.jpg).

Two steel gun arms (columns 4-6 and 16-18) stand either side of a brass pod, joined behind it by a
wide brass U-band. Each arm is a chamfered gun body (rows 9.4-19.8) with a thin barrel and muzzle
ring out front (rows 7-9.4), a lattice rail down its inner side, armour boxes down its outer side
and dark collars at rows 14 and 19. A round pivot hub on each arm's inner side carries two short
struts to the pod. The pod is a polished brass egg, round in section, with a small dark glass
window on its nose (row 14.5), a raised pale trim strip (column 10), a groove (column 12), a collar
and a short dark exhaust nozzle at its back (rows 20.1-21.4). The U-band is a broad flat brass
plate with chamfered edges and a dark grey inner rim, from the arms' ends round to row 25.7.
Built around the middle of sprite column 11.

Run: blender --background --python assets/blender/ships/ship-u-ship.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "enemies"))
import bmesh  # noqa: E402

import common  # noqa: E402
from lib_b002 import P, X, Y  # noqa: E402

NAME = "ship-u-ship"
MODEL = f"ships/{NAME}"
ROOT = common.repo_root(__file__)
AXIS = 11.5  # the middle of sprite column 11 (pixel edges)
LEFT, RIGHT = 5.5, 17.5  # the middle of columns 5 and 17

CHAMFER = 0.25  # default edge chamfer, px
SHARP = math.radians(38)  # edges sharper than this stay crisp; the rest is smooth shaded

# The pod: (row, half width, half height), an egg round at the front, tapering a little to the
# collar at its back (the concept's pod, rows 12.8-20.3 (its nose a little ahead of the concept's, to fill the sprite), columns 8.5-14.5).
POD = [(12.8, 0.0, 0.0), (12.95, 1.05, 0.9), (13.3, 1.75, 1.5), (13.9, 2.45, 2.05), (14.7, 2.95, 2.45),
       (16.0, 3.05, 2.6), (19.2, 2.95, 2.55), (19.9, 2.7, 2.3), (20.3, 2.2, 1.9)]
POD_W = 3.05


def octagon(hw, hh, c=CHAMFER):
    """A tall box section with chamfered corners, counter-clockwise from the right side."""
    return [(hw, -(hh - c)), (hw, hh - c), (hw - c, hh), (-(hw - c), hh), (-hw, hh - c), (-hw, -(hh - c)),
            (-(hw - c), -hh), (hw - c, -hh)]


def band(bm, rings, mats, cap_start=True, cap_end=True):
    """A band along a path in the sprite plane. rings: (col, row, profile, z) with profile a list of
    (across, up) px; mats: one material per segment (or one for all). Rings are square to the
    path."""
    pos = [(X(c), Y(r)) for c, r, *_ in rings]
    loops = []
    for i, (c, r, prof, z) in enumerate(rings):
        x, y = pos[i]
        (x0, y0), (x1, y1) = pos[max(i - 1, 0)], pos[min(i + 1, len(pos) - 1)]
        dx, dy = x1 - x0, y1 - y0
        d = math.hypot(dx, dy) or 1
        nx, ny = dy / d, -dx / d
        loops.append([bm.verts.new((x + nx * P(u), y + ny * P(u), P(z + v))) for u, v in prof])
    if isinstance(mats, int):
        mats = [mats] * (len(loops) - 1)
    n = len(loops[0])
    for k, (l0, l1) in enumerate(zip(loops, loops[1:])):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((l0[i], l0[j], l1[j], l1[i])).material_index = mats[k]
    if cap_start:
        bm.faces.new(list(reversed(loops[0]))).material_index = mats[0]
    if cap_end:
        bm.faces.new(loops[-1]).material_index = mats[-1]


def pod_dims(row):
    """The pod's half width and half height at a row (linear between the POD sections)."""
    for (r0, w0, h0), (r1, w1, h1) in zip(POD, POD[1:]):
        if r0 <= row <= r1:
            t = (row - r0) / (r1 - r0)
            return w0 + (w1 - w0) * t, h0 + (h1 - h0) * t
    return 0.0, 0.0


def pod_top(dx, row):
    """Height of the pod's upper surface above its axis at an offset dx from the axis (px)."""
    w, h = pod_dims(row)
    if w <= 0:
        return 0.0
    return h * math.sqrt(max(0.0, 1.0 - (dx / w) ** 2))


def build_pod(bm, POD_M, PALE, GROOVE):
    """The pod lofted ring by ring. Each ring is an ellipse sampled at fixed angles, with four extra
    vertices for the groove (cut in round column 12) and four for the trim strip (raised round
    column 10); their depth and rise ramp in and out along the pod."""
    def ang(x):
        return math.acos(max(-1.0, min(1.0, x / POD_W)))
    g0, g1 = ang(1.5), ang(0.9)  # groove edges, x = +1.5 .. +0.9 (column 12, the plate's right seam)
    s0, s1 = ang(-0.95), ang(-1.55)  # trim strip edges, x = -0.95 .. -1.55 (column 10)
    base = [2 * math.pi * k / 28 for k in range(28)]
    base = [a for a in base if not (g0 - 0.05 < a < g1 + 0.05 or s0 - 0.05 < a < s1 + 0.05)]
    # (angle, kind): kind 0 plain, 1 groove edge on surface, 2 groove floor, 3 strip top, 4 strip edge
    spec = [(a, 0) for a in base] + [(g0, 1), (g0 + 1e-4, 2), (g1 - 1e-4, 2), (g1, 1),
                                     (s0, 4), (s0 + 1e-4, 3), (s1 - 1e-4, 3), (s1, 4)]
    spec.sort()

    def ramp(r, a, b, c, d):
        if r <= a or r >= d:
            return 0.0
        if r < b:
            return (r - a) / (b - a)
        if r > c:
            return (d - r) / (d - c)
        return 1.0

    rows = [12.95, 13.3, 13.9, 14.7, 15.1, 15.4, 16.3, 16.6, 16.9, 18.0, 19.2, 19.5, 19.8, 19.9, 20.3]
    loops = []
    tip = bm.verts.new((X(AXIS), Y(POD[0][0]), 0.0))
    for r in rows:
        w, h = pod_dims(r)
        groove = 0.35 * ramp(r, 15.1, 15.4, 19.5, 19.8)
        strip = 0.25 * ramp(r, 16.3, 16.6, 19.5, 19.8)
        loop = []
        for a, kind in spec:
            px, pz = w * math.cos(a), h * math.sin(a)
            nx, nz = h * math.cos(a), w * math.sin(a)
            nl = math.hypot(nx, nz) or 1
            off = -groove if kind == 2 else strip if kind == 3 else 0.0
            px, pz = px + nx / nl * off, pz + nz / nl * off
            loop.append(bm.verts.new((X(AXIS) + P(px), Y(r), P(pz))))
        loops.append(loop)
    kinds = [k for _, k in spec]
    n = len(spec)

    def seg_mat(i):
        a, b = kinds[i], kinds[(i + 1) % n]
        if {a, b} <= {1, 2} and 2 in (a, b):
            return GROOVE
        if {a, b} <= {3, 4} and 3 in (a, b):
            return PALE
        return POD_M

    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((tip, loops[0][j], loops[0][i])).material_index = POD_M
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((l0[i], l0[j], l1[j], l1[i])).material_index = seg_mat(i)
    bm.faces.new(loops[-1]).material_index = POD_M  # the flat back


def build_window(bm, GLASS, FRAME):
    """A dark glass window set in a raised frame on the pod's nose (rows 13-15, a little left of
    the axis like the sprite's dark pixels): the glass follows the nose 0.1 px up, the frame stands
    0.35 px up round it."""
    x0, x1, r0, r1 = -0.8, 0.7, 14.45, 15.25
    fw = 0.35  # frame width, px
    glass_z, frame_z = 0.1, 0.38

    def v(dx, r, dz):
        return bm.verts.new((X(AXIS + dx), Y(r), P(pod_top(dx, r) + dz)))

    nx_, nr_ = 5, 3
    grid = [[v(x0 + (x1 - x0) * i / nx_, r0 + (r1 - r0) * j / nr_, glass_z) for i in range(nx_ + 1)]
            for j in range(nr_ + 1)]
    for j in range(nr_):
        for i in range(nx_):
            bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1])).material_index = GLASS

    # The frame's loop round the rectangle, sampled every ~0.45 px, clockwise seen from above.
    def edge(a, b, steps):
        return [(a[0] + (b[0] - a[0]) * t / steps, a[1] + (b[1] - a[1]) * t / steps) for t in range(steps)]
    corners = [(x0, r0), (x1, r0), (x1, r1), (x0, r1)]
    outer = [(x0 - fw, r0 - fw), (x1 + fw, r0 - fw), (x1 + fw, r1 + fw), (x0 - fw, r1 + fw)]
    steps = [nx_, nr_, nx_, nr_]
    inner_pts, outer_pts = [], []
    for k in range(4):
        inner_pts += edge(corners[k], corners[(k + 1) % 4], steps[k])
        outer_pts += edge(outer[k], outer[(k + 1) % 4], steps[k])
    rings = []
    for (ix, ir), (ox, orr) in zip(inner_pts, outer_pts):
        rings.append([v(ox, orr, -0.25), v(ox, orr, frame_z), v(ix, ir, frame_z), v(ix, ir, glass_z - 0.05)])
    m = len(rings)
    for k in range(m):
        a, b = rings[k], rings[(k + 1) % m]
        for i in range(3):
            bm.faces.new((a[i], b[i], b[i + 1], a[i + 1])).material_index = FRAME


def circle(r, n=12):
    """A round section of radius r px, counter-clockwise."""
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def box(bm, c0, c1, r0, r1, z0, z1, mat, ch=0.18):
    """A chamfered box between columns c0-c1, rows r0-r1 and heights z0-z1 (px)."""
    prof = octagon((c1 - c0) / 2, (z1 - z0) / 2, ch)
    zc, cc = (z0 + z1) / 2, (c0 + c1) / 2
    band(bm, [(cc, r0, prof, zc), (cc, r1, prof, zc)], mat)


def cyl_z(bm, cx, cy, r, z0, z1, mat, n=12):
    """An upright cylinder (a disc seen from above) at column cx, row cy."""
    rings = [[bm.verts.new((X(cx) + P(r * math.cos(2 * math.pi * k / n)),
                            Y(cy) + P(r * math.sin(2 * math.pi * k / n)), P(z))) for k in range(n)]
             for z in (z0, z1)]
    for k in range(n):
        j = (k + 1) % n
        bm.faces.new((rings[0][k], rings[0][j], rings[1][j], rings[1][k])).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bm.faces.new(rings[1]).material_index = mat


def u_path(rx, ry, top, n=24, p=0.9):
    """The U-band's centre line: a superellipse from the left arm (row `top`) round to the right."""
    out = []
    for i in range(n + 1):
        t = math.pi * i / n
        ct, st = math.cos(t), math.sin(t)
        out.append((AXIS - rx * math.copysign(abs(ct) ** p, ct), top + ry * abs(st) ** p))
    return out


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    # Polished steel guns and struts, polished brass band and pod, glossy dark glass. Each part takes
    # its mid-tone; the sprite's lit and shaded pixels come from the game's lights and outline.
    mats = [
        pal(9, metallic=0.55, roughness=0.4),  # 0 gun bodies
        pal(7, metallic=0.75, roughness=0.3),  # 1 barrels
        pal(5, metallic=0.65, roughness=0.35),  # 2 muzzles and dark collars
        pal(8, metallic=0.7, roughness=0.35),  # 3 outer armour boxes
        pal(4, metallic=0.6, roughness=0.45),  # 4 lattice rails
        pal(26, metallic=0.6, roughness=0.32),  # 5 brass U-band
        pal(6, metallic=0.65, roughness=0.4),  # 6 the band's inner rim, the pod's collar
        pal(25, metallic=0.6, roughness=0.3),  # 7 brass pod
        pal(28, metallic=0.65, roughness=0.25),  # 8 pale trim strip on the pod
        pal(162, metallic=0.4, roughness=0.5),  # 9 the pod's groove
        pal(163, metallic=0.1, roughness=0.06),  # 10 window glass
        pal(22, metallic=0.6, roughness=0.32),  # 11 window frame
        pal(7, metallic=0.75, roughness=0.32),  # 12 struts
        pal(8, metallic=0.7, roughness=0.3),  # 13 pivot hubs
        pal(5, metallic=0.7, roughness=0.3),  # 14 exhaust nozzle
        pal(3, metallic=0.3, roughness=0.6),  # 15 inside the nozzle
    ]
    (BODY, BARREL, DARK, SIDE, LATTICE, CURVE, RIM, POD_M, PALE, GROOVE, GLASS, FRAME, STRUT, HUB, NOZ,
     NOZ_IN) = range(16)
    bm = bmesh.new()

    for c in (LEFT, RIGHT):
        s = 1 if c == LEFT else -1  # +1 points inward (towards the pod)
        # The gun: a muzzle ring and thin barrel out front, then the chamfered body, tapering at its
        # front end (row 9.4) and running back into the U-band.
        band(bm, [(c, 7.1, circle(0.5), 0.5), (c, 7.55, circle(0.5), 0.5)], DARK)
        band(bm, [(c, 7.5, circle(0.36, 10), 0.5), (c, 9.8, circle(0.36, 10), 0.5)], BARREL)
        band(bm, [(c, 9.4, octagon(0.42, 0.85, 0.2), 0.3), (c, 10.4, octagon(0.72, 1.3), 0.0),
                  (c, 19.9, octagon(0.72, 1.3), 0.0)], BODY)
        # Dark collars round the body at rows 14 and 19.
        for r in (14.3, 19.0):
            box(bm, c - 0.86, c + 0.86, r, r + 0.6, -1.45, 1.45, DARK, 0.3)
        # Armour boxes down the outer side, a lattice rail down the inner side (front and back).
        o0, o1 = sorted((c - s * 1.35, c - s * 0.66))
        box(bm, o0, o1, 11.8, 14.3, -1.0, 0.6, SIDE, 0.15)
        box(bm, o0, o1, 14.9, 19.0, -1.0, 0.9, SIDE, 0.15)
        i0, i1 = sorted((c + s * 0.7, c + s * 1.2))
        box(bm, i0, i1, 8.6, 13.5, -0.4, 1.0, LATTICE, 0.1)
        box(bm, i0, i1, 17.6, 19.8, -0.6, 0.8, LATTICE, 0.1)
        # The pivot hub on the inner side and its two struts to the pod.
        cyl_z(bm, c + s * 1.2, 17.6, 0.62, -0.55, 0.85, HUB)
        a0, a1 = sorted((c + s * 1.5, AXIS - s * 2.75))
        box(bm, a0, a1, 16.4, 17.1, -0.3, 0.5, STRUT, 0.12)
        pts = [(c + s * 1.6, 18.0, octagon(0.3, 0.35, 0.1), -0.2), (AXIS - s * 2.7, 18.9, octagon(0.3, 0.35, 0.1), -0.2)]
        band(bm, pts if s == 1 else list(reversed(pts)), STRUT)

    # The U-band: a broad flat brass plate from one gun's back end round to the other, with a dark
    # grey rim along its inner edge.
    main = octagon(1.15, 0.9, 0.3)
    rings = [(LEFT, 19.2, main, -0.1)] + [(cc, r, main, -0.1) for cc, r in u_path(6.0, 5.2, 19.5)] + \
        [(RIGHT, 19.2, main, -0.1)]
    band(bm, rings, CURVE)
    lip = octagon(0.38, 0.55, 0.12)
    band(bm, [(cc, r, lip, -0.35) for cc, r in u_path(4.85, 4.05, 19.7)], RIM)

    build_pod(bm, POD_M, PALE, GROOVE)
    build_window(bm, GLASS, FRAME)
    # The collar and short exhaust nozzle behind the pod, dark inside.
    band(bm, [(AXIS, 20.1, circle(2.1, 16), 0), (AXIS, 20.45, circle(2.1, 16), 0),
              (AXIS, 20.45, circle(1.5, 16), 0), (AXIS, 21.35, circle(1.5, 16), 0),
              (AXIS, 21.37, circle(1.1, 16), 0)], [RIM, RIM, NOZ, NOZ], cap_end=False)
    band(bm, [(AXIS, 21.1, circle(1.1, 16), 0), (AXIS, 21.36, circle(1.1, 16), 0)], NOZ_IN, cap_start=False)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # Hard edges stay hard: mark every crease sharper than SHARP so smooth shading keeps it crisp.
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
        level = sprite["frames"][len(sprite["frames"]) // 2]
        ref = ROOT / "reference" / "models" / NAME / level["image"]
        common.render_preview([obj], out, ref, size=level["size"])


if __name__ == "__main__":
    main()
