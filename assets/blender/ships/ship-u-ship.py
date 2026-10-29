"""U-Ship (player ship, tyrian.shp#8 frame 271 and its banking frames 267-275): a 3D version of
its sprite.

A U-shaped band standing on edge, open end forward, with a bell-shaped brown pod hung in the
middle on two short struts. Seen from above (the level frame) the band is a thin line; the
banking frames show its grey and brown sides about 3 px deep, so it is a tall flat ribbon with
chamfered edges (a hard part, as in the concept): grey arms (columns 5 and 17, rows 7-19) with a
flat front end and dark raised joint bands at rows 14 and 19, turning brown at row 20 where it
curves round behind the pod in a smooth unbroken half ellipse down to row 24. Short boxy struts at row 16 join the
arms, at a round hub, to the pod. The pod is a polished brass bell, round in section, round at the
front (row 12) and flat at the back (row 20), with a framed dark glass window on the nose (rows
13-15), a raised pale trim strip down its left (column 10, rows 16-19) and a groove cut down its
right (column 12). Built around the middle of sprite column 11.

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

BAND_W = 0.8  # half thickness of the band, px (the 1 px line seen from above)
BAND_H = 2.0  # half height of the band, px (the banking frames show about 3 px of side)
CHAMFER = 0.3  # the band's edge chamfer, px
SHARP = math.radians(38)  # edges sharper than this stay crisp; the rest is smooth shaded

# The pod: (row, half width, half height), a bell round at the front, flat at the back.
POD = [(12.0, 0.0, 0.0), (12.2, 1.15, 0.95), (12.6, 1.85, 1.55), (13.3, 2.5, 2.1), (14.2, 2.9, 2.45),
       (15.2, 3.05, 2.6), (19.6, 3.05, 2.6), (19.9, 2.95, 2.5), (20.2, 2.55, 2.15)]
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
    g0, g1 = ang(1.45), ang(0.55)  # groove edges, x = +1.45 .. +0.55 (column 12)
    s0, s1 = ang(-0.45), ang(-1.5)  # trim strip edges, x = -0.45 .. -1.5 (column 10)
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

    rows = [12.2, 12.6, 13.3, 14.2, 14.7, 15.0, 15.2, 15.6, 15.9, 17.0, 18.5, 19.6, 19.9, 20.2]
    loops = []
    tip = bm.verts.new((X(AXIS), Y(12.0), 0.0))
    for r in rows:
        w, h = pod_dims(r)
        groove = 0.4 * ramp(r, 14.4, 14.7, 19.9, 20.0)
        strip = 0.28 * ramp(r, 15.3, 15.6, 19.6, 19.9)
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
    x0, x1, r0, r1 = -1.75, 0.4, 13.2, 15.15
    fw = 0.35  # frame width, px
    glass_z, frame_z = 0.1, 0.38

    def v(dx, r, dz):
        return bm.verts.new((X(AXIS + dx), Y(r), P(pod_top(dx, r) + dz)))

    nx_, nr_ = 6, 5
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


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    # Polished steel arms and struts, polished brass curve and pod, glossy dark glass. Each part takes
    # its mid-tone; the sprite's lit and shaded pixels come from the game's lights and outline.
    mats = [
        pal(9, metallic=0.75, roughness=0.3),  # 0 grey arm, front
        pal(10, metallic=0.75, roughness=0.3),  # 1 grey arm, between the joints
        pal(5, metallic=0.6, roughness=0.4),  # 2 dark joint bands
        pal(26, metallic=0.6, roughness=0.32),  # 3 brown curve
        pal(24, metallic=0.6, roughness=0.3),  # 5 brass pod
        pal(28, metallic=0.65, roughness=0.25),  # 6 pale trim strip on the pod
        pal(162, metallic=0.4, roughness=0.5),  # 7 the pod's groove
        pal(163, metallic=0.1, roughness=0.06),  # 8 window glass
        pal(22, metallic=0.6, roughness=0.32),  # 9 window frame
        pal(7, metallic=0.75, roughness=0.32),  # 10 struts
        pal(6, metallic=0.7, roughness=0.35),  # 11 strut hubs
    ]
    ARM, ARM2, JOINT, CURVE, POD_M, PALE, GROOVE, GLASS, FRAME, STRUT, HUB = range(11)
    bm = bmesh.new()
    sect = octagon(BAND_W, BAND_H)
    small = octagon(BAND_W - 0.15, BAND_H - 0.15, CHAMFER - 0.1)
    joint = octagon(BAND_W + 0.18, BAND_H + 0.18)
    joint_end = octagon(BAND_W + 0.04, BAND_H + 0.04, CHAMFER + 0.04)

    for c in (LEFT, RIGHT):
        # The arm: a flat front end at row 7.6 with a small chamfer, grey to the joint at row 19.
        band(bm, [(c, 7.6, small, 0), (c, 7.75, sect, 0), (c, 14.0, sect, 0), (c, 20.0, sect, 0)],
             [ARM, ARM, ARM2], cap_end=False)
        # Dark joint bands round it (rows 14 and 19), raised with chamfered ends.
        for r in (14.0, 19.0):
            band(bm, [(c, r, joint_end, 0), (c, r + 0.15, joint, 0), (c, r + 0.85, joint, 0),
                      (c, r + 1.0, joint_end, 0)], JOINT)
        # Strut from the arm to the pod (row 16): a boxy bar, and a round hub on the arm's inner side.
        s = 1 if c == LEFT else -1
        bar = octagon(0.5, 0.6, 0.15)
        x_arm, x_pod = c + s * 0.6, AXIS - s * 2.6
        pts = [(x_arm, 16.5, bar, 0), (x_pod, 16.5, bar, 0)]
        band(bm, pts if s == 1 else list(reversed(pts)), STRUT)
        hub = [(0.9 * math.cos(2 * math.pi * k / 10), 0.9 * math.sin(2 * math.pi * k / 10)) for k in range(10)]
        hub_edge = [(u * 0.8, v * 0.8) for u, v in hub]
        hx = [c + s * 0.6, c + s * 0.95, c + s * 1.1]
        rings = [(hx[0], 16.5, hub, 0), (hx[1], 16.5, hub, 0), (hx[2], 16.5, hub_edge, 0)]
        band(bm, rings if s == 1 else list(reversed(rings)), HUB)

    # The U's curve behind the pod, brown: a smooth half ellipse from one arm (row 20) round to the
    # other, its bottom along row 24, in one piece.
    cx, cy, rx, ry, p = AXIS, 20.0, 6.0, 4.5, 0.9
    n = 24
    rings = []
    for i in range(n + 1):
        t = math.pi * i / n
        ct, st = math.cos(t), math.sin(t)
        col = cx - rx * math.copysign(abs(ct) ** p, ct)
        row = cy + ry * abs(st) ** p
        rings.append((col, row, sect, 0))
    rings = [(LEFT, 19.9, sect, 0)] + rings + [(RIGHT, 19.9, sect, 0)]
    band(bm, rings, CURVE, cap_start=False, cap_end=False)

    build_pod(bm, POD_M, PALE, GROOVE)
    build_window(bm, GLASS, FRAME)

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
