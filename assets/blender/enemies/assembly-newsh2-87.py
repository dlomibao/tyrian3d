"""Blue-armed ground gun walker (newsh2.shp frames 85 and 87, an assembly of 2 pieces): a 3D version
of its sprites.

Seen in episodes 1 and 3 (levels 1.25, 1.28, 1.3, 1.36, 3.17). Two 2x2 enemies side by side
(newsh2-85 on the left, newsh2-87 on the right, sprite.json `assemblyLayout`) make one 48x28 px
machine.

A hard-surface walker that is the sprite in 3D. Silhouette and readability first: from the tilted
game camera it reads as four clear masses - a grey armoured hull with a dark faceted visor and a
glowing exhaust louvre at the back, red thruster pods either side, two bright blue T-shaped gun
arms (the highest, brightest parts, as in the sprite) with forward-facing bored muzzles, and a
hanging ball eye with a red lens - carried on two level box-section legs standing on the ground
(an inner shin strut to a foot, an outer claw with an armour plate and a knee; level so the prongs
stay straight under the off-axis game camera, D163). Detail second: chamfered sections, modelled
panel-line grooves on the big top panels, rivets, louvre ribs, deep bores and nozzles, hydraulic
rams on the legs, cables beside the eye stem. The underside is just closed hull, with no detail.

The sprite is authoritative for the top-down outline (row by row), the screen, lamps, lens and vents
and the colours: every part takes the palette index of the sprite pixels under it (their median,
the darkest shading and brightest sheen left out). Satin metal; no concept projection bake (no
"crinkled foil", as the player ships in #84): only an occlusion / edge colour multiplier and a
roughness map baked from the model itself (maps.json "bake": "model").

Coordinates: u = sprite column edge (0..48), v = sprite row edge (0 = rear/top of the sprite,
28 = front), z = height above the ground, all in sprite px (1 px = 1/12 unit). Mirror plane u = 23
(pixel c <-> 45 - c). The sprite is not quite symmetric (the right claw is one column narrower,
the right arm tab one column further in); the model follows it.

The whole machine is built in assembly coordinates and cut into newsh2-85 / newsh2-87 with
common.split_assembly (CX0, CY0 = 206, 43 at the Blender origin) and exported as
public/models/enemies/newsh2-85.glb and newsh2-87.glb, each with its own spriteModels entry (one frame
each) and its part of the outline shell (D51), cut at the seam and capped so each piece's shell is
closed on its own.

Run: blender --background --factory-startup --python assets/blender/enemies/assembly-newsh2-87.py
     [-- --preview out.png] [--views DIR] [--out whole.glb] [--no-bake]
(--views renders the review views and an index render of the top, --out writes both pieces placed
as in the layout into one file.)
"""

import math
import json
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b083 as lib  # noqa: E402

ROOT = common.repo_root(__file__)
NAME = "assembly-newsh2-87"
PIECES = ["newsh2-85", "newsh2-87"]
CX0, CY0 = 206, 43
PX = 1 / 12
AX2 = 46.0  # u -> 46 - u mirrors pixel c to 45 - c

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def P(u, v, z):
    return Vector(((u - 24) * PX, (14 - v) * PX, z * PX))


# ---------------------------------------------------------------- materials -------------------
# key: (palette index, metallic, roughness, emission strength)
MATS = {
    "steel": (4, 0.3, 0.45, 0),       # dark grey hull, ball, clamps
    "clamp": (8, 0.35, 0.4, 0),       # stem clamps
    "frame": (6, 0.35, 0.42, 0),        # screen frame, pipe, hips, eye bezel ring
    "house": (7, 0.35, 0.4, 0),        # light grey housings
    "bright": (9, 0.35, 0.4, 0),       # collar
    "knob": (6, 0.35, 0.42, 0),
    "collar": (10, 0.35, 0.4, 0),      # light ring where the eye stem meets the ball
    "dark": (2, 0.35, 0.6, 0),         # grilles, chin, sockets
    "glass": (58, 0.0, 0.3, 0.6),      # visor upper pane: a lit screen, light blue as the sprite's
    "glass_lo": (129, 0.15, 0.1, 0),   # visor front facet
    "rim": (59, 0.3, 0.3, 0),          # sensor strip
    "pod": (117, 0.3, 0.42, 0),        # red thruster pods
    "pod_dk": (116, 0.35, 0.45, 0),    # dark red ribs, chin vents
    "arm": (155, 0.4, 0.38, 0),        # bright blue arms
    "muzzle": (56, 0.45, 0.4, 0),      # gun muzzle block
    "bore": (52, 0.3, 0.6, 0),
    "leg": (57, 0.35, 0.45, 0),        # blue-steel spines, feet
    "strut": (6, 0.35, 0.42, 0),       # strut beams (grey steel, as the sprite's pixels there)
    "ram": (55, 0.35, 0.45, 0),        # hydraulic plate under the arm
    "claw": (57, 0.35, 0.42, 0),       # left upper claw
    "ankle": (58, 0.35, 0.42, 0),
    "plate": (101, 0.4, 0.45, 0),      # outer claw armour
    "claw_lo": (100, 0.4, 0.45, 0),    # lower claws, right outer claw
    "glow_vent": (117, 0, 0.5, 3.0),   # side vent glows
    "glow_rear": (118, 0, 0.5, 3.0),   # exhaust louvre
    "glow_hot": (121, 0, 0.5, 5.0),    # pod nozzles
    "glow_core": (122, 0, 0.5, 5.0),   # exhaust core
    "glow_lamp": (120, 0, 0.5, 3.0),   # lamps, pod slits
    "lens": (116, 0.2, 0.15, 1.2),     # red lens
    "lens_core": (118, 0, 0.3, 4.0),
}
MKEYS = list(MATS)


def make_materials(sprite):
    mats = []
    for k in MKEYS:
        pal, met, rough, em = MATS[k]
        mats.append(common.palette_material(sprite, pal, f"nsh2_87_{k}", metallic=met, roughness=rough,
                                            emission_strength=em))
    return mats


