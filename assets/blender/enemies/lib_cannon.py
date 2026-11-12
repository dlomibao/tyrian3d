"""The grey jungle gun emplacement of episode 2 (assembly-newshg-231 and its mirror image
assembly-newshg-267): newshg-229 | newshg-231, or mirrored newshg-267 | newshg-269, 48 x 28 px, a 3D
version of the sprites. build_cannon / cannon_main are called by the two wrapper scripts (the old
builder lived in lib_b077; it was replaced here, lib_b077's other helpers are unchanged).

WHAT IT IS: a fixed heavy gun lying in the jungle grass (types 753/754 and 756/757: mv 0, armour 20,
no link moves; 754 and 756 launch the newshj-19 fireball every 50 ticks). Read from the tilted game
camera, in order of mass:
  1. one long round steel BARREL (rows 1-7) on two cradles, bending at its left end through a
     lobster-back ELBOW (three mitred segments) down the screen into a capped leg on a saddle block;
  2. a machined SIGHT HOUSING on the barrel: scope lens + sliding hatch (frames: shut / slid / open),
     four corner bolts;
  3. at the right, a narrow drive SHAFT through a big COLLAR disc into an END BOX with louvres;
  4. a low armoured DECK along the front with five cooling FINS, running lamps on their tips and a
     glowing breech PORT at the seam;
  5. a hydraulic STRUT (cylinder + rod) down from the collar to a foot pad, a slim brace beside it,
     and the EXHAUST NOZZLE (the launcher): a flattened shroud with a smooth glowing insert and a
     hot core, aimed down-screen right; on the last frame its glow streaks down the strut.
The jungle grass is ground (D130): no floor plate, the machine stands on the HD ground at z = 0.

The machine is built whole in assembly coordinates (sprite px: x right, y down the screen, z up;
Blender X = (x - 24) / 12, Y = (14 - y) / 12, Z = z / 12), mirrored for 267|269 (x -> -x, then 1 px
left, where those sprites draw it), the D51 outline shell is made from a sealed copy (D90, D118),
and everything is cut into the two pieces with common.split_assembly (the shell is cut open, so
no ink along the seam). Frames k = 0, 1, 2 are each piece's own sprite frames in order. No baked
textures (no concept projection, D65); palette materials pal_<index> per region.
"""

import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

import common  # noqa: E402

ZC = 4.4    # barrel axis height (px)
RT = 3.45   # barrel radius
TY = 4.5    # barrel axis row
K = 3       # frames per piece
UNIT = 1 / 12

# state of the build in progress (reset by build_cannon)
NAME = ""
SPR = {}
MATS = []
ANIM = {}   # slot -> (palette index, metallic, roughness, emit, tag, {k: palette index})
MIRROR = False


def P(x, y, z):
    return Vector(((x - 24) / 12, (14 - y) / 12, z / 12))


def mat(index, metallic=0.55, roughness=0.42, emit=0.0, frames=None, tag=""):
    """Slot of pal_<index>. `frames`: {k: palette index} animates it (per piece, at export)."""
    t = f"{NAME}B{tag}" if not frames else f"{NAME}B-{tag}"
    m = common.palette_material(SPR, index, t, metallic=metallic, roughness=roughness, emission_strength=emit)
    if m not in MATS:
        MATS.append(m)
    slot = MATS.index(m)
    if frames:
        ANIM[slot] = (index, metallic, roughness, emit, tag, dict(frames))
    return slot


# ---------------------------------------------------------------------------------------------
# Geometry helpers (px space)
# ---------------------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(P(*p))

    def face(self, vs, m, smooth=False):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = m
        f.smooth = smooth
        return f


def _rot_between(a, b):
    a = a.normalized()
    b = b.normalized()
    c = a.cross(b)
    s = c.length
    d = max(-1.0, min(1.0, a.dot(b)))
    if s < 1e-9:
        return Matrix.Identity(3)
    return Matrix.Rotation(math.atan2(s, d), 3, c / s)


def _ring_faces(M, r0, r1, m, smooth):
    n = len(r0)
    for i in range(n):
        j = (i + 1) % n
        M.face([r0[i], r0[j], r1[j], r1[i]], m, smooth)


