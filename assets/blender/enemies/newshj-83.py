"""newshj-83, the grey dome turret of the TORM / 2.x jungle (newshj.shp size 2, frames
83 / 121 / 85 / 123 / 87 / 125, 24 x 28 px), rebuilt as what it is (D65, D120, D122, D130).

WHAT IT IS: a steel dome emplacement on the ground layer. Frame 83 is the dome shut; on the
other five its iris opens and the core inside glows, cold tan (121) -> pink (85) -> red (123)
-> orange with a white heart (87) -> white-hot (125). Terrain-fixed, so it stands on the HD
ground at z 0: the sprite's green jungle round the dome is a pixel floor plate and is not built
(D130); the measured mask is the sprite without its greens (32-35, 192-199).

Reading the sprite (row/col = sprite pixel, edges in px):
- Dome, rows 4-18: a steel cap (palette 9, shading 7/8 and 4-6 is lighting; the 13-15 spot at
  row 8 col 7 is sheen, not a bump) on a short dark skirt (rows 17-18, 2-5).
- Plinth: an oval base that is flush with the dome on the north and stands out as a front apron
  to the south and east (rows 14-22): its dark trough round the dome's foot (rows 18-19, 1-3), the
  lit rim of its top edge (the 10-12 crescent from row 14 col 19 to row 20 col 14) and its front
  wall (rows 20-22, 4-8).
- Open frames: an iris opening rows 5-12, cols 7-14 (centre x 11, y 9) holding the core, a
  fireball: frame 87's white heart is ~8 px (rows 7-9, cols 9-11, NW of the iris centre) in a
  yellow 122-125 halo, then 117-121 orange, red 113-117 only at the rim; on 125 heart and halo
  are both white (~21 px), a dark socket gap (col 6 and col 15), the leaves'
  lit lips outside it (col 16 rows 7-12, cols 4-5 rows 10-11), and the leaves' parting slit down
  the front (dark col 10, lit edge col 11, rows 13-21).

Build: the plinth's footprint is a smooth curve fitted to the sprite's mask (a 6-harmonic polar
radius about (11.3, 13.0)) with a battered front wall; the dome is a clean ellipse inside it, peak
at (11.1, 10.0). The open model's iris is a boolean cut ringed by a short barbette (raised on the
north, following the dome's fall, so the opening never notches the dome's back) under the
leaves' lip. Two
models, as the game contract has them: newshj-83 (frame 83, shut) and newshj-83-f2 (85, 87, 121,
123, 125, open; heart, halo, bowl and rim colours animated per frame, D17). Outline shell from a sealed
pre-cull copy (D51/D90/D118); hidden faces culled. No textures/newshj-83 folder exists, so no maps.

    blender --background --factory-startup --python assets/blender/enemies/newshj-83.py
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "newshj-83"
PX = 1 / 12


def bl(x, y, z):
    """Sprite px (column edge, row edge, height) to Blender units (24 x 28 block, centred)."""
    return Vector(((x - 12) * PX, (14 - y) * PX, z * PX))


# --- footprint ---------------------------------------------------------------------------------

C = (11.3, 13.0)  # polar centre of the footprint fit (image coords, y down)
COEF = [(9.4516, 0.0), (0.2136, 0.2081), (0.1977, 0.3951), (-0.2635, 0.0428), (0.1593, 0.1403),
        (-0.0806, -0.0049), (0.1753, 0.0788)]
OUT = 0.0  # outward grow of the fitted curve (px)


def R_out(t):
    """Distance from C to the sprite outline at image angle t (0 east, pi/2 south)."""
    return OUT + COEF[0][0] + sum(a * math.cos(k * t) + b * math.sin(k * t) for k, (a, b) in enumerate(COEF) if k)


# The dome's own outline: a clean ellipse inside the outline (inset ~1 px north and on the sides,
# where the plinth's battered wall shows as a thin band; 3-4 px to the south, the apron).
DOME_SE = (11.2, 11.7, 9.0, 9.0, 7.0, 6.5, 2.0)  # cx, cy, rx west, rx east, ry north, ry south, n


def in_dome(x, y):
    cx, cy, rxw, rxe, ryn, rys, n = DOME_SE
    rx = rxw if x < cx else rxe
    ry = ryn if y < cy else rys
    if abs((x - cx) / rx) ** n + abs((y - cy) / ry) ** n > 1:
        return False
    return math.hypot(x - C[0], y - C[1]) < R_out(math.atan2(y - C[1], x - C[0]))


def ray_len(inside, src, ang, hi=20.0):
    dx, dy = math.cos(ang), math.sin(ang)
    lo = 0.0
    for _ in range(40):
        m = (lo + hi) / 2
        if inside(src[0] + dx * m, src[1] + dy * m):
            lo = m
        else:
            hi = m
    return lo


def apron(t):
    """How far the plinth stands out past the dome at angle t about C."""
    return max(0.0, R_out(t) - ray_len(in_dome, C, t))


def R_plinth(t):
    """The plinth's edge: the sprite's outline all round (a thin battered band on the north and
    sides, the apron to the south and east)."""
    return R_out(t)


def outline_pt(Rf, t, k=0.0):
    r = Rf(t) - k
    return C[0] + r * math.cos(t), C[1] + r * math.sin(t)


# --- dome --------------------------------------------------------------------------------------

PEAK = (11.1, 10.0)  # top of the dome (px)
ZB = 2.6             # skirt height: the cap starts here
HCAP = 7.0           # cap height above the skirt
NT = 96              # samples round
NR = 16              # rings from the peak to the skirt


_BD = {}


def dome_edge(ang):
    k = round(ang, 6)
    if k not in _BD:
        _BD[k] = ray_len(in_dome, PEAK, ang)
    return _BD[k]


def dome_z(x, y):
    """Height of the dome's cap over (x, y) px; ZB at the edge, None outside."""
    ang = math.atan2(y - PEAK[1], x - PEAK[0])
    d = math.hypot(x - PEAK[0], y - PEAK[1]) / dome_edge(ang)
    if d >= 1:
        return None
    return ZB + HCAP * math.sqrt(1 - d * d)


