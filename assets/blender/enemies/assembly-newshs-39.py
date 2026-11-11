"""Black glass orb on brown claws (newshs.shp 39/41 over 77/79, 2x2 pieces = 48 x 56 px): a 3D
version of its sprites, built as engineered cross-sections.

The machine (read off the sprite):
  - a black glass ORB (plan a superellipse, 31 x 28.6 px, near-hemispherical in height) with an
    equator BAND that carries the claws and a slotted vent plate on its rear (north) face; the big
    white glint, the grey flecks and the lower-right crescent are sheen, not geometry (rubric);
  - a dark CRADLE plinth the orb sits in, with two brown horn LUGS;
  - two brown side LEGS (left 21, right 19) from band knuckles, knee seam at row 28.5;
  - two taupe HORNS (164) from collars on the cradle down to tips on the deck, banded at the root;
  - a brown YOKE beam (rows 35-40) with a four-rib grille;
  - the LAUNCH BAY: a pit sunk into the deck with a coaming lip and, on frames 39-79, a raised black
    glass ball in a ringed collar with two bolt lugs (the sprite's small black ball with a white
    glint); on 81/83 the ball is pink (69) and half risen, on 85/87 up on its piston, bright (75);
  - the stone FLOOR plate under it all, painted per pixel from the sprite: built for the review
    renders only and not exported (D130), since the game draws the tile's ground in HD and the plate
    showed as grey pixel cells on it. The machine and the bay's pit and coaming stand on the ground.

Built whole and cut into the pieces with split_assembly; exports newshs-39, -41, -77, -77-f2 (frames
81, 85), -79, -79-f2 (83, 87), each with its piece at the origin.

Run: blender --background --python assets/blender/enemies/assembly-newshs-39.py
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from usp_talon import pchip  # noqa: E402

HERE = Path(__file__).resolve().parent
WT = common.repo_root(__file__)
NAME = "assembly-newshs-39"
TAG = "nshs39"
PX = 1 / 12
W, H = 48, 56
MACHINE = [
    "000000000000000000000000000000000000000000000000",
    "000000000000000000000000000000000000000000000000",
    "000000000000000000000000000000000000000000000000",
    "000000000000000000000000000000000000000000000000",
    "000000000000000011111111111000000000000000000000",
    "000000000000001111111111111110000000000000000000",
    "000000000000111111111111111111100000000000000000",
    "000000000011111111111111111111111000000000000000",
    "000000000111111111111111111111111100000000000000",
    "000000001111111111111111111111111110000000000000",
    "000000011111111111111111111111111111000000000000",
    "000000011111111111111111111111111111000000000000",
    "000000111111111111111111111111111111100000000000",
    "000000111111111111111111111111111111100000000000",
    "000001111111111111111111111111111111110000000000",
    "000001111111111111111111111111111111110000000000",
    "000001111111111111111111111111111111110000000000",
    "000001111111111111111111111111111111110000000000",
    "000001111111111111111111111111111111110000000000",
    "000001111111111111111111111111111111110000000000",
    "000001111111111111111111111111111111110000000000",
    "000001111111111111111111111111111111110000000000",
    "000001111111111111111111111111111111110000000000",
    "000111111111111111111111111111111111111100000000",
    "001111111111111111111111111111111111111110000000",
    "001111111111111111111111111111111111111110000000",
    "011111111111111111111111111111111111111111000000",
    "011111111111111111111111111111111111111111000000",
    "011111111111111111111111111111111111111111000000",
    "011111111111111111111111111111111111111111000000",
    "011111111111111111111111111111111111111111000000",
    "011111111111111111111111111111111111111111000000",
    "011111111111111111111111111111111111111111000000",
    "011111111111111111111111111111111111111111000000",
    "001111111111111111111111111111111111111110000000",
    "001011111111111111111111111111111111111010000000",
    "000011111111111111111111111111111111111000000000",
    "000011111111111111111111111111111111110000000000",
    "000011111111111111111111111111111111100000000000",
    "000001111111111111111111111111111111100000000000",
    "000001111111111111111111111111111111100000000000",
    "000001111111111111111111111111111111100000000000",
    "000000111111000111111111111111111111100000000000",
    "000000011111011111111111111111111111000000000000",
    "000000011111010111111111111111111111000000000000",
    "000000001111000111111111111111111111000000000000",
    "000000011111000111111111111111111111000000000000",
    "000000000000000111111111111111111000000000000000",
    "000000000000000011111111111111111000000000000000",
    "000000000000000001111111111111110000000000000000",
    "000000000000000000111111111111000000000000000000",
    "000000000000000000111111111111110000000000000000",
    "000000000000000000011111101000000000000000000000",
    "000000000000000000000000000000000000000000000000",
    "000000000000000000000000000000000000000000000000",
    "000000000000000000000000000000000000000000000000",
]  # 1 where the sprite shows the machine (not stone floor)
FLOOR = 0.36                     # top of the stone floor plate, px (lib_b073 FLOOR 0.03 u)
PIECES = [("newshs-39", 0, 0), ("newshs-41", 24, 0), ("newshs-77", 0, 28), ("newshs-79", 24, 28)]
LAYOUT = [(n, c0 + 12 - W / 2, r0 + 14 - H / 2) for n, c0, r0 in PIECES]   # piece centres, px

# --- the sprite --------------------------------------------------------------------------------
REF = WT / "reference" / "models"


def load_sprite():
    cols, grids = {}, []
    data = {n: json.loads((REF / n / "sprite.json").read_text()) for n, _, _ in PIECES}
    for d in data.values():
        cols.update(d["colors"])
    for k in range(3):
        g = [[-1] * W for _ in range(H)]
        for n, c0, r0 in PIECES:
            for r, row in enumerate(data[n]["frames"][k]["pixels"]):
                for c, v in enumerate(row.split()):
                    g[r0 + r][c0 + c] = int(v)
        grids.append(g)
    return {"name": NAME, "colors": cols}, grids


SPRITE, GRIDS = load_sprite()
G0 = GRIDS[0]


def luma(i):
    r, g, b = SPRITE["colors"][str(i)]
    return 0.299 * r + 0.587 * g + 0.114 * b


def trace(sel, rows, cols):
    """Per row: (row centre, left edge, right edge) of the pixels sel(v, r, c) in the column range."""
    out = []
    for r in rows:
        xs = [c for c in cols if sel(G0[r][c], r, c)]
        if xs:
            out.append([r + 0.5, min(xs), max(xs) + 1.0])
    return out


def smooth_trace(t, k=1):
    """[1, 2, 1] filter on the edges (ends kept): pixel stairs -> a smooth line through them."""
    for _ in range(k):
        n = [row[:] for row in t]
        for i in range(1, len(t) - 1):
            for j in (1, 2):
                n[i][j] = (t[i - 1][j] + 2 * t[i][j] + t[i + 1][j]) / 4
        t = n
    return t


def P(c, r, z):
    """Sprite px (column c east, row r south, z up) -> Blender units, origin = assembly centre."""
    return Vector(((c - W / 2) * PX, (H / 2 - r) * PX, z * PX))


# --- materials ---------------------------------------------------------------------------------
class Mats:
    def __init__(self):
        self.list, self.slots = [], {}

    def __call__(self, index, metallic=0.6, roughness=0.4):
        key = (index, metallic, roughness)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(SPRITE, index, f"{TAG}_{len(self.list)}",
                                                     metallic=metallic, roughness=roughness))
        return self.slots[key]

    def glass(self, index):
        return self(index, metallic=0.15, roughness=0.08)

    def stone(self, index):
        return self(index, metallic=0.05, roughness=0.85)


M = Mats()


# --- mesh builder ------------------------------------------------------------------------------
class Mesh:
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()

    def face(self, vs, mat, smooth):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        f.smooth = smooth
        return f

    def loft(self, rings, mats, smooth=True, cap0=True, cap1=True, cap_mat=None):
        """rings: lists of (c, r, z) with the same count, closed loops. mats: one index or one per
        segment between rings."""
        vs = [[self.bm.verts.new(P(*p)) for p in ring] for ring in rings]
        n = len(rings[0])
        for i in range(len(vs) - 1):
            m = mats[i] if isinstance(mats, (list, tuple)) else mats
            for k in range(n):
                self.face([vs[i][k], vs[i][(k + 1) % n], vs[i + 1][(k + 1) % n], vs[i + 1][k]], m, smooth)
        cm = cap_mat if cap_mat is not None else (mats[0] if isinstance(mats, (list, tuple)) else mats)
        for flag, ring, src in ((cap0, vs[0], rings[0]), (cap1, vs[-1], rings[-1])):
            if not flag:
                continue
            ctr = self.bm.verts.new(P(*[sum(p[j] for p in src) / len(src) for j in range(3)]))
            for k in range(n):
                self.face([ring[k], ring[(k + 1) % n], ctr], cm, False)

    def finish(self, coll, sharp=38.0, recalc=True):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        if recalc:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for m in M.list:
            me.materials.append(m)
        if sharp:
            me.set_sharp_from_angle(angle=math.radians(sharp))
        obj = bpy.data.objects.new(self.name, me)
        coll.objects.link(obj)
        return obj


def superellipse(a, b, p, n, phase=0.0):
    pts = []
    for k in range(n):
        t = 2 * math.pi * (k + phase) / n
        c, s = math.cos(t), math.sin(t)
        pts.append((a * math.copysign(abs(c) ** (2 / p), c), b * math.copysign(abs(s) ** (2 / p), s)))
    return pts


def poly_offset(poly, d):
    """Mitred offset of a closed polygon (c, r): d > 0 moves the edges inward."""
    area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
               for i in range(len(poly))) / 2
    s = 1 if area > 0 else -1
    out = []
    n = len(poly)
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0 = Vector((-e0.y, e0.x)) * s
        n1 = Vector((-e1.y, e1.x)) * s
        bis = (n0 + n1)
        if bis.length < 1e-6:
            bis = n0
        bis.normalize()
        cosh = max(0.35, bis.dot(n0))
        q = p1 + bis * (d / cosh)
        out.append((q.x, q.y))
    return out


def prism(mesh, poly, z0, z1, mat, ch=0.4, top_mat=None, smooth=False):
    """A block over a convex-ish plan polygon, its top edge chamfered by ch."""
    rings = [[(c, r, z0) for c, r in poly], [(c, r, z1 - ch) for c, r in poly],
             [(c, r, z1) for c, r in poly_offset(poly, ch)]]
    mesh.loft(rings, [mat, mat], smooth=smooth, cap_mat=mat)
    if top_mat is not None:
        bm = mesh.bm
        bm.faces.ensure_lookup_table()
        nverts = len(poly)
        for f in bm.faces[-nverts:]:
            f.material_index = top_mat


def cylinder(mesh, a, b, rad, mat, n=12, smooth=True, ch=0.0):
    """A cylinder between points a, b (px) with optional end chamfer."""
    A, B = Vector(a), Vector(b)
    t = (B - A).normalized()
    u = t.orthogonal().normalized()
    w = t.cross(u)
    def ring(p, rr):
        return [tuple(p + rr * (math.cos(2 * math.pi * k / n) * u + math.sin(2 * math.pi * k / n) * w)) for k in range(n)]
    if ch > 0:
        rings = [ring(A, rad - ch), ring(A + t * ch, rad), ring(B - t * ch, rad), ring(B, rad - ch)]
    else:
        rings = [ring(A, rad), ring(B, rad)]
    mesh.loft(rings, mat, smooth=smooth)


def lathe(mesh, cx, cr, prof, mats, n=32, sx=1.0, sy=1.0, smooth=True, cap0=True, cap1=True):
    """Profile [(radius, z)] revolved round the vertical axis at (cx, cr), plan scaled sx, sy."""
    rings = []
    for rad, z in prof:
        rings.append([(cx + rad * sx * math.cos(2 * math.pi * k / n), cr - rad * sy * math.sin(2 * math.pi * k / n), z)
                      for k in range(n)])
    mesh.loft(rings, mats, smooth=smooth, cap0=cap0, cap1=cap1)


# --- the orb, band and cradle ---------------------------------------------------------------------
ORB = dict(c=21.5, r=19.3, a=15.55, b=14.3, p=2.3, zc=6.0, up=14.2, dn=5.6)
CRADLE = dict(c=21.5, r=24.4, a=15.9, b=11.4, p=2.4, z=3.2)


def plan_radius(a, b, p, t):
    c, s = abs(math.cos(t)), abs(math.sin(t))
    return 1.0 / (((c / a) ** p + (s / b) ** p) ** (1.0 / p))


def build_orb(mesh):
    o = ORB
    n, nr = 72, 18
    glass = M.glass(1)
    rings = []
    for j in range(nr + 1):
        phi = -math.pi / 2 + math.pi * j / nr
        k = math.cos(phi)
        z = o["zc"] + (o["up"] if phi > 0 else o["dn"]) * math.sin(phi)
        ring = []
        for i in range(n):
            t = 2 * math.pi * i / n
            R = (plan_radius(o["a"], o["b"], o["p"], t) - 0.35) * max(k, 1e-3)
            ring.append((o["c"] + R * math.cos(t), o["r"] - R * math.sin(t), z))
        rings.append(ring)
    mesh.loft(rings[1:-1], glass, smooth=True)   # poles closed by the caps
    # equator band: dark satin, a groove (panel line) round its middle; its outer face is the plan
    band, groove = M(2, 0.55, 0.35), M(1, 0.5, 0.5)
    prof = [(-0.6, -1.1), (0.0, -0.85), (0.0, -0.12), (-0.12, -0.05), (-0.12, 0.05), (0.0, 0.12), (0.0, 0.85),
            (-0.6, 1.1)]
    rings = []
    for dr, dz in prof:
        ring = []
        for i in range(n):
            t = 2 * math.pi * i / n
            R = plan_radius(o["a"], o["b"], o["p"], t) + dr
            ring.append((o["c"] + R * math.cos(t), o["r"] - R * math.sin(t), o["zc"] + dz))
        rings.append(ring)
    mesh.loft(rings, [band, band, groove, groove, groove, band, band], smooth=False, cap0=False, cap1=False)


def build_vent(mesh):
    """Slotted vent plate on the rear (north) face of the orb's band: a dark backing with four ribs."""
    plate, slot, rib = M(2, 0.6, 0.35), M(17, 0.3, 0.6), M(18, 0.6, 0.35)
    r_out = ORB["r"] - ORB["b"] + 0.02            # the band's north face (r grows south)
    prism(mesh, [(17.9, r_out + 0.55), (25.1, r_out + 0.55), (25.1, r_out + 1.1), (17.9, r_out + 1.1)], 3.9, 8.1,
          plate, ch=0.1)
    prism(mesh, [(18.4, r_out + 0.2), (24.6, r_out + 0.2), (24.6, r_out + 0.8), (18.4, r_out + 0.8)], 4.5, 7.5,
          slot, ch=0.05)
    for k in range(4):
        c0 = 18.7 + k * 1.55
        prism(mesh, [(c0, r_out + 0.05), (c0 + 0.8, r_out + 0.05), (c0 + 0.8, r_out + 0.8), (c0, r_out + 0.8)],
              4.7, 7.3, rib, ch=0.12)


