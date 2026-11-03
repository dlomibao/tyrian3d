"""Star core panel (newsh2.shp frames 153 / 155 / 157, 24x28 px, enemy type 40): a hard-surface
machine that is its sprite in 3D, built the way the player ships are (usp_talon.py, ships/*.py,
D50-D53).

Seen in episode 1 and episode 3. A machine set into the island (the sprite has no transparent
pixels: round the machine it paints the island's rock, a tan stone at the top left, grey stones at
the top right, tan and grey stones along the bottom edge), the five-pointed star standing in
relief -- the top point a clean chamfered blade (lit left flank, crisp 11 ridge, dark right flank),
the side points two long pale grey pointed arms falling from the raised core housing to the side
beams, the lower points two rust legs that taper down and out to a point over engine housings
with deep nozzles on the screen-down face -- round the glowing core, with a lit salmon lip under
it. Low dark red shoulder armour sits between the top point and the arms.

The sprite is authoritative for the plan (every part sits on the pixels the sprite gives it), the
core's position and size and each region's palette index (the trimmed median of its pixels, the
darkest shading and brightest sheen left out). Concept (assets/blender/features/concepts/newsh2-153.jpg) only for the side and end
design: swept wings with ball studs and struts, rear housings, cable boxes, chin grille, pod flanges.
Bright pixels (the prow's col-11 streak, the arms' 12 knuckles) are sheen, not parts; the chin's
row-18 70-78 strip is a light the sprite shows on every frame, modelled as a polished glowing lip.

The rock round and between the parts is island rock: the sprite's own pixels as the islands'
relief (lib_tiles.sprite_rock, DECISIONS.md D66), a separate object with no outline and no shadow,
so the machine stands in the island instead of on a plate in a rimmed box; the dark floor between
the parts is the sprite's dark pixels there, low in that relief.

Units while building: sprite px (X = column edge - 12, Y = 14 - row edge, Z up, the rock's dark
gaps at Z = 0); scaled by 1/12 at the end like every enemy model (24 px = 2 units).
Underside: plain closed parts standing on the rock, no detail (almost never seen).

The three frames only brighten the core: one model, the core's collar / orb / heart materials
change palette index per frame (common.palette_material frames=, D17).

Texture: no concept projection (its maps.json says "bake": "model", as the player ships, D50): an
ambient occlusion / roughness bake only, Base Color = map x palette colour, so pal_<index>, fades
and the hit flash still apply (the rock is there as an occluder, not baked). An outline shell
(common.outline_shell, D51) of the machine rides along as a child.
No engine glows: the pods' nozzles belong to a fixed panel, not a craft in flight.

Run: blender --background --factory-startup --python assets/blender/enemies/newsh2-153.py
     [-- --preview out.png] [--no-bake] [--out x.glb]
Without --out it exports public/models/enemies/newsh2-153.glb and src/render/spriteModels/newsh2-153.json.
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "tiles")]
import common  # noqa: E402
import lib_tiles as lt  # noqa: E402
import usp_talon  # noqa: E402  (cull_hidden)

NAME = "newsh2-153"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12


# ---- palette slots: name -> (palette index, metallic, roughness, emission, frames) ----------------
SLOTS = [
    # Greys are satin, low-metal (the Talon scales its metals by 0.3): metal at 0.55 mirrored the
    # dark sky and turned the sprite's light-grey rails and arms charcoal in game.
    ("dark2", 2, 0.3, 0.55, 0, None),       # swept wings, under-wings, rear housings
    ("dark3", 3, 0.3, 0.5, 0, None),        # struts, ribs, bay pipes, pistons
    ("gun4", 4, 0.3, 0.45, 0, None),        # prow flank plates, lower arms, cable boxes, housing
    ("grey5", 5, 0.3, 0.42, 0, None),       # bottom lip, beam feet, rivets
    ("grey6", 6, 0.3, 0.4, 0, None),        # upper beam runs, top strip
    ("grey7", 7, 0.3, 0.4, 0, None),        # the left beam's upper run
    ("grey8", 8, 0.35, 0.35, 0, None),      # left nozzle bell
    ("grey9", 9, 0.3, 0.38, 0, None),       # side beams, ledges, studs
    ("grey11", 11, 0.4, 0.3, 0, None),      # beam bolt heads
    ("red67", 67, 0.25, 0.5, 0, None),      # shoulder armour, chin, pods
    ("red70", 70, 0.25, 0.48, 0, None),     # chin lip, pod top seams (the lit rust)
    ("brown22", 22, 0.3, 0.5, 0, None),     # left pod's aft section
    ("brown163", 163, 0.3, 0.55, 0, None),  # right pod's nozzle housing
    ("brown20", 20, 0.3, 0.45, 0, None),    # right nozzle bell
    ("collar", 113, 0.3, 0.35, 0.6, {157: 118}),           # core collar (a faint glow: the sprite's bleed)
    # Frame 153's core is mostly dark red (113-116) round a small orange centre (121/123), 155 an
    # orange-yellow glow and 157 near white: the lens starts at dark red 114 and the heart at 121,
    # so the three frames ramp the way the sprite does instead of 153 already reading hot.
    ("orb", 114, 0.0, 0.12, 1.8, {155: 121, 157: 126}),    # core lens
    ("heart", 121, 0.0, 0.12, 2.6, {155: 127, 157: 127}),  # hot centre
    ("throat", 1, 0.2, 0.9, 0, None),       # nozzle throats, vents, grille slots (unbaked-ish deep)
    # The prow blade: the sprite's lit flank (trimmed median 7) and its crest (11), polished more
    # than the plate so the ridge bevel picks up the key light at the 32-degree game camera.
    ("prow", 7, 0.45, 0.24, 0, None),
    # The crest bevel is broad and flat enough to catch the key light down the blade's whole length,
    # with a faint lift so it stays the sprite's near-white crest at game size.
    ("ridge", 11, 0.5, 0.16, 0.5, None),
    # The prow's right flank, away from the light: the sprite's dark flank (trimmed median 4).
    ("prowdark", 4, 0.45, 0.26, 0, None),
    ("prowdark5", 5, 0.45, 0.28, 0, None),  # its outer edge (sprite cols 13-14 are 4-5)
    # The star's side arms: polished blades, the lit upper facet (left 11 / right 9, the sprite's
    # row-16 medians), a 12 crest and the shaded lower facet (6).
    # The upper facet is about two sprite rows wide (rows 16-17) and lifted a little so the pale
    # arms, not the red shoulders, carry the star at sprite scale.
    ("arm11", 11, 0.2, 0.26, 0.3, None),
    ("arm9", 9, 0.2, 0.26, 0.3, None),
    ("crest12", 12, 0.25, 0.22, 0, None),
    # The lit lip under the core (sprite row 18: 70 75 78 75 70): a polished, faintly glowing strip.
    ("lip", 75, 0.2, 0.2, 0.7, None),
    ("lipc", 78, 0.1, 0.15, 1.0, None),
    ("dark1", 1, 0.3, 0.5, 0, None),        # right swept wing, rear housings (sprite 1 there)
    ("red66", 66, 0.25, 0.5, 0, None),      # the chin body
]
S = {name: i for i, (name, *_rest) in enumerate(SLOTS)}
NO_BAKE = {S["orb"], S["heart"]}


def make_materials(sprite):
    mats = []
    for name, idx, metal, rough, emit, frames in SLOTS:
        tag = f"{NAME}-{name}"
        mats.append(common.palette_material(sprite, idx, tag, metallic=metal, roughness=rough,
                                            emission_strength=emit, frames=frames))
    return mats


# ---- geometry builder (sprite px units) -----------------------------------------------------------
def X(c):
    return c - 12.0


def Y(r):
    return 14.0 - r


class B:
    def __init__(self):
        self.bm = bmesh.new()
        self.sharp = []  # vertex pairs whose edge is split into a hard edge

    def v(self, p):
        return self.bm.verts.new(p)

    def face(self, vs, mat, smooth=False):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        f.smooth = smooth
        return f


def area2(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


def ccw(p):
    return p if area2(p) > 0 else p[::-1]


def inset(p, d):
    """Offset a CCW polygon inward by d (mitred, clamped)."""
    n = len(p)
    out = []
    for i in range(n):
        a, b, c = p[i - 1], p[i], p[(i + 1) % n]
        e1 = (b[0] - a[0], b[1] - a[1])
        e2 = (c[0] - b[0], c[1] - b[1])
        l1 = math.hypot(*e1) or 1
        l2 = math.hypot(*e2) or 1
        n1 = (-e1[1] / l1, e1[0] / l1)
        n2 = (-e2[1] / l2, e2[0] / l2)
        m = (n1[0] + n2[0], n1[1] + n2[1])
        ml = math.hypot(*m) or 1
        m = (m[0] / ml, m[1] / ml)
        k = min(max(d / max(0.25, m[0] * n1[0] + m[1] * n1[1]), 0), 3 * d)
        out.append((b[0] + m[0] * k, b[1] + m[1] * k))
    return out


def prism(b, mat, cr, z0, z1, bev=0.25, top_mat=None, side_mat=None, bottom=True, slope=None, edge_mats=None):
    """Chamfered plate on an outline of (column edge, row edge) points from z0 to z1.
    slope=(dzdx, dzdy) tilts the top (and chamfer ring) linearly about the outline's centre.
    edge_mats={k: mat} gives the side wall and chamfer of outline edge k (cr[k] -> cr[k+1]) its own
    material (a lit leading edge)."""
    raw = [(X(c), Y(r)) for c, r in cr]
    pts = ccw(raw)
    flipped = pts is not raw
    n0 = len(pts)
    emap = {}
    for k, m_ in (edge_mats or {}).items():
        emap[(n0 - 2 - k) % n0 if flipped else k] = m_
    top = inset(pts, bev) if bev > 0 else pts
    cx = sum(q[0] for q in pts) / len(pts)
    cy = sum(q[1] for q in pts) / len(pts)

    def tz(q, z):
        if slope is None:
            return z
        return z + slope[0] * (q[0] - cx) + slope[1] * (q[1] - cy)

    zm = z1 - bev if bev > 0 else z1
    Bv = [b.v((q[0], q[1], z0)) for q in pts]
    Mv = [b.v((q[0], q[1], tz(q, zm))) for q in pts]
    Tv = [b.v((q[0], q[1], tz(q, z1))) for q in top] if bev > 0 else Mv
    sm = side_mat if side_mat is not None else mat
    n = len(pts)
    if bottom:
        b.face(Bv[::-1], mat)
    for i in range(n):
        j = (i + 1) % n
        b.face((Bv[i], Bv[j], Mv[j], Mv[i]), emap.get(i, sm))
        if bev > 0:
            b.face((Mv[i], Mv[j], Tv[j], Tv[i]), emap.get(i, mat))
    b.face(Tv, top_mat if top_mat is not None else mat)


def box(b, mat, c0, r0, c1, r1, z0, z1, bev=0.15, **kw):
    prism(b, mat, [(c0, r0), (c1, r0), (c1, r1), (c0, r1)], z0, z1, bev, **kw)


def mirror_cr(cr):
    return [(24 - c, r) for c, r in cr][::-1]


def ring(cx, cy, z, rx, ry, n, phase=0.0):
    return [(cx + rx * math.cos(2 * math.pi * (i + phase) / n), cy + ry * math.sin(2 * math.pi * (i + phase) / n), z)
            for i in range(n)]


def loft(b, rings, mat, cap0=True, cap1=True, smooth=False, mats=None):
    """Rings of equal length (lists of 3D points), quads between them, fan caps (separate verts)."""
    V = [[b.v(p) for p in r] for r in rings]
    n = len(rings[0])
    for k in range(len(V) - 1):
        m = mats[k] if mats else mat
        for i in range(n):
            j = (i + 1) % n
            b.face((V[k][i], V[k][j], V[k + 1][j], V[k + 1][i]), m, smooth)
    if cap0:
        b.face([b.v(p) for p in rings[0]][::-1], mat)
    if cap1:
        b.face([b.v(p) for p in rings[-1]], mats[-1] if mats else mat)


def dome(b, mat, cx, cy, z0, rx, ry, rz, seg=16, rings_=4, smooth=True, base=True):
    R = []
    for k in range(rings_ + 1):
        t = (k / rings_) * (math.pi / 2)
        f = math.cos(t) if k < rings_ else 0.0
        R.append(ring(cx, cy, z0 + rz * math.sin(t), max(rx * f, 1e-4), max(ry * f, 1e-4), seg))
    V = [[b.v(p) for p in r] for r in R[:-1]]
    tip = b.v((cx, cy, z0 + rz))
    for k in range(len(V) - 1):
        for i in range(seg):
            j = (i + 1) % seg
            b.face((V[k][i], V[k][j], V[k + 1][j], V[k + 1][i]), mat, smooth)
    for i in range(seg):
        j = (i + 1) % seg
        b.face((V[-1][i], V[-1][j], tip), mat, smooth)
    if base:
        b.face([b.v(p) for p in R[0]][::-1], mat)


def sphere(b, mat, c, r, seg=10, rings_=6):
    pts = []
    for k in range(1, rings_):
        t = -math.pi / 2 + k * math.pi / rings_
        pts.append(ring(c[0], c[1], c[2] + r * math.sin(t), r * math.cos(t), r * math.cos(t), seg))
    V = [[b.v(p) for p in rr] for rr in pts]
    bot = b.v((c[0], c[1], c[2] - r))
    top = b.v((c[0], c[1], c[2] + r))
    for k in range(len(V) - 1):
        for i in range(seg):
            j = (i + 1) % seg
            b.face((V[k][i], V[k][j], V[k + 1][j], V[k + 1][i]), mat, True)
    for i in range(seg):
        j = (i + 1) % seg
        b.face((V[0][j], V[0][i], bot), mat, True)
        b.face((V[-1][i], V[-1][j], top), mat, True)


def frame_at(a, bpt):
    a, bpt = Vector(a), Vector(bpt)
    ax = (bpt - a).normalized()
    up = Vector((1, 0, 0)) if abs(ax.z) > 0.9 else Vector((0, 0, 1))
    u = ax.cross(up).normalized()
    w = u.cross(ax)
    return a, bpt, u, w


def cyl(b, mat, a, bpt, r, sides=8, cap0=True, cap1=True, smooth=True, cap_mat=None):
    a, bpt, u, w = frame_at(a, bpt)

    def rg(o, rr):
        return [tuple(o + u * (rr * math.cos(2 * math.pi * (i + 0.5) / sides)) + w * (rr * math.sin(2 * math.pi * (i + 0.5) / sides)))
                for i in range(sides)]
    A, Bq = rg(a, r), rg(bpt, r)
    VA = [b.v(p) for p in A]
    VB = [b.v(p) for p in Bq]
    for i in range(sides):
        j = (i + 1) % sides
        b.face((VA[i], VA[j], VB[j], VB[i]), mat, smooth)
    cm = cap_mat if cap_mat is not None else mat
    if cap0:
        b.face([b.v(p) for p in A][::-1], mat)
    if cap1:
        b.face([b.v(p) for p in Bq], cm)


def nozzle(b, bell, throat, c, r0, r1, z, rad, depth=1.1, lip=0.28, sides=14):
    """A bell along -Y (screen-down face): solid from row r0 to its mouth at row r1, a lip ring and a
    deep dark throat going back `depth` px."""
    cx, y0, y1 = X(c), Y(r0), Y(r1)
    n = sides

    def rg(y, rr):
        return [(cx + rr * math.cos(2 * math.pi * (i + 0.5) / n), y, z + rr * math.sin(2 * math.pi * (i + 0.5) / n)) for i in range(n)]
    back = rg(y0, rad * 0.92)
    mid = rg(y1 + 0.35, rad)
    mouth = rg(y1, rad)
    inner = rg(y1, rad - lip)
    deep = rg(y1 + depth, (rad - lip) * 0.8)
    V = [[b.v(p) for p in rr] for rr in (back, mid, mouth)]
    for k in range(2):
        for i in range(n):
            j = (i + 1) % n
            b.face((V[k][j], V[k][i], V[k + 1][i], V[k + 1][j]), bell, True)
    b.face([b.v(p) for p in back], bell)
    M = [b.v(p) for p in mouth]
    I1 = [b.v(p) for p in inner]
    for i in range(n):
        j = (i + 1) % n
        b.face((M[j], M[i], I1[i], I1[j]), bell)
    I2 = [b.v(p) for p in inner]
    D = [b.v(p) for p in deep]
    for i in range(n):
        j = (i + 1) % n
        b.face((I2[j], I2[i], D[i], D[j])[::-1], throat, True)
    b.face([b.v(p) for p in deep][::-1], throat)


def rivet(b, mat, c, r, z, rad=0.22):
    dome(b, mat, X(c), Y(r), z, rad, rad, rad * 0.6, seg=6, rings_=2, smooth=True, base=False)


# ---- the model ---------------------------------------------------------------------------------------
def build_beams(b):
    # Grey beams down both side edges: an upper sloped run (pal 6), the lit middle run (9) with bolt
    # heads, a lower run (6) and the feet (5), each a separate plate so the joins are real seams.
    for flip in (False, True):
        m = (lambda cr: mirror_cr(cr)) if flip else (lambda cr: cr)
        prism(b, S["grey5" if flip else "grey7"], m([(0, 10.3), (1.6, 9.7), (3.0, 10.7), (3.0, 15.5), (0, 15.5)]), 0, 1.4, 0.3)
        prism(b, S["grey9"], m([(0, 15.65), (3.0, 15.65), (3.0, 22.9), (0, 22.9)]), 0, 1.75, 0.35)
        prism(b, S["grey6"], m([(0, 23.05), (3.0, 23.05), (3.0, 25.3), (0, 25.3)]), 0, 1.35, 0.3)
        prism(b, S["grey6"], m([(0, 25.45), (2.1, 25.45), (2.1, 28), (0, 28)]), 0, 0.9, 0.2)
        # a groove down the middle run (two flutes)
        c0 = 21.9 if flip else 1.9
        box(b, S["dark3"], c0, 16.4, c0 + 0.22, 22.2, 1.6, 1.8, bev=0)
        for r, zt in ((12.6, 1.4), (16.6, 1.75), (19.4, 1.75), (21.9, 1.75), (24.2, 1.35)):
            c = 22.6 if flip else 1.4
            dome(b, S["grey11"], X(c), Y(r), zt, 0.34, 0.34, 0.2, seg=8, rings_=2, base=False)


def build_rear(b):
    # Rear housings (the concept's dark cylinders behind the wings; sprite cols 5-9 / 13-18 rows
    # 1-4, dark 1-5): a block with a round-ended barrel pointing up-screen, a dark port in its end.
    for cx, w in ((7.4, 1.35), (16.0, 1.45)):
        box(b, S["dark1"], cx - w - 0.3, 1.6, cx + w + 0.3, 4.5, 0, 1.2, bev=0.25)
        y0, y1 = Y(4.3), Y(1.0)
        n = 12
        rings_ = []
        for y in (y0, y1 + 0.35, y1):
            rr = w if y != y1 else w * 0.9
            rings_.append([(X(cx) + rr * math.cos(2 * math.pi * (i + 0.5) / n), y, 1.25 + rr * 0.85 * math.sin(2 * math.pi * (i + 0.5) / n))
                           for i in range(n)])
        loft(b, rings_, S["dark1"], cap0=True, cap1=False, smooth=True)
        # port: annulus + recessed throat
        mouth = rings_[-1]
        inner = [(X(cx) + (p[0] - X(cx)) * 0.62, y1, 1.25 + (p[2] - 1.25) * 0.62) for p in mouth]
        deep = [(p[0], y1 - 0.8, p[2]) for p in inner]
        M = [b.v(p) for p in mouth]
        I = [b.v(p) for p in inner]
        for i in range(n):
            j = (i + 1) % n
            b.face((M[i], M[j], I[j], I[i]), S["gun4"])
        loft(b, [inner, deep], S["throat"], cap0=False, cap1=True, smooth=True)
        # a band ring round the barrel
        loft(b, [[(X(cx) + w * 1.06 * math.cos(2 * math.pi * (i + 0.5) / n), Y(r), 1.25 + w * 1.06 * 0.85 * math.sin(2 * math.pi * (i + 0.5) / n)) for i in range(n)]
                 for r in (2.6, 3.0)], S["gun4"], smooth=True)
        rivet(b, S["grey5"], cx, 3.7, 1.25 + w * 0.85, 0.2)


def build_wings(b):
    # Dark swept wings behind the prow (sprite 1-5 rows 4-10), each two plates split by a diagonal
    # seam, with a raised rib, the ball stud at the tip (sprite 12 / 8 at row 6) and a strut with a
    # piston running in to the prow's flank.
    fore = [(0, 4.3), (5.4, 4.3), (7.0, 5.5), (2.6, 7.6), (0, 7.6)]
    aft = [(0, 7.85), (2.75, 7.85), (7.2, 5.75), (8.7, 6.9), (8.7, 10.7), (3.4, 10.7), (0, 9.4)]
    for flip in (False, True):
        m = mirror_cr if flip else (lambda cr: cr)
        wm = S["dark1"] if flip else S["dark2"]  # sprite: left wing 2, right wing 1
        prism(b, wm, m(fore), 0, 1.0, 0.25)
        prism(b, wm, m(aft), 0, 1.1, 0.25)
        # rib along the fore plate
        rib = [(0.6, 5.0), (4.9, 5.0), (5.6, 5.5), (0.6, 5.5)]
        prism(b, S["dark3"], m(rib), 1.0, 1.25, 0.06, bottom=False)
        sc = 21.5 if flip else 2.5
        sphere(b, S["grey9"], (X(sc), Y(6.5), 1.45), 0.85, 10, 6)
        box(b, S["gun4"], sc - 0.9, 5.7, sc + 0.9, 7.3, 0.8, 1.15, bev=0.12)  # stud base
        # strut + piston from the stud to the prow flank
        ex = 15.6 if flip else 8.4
        cyl(b, S["dark3"], (X(sc + (0.8 if not flip else -0.8)), Y(6.9), 1.35), (X(ex), Y(8.2), 1.55), 0.32, 6)
        mid = sc + (3.4 if not flip else -3.4)
        cyl(b, S["grey5"], (X(mid), Y(7.6), 1.47), (X(ex), Y(8.2), 1.55), 0.42, 6)
        for c, r in ((4.6, 9.6), (7.6, 9.6), (1.0, 8.6)):
            rivet(b, S["grey5"], 24 - c if flip else c, r, 1.1, 0.18)


def pchip(xs, ys):
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = 0
        while x > xs[i + 1]:
            i += 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1]
                + (t3 - t2) * h[i] * m[i + 1])
    return f


PROW_X = -0.4  # the sprite's ridge runs down col 11 (core centre col 11.6)
PROW_R = [0, 1.5, 4, 6, 8, 10, 11.4, 12.3]
HW = pchip(PROW_R, [1.4, 1.8, 2.9, 3.7, 4.3, 4.6, 4.2, 3.3])
HT = pchip(PROW_R, [1.5, 1.9, 2.7, 3.35, 3.9, 4.3, 4.3, 3.9])
# Blade cross-section, left to right (u across the half width, v up the height): a low side wall,
# a chamfer, the long flat flank, a narrow ridge bevel either side of the one crisp centre ridge.
# The lit-side crest bevel is broad (a third of the half width) and flatter than the flank, so it
# faces the key light and the camera and reads as the sprite's white crest; the dark flank's outer
# edge is a shade lighter (5), as the sprite's cols 13-14; the lit flank's foot is 5 too (col 8).
ACROSS = [(-1, 0), (-1, 0.2), (-0.9, 0.33), (-0.72, 0.477), (-0.24, 0.87), (0, 1), (0.1, 0.95), (0.45, 0.68), (0.9, 0.33),
          (1, 0.2), (1, 0)]
BAND_MAT = ["prowdark5", "prowdark5", "prowdark5", "prow", "ridge", "ridge", "prowdark", "prowdark5", "prowdark5", "prowdark5"]


def build_prow(b):
    # The star's top point: one clean chamfered blade, lofted through pchip stations (smooth along
    # its length), each facet band its own strip so the chamfers and the ridge stay crisp edges.
    rr = [12.3 * i / 28 for i in range(29)]
    V = [[b.v((PROW_X + u * HW(r), Y(r), v * HT(r))) for u, v in ACROSS] for r in rr]
    n = len(ACROSS)
    for k in range(len(V) - 1):
        for i in range(n - 1):
            b.face((V[k][i], V[k][i + 1], V[k + 1][i + 1], V[k + 1][i]), S[BAND_MAT[i]], True)
        b.face((V[k][n - 1], V[k][0], V[k + 1][0], V[k + 1][n - 1]), S["prow"])  # base (hidden)
    b.face(V[0][::-1], S["prow"])   # back end on the block's top edge
    b.face(V[-1], S["prow"])        # front end, hidden in the hood vent
    # Every band boundary along the length is a hard edge (split after the normals are fixed).
    for i in range(n):
        for k in range(len(V) - 1):
            b.sharp.append((V[k][i], V[k + 1][i]))
    # Stepped flank armour (concept) under the prow's sides.
    fl = [(7.0, 8.6), (8.2, 6.5), (9.1, 6.5), (9.1, 11.7), (7.0, 11.7)]
    prism(b, S["gun4"], fl, 0, 1.95, 0.3)
    prism(b, S["gun4"], mirror_cr(fl), 0, 1.95, 0.3)
    for c, r in ((7.9, 10.6), (16.1, 10.6)):
        rivet(b, S["grey5"], c, r, 1.95, 0.18)
    # Hood vent over the core: a dark slotted box on the hood's down-screen face.
    box(b, S["throat"], 10.3, 11.8, 12.9, 12.35, 2.2, 3.4, bev=0.05)
    for z in (2.55, 2.95):
        box(b, S["gun4"], 10.35, 12.1, 12.85, 12.42, z, z + 0.14, bev=0)


def build_points(b):
    # Left/right points: dark under-wings, red stepped shoulder armour (sprite 66/67, lit inner edge
    # 71-73 = its chamfer facing the light), cable boxes in the outer step, grey ledges below.
    under = [(2.9, 11.0), (6.0, 10.3), (9.5, 10.9), (9.5, 17.0), (2.9, 17.0)]
    prism(b, S["dark2"], under, 0, 1.2, 0.25)
    prism(b, S["dark2"], mirror_cr(under), 0, 1.2, 0.25)
    # left shoulder: rows 12-16 cols 5-9 (row 12 starts at col 6)
    shL = [(5.0, 13.0), (6.0, 11.9), (9.4, 11.9), (9.4, 16.0), (5.0, 16.0)]
    shR = [(14.6, 12.85), (18.6, 12.85), (19.8, 14.6), (19.8, 16.0), (14.6, 16.0)]
    # Kept low (under the arms' ridges) so the grey star arms, not the red blocks, carry the shape.
    for sh in (shL, shR):
        prism(b, S["red67"], sh, 0.8, 2.2, 0.35)
        # raised top plate, inset, with a seam groove left round it by the inset
        cxs = sum(c for c, _ in sh) / len(sh)
        cys = sum(r for _, r in sh) / len(sh)
        top = [(cxs + (c - cxs) * 0.72, cys + (r - cys) * 0.7) for c, r in sh]
        prism(b, S["red67"], top, 2.05, 2.5, 0.2)
    for c, r in ((6.2, 15.4), (8.6, 12.6), (15.4, 15.4), (18.8, 15.4)):
        rivet(b, S["gun4"], c, r, 2.2, 0.17)
    # cable boxes and conduit in the outer step (concept)
    box(b, S["gun4"], 3.3, 12.3, 5.0, 14.3, 0.8, 1.95, bev=0.15)
    box(b, S["gun4"], 19.8, 12.7, 21.1, 14.5, 0.8, 1.95, bev=0.15)
    for (c0, c1, r) in ((3.5, 4.8, 12.9), (3.5, 4.8, 13.6), (20.0, 20.9, 13.3), (20.0, 20.9, 13.9)):
        box(b, S["throat"], c0, r, c1, r + 0.22, 1.9, 2.0, bev=0)
    # The star's side arms (sprite row 16: 6 9 11 12 / 6 12 9 7, row 17 below them 4-8): long
    # pointed blades from under the core housing out to the side beams, the ridge falling from the
    # housing to the tip, the lit upper facet to the screen-up side, the shaded facet below.
    blade(b, (10.0, 17.65), (3.2, 16.95), S["arm11"], S["grey6"])
    blade(b, (14.0, 17.65), (20.8, 16.95), S["arm9"], S["grey6"])


def blade(b, root, tip, up_mat, dn_mat, wu=1.75, wd=0.6, zr=(3.15, 1.45), ze=(2.75, 1.2), zd=(2.1, 1.0), z0=0.6, n=14):
    """A pointed, ridged arm lofted from root to tip (sprite col/row points): section, screen-up side
    first: side wall, a broad, nearly flat upper facet (it faces the light and the game camera), a
    narrow 12 crest, the steeper shaded lower facet, side wall; it narrows to a point over its last
    third and its ridge falls from root to tip."""
    R = Vector((X(root[0]), Y(root[1]), 0))
    T = Vector((X(tip[0]), Y(tip[1]), 0))
    d = (T - R).normalized()
    nv = Vector((-d.y, d.x, 0))
    if nv.y < 0:
        nv = -nv  # the screen-up side
    rings = []
    for k in range(n + 1):
        t = k / n
        taper = max(1 - t ** 3, 0.0) * 0.97 + 0.03
        a, bb = wu * taper, wd * taper
        c = 0.09 * taper + 0.01
        zrt = zr[0] + (zr[1] - zr[0]) * t
        zet = ze[0] + (ze[1] - ze[0]) * t
        zdt = zd[0] + (zd[1] - zd[0]) * t
        o = R + (T - R) * t
        sec = [(a, z0), (a, zet), (c, zrt), (-c, zrt), (-bb, zdt), (-bb, z0)]
        rings.append([tuple(o + nv * u + Vector((0, 0, v))) for u, v in sec])
    V = [[b.v(p) for p in r] for r in rings]
    mats = [up_mat, up_mat, S["crest12"], dn_mat, dn_mat, S["dark3"]]
    for k in range(n):
        for i in range(6):
            j = (i + 1) % 6
            b.face((V[k][i], V[k][j], V[k + 1][j], V[k + 1][i]), mats[i])
    b.face([b.v(p) for p in rings[0]][::-1], dn_mat)
    b.face([b.v(p) for p in rings[-1]], dn_mat)


EYE_C, EYE_R, EYE_RAD = 12.0, 15.0, 3.2


def build_core(b):
    cx, cy = X(EYE_C), Y(EYE_R)
    R = EYE_RAD
    DZ = 0.6  # the core housing stands proud of the star: the arms and legs rise to it
    # gunmetal housing with eight machined segment blocks round its foot
    loft(b, [ring(cx, cy, 0, R + 0.15, R + 0.15, 24), ring(cx, cy, 2.0 + DZ, R + 0.1, R + 0.1, 24),
             ring(cx, cy, 2.25 + DZ, R - 0.05, R - 0.05, 24)], S["gun4"], cap0=False, cap1=False, smooth=True)
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        px_, py_ = cx + (R + 0.1) * math.cos(a), cy + (R + 0.1) * math.sin(a)
        ca, sa = math.cos(a), math.sin(a)
        hw_, hd = 0.55, 0.35
        pts = [(px_ - sa * hw_ - ca * hd, py_ + ca * hw_ - sa * hd), (px_ + sa * hw_ - ca * hd, py_ - ca * hw_ - sa * hd),
               (px_ + sa * hw_ + ca * hd, py_ - ca * hw_ + sa * hd), (px_ - sa * hw_ + ca * hd, py_ + ca * hw_ + sa * hd)]
        prism(b, S["gun4"], [(p[0] + 12, 14 - p[1]) for p in pts], 0.8, 2.0 + DZ, 0.12)
    # dark red collar, a torus-like ring (sprite 112-114 rim)
    loft(b, [ring(cx, cy, 2.25 + DZ, R - 0.05, R - 0.05, 24), ring(cx, cy, 2.75 + DZ, R - 0.3, R - 0.3, 24),
             ring(cx, cy, 2.8 + DZ, R - 0.6, R - 0.6, 24), ring(cx, cy, 2.4 + DZ, R - 0.75, R - 0.75, 24)],
         S["collar"], cap0=False, cap1=True, smooth=True)
    # The glowing core: a recessed faceted lens inside the collar -- a low octagonal frustum turned
    # to read as the sprite's square/diamond glow, flat-topped, with a raised diamond hot centre
    # up-left of its middle like the sprite (123 at col 11 row 14).
    rl = R - 0.72
    lens = [ring(cx, cy, 2.3 + DZ, rl, rl, 8, 0.0), ring(cx, cy, 2.62 + DZ, rl * 0.86, rl * 0.86, 8, 0.0),
            ring(cx, cy, 2.86 + DZ, rl * 0.6, rl * 0.6, 8, 0.0)]
    loft(b, lens, S["orb"], cap0=False, cap1=True, smooth=False)
    hx, hy = X(11.85), Y(14.55)
    loft(b, [ring(hx, hy, 2.8 + DZ, 0.95, 0.95, 4, 0.0), ring(hx, hy, 3.0 + DZ, 0.55, 0.55, 4, 0.0)],
         S["heart"], cap0=False, cap1=True, smooth=False)


def build_chin(b):
    # Rust chin under the core (sprite 66/67; row 18 70-78 is its lit upper bevel = sheen) with a
    # lit-rust lip, a grille of slots on its front face, and the grey nose cap between it and the
    # collar (concept).
    ch = [(8.9, 17.9), (15.1, 17.9), (15.1, 20.2), (14.0, 21.4), (10.0, 21.4), (8.9, 20.2)]
    prism(b, S["red66"], ch, 0, 2.5, 0.55)
    # The lit lip right under the core (sprite row 18: 70 75 78 75 70 on every frame): a polished,
    # faintly glowing strip across the chin's top edge, its brightest segment in the middle.
    box(b, S["red70"], 9.0, 18.0, 15.0, 18.95, 1.9, 2.75, bev=0.12)
    box(b, S["lip"], 9.75, 18.02, 14.25, 18.93, 2.6, 2.95, bev=0.1)
    box(b, S["lipc"], 11.0, 18.08, 12.4, 18.87, 2.9, 3.0, bev=0.04)
    for k in range(3):
        box(b, S["throat"], 10.5, 21.25, 13.5, 21.5, 0.45 + k * 0.55, 0.75 + k * 0.55, bev=0)
    rivet(b, S["gun4"], 10.0, 19.6, 2.5, 0.18)
    rivet(b, S["gun4"], 14.0, 19.6, 2.5, 0.18)


def build_arms_bay(b):
    # Lower arms from the ledges to the chin (sprite 4-8), pistons over the bay, the bay pipes.
    al = [(4.2, 17.5), (5.2, 18.2), (8.8, 18.2), (8.8, 21.0), (8.2, 21.0), (7.6, 19.7), (4.2, 19.5)]
    prism(b, S["gun4"], al, 0, 1.9, 0.25)
    prism(b, S["gun4"], mirror_cr(al), 0, 1.9, 0.25)
    for flip in (False, True):
        f = (lambda c: 24 - c) if flip else (lambda c: c)
        cyl(b, S["dark3"], (X(f(4.6)), Y(18.6), 2.15), (X(f(7.0)), Y(19.9), 1.8), 0.32, 6)
        cyl(b, S["grey9"], (X(f(6.6)), Y(19.7), 1.85), (X(f(8.0)), Y(20.5), 1.55), 0.2, 6)
    # bay machinery (sprite rows 21-25 cols 8-15): two cross pipes and three uprights on the floor
    cyl(b, S["dark3"], (X(8.4), Y(24.5), 0.42), (X(15.6), Y(24.5), 0.42), 0.42, 8)
    cyl(b, S["dark3"], (X(8.4), Y(25.5), 0.32), (X(15.6), Y(25.5), 0.32), 0.32, 8)
    for c in (10.0, 12.0, 14.0):
        cyl(b, S["dark3"], (X(c), Y(21.4), 0.25), (X(c), Y(24.4), 0.25), 0.24, 6)
    for c in (10.0, 14.0):
        box(b, S["gun4"], c - 0.45, 24.05, c + 0.45, 24.95, 0, 0.95, bev=0.1)


def build_pods(b):
    # Left pod: rust body rows 20-24 with its upper-outer corner cut (sprite 66-71), a brown aft
    # section (20-24), a side flange, the grey nozzle bell on the bottom edge (sprite 6-10).
    # The star's lower legs: tapered wedges that fall from the chin down and out to a point, a lit
    # 70 leading edge on the sprite's lit side (69-71 down the diagonal), a raised spine plate.
    podL = [(3.0, 24.15), (6.4, 19.9), (8.2, 19.9), (8.2, 24.15)]
    prism(b, S["red67"], podL, 0, 2.4, 0.45, slope=(0.25, 0.25), edge_mats={0: S["red70"]})
    prism(b, S["red67"], [(4.0, 23.9), (6.7, 20.5), (7.9, 20.5), (7.9, 23.9)], 0.5, 2.75, 0.2, slope=(0.25, 0.25))
    prism(b, S["brown22"], [(3.0, 24.3), (8.4, 24.3), (8.4, 25.95), (7.8, 26.4), (3.6, 26.4), (3.0, 25.8)], 0, 1.5, 0.35)
    box(b, S["grey5"], 2.3, 22.4, 3.05, 25.6, 0.3, 1.9, bev=0.12)   # side flange
    nozzle(b, S["grey8"], S["throat"], 6.4, 25.0, 28.0, 1.25, 1.15)
    rivet(b, S["gun4"], 4.0, 25.0, 1.5, 0.17)
    # Right pod: rust body rows 21-25 (sprite 66-71), the dark brown nozzle housing (162/163) and
    # the brown bell (20/21) on the bottom edge.
    podR = [(15.2, 23.0), (16.6, 20.8), (18.6, 20.8), (21.0, 24.7), (20.6, 25.2), (15.2, 25.2)]
    prism(b, S["red67"], podR, 0, 2.4, 0.45, slope=(-0.25, 0.25), edge_mats={0: S["red70"], 5: S["red70"]})
    prism(b, S["red67"], [(16.0, 23.0), (17.0, 21.5), (18.8, 21.5), (20.0, 23.3), (20.0, 24.6), (16.0, 24.6)], 0.5, 2.75, 0.2,
          slope=(-0.25, 0.25))
    prism(b, S["brown20"], [(15.6, 25.35), (21.0, 25.35), (21.0, 27.0), (20.4, 27.3), (16.2, 27.3), (15.6, 26.8)], 0, 1.5, 0.3)
    box(b, S["brown163"], 16.6, 25.7, 20.2, 26.9, 1.35, 1.6, bev=0.1)  # dark top panel (sprite 162/163)
    box(b, S["grey5"], 20.9, 23.2, 21.3, 26.4, 0.3, 1.6, bev=0.1)
    nozzle(b, S["brown20"], S["throat"], 18.6, 26.0, 28.0, 1.2, 1.1)
    rivet(b, S["gun4"], 20.3, 26.0, 1.6, 0.17)


STAR_BODY = [(10.0, 2.6), (13.4, 2.6), (15.4, 10.6), (20.4, 15.5), (20.4, 18.4), (16.4, 19.2), (19.6, 24.6), (15.8, 21.7),
             (12.0, 21.3), (8.2, 21.7), (4.2, 24.0), (7.6, 19.2), (3.6, 18.4), (3.6, 15.5), (8.6, 10.6)]


def build_star_body(b):
    # One continuous raised star housing under the prow, the arms, the core and the legs, so the
    # points read as one machine standing on the plate rather than separate blocks on a deck.
    # Two chamfered tiers; mostly covered from above, it shows as the stepped flank in the side,
    # front and 3/4 views. Gunmetal 4, as the sprite's dark machinery between the points.
    prism(b, S["gun4"], STAR_BODY, 0, 1.05, 0.3)
    cx, cy = 12.0, 15.6
    inner = [(cx + (c - cx) * 0.8, cy + (r - cy) * 0.82) for c, r in STAR_BODY]
    prism(b, S["gun4"], inner, 0.9, 1.6, 0.25)


def build(b):
    # No deck plate and no corner blocks: the sprite's stones in the corners and along the bottom
    # edge, and the dark floor between the parts, are the island rock (lib_tiles.sprite_rock).
    build_star_body(b)
    build_beams(b)
    build_rear(b)
    build_wings(b)
    build_prow(b)
    build_points(b)
    build_core(b)
    build_chin(b)
    build_arms_bay(b)
    build_pods(b)


def to_object(b, name, mats, coll):
    bm = b.bm
    bmesh.ops.scale(bm, vec=(PX, PX, PX), verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    sharp = [e for e in (bm.edges.get(pair) for pair in b.sharp) if e is not None]
    bmesh.ops.split_edges(bm, edges=sharp)
    # Non-planar quads (the prow's lofted facets) would shade with one normal over two differently
    # tilted triangles, which the bake's edge term turns into blotches: triangulate them.
    nonplanar = [f for f in bm.faces if len(f.verts) == 4 and
                 max(abs((v.co - f.calc_center_median()).dot(f.normal)) for v in f.verts) > 1e-5]
    bmesh.ops.triangulate(bm, faces=nonplanar, quad_method="BEAUTY")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def bake_maps(obj, out_dir, mats, size=1024, samples=96):
    """usp_talon.bake_maps, adapted (as the assembly-newsh2-245 A did): AO at two scales x an edge
    lift as a grey colour multiplier, and a roughness/metal map; NO concept projection. Wired as
    Base Color = map x palette colour, so the palette, fades and the hit flash still apply."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
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
    except Exception as err:  # noqa: BLE001
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
    col_img = bpy.data.images.new(f"{NAME}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{NAME}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def mth(op, a, b_=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, val in enumerate((a, b_)):
                if val is None:
                    continue
                if isinstance(val, (int, float)):
                    n.inputs[k].default_value = val
                else:
                    nt.links.new(val, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 32
        ao_s.inputs["Distance"].default_value = 0.02
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 32
        ao_l.inputs["Distance"].default_value = 0.12
        bev = node("ShaderNodeBevel")
        bev.samples = 16
        bev.inputs["Radius"].default_value = 0.004
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = mth("MINIMUM", mth("MULTIPLY", mth("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = mth("MULTIPLY", mth("POWER", ao_s.outputs["AO"], 0.8),
                   mth("ADD", 0.65, mth("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            val = mth("MINIMUM", mth("ADD", mth("ADD", 0.66, mth("MULTIPLY", occl, 0.45)), mth("MULTIPLY", edge, 0.12)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(val, comb.inputs[k])
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        else:
            r = mth("ADD", rough, mth("SUBTRACT", mth("MULTIPLY", mth("SUBTRACT", 1.0, occl), 0.3), mth("MULTIPLY", edge, 0.14)))
            r = mth("MAXIMUM", mth("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
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
        if i in NO_BAKE:
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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    mats = make_materials(sprite)
    b = B()
    build(b)
    obj = to_object(b, NAME, mats, coll)
    # The island rock round the machine (D66); there for the bake as an occluder.
    rock = lt.build_sprite_rock(ROOT, [obj], [(NAME, 0, 0)], 24, 28, coll, f"{NAME}-rock")[NAME]
    # The outline shell (D51) is made from the closed parts, before hidden faces are culled.
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=2000)
    usp_talon.cull_hidden(obj, grid=4, ndirs=32)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles; outline shell {len(shell.data.polygons)} faces")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        shell.hide_render = True  # the shell would occlude the AO rays where it pokes through
        bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"), mats)
        shell.hide_render = False
        fmt = "WEBP"
    shell.parent = obj
    rock.parent = obj
    print(f"{NAME}: rock {sum(len(p.vertices) - 2 for p in rock.data.polygons)} triangles")
    if out:
        common.export_glb([obj, shell, rock], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(ROOT, [obj, shell, rock], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj, rock], argv[argv.index("--preview") + 1], ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