# ---------------------------------------------------------------- builder ---------------------
class Builder:
    def __init__(self):
        self.bm = bmesh.new()
        self.pid = self.bm.faces.layers.int.new("part")
        self.parts = []  # (name, matkey, side)
        self.cur = 0
        self.mat = 0
        self.mirror = False
        self.smooth = False

    def part(self, name, mk, side="C"):
        if self.mirror:
            name = name.replace("_L", "_R")
            side = "R" if side == "L" else side
        self.parts.append((name, mk, side))
        self.cur = len(self.parts) - 1
        self.mat = MKEYS.index(mk)

    def M(self, u):
        return AX2 - u if self.mirror else u

    def vs(self, pts):
        return [self.bm.verts.new(P(self.M(u), v, z)) for u, v, z in pts]

    def f(self, verts, smooth=None):
        try:
            face = self.bm.faces.new(verts)
        except ValueError:
            return None
        face.material_index = self.mat
        face[self.pid] = self.cur
        face.smooth = self.smooth if smooth is None else smooth
        return face

    def bridge(self, a, b, closed=True, smooth=None):
        n = len(a)
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            self.f((a[i], a[j], b[j], b[i]), smooth)


def inset(poly, d):
    """Offset a (u, v) polygon inwards by d along corner bisectors."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    s = 1 if area > 0 else -1
    out = []
    for i in range(n):
        a, b, c = poly[i - 1], poly[i], poly[(i + 1) % n]
        e1 = (b[0] - a[0], b[1] - a[1])
        e2 = (c[0] - b[0], c[1] - b[1])
        l1, l2 = math.hypot(*e1), math.hypot(*e2)
        n1 = (-e1[1] / l1 * s, e1[0] / l1 * s)
        n2 = (-e2[1] / l2 * s, e2[0] / l2 * s)
        dd = max(0.2, 1 + n1[0] * n2[0] + n1[1] * n2[1])
        out.append((b[0] + d * (n1[0] + n2[0]) / dd, b[1] + d * (n1[1] + n2[1]) / dd))
    return out


def rect(u0, v0, u1, v1, cut=0.0):
    if cut <= 0:
        return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    return [(u0 + cut, v0), (u1 - cut, v0), (u1, v0 + cut), (u1, v1 - cut), (u1 - cut, v1),
            (u0 + cut, v1), (u0, v1 - cut), (u0, v0 + cut)]


def chamfer(c):
    return [(0, c), (c, 0)]


def fillet(r, k=3):
    return [(r * (1 - math.cos(math.pi / 2 * i / k)), r * (1 - math.sin(math.pi / 2 * i / k))) for i in range(k + 1)]


def prism(B, outline, z0, top, ptop=((0, 0),), pbot=((0, 0),), groove=None):
    """A block over a (u, v) outline from z0 to top (number or f(u, v)). ptop: (inset, drop) steps up
    the top edge (chamfer / fillet); pbot the same for the bottom edge, listed bottom-up as
    (inset, rise). groove = (inset, width, depth): a modelled panel line round the top panel."""
    tf = top if callable(top) else (lambda u, v: top)
    rings = []
    for ins, rise in pbot:
        poly = inset(outline, ins) if ins else outline
        rings.append([(u, v, z0 + rise) for u, v in poly])
    for ins, drop in ptop:
        poly = inset(outline, ins) if ins else outline
        rings.append([(u, v, tf(u, v) - drop) for u, v in poly])
    if groove:
        base = ptop[-1][0]
        gi, gw, gd = groove
        for ins, dz in ((base + gi, 0), (base + gi, gd), (base + gi + gw, gd), (base + gi + gw, 0)):
            poly = inset(outline, ins)
            rings.append([(u, v, tf(u, v) - dz) for u, v in poly])
    vr = [B.vs(r) for r in rings]
    B.f(list(reversed(vr[0])))
    for a, b in zip(vr, vr[1:]):
        B.bridge(a, b)
    B.f(vr[-1])


def ring_prism(B, outer, inner, z0, z1):
    ob, ot = B.vs([(u, v, z0) for u, v in outer]), B.vs([(u, v, z1) for u, v in outer])
    ib, it = B.vs([(u, v, z0) for u, v in inner]), B.vs([(u, v, z1) for u, v in inner])
    B.bridge(ob, ot)
    B.bridge(it, ib)
    B.bridge(ot, it)
    B.bridge(ib, ob)


def pchip(xs, ys):
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    if n == 2:
        m = [d[0], d[0]]
    else:
        for i in range(1, n - 1):
            if d[i - 1] * d[i] > 0:
                w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
        m[0], m[-1] = d[0], d[-1]

    def f(x):
        i = 0
        while i < n - 2 and x > xs[i + 1]:
            i += 1
        t = min(1, max(0, (x - xs[i]) / h[i]))
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1]
                + (t3 - t2) * h[i] * m[i + 1])
    return f


def sweep(B, st, ch=0.3, steps=12, taper_end=0.0, keel=1.0):
    """Box-section beam with chamfered corners along stations (u, v, zc, w, h), rings at constant v.
    keel < 1 narrows the bottom to that fraction of the width (the sides lean in under the top)."""
    vs = [s[1] for s in st]
    fu, fz, fw, fh = (pchip(vs, [s[k] for s in st]) for k in (0, 2, 3, 4))
    rings = []
    # uniform rings plus one at every station, so a station's width lands exactly where it is set
    samples = sorted({round(vs[0] + (vs[-1] - vs[0]) * k / steps, 4) for k in range(steps + 1)} | set(vs))
    samples = [v for i, v in enumerate(samples) if i == 0 or v - samples[i - 1] > 0.12 or v in vs]
    for v in samples:
        u, zc, w, hh = fu(v), fz(v), fw(v) / 2, fh(v) / 2
        c = min(ch, w * 0.45, hh * 0.45)
        wb = w * keel
        sec = [(-w + c, hh), (w - c, hh), (w, hh - c), (wb, -hh + c), (wb - c, -hh), (-wb + c, -hh), (-wb, -hh + c),
               (-w, hh - c)]
        rings.append(B.vs([(u + a, v, zc + b) for a, b in sec]))
    B.f(list(reversed(rings[0])))
    for a, b in zip(rings, rings[1:]):
        B.bridge(a, b)
    B.f(rings[-1])


def basis(n):
    n = Vector(n).normalized()
    t = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    a = n.cross(t).normalized()
    return n, a, n.cross(a)


def cyl(B, p0, p1, r0, r1=None, sides=12, bev=0.0, smooth=True, cap0=True, cap1=True):
    """Cylinder p0 -> p1 ((u, v, z) px); bev chamfers both rims."""
    r1 = r0 if r1 is None else r1
    p0, p1 = Vector(p0), Vector(p1)
    n, a, b = basis(p1 - p0)
    ln = (p1 - p0).length
    prof = [(0, r0 - bev), (bev, r0), (ln - bev, r1), (ln, r1 - bev)] if bev else [(0, r0), (ln, r1)]
    rings = []
    for t, r in prof:
        c = p0 + n * t
        rings.append(B.vs([tuple(c + a * (r * math.cos(2 * math.pi * (i + 0.5) / sides))
                                 + b * (r * math.sin(2 * math.pi * (i + 0.5) / sides))) for i in range(sides)]))
    if cap0:
        B.f(list(reversed(rings[0])), False)
    for k, (ra, rb) in enumerate(zip(rings, rings[1:])):
        sm = smooth and not (bev and k != 1)
        B.bridge(ra, rb, smooth=sm)
    if cap1:
        B.f(rings[-1], False)


def tube(B, p0, p1, ro, ri, depth, sides=12, back=None):
    """A thick-walled tube p0 -> p1 (open at p1) with a recessed floor `depth` px in: a bore / nozzle.
    Returns the floor centre so a glow disc can go there."""
    p0, p1 = Vector(p0), Vector(p1)
    n, a, b = basis(p1 - p0)

    def ring(c, r):
        return B.vs([tuple(c + a * (r * math.cos(2 * math.pi * (i + 0.5) / sides))
                           + b * (r * math.sin(2 * math.pi * (i + 0.5) / sides))) for i in range(sides)])
    o0, o1, i1, i0 = ring(p0, ro), ring(p1, ro), ring(p1, ri), ring(p1 - n * depth, ri)
    B.f(list(reversed(o0)), False)
    B.bridge(o0, o1, smooth=True)
    B.bridge(o1, i1, smooth=False)
    B.bridge(i1, i0, smooth=True)
    B.f(list(reversed(i0)), False)
    return p1 - n * depth


def dome(B, c, n, r, h, seg=16, rings=4, smooth=True):
    c = Vector(c)
    N, a, b = basis(n)
    prev = None
    rows = []
    for i in range(rings + 1):
        th = math.pi / 2 * i / rings
        rr = r * math.cos(th)
        if i == rings:
            rows.append(B.vs([tuple(c + N * h)]))
        else:
            rows.append(B.vs([tuple(c + N * (h * math.sin(th)) + a * (rr * math.cos(2 * math.pi * j / seg))
                                    + b * (rr * math.sin(2 * math.pi * j / seg))) for j in range(seg)]))
    B.f(list(reversed(rows[0])), False)
    for ra, rb in zip(rows, rows[1:]):
        if len(rb) == 1:
            for j in range(seg):
                B.f((ra[j], ra[(j + 1) % seg], rb[0]), smooth)
        else:
            B.bridge(ra, rb, smooth=smooth)


def bolt(B, u, v, z, r=0.24, h=0.22):
    cyl(B, (u, v, z - 0.1), (u, v, z + h), r, r * 0.8, sides=6, smooth=False)


# ---------------------------------------------------------------- the ball eye ---------------
# rv / p: the front half (a plain ellipse into the sprite's narrow bottom rows); rvb / pb: the back
# half, squarer and longer, full width by row 19 where it meets the collar.
BALL = dict(cu=23.0, cv=22.5, cz=7.0, ru=3.0, rv=3.5, rvb=3.6, rz=3.8, p=2.5, pb=3.5)


def bexp(d):
    """The ball's superellipse exponent: squarer at the back where it meets the collar, a plain
    ellipse at the front, rounding in to the sprite's narrow bottom rows."""
    return BALL["pb"] if d < 0 else BALL["p"]