def build_dome(bm, mat_cap, mat_skirt, mat_bead):
    """A closed solid: cap rings from the peak, the skirt down to z 0 with a bead at its top, a
    flat bottom."""
    angs = [2 * math.pi * k / NT for k in range(NT)]
    rings = []
    for j in range(1, NR + 1):
        ph = (math.pi / 2) * j / NR
        s, z = math.sin(ph), ZB + HCAP * math.cos(ph)
        rings.append([(PEAK[0] + s * dome_edge(a) * math.cos(a), PEAK[1] + s * dome_edge(a) * math.sin(a), z, mat_cap)
                      for a in angs])
    # skirt: bead out 0.18 px at ZB-0.15 .. ZB-0.55, then the band in 0.1 px down to the ground
    def ring_at(k_in, z, mat):
        out = []
        for a in angs:
            r = dome_edge(a) - k_in
            out.append((PEAK[0] + r * math.cos(a), PEAK[1] + r * math.sin(a), z, mat))
        return out
    rings.append(ring_at(-0.18, ZB - 0.12, mat_bead))
    rings.append(ring_at(-0.18, ZB - 0.55, mat_bead))
    rings.append(ring_at(0.1, ZB - 0.7, mat_skirt))
    rings.append(ring_at(0.1, 0.0, mat_skirt))
    vr = [[bm.verts.new(bl(x, y, z)) for x, y, z, _ in r] for r in rings]
    pole = bm.verts.new(bl(PEAK[0], PEAK[1], ZB + HCAP))
    faces = []
    for k in range(NT):
        m = (k + 1) % NT
        f = bm.faces.new((pole, vr[0][m], vr[0][k]))
        f.material_index = mat_cap
        faces.append(f)
    for i in range(len(vr) - 1):
        for k in range(NT):
            m = (k + 1) % NT
            f = bm.faces.new((vr[i][k], vr[i][m], vr[i + 1][m], vr[i + 1][k]))
            f.material_index = rings[i + 1][k][3] if i + 1 >= NR else mat_cap
            faces.append(f)
    bot = bm.verts.new(bl(PEAK[0], PEAK[1], 0.0))
    for k in range(NT):
        m = (k + 1) % NT
        f = bm.faces.new((vr[-1][k], vr[-1][m], bot))
        f.material_index = mat_skirt
        faces.append(f)
    return faces


