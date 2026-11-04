"""Grey two-legged ground pylon with a blue tube (newsh2.shp frames 123 and 125, enemy types 8 and 9):
an assembly of two 2x2 pieces side by side (48x28 px), seen just below the gun walker
(assembly-newsh2-87) in levels 1.25, 1.3, 1.36 and 3.17. Hard-surface, as the player ships (D50-D53).

The sprite is authoritative (D52): the plan outline covers the composite sprite's INNER mask row by
row (D74, docs/agents/OUTLINE-BORDER.md: inside the dark ink ring, which the game's outline draws;
out to the edge only where the sprite has no ink, the feet's outer rim at rows 20-23), the square beacon and the glass tube sit on the sprite's own
pixels, and every part takes the palette index the sprite uses there (median of the part's pixels
without the outline, the darkest shading and the brightest sheen; see `PAL`). The concept
(assets/blender/features/concepts/assembly-newsh2-123.jpg) only guides the side, front and rear.

The machine (coordinates in sprite px: x = column - 23, the mirror plane between columns 22 and 23;
y = sprite row, the screen bottom is +y; z up):

- A beacon tower (rows 0-5, x +-5): two armoured cheek plates with chamfered tops, louvres on the
  front and flanks, and on the back (north) a vent grille on the beacon column, service hatches and
  ribs, either side of a dark column whose top is the bezel of a square glass beacon (the sprite's
  4x4 blue light, columns 21-24, rows 1-4).
- A shoulder housing (rows 5-7) whose top slopes forward and out (the sprite's shaded rows 5-6), with
  cooling fins on its back faces.
- A glass reactor tube in a dark cradle down the middle (columns 21-24, rows 6-14), between two
  channel walls (columns 20 and 25), end collars and a strap at mid length.
- Two legs, each one hydraulic barrel running forward and down from a raised hip: a ribbed dark heat
  sink end cap (rows 7-8, the sprite's dark band), a polished ring band and collar (rows 9-10), the
  hip housing, then a narrower leg barrel (rows 13-21) sinking into the foot, a light strip along its
  inner top edge (column 17 / 28, rows 14-23), a hydraulic ram on a bolted saddle plate along its
  outer top, and a coolant pipe that leaves a manifold on the hip, runs straight out over the hip's
  crown (row 11, pal 131), drops down its outer end and runs forward along the leg's outer edge
  (column 13 / 32, rows 12-16, the sprite's darker pal 58) into the leg.
- Two axe-blade feet (rows 19-27): a dark sole, a glowing light-bar layer (the sprite's blue rim down
  the outer edge and across the toe, rows 24-26) and a chamfered armour shoe over it.
- Between the legs a low gearbox (rows 13-20, rounded front at rows 19-20, the sprite's pal 2 floor)
  carrying two upright meshing gears facing the camera, their bosses, and the drive shaft from the
  tube's lower end.

The underside is only closed (every part stands on z = 0 or is a closed solid), no detail.
Texture: no concept projection (maps.json "bake": "model"); an ambient-occlusion / edge colour
multiplier and a roughness / metalness map baked with Cycles, as the player ships (D50-D53). Outline
shell as common.outline_shell (D51), cut into the pieces without filling the seam.

Built whole in assembly coordinates (Blender X = (x - 1) / 12, Y = (14 - y) / 12, Z = z / 12; the origin
is screen pixel (173, 51) between the pieces' centres), cut into the pieces newsh2-123 and newsh2-125
with common.split_assembly (piece-local coordinates) and exported each to
public/models/enemies/<piece>.glb with its src/render/spriteModels/<piece>.json entry.

Run: blender --background --factory-startup --python assets/blender/enemies/assembly-newsh2-123.py
     [-- --no-bake] [--preview out.png]
"""

import bisect
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b083 as lib  # noqa: E402

ROOT = common.repo_root(__file__)

NAME = "assembly-newsh2-123"
PIECES = ["newsh2-123", "newsh2-125"]
CX0, CY0 = 173, 51
PX = 1 / 12

# Material slots and their palette index (sprite region medians, see the docstring). PIPE is the
# coolant pipe's run over the hip (row 11: 131/132), CONDUIT its run down the leg's outer edge
# (column 13: 58).
(HEAD, SHOULDER, FRAME, FLOOR, LEG, HIPRING, LIGHT, TUBE, STRIP, PIPE, RIM, FOOT, HUB, CONDUIT) = range(14)
PAL = {HEAD: 6, SHOULDER: 4, FRAME: 3, FLOOR: 2, LEG: 6, HIPRING: 9, LIGHT: 156, TUBE: 155, STRIP: 132,
       PIPE: 131, RIM: 57, FOOT: 4, HUB: 7, CONDUIT: 58}
