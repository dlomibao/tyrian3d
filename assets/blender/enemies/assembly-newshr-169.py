"""assembly-newshr-169, (newshr.shp, two 2x2 pieces, 24 x 56 px: newshr-167 over newshr-169):
the furnace column of the IXMUCANE boss machine, a 3D version of its sprites in the hard-surface
style of batch 1's assembly-newshr-273 / -267 (D65).

What it is: three machined grey blocks standing on the ground, separated by two gaps (rows 37-38 and
46-47 are empty in the sprite):
- the furnace housing (rows 10-37): a chamfered grey plinth; on it a raised grey bezel ring (a rounded
  square, superellipse) holding a bronze-rimmed socket with a big glowing fireball in it (orange skin,
  ragged yellow mid zone, a flame-lobed bright core upper left with a tongue down the right, all
  faces of the ball's own mesh, no painted highlight: the game lights it); below the ball a first oval
  lens in a ring bezel, a raised panel on the left and a vertical vent slot on the right that opens
  out of the block's bottom edge;
- the second block (rows 39-46): a louvre of two horizontal slats on the left, a smaller lens in a
  bezel, a low bay on the right where a thin brown feed pipe drops into the big brown pipe;
- the third block (rows 48-56): two vertical fins on the left, a small lens, a low bay under the
  lens, the big brown pipe running down the right edge.
Every frame only changes colours, so one model per piece covers its 4 frames with frame-animated
palette materials (D17): the fire dims two palette steps a frame (121 -> 119 -> 117 -> 115) and its
bronze rim reddens; lens 1 and lens 3 brighten, lens 2 dims.

Build: one object per block in column coordinates (pixel edges, origin at the column's centre),
joined and cut into the two pieces with common.split_assembly (seam caps cleaned as batch 1). The
blocks are disjoint, so the D90/D118 outline shell is made per block (common.outline_shell keeps only
the largest island), from a sealed pre-cull copy, joined and cut per piece without filling.

Run: tools/build-models.sh assets/blender/enemies/assembly-newshr-169.py
(Blender --background --python assembly-newshr-169.py -- [--views DIR] [--out GLB] for review renders).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
HERE = Path(__file__).resolve().parent
NAME = "assembly-newshr-169"
W, H = 24, 56
PX = 1 / 12
TAG = "nshr169A"
PIECES = [("newshr-167", 0, -14), ("newshr-169", 0, 14)]
FRAME_PAIRS = [(167, 169), (205, 207), (243, 245), (281, 283)]


def X(c):
    return (c - W / 2) * PX


def Y(r):
    return (H / 2 - r) * PX


SPRITES = {n: common.load_sprite(ROOT, n) for n, _, _ in PIECES}
PAL = {"name": NAME, "colors": {}}
for _s in SPRITES.values():
    PAL["colors"].update(_s["colors"])


# --- materials ----------------------------------------------------------------------------------

def spec_level(m, v):
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = v
            break


MATS = {}


def mat(index, kind="metal", frames=None, part=""):
    key = (index, kind, part)
    if key in MATS:
        return MATS[key]
    tag = f"{TAG}_{kind}{('_' + part) if part else ''}"
    if kind == "glow":  # D126/D173: glow surfaces metallic 1, rough; the glow carries the colour
        m = common.palette_material(PAL, index, tag, metallic=1.0, roughness=0.9,
                                    emission_strength=GLOW.get(part, 1.0), frames=frames)
        spec_level(m, 0.5)
    elif kind == "polish":  # rails, bezel lips: smoother satin metal
        m = common.palette_material(PAL, index, tag, metallic=0.55, roughness=0.32, frames=frames)
        spec_level(m, 0.7)
    elif kind == "bronze":  # satin bronze, not mirror gold
        m = common.palette_material(PAL, index, tag, metallic=0.6, roughness=0.4, frames=frames)
        spec_level(m, 0.6)
    elif kind == "pipe":
        m = common.palette_material(PAL, index, tag, metallic=0.35, roughness=0.5, frames=frames)
        spec_level(m, 0.5)
    else:  # satin machine metal
        m = common.palette_material(PAL, index, tag, metallic=0.4, roughness=0.45, frames=frames)
        spec_level(m, 0.5)
    MATS[key] = m
    return m


# Glow strengths (D126): ~1 = the palette colour unlit; the white-hot parts a little over.
GLOW = {"fire": 1.0, "fire_mid": 1.0, "fire_core": 1.05,
        "l1": 0.95, "l1c": 1.0, "l2": 0.95, "l2c": 1.0, "l3": 0.95, "l3c": 1.0}


# --- mesh helpers (copied from batch 1's assembly-newshr-273.py; candidates for a shared lib) ------

class Part:
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []

    def slot(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def tag(self, start, m, smooth=False):
        """Tag every face not tagged yet (the builder just made them; `start` is kept for the
        helpers' signature: face indices aren't creation order after a hull's dissolve)."""
        lay = self.bm.faces.layers.int.get("done") or self.bm.faces.layers.int.new("done")
        k = self.slot(m)
        for f in self.bm.faces:
            if not f[lay]:
                f[lay] = 1
                f.material_index = k
                f.smooth = smooth

    def obj(self, coll, sharp=35):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for m in self.mats:
            me.materials.append(m)
        o = bpy.data.objects.new(self.name, me)
        coll.objects.link(o)
        me.set_sharp_from_angle(angle=math.radians(sharp))
        return o


def hull(P, pts, m, smooth=False):
    bm = P.bm
    n = len(bm.faces)
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    P.tag(n, m, smooth)


def chbox(P, c0, r0, c1, r1, z0, z1, ch, m, chz=None):
    """A box over pixel edges c0..c1, r0..r1, z0..z1, its top edges chamfered `ch` px."""
    x0, x1, y0, y1 = X(c0), X(c1), Y(r1), Y(r0)
    d = ch * PX
    dz = chz if chz is not None else d
    pts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)]
    pts += [(x0, y0, z1 - dz), (x1, y0, z1 - dz), (x1, y1, z1 - dz), (x0, y1, z1 - dz)]
    pts += [(x0 + d, y0 + d, z1), (x1 - d, y0 + d, z1), (x1 - d, y1 - d, z1), (x0 + d, y1 - d, z1)]
    hull(P, pts, m)