# --- plinth ------------------------------------------------------------------------------------

Z_WALL, Z_RIM, Z_TROUGH = 1.9, 2.4, 1.25
# (inset px, z): foot, battered front wall (the sprite's front face, seen from above too), chamfer,
# rim top (the lit crescent), inner slope, trough round the dome's foot
PROF = [(0.0, 0.0), (0.0, 0.3), (1.3, Z_WALL), (1.55, Z_RIM), (2.2, Z_RIM), (2.7, Z_TROUGH)]


def plinth_z(x, y):
    """Top surface height of the plinth over (x, y), None outside (approximate, for paths)."""
    t = math.atan2(y - C[1], x - C[0])
    d = R_plinth(t) - math.hypot(x - C[0], y - C[1])
    if d < 0:
        return None
    for (d0, z0), (d1, z1) in zip(PROF, PROF[1:]):
        if d < d1:
            return z0 + (z1 - z0) * (d - d0) / max(1e-6, d1 - d0)
    return Z_TROUGH


def build_plinth(bm, mat_wall, mat_rim, mat_trough, mat_line):
    """Rings inward from the outer wall: wall (with a panel line), chamfer and rim top (the lit
    rim), the inner slope and the trough round the dome's foot, closed under the dome."""
    angs = [2 * math.pi * k / NT for k in range(NT)]
    k = 1.3 / (Z_WALL - 0.3)  # batter: inset per px of height
    def wall(z):
        return k * (z - 0.3)
    prof = [  # (inset px, z, material of the band above this ring); a panel line across the wall
        (0.0, 0.0, None), (0.0, 0.3, mat_wall), (wall(0.95), 0.95, mat_wall), (wall(0.95) + 0.12, 0.98, mat_line),
        (wall(1.15) + 0.12, 1.15, mat_line), (wall(1.18), 1.18, mat_line), (1.3, Z_WALL, mat_wall),
        (1.55, Z_RIM, mat_rim), (2.2, Z_RIM, mat_rim), (2.7, Z_TROUGH, mat_trough), (4.2, Z_TROUGH, mat_trough)]
    vr = []
    for inset, z, _ in prof:
        vr.append([bm.verts.new(bl(*outline_pt(R_plinth, a, inset), z)) for a in angs])
    for i in range(len(vr) - 1):
        for k in range(NT):
            m = (k + 1) % NT
            f = bm.faces.new((vr[i][k], vr[i][m], vr[i + 1][m], vr[i + 1][k]))
            f.material_index = prof[i + 1][2]
    top = bm.verts.new(bl(C[0], C[1], Z_TROUGH))
    bot = bm.verts.new(bl(C[0], C[1], 0.0))
    for k in range(NT):
        m = (k + 1) % NT
        bm.faces.new((vr[-1][k], vr[-1][m], top)).material_index = mat_trough
        bm.faces.new((vr[0][m], vr[0][k], bot)).material_index = mat_wall


# --- small parts -------------------------------------------------------------------------------

def spow(v, e):
    return math.copysign(abs(v) ** e, v)


def loft(bm, rings, mat, cap=True):
    vr = [[bm.verts.new(bl(*p)) for p in r] for r in rings]
    faces = []
    for r0, r1 in zip(vr, vr[1:]):
        n = len(r0)
        for i in range(n):
            j = (i + 1) % n
            faces.append(bm.faces.new((r0[i], r0[j], r1[j], r1[i])))
    if cap:
        for r, flip in ((vr[0], True), (vr[-1], False)):
            c = bm.verts.new(sum((v.co for v in r), Vector()) / len(r))
            n = len(r)
            for i in range(n):
                j = (i + 1) % n
                faces.append(bm.faces.new((r[j], r[i], c) if flip else (r[i], r[j], c)))
    for f in faces:
        f.material_index = mat
    return faces