def build_cradle(mesh):
    k = CRADLE
    n = 64
    dark, bolt = M(1, 0.55, 0.45), M(2, 0.7, 0.3)
    def ring(dr, z):
        out = []
        for i in range(n):
            t = 2 * math.pi * i / n
            R = plan_radius(k["a"], k["b"], k["p"], t) + dr
            out.append((k["c"] + R * math.cos(t), k["r"] - R * math.sin(t), z))
        return out
    prof = [(0.0, FLOOR - 0.3), (0.0, 1.25), (-0.25, 1.45), (0.0, 1.65), (0.0, k["z"] - 0.55), (-0.55, k["z"]),
            (-2.2, k["z"])]
    mesh.loft([ring(dr, z) for dr, z in prof], dark, smooth=False)
    # bolt heads round the top flat, only where the orb doesn't hide them
    o = ORB
    for i in range(18):
        t = 2 * math.pi * (i + 0.5) / 18
        R = plan_radius(k["a"], k["b"], k["p"], t) - 1.35
        c, r = k["c"] + R * math.cos(t), k["r"] - R * math.sin(t)
        to = math.atan2(-(r - o["r"]), c - o["c"])
        if math.hypot(c - o["c"], r - o["r"]) < plan_radius(o["a"], o["b"], o["p"], to) + 0.3:
            continue
        cylinder(mesh, (c, r, k["z"] - 0.05), (c, r, k["z"] + 0.35), 0.42, bolt, n=6, smooth=False)