def brv(d):
    return BALL["rvb"] if d < 0 else BALL["rv"]


def bk(c, d):
    p = bexp(d)
    return 1 / (abs(c) ** p + abs(d) ** p) ** (1 / p)


def superball(B, scale=1.0, zlim=None, seg=24, rings=10):
    pts = []
    for i in range(rings + 1):
        th = math.pi * i / rings
        s = math.sin(th)
        row = []
        for j in range(seg):
            ph = 2 * math.pi * j / seg
            c, d = math.cos(ph), math.sin(ph)
            k = bk(c, d)
            row.append((BALL["cu"] + BALL["ru"] * scale * s * c * k, BALL["cv"] + brv(d) * scale * s * d * k,
                        BALL["cz"] + BALL["rz"] * scale * math.cos(th)))
        pts.append(row)
    top = B.vs([pts[0][0]])
    bot = B.vs([pts[-1][0]])
    rows = [B.vs(r) for r in pts[1:-1]]
    for j in range(seg):
        B.f((top[0], rows[0][(j + 1) % seg], rows[0][j]), True)
        B.f((bot[0], rows[-1][j], rows[-1][(j + 1) % seg]), True)
    for a, b in zip(rows, rows[1:]):
        B.bridge(a, b, smooth=True)


def ball_band(B, z0, z1, scale, seg=24):
    """A belt round the ball between heights z0 and z1 (a thin superellipse ring)."""
    def ring(z, sc):
        t = max(-1, min(1, (z - BALL["cz"]) / BALL["rz"]))
        s = math.sqrt(1 - t * t) * sc
        out = []
        for j in range(seg):
            ph = 2 * math.pi * j / seg
            c, d = math.cos(ph), math.sin(ph)
            k = bk(c, d)
            out.append((BALL["cu"] + BALL["ru"] * s * c * k, BALL["cv"] + brv(d) * s * d * k, z))
        return out
    a0, a1 = B.vs(ring(z0, scale)), B.vs(ring(z1, scale))
    b0, b1 = B.vs(ring(z0, 0.9)), B.vs(ring(z1, 0.9))
    B.bridge(a0, a1, smooth=True)
    B.bridge(a1, b1, smooth=False)
    B.bridge(b0, a0, smooth=False)
    B.bridge(b1, b0, smooth=True)