def tube(M, pts, radii, m, sides=16, cap0="flat", cap1="flat", ch=0.22, sz=1.0, mats=None,
         cap_len=1.0, up=(0, 0, 1), smooth=True):
    """Swept tube along a polyline with exact mitre joints (lobster-back) and chamfered or domed
    caps. pts: (x, y, z) px; radii per point; mats: per-segment material slots."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    d = [(pts[i + 1] - pts[i]).normalized() for i in range(n - 1)]
    u = Vector(up)
    u = (u - d[0] * u.dot(d[0]))
    if u.length < 1e-6:
        u = Vector((0, 1, 0)) - d[0] * d[0].y
    u.normalize()
    bases = []
    cu = u
    for i in range(n - 1):
        if i > 0:
            cu = (_rot_between(d[i - 1], d[i]) @ cu).normalized()
        bases.append((cu, d[i].cross(cu).normalized()))

    def circle(c, r, uu, vv):
        out = []
        for s in range(sides):
            a = 2 * math.pi * s / sides
            w = uu * math.cos(a) * r + vv * math.sin(a) * r
            w.z *= sz
            out.append(c + w)
        return out

    rings = []  # (points, seg index for material of the faces AFTER this ring)
    for i in range(n):
        r = radii[i]
        if i == 0:
            uu, vv = bases[0]
            rings.append(circle(pts[0], r, uu, vv))
        elif i == n - 1:
            uu, vv = bases[-1]
            rings.append(circle(pts[-1], r, uu, vv))
        else:
            uu, vv = bases[i - 1]
            nrm = (d[i - 1] + d[i]).normalized()
            ring = []
            for q in circle(pts[i], r, uu, vv):
                t = -(q - pts[i]).dot(nrm) / d[i - 1].dot(nrm)
                ring.append(q + d[i - 1] * t)
            rings.append(ring)
    segm = mats or [m] * (n - 1)
    vr = [[M.v(tuple(q)) for q in ring] for ring in rings]

    def cap(end, kind):
        idx = 0 if end == 0 else n - 1
        dd = -d[0] if end == 0 else d[-1]
        uu, vv = bases[0] if end == 0 else bases[-1]
        r = radii[idx]
        c = pts[idx]
        mm = segm[0] if end == 0 else segm[-1]
        base = vr[idx]
        if kind == "dome":
            prev = base
            steps = 4
            for s in range(1, steps):
                a = (math.pi / 2) * s / steps
                ring = [M.v(tuple(q)) for q in circle(c + dd * cap_len * math.sin(a), r * math.cos(a), uu, vv)]
                _ring_faces(M, prev, ring, mm, True) if end == 1 else _ring_faces(M, ring, prev, mm, True)
                prev = ring
            tip = M.v(tuple(c + dd * cap_len))
            for s in range(sides):
                M.face([prev[s], prev[(s + 1) % sides], tip], mm, True)
        else:
            c2 = ch if kind == "flat" else 0.0
            if c2 > 0:
                ring = [M.v(tuple(q)) for q in circle(c + dd * c2, max(0.05, r - c2), uu, vv)]
                _ring_faces(M, base, ring, mm, False)
                M.face(ring, mm, False)
            else:
                M.face(base, mm, False)

    for i in range(n - 1):
        _ring_faces(M, vr[i], vr[i + 1], segm[i], smooth)
    cap(0, cap0)
    cap(1, cap1)


def _inset(poly, c):
    """Mitre-offset a simple polygon inward by c."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x)) * sgn
        n1 = Vector((-e1.y, e1.x)) * sgn
        b = n0 + n1
        if b.length < 1e-6:
            b = n0
        b.normalize()
        k = c / max(0.3, b.dot(n0))
        q = p1 + b * k
        out.append((q.x, q.y))
    return out


def zprism(M, poly, z0, z1, m, c=0.25, top_m=None):
    """Vertical extrusion of a plan polygon with a chamfered top edge."""
    tm = m if top_m is None else top_m
    c = min(c, (z1 - z0) * 0.45)
    b = [M.v((x, y, z0)) for x, y in poly]
    s = [M.v((x, y, z1 - c)) for x, y in poly]
    t = [M.v((x, y, z1)) for x, y in _inset(poly, c)] if c > 0 else None
    _ring_faces(M, b, s, m, False)
    if t:
        _ring_faces(M, s, t, tm, False)
        M.face(t, tm, False)
    else:
        M.face(s, tm, False)
    M.face(list(reversed(b)), m, False)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def xprism(M, prof, x0, x1, m, c=0.2):
    """Extrusion along x of a (y, z) profile, chamfered at both ends."""
    ins = _inset(prof, c)
    rings = [(x0, ins), (x0 + c, prof), (x1 - c, prof), (x1, ins)]
    vr = [[M.v((x, y, z)) for y, z in pr] for x, pr in rings]
    for i in range(3):
        _ring_faces(M, vr[i], vr[i + 1], m, False)
    M.face(vr[0], m, False)
    M.face(list(reversed(vr[3])), m, False)