def build_lugs(mesh):
    """Brown horn lugs on the cradle front (sprite (13, 32-33) and (29, 32-33): 18/17, 19/17)."""
    lug = M(18)
    for c0 in (12.55, 28.55):
        prism(mesh, [(c0, 31.8), (c0 + 1.5, 31.8), (c0 + 1.5, 34.0), (c0, 34.0)], FLOOR - 0.2, 4.2, lug, ch=0.35)
        cylinder(mesh, (c0 - 0.15, 32.6, 3.3), (c0 + 1.65, 32.6, 3.3), 0.55, M(17), n=10)


# --- claws ---------------------------------------------------------------------------------------
def loft_rows(mesh, tr, zf, hf, mats_of, p=2.0, n=16, step=0.25, r0=None, r1=None, grow=None):
    """Loft along the sprite rows. tr: smoothed trace [(row centre, left, right)]; zf(r), hf(r):
    centre height and half height; mats_of(r): material per station segment."""
    rs = [t[0] for t in tr]
    L = pchip(rs, [t[1] for t in tr])
    R = pchip(rs, [t[2] for t in tr])
    r0 = rs[0] - 0.5 if r0 is None else r0
    r1 = rs[-1] + 0.5 if r1 is None else r1
    st = []
    r = r0
    while r < r1 - 1e-6:
        st.append(r)
        r += step
    st.append(r1)
    rings, mats = [], []
    unit = superellipse(1.0, 1.0, p, n, phase=0.5)
    for i, r in enumerate(st):
        rr = min(max(r, rs[0]), rs[-1])
        a, b = L(rr), R(rr)
        taper = 1.0
        if r < rs[0]:
            taper = max(0.35, 1 - (rs[0] - r) / 1.2)
        if r > rs[-1]:
            taper = max(0.25, 1 - (r - rs[-1]) / 0.8)
        cx, hw = (a + b) / 2, max(0.15, (b - a) / 2 * taper + (grow(r) if grow else 0.0))
        zc, hh = zf(r), max(0.15, hf(r) * taper)
        rings.append([(cx + hw * u, r, zc + hh * v) for u, v in unit])
        if i:
            mats.append(mats_of((r + st[i - 1]) / 2))
    mesh.loft(rings, mats, smooth=True)
    return L, R