def ball_point(u, v):
    rv = brv(v - BALL["cv"])
    du, dv = (u - BALL["cu"]) / BALL["ru"], (v - BALL["cv"]) / rv

    def zf(a, b):
        pe = bexp(b)
        q = (abs(a) ** pe + abs(b) ** pe) ** (2 / pe)
        return BALL["cz"] + BALL["rz"] * math.sqrt(max(0, 1 - q))
    e = 1e-3
    gu = (zf(du + e / BALL["ru"], dv) - zf(du - e / BALL["ru"], dv)) / (2 * e)
    gv = (zf(du, dv + e / rv) - zf(du, dv - e / rv)) / (2 * e)
    # world: v grows to -y, so the normal's y is +gv
    return Vector((u, v, zf(du, dv))), Vector((-gu, -gv, 1)).normalized()


# ---------------------------------------------------------------- build -----------------------
def build_centre(B):
    # hull core: the armoured tub under everything (closed belly)
    B.part("hull_core", "steel")
    prism(B, rect(14.6, 1.0, 31.4, 10.0, 0.6), 5.1, 8.7, chamfer(0.3), [(0.5, 0), (0, 0.5)])
    # exhaust: vent box across the back, a louvred glow bay recessed between ribs, a dark grille deck
    B.part("vent_box", "steel")
    prism(B, rect(18.0, 1.0, 28.0, 2.4), 6.5, 9.8, chamfer(0.15))
    B.part("vent_glow", "glow_rear")
    prism(B, rect(20.0, 0.0, 27.0, 1.15), 6.9, 9.9)
    B.part("vent_core", "glow_core")
    prism(B, rect(21.5, -0.05, 25.5, 0.9), 7.3, 9.95)
    B.part("vent_rib", "steel")
    for k in range(5):
        u = 20.1 + k * 1.6
        prism(B, rect(u, -0.15, u + 0.35, 1.2), 6.6, 10.05, chamfer(0.08))
    prism(B, rect(20.0, -0.15, 27.0, 0.3), 6.4, 7.0)  # sill under the louvres
    for z in (7.75, 8.6, 9.4):  # horizontal guard bars across the glowing bay
        prism(B, rect(20.0, -0.2, 27.0, 0.05), z, z + 0.32, chamfer(0.06))
    B.part("vent_grille", "dark")
    prism(B, rect(18.9, 1.1, 27.1, 2.35), 9.0, 9.9)
    for k in range(6):
        u = 19.4 + k * 1.4
        prism(B, rect(u, 1.2, u + 0.32, 2.25), 9.5, 10.02)
    # screen: a frame block, a raised lip round a two-facet visor (flat upper pane, lower pane
    # angled down to the front, the sprite's darker band), a light sensor strip on the front lip
    B.part("screen_frame", "frame")
    prism(B, rect(18.0, 2.0, 28.0, 8.2, 0.5), 6.1, 10.25, chamfer(0.3))
    ring_prism(B, rect(18.75, 2.1, 27.25, 7.75, 0.8), rect(19.45, 2.5, 26.55, 7.05, 0.55), 10.0, 10.75)
    B.part("screen_glass", "glass")
    prism(B, [(19.45, 2.5), (26.55, 2.5), (26.55, 5.95), (19.45, 5.95)], 9.9,
          lambda u, v: 11.0 - 0.04 * (v - 2.5), chamfer(0.25))
    B.part("screen_glass_lo", "glass_lo")
    prism(B, [(19.45, 5.95), (26.55, 5.95), (26.55, 7.05), (19.45, 7.05)], 9.9,
          lambda u, v: 10.86 - 0.5 * (v - 5.95), [(0, 0.12), (0.15, 0)])
    B.part("screen_rim", "rim")
    prism(B, rect(19.9, 7.15, 26.1, 7.8), 10.2, 10.85, chamfer(0.12))
    # glacis: sloped armour in front of the screen with a panel line and rivets
    B.part("glacis", "steel")
    gl = [(15.2, 7.4), (30.8, 7.4), (30.8, 9.4), (30.0, 10.2), (16.0, 10.2), (15.2, 9.4)]
    gtop = lambda u, v: 10.1 - 0.45 * (v - 7.4)  # noqa: E731
    prism(B, gl, 5.9, gtop, chamfer(0.22), groove=(0.45, 0.16, 0.12))
    B.part("glacis_bolts", "steel")
    for u in (16.0, 30.0):
        for v in (8.0, 9.6):
            bolt(B, u, v, gtop(u, v) - 0.05, r=0.2)
    # chin: dark block under the glacis with red-lit louvred vent blocks either side of the stem
    B.part("chin", "dark")
    prism(B, [(19.6, 9.6), (26.4, 9.6), (26.9, 10.1), (26.9, 13.6), (26.5, 14.0), (25.0, 14.0), (24.85, 14.9),
              (21.15, 14.9), (21.0, 14.0), (19.5, 14.0), (19.1, 13.6), (19.1, 10.1)], 4.5, 7.9, chamfer(0.25), [(0.3, 0), (0, 0.3)])
    # eye stem: neck, armoured sleeve with two clamps, cables either side
    B.part("pipe_neck", "frame")
    cyl(B, (23, 9.8, 8.1), (23, 14.2, 8.0), 0.85, sides=12)
    B.part("pipe_sleeve", "clamp")
    cyl(B, (23, 13.9, 7.8), (23, 18.6, 7.8), 1.1, 1.15, sides=14, bev=0.15)
    B.part("pipe_clamp", "clamp")
    for v, r in ((14.15, 1.8), (17.25, 1.3)):
        cyl(B, (23, v, 7.8), (23, v + 0.6, 7.8), r, sides=10, bev=0.12)
    B.part("ball_collar", "collar")
    cyl(B, (23, 18.0, 7.8), (23, 19.4, 7.9), 1.95, 2.6, sides=16, bev=0.15)
    # the eye housing
    B.part("ball", "frame")
    superball(B)
    B.part("ball_band", "steel")
    ball_band(B, 5.9, 6.6, 1.025)
    p, n = ball_point(23.0, 21.0)
    B.part("lens_bezel", "steel")
    # bezel: a ring standing proud of the ball round the lens
    nn, a, b = basis(n)
    sides = 20

    def ring(c, r):
        return B.vs([tuple(c + a * (r * math.cos(2 * math.pi * i / sides)) + b * (r * math.sin(2 * math.pi * i / sides)))
                     for i in range(sides)])
    c0, c1 = p - nn * 0.6, p + nn * 0.45
    o0, o1, i1, i0 = ring(c0, 2.3), ring(c1, 2.2), ring(c1, 1.9), ring(c0 + nn * 0.2, 1.9)
    B.bridge(o0, o1, smooth=True)
    B.bridge(o1, i1, smooth=False)
    B.bridge(i1, i0, smooth=True)
    B.bridge(i0, o0, smooth=False)
    B.part("lens", "lens")
    dome(B, p + nn * 0.0, n, 1.95, 0.5, seg=18, rings=4)
    B.part("lens_core", "lens_core")
    dome(B, p + nn * 0.25, n, 1.05, 0.38, seg=14, rings=3)
    # bolts round the ball's flanks (seen from the sides and the game camera)
    B.part("ball_bolts", "steel")
    for ang in (35, 145, 215, 325):
        t = math.radians(ang)
        q, m = ball_point(23 + 2.7 * math.cos(t), 22.5 + 3.0 * math.sin(t))
        cyl(B, tuple(q - m * 0.1), tuple(q + m * 0.25), 0.28, 0.22, sides=6, smooth=False)