def dome(M, c, r, m, rings=5, sides=16):
    c = Vector(c)
    prev = None
    for i in range(rings + 1):
        a = (math.pi / 2) * i / rings
        if i == rings:
            tip = M.v((c.x, c.y, c.z + r[2]))
            for s in range(sides):
                M.face([prev[s], prev[(s + 1) % sides], tip], m, True)
            break
        ring = [M.v((c.x + r[0] * math.cos(a) * math.cos(2 * math.pi * s / sides),
                     c.y + r[1] * math.cos(a) * math.sin(2 * math.pi * s / sides),
                     c.z + r[2] * math.sin(a))) for s in range(sides)]
        if prev is None:
            M.face(list(reversed(ring)), m, False)
        else:
            _ring_faces(M, prev, ring, m, True)
        prev = ring


def to_object(M, name, coll):
    bm = M.bm
    if MIRROR:  # x -> -x, then 1 px left (where newshg-267|269 draw it)
        for v in bm.verts:
            v.co.x = -v.co.x - UNIT
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # hard edges between flat and smooth faces
    for e in bm.edges:
        fs = e.link_faces
        if len(fs) == 2 and (fs[0].smooth != fs[1].smooth or not fs[0].smooth):
            e.smooth = False
        if len(fs) == 2 and fs[0].smooth and fs[1].smooth:
            if fs[0].normal.angle(fs[1].normal, 0) > math.radians(40):
                e.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mm in MATS:
        me.materials.append(mm)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


# ---------------------------------------------------------------------------------------------
# The machine
# ---------------------------------------------------------------------------------------------



# ---------------------------------------------------------------------------------------------
# The machine
# ---------------------------------------------------------------------------------------------