def build_legs(mesh):
    for side in ("L", "R"):
        if side == "L":
            tr = trace(lambda v, r, c: 16 <= v <= 25, range(22, 36), range(0, 8))
            colour = 21
        else:
            tr = trace(lambda v, r, c: 16 <= v <= 25, range(22, 36), range(36, 44))
            colour = 19
        tr = smooth_trace(tr)
        zf = pchip([22.6, 24.0, 26.0, 28.5, 31.0, 33.0, 34.6, 35.6], [6.6, 7.4, 7.5, 6.7, 4.9, 3.1, 1.7, 1.0])
        hf = pchip([22.6, 24.0, 26.0, 28.5, 31.0, 33.0, 34.6, 35.6], [1.4, 1.6, 1.95, 2.05, 1.85, 1.45, 1.05, 0.7])
        body, seam = M(colour), M(17)
        knee = lambda r: 1.07 if 28.25 <= r <= 28.75 else 1.0
        L, R = loft_rows(mesh, tr, zf, lambda r: hf(r) * knee(r), lambda r: seam if 28.25 <= r <= 28.75 else body,
                         p=3.0, n=16, r1=35.05, grow=lambda r: (knee(r) - 1) * 2.0)
        # knee groove: a thin ring of the seam colour proud of nothing (the loft takes 17 there)
        # knuckle on the band where the leg springs (horizontal pin, axis east-west)
        top = tr[0][0]
        cxt = (L(top) + R(top)) / 2
        if side == "L":
            cylinder(mesh, (cxt - 0.9, 24.0, 6.8), (ORB["c"] - 13.6, 24.0, 6.4), 1.1, M(18), n=14, ch=0.25)
        else:
            cylinder(mesh, (ORB["c"] + 13.6, 24.0, 6.4), (cxt + 0.9, 24.0, 6.8), 1.1, M(18), n=14, ch=0.25)
        # knee hinge: a round boss on the outer flank at the seam (row 28.5), flush with the plan
        kz = zf(28.5)
        if side == "L":
            xo = L(28.5) + 0.1
            cylinder(mesh, (xo, 28.5, kz), (xo + 1.6, 28.5, kz), 1.35, M(17), n=14, ch=0.2)
        else:
            xo = R(28.5) - 0.1
            cylinder(mesh, (xo - 1.6, 28.5, kz), (xo, 28.5, kz), 1.35, M(17), n=14, ch=0.2)
        # foot pad on the deck under the tip
        end = tr[-1][0]
        fc = (L(end) + R(end)) / 2
        lathe(mesh, fc, end - 0.3, [(0.001, FLOOR - 0.05), (1.0, FLOOR - 0.05), (1.0, FLOOR + 0.35), (0.7, FLOOR + 0.6),
                                    (0.001, FLOOR + 0.6)], M(18), n=12, smooth=False)


def build_horns(mesh):
    root, body = M(161), M(164)
    for side in ("L", "R"):
        cols = range(0, 22) if side == "L" else range(22, 44)
        tr = trace(lambda v, r, c: 160 <= v <= 167, range(29, 45), cols)
        for t in tr:   # the dark pixel between claw and horn is the horn's shaded flank
            if side == "L" and t[0] < 36.5:
                t[1] -= 0.6
            if side == "R" and t[0] < 37.5:
                t[2] += 0.6
        tr = smooth_trace(tr, 2)
        rs = [t[0] for t in tr]
        ctr = pchip(rs, [(t[1] + t[2]) / 2 for t in tr])
        wid = pchip(rs, [t[2] - t[1] for t in tr])
        r_end = rs[-1] + 0.5
        zk_r = [28.6, 30.5, 32.5, 35.0, 37.5, 40.0, 42.0, r_end]
        zk_z = [3.4, 4.6, 4.7, 4.0, 2.9, 1.7, 1.0, 0.55]
        zf = pchip(zk_r, zk_z)

        def hf(r, ctr=ctr, wid=wid, zf=zf):
            rr = min(max(r, rs[0]), rs[-1])
            dc = (ctr(rr + 0.3) - ctr(rr - 0.3)) / 0.6
            cos_phi = 1 / math.sqrt(1 + dc * dc)
            d = wid(rr) * cos_phi           # true diameter of the round tusk
            return min(d / 2, zf(r) - 0.05 + 0.3)
        loft_rows(mesh, tr, zf, hf, lambda r: root if r < 30.0 else body, p=2.0, n=16, r0=28.6, r1=r_end)


# --- the yoke --------------------------------------------------------------------------------------
YOKE_L = [(12.0, 35.0), (17.3, 35.0), (18.25, 35.9), (18.25, 40.0), (10.0, 40.0), (10.0, 37.3), (11.0, 35.7)]
YOKE_R = [(26.0, 35.0), (31.0, 35.0), (32.1, 36.0), (32.6, 38.4), (32.2, 40.0), (28.1, 40.0), (25.85, 38.6)]


def split_poly(poly, c_cut, gap):
    """Two halves of a convex plan polygon either side of column c_cut, a gap between them."""
    def clip(pts, keep_left, cc):
        out = []
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            ina = (a[0] <= cc) if keep_left else (a[0] >= cc)
            inb = (b[0] <= cc) if keep_left else (b[0] >= cc)
            if ina:
                out.append(a)
            if ina != inb:
                t = (cc - a[0]) / (b[0] - a[0])
                out.append((cc, a[1] + t * (b[1] - a[1])))
        return out
    return clip(poly, True, c_cut - gap / 2), clip(poly, False, c_cut + gap / 2)