def sweep(bm, mat, path, sides=8, n=3.0, closed=False):
    """A tube through path [(x, y, z, half_w, half_h)] px, sections upright (horizontal side
    vector), squarish (superellipse n)."""
    pts = [Vector(p[:3]) for p in path]
    N = len(path)
    rings = []
    for i, (x, y, z, w, h) in enumerate(path):
        if closed:
            t = pts[(i + 1) % N] - pts[(i - 1) % N]
        else:
            t = pts[min(i + 1, N - 1)] - pts[max(i - 1, 0)]
        t.z = 0
        if t.length < 1e-6:
            t = Vector((0, 1, 0))
        t.normalize()
        side = Vector((-t.y, t.x, 0))
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5) / sides
            q = Vector((x, y, z)) + side * (w * spow(math.cos(a), 2 / n)) + Vector((0, 0, h * spow(math.sin(a), 2 / n)))
            ring.append(tuple(q))
        rings.append(ring)
    if closed:
        rings.append(rings[0])
        return loft(bm, rings, mat, cap=False)
    return loft(bm, rings, mat)


def stud(bm, mat, cx, cy, z0, r, h, seg=10, rings=3):
    """A round-headed bolt: a short shank from z0 - 0.3 and a dome head."""
    rs = [[(cx + r * math.cos(2 * math.pi * k / seg), cy + r * math.sin(2 * math.pi * k / seg), z0 - 0.3) for k in range(seg)]]
    for i in range(rings):
        th = (math.pi / 2) * i / rings
        rs.append([(cx + r * math.cos(th) * math.cos(2 * math.pi * k / seg), cy + r * math.cos(th) * math.sin(2 * math.pi * k / seg),
                    z0 + h * math.sin(th)) for k in range(seg)])
    rs.append([(cx + 0.02 * math.cos(2 * math.pi * k / seg), cy + 0.02 * math.sin(2 * math.pi * k / seg), z0 + h) for k in range(seg)])
    return loft(bm, rs, mat)


def surf_z(x, y):
    zs = [z for z in (dome_z(x, y), plinth_z(x, y)) if z is not None]
    return max(zs) if zs else 0.0


# --- the aperture (open model) -----------------------------------------------------------------

AP = (11.0, 9.2)        # iris centre (px)
AP_R = (4.9, 4.1)       # socket cut radii
LIP_R = (5.45, 4.5)      # leaf lip ring radii
Z_FLOOR = 3.2


def cutter(coll, mat):
    """Elliptic cylinder from the socket floor up through the cap."""
    bm = bmesh.new()
    seg = 48
    rings = [[(AP[0] + AP_R[0] * math.cos(2 * math.pi * k / seg), AP[1] + AP_R[1] * math.sin(2 * math.pi * k / seg), z)
              for k in range(seg)] for z in (Z_FLOOR, 20.0)]
    loft(bm, rings, 0)
    return common.mesh_object(f"{NAME}_cut", bm, [mat], coll)


HEART = (10.5, 8.5)  # the core's hot centre (px): the sprite's white heart, NW of the iris centre
CORE_R = 2.5          # core sphere radius (px)
HEART_R = 1.6         # white heart (top cap) radius seen from above: ~8 px, as frame 87's
HALO_R = 2.45         # yellow halo ring out to here; the sphere's flanks below it are the bowl's orange