def offset_poly(pts, d):
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x))
        n1 = Vector((-e1.y, e1.x))
        b = n0 + n1
        if b.length < 1e-6:
            b = n0
        b.normalize()
        cosh = max(0.35, b.dot(n0))
        q = p1 + b * (d / cosh)
        out.append((q.x, q.y))
    return out


def ccw(pts):
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return pts if a > 0 else pts[::-1]


def plinth(P, outline_px, z0, z1, ch, m):
    """A slab on a pixel-edge outline, z0..z1, its top edge chamfered `ch` px (ring inset)."""
    base = ccw([(X(c), Y(r)) for c, r in outline_px])
    top = offset_poly(base, ch * PX)
    bm = P.bm
    n0 = len(bm.faces)
    rings = [[bm.verts.new((x, y, z0)) for x, y in base],
             [bm.verts.new((x, y, z1 - ch * PX)) for x, y in base],
             [bm.verts.new((x, y, z1)) for x, y in top]]
    k = len(base)
    for a, b in zip(rings, rings[1:]):
        for i in range(k):
            j = (i + 1) % k
            bm.faces.new((a[i], a[j], b[j], b[i]))
    from mathutils.geometry import tessellate_polygon  # concave outlines: ear-clip the caps
    for ring, flip in ((rings[-1], False), (rings[0], True)):
        for tri in tessellate_polygon([[v.co for v in ring]]):
            vs = [ring[i] for i in tri]
            n = (vs[1].co - vs[0].co).cross(vs[2].co - vs[0].co)
            if (n.z < 0) != flip:
                vs.reverse()
            bm.faces.new(vs)
    P.tag(n0, m, False)