# The legs' heights (sprite px): the strut's top and the outer claw's top, both level (D163).
LEG_TS = 6.0
LEG_TC = 5.5
# Their sides lean in to this fraction of the top's width at the ground, so near the screen's sides
# the camera sees less of the side walls (a box leg read as a wide slab there).
LEG_KEEL = 0.55


def build_side(B, right):
    """Left-side parts (u < 23); with right=True the same mirrored, except where the sprite differs."""
    B.mirror = right
    # armoured housing beside the screen: a rounded-top block (the sprite shades it as a cylinder)
    B.part("housing_L", "house", "L")
    prism(B, [(15.0, 0.0), (17.85, 0.0), (18.2, 0.35), (18.2, 7.05), (17.75, 7.5), (14.45, 7.5), (14.0, 7.05),
              (14.0, 1.3)], 5.9, 11.1, fillet(1.0, 3), [(0.3, 0), (0, 0.3)],
          groove=(0.3, 0.14, 0.1))
    B.part("housing_hatch_L", "bright", "L")
    prism(B, rect(14.9, 0.7, 17.3, 3.2, 0.3), 10.6, 11.35, chamfer(0.15))
    B.part("housing_port_L", "dark", "L")
    prism(B, [(15.2, -0.06), (17.5, -0.06), (17.5, 0.1), (15.2, 0.1)], 6.6, 9.4)  # rear exhaust slot face
    B.part("housing_port_glow_L", "glow_vent", "L")
    prism(B, [(15.4, -0.1), (17.2, -0.1), (17.2, 0.0), (15.4, 0.0)], 7.0, 7.6)
    # red thruster pod; a hot intake grille across its top rear, a glowing slit strip down its outer
    # top edge, a dark cap at the back with a deep glowing nozzle
    B.part("pod_L", "pod", "L")
    prism(B, [(11.3, 2.0), (13.6, 2.0), (14.0, 2.4), (14.0, 8.0), (13.6, 8.4), (10.4, 8.4), (10.0, 8.0), (10.0, 3.3)],
          6.1, 10.5, fillet(0.55, 2), [(0.3, 0), (0, 0.3)])
    B.part("pod_intake_L", "glow_lamp", "L")
    prism(B, rect(11.25, 2.05, 13.6, 4.0, 0.2), 9.8, 10.55)
    B.part("pod_intake_slat_L", "pod_dk", "L")
    for v in (2.6, 3.3):
        prism(B, rect(11.15, v, 13.7, v + 0.22), 10.2, 10.7, chamfer(0.05))
    B.part("pod_slit_L", "glow_lamp", "L")
    prism(B, rect(10.3, 4.0, 11.5, 7.2), 9.9, 10.5)
    B.part("pod_rib_L", "pod_dk", "L")
    for k in range(3):
        v = 4.5 + k * 0.95
        prism(B, rect(10.2, v, 11.6, v + 0.26), 9.9, 10.62, chamfer(0.05))
    B.part("pod_cap_L", "dark", "L")
    prism(B, rect(11.4, 1.85, 13.85, 2.3, 0.2), 7.3, 9.7, chamfer(0.15))
    B.part("pod_nozzle_L", "steel", "L")
    floor = tube(B, (12.6, 2.4, 8.5), (12.6, 1.8, 8.5), 0.9, 0.64, 0.4, sides=12)
    B.part("pod_nozzle_glow_L", "glow_hot", "L")
    cyl(B, tuple(floor + Vector((0, 0.05, 0))), tuple(floor + Vector((0, -0.08, 0))), 0.66, sides=12)
    # the bright blue T arm: tab into the housing, bar over the pod, blade down to the gun
    du = 1.0 if right else 0.0  # the sprite's right tab sits one column further in (mirrored: out)
    T = [(13.0 + du, 4.9), (17.0 + du, 4.9), (17.0 + du, 7.0), (16.0, 7.0), (16.0, 10.1), (16.0, 12.6), (15.05, 13.1), (15.05, 14.3),
         (12.95, 14.3), (12.95, 13.1), (12.0, 12.6), (12.0, 10.1), (10.4, 10.1), (10.0, 9.7), (10.0, 7.3), (10.4, 6.9), (13.0 + du, 6.9)]
    atop = lambda u, v: 12.1 if v < 10.1 else 12.1 - 0.11 * (v - 10.1)  # noqa: E731
    B.part("arm_L", "arm", "L")
    prism(B, T, 10.4, atop, [(0, 0.38), (0.22, 0.1), (0.36, 0)], [(0.2, 0), (0, 0.2)], groove=(0.38, 0.13, 0.1))
    B.part("arm_bolts_L", "arm", "L")
    for u, v in ((10.9, 7.6), (10.9, 9.4), (14.0 + du, 5.6), (16.0 + du, 5.6), (14.0, 12.2)):
        bolt(B, u, v, atop(u, v) - 0.05, r=0.21)
    # gun: a muzzle block under the blade's front with a barrel and a deep bore facing the front
    B.part("muzzle_L", "muzzle", "L")
    prism(B, [(12.95, 12.4), (15.05, 12.4), (15.05, 16.6), (14.85, 16.95), (13.85, 16.95), (13.65, 16.6),
              (13.65, 16.05), (13.15, 16.05), (12.95, 15.85)], 9.4,
          lambda u, v: 11.6 - 0.12 * (v - 13.9), chamfer(0.3), [(0.2, 0), (0, 0.2)])
    B.part("barrel_L", "muzzle", "L")
    tube(B, (14.35, 15.6, 10.2), (14.35, 16.95, 10.2), 0.62, 0.38, 0.7, sides=10)
    B.part("bore_L", "bore", "L")
    cyl(B, (14.35, 16.1, 10.2), (14.35, 16.3, 10.2), 0.39, sides=10)
    # red-lit chin vent beside the stem: louvred top, glowing grille in its front face
    B.part("chin_vent_L", "pod_dk", "L")
    prism(B, rect(19.7, 10.6, 21.2, 13.9, 0.2), 5.1, 8.25, chamfer(0.15))
    for k in range(4):
        v = 11.0 + k * 0.75
        prism(B, rect(19.8, v, 21.1, v + 0.3), 8.0, 8.42, chamfer(0.06))
    B.part("chin_vent_glow_L", "glow_vent", "L")
    prism(B, rect(19.9, 13.85, 21.0, 14.02), 5.5, 7.7)
    B.part("chin_vent_bar_L", "pod_dk", "L")
    for z in (6.1, 6.9):
        prism(B, rect(19.8, 13.8, 21.1, 14.1), z, z + 0.25)
    # under the arm: a lamp in a dark socket, a grille box with a knob, a hydraulic plate
    B.part("lamp_box_L", "dark", "L")
    prism(B, [(10.3, 9.9), (12.7, 9.9), (13.0, 10.2), (13.0, 11.7), (12.7, 12.0), (11.0, 12.0), (11.0, 12.95),
              (10.0, 12.95), (10.0, 10.2)], 6.9, 9.1, chamfer(0.25))
    B.part("lamp_L", "glow_lamp", "L")
    dome(B, (11.5, 11.2, 9.0), (0, -0.35, 1), 0.7, 0.4, seg=12, rings=2)
    B.part("grille_box_L", "steel", "L")
    prism(B, rect(15.0, 9.9, 18.0, 12.0, 0.3), 6.7, 8.7, chamfer(0.2))
    for k in range(3):
        v = 10.3 + k * 0.55
        prism(B, rect(15.3, v, 17.7, v + 0.22), 8.4, 8.85)
    B.part("knob_L", "knob", "L")
    cyl(B, (16.5, 11.0, 8.6), (16.5, 11.0, 9.15), 0.5, 0.42, sides=10, smooth=False)
    B.part("ram_plate_L", "ram", "L")
    prism(B, rect(18.0, 9.9, 19.1, 13.0), 5.5, 8.5, chamfer(0.15))
    # leg: hip, inner strut down to the foot, outer claw + armour plate, knee, lower claw.
    # Each member is level along its length and stands on the ground (a closed box down to z = 0):
    # under the tilted, off-axis game camera a part's height shifts it sideways on screen, so a leg
    # whose top fell from a high knee to the toe leaned out at the knee by up to ~5 px near the
    # screen's sides and read as a splayed fork where the sprite's prongs are straight (D163). A
    # level top shifts as one piece and stays straight; the plan (u, v and widths) is the sprite's.
    B.part("hip_L", "frame", "L")
    cyl(B, (8.0, 6.4, LEG_TS - 1.5), (10.9, 6.4, LEG_TS - 1.5), 1.25, sides=8, bev=0.2)
    B.part("strut_L", "strut", "L")
    # the inner shin strut (narrowed to end at u = 10 where it passes under the arm bar, which the
    # sprite shows on top)
    sweep(B, [(u, v, LEG_TS / 2, w, LEG_TS) for u, v, w in
              ((9.6, 4.0, 3.0), (9.5, 5.3, 3.0), (9.0, 6.8, 2.0), (8.6, 9.6, 2.8), (8.6, 10.6, 2.8),
               (8.4, 13.5, 3.0), (8.3, 17.3, 3.0), (7.9, 20.4, 2.8))], ch=0.45, steps=9, keel=LEG_KEEL)
    B.part("strut_spine_L", "leg", "L")  # raised spine plate over the strut top (the sprite's blue)
    sweep(B, [(u, v, LEG_TS + 0.2, w, 0.5) for u, v, w in
              ((9.55, 4.4, 2.4), (9.45, 5.5, 2.5), (9.0, 6.8, 1.6), (8.6, 9.6, 2.3), (8.6, 10.6, 2.3),
               (8.4, 13.5, 2.5), (8.3, 17.3, 2.5), (7.95, 20.0, 2.2))], ch=0.15, steps=8)
    B.part("strut_ram_L", "steel", "L")
    cyl(B, (8.6, 6.0, LEG_TS - 1.0), (8.3, 15.5, LEG_TS - 1.0), 0.42, sides=8)  # hydraulic ram body -> shin
    cyl(B, (8.6, 5.6, LEG_TS - 1.0), (8.6, 10.0, LEG_TS - 1.0), 0.6, sides=8, bev=0.08)
    claw = lambda st: [(u, v, LEG_TC / 2, w, LEG_TC) for u, v, w in st]  # noqa: E731
    toe = lambda st: [(u, v, z / 2, w, z) for u, v, w, z in st]  # noqa: E731
    if not right:
        B.part("claw_upper_L", "claw", "L")
        sweep(B, claw(((6.4, 9.0, 1.8), (6.3, 10.0, 1.6), (6.3, 13.5, 1.6), (6.2, 17.6, 1.6))), ch=0.3, steps=6,
              keel=LEG_KEEL)
        B.part("claw_plate_L", "plate", "L")
        sweep(B, [(u, v, (LEG_TC - 0.5) / 2, w, LEG_TC - 0.5) for u, v, w in
                  ((6.0, 9.0, 1.0), (5.6, 9.6, 1.2), (5.6, 10.4, 1.2), (5.6, 13.5, 1.2), (5.8, 17.95, 1.2))],
              ch=0.3, steps=6, keel=LEG_KEEL)
        B.part("knee_L", "steel", "L")  # a hinge across the claw's top
        cyl(B, (5.6, 17.5, LEG_TC), (7.6, 17.5, LEG_TC), 0.85, sides=8, bev=0.15)
        B.part("claw_lower_L", "claw_lo", "L")
        sweep(B, toe(((6.5, 17.5, 1.4, LEG_TC), (6.6, 21.0, 1.2, LEG_TC), (6.6, 23.0, 1.2, LEG_TC),
                      (7.3, 24.2, 1.0, LEG_TC - 0.4), (7.8, 24.85, 0.9, LEG_TC - 1.2))), ch=0.3, steps=5,
              keel=LEG_KEEL)
    else:
        B.mirror = False  # right outer claw: one narrower member, as the sprite's column 39
        B.part("claw_upper_R", "claw", "R")
        sweep(B, claw(((39.5, 9.0, 1.0), (39.5, 10.0, 1.05), (39.5, 13.5, 1.05), (39.5, 17.6, 1.0))), ch=0.22, steps=6,
              keel=LEG_KEEL)
        B.part("knee_R", "steel", "R")
        cyl(B, (38.0, 17.5, LEG_TC), (39.3, 17.5, LEG_TC), 0.85, sides=8, bev=0.15)
        B.part("claw_lower_R", "claw_lo", "R")
        sweep(B, toe(((38.9, 17.5, 1.0, LEG_TC), (39.4, 19.0, 1.0, LEG_TC), (39.4, 21.5, 1.0, LEG_TC),
                      (38.9, 23.5, 1.0, LEG_TC - 0.4), (38.5, 24.8, 1.0, LEG_TC - 1.2))), ch=0.2, steps=5,
              keel=LEG_KEEL)
        B.mirror = True
    B.part("ankle_L", "ankle", "L")  # pin where the strut meets the foot
    cyl(B, (7.0, 20.5, 2.3), (9.6, 20.5, 2.3), 0.55, sides=8, bev=0.12)
    B.part("foot_L", "leg", "L")
    prism(B, [(6.2, 20.0), (9.8, 20.0), (9.8, 20.8), (9.0, 21.3), (9.0, 24.6), (8.7, 25.0), (7.3, 25.0), (7.0, 24.7),
              (7.0, 24.1), (6.2, 23.9)], 0.0,
          lambda u, v: 2.2 - 0.25 * (v - 20.0), chamfer(0.35), [(0.15, 0), (0, 0.15)], groove=(0.3, 0.12, 0.08))
    B.mirror = False