TAGS = ["head", "shoulder", "frame", "floor", "leg", "hipring", "light", "tube", "strip", "pipe", "rim", "foot",
        "hub", "conduit"]
GLOWS = {LIGHT: 1.6, TUBE: 1.2, STRIP: 0.9, PIPE: 0.35, RIM: 0.45, CONDUIT: 0.35}
SATIN = {HEAD: (0.55, 0.38), SHOULDER: (0.5, 0.42), FRAME: (0.45, 0.48), FLOOR: (0.3, 0.6), LEG: (0.35, 0.42),
         HIPRING: (0.7, 0.3), FOOT: (0.5, 0.44), HUB: (0.6, 0.35)}
# Baked occlusion multiplier per slot: (floor, occlusion weight). The legs are lifted so their round
# barrels read as the sprite's mid grey (pal 6) from the game camera, not near black.
AO = {LEG: (0.72, 0.36)}
AO_DEFAULT = (0.48, 0.62)


# --- curves and plan helpers ------------------------------------------------------------------

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


def frange(a, b, step):
    n = max(1, int(math.ceil((b - a) / step - 1e-9)))
    return [a + (b - a) * i / n for i in range(n + 1)]


def ccw(poly):
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    return poly if area > 0 else poly[::-1]


def inset(poly, d):
    """A convex polygon moved in by d (per edge: a list of d's, one per edge from vertex i)."""
    poly = ccw(poly)
    n = len(poly)
    ds = d if isinstance(d, (list, tuple)) else [d] * n
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1e-9
        nx, ny = -dy / ln, dx / ln  # inward for counter-clockwise
        lines.append(((x0 + nx * ds[i], y0 + ny * ds[i]), (dx, dy)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        den = u[0] * v[1] - u[1] * v[0]
        if abs(den) < 1e-9:
            out.append(q)
            continue
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        out.append((p[0] + u[0] * t, p[1] + u[1] * t))
    return out


def arc(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def fillet_path(corners, radius, k=5):
    """A 3D polyline with each interior corner rounded (quadratic Bezier, k segments)."""
    pts = [Vector(c) for c in corners]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        a, b = (p0 - p1), (p2 - p1)
        t = min(radius, a.length * 0.45, b.length * 0.45)
        s, e = p1 + a.normalized() * t, p1 + b.normalized() * t
        for j in range(k + 1):
            u = j / k
            out.append((1 - u) ** 2 * s + 2 * u * (1 - u) * p1 + u * u * e)
    out.append(pts[-1])
    return out


# --- mesh building (sprite px) ---------------------------------------------------------------

class Builder:
    def __init__(self):
        self.bm = bmesh.new()

    def _mat(self, faces, mat, smooth=True):
        for f in faces:
            f.material_index = mat
            f.smooth = smooth

    def hull(self, pts, mat):
        """Convex hull of the points (a chamfered block), coplanar triangles merged."""
        bm = self.bm
        vs = [bm.verts.new(p) for p in pts]
        res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(bm, geom=junk, context="VERTS")
        live = [v for v in vs if v.is_valid]
        faces = list({f for v in live for f in v.link_faces})
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                                 edges=list({e for f in faces for e in f.edges}))
        live = [v for v in vs if v.is_valid]
        self._mat({f for v in live for f in v.link_faces}, mat)

    def prism(self, poly, z0, z1, ct, mat, cb=0.0):
        """A block over a convex plan polygon from z0 to z1, the top edge chamfered by ct (and the
        bottom by cb). z1 may be a function of (x, y): a sloped top (concave)."""
        zt = z1 if callable(z1) else (lambda x, y: z1)
        pts = []
        top_in = inset(poly, ct) if ct > 0 else poly
        bot_in = inset(poly, cb) if cb > 0 else poly
        for x, y in bot_in:
            pts.append((x, y, z0))
        for x, y in poly:
            if cb > 0:
                pts.append((x, y, z0 + cb))
            pts.append((x, y, zt(x, y) - ct))
        for x, y in top_in:
            pts.append((x, y, zt(x, y)))
        self.hull(pts, mat)

    def box(self, x0, x1, y0, y1, z0, z1, ct, mat, cb=0.0):
        self.prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, ct, mat, cb)

    def loft(self, rings, mats, cap0=True, cap1=True, smooth=True):
        """A closed tube through rings of equal length; mats[i] between ring i and i + 1."""
        bm = self.bm
        vr = [[bm.verts.new(p) for p in ring] for ring in rings]
        n = len(vr[0])
        if not isinstance(mats, (list, tuple)):
            mats = [mats] * (len(rings) - 1)
        for i, (a, b) in enumerate(zip(vr, vr[1:])):
            for k in range(n):
                j = (k + 1) % n
                self._mat([bm.faces.new((a[k], a[j], b[j], b[k]))], mats[i], smooth)
        if cap0:
            self._mat([bm.faces.new(vr[0])], mats[0], smooth)
        if cap1:
            self._mat([bm.faces.new(vr[-1])], mats[-1], smooth)

    def tube(self, path, r, mat, n=10, rz=None):
        """A round tube of one radius along a 3D path (rotation-minimising frames)."""
        pts = [Vector(p) for p in path]
        rz = r if rz is None else rz
        tans = []
        for i in range(len(pts)):
            t = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
            tans.append(t.normalized())
        up = Vector((0, 0, 1))
        nrm = tans[0].cross(up) if abs(tans[0].dot(up)) < 0.9 else tans[0].cross(Vector((1, 0, 0)))
        nrm.normalize()
        rings = []
        for p, t in zip(pts, tans):
            nrm = (nrm - t * nrm.dot(t)).normalized()
            b = t.cross(nrm)
            rings.append([p + nrm * (r * math.cos(2 * math.pi * (k + 0.5) / n))
                          + b * (rz * math.sin(2 * math.pi * (k + 0.5) / n)) for k in range(n)])
        self.loft(rings, mat)

    def rect_strip(self, path, ups, w, h, mat):
        """A flat bar (w wide, h tall) along a path, its top facing `ups` (one per point)."""
        pts = [Vector(p) for p in path]
        rings = []
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            u = Vector(ups[i]).normalized()
            s = t.cross(u).normalized()
            u = s.cross(t).normalized()
            c = 0.12
            rings.append([p + s * (w / 2) - u * h, p + s * (w / 2) + u * (h - c), p + s * (w / 2 - c) + u * h,
                          p - s * (w / 2 - c) + u * h, p - s * (w / 2) + u * (h - c), p - s * (w / 2) - u * h])
        self.loft(rings, mat, smooth=False)

    def cylinder(self, cx, cy, z0, z1, r, mat, n=16, ct=0.0):
        rings = []
        for z, rr in ((z0, r), (z1 - ct, r), (z1, r - ct)) if ct > 0 else ((z0, r), (z1, r)):
            rings.append([(cx + rr * math.cos(2 * math.pi * k / n), cy + rr * math.sin(2 * math.pi * k / n), z)
                          for k in range(n)])
        self.loft(rings, mat)

    def gear_y(self, cx, cz, y0, y1, r, teeth, mat):
        """An upright toothed disc in the x-z plane, from y0 to y1, its rim chamfered."""
        m = 4 * teeth
        rim = []
        for k in range(m):
            a = 2 * math.pi * k / m
            rr = r if (k % 4) in (1, 2) else r * 0.82
            rim.append((rr * math.cos(a), rr * math.sin(a)))
        c = min(0.12, (y1 - y0) / 4)
        rings = []
        for y, f in ((y0, 0.93), (y0 + c, 1.0), (y1 - c, 1.0), (y1, 0.93)):
            rings.append([(cx + x * f, y, cz + z * f) for x, z in rim])
        self.loft(rings, mat, smooth=False)

    def gear(self, cx, cy, z0, z1, r, teeth, mat):
        m = 4 * teeth
        rim = []
        for k in range(m):
            a = 2 * math.pi * k / m
            rr = r if (k % 4) in (1, 2) else r * 0.84
            rim.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        self.loft([[(x, y, z0) for x, y in rim], [(x, y, z1) for x, y in rim]], mat, smooth=False)


def ring(cx, y, cz, r, n=20, p=2.2, rz=None):
    """A superellipse section across y (power 2 = round), starting at the top."""
    rz = r if rz is None else rz
    e = 2 / p
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        s, c = math.sin(a), math.cos(a)
        out.append((cx + r * math.copysign(abs(s) ** e, s), y, cz + rz * math.copysign(abs(c) ** e, c)))
    return out


# --- the machine --------------------------------------------------------------------------------

# Leg axis (centre x of the left leg, height of its axis) along y; the right leg is mirrored.
# Fitted to the sprite's inner mask (D74): the hip sits at x -5.5 (rows 7-10 stair out to the
# shoulder), the leg barrel at -6 with radius 2 (row 18: columns 15-18 inside the ink).
# Past row 18 the barrel tapers and leans out into the ankle fairing (rows 19-23 inside x -5).
LEG_X = pchip([6.0, 10.5, 13.0, 18.6, 19.6, 23.0], [-5.5, -5.5, -6.0, -6.0, -6.5, -6.5])
LEG_Z = pchip([6.0, 11.5, 16.0, 21.0, 23.0], [4.0, 4.0, 3.4, 1.9, 1.5])
LEG_R = 2.0
HIP_R = 3.4


def leg_r(y):
    return max(1.45, LEG_R - 0.7 * max(0.0, y - 18.6))


def foot_plan(s):
    """The foot's plan (sprite rows 19-26, the inner mask): straight inner edge at column 18 / 28
    (x -5), the heel chamfered from column 14 (row 19) out to column 12 / 33 (rows 20-23, the
    sprite's lit rim there has no ink), then rounding into the toe (rows 24-26) and ending at row 27."""
    pts = [(-5.0, 19.95), (-10.6, 19.95), (-11.0, 20.3), (-11.0, 23.5), (-9.0, 26.5), (-8.0, 27.0), (-5.0, 27.0)]
    return [(-x if s > 0 else x, y) for x, y in pts]


def heel_plan(s):
    """The heel (row 19, columns 14-17 / 28-31): narrower than the foot, so its own block."""
    pts = [(-5.0, 19.0), (-8.9, 19.0), (-9.1, 20.1), (-5.0, 20.1)]
    return [(-x if s > 0 else x, y) for x, y in pts]


def foot_top(y):
    return 3.7 - 0.45 * max(0.0, min(1.0, (y - 20.0) / 4.0))


def build_side(B, s):
    """One leg, hip, pipe and foot. s = -1 left, +1 right (x mirrored)."""
    X = lambda x: -x if s > 0 else x  # noqa: E731  (left-side numbers, mirrored for the right)

    # Hip: ribbed heat-sink end cap, polished ring band, collar, housing; one loft along y.
    # The cap is a stepped dome (the sprite's rows 7-10 stair out by a pixel a row): its ribs grow from
    # radius 1.3 at row 7 to 2.4 at rows 8-9, the ring band and the housing reach 3.2 from row 10.
    st = [(6.95, 0.9, FRAME), (7.1, 1.25, FRAME), (7.4, 1.45, FRAME), (7.7, 1.45, FRAME), (7.8, 1.3, FRAME),
          (7.95, 1.3, FRAME), (8.05, 2.1, FRAME), (8.35, 2.3, FRAME), (8.45, 2.1, FRAME), (8.6, 2.1, FRAME),
          (8.7, 2.4, FRAME), (8.85, 2.4, FRAME),
          (8.95, 2.45, HIPRING), (9.08, 2.55, HIPRING), (9.72, 2.55, HIPRING), (9.85, 2.4, FRAME),
          (10.0, 2.6, HIPRING), (10.05, 3.3, HIPRING), (10.65, 3.3, LEG), (10.8, 3.4, LEG),
          (12.0, 3.4, LEG), (12.7, 3.1, LEG), (13.25, 2.2, LEG), (13.4, 2.05, LEG)]
    rings = [ring(X(LEG_X(y)), y, LEG_Z(y), r) for y, r, _ in st]
    B.loft(rings, [m for _, _, m in st[:-1]])
    # Leg barrel, sinking into the foot; a dark collar at the ankle.
    ys = frange(13.3, 21.6, 0.6)
    B.loft([ring(X(LEG_X(y)), y, LEG_Z(y), leg_r(y)) for y in ys], LEG)
    B.loft([ring(X(LEG_X(y)), y, LEG_Z(y), r) for y, r in ((17.4, 2.0), (17.5, 2.15), (18.1, 2.15), (18.2, 2.0))],
           FRAME)
    B.loft([ring(X(LEG_X(y)), y, LEG_Z(y), r) for y, r in ((13.6, 2.0), (13.7, 2.14), (14.1, 2.14), (14.2, 2.0))],
           HIPRING)
    # Hip mount under the raised hip (closes the side view).
    B.box(X(-7.4) if s < 0 else X(-4.0), X(-4.0) if s < 0 else X(-7.4), 8.3, 12.8, 0.0, 3.4, 0.3, FRAME)
    # A low sill along under the leg (the sprite's dark pixels either side of it, rows 12-17).
    B.box(X(-9.0) if s < 0 else X(-3.9), X(-3.9) if s < 0 else X(-9.0), 12.5, 17.95, 0.0, 1.6, 0.2, FRAME)

    # Light strip along the leg's inner top edge (column 17 / 28) onto the foot's armour.
    path, ups = [], []
    for y in frange(13.9, 24.1, 0.5):
        cx, cz = LEG_X(y), LEG_Z(y)
        dx = -5.5 - cx
        zb = cz + math.sqrt(max(0.0, leg_r(y) ** 2 - dx * dx)) if y < 22.0 else -9
        zf = foot_top(y) if y > 19.0 else -9
        if 18.95 <= y <= 22.6:  # over the ankle fairing (its chamfered top edge sits 0.45 below)
            zf = max(zf, 5.0 - 0.38 * (y - 19.0))
        if zb >= zf:
            n = Vector((X(dx), 0, zb - cz)).normalized()
            path.append((X(-5.5), y, zb + 0.02))
            ups.append(tuple(n))
        else:
            path.append((X(-5.5), y, zf + 0.02))
            ups.append((0, 0, 1))
    B.rect_strip(path, ups, 0.9, 0.18, STRIP)

    # Coolant pipe (one diameter, a bent pipe as in the sprite's L-shaped cyan run): out of a manifold
    # on the hip's inner top, straight out over the hip's crown (row 11, pal 131), down its outer end
    # into a coupling, then (pal 58) forward along the leg's outer edge (column 13 / 32) and into the leg.
    pr = 0.7
    # Its outer face is the plan's edge at rows 11-16 (x -10, inside the ink at column 12 / 33).
    px, py, pe = -9.3, 11.6, 16.2
    zc = LEG_Z(py) + HIP_R + pr + 0.05
    run = fillet_path([(-3.4, py, zc), (px, py, zc), (px, py, 5.0)], 1.0, k=6)
    B.tube([(X(x), y, z) for x, y, z in run], pr, PIPE, n=12)
    flank = fillet_path([(px, py, 5.2), (px, py, 4.0), (px, pe, 3.4), (-7.4, pe, 3.4)], 1.0, k=6)
    B.tube([(X(x), y, z) for x, y, z in flank], pr, CONDUIT, n=12)
    # Coupling at the joint (a collar round the pipe) and a bracket from it to the hip mount.
    B.cylinder(X(px), py, 4.55, 5.45, 0.72, FRAME, n=12, ct=0.12)
    B.box(min(X(-9.0), X(-7.4)), max(X(-9.0), X(-7.4)), py - 0.5, py + 0.5, 2.6, 4.9, 0.2, FRAME)
    # Two pipe clamps along the leg's flank, and the coupling where the pipe turns into the leg.
    for yc in (13.2, 15.0):
        zp = 4.0 + (3.4 - 4.0) * (yc - py) / (pe - py)
        B.box(min(X(-10.0), X(-8.6)), max(X(-10.0), X(-8.6)), yc - 0.28, yc + 0.28, zp - 0.9, zp + 0.9, 0.15, FRAME)
    B.box(X(-9.9) if s < 0 else X(-8.0), X(-8.0) if s < 0 else X(-9.9), 15.7, 16.95, 1.9, 4.5, 0.25, FRAME)
    # Manifold on the hip's inner top where the pipe starts.
    B.box(min(X(-3.85), X(-2.75)), max(X(-3.85), X(-2.75)), py - 0.8, py + 0.8, LEG_Z(py) + 1.5, zc + 0.8, 0.25,
          FRAME)

    # Hydraulic ram along the leg's outer top (45 degrees out from the top) on a bolted saddle plate.
    def leg_pt(y, ang, r):  # a point at radius r round the leg axis, ang degrees out from the top
        a = math.radians(ang)
        return (X(LEG_X(y) - r * math.sin(a)), y, LEG_Z(y) + r * math.cos(a))
    for y0, y1 in ((12.9, 15.4), (16.0, 18.3)):
        rings = []
        for y in frange(y0, y1, 0.6):
            inner = [leg_pt(y, a, LEG_R + 0.02) for a in frange(38.0, 78.0, 5.0)]
            outer = [leg_pt(y, a, LEG_R + 0.3) for a in frange(78.0, 38.0, 5.0)]
            rings.append(inner + outer)
        B.loft(rings, LEG, smooth=False)
        for y in (y0 + 0.4, y1 - 0.4):
            for ang in (64.0, 75.0):
                p0 = Vector(leg_pt(y, ang, LEG_R + 0.28))
                p1 = Vector(leg_pt(y, ang, LEG_R + 0.5))
                B.tube([p0, p1], 0.17, HUB, n=6)
    B.tube([leg_pt(y, 45.0, LEG_R + 0.75) for y in (12.6, 16.4)], 0.5, FRAME, n=12)  # cylinder
    B.tube([leg_pt(y, 45.0, LEG_R + 0.75) for y in (16.2, 19.7)], 0.27, HUB, n=8)  # rod
    for y in (12.5, 19.8):  # clevis lugs
        B.tube([leg_pt(y, 45.0, LEG_R + 0.2), leg_pt(y, 45.0, LEG_R + 1.1)], 0.36, FRAME, n=8)

    # Foot: dark sole, glowing light-bar layer, chamfered armour shoe.
    plan = foot_plan(s)
    B.prism(plan, 0.0, 1.25, 0.25, FOOT, cb=0.15)
    B.prism(heel_plan(s), 0.0, 1.25, 0.25, FOOT, cb=0.15)
    glow = inset(plan, 0.3)
    B.prism(glow, 1.2, 1.8, 0.12, RIM)
    B.prism(inset(heel_plan(s), [0.3, 0.3, 0.0, 0.3]), 1.2, 1.8, 0.12, RIM)
    # Armour: inner edge flush, rear flush, outer edge in by 1 (column 13 / 32), front at row 24.
    shoe = [(-5.0, 19.0), (-8.6, 19.0), (-8.85, 20.0), (-5.0, 20.0)]
    B.prism([(X(x), y) for x, y in shoe], 1.75, lambda x, y: foot_top(y), 0.45, FOOT)
    shoe = [(-5.0, 19.9), (-9.9, 19.9), (-10.2, 20.3), (-10.2, 23.2), (-9.4, 24.0), (-5.0, 24.0)]
    shoe = [(X(x), y) for x, y in shoe]
    B.prism(shoe, 1.75, lambda x, y: foot_top(y), 0.45, FOOT)
    # Ankle fairing: a sloped block from the shoe up round the barrel's end.
    ank = [(-8.4, 18.95), (-5.05, 18.95), (-5.05, 22.6), (-8.4, 22.6)]
    B.prism([(X(x), y) for x, y in ank], 1.75, lambda x, y: 5.0 - 0.38 * (y - 19.0), 0.45, FOOT)
    # Two dark cleats on the sole's outer flank.
    for y0 in (20.2, 22.2):
        B.box(X(-10.95) if s < 0 else X(-10.6), X(-10.6) if s < 0 else X(-10.95), y0, y0 + 1.0, 0.2, 1.1, 0.1, FRAME)


def build_centre(B):
    # Beacon tower: cheek plates either side of the beacon column.
    for s in (-1, 1):
        X = lambda x: -x if s > 0 else x  # noqa: E731
        cheek = [(-3.95, 1.35), (-3.65, 1.05), (-2.2, 1.05), (-2.2, 5.3), (-3.95, 5.3)]
        B.prism([(X(x), y) for x, y in cheek], 0.0, 9.1, 0.55, HEAD)
        # Louvres on the tower front (seen by the game camera) and its outer flank.
        for z in (7.1, 7.75, 8.4):
            B.box(min(X(-3.65), X(-2.45)), max(X(-3.65), X(-2.45)), 5.25, 5.45, z, z + 0.35, 0.06, FRAME)
        for z in (4.2, 5.0, 5.8):
            x0, x1 = (-4.08, -3.9) if s < 0 else (3.9, 4.08)
            B.box(x0, x1, 2.0, 4.6, z, z + 0.4, 0.06, FRAME)
        # Rear (north): a service hatch on each cheek's back face with a vent grille, two ribs above it
        # and a bolted strap below.
        # (The tower's back face is at row 1, y 1.05, inside the sprite's ink row 0; these stand
        # proud of it by at most 0.25.)
        x0, x1 = sorted((X(-3.6), X(-2.4)))
        B.box(x0, x1, 0.93, 1.15, 1.6, 6.6, 0.08, FRAME)
        for z in (2.2, 2.9, 3.6, 4.3, 5.0, 5.7):
            B.box(x0 + 0.2, x1 - 0.2, 0.81, 0.99, z, z + 0.32, 0.04, HUB)
        for z in (7.15, 7.85):
            B.box(x0 - 0.1, x1 + 0.1, 0.89, 1.15, z, z + 0.35, 0.08, FRAME)
        B.box(x0 - 0.1, x1 + 0.1, 0.91, 1.15, 0.5, 1.1, 0.08, FRAME)
        for xb in (x0 + 0.3, x1 - 0.3):
            B.tube([(xb, 1.05, 0.8), (xb, 0.9, 0.8)], 0.14, HUB, n=6)
    B.box(-2.15, 2.15, 1.1, 5.15, 0.0, 8.4, 0.2, FRAME)  # beacon column
    # Its back (north) face: a vent grille of upright slats in a frame, a rib across the top.
    B.box(-1.95, 1.95, 0.98, 1.15, 1.0, 1.4, 0.06, HEAD)
    B.box(-1.95, 1.95, 0.98, 1.15, 6.8, 7.2, 0.06, HEAD)
    for xs in (-1.45, -0.725, 0.0, 0.725, 1.45):
        B.box(xs - 0.2, xs + 0.2, 0.83, 1.15, 1.4, 6.8, 0.07, HEAD)
    B.box(-2.25, 2.25, 0.85, 1.15, 7.45, 7.85, 0.1, HUB)
    # Bezel: four chamfered bars round the glass (the sprite's 4x4 light, columns 21-24, rows 1-4).
    B.box(-2.15, 2.15, 1.1, 1.45, 8.0, 9.35, 0.12, FRAME)
    B.box(-2.15, 2.15, 4.85, 5.15, 8.0, 9.35, 0.12, FRAME)
    B.box(-2.15, -1.8, 1.1, 5.15, 8.0, 9.35, 0.12, FRAME)
    B.box(1.8, 2.15, 1.1, 5.15, 8.0, 9.35, 0.12, FRAME)
    B.box(-1.85, 1.85, 1.35, 4.9, 7.0, 9.15, 0.35, LIGHT)  # the glass beacon, bevelled
    # Shoulder housing: top slopes forward and out (the sprite's shaded rows 5-6).
    pts = []
    for y, hw, zt in ((4.95, 4.45, 7.4), (6.0, 5.5, 6.95)):
        for sx in (-1, 1):
            pts += [(sx * hw, y, 0.0), (sx * hw, y, zt - 1.1), (sx * (hw - 1.1), y, zt)]
    B.hull(pts, SHOULDER)
    for sx in (-1, 1):  # the shoulders run on beside the tube, under the hip caps
        pts = []
        for y, hw, zt in ((5.5, 5.0, 7.1), (7.5, 7.0, 6.75), (8.4, 7.0, 6.5)):
            pts += [(sx * hw, y, 0.0), (sx * hw, y, zt - 1.1), (sx * (hw - 1.1), y, zt),
                    (sx * 2.6, y, 0.0), (sx * 2.6, y, zt - 0.3)]
        B.hull(pts, SHOULDER)
        # Cooling fins on the shoulder's back face, beside the tower.
        for z in (1.6, 2.8, 4.0, 5.2):
            B.box(min(sx * 4.0, sx * 4.85), max(sx * 4.0, sx * 4.85), 5.0, 5.45, z, z + 0.55, 0.12, FRAME)
    # Tube cradle: channel walls, floor, end block.
    for s in (-1, 1):
        x0, x1 = (-3.1, -2.05) if s < 0 else (2.05, 3.1)
        B.box(x0, x1, 6.0, 14.5, 0.0, 6.0, 0.35, FRAME)
    B.box(-2.1, 2.1, 6.0, 14.5, 0.0, 1.8, 0.0, FLOOR)
    B.box(-3.1, 3.1, 14.0, 14.7, 0.0, 5.0, 0.35, FRAME)
    # The glass tube: round, rounded ends, an end collar each side and a strap at mid length.
    tz = 3.9
    B.loft([ring(0.0, y, tz, r, n=20, p=2.0) for y, r in ((6.1, 1.3), (6.3, 1.75), (6.6, 1.95), (13.75, 1.95),
                                                         (14.0, 1.75), (14.2, 1.3))], TUBE)
    B.loft([ring(0.0, y, tz, r, n=20, p=2.0) for y, r in ((5.4, 2.1), (6.25, 2.1), (6.35, 2.05))], FRAME)
    B.loft([ring(0.0, y, tz, r, n=20, p=2.0) for y, r in ((13.95, 2.05), (14.05, 2.12), (14.6, 2.12))], FRAME)
    B.loft([ring(0.0, y, tz, r, n=20, p=2.0) for y, r in ((9.85, 2.02), (10.15, 2.02))], HIPRING)
    # Gearbox between the legs: rounded front (rows 19-20).
    half = [(3.0, 13.4), (3.0, 18.4), (2.7, 18.9), (2.2, 19.5), (1.6, 19.9), (1.1, 20.05)]
    case = half + [(-x, y) for x, y in reversed(half)]
    B.prism(case, 0.0, 1.6, 0.25, FLOOR)
    # Its base plate, out to the legs (the sprite's dark column 19 / 26 at rows 13-17).
    B.box(-4.1, 4.1, 13.4, 17.95, 0.0, 1.2, 0.15, FLOOR)
    # Two upright gears facing the camera (south), each on a boss, either side of the drive shaft.
    B.gear_y(-2.1, 3.1, 15.5, 16.3, 1.9, 10, FRAME)
    B.tube([(-2.1, 15.0, 3.1), (-2.1, 16.85, 3.1)], 0.62, SHOULDER, n=12)
    B.tube([(-2.1, 16.8, 3.1), (-2.1, 17.05, 3.1)], 0.3, HUB, n=8)
    B.gear_y(2.7, 2.7, 16.1, 16.8, 1.5, 8, FRAME)
    B.tube([(2.7, 15.6, 2.7), (2.7, 17.3, 2.7)], 0.5, SHOULDER, n=12)
    B.tube([(2.7, 17.25, 2.7), (2.7, 17.5, 2.7)], 0.25, HUB, n=8)
    B.box(-3.6, -0.6, 14.75, 15.15, 1.5, 3.3, 0.1, SHOULDER)  # bearing blocks behind the gears
    B.box(1.4, 3.9, 15.35, 15.75, 1.5, 3.0, 0.1, SHOULDER)
    B.tube([(0.5, 14.3, 2.6), (0.5, 18.9, 2.2)], 0.45, HUB, n=8)  # drive shaft from the tube's end
    B.cylinder(0.5, 19.0, 1.5, 2.6, 0.75, SHOULDER, n=12, ct=0.15)


def materials(sprite):
    mats = []
    for slot, tag in enumerate(TAGS):
        if slot in GLOWS:
            m = common.palette_material(sprite, PAL[slot], f"nsh2_123_{tag}", metallic=0.0, roughness=0.18,
                                        emission_strength=GLOWS[slot])
        else:
            met, rough = SATIN[slot]
            m = common.palette_material(sprite, PAL[slot], f"nsh2_123_{tag}", metallic=met, roughness=rough)
        mats.append(m)
    return mats


def build(sprite, coll):
    B = Builder()
    build_centre(B)
    for s in (-1, 1):
        build_side(B, s)
    bm = B.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    m = Matrix(((PX, 0, 0, -PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for mat in materials(sprite):
        me.materials.append(mat)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    flat = [p.use_smooth for p in me.polygons]
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(32))
    for p, sm in zip(me.polygons, flat):
        p.use_smooth = sm
    return obj


# --- bake (as the ships: occlusion / edge colour multiplier, roughness / metalness) ---------------

def bake_maps(obj, out_dir, size=1024, samples=64):
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
    col_img = bpy.data.images.new("nsh2_123_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("nsh2_123_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode, slot):
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
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            base, weight = AO.get(slot, AO_DEFAULT)
            v = math_("MINIMUM", math_("ADD", math_("ADD", base, math_("MULTIPLY", occl, weight)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k, tint in enumerate((1.0, 0.98, 0.95)):
                L(math_("MULTIPLY", v, tint), comb.inputs[k])
            L(comb.outputs[0], em.inputs["Color"])
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
        tmps = {m.name: bake_shader(m, mode, slot) for slot, m in enumerate(mats)}
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

    for slot, m in enumerate(mats):
        if slot in GLOWS:
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


def split_open(obj, layout, coll):
    """Cut an outline shell into the pieces without filling the cuts (no outline along the seam)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        out[name] = sh
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = lib.merged_sprite(ROOT, PIECES)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="nsh2_123_bake_"))
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, faces=2400)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    parts = common.split_assembly(obj, layout, coll)  # piece-local: each piece's centre at the origin
    shells = split_open(shell, layout, coll)
    for piece in PIECES:
        t = sum(len(p.vertices) - 2 for p in parts[piece].data.polygons)
        print(f"{piece}: {t} triangles")
        data = common.load_sprite(ROOT, piece)
        common.export_sprite_model(ROOT, [parts[piece], shells[piece]], f"enemies/{piece}", data["sprites"],
                                   image_format=fmt)
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        ref = lib.composite_png(ROOT, layout, Path(tempfile.mkdtemp()) / "assembly.png", 48, 56)
        common.render_preview([obj], str(out), str(ref), size=4, view_px=480)


if __name__ == "__main__":
    main()