def build_core(bm, mat_heart, mat_halo, mat_bowl, mat_rim, mat_sock):
    """The emitter bowl (a ribbed cup, its rim the cooler red) and the fireball core in it: a
    sphere whose top cap is the white heart, ringed by the yellow halo, its flanks orange."""
    seg = 40
    def ell(rx, ry, z, cx=AP[0], cy=AP[1]):
        return [(cx + rx * math.cos(2 * math.pi * k / seg), cy + ry * math.sin(2 * math.pi * k / seg), z) for k in range(seg)]
    # bowl: outer wall up from the floor (orange), its lip (red), inner face down to the core (orange)
    rings = [ell(2.6, 2.4, Z_FLOOR - 0.2), ell(3.6, 3.3, Z_FLOOR + 1.3), ell(4.1, 3.75, 5.45), ell(3.9, 3.55, 5.65),
             ell(3.2, 2.95, 5.25), ell(2.2, 2.0, 4.7)]
    band = [mat_bowl, mat_rim, mat_rim, mat_bowl, mat_bowl]  # material of the band above ring i
    vr = [[bm.verts.new(bl(*p)) for p in r] for r in rings]
    for i in range(len(vr) - 1):
        for k in range(seg):
            m = (k + 1) % seg
            bm.faces.new((vr[i][k], vr[i][m], vr[i + 1][m], vr[i + 1][k])).material_index = band[i]
    for r, flip, mat in ((vr[0], True, mat_bowl), (vr[-1], False, mat_bowl)):
        c = bm.verts.new(sum((v.co for v in r), Vector()) / len(r))
        for k in range(seg):
            m = (k + 1) % seg
            bm.faces.new((r[m], r[k], c) if flip else (r[k], r[m], c)).material_index = mat
    # cooling ribs on the bowl's inner face (radial), the bowl's orange
    for k in range(10):
        a = 2 * math.pi * (k + 0.5) / 10
        ca, sa = math.cos(a), math.sin(a)
        path = []
        for u in (0.0, 0.5, 1.0):
            r = 2.3 + 1.5 * u
            path.append((AP[0] + r * 1.0 * ca, AP[1] + r * 0.92 * sa, 4.8 + 0.8 * u + 0.12, 0.16, 0.12))
        sweep(bm, mat_bowl, path, sides=6, n=2.5)
    # the core: a sphere, banded by how far each face sits from the heart seen from above
    segc, cz, rr = 32, 6.2, CORE_R
    th_heart = math.acos(HEART_R / rr)
    th_halo = math.acos(HALO_R / rr)
    ths = sorted({*(-math.pi / 2 + math.pi * i / 12 for i in range(1, 12)), th_heart, th_halo,
                  (th_heart + math.pi / 2) / 2, (th_halo + th_heart) / 2})
    ths = [t for t in ths if t < math.pi / 2 - 1e-3]
    vr = [[bm.verts.new(bl(HEART[0] + rr * math.cos(t) * math.cos(2 * math.pi * k / segc),
                           HEART[1] + rr * 0.95 * math.cos(t) * math.sin(2 * math.pi * k / segc), cz + rr * math.sin(t)))
           for k in range(segc)] for t in ths]
    def mat_of(t):
        return mat_heart if t >= th_heart - 1e-6 else (mat_halo if t >= th_halo - 1e-6 else mat_bowl)
    for i in range(len(vr) - 1):
        mi = mat_of(ths[i])
        for k in range(segc):
            m = (k + 1) % segc
            bm.faces.new((vr[i][k], vr[i][m], vr[i + 1][m], vr[i + 1][k])).material_index = mi
    top = bm.verts.new(bl(HEART[0], HEART[1], cz + rr))
    bot = bm.verts.new(bl(HEART[0], HEART[1], cz - rr))
    for k in range(segc):
        m = (k + 1) % segc
        bm.faces.new((vr[-1][k], vr[-1][m], top)).material_index = mat_heart
        bm.faces.new((vr[0][m], vr[0][k], bot)).material_index = mat_bowl
    # a stem under it into the floor (dark)
    loft(bm, [ell(1.0, 1.0, Z_FLOOR - 0.2, *HEART), ell(1.0, 1.0, cz - 1.6, *HEART)], mat_sock)


def lip_z(x, y):
    """Top of the iris ring: on the cap where the cap is high, raised on a plane toward the north
    so the ring stands up as a short barbette there instead of notching the dome's back."""
    return max((dome_z(x, y) or ZB) + 0.05, 7.9 - 0.42 * (AP[1] - y))