def build(coll):
    """The whole gun in assembly coordinates: (body, [(part object, [k, ...])])."""
    TUBE = mat(7, 0.65, 0.34)
    LEG = mat(5, 0.6, 0.4)
    FLANGE = mat(11, 0.7, 0.3)
    RIM = mat(5, 0.65, 0.35)
    DARK = mat(3, 0.5, 0.5)
    INK = mat(1, 0.2, 0.8)
    STEEL4 = mat(4, 0.55, 0.45)
    LENS = mat(9, 0.4, 0.15)
    RAIL = mat(9, 0.65, 0.3)
    SHAFT = mat(5, 0.65, 0.35)
    COLLAR = mat(8, 0.65, 0.32)
    BOX = mat(7, 0.6, 0.38)
    STRUT = mat(6, 0.65, 0.35)
    ROD = mat(8, 0.75, 0.25)
    body = Mesh()

    # ---- barrel with lobster-back elbow ----
    # stations along the straight barrel: breech ring at the right, two panel grooves, flange at left
    g = 0.16
    bar = [(32.0, RT), (30.0, RT), (29.85, RT - g), (29.6, RT - g), (29.45, RT),
           (22.3, RT), (22.15, RT - g), (21.85, RT - g), (21.7, RT), (11.5, RT)]
    pts = [(x, TY, ZC) for x, _ in bar]
    rads = [r for _, r in bar]
    mats = [TUBE] * (len(pts) - 1)
    # elbow: mitres at (11, 4.5) -> down-left -> down
    # (fitted to the sprite's flat-cut corner: elbow_fit.py)
    elbow = [((4.0, 8.5, 3.15), 2.9), ((4.2, 12.2, 2.95), 2.8)]
    for p, r in elbow:
        pts.append(p)
        rads.append(r)
    mats += [TUBE, LEG]
    tube(body, pts, rads, TUBE, sides=24, cap0="flat", cap1="dome", cap_len=1.2, mats=mats)
    # flange rings: at the first mitre (bolted) and at the second
    m1, m2 = Vector((11.5, TY, ZC)), Vector((4.0, 8.5, 3.15))
    dd = (m2 - m1).normalized()
    # the bright joint collar wraps the first mitre (cols 9-10), mitred with it
    tube(body, [(12.4, TY, ZC), tuple(m1), tuple(m1 + dd * 1.3)], [RT + 0.16, RT + 0.16, RT + 0.06], FLANGE,
         sides=24, ch=0.18)
    for a in range(-3, 4):  # bolt heads on the collar's barrel-side face
        ang = math.pi / 2 + a * 0.42
        y, z = TY + math.cos(ang) * (RT - 0.2), ZC + math.sin(ang) * (RT - 0.2)
        tube(body, [(12.75, y, z), (12.3, y, z)], [0.28, 0.28], RIM, sides=8, ch=0.08)
    # weld band at the second mitre, on the leg
    d2 = (Vector((4.2, 12.2, 2.95)) - m2).normalized()
    tube(body, [tuple(m2 + d2 * 0.2), tuple(m2 + d2 * 0.9)], [3.0, 2.98], TUBE, sides=24, ch=0.12)
    # breech ring and the chamfered breech plate
    tube(body, [(29.4, TY, ZC), (31.5, TY, ZC)], [RT + 0.14] * 2, RIM, sides=24, ch=0.2)
    tube(body, [(31.5, TY, ZC), (32.7, TY, ZC)], [RT - 0.2, 2.6], RIM, sides=24, ch=0.1)
    # cradles under the barrel and the elbow foot
    for x0 in (12.6, 26.4):
        xprism(body, [(1.6, 0), (7.4, 0), (7.4, 1.6), (6.2, 3.0), (2.8, 3.0), (1.6, 1.6)], x0, x0 + 2.2, DARK, c=0.2)
    zprism(body, [(1.3, 11.2), (6.4, 11.2), (6.4, 15.0), (2.2, 15.0), (1.3, 13.9)], 0, 1.5, DARK, c=0.35)  # saddle block

    # ---- sight housing, lens, hatch ----
    HT = ZC + RT + 0.75  # housing top
    zprism(body, rect(13.9, 1.85, 25.8, 6.05), ZC + 1.2, HT - 0.7, DARK, c=0.0)
    zprism(body, rect(13.9, 1.85, 18.6, 6.05), HT - 0.75, HT, DARK, c=0.35)       # lens block
    for poly in (rect(18.5, 1.85, 25.8, 2.85), rect(18.5, 5.45, 25.8, 6.05), rect(25.0, 1.85, 25.8, 6.05)):
        zprism(body, poly, HT - 0.75, HT, DARK, c=0.2)                            # hatch frame
    zprism(body, rect(18.4, 2.8, 25.1, 5.5), HT - 0.75, HT - 0.55, INK, c=0.0)     # open well floor
    zprism(body, rect(14.7, 2.75, 18.2, 5.15), HT - 0.2, HT + 0.2, STEEL4, c=0.15)
    dome(body, (16.45, 3.95, HT + 0.1), (1.4, 1.0, 0.5), LENS)
    for x, y in ((14.4, 2.35), (25.2, 2.35), (14.4, 5.55), (25.2, 5.55)):  # corner bolts
        tube(body, [(x, y, HT), (x, y, HT + 0.18)], [0.28, 0.22], STEEL4, sides=6, cap0="plain", cap1="plain")

    # ---- conduit along the barrel's front shoulder ----
    tube(body, [(10.6, 6.75, ZC + 2.45), (23.2, 6.75, ZC + 2.45)], [0.55, 0.55], RAIL, sides=10,
         cap0="dome", cap1="dome", cap_len=0.4)
    for x in (13.2, 17.4, 21.4):
        zprism(body, rect(x, 6.0, x + 0.8, 7.55), ZC + 1.6, ZC + 3.15, STEEL4, c=0.12)

    # ---- right: shaft, collar, end box ----
    tube(body, [(31.8, TY, ZC), (38.5, TY, ZC)], [1.55, 1.55], SHAFT, sides=16, ch=0.0)
    # a grooved band on the shaft
    tube(body, [(34.4, TY, ZC), (35.4, TY, ZC)], [1.8, 1.8], RIM, sides=16, ch=0.12)
    tube(body, [(37.25, TY, ZC), (37.9, TY, ZC), (40.9, TY, ZC), (41.6, TY, ZC)],
         [2.6, RT + 0.15, RT + 0.15, 3.1], COLLAR, sides=28, ch=0.0)
    # collar face rim groove (machined ring)
    tube(body, [(39.3, TY, ZC), (39.6, TY, ZC)], [RT + 0.22, RT + 0.22], RIM, sides=28, ch=0.05)
    xprism(body, [(2.9, 0), (2.9, ZC + 2.0), (3.4, ZC + 2.5), (6.0, ZC + 2.5), (8.3, ZC - 0.6), (8.3, 0)],
           41.1, 46.0, BOX, c=0.35)
    for i in range(3):  # louvres on the sloped front
        xprism(body, [(6.15 + i * 0.72, ZC + 2.32 - i * 0.98), (6.75 + i * 0.72, ZC + 1.52 - i * 0.98),
                      (6.95 + i * 0.72, ZC + 1.6 - i * 0.98), (6.35 + i * 0.72, ZC + 2.4 - i * 0.98)],
               41.7, 45.4, DARK, c=0.08)
    zprism(body, [(40.4, 2.6), (46.0, 2.6), (46.0, 7.9), (44.6, 9.2), (40.4, 9.2)], 0, 0.8, STEEL4, c=0.2)

    # ---- beam, web, strut, brace, exhaust ----
    xprism(body, [(7.4, 0), (7.4, 3.3), (8.4, 3.5), (9.0, 3.3), (10.0, 2.2), (10.0, 0)], 22.8, 31.2, STEEL4, c=0.25)
    zprism(body, [(30.8, 5.6), (38.0, 5.6), (38.0, 7.2), (33.6, 11.6), (30.8, 11.6)], 0, 3.0, DARK, c=0.3)
    # hydraulic strut: cylinder (upper) + polished rod (lower) + end eyes
    a, b = Vector((38.9, 7.5, ZC - 0.6)), Vector((32.7, 13.3, 1.1))
    m1 = a.lerp(b, 0.55)
    tube(body, [tuple(a), tuple(m1)], [1.4, 1.4], STRUT, sides=14, ch=0.18)
    tube(body, [tuple(m1), tuple(b)], [0.85, 0.85], ROD, sides=12, ch=0.1)
    tube(body, [tuple(m1 + (b - a).normalized() * -0.4), tuple(m1 + (b - a).normalized() * 0.15)],
         [1.55, 1.55], RIM, sides=14, ch=0.12)
    zprism(body, [(31.0, 11.6), (35.6, 11.6), (37.0, 13.6), (37.0, 15.0), (31.0, 15.0)], 0, 1.6, LEG, c=0.35)
    # clevis eye where the rod meets the foot
    tube(body, [(33.3, 11.9, 1.3), (33.3, 14.4, 1.3)], [0.75, 0.75], STEEL4, sides=10, ch=0.1, up=(0, 0, 1))
    tube(body, [(40.6, 8.6, 2.8), (36.4, 14.2, 0.7)], [0.65, 0.65], DARK, sides=10, ch=0.1)
    # web plate tying the brace to the strut
    zprism(body, [(37.6, 9.6), (39.4, 9.6), (38.6, 13.6), (36.4, 13.6)], 0, 1.6, DARK, c=0.2)
    # exhaust nozzle (the launcher): a flattened armoured shroud on a bracket off the end box's base;
    # its mouth, lower left, points down-screen where the fireball leaves
    zprism(body, [(43.2, 8.2), (45.6, 9.2), (43.0, 12.0), (41.0, 10.8)], 0, 1.3, mat(2, 0.3, 0.55), c=0.2)
    tube(body, [(43.7, 8.9, 2.0), (39.4, 13.9, 1.0)], [1.75, 1.75], DARK, sides=8, sz=0.55, ch=0.2)
    tube(body, [(39.7, 13.55, 1.07), (39.25, 14.07, 0.97)], [1.85, 1.85], STEEL4, sides=8, sz=0.6,
         cap0="plain", ch=0.15)
    for t in (0.22, 0.62):  # strap clamps holding the nozzle to its bracket
        p0, p1 = Vector((43.7, 8.9, 2.0)), Vector((39.4, 13.9, 1.0))
        q0, q1 = p0.lerp(p1, t - 0.04), p0.lerp(p1, t + 0.04)
        tube(body, [tuple(q0), tuple(q1)], [1.9, 1.9], STEEL4, sides=8, sz=0.58, ch=0.1)

    # ---- deck, fins, port ----
    deck = [(4.6, 7.4), (26.2, 7.4), (26.2, 13.9), (20.2, 13.9), (19.8, 14.9), (4.6, 14.9)]
    zprism(body, deck, 0, 2.3, DARK, c=0.45)
    zprism(body, rect(10.7, 8.4, 20.0, 14.5), 2.0, 2.36, INK, c=0.05)
    for c in (11, 13, 15, 17, 19):
        xprism(body, [(8.6, 2.0), (8.6, 3.25), (9.4, 3.4), (14.0, 3.4), (14.75, 2.6), (14.75, 2.0)],
               c + 0.12, c + 0.88, STEEL4, c=0.08)
    for c in (11, 13, 15, 17, 19):  # the fins run on down the deck's front face as ribs
        zprism(body, rect(c + 0.18, 14.6, c + 0.82, 15.2), 0.25, 2.15, STEEL4, c=0.12)
    zprism(body, rect(4.6, 14.6, 10.4, 15.15), 0.25, 1.1, STEEL4, c=0.15)  # kick plate at the left
    zprism(body, rect(5.2, 8.0, 9.8, 11.0), 2.0, 2.7, DARK, c=0.3)
    for x in (6.0, 9.0):  # its two bolt heads
        tube(body, [(x, 9.5, 2.6), (x, 9.5, 2.9)], [0.3, 0.3], STEEL4, sides=8, ch=0.06)
    zprism(body, rect(6.8, 12.6, 10.0, 14.6), 2.0, 2.6, DARK, c=0.2)
    zprism(body, rect(19.5, 10.2, 25.6, 14.0), 2.0, 2.55, mat(2, 0.4, 0.6), c=0.2)
    zprism(body, [(25.8, 7.4), (31.2, 7.4), (31.2, 13.7), (29.95, 13.7), (29.95, 12.9), (25.8, 12.9)], 0, 1.3, DARK, c=0.3)
    tube(body, [(25.9, 12.0, 1.9), (30.0, 12.0, 1.9)], [0.7, 0.7], DARK, sides=10, cap1="dome", cap_len=0.4)

    # glowing parts with animated colours (on the body: every frame)
    PORT = mat(114, 0.0, 0.6, emit=1.0, frames={1: 115, 2: 116}, tag="port")
    zprism(body, rect(20.1, 10.8, 25.0, 13.6), 2.1, 2.6, PORT, c=0.1)
    # the glowing insert of the nozzle (smooth, flat) and its hot core
    EXH = mat(116, 0.0, 0.6, emit=1.0, frames={1: 119, 2: 125}, tag="exh")
    tube(body, [(43.3, 9.4, 2.78), (39.75, 13.5, 1.8)], [1.3, 1.3], EXH, sides=8, sz=0.2, ch=0.1)
    ECORE = mat(120, 0.0, 0.6, emit=1.25, frames={1: 127, 2: 127}, tag="ecore")
    tube(body, [(42.6, 10.2, 2.92), (40.5, 12.6, 2.36)], [0.6, 0.6], ECORE, sides=8, sz=0.25,
         cap0="dome", cap1="dome", cap_len=0.4)
    lamps = [(15, {1: 3, 2: 3}, 9), (17, {1: 10, 2: 4}, 5), (19, {2: 9}, 5)]
    for c, fr, i0 in lamps:
        LM = mat(i0, 0.6, 0.3, frames=fr, tag=f"lamp{c}")
        zprism(body, rect(c + 0.1, 8.7, c + 0.9, 10.0), 3.2, 3.55, LM, c=0.06)

    parts = []

    def part(name, ks):
        pm = Mesh()
        parts.append((name, pm, ks))
        return pm

    # hatch: k0 shut plate (8), k1 slid-back inner shutter (4), k2 open (black well shows)
    zprism(part("hatch0", [0]), rect(18.7, 2.7, 25.0, 5.6), HT - 0.3, HT + 0.12, mat(8, 0.6, 0.35), c=0.15)
    zprism(part("hatch1", [1]), rect(18.7, 2.85, 25.0, 5.45), HT - 0.5, HT - 0.3, mat(4, 0.5, 0.45), c=0.08)
    # port hot core (k1, k2) and spill (k2)
    CORE = mat(121, 0.0, 0.6, emit=1.0, frames={2: 123}, tag="portcore")
    zprism(part("portcore", [1, 2]), rect(20.6, 11.0, 23.8, 13.0), 2.1, 2.66, CORE, c=0.08)
    zprism(part("portspill", [2]), rect(18.4, 10.0, 20.1, 14.0), 2.1, 2.42, mat(113, 0.0, 0.6, emit=1.0), c=0.05)
    # frame 2: the shot leaves -- the glow streaks along the nozzle and down the strut
    fl = part("flare", [2])
    HOT, FL = mat(125, 0.0, 0.6, emit=1.0), mat(121, 0.0, 0.6, emit=1.0)  # the sprite's white-hot yellow, orange tail
    tube(fl, [(44.6, 8.4, 2.95), (39.75, 13.5, 1.9)], [1.4, 1.4], HOT, sides=8, sz=0.22, cap0="dome", cap_len=0.6)
    tube(fl, [(39.4, 13.9, 1.0), (37.4, 15.1, 0.7)], [1.3, 0.25], FL, sides=10, sz=0.5, cap0="plain", cap1="plain")

    obj = to_object(body, NAME, coll)
    pobjs = [(to_object(pm, f"{NAME}-{name}", coll), ks) for name, pm, ks in parts]
    return obj, pobjs




