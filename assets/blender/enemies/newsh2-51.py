"""Claw, right-hand (newsh2.shp frame 51): its partner newsh2-49's machine mirrored on X (D50-D53).

Seen in episode 1 (levels 28-30) and episode 3 beside newsh2-49 (enemy types 27 and 29 with 26
and 28). The two sprites (24 x 28 px, one frame each) are exact mirror images in outline, so the
two claws are one design: this script is newsh2-49.py's geometry with every part authored in the
partner's frame (c' = 24 - c) and mirrored by V() (X = (12 - c') / 12, Y = (14 - r) / 12,
Z = z / 12; r = row 0..28 south, z = px up). Front of the enemy = south (towards the player).
Only what this sprite shows differently changes: each part's palette index is the trimmed median
of this sprite's pixels under it (darkest shading and brightest sheen left out), the housing's
beige mark sits where frame 51 has it (row 2, columns 3-4), and the light at row 14 column 1
(palette 109) is the lens, in the same bezel style as the partner's.

What it is: a heavy armoured arm hooking from a purple head (top left) over to the right and down
into a purple blade, and from the head a hanger (link, cross joint, twin rods, clamp) carrying a
grey sensor block with a pale lens and a glowing red crystal.

- Outer arm: a rounded armour band (chamfered shoulders, crowned top, closed belly), pchip
  stations, four segment joints as real V grooves, hex bolts at the joints, a recessed hydraulic
  channel between it and the inner arm (the sprite's dark row 4) holding a ram.
- Inner arm: a lower flat-topped plate with chamfered edges, two joint grooves, then the spine
  rail down the blade's inner edge to the point.
- Blade (purple): knife edged on the outer (east) side, thick at the spine; a raised armour plate
  ending in the diagonal edge, a beige badge in a sunk grey bezel, a grey diagonal brace and rail
  framing the lower panels with a dark vent.
- Head (purple): a rounded hood with a joint groove, a plate with the beige mark, a dark eye
  slot on the south face.
- Hanger: link, cross joint block with hub, rods with a clamp; the sensor block with a vented
  south face, the lens (109, glowing) in a bezel; the dark red collar (67) and a faceted crystal
  (117, glowing).
- Underside: closed bellies only, no detail.

Texture: no concept projection (its maps.json says "bake": "model", as the player ships, D50).
Cycles bakes a colour multiplier (ambient occlusion, edge lift) and a roughness/metalness map
(bake_maps below, after usp_talon.bake_maps) to assets/blender/textures/newsh2-51/bake/; Base
Color = map x palette colour, so pal_<index>, fades and the hit flash still apply. Emissive parts
keep their flat palette colour. An outline shell (common.outline_shell, D51) rides as a child.

Run: blender --background --factory-startup --python assets/blender/enemies/newsh2-51.py
     [-- --preview out.png] [--no-bake]
"""

import bisect
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
NAME = "newsh2-51"
MODEL = f"enemies/{NAME}"
TAG = "newsh2_51"