def build_yoke(mesh):
    body, slot, rib, joint = M(19), M(17), M(21), M(17)
    z1 = 3.6
    for poly, cut in ((YOKE_L, 14.4), (YOKE_R, 29.0)):
        a, b = split_poly(poly, cut, 0.3)
        prism(mesh, a, FLOOR - 0.2, z1, body, ch=0.5)
        prism(mesh, b, FLOOR - 0.2, z1, body, ch=0.5)
        j0, j1 = split_poly(poly, cut, 0.0)
        # the joint between the halves, sunk 0.45 px (a modelled panel line)
        lo = [(c, r) for c, r in poly_offset(poly, 0.25)]
        mid = [p for p in split_poly(split_poly(lo, cut - 0.2, 0.0)[1], cut + 0.2, 0.0)[0]]
        if len(mid) >= 3:
            prism(mesh, mid, FLOOR - 0.2, z1 - 0.45, joint, ch=0.1)
    # grille housing between the blocks: slots (17) between four ribs (21) at cols 19, 21, 23, 25
    prism(mesh, [(18.0, 35.85), (26.1, 35.85), (26.1, 38.0), (18.0, 38.0)], FLOOR - 0.2, 2.9, slot, ch=0.25)
    for c in (19, 21, 23, 25):
        prism(mesh, [(c + 0.08, 35.95), (c + 0.92, 35.95), (c + 0.92, 37.9), (c + 0.08, 37.9)], 2.0, 3.35, rib, ch=0.18)


# --- the launch bay ----------------------------------------------------------------------------------
BAY = [(7.9, 39.0), (10.0, 39.0), (10.0, 40.0), (18.0, 40.0), (18.0, 39.0), (19.0, 38.0), (26.0, 38.0),
       (28.0, 39.0), (28.0, 40.0), (32.0, 40.0), (32.3, 39.0), (33.0, 38.0), (35.0, 38.0), (36.0, 39.5),
       (37.0, 40.0), (37.0, 42.5), (36.2, 43.2), (36.0, 46.0), (35.0, 47.0), (33.0, 47.0), (33.0, 48.6),
       (32.0, 49.8), (31.4, 51.4), (29.5, 52.1), (25.2, 52.1), (24.8, 53.0),
       (19.4, 53.0), (18.4, 51.6), (18.0, 50.2), (17.0, 49.0), (16.0, 48.0), (15.3, 47.3), (15.3, 41.7),
       (11.7, 41.7), (11.7, 47.0), (7.2, 47.0), (6.8, 45.0), (6.9, 42.6), (7.5, 41.6)]
PIT_Z = 0.02
LIP = 0.8


def chaikin(poly, k=1):
    for _ in range(k):
        out = []
        n = len(poly)
        for i in range(n):
            a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
            out += [tuple(a.lerp(b, 0.25)), tuple(a.lerp(b, 0.75))]
        poly = out
    return poly


BAY_S = chaikin(BAY, 1)
REMOVED = set()


def inside(poly, x, y):
    c = False
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def dist_poly(poly, x, y):
    best = 1e9
    n = len(poly)
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        p = Vector((x, y))
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
        best = min(best, (a + ab * t - p).length)
    return best


def bay_removed():
    """The deck pixels the pit replaces: those whose centre is inside the bay outline (so the pit is
    exactly the sprite's dark pixels, row by row)."""
    return {(c, r) for r in range(H) for c in range(W) if inside(BAY_S, c + 0.5, r + 0.5)}


def build_pit(mesh, removed):
    """The pit floor (z 0.02) under the removed deck pixels and its walls up to the deck, faces
    oriented by hand (an open surface)."""
    pit = M(1, 0.3, 0.6)
    bm = mesh.bm
    for c, r in sorted(removed):
        vs = [bm.verts.new(P(x, y, PIT_Z)) for x, y in ((c, r + 1), (c + 1, r + 1), (c + 1, r), (c, r))]
        mesh.face(vs, pit, False)
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (c + dc, r + dr) in removed:
                continue
            if dc:
                x = c + (1 if dc > 0 else 0)
                e = [(x, r), (x, r + 1)]
            else:
                y = r + (1 if dr > 0 else 0)
                e = [(c, y), (c + 1, y)]
            vs = [bm.verts.new(P(e[0][0], e[0][1], PIT_Z)), bm.verts.new(P(e[1][0], e[1][1], PIT_Z)),
                  bm.verts.new(P(e[1][0], e[1][1], FLOOR)), bm.verts.new(P(e[0][0], e[0][1], FLOOR))]
            f = mesh.face(vs, pit, False)
            if f:
                f.normal_update()
                want = Vector((-dc, dr, 0))      # towards the pit (r grows south = -Y)
                if f.normal.dot(want) < 0:
                    f.normal_flip()


def build_lip(mesh):
    """The coaming round the bay on the deck: a closed chamfered ring along the smooth outline; it
    hides the pixel stairs of the pit's edge."""
    lip = M(1, 0.55, 0.4)
    outer = BAY_S
    rings = [[(c, r, FLOOR - 0.1) for c, r in outer], [(c, r, FLOOR + 0.2) for c, r in outer],
             [(c, r, FLOOR + 0.42) for c, r in poly_offset(outer, 0.22)],
             [(c, r, FLOOR + 0.42) for c, r in poly_offset(outer, LIP)],
             [(c, r, FLOOR + 0.2) for c, r in poly_offset(outer, LIP + 0.15)],
             [(c, r, FLOOR - 0.1) for c, r in poly_offset(outer, LIP + 0.15)],
             [(c, r, FLOOR - 0.1) for c, r in outer]]
    mesh.loft(rings, lip, smooth=False, cap0=False, cap1=False)


HATCH = dict(c=22.7, r=44.8, rad=6.3)


def build_hatch_frame(mesh):
    """The hatch frame ring in the pit (shown on every frame set)."""
    h = HATCH
    ring = M(2, 0.6, 0.35)
    lathe(mesh, h["c"], h["r"], [(h["rad"] - 0.2, 0.05), (h["rad"] + 1.1, 0.05), (h["rad"] + 1.1, 0.4),
                                 (h["rad"] + 0.8, 0.8), (h["rad"] - 0.2, 0.8)], ring, n=40, smooth=False,
          cap0=False, cap1=False)


