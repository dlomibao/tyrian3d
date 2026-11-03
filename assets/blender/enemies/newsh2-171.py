"""Spinning brown pod (newsh2.shp frames 171, 190, 209, 228, 247, 266): a hard-surface armoured
machine that is its sprite in 3D (the treatment of the player ships, PR #84 / D50-D53).

Seen in episodes 1, 2 and 3 (enemy types 3 and 16). A brown heart-shaped pod, 12 x 14 px, spinning
about its long axis (the sprite's vertical). Six models, one per frame (D46), the same pod turned
to the frame's measured spin angle: newsh2-171 (frame 171), newsh2-171-f2 (190) ... -f6 (266).

The sprite is authoritative (D52, the user's rule):
- Plan outline: an envelope (half width and half thickness per row, pchip-interpolated, a p=2.05
  superellipse section) whose top view gives frame 171's mask including its outline ring; the
  armour plates all finish on that envelope, so the silhouette is the plates'. Spin angles per frame
  fitted to each frame's silhouette; with the row-7 thickness bump (THK) every frame's top view
  matches its sprite mask exactly (IoU 1.0, every row's width), measured both by ray casting
  (--measure) and by a 20x top ortho render of the exported GLBs.
- Spin cadence: 0 / 45 / 50 / 90 / 130 / 135 degrees, steps 45, 5, 40, 40, 5, 45. Only 45-50 degrees
  fits frames 190 / 209 (40 and below, 55 and above fall under IoU 0.95), so the silhouette rule
  forces the near-equal pairs 190 / 209 and 247 / 266; the sprite tells those apart only by its
  interior shading. Accepted (fix round 1).
- Features where the sprite draws them: a narrow raised spine down column 6 (rows 0.3-8.9) with a
  dark channel beside it (cols 5 and 7, rows 0-9; the blocks stop short of it) carrying louvre slats, the dark strap across it at row 2,
  the framed glowing lens at rows 5-6, chamfered armour tiles over the shoulders (rows 1-2 and 4,
  cols 2-4 / 8-10) with rivets and a dark recessed groove across them at row 3, side straps at
  row 5, armour blocks rows 6-8, a V plate wrapping the tail with a notch block in its V (rows
  9-10), a machined tip cap (rows 12-13), a keel rib along each edge (frame 228's bright centre
  line edge on) and, at the blunt end, a dished cap inside a segmented lip with radial vanes, bolts
  and a stepped hub.
- No see-through seams: the core hull is closed and sits just under the plates (CORE_EDGE) from the
  shoulders out, deep (CORE) only under the channel; cull_kept never culls it, and culls the rest
  densely enough to keep the plates' skirts.
- Colours: each part takes the median palette index of the sprite pixels it covers (16-17 shading
  and 29-31 sheen left out): spine 23, pads 22, channel/core 19, strap and lens frame 18, lens 27
  (emissive), side straps 21, blocks 20 (with the channel now beside them), tail V 20, notch 21, keel 24. Satin metal.
- The pod spins, so both faces are the same armour mirrored (z -> -z); no separate underside work.

Texture: no concept projection (its maps.json says "bake": "model", as the player ships, D50).
Cycles bakes a colour multiplier (ambient occlusion, edge lift) and a roughness/metalness map
(bake_maps, after usp_talon.bake_maps) once on the unturned pod to
assets/blender/textures/newsh2-171/bake/; every frame is a turned copy of that mesh, so all six
share the maps. Base Color = map x palette colour, so pal_<index>, fades and the hit flash apply;
the lens keeps its flat emissive palette colour. Each frame's GLB embeds the two maps (about
430 KB a frame). Each frame carries an outline shell
(common.outline_shell, D51). No engines, so no engine glows.

Coordinates while building: sprite px, x = column - 6.5 (the spin axis), y = row (0 the blunt top
end, 14 the tail point), z up. Moved to Blender at the end: X = x / 12, Y = (7 - y) / 12, Z = z / 12,
then turned about Y by the frame's spin angle and lifted to SPIN_Z (it spins just above the ground).

Run: blender --background --factory-startup --python assets/blender/enemies/newsh2-171.py
     [-- --preview out.png] [--no-bake] [--measure out.json]
(each extra model's preview goes next to out.png as <name>-fN.png).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from usp_talon import Part, pchip, hull  # noqa: E402

NAME = "newsh2-171"
ROOT = common.repo_root(__file__)
PX = 1 / 12
SPIN_Z = 0.38
# Spin per frame (degrees), from the silhouette fit (top-view IoU 1.0 / 0.95 / 0.98 /
# 1.0 / 0.98 / 0.95); positive turns the top face toward +X, as the current script.
ANGLES = [0.0, 45.0, 50.0, 90.0, 130.0, 135.0]
EXP = 2.05
TINT = (0.76, 0.86, 1.0)  # D53: lifts blue so the game's tone mapping keeps the sprite's khaki-brown

# --- envelope (blueprint) -------------------------------------------------------------------------
_EV = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11,
       11.5, 12, 12.5, 13, 13.5, 14]
_EW = [2.9, 3.6, 4.35, 4.879, 5.208, 5.402, 5.468, 5.499, 5.45, 5.3, 4.961, 4.6, 4.442, 4.3, 4.094,
       3.85, 3.554, 3.25, 2.994, 2.75, 2.5, 2.25, 2.0, 1.75, 1.51, 1.25, 0.929, 0.519, 0.0]
_ET = [1.2, 2.0, 2.577, 2.795, 2.908, 2.95, 2.945, 2.932, 2.91, 2.86, 2.729, 2.6, 2.511, 2.43, 2.35,
       2.262, 2.174, 2.1, 2.05, 2.008, 1.95, 1.845, 1.7, 1.517, 1.3, 1.067, 0.8, 0.478, 0.0]
HW = pchip(_EV, _EW)
HT = pchip(_EV, _ET)
# Per-row tweaks found by measurement (half thickness scale), so the edge-on frame keeps its widths.
THK = pchip([0, 5.4, 6.5, 7.4, 8.15, 8.6, 9.6, 10.5, 11.3, 14],
            [1.0, 1.0, 1.07, 1.13, 1.0, 1.0, 1.0, 1.1, 1.0, 1.0])
CORE = -0.45  # the core hull's inset under the centre plates (px): the deep dark channel
CORE_EDGE = -0.17  # its inset toward the edges, just under the plates' chamfers, so no seam sees through


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def core_g(v, a):
    """The core's inset at row v, section angle a: deep under the channel beside the spine, shallow
    (a floor right under every plate seam) from the shoulders out to the keels and at the tail."""
    A = HW(v)
    x = abs(P(v, a, 0.0)[0])
    t = max(smoothstep(1.75, 2.35, x), smoothstep(A - 1.2, A - 0.7, x))
    return CORE + (CORE_EDGE - CORE) * t


def semi(v, g):
    a = max(0.04, HW(v) + g)
    b = max(0.04, HT(v) * THK(v) + g)
    return a, b


def P(v, a, g=0.0):
    """Surface point at row v, section angle a (0 = +x keel, pi/2 = top centre), grown by g."""
    A, B = semi(v, g)
    c, s = math.cos(a), math.sin(a)
    e = 2.0 / EXP
    return (A * math.copysign(abs(c) ** e, c), v, B * math.copysign(abs(s) ** e, s))


def ang_x(v, x, g=0.0, top=True):
    """Section angle where the top (or bottom) face reaches x."""
    A, _ = semi(v, g)
    r = min(1.0, abs(x) / A) ** (EXP / 2)
    a = math.acos(r)
    if x < 0:
        a = math.pi - a
    return a if top else -a


def dPda(v, a, g=0.0):
    h = 1e-3
    p0, p1 = P(v, a - h, g), P(v, a + h, g)
    return math.dist(p0, p1) / (2 * h)


def normal(v, a, g=0.0):
    h = 1e-3
    pa = Vector(P(v, a + h, g)) - Vector(P(v, a - h, g))
    pv = Vector(P(v + h, a, g)) - Vector(P(v - h, a, g))
    n = pa.cross(pv).normalized()
    c = Vector(P(v, a, g))
    if n.dot(Vector((c.x, 0, c.z))) < 0:
        n = -n
    return n


# --- primitives -----------------------------------------------------------------------------------

def band(part, v0, v1, alo, ahi, mat, g=0.0, c=0.15, depth=-0.75, vstep=0.6, astep=0.23,
         chv=(True, True)):
    """An armour plate on the envelope: rows v0..v1, section angles alo(v)..ahi(v) (functions or
    numbers), its top at grow g, 45-degree chamfered borders c wide, skirts down to `depth`."""
    fl = alo if callable(alo) else (lambda v, k=alo: k)
    fh = ahi if callable(ahi) else (lambda v, k=ahi: k)
    c = min(c, (v1 - v0) / 3)
    vs = [v0]
    if chv[0]:
        vs.append(v0 + c)
    a, b = (v0 + c if chv[0] else v0), (v1 - c if chv[1] else v1)
    n = max(1, math.ceil((b - a) / vstep))
    vs += [a + (b - a) * i / n for i in range(1, n)]
    if chv[1]:
        vs.append(v1 - c)
    vs.append(v1)
    spans = [fh(v) - fl(v) for v in vs]
    na = max(1, math.ceil(max(spans) / astep))
    grid, lows = [], []
    for ri, v in enumerate(vs):
        lo, hi = fl(v), fh(v)
        span = hi - lo
        d0 = min(c / max(dPda(v, lo, g), 1e-3), 0.3 * span)
        d1 = min(c / max(dPda(v, hi, g), 1e-3), 0.3 * span)
        ia, ib = lo + d0, hi - d1
        cols = [(lo, True)] + [(ia + (ib - ia) * i / na, False) for i in range(na + 1)] + [(hi, True)]
        rb = (ri == 0 and chv[0]) or (ri == len(vs) - 1 and chv[1])
        row = []
        for k, (an, bc) in enumerate(cols):
            off = g - c if (rb or bc) else g
            row.append((part.v(P(v, an, off)), v, an))
        grid.append(row)
    nr, nc = len(grid), len(grid[0])
    for r in range(nr - 1):
        for k in range(nc - 1):
            q = (grid[r][k][0], grid[r][k + 1][0], grid[r + 1][k + 1][0], grid[r + 1][k][0])
            vm = (grid[r][k][1] + grid[r + 1][k][1]) / 2
            am = (grid[r][k][2] + grid[r][k + 1][2]) / 2
            part.f(q, mat, out=tuple(normal(vm, am, g)))

    def skirt(chain, inner):
        low = [part.v(P(v, an, depth)) for _, v, an in chain]
        for i in range(len(chain) - 1):
            ctr = (Vector(chain[i][0].co) + Vector(chain[i + 1][0].co)) / 2
            ref = (Vector(inner[i][0].co) + Vector(inner[i + 1][0].co)) / 2
            part.f((chain[i][0], chain[i + 1][0], low[i + 1], low[i]), mat, out=tuple(ctr - ref))
    skirt(grid[0], grid[1])
    skirt(grid[-1], grid[-2])
    skirt([grid[r][0] for r in range(nr)], [grid[r][1] for r in range(nr)])
    skirt([grid[r][-1] for r in range(nr)], [grid[r][-2] for r in range(nr)])


def surf_box(part, v, x, w, l, h, mat, g=CORE, ch=0.05, top=True, along=None):
    """A chamfered box standing on the surface (grow g) at row v, top-face x: w across, l along
    the row axis, h tall."""
    a = ang_x(v, x, g, top)
    o = Vector(P(v, a, g))
    n = normal(v, a, g)
    t = Vector(P(v, a + 1e-3, g)) - Vector(P(v, a - 1e-3, g))
    t.normalize()
    u = n.cross(t).normalized()  # along the length (about +-y)
    if along is not None:
        u = Vector(along).normalized()
        t = u.cross(n).normalized()
    pts = []
    for sx in (-1, 1):
        for su in (-1, 1):
            for z, cz in (((-0.3, 0.0), (h, 0.0)) if ch <= 0 else ((-0.3, 0.0), (h - ch, 0.0), (h, ch))):
                pts.append(o + t * sx * (w / 2 - cz) + u * su * (l / 2 - cz) + n * z)
    hull(part, [tuple(p) for p in pts], mat)


def rivet(part, v, a, mat, g=0.0, r=0.12, h=0.09):
    o = Vector(P(v, a, g))
    n = normal(v, a, g)
    t = Vector(P(v, a + 1e-3, g)) - Vector(P(v, a - 1e-3, g))
    t.normalize()
    u = n.cross(t)
    pts = []
    for k in range(6):
        th = 2 * math.pi * k / 6
        d = t * math.cos(th) + u * math.sin(th)
        pts.append(o + d * r - n * 0.05)
        pts.append(o + d * (r * 0.6) + n * h)
    hull(part, [tuple(p) for p in pts], mat)


def mirror_x(f):
    return (lambda v: math.pi - f(v)) if callable(f) else math.pi - f


def mirror_z(f):
    return (lambda v: -f(v)) if callable(f) else -f


def quad(part, v0, v1, lo, hi, mat, **kw):
    """A plate on the right-top quadrant and its three mirrors (left-top, right-bottom, left-bottom)."""
    band(part, v0, v1, lo, hi, mat, **kw)
    band(part, v0, v1, mirror_x(hi), mirror_x(lo), mat, **kw)
    band(part, v0, v1, mirror_z(hi), mirror_z(lo), mat, **kw)
    band(part, v0, v1, mirror_z(mirror_x(lo)), mirror_z(mirror_x(hi)), mat, **kw)


def faces2(part, v0, v1, lo, hi, mat, **kw):
    """A plate across the top centre and its mirror on the bottom face."""
    band(part, v0, v1, lo, hi, mat, **kw)
    band(part, v0, v1, mirror_z(hi), mirror_z(lo), mat, **kw)


# --- the pod --------------------------------------------------------------------------------------

M_CORE, M_PAD, M_SPINE, M_STRAP, M_FRAME, M_LENS, M_SSTRAP, M_BLOCK, M_TAIL, M_NOTCH, M_KEEL, M_RIVET, M_NOSE = range(13)
PAL_OF = {M_CORE: 19, M_PAD: 22, M_SPINE: 23, M_STRAP: 18, M_FRAME: 18, M_LENS: 27, M_SSTRAP: 21,
          M_BLOCK: 20, M_TAIL: 20, M_NOTCH: 21, M_KEEL: 24, M_RIVET: 24, M_NOSE: 20}
KEEL = math.radians(10)  # keel rib half angle
GAP = 0.035  # seam between plates (radians on the section)


def build_core(part):
    vs = [0.25 + i * 0.7 for i in range(30) if 0.25 + i * 0.7 < 13.5] + [13.6]
    N = 24
    rings = []
    for v in vs:
        ring = []
        for k in range(N):
            a = 2 * math.pi * k / N
            ring.append(part.v(P(v, a, max(core_g(v, a), -0.4 * HW(v)))))
        rings.append(ring)
    tip = part.v((0.0, 13.95, 0.0))
    for r0, r1, v in zip(rings, rings[1:], vs):
        for k in range(N):
            j = (k + 1) % N
            part.f((r0[k], r0[j], r1[j], r1[k]), M_CORE, away=(0.0, v, 0.0))
    for k in range(N):
        part.f((rings[-1][k], rings[-1][(k + 1) % N], tip), M_CORE, away=(0.0, 13.0, 0.0))
    part.f(rings[0], M_CORE, out=(0, -1, 0))


def build_nose(part):
    """The blunt end: a dished cap recessed inside a segmented machined lip, eight radial vanes and
    a stepped hub (the viewer's front views; the game camera hardly sees it)."""
    A0, B0 = semi(0.3, 0.0)
    e = 2.0 / EXP

    def ell(a, sc, v):
        c, s_ = math.cos(a), math.sin(a)
        return (sc * A0 * math.copysign(abs(c) ** e, c), v, sc * B0 * math.copysign(abs(s_) ** e, s_))
    # Dish: its face sits back at v 0.17, inside the lip.
    hull(part, [ell(2 * math.pi * k / 24, sc, v) for k in range(24) for sc, v in ((0.7, 0.17), (0.8, 0.32))],
         M_NOSE)
    # Lip: 16 chamfered segments round the dish.
    n = 12
    for k in range(n):
        a0, a1 = 2 * math.pi * (k + 0.06) / n, 2 * math.pi * (k + 0.94) / n
        pts = []
        for a in (a0, (a0 + a1) / 2, a1):
            for sc, v in ((0.67, 0.24), (0.69, 0.06), (0.77, 0.03), (0.81, 0.24)):
                pts.append(ell(a, sc, v))
        hull(part, pts, M_PAD)
    # Vanes from the hub to the lip, and a bolt at each one's outer end.
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        c, s_ = math.cos(a), math.sin(a)
        t = (-s_, 0.0, c)
        pts = []
        for sc in (0.2, 0.64):
            x, _, z = ell(a, sc, 0.0)
            for w in (-0.07, 0.07):
                for v in (0.1, 0.2):
                    pts.append((x + t[0] * w, v, z + t[2] * w))
        hull(part, pts, M_STRAP)
        x, _, z = ell(a, 0.59, 0.0)
        hull(part, [(x + 0.11 * math.cos(b), v, z + 0.11 * math.sin(b))
                    for b in (2 * math.pi * j / 6 for j in range(6)) for v in (0.06, 0.18)], M_RIVET)
    # Hub: a boss and a smaller cap on it.
    hub = []
    for v, r in ((0.06, 0.5), (0.18, 0.62)):
        for k in range(8):
            a = 2 * math.pi * (k + 0.5) / 8
            hub.append((r * 1.5 * math.cos(a), v, r * 0.8 * math.sin(a)))
    hull(part, hub, M_KEEL)
    cap = []
    for v, r in ((0.0, 0.26), (0.08, 0.34)):
        for k in range(8):
            a = 2 * math.pi * (k + 0.5) / 8
            cap.append((r * 1.5 * math.cos(a), v, r * 0.8 * math.sin(a)))
    hull(part, cap, M_STRAP)


def pad_in(v):
    """Inner edge x of the shoulder tiles (the sprite's cols 3-4 / 8-9 are pad, col 5 / 7 channel)."""
    return 1.62 + 0.18 * max(0.0, v - 3.5) / 1.5


def build_pads(part, det):
    top = lambda x: (lambda v: ang_x(v, x(v) if callable(x) else x))  # noqa: E731
    lo_keel = KEEL + GAP
    inner = lambda v: ang_x(v, pad_in(v)) - 0.0  # noqa: E731
    # The split between the outer and inner tiles: an arc (the concept's curved shoulder rows).
    split = lambda v: ang_x(v, 3.15 + 0.35 * min(v, 3.0) / 3.0)  # noqa: E731
    for v0, v1 in ((0.12, 2.98),):
        quad(part, v0, v1, lo_keel, lambda v: split(v) - GAP, M_PAD, g=0.0, c=0.14, astep=0.27)
        quad(part, v0, v1, lambda v: split(v) + GAP, inner, M_PAD, g=0.0, c=0.14)
    # The dark recessed band across the shoulders at row 3 (the sprite's dark row).
    quad(part, 3.04, 3.79, lo_keel, inner, M_CORE, g=-0.14, c=0.08, astep=0.3)
    # Lower tile (row 4): one piece from the keel to the channel.
    quad(part, 3.85, 4.95, lo_keel, inner, M_PAD, g=0.0, c=0.14, astep=0.27)
    # Rivets on the tiles.
    for v in (0.8, 2.3):
        for x in (2.45, 4.25):
            if x < HW(v) - 0.6:
                for sx in (1, -1):
                    for top_ in (True, False):
                        rivet(det, v, ang_x(v, sx * x, 0.0, top_), M_RIVET)
    for sx in (1, -1):
        for top_ in (True, False):
            rivet(det, 4.4, ang_x(4.4, sx * 3.0, 0.0, top_), M_RIVET)
    del top


def build_keel(part):
    for side in (0.0, math.pi):
        band(part, 0.3, 8.82, side - KEEL, side + KEEL, M_KEEL, g=0.06, c=0.16, vstep=0.7)


def build_spine(part, det):
    def half(v):
        if v > 8.0:
            return 0.75 + (0.14 - 0.75) * (v - 8.0) / 0.9
        return 0.75
    lo = lambda v: ang_x(v, half(v))  # noqa: E731
    hi = lambda v: ang_x(v, -half(v))  # noqa: E731
    faces2(part, 0.3, 8.9, lo, hi, M_SPINE, g=0.38, c=0.2, vstep=0.5)
    # Strap across the spine (row 2).
    faces2(part, 1.95, 2.85, lambda v: ang_x(v, 0.92), lambda v: ang_x(v, -0.92), M_STRAP, g=0.55, c=0.12)

    # Lens: an elongated octagonal frame (rows 4.85-7.15) and the glowing glass in it (rows 5-7).
    def octo(v0, v1, w, cut):
        def h(v):
            d = min(v - v0, v1 - v)
            return max(0.08, w - max(0.0, cut - d))
        return h
    fh = octo(4.85, 7.15, 0.6, 0.3)
    faces2(part, 4.85, 7.15, lambda v: ang_x(v, fh(v)), lambda v: ang_x(v, -fh(v)), M_FRAME, g=0.52, c=0.1)
    gh = octo(5.08, 6.92, 0.37, 0.22)
    faces2(det, 5.08, 6.92, lambda v: ang_x(v, gh(v)), lambda v: ang_x(v, -gh(v)), M_LENS, g=0.6, c=0.08,
           vstep=0.3)
    # Louvre slats across the channel beside the spine (rows 0.6-2.8 and 7.2-8.6).
    for v in (0.85, 1.4, 7.6, 8.2):
        for sx in (1, -1):
            for top_ in (True, False):
                x = 1.2 if v < 3 or v > 7 else 1.3
                surf_box(det, v, sx * x, 0.62, 0.22, 0.32, M_STRAP, top=top_, ch=0.0)


def build_body(part):
    """Side straps (row 5), armour blocks (rows 6-8), the tail V and its notch block."""
    lo_keel = KEEL + GAP
    quad(part, 5.05, 5.95, lo_keel, lambda v: ang_x(v, 1.5), M_SSTRAP, g=0.1, c=0.12)
    # The blocks stop at x 1.55 so the dark channel (cols 5 / 7) runs on down beside the spine.
    quad(part, 6.08, 7.32, lo_keel, lambda v: ang_x(v, 1.55), M_BLOCK, g=0.0, c=0.14)
    quad(part, 7.44, 8.75, lo_keel, lambda v: ang_x(v, 1.55), M_BLOCK, g=0.0, c=0.14)

    # Tail V: each arm wraps its edge from the top face round to the bottom face.
    def xin(v):
        if v < 10.55:
            return 0.55
        return max(0.07, 0.55 - 0.48 * (v - 10.55) / 0.75)
    for side in (1, -1):
        if side > 0:
            lo = lambda v: -ang_x(v, xin(v))  # noqa: E731
            hi = lambda v: ang_x(v, xin(v))  # noqa: E731
        else:
            lo = lambda v: ang_x(v, -xin(v))  # noqa: E731
            hi = lambda v: 2 * math.pi - ang_x(v, -xin(v))  # noqa: E731
        band(part, 8.9, 11.2, lo, hi, M_TAIL, g=0.06, c=0.16, vstep=0.8, astep=0.3)
        band(part, 11.32, 12.2, lo, hi, M_TAIL, g=0.0, c=0.14, vstep=1.0, astep=0.42)
    # A dark machined tip cap (rows 12-13, the sprite's 18 there), in two halves.
    for a0 in (-math.pi / 2, math.pi / 2):
        band(part, 12.3, 13.72, a0, a0 + math.pi, M_STRAP, g=0.02, c=0.1, vstep=0.8, astep=0.5)
    # Notch block in the V (rows 9-10, the sprite's 21 down col 6).
    def nh(v):
        return 0.43 if v < 10.3 else max(0.06, 0.43 * (11.0 - v) / 0.7)
    faces2(part, 8.98, 11.0, lambda v: ang_x(v, nh(v)), lambda v: ang_x(v, -nh(v)), M_NOTCH, g=0.12, c=0.1)


def materials(sprite):
    mats = []
    spec = {M_CORE: (0.3, 0.62), M_PAD: (0.45, 0.42), M_SPINE: (0.5, 0.36), M_STRAP: (0.35, 0.55),
            M_FRAME: (0.45, 0.4), M_SSTRAP: (0.4, 0.46), M_BLOCK: (0.45, 0.44), M_TAIL: (0.45, 0.42),
            M_NOTCH: (0.45, 0.42), M_KEEL: (0.5, 0.34), M_RIVET: (0.55, 0.32), M_NOSE: (0.4, 0.45)}
    tags = {M_CORE: "core", M_PAD: "pad", M_SPINE: "spine", M_STRAP: "strap", M_FRAME: "frame", M_LENS: "lens",
            M_SSTRAP: "sstrap", M_BLOCK: "block", M_TAIL: "tail", M_NOTCH: "notch", M_KEEL: "keel",
            M_RIVET: "rivet", M_NOSE: "nose"}
    for i in range(13):
        tag = f"nsh2_171_{tags[i]}"
        if i == M_LENS:
            mats.append(common.palette_material(sprite, PAL_OF[i], tag, metallic=0.0, roughness=0.08,
                                                emission_strength=0.45))
        else:
            met, rough = spec[i]
            mats.append(common.palette_material(sprite, PAL_OF[i], tag, metallic=met * 0.3, roughness=rough))
    return mats


def finish(part, mats, coll, smooth_angle):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0), (0, -PX, 0, 7 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    return obj


def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


def build(coll, mats):
    core = Part("pod_core", smooth_angle=40)
    build_core(core)
    plates = Part("pod_plates", smooth_angle=34)
    det = Part("pod_detail", smooth_angle=30)
    build_nose(det)
    build_pads(plates, det)
    build_keel(plates)
    build_spine(plates, det)
    build_body(plates)
    core_obj = finish(core, mats, coll, 40)
    # The core is the closed body every seam bottoms out on: cull_kept never removes its faces.
    keep = core_obj.data.attributes.new(KEEP, "INT", "FACE")
    keep.data.foreach_set("value", [1] * len(core_obj.data.polygons))
    objs = [core_obj, finish(plates, mats, coll, 34), finish(det, mats, coll, 30)]
    return join(objs, NAME + "_base")


KEEP = "nsh2_keep"


def cull_kept(obj, grid=6, ndirs=48):
    """usp_talon.cull_hidden, except that faces marked KEEP (the core) always stay. The core sits
    under narrow plate seams that the cull's sample grid can miss; culling it there opens slits
    you can see through (fix round 1). The marker attribute is removed afterwards."""
    from mathutils.bvhtree import BVHTree
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    layer = bm.faces.layers.int.get(KEEP)
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    dead = []
    for f in bm.faces:
        if layer is not None and f[layer]:
            continue
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        if len(vs) == 4:
            for i in range(grid):
                for j in range(grid):
                    a = vs[0].lerp(vs[1], (i + 0.5) / grid)
                    b = vs[3].lerp(vs[2], (i + 0.5) / grid)
                    pts.append(a.lerp(b, (j + 0.5) / grid))
        else:
            for vco in vs:
                for t in (0.35, 0.7, 0.92):
                    pts.append(c.lerp(vco, t))
        cand = [d for d in dirs if d.dot(n) > 0.05]
        if not any(tree.ray_cast(p + n * 2e-4, d, 50.0)[0] is None for p in pts for d in cand):
            dead.append(f)
    print(f"{NAME}: culled {len(dead)} hidden faces of {len(bm.faces)}")
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()
    if KEEP in me.attributes:
        me.attributes.remove(me.attributes[KEEP])


# --- bake (AO + edge lift, roughness/metal), as usp_talon.bake_maps -------------------------------

def bake_maps(obj, out_dir, size=512, samples=64):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:
        print(f"{NAME}: no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new("nsh2_171_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("nsh2_171_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        L = nt.links.new
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, val in enumerate((a, b)):
                if val is None:
                    continue
                if isinstance(val, (int, float)):
                    n.inputs[k].default_value = val
                else:
                    L(val, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.025
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.12
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            val = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                         math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                L(math_("MULTIPLY", val, TINT[k]), tint.inputs[k])
            L(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()

    for i, m in enumerate(mats):
        if i == M_LENS:
            continue
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


# --- frames, measure, export ----------------------------------------------------------------------

def frame_matrix(angle):
    return Matrix.Translation((0.5 * PX, 0.0, SPIN_Z)) @ Matrix.Rotation(math.radians(angle), 4, "Y")


def frame_copy(src, name, coll, angle, weighted=True):
    me = src.data.copy()
    me.transform(frame_matrix(angle))
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    for k in src.keys():
        obj[k] = src[k]
    if weighted:
        wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
    return obj


def measure(objs, sprite, sub=8):
    """Top-down coverage of each frame model on the sprite's 12 x 14 grid (ray cast straight down,
    sub x sub samples per pixel), IoU vs the sprite mask (outline ring included), per-row widths,
    and per-material sprite palette medians (the region colour check)."""
    from mathutils.bvhtree import BVHTree
    res = []
    for obj, fr in zip(objs, sprite["frames"]):
        dg = bpy.context.evaluated_depsgraph_get()
        ev = obj.evaluated_get(dg)
        bm = bmesh.new()
        bm.from_mesh(ev.to_mesh())
        bm.faces.ensure_lookup_table()
        tree = BVHTree.FromBMesh(bm)
        mats = [f.material_index for f in bm.faces]
        pix = fr["pixels"]
        cov = [[0.0] * 12 for _ in range(14)]
        matpix = [[None] * 12 for _ in range(14)]
        for r in range(14):
            for cidx in range(12):
                hits, counts = 0, {}
                for i in range(sub):
                    for j in range(sub):
                        u = cidx + (i + 0.5) / sub
                        v = r + (j + 0.5) / sub
                        X, Y = (u - 6) * PX, (7 - v) * PX
                        hit = tree.ray_cast(Vector((X, Y, 5.0)), Vector((0, 0, -1)), 20.0)
                        if hit[0] is not None:
                            hits += 1
                            mi = mats[hit[2]]
                            counts[mi] = counts.get(mi, 0) + 1
                cov[r][cidx] = hits / sub / sub
                if counts:
                    matpix[r][cidx] = max(counts, key=counts.get)
        model = [[cov[r][c] >= 0.5 for c in range(12)] for r in range(14)]
        spr = [[pix[r][c] >= 0 for c in range(12)] for r in range(14)]
        inter = sum(model[r][c] and spr[r][c] for r in range(14) for c in range(12))
        union = sum(model[r][c] or spr[r][c] for r in range(14) for c in range(12))
        regions = {}
        for r in range(14):
            for c in range(12):
                if matpix[r][c] is not None and pix[r][c] > 1 and cov[r][c] >= 0.5:
                    regions.setdefault(matpix[r][c], []).append(pix[r][c])
        res.append({"frame": fr["index"], "iou": round(inter / union, 4),
                    "rowsSprite": [sum(row) for row in spr], "rowsModel": [sum(row) for row in model],
                    "cov": [[round(x, 2) for x in row] for row in cov],
                    "mat": matpix, "regions": {str(k): v for k, v in regions.items()}})
        bm.free()
        ev.to_mesh_clear()
    return res


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    base = build(coll, mats)
    if "--no-cull" not in argv:
        cull_kept(base, grid=10, ndirs=200)
    tris = sum(len(p.vertices) - 2 for p in base.data.polygons)
    print(f"{NAME}: {len(base.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_dir = ROOT / "assets" / "blender" / "textures" / NAME / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(base, bake_dir)  # before the shell exists, so it can't occlude the model
        fmt = "WEBP"
    shell = common.outline_shell(base, coll, faces=1200)
    sheet = sprite["sprites"][0]
    objs = []
    for k, (frame, angle) in enumerate(zip(sprite["frames"], ANGLES)):
        name = NAME if k == 0 else f"{NAME}-f{k + 1}"
        obj = frame_copy(base, name, coll, angle)
        obj["tyrian_frame"] = frame["index"]
        sh = frame_copy(shell, f"{name}_outline", coll, angle, weighted=False)
        sh.parent = obj
        subset = [{**sheet, "frames": [frame["index"]]}]
        common.export_sprite_model(ROOT, [obj, sh], f"enemies/{name}", subset, image_format=fmt)
        objs.append((name, obj, frame))
    base.hide_render = True
    shell.hide_render = True
    if "--measure" in argv:
        info = {"triangles": tris, "angles": ANGLES, "frames": measure([o for _, o, _ in objs], sprite),
                "matPal": {str(i): PAL_OF[i] for i in PAL_OF}}
        Path(argv[argv.index("--measure") + 1]).write_text(json.dumps(info, indent=1))
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        for name, obj, frame in objs:
            ref = ROOT / "reference" / "models" / NAME / frame["image"]
            path = out if name == NAME else out.parent / f"{name}.png"
            common.render_preview([obj], str(path), ref, size=frame["size"])


if __name__ == "__main__":
    main()