# --- palette (sprite region medians with the darkest shading and brightest sheen left out) ------
SLOTS = [  # name, palette index (frame 51's trimmed median under the part), metallic, roughness, emission
    ("outer", 5, 0.5, 0.42, 0.0),     # outer armour band (49: 6); see the note under SLOTS
    ("inner", 7, 0.55, 0.36, 0.0),    # inner arm plate
    ("spine", 86, 0.4, 0.42, 0.0),    # spine rail down the blade's inner edge (49: grey 5)
    ("blade", 87, 0.4, 0.42, 0.0),    # blade armour (49: 91)
    ("badge", 170, 0.55, 0.34, 0.0),  # blade badge (49: 171)
    ("cap", 88, 0.4, 0.42, 0.0),      # head hood (49: 87)
    ("deep", 3, 0.3, 0.6, 0.0),
    ("hub", 9, 0.65, 0.3, 0.0),
    ("bezel", 8, 0.6, 0.34, 0.0),
    ("lens", 109, 0.0, 0.2, 2.0),     # the light at row 14, column 1 (49: 110)
    ("collar", 67, 0.3, 0.5, 0.0),
    ("crystal", 117, 0.0, 0.25, 1.6),
    ("hplate", 87, 0.4, 0.42, 0.0),   # head side plate (49: 91)
    ("mark", 171, 0.55, 0.34, 0.0),   # beige mark on the hood, row 2 columns 3-4
    ("brace", 3, 0.3, 0.6, 0.0),      # diagonal brace: frame 51 shows a dark lattice here (49: 7)
    ("rail", 5, 0.5, 0.42, 0.0),      # outer rail of the blade (49: 6)
    ("link", 88, 0.4, 0.42, 0.0),     # hanger link, under the hood (unseen from above: the hood's index)
    ("joint", 5, 0.5, 0.42, 0.0),     # cross joint block (49: 6)
    ("rod1", 4, 0.3, 0.5, 0.0),      # inner hanger rod (49: 7)
    ("rod2", 5, 0.5, 0.42, 0.0),      # outer hanger rod (49: 6)
    ("clamp", 5, 0.5, 0.42, 0.0),
    ("block", 4, 0.3, 0.5, 0.0),     # sensor block (49: 6)
]
# The outer band's pixels (outline left out) run 2..8: its lit crown 5-8 and the shadowed channel side
# 2-4. With the shadow levels (2, 3) and the sheen (8) left out the median is 5; a plain 15 % trim
# gives 4, which reads as a black rubber hose in 3D (the previous model's drum), so 5 it is.
(OUTER, INNER, SPINE, BLADE, BADGE, CAP, DEEP, HUB, BEZEL, LENS, COLLAR, CRYSTAL, HPLATE, MARK, BRACE, RAIL,
 LINK, JOINT, ROD1, ROD2, CLAMP, BLOCK) = range(len(SLOTS))
EMISSIVE = (LENS, CRYSTAL)


def V(c, r, z):
    """Partner-frame (c', r, z) px -> Blender, mirrored on X: this claw is newsh2-49 reflected."""
    return Vector(((12 - c) / 12, (14 - r) / 12, z / 12))


# --- curves -------------------------------------------------------------------------------------