def build_hatch(mesh):
    """Closed hatch (frames 39-79): the sprite's small black ball with a white glint, a raised black
    glass dome in a ringed collar with two bolt lugs."""
    h = HATCH
    rad, zc = 4.5, 1.3
    ring, lug = M(2, 0.6, 0.35), M(18, 0.6, 0.35)
    # collar: a stepped ring round the dome foot
    lathe(mesh, h["c"], h["r"], [(h["rad"] - 0.3, 0.05), (h["rad"] - 0.3, 0.7), (h["rad"] - 0.9, 1.05),
                                 (rad + 0.9, 1.05), (rad + 0.5, 0.7), (rad + 0.5, 0.05)], ring, n=40,
          smooth=False, cap0=False, cap1=False)
    # the dome: a near-hemisphere from the collar
    prof = []
    for j in range(11):
        t = math.pi / 2 * j / 10
        prof.append((max(0.001, rad * math.cos(t)), zc + 3.9 * math.sin(t)))
    lathe(mesh, h["c"], h["r"], [(rad, 0.05)] + prof[:-1] + [(0.001, zc + 3.9)], M.glass(1), n=36)
    # glint: a small white sheen spot high on the upper left
    ang = math.radians(135)
    gc, gr = h["c"] + 2.0 * math.cos(ang), h["r"] - 2.0 * math.sin(ang)
    dz = zc + 3.9 * math.sqrt(max(0.0, 1 - (2.0 / rad) ** 2))
    lathe(mesh, gc, gr, [(0.001, dz - 0.02), (0.75, dz - 0.25), (0.8, dz - 0.5), (0.001, dz - 0.5)], M(14, 0.1, 0.2),
          n=10, smooth=True, cap0=False, cap1=False)
    # two bolt lugs on the collar, east and west
    for sgn in (-1, 1):
        cc = h["c"] + sgn * (h["rad"] - 1.6)
        cylinder(mesh, (cc, h["r"], 0.9), (cc, h["r"], 1.5), 0.5, lug, n=8, smooth=False)


def build_iris_open(mesh):
    """Open iris (frames 81-87): the petals retracted into a ring round the opening."""
    h = HATCH
    lathe(mesh, h["c"], h["r"], [(h["rad"] - 1.3, 0.05), (h["rad"], 0.05), (h["rad"], 0.55), (h["rad"] - 1.3, 0.3)],
          M(2, 0.6, 0.35), n=40, smooth=False)


BALLS = {"dim": dict(c=22.6, r=44.4, rad=7.0, zc=3.2, pal=69, frames={"newshs-77-f2": [81], "newshs-79-f2": [83]}),
         "bright": dict(c=22.9, r=45.3, rad=7.0, zc=7.4, pal=75, frames={"newshs-77-f2": [85], "newshs-79-f2": [87]})}


def build_ball(mesh, b):
    prof = []
    t0 = math.asin(max(-1.0, min(1.0, (0.1 - b["zc"]) / b["rad"])))   # cut flat at the pit floor
    for j in range(17):
        t = t0 + (math.pi / 2 - t0) * j / 16
        prof.append((max(0.001, b["rad"] * math.cos(t)), b["zc"] + b["rad"] * math.sin(t)))
    lathe(mesh, b["c"], b["r"], prof[:-1], M(b["pal"], 0.2, 0.4), n=36)
    # lift piston under it (in the pit)
    lathe(mesh, b["c"], b["r"], [(2.2, PIT_Z), (2.2, b["zc"] - 3.0)], M(18), n=16, smooth=True)


# --- the floor -----------------------------------------------------------------------------------------
def floor_tones():
    bins = ((1, 3), (4, 6), (7, 9), (10, 15))
    have = {int(k) for k in SPRITE["colors"]}
    slots = []
    for lo, hi in bins:
        idx = [i for i in range(lo, hi + 1) if i in have]
        slots.append(M.stone(min(idx, key=lambda i: abs(i - (lo + hi) / 2))) if idx else None)
    fb = slots[1]
    slots = [s if s is not None else fb for s in slots]

    def of(v):
        for (lo, hi), s in zip(bins, slots):
            if lo <= v <= hi:
                return s
        return fb
    return of


def build_floor(mesh, machine):
    """The stone plate: z 0..FLOOR, top painted per pixel (runs of one tone merged); no deck where
    the bay pit is."""
    tone = floor_tones()
    bm = mesh.bm
    for r in range(H):
        c = 0
        row = []
        for cc in range(W):
            x, y = cc + 0.5, r + 0.5
            if (cc, r) in REMOVED:
                row.append(None)
            else:
                v = G0[r][cc]
                row.append(tone(4 if machine[r][cc] else v))
        while c < W:
            if row[c] is None:
                c += 1
                continue
            e = c
            while e + 1 < W and row[e + 1] == row[c]:
                e += 1
            vs = [bm.verts.new(P(x, y, FLOOR)) for x, y in ((c, r + 1), (e + 1, r + 1), (e + 1, r), (c, r))]
            f = mesh.face(vs, row[c], False)
            c = e + 1
    # sides and bottom (closed plate)
    skirt = tone(4)
    z0 = 0.0
    corners = [(0, H), (W, H), (W, 0), (0, 0)]
    top = [bm.verts.new(P(x, y, FLOOR - 0.002)) for x, y in corners]
    bot = [bm.verts.new(P(x, y, z0)) for x, y in corners]
    for i in range(4):
        mesh.face([bot[i], bot[(i + 1) % 4], top[(i + 1) % 4], top[i]], skirt, False)
    mesh.face(bot[::-1], skirt, False)


# --- outline shells, cutting, export --------------------------------------------------------------------
def split_assembly_flatcap(obj, layout, collection=None):
    """common.split_assembly, but the cut caps are flat-shaded and their loop edges marked sharp, so
    the smooth surfaces either side of a cut keep their own normals (else the caps' normals bleed into
    the rim and the orb shows dark crack lines along the piece seams in the game). Candidate for a
    shared fix in common.split_assembly."""
    result = {}
    coll = collection or obj.users_collection[0]
    src = source_normals(obj)
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        cap = bm.faces.layers.int.new("cut_cap")
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
            edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge) and e.is_valid]
            for e in edges:
                e.smooth = False
            if edges:
                filled = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
                for f in filled["faces"]:
                    f.smooth = False
                    f[cap] = 1
                    for e in f.edges:
                        e.smooth = False
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for mat in obj.data.materials:
            mesh.materials.append(mat)
        transfer_normals(mesh, src, Vector((x0, y0, 0)))
        piece = bpy.data.objects.new(name, mesh)
        coll.objects.link(piece)
        result[name] = piece
    return result