def build(sprite, coll):
    B = Builder()
    build_centre(B)
    build_side(B, False)
    build_side(B, True)
    bm = B.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    for m in make_materials(sprite):
        mesh.materials.append(m)
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj, B.parts


# ---------------------------------------------------------------- export ----------------------
def split_shell(shell, layout, coll):
    """Cut the whole machine's outline shell into the pieces as split_assembly cuts the model, each
    cut capped so a piece's shell is closed on its own (in ?viewer one piece at a time) while the
    two pieces' outer surfaces still meet exactly at the seam (no step in the outline in game)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(shell.data)
        bmesh.ops.transform(bm, matrix=shell.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            cut = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                         plane_no=no, clear_outer=True)
            edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if edges:
                bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + "_outline")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(shell.data.materials[0])
        me.shade_smooth()
        o = bpy.data.objects.new(name + "_outline", me)
        coll.objects.link(o)
        o["tyrian_outline"] = True
        out[name] = o
    return out


def open_edges(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    n = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return n


# ---------------------------------------------------------------- views -----------------------
def setup_ids(obj, parts):
    """Corner colour attribute: R = part id, G = palette index (sRGB bytes), for the index render."""
    me = obj.data
    pid = me.attributes["part"].data
    attr = me.color_attributes.new("ids", "FLOAT_COLOR", "CORNER")

    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    for poly in me.polygons:
        k = pid[poly.index].value
        pal = MATS[parts[k][1]][0]
        col = (lin(2 * (k + 1)), lin(pal), 0.0, 1.0)
        for li in poly.loop_indices:
            attr.data[li].color = col
    me.color_attributes.active_color = attr


def camera(scene, name, rot_deg, loc, ortho=4.4):
    data = bpy.data.cameras.new(name)
    data.type = "ORTHO"
    data.ortho_scale = ortho
    data.clip_end = 200
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.rotation_euler = [math.radians(a) for a in rot_deg]
    cam.location = loc
    return cam


def look_cam(scene, name, rot_deg, dist=20, target=(0, 0, 0.45), ortho=4.4):
    from mathutils import Euler
    e = Euler([math.radians(a) for a in rot_deg])
    d = Vector((0, 0, -1))
    d.rotate(e)
    loc = Vector(target) - d * dist
    return camera(scene, name, rot_deg, loc, ortho)


def render_views(obj, parts, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    # 1. index render (top ortho, 20 px per sprite px, no AA)
    setup_ids(obj, parts)
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    sh = scene.display.shading
    sh.light = "FLAT"
    try:
        sh.color_type = "VERTEX"
    except TypeError as err:
        print("color types", err)
        sh.color_type = "ATTRIBUTE"
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 960, 560
    scene.render.resolution_percentage = 100
    top = camera(scene, "top", (0, 0, 0), (0, 0, 10), ortho=4.0)
    scene.camera = top
    scene.render.filepath = str(out_dir / "top_ids.png")
    bpy.ops.render.render(write_still=True)
    if "--top-only" in argv:
        return
    # 2. beauty renders (Cycles)
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        scene.cycles.device = "GPU"
    except Exception as err:
        print("no gpu", err)
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.32, 0.36, 0.42, 1)
    bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    sun.data.angle = math.radians(8)
    sun.rotation_euler = (math.radians(38), math.radians(-22), math.radians(-30))
    scene.collection.objects.link(sun)
    # ground plane for context in side views
    gp = bpy.data.meshes.new("ground")
    gbm = bmesh.new()
    for x, y in ((-6, -6), (6, -6), (6, 6), (-6, 6)):
        gbm.verts.new((x, y, -0.002))
    gbm.faces.new(gbm.verts)
    gbm.to_mesh(gp)
    gbm.free()
    gmat = bpy.data.materials.new("groundmat")
    gmat.use_nodes = True
    gb = next(n for n in gmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    gb.inputs["Base Color"].default_value = (0.06, 0.07, 0.08, 1)
    gb.inputs["Roughness"].default_value = 0.9
    gp.materials.append(gmat)
    ground = bpy.data.objects.new("ground", gp)
    scene.collection.objects.link(ground)
    views = {
        "top": ((0, 0, 0), 960, 560, 4.0),
        "game": ((32, 0, 0), 960, 640, 4.2),
        "side": ((90, 0, -90), 960, 420, 3.6),
        "side_r": ((90, 0, 90), 960, 420, 3.6),
        "front": ((90, 0, 0), 960, 420, 4.0),
        "rear": ((90, 0, 180), 960, 420, 4.0),
        "q_fl": ((55, 0, -45), 960, 720, 4.6),
        "q_rr": ((55, 0, 135), 960, 720, 4.6),
        "q_fr_low": ((75, 0, 40), 960, 600, 4.6),
        "under": ((180, 0, 0), 960, 560, 4.0),
    }
    for name, (rot, w, h, osc) in views.items():
        ground.hide_render = name in ("top", "under", "game")
        cam = look_cam(scene, "cam_" + name, rot, ortho=osc)
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = w, h
        scene.render.filepath = str(out_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    # the game camera at game size (about 3 screen px per sprite px), for readability
    ground.hide_render = True
    cam = look_cam(scene, "cam_game_small", (32, 0, 0), ortho=4.2)
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = 200, 133
    scene.render.filepath = str(out_dir / "game_small.png")
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- AO / roughness bake ---------
NO_BAKE = {"glass", "glass_lo", "rim", "lens", "lens_core"} | {k for k, m in MATS.items() if m[3]}


def bake_maps(obj, out_dir, size=1024, samples=64):
    """As the ships (#84): Smart UV, bake a grey colour multiplier (occlusion at two scales plus a
    lift on bevelled edges) and a roughness/metalness map, then Base Color = map x palette colour.
    No concept projection."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
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
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new("nsh2_87_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("nsh2_87_rm", size // 2, size // 2, alpha=False)
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

        def mth(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    L(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.14
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.004
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = mth("MINIMUM", mth("MULTIPLY", mth("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = mth("MULTIPLY", mth("POWER", ao_s.outputs["AO"], 0.8),
                   mth("ADD", 0.65, mth("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        comb = node("ShaderNodeCombineColor")
        if mode == "colour":
            v = mth("MINIMUM", mth("ADD", mth("ADD", 0.48, mth("MULTIPLY", occl, 0.62)), mth("MULTIPLY", edge, 0.2)), 1.0)
            for k in range(3):
                L(v, comb.inputs[k])
        else:
            r = mth("ADD", rough, mth("SUBTRACT", mth("MULTIPLY", mth("SUBTRACT", 1.0, occl), 0.3),
                                      mth("MULTIPLY", edge, 0.16)))
            r = mth("MAXIMUM", mth("MINIMUM", r, 1.0), 0.05)
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
    for key, m in zip(MKEYS, mats):
        if key in NO_BAKE:
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
    root = ROOT
    # Nothing else in the scene (the startup cube would shadow the occlusion bake and the views).
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sprite = lib.merged_sprite(root, PIECES)
    coll = common.reset_collection(NAME)
    obj, parts = build(sprite, coll)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} tris")
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    if views:
        views.mkdir(parents=True, exist_ok=True)
        json.dump({"parts": [{"id": i + 1, "name": n, "mat": mk, "pal": MATS[mk][0], "side": s}
                             for i, (n, mk, s) in enumerate(parts)], "tris": tris,
                   "max_z_px": max(v.co.z for v in obj.data.vertices) * 12},
                  open(views / "parts.json", "w"), indent=1)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="nsh2_87_bake_"))
        fmt = "WEBP"
    # The outline shell (D51) of the whole machine, made after the bake so occlusion never sees it,
    # then cut into the pieces with them.
    shell = common.outline_shell(obj, coll, faces=1800)
    shell.hide_render = True
    pieces = common.split_assembly(obj, layout)
    shells = split_shell(shell, layout, coll)
    for name in PIECES:
        p, s = pieces[name], shells[name]
        s.hide_render = True
        print(f"piece {name}: {sum(len(q.vertices) - 2 for q in p.data.polygons)} tris, shell "
              f"{len(s.data.polygons)} faces, shell open edges {open_edges(s)}")
        data = common.load_sprite(root, name)
        common.export_sprite_model(root, [p, s], f"enemies/{name}", data["sprites"], image_format=fmt)
    if "--out" in argv:
        # Both pieces placed as in the layout (node translation = piece centre), for review.
        objs = []
        for name, cx, cy in layout:
            for o in (pieces[name], shells[name]):
                o.location = (cx * PX, -cy * PX, 0.0)
                objs.append(o)
        common.export_glb(objs, argv[argv.index("--out") + 1], image_format=fmt)
        for o in objs:
            o.location = (0.0, 0.0, 0.0)
        print("exported", argv[argv.index("--out") + 1])
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        for o in pieces.values():
            o.hide_render = True
        ref = lib.composite_png(root, layout, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56)
        common.render_preview([obj], str(out), str(ref), size=4, view_px=480)
        for name in PIECES:
            data = common.load_sprite(root, name)
            img = root / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
    if views:
        for o in list(pieces.values()) + list(shells.values()) + [shell]:
            o.hide_render = True
        obj.hide_render = False
        render_views(obj, parts, views)


if __name__ == "__main__":
    main()