def build_lips(bm, mat_lip, mat_cap, mat_sock):
    """The iris ring: a short barbette (outer wall in the cap's steel, inner wall dark) under the
    leaves' rounded lip."""
    seg = 64
    path, rin_b, rin_t, rout_t, rout_b = [], [], [], [], []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        ca, sa = math.cos(a), math.sin(a)
        x, y = AP[0] + LIP_R[0] * ca, AP[1] + LIP_R[1] * sa
        z = lip_z(x, y)
        path.append((x, y, z + 0.08, 0.55, 0.34))
        xi, yi = AP[0] + (AP_R[0] - 0.08) * ca, AP[1] + (AP_R[1] - 0.08) * sa
        xo, yo = AP[0] + (LIP_R[0] + 0.3) * ca, AP[1] + (LIP_R[1] + 0.3) * sa
        rin_b.append((xi, yi, Z_FLOOR + 0.05))
        rin_t.append((xi, yi, lip_z(xi, yi)))
        rout_t.append((xo, yo, lip_z(xo, yo) - 0.1))
        rout_b.append((xo, yo, (dome_z(xo, yo) or ZB) - 0.5))
    sweep(bm, mat_lip, path, sides=8, n=2.4, closed=True)
    vr = [[bm.verts.new(bl(*p)) for p in r] for r in (rin_b, rin_t, rout_t, rout_b)]
    mats = (mat_sock, mat_lip, mat_cap, mat_cap)
    for i in range(4):
        r0, r1 = vr[i], vr[(i + 1) % 4]
        for k in range(seg):
            m = (k + 1) % seg
            bm.faces.new((r0[k], r0[m], r1[m], r1[k])).material_index = mats[i]


def build_slit(bm, mat_dark, mat_lip):
    """The leaves' parting line down the front: a dark slit (col 10) with a lit edge (col 11),
    from the lip over the cap, the skirt and the plinth to the ground."""
    y0 = AP[1] + LIP_R[1] + 0.25
    for x, w, h, mat, dz in ((10.55, 0.36, 0.07, mat_dark, 0.0), (11.45, 0.34, 0.22, mat_lip, 0.04)):
        path = []
        y = y0
        while True:
            z = surf_z(x, y)
            if z <= 0.01:
                break
            path.append((x, y, z + dz, w, h))
            y += 0.12
        # down the plinth's front wall
        path.append((x, y - 0.06, 0.4, w, h))
        sweep(bm, mat, path, sides=6, n=2.5)


def build_bolts(bm, mat):
    """Bolts along the rim top, where the apron shows (south-east to south-west)."""
    for deg in range(10, 171, 16):
        t = math.radians(deg)
        if apron(t) < 2.6:
            continue
        x, y = outline_pt(R_plinth, t, 1.88)
        stud(bm, mat, x, y, Z_RIM, 0.24, 0.16)


def build_vents(bm, mat):
    """A louvre on the dome's back skirt (rear detail): four slats."""
    for k in range(4):
        a = math.radians(-90 - 18 + 12 * k)
        r = dome_edge(a) + 0.1
        x, y = PEAK[0] + r * math.cos(a), PEAK[1] + r * math.sin(a)
        loft(bm, [[(x + dx, y + dy, z) for dx, dy in ((-0.25, -0.12), (0.25, -0.12), (0.25, 0.12), (-0.25, 0.12))]
                  for z in (0.45, 1.65)], mat)


# --- assemble ----------------------------------------------------------------------------------