def source_normals(obj):
    """BVH over the unsplit object's loop triangles (world space) with its corner normals."""
    from mathutils.bvhtree import BVHTree
    me = obj.data
    me.calc_loop_triangles()
    mw = obj.matrix_world
    vs = [mw @ v.co for v in me.vertices]
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    cn = [Vector(c.vector) for c in me.corner_normals]
    rot = mw.to_3x3()
    tri_n = [[(rot @ cn[li]).normalized() for li in t.loops] for t in me.loop_triangles]
    return BVHTree.FromPolygons(vs, tris), vs, tris, tri_n


def transfer_normals(mesh, src, offset):
    """Custom normals on a cut piece from the unsplit source (so the shading runs on across the cut
    exactly as on the whole); the cap faces keep flat normals. Each corner samples the source just
    inside its own face, so it never picks the face across a sharp edge."""
    from mathutils.geometry import barycentric_transform
    bvh, vs, tris, tri_n = src
    caps = mesh.attributes.get("cut_cap")
    capv = [d.value for d in caps.data] if caps else [0] * len(mesh.polygons)
    out = [None] * len(mesh.loops)
    for poly in mesh.polygons:
        fn = Vector(poly.normal)
        if capv[poly.index] or not poly.use_smooth:
            for li in poly.loop_indices:
                out[li] = fn
            continue
        ctr = Vector(poly.center)
        for li in poly.loop_indices:
            co = Vector(mesh.vertices[mesh.loops[li].vertex_index].co)
            q = co.lerp(ctr, 0.03) + offset
            loc, _n, ti, d = bvh.find_nearest(q)
            if ti is None or d > 0.02:
                out[li] = Vector(mesh.corner_normals[li].vector)
                continue
            a, b, c = (vs[i] for i in tris[ti])
            na, nb, nc = tri_n[ti]
            # barycentric weights of loc in (a, b, c) via transform onto a unit triangle
            w = barycentric_transform(loc, a, b, c, Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
            n = na * w.x + nb * w.y + nc * w.z
            out[li] = n.normalized() if n.length > 1e-6 else fn
    mesh.normals_split_custom_set([tuple(n) for n in out])
    if caps:
        mesh.attributes.remove(mesh.attributes["cut_cap"])


def split_open(obj, coll, layout):
    """Cut a shell into the pieces without filling the cut (it is drawn only as an outline)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx * PX, -cy * PX
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 12 * PX, 14 * PX
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        me.shade_smooth()
        o = bpy.data.objects.new(f"{name}_outline", me)
        o["tyrian_outline"] = True
        coll.objects.link(o)
        out[name] = o
    return out


def join_copy(objs, name, coll):
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in M.list:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


# --- renders ----------------------------------------------------------------------------------------------
def render_setup(px):
    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x = scene.render.resolution_y = px
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.30, 0.33, 0.42, 1)
    bg.inputs[1].default_value = 0.7
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    if "sun" not in bpy.data.objects:
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 4.0
        scene.collection.objects.link(sun)
        sun.rotation_euler = Vector((-6, -8.4, 20)).to_track_quat("Z", "Y").to_euler()
    if "cam" not in bpy.data.objects:
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        scene.collection.objects.link(cam)
    cam = bpy.data.objects["cam"]
    scene.camera = cam
    return scene, cam


def shot(out, name, direction, ortho=5.6, px=520):
    scene, cam = render_setup(px)
    d = Vector(direction).normalized()
    cam.location = d * 14.0
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    if d.z > 0.999:
        cam.rotation_euler = (0, 0, 0)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho
    cam.data.clip_end = 100
    scene.render.filepath = str(out / f"{name}.png")
    bpy.ops.render.render(write_still=True)


def top_flat(out, name, k=8, mask=False):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = W * k, H * k
    scene.render.film_transparent = True
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "SINGLE" if mask else "MATERIAL"
    sh.single_color = (1, 1, 1)
    sh.show_shadows = False
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = "Standard"
    if "topcam" not in bpy.data.objects:
        cam = bpy.data.objects.new("topcam", bpy.data.cameras.new("topcam"))
        scene.collection.objects.link(cam)
    cam = bpy.data.objects["topcam"]
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(W, H) * PX
    cam.location = (0, 0, 10)
    cam.rotation_euler = (0, 0, 0)
    scene.camera = cam
    scene.render.filepath = str(out / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    scene.render.film_transparent = False


def show_only(objs):
    keep = set(o.name for o in objs)
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in keep


# --- main --------------------------------------------------------------------------------------------------
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    rdir = Path(argv[argv.index("--render") + 1]) if "--render" in argv else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    bpy.context.view_layer.update()

    machine = [[ch == "1" for ch in row] for row in MACHINE]

    global REMOVED
    REMOVED = bay_removed()          # before the floor, so the deck leaves the pit open
    m_floor = Mesh("floor"); build_floor(m_floor, machine)
    m_pit = Mesh("pit"); build_pit(m_pit, REMOVED)
    m_lip = Mesh("lip"); build_lip(m_lip); build_hatch_frame(m_lip)
    m_base = Mesh("machine")
    build_orb(m_base); build_vent(m_base); build_cradle(m_base); build_lugs(m_base); build_legs(m_base); build_horns(m_base)
    build_yoke(m_base)
    m_hatch = Mesh("hatch"); build_hatch(m_hatch)
    m_iris = Mesh("iris"); build_iris_open(m_iris)
    balls = {}
    for k, b in BALLS.items():
        mb = Mesh(f"ball_{k}"); build_ball(mb, b); balls[k] = mb

    o_floor = m_floor.finish(coll, sharp=None, recalc=False)
    o_pit = m_pit.finish(coll, recalc=False)
    o_lip = m_lip.finish(coll)
    o_pit = join_copy([o_pit, o_lip], "bay", coll)
    o_base = m_base.finish(coll)
    o_hatch = m_hatch.finish(coll)
    o_iris = m_iris.finish(coll)
    o_balls = {k: mb.finish(coll) for k, mb in balls.items()}
    print("triangles: floor", tris(o_floor), "pit", tris(o_pit), "machine", tris(o_base), "hatch", tris(o_hatch),
          "iris", tris(o_iris), "balls", {k: tris(o) for k, o in o_balls.items()})

    if rdir:
        rdir.mkdir(parents=True, exist_ok=True)
        sets = {0: [o_floor, o_pit, o_base, o_hatch], 1: [o_floor, o_pit, o_base, o_iris, o_balls["dim"]],
                2: [o_floor, o_pit, o_base, o_iris, o_balls["bright"]]}
        for k, objs in sets.items():
            show_only(objs)
            top_flat(rdir, f"top_flat_{k}")
            show_only([o for o in objs if o is not o_floor])
            top_flat(rdir, f"top_mask_{k}", mask=True)
            top_flat(rdir, f"top_mflat_{k}")
        t = math.radians(30)
        show_only(sets[0])
        shot(rdir, "top", (0, -0.0001, 1), ortho=56 / 12 * 1.05)
        shot(rdir, "game", (0, -math.sin(t), math.cos(t)), ortho=5.0)
        shot(rdir, "front", (0, -1, 0.0001), ortho=4.6)
        shot(rdir, "rear", (0, 1, 0.0001), ortho=4.6)
        shot(rdir, "left", (-1, 0, 0.0001), ortho=4.6)
        shot(rdir, "right", (1, 0, 0.0001), ortho=4.6)
        shot(rdir, "q34_fl", (-0.7, -0.75, 0.62), ortho=4.8)
        shot(rdir, "q34_rr", (0.7, 0.75, 0.62), ortho=4.8)
        shot(rdir, "close", (-0.35, -0.9, 0.55), ortho=2.6)
        shot(rdir, "under", (0.2, -0.3, -1), ortho=5.2)
        show_only(sets[1])
        shot(rdir, "game_1", (0, -math.sin(t), math.cos(t)), ortho=5.0)
        shot(rdir, "q34_rr_1", (0.7, 0.75, 0.62), ortho=4.8)
        show_only(sets[2])
        shot(rdir, "game_2", (0, -math.sin(t), math.cos(t)), ortho=5.0)
        shot(rdir, "q34_fl_2", (-0.7, -0.75, 0.62), ortho=4.8)
        for o in bpy.data.objects:
            if o.type == "MESH":
                o.hide_render = False

    # outline shells (D51): the machine (one island: claws, yoke, lugs all reach the cradle) and each
    # ball; the pit and the hatch sit in the deck and take none (the sprite's bay has no ink ring)
    shell = common.outline_shell(o_base, coll, voxel=0.014, faces=4500, smooth=6, inside=0.01)
    ball_shells = {k: common.outline_shell(o, coll, voxel=0.014, faces=1200, smooth=6, inside=0.01)
                   for k, o in o_balls.items()}

    whole = join_copy([o_pit, o_base], "whole", coll)  # not the floor plate (D130)
    cut = split_assembly_flatcap(whole, LAYOUT, coll)
    hatch_cut = split_assembly_flatcap(o_hatch, LAYOUT, coll)
    iris_cut = split_assembly_flatcap(o_iris, LAYOUT, coll)
    ball_cut = {k: split_assembly_flatcap(o, LAYOUT, coll) for k, o in o_balls.items()}
    for d, lab in ((cut, "body"), (hatch_cut, "hatch"), (iris_cut, "iris"), *((ball_cut[k], k) for k in ball_cut)):
        for o in d.values():
            o.name = f"_cut_{o.name}_{lab}"
    shells = split_open(shell, coll, LAYOUT)
    bshells = {k: split_open(s, coll, LAYOUT) for k, s in ball_shells.items()}

    report = {}

    def sprites_of(name, frames=None):
        sp = common.load_sprite(WT, name)["sprites"]
        if frames is None:
            return sp
        out = []
        for s in sp:
            keep = [f for f in s["frames"] if f in frames]
            if keep:
                out.append({**s, "frames": keep})
        return out

    def export(model, objs, sprites):
        for o in objs:
            if o.type == "MESH" and not o.data.polygons:
                raise RuntimeError(f"{model}: empty part {o.name}")
        report[model] = [(o.name, tris(o)) for o in objs]
        common.export_sprite_model(WT, objs, f"enemies/{model}", sprites)

    def named(obj, model, label, frames=None):
        obj.name = f"{model}|{label}"
        if frames:
            common.frame_part(obj, frames)
        return obj

    def dup(o):
        d = o.copy()
        d.data = o.data.copy()
        coll.objects.link(d)
        return d

    for name, cx, cy in LAYOUT:
        if name in ("newshs-39", "newshs-41"):
            export(name, [named(cut[name], name, "body"), named(shells[name], name, "outline")],
                   sprites_of(name))
            continue
        frames = {"newshs-77": [77], "newshs-79": [79]}[name]
        export(name, [named(cut[name], name, "body"), named(shells[name], name, "outline"),
                      named(hatch_cut[name], name, "hatch")], sprites_of(name, frames))
        f2 = name + "-f2"
        objs = [named(dup(cut[name]), f2, "body"), named(dup(shells[name]), f2, "outline"),
                named(iris_cut[name], f2, "iris")]
        for k, bb in BALLS.items():
            fr = bb["frames"][f2]
            if ball_cut[k][name].data.polygons:
                objs.append(named(ball_cut[k][name], f2, f"ball_{k}", fr))
            bs = bshells[k][name]
            if bs.data.polygons:
                objs.append(named(bs, f2, f"ball_{k}_outline", fr))
        export(f2, objs, sprites_of(name, [f for bb in BALLS.values() for f in bb["frames"][f2]]))
    for name, items in report.items():
        print(name, items, "total", sum(t for lab, t in items if "outline" not in lab))
    if rdir:
        (rdir / "stats.json").write_text(json.dumps({"tris": report, "machine_tris": tris(o_base)}, indent=1))


if __name__ == "__main__":
    main()