# ---------------------------------------------------------------------------------------------
# Build, cut into the pieces, export
# ---------------------------------------------------------------------------------------------

def build_cannon(name, colors, mirror=False):
    """Build the whole gun (see the module doc) and return (body, [(part, [k..])], collection)."""
    global NAME, SPR, MATS, ANIM, MIRROR
    NAME, SPR, MATS, ANIM, MIRROR = name, {"name": name, "colors": colors}, [], {}, mirror
    coll = common.reset_collection(name)
    for o in list(bpy.data.objects):
        if o.name not in coll.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    body, parts = build(coll)
    return body, parts, coll


def split_open(obj, layout, coll):
    """Cut the outline shell into the pieces without filling the cuts (no outline along the seam)."""
    out = {}
    for n, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{n}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(f"{n}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        out[n] = sh
    return out


def cannon_main(root, left, right, mirror, name):
    """Build, split and export an assembly of two cannon pieces (left and right model names)."""
    import lib_b077 as L
    a, b = common.load_sprite(root, left), common.load_sprite(root, right)
    colors = L.merged_colors([a, b])
    sprites = {left: a, right: b}
    frames = {n: [f["index"] for f in d["frames"]] for n, d in sprites.items()}
    body, parts, coll = build_cannon(name, colors, mirror)
    # D51/D90/D118: the outline shell from a sealed copy of the always-visible machine
    sealed = bpy.data.objects.new(f"{name}_sealed", body.data.copy())
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    shell = common.outline_shell(sealed, coll, voxel=0.03, faces=2500, inside=0.004)
    bpy.data.objects.remove(sealed, do_unlink=True)
    layout = [(left, -12, 0), (right, 12, 0)]
    shells = split_open(shell, layout, coll)
    models = {n: [piece] for n, piece in common.split_assembly(body, layout, coll).items()}
    for part, ks in parts:
        for n, piece in common.split_assembly(part, layout, coll).items():
            if not piece.data.polygons:  # this part lies wholly in the other piece
                bpy.data.objects.remove(piece)
                continue
            piece.name = f"{n}-{part.name.rsplit('-', 1)[-1]}"
            if len(ks) < K:
                common.frame_part(piece, [frames[n][k] for k in ks])
            models[n].append(piece)
    for n, data in sprites.items():
        mats = {slot: common.palette_material(SPR, idx, f"{n}-{tag}", metallic=met, roughness=rough,
                                              emission_strength=emit, frames={frames[n][k]: i for k, i in fr.items()})
                for slot, (idx, met, rough, emit, tag, fr) in ANIM.items()}
        for o in models[n]:
            for slot, m in mats.items():
                o.data.materials[slot] = m
        models[n].append(shells[n])
        common.export_sprite_model(root, models[n], f"enemies/{n}", data["sprites"])
        L.frame_previews(models[n], n, data, root, data["sprites"][0]["frames"])
    out = L.preview_arg()
    if out:
        for n, data in sprites.items():
            img = root / "reference" / "models" / n / data["frames"][0]["image"]
            common.render_preview(models[n], str(out.parent / f"{n}.png"), img, size=2,
                                  frame=data["sprites"][0]["frames"][0])