MATS = {  # name: (palette index, kwargs)
    "cap": (9, dict(metallic=0.6, roughness=0.34)),
    "skirt": (5, dict(metallic=0.5, roughness=0.5)),
    "bead": (8, dict(metallic=0.6, roughness=0.36)),
    "sock": (3, dict(metallic=0.4, roughness=0.65)),
    "lip": (10, dict(metallic=0.65, roughness=0.3)),
    "wall": (6, dict(metallic=0.5, roughness=0.45)),
    "line": (4, dict(metallic=0.5, roughness=0.55)),
    "bolt": (7, dict(metallic=0.6, roughness=0.4)),
    "dark": (2, dict(metallic=0.3, roughness=0.7)),
}
# The glow, base colours from frame 87 (white heart -> yellow halo -> orange bowl -> red rim), with
# each frame's own ramp (D17): 121 cold tan, 85 pink, 123 red, 125 white-hot (its heart and halo
# both white, the ~21 px white disc of that frame).
GLOW = {  # name: (palette index, {frame: index}, emission strength)
    "heart": (127, {85: 75, 121: 27, 123: 125}, 1.0),
    "halo": (124, {85: 73, 121: 26, 123: 121, 125: 127}, 1.0),
    "bowl": (120, {85: 72, 121: 167, 123: 116, 125: 124}, 0.8),
    "rim": (118, {85: 70, 121: 166, 123: 113, 125: 122}, 0.6),
}


def make_mats(sprite, model, open_):
    names = list(MATS)
    mats = [common.palette_material(sprite, MATS[n][0], model, **MATS[n][1]) for n in names]
    if open_:
        for n, (idx, fr, em) in GLOW.items():
            mats.append(common.palette_material(sprite, idx, f"{model}-{n}", metallic=1.0, roughness=0.9,
                                                emission_strength=em, frames=fr))
            names.append(n)
    return mats, {n: i for i, n in enumerate(names)}


def apply_mod(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(o == obj)
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def build(model, sprite, coll, open_):
    mats, I = make_mats(sprite, model, open_)
    # dome solid (cut for the iris on the open model)
    bm = bmesh.new()
    build_dome(bm, I["cap"], I["skirt"], I["bead"])
    dome = common.mesh_object(f"{model}_dome", bm, mats, coll, smooth=True)
    parts = [dome]
    if open_:
        cut = cutter(coll, mats[I["sock"]])
        mod = dome.modifiers.new("iris", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = cut
        try:
            mod.material_mode = "TRANSFER"
        except (AttributeError, TypeError):
            pass
        apply_mod(dome)
        bpy.data.objects.remove(cut, do_unlink=True)
    bm = bmesh.new()
    build_plinth(bm, I["wall"], I["lip"], I["sock"], I["line"])
    build_bolts(bm, I["lip"])
    build_vents(bm, I["skirt"])
    if open_:
        build_core(bm, I["heart"], I["halo"], I["bowl"], I["rim"], I["sock"])
        build_lips(bm, I["lip"], I["cap"], I["sock"])
        build_slit(bm, I["dark"], I["lip"])
    rest = common.mesh_object(f"{model}_rest", bm, mats, coll, smooth=True)
    parts.append(rest)
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(o in parts)
    bpy.context.view_layer.objects.active = dome
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = obj.data.name = model
    obj.data.set_sharp_from_angle(angle=math.radians(40))
    return obj


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(WT, NAME)
    frames = sprite["sprites"][0]["frames"]
    for model, open_, keep in ((NAME, False, frames[:1]), (f"{NAME}-f2", True, frames[1:])):
        coll = common.reset_collection(model)
        obj = build(model, sprite, coll, open_)
        seal = bpy.data.objects.new(f"{model}_seal", obj.data.copy())
        coll.objects.link(seal)
        bpy.context.view_layer.update()
        shell = common.outline_shell(seal, coll, voxel=0.01, faces=1500, smooth=5, inside=0.003)
        shell.name = shell.data.name = f"{model}_outline"
        bpy.data.objects.remove(seal, do_unlink=True)
        T.cull_hidden(obj)
        print("built", model, "triangles", sum(len(p.vertices) - 2 for p in obj.data.polygons), "shell faces", len(shell.data.polygons))
        common.export_sprite_model(WT, [obj, shell], f"enemies/{model}", [{**sprite["sprites"][0], "frames": keep}])


if __name__ == "__main__":
    main()