def pchip(xs, ys):
    """Monotone cubic interpolation through (xs, ys): smooth, no overshoot."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def stations_fn(stations):
    """Stations (lists of numbers) spaced by the arc length of their centre line -> f(t), t 0..1."""
    cen = [((s[0] + s[2]) / 2, (s[1] + s[3]) / 2) for s in stations]
    acc = [0.0]
    for a, b in zip(cen, cen[1:]):
        acc.append(acc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    xs = [a / acc[-1] for a in acc]
    fs = [pchip(xs, [s[k] for s in stations]) for k in range(len(stations[0]))]
    return lambda t: [f(t) for f in fs]


def inset(pts, d):
    """Offset a closed (c, r) outline inward by d px (mitred, miter capped)."""
    n = len(pts)
    a2 = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    s = 1 if a2 > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x)) * s
        n1 = Vector((-e1.y, e1.x)) * s
        b = n0 + n1
        if b.length < 1e-6:
            b = n0
        b.normalize()
        q = p1 + b * (d / max(0.35, b.dot(n0)))
        out.append((q.x, q.y))
    return out


# --- mesh builder -------------------------------------------------------------------------------

class Builder:
    def __init__(self):
        self.bm = bmesh.new()

    def face(self, verts, mat):
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return None
        f.material_index = mat
        return f

    def rings(self, rings, mat, cap0=True, cap1=True, mats=None):
        """Loft closed rings of (c, r, z) points of equal length; mats = material per band."""
        vr = [[self.bm.verts.new(V(*p)) for p in ring] for ring in rings]
        n = len(vr[0])
        for k in range(len(vr) - 1):
            m = mats[k] if mats else mat
            for i in range(n):
                j = (i + 1) % n
                self.face([vr[k][i], vr[k][j], vr[k + 1][j], vr[k + 1][i]], m)
        if cap0:
            self.face(list(reversed(vr[0])), mats[0] if mats else mat)
        if cap1:
            self.face(vr[-1], mats[-1] if mats else mat)
        return vr

    def prism(self, pts, z0, z1, mat, ch=0.0, chb=0.25, mats=None):
        """A plate over a (c, r) outline from z0 to z1: top edge chamfered in by `ch`, bottom by
        `chb` (a closed, plausible belly)."""
        rings = []
        if chb > 0:
            rings.append([(c, r, z0) for c, r in inset(pts, chb)])
        rings.append([(c, r, z0 + chb) for c, r in pts])
        if ch > 0:
            rings.append([(c, r, z1 - ch * 0.8) for c, r in pts])
            rings.append([(c, r, z1) for c, r in inset(pts, ch)])
        else:
            rings.append([(c, r, z1) for c, r in pts])
        return self.rings(rings, mat, mats=mats)

    def loft(self, stations, prof, mat, n=24, seams=(), groove=0.32, mats_fn=None):
        """A band between a left edge L and right edge R: stations [Lc, Lr, Rc, Rr, h, z0];
        `prof` is a closed loop of (u 0 at L..1 at R, z 0..1 scaled by h above z0). Seams (0..1)
        are V grooves across it, `groove` px deep."""
        f = stations_fn(stations)
        ts = sorted(set([k / (n - 1) for k in range(n)] + [s + d for s in seams for d in (-0.018, 0.0, 0.018)]))
        ts = [t for t in ts if 0 <= t <= 1]
        rings = []
        for t in ts:
            lc, lr, rc, rr, h, z0 = f(t)
            ring = [(lc + (rc - lc) * u, lr + (rr - lr) * u, z0 + z * h) for u, z in prof]
            if any(abs(t - s) < 1e-9 for s in seams):
                cc = sum(p[0] for p in ring) / len(ring)
                cr = sum(p[1] for p in ring) / len(ring)
                cz = sum(p[2] for p in ring) / len(ring)
                out = []
                for p in ring:
                    d = Vector((cc - p[0], cr - p[1], cz - p[2]))
                    q = Vector(p) + d.normalized() * min(groove, d.length * 0.4)
                    out.append(tuple(q))
                ring = out
            rings.append(ring)
        mats = None
        if mats_fn:
            mats = [mats_fn((a + b) / 2) for a, b in zip(ts, ts[1:])]
        self.rings(rings, mat, mats=mats)
        return f, ts

    def lathe(self, a, b, radii, n, mat, rot=0.0, squash=1.0, mats=None):
        """A lathe along a -> b ((c, r, z) px): radii [(fraction, radius px)]."""
        a, b = Vector(a), Vector(b)
        ax = b - a
        d = ax.normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        u = d.cross(up).normalized()
        v = d.cross(u).normalized()
        rings = []
        for fr, rad in radii:
            c = a + ax * fr
            rings.append([tuple(c + u * math.cos(rot + 2 * math.pi * i / n) * rad
                                + v * math.sin(rot + 2 * math.pi * i / n) * rad * squash) for i in range(n)])
        return self.rings(rings, mat, mats=mats)

    def hexbolt(self, c, r, z, rad=0.32, h=0.22, mat=HUB, normal=(0, 0, 1)):
        nrm = Vector(normal).normalized()
        a = Vector((c, r, z)) - nrm * 0.15
        self.lathe(a, a + nrm * (h + 0.15), [(0, rad), (0.7, rad), (1, rad * 0.7)], 6, mat, rot=0.3)


# --- profiles (u across 0..1, z up 0..1; closed loops, west/L side first going over the top) --
BAND = [(0.12, -0.14), (0.0, 0.12), (0.0, 0.5), (0.05, 0.74), (0.17, 0.92), (0.33, 1.0), (0.67, 1.0),
        (0.83, 0.92), (0.95, 0.74), (1.0, 0.5), (1.0, 0.12), (0.88, -0.14)]
PLATE = [(0.1, -0.15), (0.0, 0.1), (0.0, 0.74), (0.09, 1.0), (0.91, 1.0), (1.0, 0.74), (1.0, 0.1), (0.9, -0.15)]
WEDGE = [(0.2, -0.12), (0.0, 0.2), (0.02, 0.36), (0.3, 0.72), (0.62, 0.9), (0.9, 1.0), (1.0, 0.95), (1.0, 0.05),
         (0.7, -0.22)]
HOOD = [(0.15, -0.12), (0.0, 0.1), (0.0, 0.58), (0.06, 0.82), (0.2, 0.97), (0.38, 1.0), (0.62, 1.0), (0.8, 0.97),
        (0.94, 0.82), (1.0, 0.58), (1.0, 0.1), (0.85, -0.12)]


# --- the parts ----------------------------------------------------------------------------------

OUTER_ST = [  # [Lc, Lr (outer edge), Rc, Rr (inner edge), height, z0]; L edge on the sprite's inner mask (D74)
    [17.9, 1.0, 17.9, 4.0, 4.0, 0.0],
    [15.0, 1.0, 15.0, 4.0, 4.0, 0.0],
    [13.0, 1.0, 12.6, 4.2, 4.0, 0.0],
    [11.0, 2.0, 11.9, 4.85, 4.1, 0.0],
    [9.0, 3.0, 11.4, 5.85, 4.1, 0.0],
    [6.6, 4.0, 11.1, 6.9, 4.0, 0.0],
    [6.0, 4.6, 10.85, 7.9, 3.85, 0.0],
    [6.0, 7.0, 10.6, 8.9, 3.6, 0.0],
    [6.0, 8.6, 10.3, 9.7, 3.3, 0.0],
    [4.6, 9.8, 10.0, 10.3, 3.0, 0.0],
]
OUTER_SEAMS = (0.13, 0.33, 0.53, 0.74)

INNER_ST = [  # R edge (south / west) on the inner mask: r 8 under the bar, then c' + r = 23.5
    [19.1, 4.6, 19.1, 8.0, 2.9, -0.3],
    [16.0, 4.6, 16.0, 8.0, 2.9, -0.3],
    [13.6, 4.65, 14.5, 9.0, 2.9, -0.3],
    [12.3, 5.2, 13.25, 10.25, 2.9, -0.3],
    [11.7, 6.6, 12.3, 11.2, 2.85, -0.3],
    [11.0, 8.3, 11.2, 12.3, 2.8, -0.3],
    [10.0, 10.2, 10.25, 13.25, 2.75, -0.3],
    [9.0, 12.0, 9.2, 14.1, 2.7, -0.3],
    [8.2, 13.8, 9.0, 15.0, 2.6, -0.3],
]

SPINE_ST = [
    [8.2, 13.6, 9.0, 14.8, 2.55, -0.3],
    [8.0, 16.0, 9.0, 16.6, 2.45, -0.3],
    [8.0, 19.0, 9.0, 19.6, 2.3, -0.3],
    [6.4, 21.0, 7.9, 21.6, 2.1, -0.25],
    [4.8, 23.0, 6.1, 23.4, 1.8, -0.2],
    [3.4, 25.0, 4.1, 25.4, 1.5, -0.15],
    [3.3, 25.6, 3.9, 25.9, 1.0, -0.1],
]

BLADE_ST = [
    [4.6, 9.7, 10.0, 10.0, 2.2, -0.2],
    [3.0, 10.7, 10.0, 11.4, 2.1, -0.2],
    [3.0, 14.0, 9.3, 14.2, 2.0, -0.2],
    [3.0, 17.0, 9.0, 17.0, 1.85, -0.2],
    [3.0, 20.0, 9.0, 20.0, 1.65, -0.2],
    [3.0, 22.0, 7.5, 22.0, 1.45, -0.15],
    [3.0, 24.0, 5.5, 24.0, 1.25, -0.1],
    [3.0, 25.0, 4.5, 25.0, 1.0, -0.1],
    [3.0, 25.9, 3.7, 25.9, 0.7, -0.05],
]


def build_arm(b):
    # Outer armour band, its segments split by V grooves.
    f, _ = b.loft(OUTER_ST, BAND, OUTER, n=40, seams=OUTER_SEAMS)
    # A hex bolt on the crown either side of each joint.
    for s in OUTER_SEAMS:
        for ds in (-0.045, 0.045):
            lc, lr, rc, rr, h, z0 = f(s + ds)
            b.hexbolt(lc + (rc - lc) * 0.5, lr + (rr - lr) * 0.5, z0 + h * 0.99, rad=0.24, h=0.16)
    # Hydraulic channel between the outer and inner arm (the sprite's dark row 4): a ram in it.
    b.lathe((18.6, 4.35, 1.6), (14.2, 4.35, 1.6), [(0, 0.7), (1, 0.7)], 10, DEEP)  # cylinder
    b.lathe((14.4, 4.35, 1.6), (12.2, 4.45, 1.6), [(0, 0.42), (1, 0.42)], 8, HUB)  # rod
    b.lathe((12.5, 4.45, 1.6), (11.7, 4.6, 1.6), [(0, 0.62), (1, 0.62)], 8, INNER)  # eye
    b.lathe((18.0, 4.35, 1.6), (17.3, 4.35, 1.6), [(0, 0.85), (1, 0.85)], 10, INNER)  # gland
    # The channel's floor, so the gap between the bands reads as a dark recess, not a hole.
    b.prism([(19.0, 3.9), (12.4, 3.9), (11.2, 5.0), (10.7, 7.2), (11.7, 7.2), (12.4, 5.7), (13.5, 5.0),
             (19.0, 5.0)], -0.3, 1.0, DEEP, ch=0.0, chb=0.2)

    # Web under the bands where their stations leave a notch (the sprite's plate is solid there).
    b.prism([(10.6, 7.0), (13.0, 7.0), (15.2, 8.0), (14.5, 9.0), (12.0, 9.0), (10.6, 9.0)], -0.3, 2.6, INNER, ch=0.3)

    # Inner band, flat topped, and the spine rail on down the blade.
    b.loft(INNER_ST, PLATE, INNER, n=30, seams=(0.2, 0.45, 0.72))
    g, _ = b.loft(SPINE_ST, PLATE, SPINE, n=22, seams=(0.33, 0.66))
    for t in (0.15, 0.48, 0.81):
        lc, lr, rc, rr, h, z0 = g(t)
        b.hexbolt((lc + rc) / 2, (lr + rr) / 2, z0 + h, rad=0.26, h=0.18)


def build_blade(b):
    b.loft(BLADE_ST, WEDGE, BLADE, n=26)
    # Raised armour plate with the diagonal edge; a groove panel line across it.
    plate = [(3.3, 10.3), (8.5, 10.3), (8.5, 13.9), (4.2, 18.2), (3.3, 18.2)]
    b.prism(plate, 0.6, 2.95, BLADE, ch=0.5)
    b.prism([(3.3, 14.1), (6.9, 14.1), (6.6, 14.45), (3.3, 14.45)], 2.7, 3.0, DEEP, ch=0.0, chb=0.0)
    # Badge: a sunk grey bezel, the beige badge proud of it.
    b.prism([(7.2, 9.95), (9.3, 9.95), (9.5, 10.6), (9.5, 13.1), (7.2, 13.1)], 1.2, 3.15, INNER, ch=0.3)
    b.prism([(7.5, 10.25), (9.0, 10.25), (9.2, 10.9), (9.2, 12.8), (7.5, 12.8)], 2.6, 3.45, BADGE, ch=0.25)
    # Grey frame: the diagonal brace and the left rail, chamfered bars.
    b.prism([(8.4, 14.2), (8.4, 16.7), (4.8, 20.2), (4.1, 21.2), (3.3, 21.2), (3.3, 18.7), (3.8, 18.5)],
            0.2, 2.2, BRACE, ch=0.4)
    b.prism([(3.1, 18.4), (4.4, 18.4), (4.4, 22.8), (3.1, 24.2)], 0.2, 2.3, RAIL, ch=0.35)
    # Lower panels: a recessed vent between the brace and spine (three dark slots).
    for k in range(3):
        r0 = 20.4 + k * 0.85
        c1 = 7.4 - k * 0.9
        b.prism([(4.6, r0), (c1, r0 - 0.9 + k * 0.1), (c1, r0 - 0.55 + k * 0.1), (4.6, r0 + 0.35)],
                1.2, 1.62 - k * 0.08, DEEP, ch=0.0, chb=0.0)


def build_head(b):
    st = [
        [16.9, 1.0, 16.9, 4.35, 4.6, -0.5],
        [18.6, 1.0, 18.6, 4.5, 5.2, -0.5],
        [20.0, 1.0, 20.0, 4.5, 5.2, -0.5],
        [21.4, 1.5, 21.4, 4.35, 4.7, -0.5],
        [22.1, 2.4, 22.1, 4.15, 3.9, -0.5],
        [22.1, 3.6, 22.1, 3.95, 2.5, -0.5],
    ]
    # stations run west -> east; the loft's L edge is north
    b.loft(st, HOOD, CAP, n=22, seams=(0.32,))
    b.prism([(16.95, 1.4), (18.15, 1.4), (18.15, 3.8), (16.95, 3.8)], 2.0, 4.95, HPLATE, ch=0.3)
    # Frame 51's beige mark sits on the hood crown (row 2, columns 3-4), not on the side plate.
    b.prism([(19.1, 2.0), (20.9, 2.0), (20.9, 3.0), (19.1, 3.0)], 3.9, 4.88, MARK, ch=0.15, chb=0.0)
    b.hexbolt(17.55, 2.35, 4.95, rad=0.24, h=0.16)
    # Eye slot on the hood's south face, sunk dark, with a hood brow over it.
    b.prism([(19.6, 3.95), (21.5, 3.95), (21.5, 4.6), (19.6, 4.6)], 1.0, 2.7, DEEP, ch=0.1, chb=0.0)
    b.prism([(19.4, 3.7), (21.7, 3.7), (21.7, 4.65), (19.4, 4.65)], 2.7, 3.15, CAP, ch=0.15, chb=0.0)
    # Bolts on the crown.
    b.hexbolt(21.3, 2.6, 3.95, rad=0.24, h=0.16)


def build_hanger(b):
    b.prism([(18.6, 3.6), (20.1, 3.6), (20.1, 5.6), (18.6, 5.6)], 0.2, 2.8, LINK, ch=0.3)
    # Cross joint block, its south face a chamfer; hub with bolts on top.
    b.prism([(19.0, 4.2), (22.6, 4.0), (23.0, 4.4), (23.0, 6.0), (24.0, 6.0), (24.0, 8.0), (20.0, 8.0), (20.0, 7.0), (19.0, 7.0)],
            -0.2, 3.0, JOINT, ch=0.35)
    b.lathe((21.6, 6.4, 2.7), (21.6, 6.4, 3.5), [(0, 0.8), (0.7, 0.8), (1, 0.65)], 12, HUB)
    b.lathe((21.6, 6.4, 3.4), (21.6, 6.4, 3.75), [(0, 0.35), (1, 0.35)], 8, DEEP)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        b.hexbolt(21.6 + math.cos(a) * 1.15, 6.4 + math.sin(a) * 1.0, 3.0, rad=0.2, h=0.16)
    # Rods to the sensor block, a clamp across them.
    b.lathe((21.5, 7.9, 1.3), (21.5, 12.5, 1.3), [(0, 0.5), (1, 0.5)], 10, ROD1)
    b.lathe((22.5, 7.9, 1.0), (22.5, 11.0, 1.0), [(0, 0.5), (1, 0.5)], 10, ROD2)
    b.lathe((21.1, 10.1, 1.2), (22.9, 10.1, 1.2), [(0, 0.5), (1, 0.5)], 8, CLAMP, rot=math.pi / 8)
    # Sensor block: chamfered box, top hatch groove, vented south face.
    blk = [(20.0, 12.0), (23.0, 12.0), (23.0, 18.0), (19.0, 18.0), (19.0, 13.0), (20.0, 13.0)]
    b.prism(blk, -0.7, 3.2, BLOCK, ch=0.55)
    b.prism([(19.5, 12.7), (21.2, 12.7), (21.2, 15.4), (19.5, 15.4)], 2.9, 3.5, BEZEL, ch=0.25, chb=0.0)
    for k in range(3):
        c = 19.6 + k * 1.1
        b.prism([(c, 17.85), (c + 0.55, 17.85), (c + 0.55, 18.1), (c, 18.1)], 0.2, 2.2, DEEP, ch=0.0, chb=0.0)
    # The lens: a tall oval eye on the block's top, tilted to the east, in a raised bezel.
    # Frame 51's light is a single pale pixel (row 14, column 1): the same lens, smaller and rounder.
    b.lathe((22.1, 14.5, 2.5), (22.25, 14.5, 3.25), [(0, 0.8), (0.75, 0.8), (1, 0.68)], 14, BEZEL, squash=0.85)
    b.lathe((22.2, 14.5, 3.1), (22.3, 14.5, 3.55), [(0, 0.52), (0.5, 0.5), (1, 0.3)], 14, LENS, squash=0.8)
    # Collar and the faceted crystal.
    b.lathe((21.0, 17.6, 1.1), (21.0, 19.9, 1.1), [(0, 1.0), (0.45, 1.05), (1, 0.95)], 8, COLLAR,
            rot=math.pi / 8)
    b.lathe((21.0, 19.8, 1.1), (20.8, 24.0, 0.9), [(0, 1.0), (0.25, 1.05), (0.6, 1.0), (0.85, 0.65), (1, 0.05)],
            6, CRYSTAL)


def build(coll, sprite):
    mats = [common.palette_material(sprite, idx, TAG, metallic=met, roughness=rough, emission_strength=em)
            for _, idx, met, rough, em in SLOTS]
    b = Builder()
    build_arm(b)
    build_blade(b)
    build_head(b)
    build_hanger(b)
    bm = b.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    mesh.shade_smooth()
    mesh.set_sharp_from_angle(angle=math.radians(38))
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj, mats


def apply_weighted_normals(obj):
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=wn.name)


# --- bake (no concept projection: occlusion and roughness only, D50) ----------------------

def bake_maps(obj, out_dir, tag, size=1024, samples=64, skip=()):
    """UV the model and bake a grey colour multiplier (two-scale ambient occlusion plus an edge
    lift) and a metallic-roughness map (G roughness, B metallic) with Cycles, then wire them into
    the palette materials (Base Color = map x palette colour) except those named in `skip`."""
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
    except Exception as err:
        print("no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(dict.fromkeys(me.materials))
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

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.2
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.6, math_("MULTIPLY", ao_l.outputs["AO"], 0.4)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.45, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.18)), 1.0)
            nt.links.new(v, em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
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

    for m in [q for q in mats if q.name not in skip]:
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
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj, mats = build(coll, sprite)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    apply_weighted_normals(obj)
    fmt = "AUTO"
    if "--no-bake" not in argv:  # bake before the shell exists, so it can't occlude the model
        bake_dir = ROOT / "assets" / "blender" / "textures" / NAME / "bake"
        bake_dir.mkdir(parents=True, exist_ok=True)
        bake_maps(obj, bake_dir, TAG, size=1024, samples=64, skip={mats[i].name for i in EMISSIVE})
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=1500)
    shell.parent = obj
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=2)


if __name__ == "__main__":
    main()