def tube(P, a, b, r, m, sides=12, rz=None, flange=None, smooth=True, flange_at=(True, True)):
    """A cylinder between Blender points a and b, radius r; optional flanges (radius, length)."""
    a, b = Vector(a), Vector(b)
    ax = (b - a).normalized()
    up = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    u = ax.cross(up).normalized()
    v = u.cross(ax).normalized()
    rz = r if rz is None else rz
    bm = P.bm
    n0 = len(bm.faces)

    def ring(c, rr, rrz):
        return [bm.verts.new(c + u * rr * math.cos(2 * math.pi * (k + 0.5) / sides)
                             + v * rrz * math.sin(2 * math.pi * (k + 0.5) / sides)) for k in range(sides)]

    L = (b - a).length
    st = []
    if flange:
        fr, fl = flange
        fl = min(fl, L * 0.3)
        if flange_at[0]:
            st += [(0, fr), (fl, fr), (fl, r)]
        else:
            st += [(0, r)]
        if flange_at[1]:
            st += [(L - fl, r), (L - fl, fr), (L, fr)]
        else:
            st += [(L, r)]
    else:
        st = [(0, r), (L, r)]
    rings = [ring(a + ax * t, rr, rr * rz / r) for t, rr in st]
    for p, q in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((p[k], p[j], q[j], q[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    P.tag(n0, m, smooth)


def se_point(rx, ry, t, n):
    """A point on a superellipse |x/rx|^n + |y/ry|^n = 1 at parameter t (n = 2: an ellipse)."""
    c, s = math.cos(t), math.sin(t)
    e = 2.0 / n
    return rx * math.copysign(abs(c) ** e, c), ry * math.copysign(abs(s) ** e, s)


def ring_bezel(P, c, r, rx, ry, w, z0, z1, m, segs=40, lip=0.35, n=2.0, wy=None):
    """A lofted ring round pixel point (c, r): inner radii rx, ry (px), w px wide (wy at top/bottom),
    z0..z1, its inner and outer top lips chamfered; superellipse exponent n."""
    bm = P.bm
    n0 = len(bm.faces)
    cx, cy = X(c), Y(r)
    wy = w if wy is None else wy
    hz = z1 - z0
    prof = [(1.0, z0), (1.0, z1 - hz * 0.3), (1 - lip, z1), (lip, z1), (0.0, z1 - hz * 0.3), (0.0, z0)]
    rings = []
    for i in range(segs):
        t = 2 * math.pi * i / segs
        ring = []
        for d, z in prof:
            px, py = se_point(rx + d * w, ry + d * wy, t, n)
            ring.append(bm.verts.new((cx + px * PX, cy - py * PX, z)))
        rings.append(ring)
    k = len(prof)
    for i in range(segs):
        a, b = rings[i], rings[(i + 1) % segs]
        for j in range(k):
            jj = (j + 1) % k
            bm.faces.new((a[j], b[j], b[jj], a[jj]))
    P.tag(n0, m, True)


class Dome:
    """A half ellipsoid over pixel point (c, r), radii rx, ry px, from z0 up h; `p` < 1 bulges it."""

    def __init__(self, c, r, rx, ry, z0, h, p=1.0):
        self.c, self.r, self.rx, self.ry, self.z0, self.h, self.p = c, r, rx, ry, z0, h, p

    def z(self, c, r):
        q = ((c - self.c) / self.rx) ** 2 + ((r - self.r) / self.ry) ** 2
        return self.z0 + self.h * max(0.0, 1 - q) ** (0.5 * self.p)

    def build(self, P, m, segs=40, rings=12):
        bm = P.bm
        n0 = len(bm.faces)
        rows = []
        for k in range(rings):
            s = math.cos((math.pi / 2) * k / rings)
            rows.append([bm.verts.new((X(self.c + self.rx * s * math.cos(2 * math.pi * i / segs)),
                                       Y(self.r + self.ry * s * math.sin(2 * math.pi * i / segs)),
                                       self.z0 + self.h * (1 - s * s) ** (0.5 * self.p)))
                         for i in range(segs)])
        top = bm.verts.new((X(self.c), Y(self.r), self.z0 + self.h))
        for a, b in zip(rows, rows[1:]):
            for i in range(segs):
                j = (i + 1) % segs
                bm.faces.new((a[i], a[j], b[j], b[i]))
        for i in range(segs):
            bm.faces.new((rows[-1][i], rows[-1][(i + 1) % segs], top))
        bm.faces.new(list(reversed(rows[0])))
        P.tag(n0, m, True)


    def edge(self, pc, pr, th):
        """Distance in px from (pc, pr), inside the dome, to its rim along direction th."""
        dx, dy = math.cos(th) / self.rx, math.sin(th) / self.ry
        ox, oy = (pc - self.c) / self.rx, (pr - self.r) / self.ry
        a, b, cc = dx * dx + dy * dy, 2 * (ox * dx + oy * dy), ox * ox + oy * oy - 1
        return (-b + math.sqrt(b * b - 4 * a * cc)) / (2 * a)

    def build_zoned(self, P, base, zones, centre, segs=48, rings=(4, 4, 6)):
        """The dome with its colour zones as faces of its own mesh (closed, no lifted patches):
        loops run out from `centre` (inside the innermost zone); `zones` lists (material,
        radius(th) px) inner to outer, each a star-shaped region round `centre`, and the dome's
        own material `base` fills the rest out to the rim. Each zone edge is an exact loop."""
        bm = P.bm
        pc, pr = centre
        ths = [2 * math.pi * i / segs for i in range(segs)]
        ed = [self.edge(pc, pr, t) for t in ths]
        bounds = [[0.0] * segs]
        for _, rf in zones:
            prev = bounds[-1]
            bounds.append([max(min(rf(t), 0.93 * e), p + 0.15) for t, e, p in zip(ths, ed, prev)])
        bounds.append(ed)
        mats = [z[0] for z in zones] + [base]

        def vert(t, d):
            u, v = pc + d * math.cos(t), pr + d * math.sin(t)
            return bm.verts.new((X(u), Y(v), self.z(u, v)))

        top = vert(0, 0)
        loop = None
        for band, m in enumerate(mats):
            r0, r1 = bounds[band], bounds[band + 1]
            n = rings[band]
            last = band == len(mats) - 1
            for k in range(1, n + 1):
                f = math.sin(0.5 * math.pi * k / n) if last else k / n  # dense near the rim
                cur = [vert(t, a + (b - a) * f) for t, a, b in zip(ths, r0, r1)]
                for i in range(segs):
                    j = (i + 1) % segs
                    if loop is None:
                        bm.faces.new((top, cur[i], cur[j]))
                    else:
                        bm.faces.new((loop[i], cur[i], cur[j], loop[j]))
                loop = cur
            P.tag(0, m, True)
        bm.faces.new(list(reversed(loop)))
        P.tag(0, base, True)


def ell(rx, ry, rot=0.0):
    """Radius function of an ellipse round the zone centre, turned `rot` degrees."""
    a = math.radians(rot)
    return lambda t: 1.0 / math.sqrt((math.cos(t - a) / rx) ** 2 + (math.sin(t - a) / ry) ** 2)


# --- the column -------------------------------------------------------------------------------------

# frame colour maps, measured from the sprite frames (index in frame 167/169 -> later frames)
F_FIRE = {205: 119, 243: 117, 281: 115}
F_FIRE_MID = {205: 121, 243: 119, 281: 117}
F_FIRE_CORE = {205: 123, 243: 121, 281: 119}
F_RIM = {205: 70, 243: 69, 281: 68}
F_L1 = {207: 119, 245: 122, 283: 124}
F_L1C = {207: 122, 245: 125, 283: 127}
F_L2 = {207: 121, 245: 119, 283: 117}
F_L2C = {207: 124, 245: 122, 283: 120}
F_L3 = {207: 119, 245: 120, 283: 123}
F_L3C = {207: 121, 245: 122, 283: 125}


def housing(coll):
    """Block 1: the furnace housing with the fireball and the first lens (rows 10-37)."""
    P = Part(f"{NAME}_housing")
    BODY, DECK, RING, LIP = mat(5), mat(4), mat(9, "polish"), mat(6, "polish")
    RECESS = mat(2)
    RIM = mat(23, "bronze", F_RIM, "rim")
    # The plinth: the whole block, with the vent slot's mouth notched out of its bottom edge.
    plinth(P, [(0, 10), (24, 10), (24, 37), (22.4, 37), (22.4, 30.6), (18.4, 30.6), (18.4, 37), (0, 37)],
           0.0, 0.30, 0.7, BODY)
    # The vent slot's floor and a cross bar in it.
    chbox(P, 18.2, 30.4, 22.6, 36.0, 0.0, 0.11, 0.3, RECESS)
    chbox(P, 18.2, 33.0, 22.6, 33.9, 0.0, 0.20, 0.3, LIP)
    # A deck plate round the first lens (rows 28-36.6), a little lower than the bezel ring above it.
    chbox(P, 4.3, 28.6, 18.0, 36.6, 0.0, 0.33, 0.6, DECK)
    # Raised panel on the left with a groove line, and its lit lip at the bottom left.
    chbox(P, 0.0, 28.4, 4.0, 35.8, 0.0, 0.37, 0.5, BODY)
    chbox(P, 0.6, 31.6, 3.4, 32.2, 0.33, 0.375, 0.15, RECESS)
    chbox(P, 0.0, 35.6, 3.6, 37.0, 0.0, 0.31, 0.4, LIP)
    # Bolts in the housing's top corners, outside the ring.
    for c, r in ((22.6, 11.3), (1.6, 27.4)):
        tube(P, (X(c), Y(r), 0.28), (X(c), Y(r), 0.335), 0.6 * PX, LIP, sides=6, smooth=False)

    # The socket: a raised grey bezel ring (rounded square), a bronze rim inside it, the fireball.
    C, R = 11.8, 19.2
    ring_bezel(P, C, R, 10.2, 8.35, 1.8, 0.22, 0.44, RING, segs=64, lip=0.3, n=2.6, wy=0.95)
    ring_bezel(P, C, R, 9.3, 7.85, 0.95, 0.24, 0.42, RIM, segs=56, lip=0.4, n=2.2, wy=0.55)
    # socket floor under the ball (closes the ring's well)
    chbox(P, 2.6, 11.6, 21.0, 26.8, 0.0, 0.30, 0.5, RECESS)
    ball = Dome(C - 0.1, R + 0.1, 9.4, 7.95, 0.27, 0.43, p=0.8)
    # Fire zones as faces of the ball (D65 fix 1: no lifted decals, no white spot): an orange
    # body (121), a ragged yellow mid zone (123) that thins to the lower left as the sprite's does,
    # and a flame-lobed bright core (125) over the sprite's hot upper left, with one low-contrast
    # tongue curling down the right where the sprite's bright arm runs.
    FC = (10.2, 17.0)
    core = ell(5.4, 3.6, -15)
    ll = math.radians(135)

    def core_r(t):
        tongue = 3.6 * math.exp(-(((t - 0.55 + math.pi) % (2 * math.pi) - math.pi) / 0.32) ** 2)
        return core(t) * (1 + 0.14 * math.sin(3 * t + 0.6) + 0.07 * math.sin(7 * t + 2.1)) + tongue

    def mid_r(t):
        e = ball.edge(*FC, t)
        cut = max(0.0, math.cos(t - ll)) ** 2
        return e * (0.88 - 0.18 * cut + 0.05 * math.sin(5 * t + 0.4) + 0.03 * math.sin(9 * t + 1.3))

    ball.build_zoned(P, mat(121, "glow", F_FIRE, "fire"),
                     [(mat(125, "glow", F_FIRE_CORE, "fire_core"), core_r),
                      (mat(123, "glow", F_FIRE_MID, "fire_mid"), mid_r)],
                     FC, segs=96, rings=(6, 5, 8))

    # The first lens: a glowing oval dome in a ring bezel.
    LC, LR = 12.0, 32.4
    ring_bezel(P, LC, LR, 6.0, 3.45, 1.05, 0.26, 0.40, RING, segs=40, lip=0.35)
    lens = Dome(LC, LR, 6.05, 3.5, 0.30, 0.10, p=0.8)
    lens.build_zoned(P, mat(117, "glow", F_L1, "l1"), [(mat(120, "glow", F_L1C, "l1c"), ell(3.6, 1.75))],
                     (10.0, 31.7), segs=48, rings=(3, 6))
    return P


def block2(coll):
    """Block 2 (rows 39-46): louvre, lens 2, bay, feed pipe into the big pipe."""
    P = Part(f"{NAME}_block2")
    BODY, RECESS, SLAT, RING = mat(3), mat(2), mat(6, "polish"), mat(9, "polish")
    PIPE = mat(165, "pipe")
    # main body (cols 4-16 full height; the louvre and the bay sit a pixel inside the top and bottom)
    plinth(P, [(4, 39), (16, 39), (16, 46), (4, 46)], 0.0, 0.29, 0.6, BODY)
    # louvre box on the left with two horizontal slats in it
    chbox(P, 0.0, 40.0, 4.6, 45.0, 0.0, 0.20, 0.4, RECESS)
    for r in (41.6, 44.0):
        tube(P, (X(0.25), Y(r), 0.22), (X(4.4), Y(r), 0.22), 0.55 * PX, SLAT, sides=8, rz=0.5 * PX)
    chbox(P, 0.0, 39.9, 4.6, 40.6, 0.0, 0.26, 0.25, BODY)
    # the bay: a low floor between the body and the pipe, a bracket the feed pipe leaves from
    chbox(P, 15.6, 40.0, 24.0, 45.0, 0.0, 0.10, 0.3, RECESS)
    chbox(P, 20.6, 40.0, 24.0, 41.4, 0.0, 0.27, 0.35, BODY)
    # lens 2
    LC, LR = 12.0, 42.5
    ring_bezel(P, LC, LR, 4.0, 2.45, 0.95, 0.24, 0.35, RING, segs=36, lip=0.35)
    lens = Dome(LC, LR, 4.05, 2.5, 0.27, 0.085, p=0.8)
    lens.build_zoned(P, mat(122, "glow", F_L2, "l2"), [(mat(125, "glow", F_L2C, "l2c"), ell(2.6, 1.5))],
                     (11.1, 41.9), segs=40, rings=(3, 5))
    # the big brown pipe (cols 20-24) coming down out of an elbow cap, flanged at the block's end
    tube(P, (X(22.0), Y(43.5), 0.17), (X(22.0), Y(46.0), 0.17), 1.75 * PX, PIPE, sides=16,
         flange=(2.0 * PX, 0.6 * PX))
    # the thin feed pipe dropping from the bracket into the elbow cap
    tube(P, (X(23.0), Y(41.0), 0.22), (X(23.0), Y(43.8), 0.22), 0.6 * PX, PIPE, sides=8)
    return P


def block3(coll):
    """Block 3 (rows 48-56): vertical fins, lens 3, bay, the big pipe."""
    P = Part(f"{NAME}_block3")
    BODY, RECESS, FIN, RING = mat(4), mat(2), mat(5, "polish"), mat(7, "polish")
    PIPE = mat(165, "pipe")
    # body: a top deck over the left two thirds (its top-left corner reaches col 0 on row 48)
    chbox(P, 1.0, 48.0, 16.2, 52.4, 0.0, 0.27, 0.6, BODY)
    chbox(P, 1.0, 52.0, 9.0, 56.0, 0.0, 0.26, 0.6, BODY)
    chbox(P, 0.0, 48.0, 2.0, 49.0, 0.0, 0.24, 0.3, BODY)
    # the low bay under the lens and right of it, its lip wall against the pipe
    chbox(P, 8.6, 48.8, 20.2, 56.0, 0.0, 0.09, 0.3, RECESS)
    chbox(P, 18.0, 49.0, 20.2, 56.0, 0.0, 0.17, 0.35, BODY)
    # vertical fins on the left
    chbox(P, 1.0, 49.0, 4.8, 56.0, 0.0, 0.18, 0.3, RECESS)
    for c in (1.9, 3.9):
        chbox(P, c - 0.5, 49.3, c + 0.5, 56.0, 0.0, 0.27, 0.25, FIN, chz=0.02)
    # lens 3
    LC, LR = 11.9, 50.4
    ring_bezel(P, LC, LR, 3.0, 1.45, 0.75, 0.22, 0.32, RING, segs=32, lip=0.35)
    lens = Dome(LC, LR, 3.05, 1.5, 0.24, 0.07, p=0.8)
    lens.build_zoned(P, mat(117, "glow", F_L3, "l3"), [(mat(119, "glow", F_L3C, "l3c"), ell(1.6, 0.8))],
                     (11.2, 50.2), segs=32, rings=(2, 4))
    # the big brown pipe down the right edge, flanged at the top
    tube(P, (X(22.0), Y(48.0), 0.17), (X(22.0), Y(56.0), 0.17), 1.75 * PX, PIPE, sides=16,
         flange=(2.0 * PX, 0.6 * PX), flange_at=(True, False))
    # clamp band round the pipe
    tube(P, (X(22.0), Y(52.4), 0.17), (X(22.0), Y(53.2), 0.17), 1.95 * PX, mat(4), sides=16)
    return P


def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = objs[0]
    o.name = o.data.name = name
    uniq = []
    for m in o.data.materials:
        if m not in uniq:
            uniq.append(m)
    remap = [uniq.index(m) for m in o.data.materials]
    fm = [remap[p.material_index] for p in o.data.polygons]
    o.data.materials.clear()
    for m in uniq:
        o.data.materials.append(m)
    for p, k in zip(o.data.polygons, fm):
        p.material_index = k
    return o


SHELL = {"voxel": 0.03, "inside": 0.008, "smooth": 8}


def shells(blocks, coll):
    """D90/D118 shell per block (outline_shell keeps only the largest island), from a sealed copy."""
    out = []
    for o, faces in zip(blocks, (2500, 1200, 1200)):
        closed = o.copy()
        closed.data = o.data.copy()
        coll.objects.link(closed)
        s = common.outline_shell(closed, coll, faces=faces, **SHELL)
        bpy.data.objects.remove(closed)
        out.append(s)
    return join(out, f"{NAME}_outline")


def split_open(obj, coll):
    out = {}
    for name, cx, cy in PIECES:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        s = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(s)
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        out[name] = s
    return out


def cap_open_ends(obj):
    """Batch 1's seam clean-up after split_assembly (see assembly-newshr-273.py)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    hw, hh, eps = 1.0, 14 / 12, 1e-4

    def on_seam(co):
        return abs(abs(co.x) - hw) < eps or abs(abs(co.y) - hh) < eps

    seam = [v for v in bm.verts if on_seam(v.co)]
    if seam:
        bmesh.ops.remove_doubles(bm, verts=seam, dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-6)
    groups = {}
    for f in bm.faces:
        groups.setdefault(frozenset(v.index for v in f.verts), []).append(f)
    drop = []
    for fs in groups.values():
        if len(fs) < 2:
            continue
        c = fs[0].calc_center_median()
        out = Vector((math.copysign(1, c.x), 0, 0)) if abs(abs(c.x) - hw) < eps else \
            Vector((0, math.copysign(1, c.y), 0))
        fs.sort(key=lambda f: -f.normal.dot(out))
        drop += fs[1:]
    if drop:
        bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()


# --- review renders -------------------------------------------------------------------------------------

def setup_render(px, py, engine="EEVEE"):
    scene = bpy.context.scene
    if engine == "WORKBENCH":
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "FLAT"
        scene.display.shading.color_type = "MATERIAL"
    else:
        for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                scene.render.engine = e
                break
            except TypeError:
                pass
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    scene.render.resolution_x, scene.render.resolution_y = px, py
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"


def lights():
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.25, 0.25, 0.28, 1)
    bg.inputs[1].default_value = 0.6
    for nm, rot, en in (("key", (math.radians(40), 0, math.radians(135)), 3.5),
                        ("fill", (math.radians(60), 0, math.radians(-40)), 0.8)):
        ld = bpy.data.lights.new(nm, "SUN")
        ld.energy = en
        lo = bpy.data.objects.new(nm, ld)
        lo.rotation_euler = rot
        scene.collection.objects.link(lo)


def cam(name, loc, look, ortho=None, lens=50):
    scene = bpy.context.scene
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    data.clip_end = 200
    c = bpy.data.objects.new(name, data)
    scene.collection.objects.link(c)
    c.location = loc
    d = Vector(look) - Vector(loc)
    c.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.camera = c
    return c


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def set_frame(mats, frames):
    """Show the materials' colours of one sprite frame (frame-animated palette materials)."""
    for m in mats:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        base = m.get("_base")
        if base is None:
            m["_base"] = list(bsdf.inputs["Base Color"].default_value)[:3]
            base = m["_base"]
        rgb = list(base)
        fr = m.get("tyrian_frame_rgb")
        if fr:
            for f in frames:
                if str(f) in fr:
                    rgb = list(fr[str(f)])
        bsdf.inputs["Base Color"].default_value = (*rgb, 1)
        if bsdf.inputs["Emission Strength"].default_value > 0:
            bsdf.inputs["Emission Color"].default_value = (*rgb, 1)


def views(out_dir, obj, shell):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH" and o is not obj:
            o.hide_render = True
    K = 8
    setup_render(W * K, H * K, "WORKBENCH")
    keep = {m.name: tuple(m.diffuse_color) for m in obj.data.materials}
    for m in obj.data.materials:
        i = int(m.name.split("_")[1])
        s = i / 255
        lin = ((s + 0.055) / 1.055) ** 2.4 if s > 0.04045 else s / 12.92
        m.diffuse_color = (lin, 0, 0, 1)
    c = cam("top", (0, 0, 20), (0, 0, 0), ortho=H * PX)
    c.rotation_euler = (0, 0, 0)
    render(out_dir / "idx_top.png")
    for m in obj.data.materials:
        m.diffuse_color = keep[m.name]
    lights()
    setup_render(W * K, H * K)
    mats = list(obj.data.materials)
    for k, pair in enumerate(FRAME_PAIRS):
        set_frame(mats, pair)
        c = cam(f"top{k}", (0, 0, 20), (0, 0, 0), ortho=H * PX)
        c.rotation_euler = (0, 0, 0)
        render(out_dir / f"top_f{k}.png")
    set_frame(mats, FRAME_PAIRS[0])
    shell.hide_render = False
    D = 9.0
    vs = {
        "game": (0, -D * math.sin(math.radians(20)), D * math.cos(math.radians(20))),
        "steep": (0, -D * math.sin(math.radians(40)), D * math.cos(math.radians(40))),
        "front": (0, -D, 0.25),
        "rear": (0, D, 0.25),
        "side_w": (-D, 0, 0.25),
        "side_e": (D, 0, 0.25),
        "q_sw": (-D * 0.55, -D * 0.6, D * 0.45),
        "q_se": (D * 0.55, -D * 0.6, D * 0.4),
        "q_nw": (-D * 0.5, D * 0.6, D * 0.45),
        "under": (0, -0.5, -D),
    }
    setup_render(900, 900)
    shell.hide_render = True
    for nm, loc in vs.items():
        cam(nm, loc, (0, 0, 0.2), lens=70)
        render(out_dir / f"{nm}.png")
    # the game camera with the outline shell, scaled, black ink: a rough stand-in for the game's ink
    shell.hide_render = False
    sm = shell.data.materials[0] if shell.data.materials else None
    shell.scale = (1.0, 1.0, 1.0)
    cam("game_ink", vs["game"], (0, 0, 0.2), lens=90)
    render(out_dir / "game_shell.png")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    parts = [housing(coll), block2(coll), block3(coll)]
    blocks = [p.obj(coll) for p in parts]
    shell = shells(blocks, coll)
    obj = join(blocks, NAME)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {tris} triangles (whole)")
    pieces = common.split_assembly(obj, PIECES)
    for q in pieces.values():
        cap_open_ends(q)
        q.data.set_sharp_from_angle(angle=math.radians(35))
    pshells = split_open(shell, coll)
    for name, _, _ in PIECES:
        print(f"{name}: {sum(len(p.vertices) - 2 for p in pieces[name].data.polygons)} triangles, "
              f"shell {len(pshells[name].data.polygons)} faces")
    if "--out" in argv:  # a scratch export of both pieces and shells, for review
        common.export_glb([o for n, _, _ in PIECES for o in (pieces[n], pshells[n])],
                          Path(argv[argv.index("--out") + 1]))
    for name, _, _ in PIECES:
        common.export_sprite_model(ROOT, [pieces[name], pshells[name]], f"enemies/{name}",
                                   SPRITES[name]["sprites"])
    objs = [o for n, _, _ in PIECES for o in (pieces[n], pshells[n])]
    for o in objs:
        o.hide_render = True
    if "--views" in argv:
        views(argv[argv.index("--views") + 1], obj, shell)


if __name__ == "__main__":
    main()
