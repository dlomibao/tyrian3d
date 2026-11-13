"""Grey bomber (newsh5.shp 115 / 117 / 119 side by side, 72 x 28 px), design A.

What it is: a twin-boom-less, four-engined straight-wing bomber flying nose-first DOWN the screen
(three rigid sky-layer enemies 24 px apart, +3/+4 px/tick). Read from the sprite (assembly
columns c, rows R; the plane's axis is the edge 36.5, x = c + 0.5 - 36.5 px):
- fuselage (cols 33-39): a round grey body, R 7 to the nose tip at R 26, with a glazed bomb-aimer
  nose (rows 18-22: dark frame lines at x = -2, 0, +2 and lit glass between them), a slim neck
  (rows 5-6) and a tail bullet (rows 1-4) carrying a thin vertical fin (the light line on col 36)
  and a red 1 px-chord tailplane (row 3, +-4.5 px);
- a long straight wing, trailing edge R 10, leading edge R 18 (root fillets to R 9 / R 19),
  span +-33.5 px, low on the fuselage; its inner leading edge painted red in two tiers (rows 13-16
  to x +-12.5, rows 15-16 to x +-16.5), a flap hinge line, the outer panels darker (4);
- big light-grey wingtip nacelles (cols 3-10, x -33.5..-25.5) with red tail cones (rows 7-9) and
  red intake cones (rows 18-20);
- underslung inner engine nacelles (x -23.5..-14.5) showing fore and aft of the wing: grey cowl,
  a red jet pipe out the back (x -16, to R 6) and a red intake lip in front, two red fences on the
  wing over them (cols 16 and 18);
- a bomb under each inner wing (x -9), its nose and finned tail showing fore and aft.

Contract: pieces newsh5-115 / 117 / 119 at (-24, 0) / (0, 0) / (24, 0) px from newsh5-117 (its centre
is the origin), one frame each (115, 117, 119), pal_<index> materials. Outline shell from a sealed
pre-cull copy (islands="outer", D189), sunk under the top surface (D185), split open per piece.

Output: public/models/enemies/newsh5-115|117|119.glb + src/render/spriteModels entries (each piece
at its own origin with its outline shell). Review outputs only behind flags:
    blender -b --factory-startup -P assembly-newsh5-117.py -- [--measure DIR] [--glb FILE]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

BLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BLD))
import common  # noqa: E402

WT = common.repo_root(__file__)
sys.path.insert(0, str(WT / "tools"))
import usp_talon as T  # noqa: E402

NAME = "assembly-newsh5-117"
TAG = "n5b117A"
PIECES = ["newsh5-115", "newsh5-117", "newsh5-119"]
LAYOUT = [("newsh5-115", -24, 0), ("newsh5-117", 0, 0), ("newsh5-119", 24, 0)]
PX = 1 / 12


def to_units(bm):
    """px (x from the axis, R row, z) -> units: X = (x + 0.5) / 12, Y = (14 - R) / 12, Z = z / 12."""
    m = Matrix(((PX, 0, 0, 0.5 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)


# --- materials ----------------------------------------------------------------------------------

class Mats:
    def __init__(self, sprite):
        self.sprite, self.list, self.index = sprite, [], {}

    def get(self, key, idx, metallic=0.55, roughness=0.4, spec=None):
        if key in self.index:
            return self.index[key]
        tag = TAG if key == str(idx) else f"{TAG}-{key}"
        m = common.palette_material(self.sprite, idx, tag, metallic=metallic, roughness=roughness)
        if spec is not None:
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            bsdf.inputs["Specular IOR Level"].default_value = spec
        self.list.append(m)
        self.index[key] = len(self.list) - 1
        return self.index[key]


def make_mats(sprite):
    M = Mats(sprite)
    k = {
        "fuse": M.get("6", 6, metallic=0.5, roughness=0.36),
        "nac": M.get("7", 7, metallic=0.5, roughness=0.34),
        "wing": M.get("5", 5, metallic=0.45, roughness=0.42),
        "wout": M.get("4", 4, metallic=0.45, roughness=0.44),
        "cowl": M.get("4", 4, metallic=0.6, roughness=0.4),
        "bomb": M.get("3", 3, metallic=0.6, roughness=0.4),
        "frame": M.get("2", 2, metallic=0.5, roughness=0.5),
        "glass": M.get("glass", 5, metallic=0.15, roughness=0.08, spec=1.0),
        "red": M.get("69", 69, metallic=0.4, roughness=0.42),
        "redf": M.get("67", 67, metallic=0.4, roughness=0.45),
        "tail": M.get("70", 70, metallic=0.4, roughness=0.42),
        "fence": M.get("71", 71, metallic=0.4, roughness=0.4),
    }
    return M, k


# --- mesh helpers (px) --------------------------------------------------------------------------

def ell(w, v, n, p=2.0):
    """A closed (super)ellipse section: n points (dx, dz), the first at the bottom."""
    out = []
    for i in range(n):
        a = -math.pi / 2 + 2 * math.pi * (i + 0.5) / n
        c, s = math.cos(a), math.sin(a)
        out.append((w * math.copysign(abs(c) ** (2 / p), c), v * math.copysign(abs(s) ** (2 / p), s)))
    return out


def loft_y(bm, stations, paint, cap0=None, cap1=None):
    """stations: [(R, xc, zc, [(dx, dz), ...] or None for a tip point)]. paint(x, R, z) -> material
    for each face (from its centre); cap0 / cap1: material of the end caps (None: no cap)."""
    rings = []
    for R, xc, zc, sec in stations:
        if sec is None:
            rings.append([bm.verts.new((xc, R, zc))])
        else:
            rings.append([bm.verts.new((xc + dx, R, zc + dz)) for dx, dz in sec])
    faces = []
    for a, b in zip(rings, rings[1:]):
        n = max(len(a), len(b))
        for i in range(n):
            j = (i + 1) % n
            if len(a) == 1:
                f = (a[0], b[j], b[i])
            elif len(b) == 1:
                f = (a[i], a[j], b[0])
            else:
                f = (a[i], a[j], b[j], b[i])
            faces.append(bm.faces.new(f))
    for f in faces:
        c = f.calc_center_median()
        f.material_index = paint(c.x, c.y, c.z)
        f.smooth = True
    if cap0 is not None and len(rings[0]) > 2:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = cap0
    if cap1 is not None and len(rings[-1]) > 2:
        f = bm.faces.new(rings[-1])
        f.material_index = cap1
    return rings


def loft_x(bm, stations, paint, cap0=None, cap1=None):
    """stations: [(x, [(R, z), ...])] closed sections across the screen."""
    rings = [[bm.verts.new((x, R, z)) for R, z in sec] for x, sec in stations]
    faces = []
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    for f in faces:
        c = f.calc_center_median()
        f.material_index = paint(c.x, c.y, c.z)
        f.smooth = True
    if cap0 is not None:
        bm.faces.new(list(reversed(rings[0]))).material_index = cap0
    if cap1 is not None:
        bm.faces.new(rings[-1]).material_index = cap1


def tube(bm, pts, ups, w, h, mat, sides=6, caps=True):
    """A small tube along a 3D polyline; ups[i] is the 'up' direction at pts[i] (surface normal)."""
    rings = []
    P = [Vector(p) for p in pts]
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        up = Vector(ups[i]).normalized()
        side = t.cross(up).normalized()
        up = side.cross(t).normalized()
        rings.append([bm.verts.new(p + side * (w * math.cos(2 * math.pi * (k + 0.5) / sides))
                                   + up * (h * math.sin(2 * math.pi * (k + 0.5) / sides))) for k in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            f = bm.faces.new((a[k], a[j], b[j], b[k]))
            f.material_index = mat
            f.smooth = True
    if caps:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat
        bm.faces.new(rings[-1]).material_index = mat


def hullbox(bm, pts, mat, smooth=False):
    vs = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs)
    dead = {v for v in res["geom_interior"] + res["geom_unused"] if isinstance(v, bmesh.types.BMVert)}
    dead |= {v for v in vs if not v.link_faces}
    if dead:
        bmesh.ops.delete(bm, geom=list(dead), context="VERTS")
    faces = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace) and g.is_valid]
    for f in faces:
        f.material_index = mat
        f.smooth = smooth
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=list({v for f in faces for v in f.verts}),
                             edges=list({e for f in faces for e in f.edges}))


def mirror_x(bm, first_vert):
    """Mirror every face built since vertex `first_vert` about x = 0 (the plane's axis)."""
    bm.verts.ensure_lookup_table()
    verts = set(bm.verts[first_vert:])
    faces = [f for f in bm.faces if all(v in verts for v in f.verts)]
    edges = list({e for f in faces for e in f.edges})
    dup = bmesh.ops.duplicate(bm, geom=list(verts) + edges + faces)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def grooves(R, gs, depth=0.14, half=0.16):
    g = 0.0
    for rg in gs:
        u = (R - rg) / half
        if abs(u) < 1:
            g += depth * (1 - u * u) ** 2
    return g


def stations_with(base, extra, half=0.16):
    """Sorted station list: base plus each groove centre and its two flanks."""
    s = set(round(v, 4) for v in base)
    for g in extra:
        s |= {round(g - half, 4), round(g, 4), round(g + half, 4)}
    return sorted(s)


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# --- shape (px) ----------------------------------------------------------------------------------

# Fuselage plan half width by row (the inner mask: tail bullet rows 1-4, neck rows 5-6, body +-3.5).
F_R = [0.75, 1.0, 1.5, 2.3, 3.5, 4.4, 5.0, 5.6, 6.6, 7.5, 8.5, 9.5, 22.8, 23.5, 24.5, 25.3, 25.7, 26.02]
F_W = [0.0, 1.0, 1.75, 2.6, 2.65, 2.4, 1.9, 1.75, 1.8, 2.8, 3.7, 3.85, 3.85, 3.4, 2.55, 1.7, 1.1, 0.0]
_FW = T.pchip(F_R, F_W)
_FZ = T.pchip([0.75, 3.0, 6.0, 9.0, 12.0, 22.0, 26.0], [5.6, 5.5, 5.1, 4.3, 4.0, 4.0, 3.9])
F_GROOVES = [6.9, 13.6, 18.05, 23.3]
ZW = 3.0  # wing chord plane


def fuse_w(R):
    return max(0.0, _FW(R)) if 0.75 < R < 26.02 else 0.0


def fuse_v(R):
    w = fuse_w(R)
    return w * (1.0 if R < 7 else 0.94)


def fuse_top(x, R):
    w, v = fuse_w(R), fuse_v(R)
    if w <= abs(x):
        return _FZ(R)
    return _FZ(R) + v * math.sqrt(1 - (x / w) ** 2)


def build_fuselage(bm, k):
    Rs = stations_with([0.75, 0.85, 1.0, 1.25, 1.5, 1.9, 2.3, 2.9, 3.5, 4.0, 4.4, 4.7, 5.0, 5.3, 5.6, 6.1, 6.6,
                        7.1, 7.5, 8.0, 8.5, 9.0, 9.5, 10.5, 11.5, 12.5, 14.6, 15.6, 16.6, 17.4, 18.5, 19.0,
                        19.5, 20.0, 20.6, 21.2, 21.8, 22.3, 22.8, 23.7, 24.1, 24.5, 24.9, 25.3, 25.5, 25.7,
                        25.86, 25.96, 26.02], F_GROOVES)
    st = []
    for R in Rs:
        w = fuse_w(R)
        if w < 1e-3:
            st.append((R, 0.0, _FZ(R), None))
            continue
        g = grooves(R, F_GROOVES, depth=0.13)
        st.append((R, 0.0, _FZ(R), ell(w - g, fuse_v(R) - g, 28)))

    def paint(x, R, z):
        if 18.1 < R < 23.25 and z > _FZ(R) + 0.35 * fuse_v(R) and abs(x) < 3.3:
            return k["glass"]
        return k["fuse"]
    loft_y(bm, st, paint)


def build_glazing_frames(bm, k):
    """Frames of the glazed nose: three ribs down the top (x = -2, 0, 2, the sprite's dark columns
    34 / 36 / 38, rows 18-22) and three hoops across (R 18.1, 20.6, 23.2)."""
    def surf(x, R, off=0.06):
        w, v, zc = fuse_w(R), fuse_v(R), _FZ(R)
        u = max(-0.999, min(0.999, x / w))
        z = zc + v * math.sqrt(1 - u * u)
        # outward normal of the ellipse section
        n = Vector((x / (w * w), 0.0, (z - zc) / (v * v))).normalized()
        return Vector((x, R, z)) + n * off, n
    for x in (-2.0, 0.0, 2.0):
        pts, ups = [], []
        for i in range(9):
            R = 18.1 + (23.2 - 18.1) * i / 8
            p, n = surf(x, R)
            pts.append(p)
            ups.append(n)
        tube(bm, pts, ups, 0.24, 0.16, k["frame"], sides=6)
    for R in (18.1, 20.6, 23.2):
        w = fuse_w(R) - 0.1
        lim = 0.88
        pts, ups = [], []
        for i in range(11):
            x = -w * lim + 2 * w * lim * i / 10
            p, n = surf(x, R)
            pts.append(p)
            ups.append(n)
        tube(bm, pts, ups, 0.22, 0.15, k["frame"], sides=6)


def build_fin_tail(bm, k):
    # Vertical fin: a tapered blade on the tail bullet's centreline (the sprite's lit col 36, rows 1-4).
    zr = 6.5
    root = [(0.95, zr), (6.6, zr - 0.6)]
    tip = [(1.25, 11.2), (3.0, 11.2)]
    pts = []
    for (R, z), t in ((root[0], 0.28), (root[1], 0.28), (tip[0], 0.16), (tip[1], 0.16)):
        pts += [(-t, R, z), (t, R, z)]
    # rounded leading edge: a mid point
    pts += [(-0.22, 4.4, 9.0), (0.22, 4.4, 9.0)]
    hullbox(bm, pts, k["fuse"])
    # Tailplane (red 70, row 3): a thin chamfered plate, root chord R 1.8-4.6, tip R 3.05-4.0.
    zt = 5.55
    outline = [(0.0, 1.8), (2.6, 2.55), (4.1, 2.95), (4.55, 3.25), (4.55, 3.8), (4.1, 4.02), (2.6, 4.25), (0.0, 4.6)]
    for sgn in (1, -1):
        top, bot = [], []
        for x, R in outline:
            th = 0.26 - 0.08 * x / 4.55
            pts = [(sgn * x, R, zt + th), (sgn * x, R, zt - th)]
            top += pts
        hullbox(bm, top, k["tail"])


# Wing
def wing_le(x):
    ax = abs(x)
    le = 17.95 + 1.05 * (1 - smoothstep(4.25, 4.95, ax))
    le -= 0.6 * math.exp(-((ax - 12.5) / 1.1) ** 2)  # the ink notch at cols 23-24 / 48-49, row 17
    return le


def wing_te(x):
    return 10.0 - 1.0 * (1 - smoothstep(4.25, 4.95, abs(x)))


WING_U = [0.0, 0.06, 0.13, 0.2, 0.27, 0.33, 0.38, 0.45, 0.52, 0.6, 0.66, 0.72, 0.8, 0.86, 0.91, 0.95, 0.975, 0.99, 1.0]
W_GROOVES = [11.35, 15.0]


def wing_section(x):
    """Closed airfoil loop in (R, z): u = 0 at the trailing edge, 1 at the leading edge; upper
    surface TE->LE then lower LE->TE."""
    te, le = wing_te(x), wing_le(x)
    c = le - te
    ax = abs(x)
    t = 0.21 - 0.07 * min(1.0, ax / 29.0)  # thickness ratio (chord 8 px: 1.5 px root, 1.0 px tip)
    us = sorted(set(WING_U) | {round((g - te) / c, 4) for g in W_GROOVES if te < g < le}
                | {round((g - te) / c + d, 4) for g in W_GROOVES for d in (-0.02, 0.02) if te < g < le})
    upper, lower = [], []
    for u in us:
        s = 1 - u  # distance from the LE / chord
        yt = 5 * t * c * (0.2969 * math.sqrt(max(s, 0)) - 0.126 * s - 0.3516 * s * s + 0.2843 * s ** 3 - 0.1036 * s ** 4)
        R = te + u * c
        g = grooves(R, W_GROOVES, depth=0.09, half=0.16) if 0.04 < u < 0.97 else 0.0
        upper.append((R, ZW + 0.15 * yt + yt * 0.95 - g))
        lower.append((R, ZW + 0.15 * yt - yt * 0.55))
    loop = upper + list(reversed(lower[1:-1]))
    return loop


def wing_top(x, R):
    te, le = wing_te(x), wing_le(x)
    if not te <= R <= le:
        return None
    c = le - te
    t = 0.21 - 0.07 * min(1.0, abs(x) / 29.0)
    s = 1 - (R - te) / c
    yt = 5 * t * c * (0.2969 * math.sqrt(max(s, 0)) - 0.126 * s - 0.3516 * s * s + 0.2843 * s ** 3 - 0.1036 * s ** 4)
    return ZW + 0.15 * yt + yt * 0.95


def build_wing(bm, k):
    xs = [0.0, -1.5, -3.0, -3.6, -4.25, -4.6, -4.95, -5.4, -6.2, -7.2, -8.2, -9.4, -10.6, -11.6, -12.1, -12.5,
          -12.9, -13.4, -14.4, -15.4, -16.5, -17.4, -18.4, -19.4, -20.6, -21.8, -23.0, -24.4, -25.8, -27.2, -28.6]

    def paint(x, R, z):
        ax = abs(x)
        top = z > ZW + 0.1
        if (3.4 < ax <= 12.5 and R >= 13.0) or (12.5 < ax <= 16.5 and R >= 15.0):
            if top or R > wing_le(x) - 0.6:
                return k["red"]
        if ax > 20.6 and top:
            return k["wout"]
        return k["wing"]
    loft_x(bm, [(x, wing_section(x)) for x in xs], paint, cap0=k["wing"], cap1=k["wing"])


def build_outer_nacelle(bm, k):
    """Wingtip nacelle (cols 3-10): light grey body, red tail cone (rows 7-9), red intake cone (rows 18-20)."""
    NR = [7.95, 8.1, 8.5, 9.2, 9.8, 10.3, 10.8, 15.5, 16.5, 17.5, 18.5, 19.5, 20.4, 20.8, 21.05]
    NW = [1.15, 1.35, 2.0, 2.6, 3.0, 3.85, 4.05, 4.05, 3.7, 2.85, 2.4, 2.1, 1.9, 1.35, 0.0]
    NX = T.pchip([7.9, 9.9, 10.6, 15.8, 17.5, 19.0, 21.1], [-28.5, -28.9, -29.4, -29.4, -28.9, -28.35, -28.5])
    nw = T.pchip(NR, NW)
    zc = ZW + 0.2
    gro = [9.95, 13.2, 18.8]
    Rs = stations_with([7.95, 8.1, 8.3, 8.5, 8.8, 9.2, 9.5, 10.3, 10.8, 11.5, 12.3, 14.2, 15.0, 15.5, 16.0,
                        16.5, 17.0, 17.5, 18.0, 18.4, 19.4, 19.8, 20.2, 20.5, 20.7, 20.85, 20.95, 21.05], gro)
    st = []
    for R in Rs:
        w = nw(R)
        if R >= 21.04:
            st.append((R, NX(R), zc, None))
            continue
        g = grooves(R, gro, depth=0.13)
        st.append((R, NX(R), zc, ell(w - g, 0.82 * w - g, 24)))

    def paint(x, R, z):
        if R < 9.95:
            return k["red"]
        if R > 18.8:
            return k["redf"]
        return k["nac"]
    loft_y(bm, st, paint, cap0=k["frame"])
    # exhaust: a dark recessed nozzle disc inside the tail cone's rim
    loft_y(bm, [(7.95, NX(7.95), zc, ell(0.95, 0.78, 16)), (8.35, NX(8.3), zc, ell(0.95, 0.78, 16))],
           lambda *a: k["frame"], cap0=k["frame"])


def build_inner_nacelle(bm, k):
    """Underslung engine (x -23.5..-14.5): grey cowl fore and aft of the wing, red intake lip in front
    of its inboard half, red jet pipe out the back at x -16."""
    NR = [6.95, 7.3, 8.0, 9.0, 10.0, 17.0, 18.5, 19.5, 20.05]
    NW = [0.6, 1.7, 2.6, 3.55, 4.15, 4.3, 4.5, 4.1, 3.4]
    nw = T.pchip(NR, NW)
    NX = T.pchip([6.9, 9.0, 12.0, 18.5, 19.5, 20.1], [-19.6, -19.5, -19.25, -19.0, -18.7, -18.6])
    zc = 1.3
    gro = [12.0, 17.3]
    Rs = stations_with([6.95, 7.1, 7.3, 7.6, 8.0, 8.5, 9.0, 9.5, 10.0, 11.0, 13.0, 15.0, 16.4, 18.0, 18.5, 19.0,
                        19.3, 19.6, 19.85, 20.05], gro)
    st = [(R, NX(R), zc, ell(nw(R) - grooves(R, gro), 0.45 * nw(R) - grooves(R, gro), 24, p=2.4)) for R in Rs]

    def paint(x, R, z):
        if R > 19.2 and x > NX(R) + 0.3:
            return k["redf"]
        return k["cowl"]
    loft_y(bm, st, paint, cap0=k["cowl"], cap1=k["frame"])
    # intake lip ring on the inboard half of the front face
    xi = -16.7
    loft_y(bm, [(19.9, xi, zc + 0.1, ell(1.75, 1.25, 16)), (20.25, xi, zc + 0.1, ell(1.75, 1.25, 16)),
                (20.3, xi, zc + 0.1, ell(1.3, 0.85, 16)), (19.95, xi, zc + 0.1, ell(1.3, 0.85, 16))],
           lambda *a: k["redf"], cap1=k["frame"])
    # jet pipe (red 69) out of the back, a dark nozzle in its end
    jx, jz = -16.0, 1.75
    js = [(6.0, ell(1.3, 1.2, 16)), (6.15, ell(1.48, 1.35, 16)), (6.6, ell(1.5, 1.38, 16)), (8.4, ell(1.45, 1.35, 16)),
          (9.0, ell(1.75, 1.45, 16)), (9.6, ell(2.25, 1.5, 16)), (10.6, ell(2.3, 1.5, 16))]
    loft_y(bm, [(R, jx, jz, s) for R, s in js], lambda *a: k["red"], cap1=k["red"])
    loft_y(bm, [(6.0, jx, jz, ell(1.0, 0.9, 16)), (6.5, jx, jz, ell(1.0, 0.9, 16))], lambda *a: k["frame"],
           cap0=k["frame"])


def build_fences(bm, k):
    """Two red fences on the wing over the inner engine (cols 16 and 18: x -20, -18)."""
    for x, r0 in ((-20.0, 12.0), (-18.0, 9.3)):
        pts, ups = [], []
        n = 14
        for i in range(n + 1):
            R = r0 + (17.3 - r0) * i / n
            zt = wing_top(x, R)
            if zt is None:  # behind the trailing edge: over the nacelle's cowl
                zt = 1.3 + 0.45 * 3.9 * math.sqrt(max(0.0, 1 - ((x + 19.4) / 3.9) ** 2)) - 0.05
            pts.append((x, R, zt + 0.12))
            ups.append((0, 0, 1))
        tube(bm, pts, ups, 0.32, 0.32, k["fence"], sides=6)


def build_bomb(bm, k):
    """A bomb under each inner wing (x -8.8), nose and finned tail showing fore and aft."""
    bx, bz = -8.7, 0.95
    BR = [8.0, 8.4, 9.0, 10.0, 11.0, 17.0, 18.2, 18.6, 19.3, 19.8, 20.1, 20.25]
    BW = [0.75, 0.95, 1.3, 1.75, 1.95, 2.0, 2.0, 1.95, 1.65, 1.2, 0.6, 0.0]
    bw = T.pchip(BR, BW)
    Rs = stations_with([8.0, 8.2, 8.4, 8.7, 9.0, 9.5, 10.0, 10.5, 11.0, 14.0, 17.0, 17.8, 18.3, 18.6, 19.0, 19.3,
                        19.6, 19.8, 19.95, 20.1, 20.2, 20.25], [10.6, 17.4], half=0.12)
    st = []
    for R in Rs:
        if R >= 20.25:
            st.append((R, bx, bz, None))
        else:
            w = bw(R) - grooves(R, [10.6, 17.4], depth=0.1, half=0.12)
            st.append((R, bx, bz, ell(w, w, 16)))
    loft_y(bm, st, lambda *a: k["bomb"], cap0=k["frame"])
    # + tail fins: root R 8.0-10.6, tip R 9.0-9.9 at radius 2.55
    for ang in (0, 90, 180, 270):
        a = math.radians(ang)
        dx, dz = math.cos(a), math.sin(a)
        pts = []
        for R, r in ((8.0, 0.5), (10.6, 0.5), (9.9, 2.55), (9.0, 2.55)):
            for t in (-0.11, 0.11):
                pts.append((bx + dx * r - dz * t, R, bz + dz * r + dx * t))
        hullbox(bm, pts, k["bomb"])
    # pylon into the wing
    hullbox(bm, T.cbox(bx - 0.28, bx + 0.28, 11.6, 16.2, bz + 1.4, ZW, 0.1), k["cowl"])


def build(bm, k):
    first = len(bm.verts)
    build_wing(bm, k)
    build_outer_nacelle(bm, k)
    build_inner_nacelle(bm, k)
    build_fences(bm, k)
    build_bomb(bm, k)
    mirror_x(bm, first)
    build_fuselage(bm, k)
    build_glazing_frames(bm, k)
    build_fin_tail(bm, k)


# --- object helpers (copied from the E3 assembly designs; candidates for common.py) --------------

def to_object(name, bm, mats, coll, sharp=40):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    to_units(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(sharp))
    return obj


def cull_hidden(obj, grid=3, ndirs=40):
    """Delete faces no ray from outside can reach (as assembly-newshu-79.py)."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    eps = 1.5e-4
    dead = []
    for f in bm.faces:
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        if len(vs) == 4:
            for i in range(grid):
                for j in range(grid):
                    u, v = (i + 0.5) / grid, (j + 0.5) / grid
                    pts.append(vs[0].lerp(vs[1], u).lerp(vs[3].lerp(vs[2], u), v))
        else:
            for vco in vs[:12]:
                for t in (0.4, 0.9):
                    pts.append(c.lerp(vco, t))
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for p in pts:
            o = p + n * eps
            for d in cand:
                if tree.ray_cast(o, d, 50.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    return len(dead)


def sink_shell(shell, model, margin, reach):
    """Keep the outline shell under the model's top surface (as newshv-10.py, D185)."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    moved = 0
    for v in shell.data.vertices:
        w = mw @ v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for kk in range(12):
            a = 2 * math.pi * kk / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = inv @ Vector((w.x, w.y, zt))
            moved += 1
    shell.data.update()
    print(shell.name, "sunk", moved, "of", len(shell.data.vertices))


def split_open(obj, layout, coll, suffix):
    """split_assembly without filling the cuts (for the outline shell: no ink along the seam)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}{suffix}")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        o = bpy.data.objects.new(f"{name}{suffix}", me)
        coll.objects.link(o)
        for key in obj.keys():
            o[key] = obj[key]
        if len(me.polygons):
            me.shade_smooth()
        out[name] = o
    return out


# --- measuring (behind --measure) ----------------------------------------------------------------

def top_mask(objs, w_px, h_px, centre, out_png, k=4):
    scene = bpy.context.scene
    hidden = {}
    for o in scene.objects:
        hidden[o.name] = o.hide_render
        o.hide_render = o not in objs
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (1, 1, 1)
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x, scene.render.resolution_y = w_px * k, h_px * k
    scene.render.resolution_percentage = 100
    cd = bpy.data.cameras.new("topcam")
    cd.type = "ORTHO"
    cd.ortho_scale = max(w_px, h_px) / 12
    cam = bpy.data.objects.new("topcam", cd)
    scene.collection.objects.link(cam)
    cam.location = (centre[0], centre[1], 30)
    scene.camera = cam
    scene.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in scene.objects:
        if o.name in hidden:
            o.hide_render = hidden[o.name]


def top_flat(objs, w_px, h_px, out_png, k=8):
    """Unlit palette-colour top view (for the per-region colour check)."""
    scene = bpy.context.scene
    hidden = {}
    for o in scene.objects:
        hidden[o.name] = o.hide_render
        o.hide_render = o not in objs
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x, scene.render.resolution_y = w_px * k, h_px * k
    cd = bpy.data.cameras.new("topcam")
    cd.type = "ORTHO"
    cd.ortho_scale = max(w_px, h_px) / 12
    cam = bpy.data.objects.new("topcam", cd)
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 30)
    scene.camera = cam
    scene.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in scene.objects:
        if o.name in hidden:
            o.hide_render = hidden[o.name]


def measure(whole, pieces, outdir):
    import sprite_mask as SM
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    res = {}
    top_mask([whole], 72, 28, (0, 0), outdir / "top_assembly.png")
    idx, colors = SM.load(NAME)
    m = SM.masks(idx, colors)
    res["assembly"] = SM.measure(m, SM.read_png_mask(str(outdir / "top_assembly.png")))
    for name, cx, cy in LAYOUT:
        top_mask([pieces[name]], 24, 28, pieces[name].location[:2], outdir / f"top_{name}.png")
        data = json.loads((WT / "reference" / "models" / name / "sprite.json").read_text())
        frames = [SM._rows(f) for f in data["frames"]]
        for f in data["frames"]:
            idx, colors = SM.load(name, f["index"])
            m = SM.masks(idx, colors, SM.pulse_partners(idx, frames))
            res[f"{name}@{f['index']}"] = SM.measure(m, SM.read_png_mask(str(outdir / f"top_{name}.png")))
    # palette materials: map the flat render's colours back to indices in the sheet script
    top_flat([whole], 72, 28, outdir / "top_flat.png")
    (outdir / "measure.json").write_text(json.dumps(res, indent=1))
    for key, r in res.items():
        print(f"MEASURE {key}: rule grid {r['iou_rule_grid']} rule {r['iou_rule']} edge {r['edge_vs_inner_px']:+.2f}")
    return res


# --- main ---------------------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    sprite = common.load_sprite(WT, PIECES[0])
    for p in PIECES[1:]:
        sprite["colors"].update(common.load_sprite(WT, p)["colors"])
    M, k = make_mats(sprite)

    bm = bmesh.new()
    build(bm, k)
    whole = to_object(NAME, bm, M.list, coll)
    print("whole tris", sum(len(p.vertices) - 2 for p in whole.data.polygons))
    bpy.context.view_layer.update()

    shell_whole = common.outline_shell(whole, coll, voxel=0.014, faces=7000, smooth=6, inside=0.004,
                                       islands="outer")
    sink_shell(shell_whole, whole, margin=0.02, reach=0.05)
    shells = split_open(shell_whole, LAYOUT, coll, "_outline")
    for o in shells.values():
        o["tyrian_outline"] = True

    pieces = common.split_assembly(whole, LAYOUT)
    info = {}
    for name, cx, cy in LAYOUT:
        n = cull_hidden(pieces[name])
        me = pieces[name].data
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(40))
        info[name] = {"tris": sum(len(p.vertices) - 2 for p in me.polygons), "culled": n,
                      "shell_faces": len(shells[name].data.polygons)}
        print(name, info[name])
        if not shells[name].data.polygons:
            raise SystemExit(f"{name}: empty outline shell")
    for name, cx, cy in LAYOUT:
        pieces[name].location = (cx / 12, -cy / 12, 0)
        shells[name].location = (cx / 12, -cy / 12, 0)
    bpy.context.view_layer.update()

    if "--measure" in argv:
        measure(whole, pieces, argv[argv.index("--measure") + 1])
    bpy.data.objects.remove(whole, do_unlink=True)
    bpy.data.objects.remove(shell_whole, do_unlink=True)

    # The game contract: one glb + spriteModels entry per piece, each at its own origin with its shell.
    for name, cx, cy in LAYOUT:
        objs = [pieces[name], shells[name]]
        for o in objs:
            o.location = (0, 0, 0)
        bpy.context.view_layer.update()
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, objs, f"enemies/{name}", data["sprites"])
        for o in objs:
            o.location = (cx / 12, -cy / 12, 0)
    bpy.context.view_layer.update()
    if "--glb" in argv:  # review output only: the three pieces placed as in the layout
        allobjs = [o for name in PIECES for o in (pieces[name], shells[name])]
        common.export_glb(allobjs, Path(argv[argv.index("--glb") + 1]))
    print("done", json.dumps(info))


if __name__ == "__main__":
    main()
