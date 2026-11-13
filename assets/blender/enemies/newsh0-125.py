"""Armoured hover pod (newsh0.shp frames 125, 127, 131), a hard-surface low-flying pod
that is its sprite in 3D.

What it is: a small air-type enemy of BOTANY A/B (2.10, 2.11) that patrols on its own legs (drift
of 1 px/tick or right-angle 2 px/tick swoops, often in rigid pairs at dx 24) and fires (tur 62).
So it is built as a flyer: it hovers, with a round closed belly, not a ground emplacement.

Read from the sprite (17 x 13 px, symmetric about column 12):
  - the armour shell (cols 8-16, rows 7-16): two blue-steel lobes either side of a groove at
    column 12, each in three plates split by dark seams at rows 11 and 14 (the "ribs");
  - a socket in the middle (cols 10-14, rows 10-15, dark 50/51) holding the red core (cols 11-13,
    rows 11-14). The frames only charge the core: dim (125), bright with an orange heart (127),
    wide open filling the socket with a yellow heart (131);
  - a ribbed hover nacelle down each side (cols 5-6, rows 9-16), bright collars at rows 10/11
    and 13, darker between;
  - the dark gap at column 7 between shell and nacelle with two struts (53) at rows 11 and 13;
  - two short stub guns (col 7 / 17, rows 16-18) poking out past the shell's lower edge: the pod's
    front is DOWN the screen, toward the player it shoots at.

Palette index per region (sprite median, darkest shading and brightest sheen ignored): measured by
--measure. Texture: AO/roughness bake only (no foil), outline shell from a sealed copy (D51/D90).

Run: blender --background --factory-startup --python enemies/newsh0-125.py -- [--no-bake] [--out X.glb]
                                                                         [--measure m.json] [--render DIR]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
from usp_talon import pchip  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "newsh0-125"
FRAMES = (125, 127, 131)
PX = 1 / 12
AXU = 12.5  # the sprite's axis of symmetry (column edge 12.5)

# Materials: (palette index, metallic, roughness, emission)
SHELL, SHELL_HI, POD, POD_RIB, CHASSIS, SOCKET, STRUT, GUN, MUZZLE = range(9)
CORE_A, HEART_A, CORE_B, HEART_B, HOT_B, CORE_C, MID_C, HEART_C, HOT_C = range(9, 18)
SHELL_LO = 18
MATS = {
    SHELL: (56, 0.3, 0.34, 0.0),      # middle plates (rows 11-13: trimmed median 55-57)
    SHELL_HI: (58, 0.3, 0.32, 0.0),   # top plates (rows 7-10: trimmed median 58)
    POD: (56, 0.3, 0.36, 0.0),        # nacelle body (trimmed median 55-56)
    POD_RIB: (59, 0.3, 0.3, 0.0),     # nacelle collars
    CHASSIS: (50, 0.45, 0.5, 0.0),    # dark keel / belly and the column-7 gap
    SOCKET: (51, 0.4, 0.5, 0.0),      # socket wall and floor (50/51)
    STRUT: (53, 0.5, 0.4, 0.0),       # struts at rows 11, 13
    GUN: (56, 0.3, 0.36, 0.0),       # stub guns (55/58)
    MUZZLE: (48, 0.4, 0.5, 0.0),      # gun bores
    # the core glows (D126: strength 1 = the palette colour unlit; D173: glow surfaces metallic 1, rough)
    CORE_A: (114, 1.0, 0.85, 1.0),    # frame 125: dim core (cols 11/13: 112-115)
    HEART_A: (117, 1.0, 0.85, 1.0),   # its centre column (114-117)
    CORE_B: (116, 1.0, 0.85, 1.0),    # frame 127: brighter (114-117)
    HEART_B: (119, 1.0, 0.85, 1.0),   # centre (116-122)
    HOT_B: (122, 1.0, 0.85, 1.0),     # the orange heart (row 13)
    CORE_C: (115, 1.0, 0.85, 1.0),    # frame 131: the core fills the socket (113-115 rim)
    MID_C: (118, 1.0, 0.85, 1.0),     # cols 11/13 (116-119)
    HEART_C: (122, 1.0, 0.85, 1.0),   # centre column (119-122)
    HOT_C: (124, 1.0, 0.85, 1.0),     # yellow heart (row 13)
    SHELL_LO: (55, 0.3, 0.36, 0.0),  # bottom plates (rows 14-16: trimmed median 54-55)
}
GLOW = tuple(range(9, 18))
# Light steel (fix round 1: at metallic 0.55 the reflections took the blue base colour and the pod
# read dark saturated blue in game). Metallic drops to 0.3 so the diffuse keeps the palette blue's
# value, and the steel parts get the F0 of IOR 2.0 through Specular IOR Level (D176: the exporter
# writes it as KHR_materials_specular), so the sun and environment panels sheen white on the crowns
# as the sprite's 60-62 highlights do.
STEEL = (SHELL, SHELL_HI, SHELL_LO, POD, POD_RIB, GUN)
STEEL_SPEC = 0.5 * ((1.0 / 3.0) ** 2 / 0.04)
TINT = (0.97, 0.985, 1.0)


# --- geometry helpers (sprite px: xr from the axis, y = sprite row edge, down the screen, z up) ----

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def face(self, vs, mat):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        return f


def ring(cx, y, hw, zb, zt, n=20, p=2.6, pb=None, hwb=None):
    """A superellipse section (x-z) at row y: half width hw (hwb at the bottom), from zb to zt."""
    pb = p if pb is None else pb
    hwb = hw if hwb is None else hwb
    zc, hh = (zb + zt) / 2, (zt - zb) / 2
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        e = p if s >= 0 else pb
        w = hw if s >= 0 else hwb
        x = cx + w * math.copysign(abs(c) ** (2 / e), c)
        z = zc + hh * math.copysign(abs(s) ** (2 / e), s)
        pts.append((x, y, z))
    return pts


def loft(m, rings, mat, mats=None):
    """Closed tube through rings (lists of xyz with the same count), capped both ends."""
    vr = [[m.bm.verts.new(p) for p in r] for r in rings]
    n = len(vr[0])
    for k, (a, b) in enumerate(zip(vr, vr[1:])):
        mk = mats[k] if mats else mat
        for i in range(n):
            j = (i + 1) % n
            m.face((a[i], a[j], b[j], b[i]), mk)
    m.face(vr[0], mats[0] if mats else mat)
    m.face(list(reversed(vr[-1])), mats[-1] if mats else mat)
    return vr


def hull(m, pts, mat):
    """Convex hull of points (chamfered blocks)."""
    bm = m.bm
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    live = [v for v in verts if v.is_valid]
    for f in {f for v in live for f in v.link_faces}:
        f.material_index = mat


def cbox(x0, x1, y0, y1, z0, z1, ch, z1b=None, chz=None):
    """Corner points of a chamfered box; the top may slope from z1 (y0 end) to z1b (y1 end)."""
    chz = ch if chz is None else chz
    z1b = z1 if z1b is None else z1b
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            for zz, sz in ((z0, 1), (None, -1)):
                if zz is None:
                    zz = z1 if y == y0 else z1b
                pts += [(x + sx * ch, y, zz + sz * chz), (x, y + sy * ch, zz + sz * chz), (x + sx * ch, y + sy * ch, zz)]
    return pts


def dome(m, cx, cy, rx, ry, z0, h, mat, n=16, k=5, p=2.2, base=0.0):
    """A closed dome: superellipse plan rx x ry at z0 (with a short vertical skirt `base`), rising h."""
    rings = []
    if base > 0:
        rings.append([(cx + x, cy + y, z0 - base) for x, y in _plan(rx, ry, n, p)])
    for i in range(k + 1):
        phi = (math.pi / 2) * i / (k + 1)
        s = math.cos(phi)
        rings.append([(cx + x * s, cy + y * s, z0 + h * math.sin(phi)) for x, y in _plan(rx, ry, n, p)])
    vr = [[m.bm.verts.new(q) for q in r] for r in rings]
    apex = m.bm.verts.new((cx, cy, z0 + h))
    for a, b in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            m.face((a[i], a[j], b[j], b[i]), mat)
    for i in range(n):
        j = (i + 1) % n
        m.face((vr[-1][i], vr[-1][j], apex), mat)
    m.face(list(reversed(vr[0])), mat)


def _plan(rx, ry, n, p):
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        out.append((rx * math.copysign(abs(c) ** (2 / p), c), ry * math.copysign(abs(s) ** (2 / p), s)))
    return out


def cyl(m, p0, p1, r, mat, n=8, r1=None):
    """A capped cylinder (or cone, r1) from p0 to p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    q = d.to_track_quat("Z", "Y")
    rot = q.to_matrix().to_4x4()
    mid = (p0 + p1) / 2
    res = bmesh.ops.create_cone(m.bm, cap_ends=True, cap_tris=False, segments=n, radius1=r,
                                radius2=r if r1 is None else r1, depth=d.length,
                                matrix=Matrix.Translation(mid) @ rot)
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat


def mirror(fn):
    for s in (-1, 1):
        fn(s)


# --- the pod ----------------------------------------------------------------------------------

def stations(a, b, step):
    n = max(2, int(round((b - a) / step)) + 1)
    return [a + (b - a) * i / (n - 1) for i in range(n)]


SOCK_Y, SOCK_RY, SOCK_RX = 13.0, 3.0, 2.5   # socket opening: cols 10-14, rows 10-15
LOBE_OUT = 4.5                                # lobes reach column edge 8 (x = -4.5)
LOBE_ZB = 1.4
CH = 0.3                                      # the armour's one chamfer (sprite px), every edge
SEAM = 0.13                                   # seam chamfer at the plate joints (rows 11, 14)
# crown height along the shell (row edge -> z)
CROWN_Y = [7.0, 9.0, 12.0, 15.0, 17.0]
CROWN_Z = [4.55, 4.9, 5.05, 4.85, 4.4]
crown = pchip(CROWN_Y, CROWN_Z)


def lobe_in(y):
    """Inner edge of the right lobe at row edge y: the groove (0.5) or the socket's rim."""
    d = (y - SOCK_Y) / SOCK_RY
    if abs(d) >= 1:
        return 0.5
    return max(0.5, SOCK_RX * math.sqrt(1 - d * d) + 0.15)


def lobe_section(y, inset=0.0, drop=0.0):
    """A right-lobe armour section at y (fix round 1: hard surface, not a pillow): vertical outer
    wall, one even 45-degree chamfer to a flat, slightly crowned top, an even chamfer into the
    groove or down into the socket, vertical inner wall. `inset`/`drop` pull the whole section in
    and down (the chamfered ends and the sloped glacis faces)."""
    sock = lobe_in(y) > 0.6
    xi, xo = lobe_in(y) + inset, LOBE_OUT - inset
    zt = crown(y) - drop
    zb = LOBE_ZB
    c = CH
    zs = zt - 0.22                                 # outer shoulder, just under the crown
    zi = zt - (0.5 if sock else 0.18)              # inner shoulder: lower at the socket rim
    w = xo - xi
    pts = [
        (xi + 0.15, zb), (xo - 0.3, zb), (xo, zb + 0.3),
        (xo, zs - c), (xo - c, zs),
        (xo - c - 0.3 * (w - 2 * c), zt - 0.04), (xo - c - 0.6 * (w - 2 * c), zt - 0.02),
        (xi + c, zi), (xi, zi - c), (xi, zb + 0.3),
    ]
    return [(x, y, z) for x, z in pts]


def build_plate(m, y0, y1, mat, ends):
    """One armour plate of the right lobe from row edge y0 to y1. Each end is ("seam",) - an even
    chamfer into the joint with the next plate - or ("glacis", run, fall): a flat sloped facet
    falling `fall` over `run` to a short chamfered end wall (the sprite's lit rows 7-8 / 15-16)."""
    def end(y, e, sign):
        if e[0] == "seam":
            return [lobe_section(y, SEAM, SEAM), lobe_section(y + sign * SEAM, 0.0, 0.0)]
        _, run, fall = e
        return [lobe_section(y, CH, fall + CH * 0.6),
                lobe_section(y + sign * CH, 0.0, fall),
                lobe_section(y + sign * (CH + run), 0.0, 0.0)]
    r0 = end(y0, ends[0], 1)
    r1 = list(reversed(end(y1, ends[1], -1)))
    ya, yb = r0[-1][0][1], r1[0][0][1]
    ys = stations(ya, yb, 0.5)[1:-1]
    loft(m, r0 + [lobe_section(y) for y in ys] + r1, mat)


SEAM_E = ("seam",)
PLATES = [(7.0, 11.0, SHELL_HI, (("glacis", 1.2, 1.0), SEAM_E)),
          (11.16, 14.0, SHELL, (SEAM_E, SEAM_E)),
          (14.16, 17.0, SHELL_LO, (SEAM_E, ("glacis", 1.0, 1.15)))]


def build_shell(m):
    for y0, y1, mat, ends in PLATES:
        build_plate(m, y0, y1, mat, ends)
    # machined detail: two hex bolts on each middle plate's outer shoulder, a recessed lifting slot
    # on the top plate
    for y in (11.85, 13.3):
        cyl(m, (3.7, y, crown(y) - 0.45), (3.7, y, crown(y) + 0.03), 0.2, STRUT, n=6)
    hull(m, cbox(2.55, 3.55, 8.9, 9.25, crown(9.1) - 0.3, crown(9.1) + 0.02, 0.06), SOCKET)


# belly: one closed rounded hull under everything (its top shows in the groove and the col-7 gap)
KEEL_Y = [7.9, 8.25, 9.2, 12.0, 15.6, 16.0, 16.3]
KEEL_HW = [4.6, 5.45, 5.5, 5.55, 5.5, 5.0, 3.8]
KEEL_ZT = [2.5, 2.7, 2.8, 2.8, 2.8, 2.7, 2.5]
KEEL_ZB = [2.0, 1.25, 0.55, 0.15, 0.55, 1.2, 1.9]


def build_keel(m):
    fh, ft, fb = pchip(KEEL_Y, KEEL_HW), pchip(KEEL_Y, KEEL_ZT), pchip(KEEL_Y, KEEL_ZB)
    ys = [7.9, 8.05] + stations(8.25, 16.05, 0.75) + [16.3]
    rings = [ring(0.0, y, fh(y), fb(y), ft(y), n=16, p=3.2, pb=2.0, hwb=fh(y) * 0.82) for y in ys]
    loft(m, rings, CHASSIS)


def build_socket(m):
    """The socket floor: a dark dished plate between the lobes (cols 10-14, rows 10-15)."""
    dome(m, 0.0, SOCK_Y, SOCK_RX + 0.2, SOCK_RY + 0.15, 2.55, 0.35, SOCKET, n=16, k=2, p=2.0, base=0.5)


# side rib stacks (cols 5-6, rows 9-16): curved armour ribs hugging the body. The centreline bows
# out mid-body and tucks in and down at both ends (row 9: one pixel at col 6; row 16: cols 6-7),
# so from the side they arc along the hull instead of standing off it as tubes.
RIBS = [(9.9, 10.75), (10.95, 11.8), (12.75, 13.7), (14.6, 15.3)]
# Both ends close with a flat chamfered cap (an armour band ends blunt), not a cone (fix round 1:
# the tapered tips read as rocket nozzles).
NAC_Y0, NAC_Y1 = 8.95, 16.62
nac_base = pchip([8.95, 9.12, 9.5, 10.0, 15.5, 16.0, 16.45, 16.62],
                 [0.36, 0.56, 0.74, 0.86, 0.86, 0.84, 0.8, 0.6])
nac_x = pchip([8.95, 9.5, 10.3, 14.8, 15.8, 16.62], [5.75, 6.05, 6.45, 6.45, 6.15, 5.6])
nac_z = pchip([8.95, 9.8, 11.0, 14.0, 15.6, 16.62], [2.15, 2.45, 2.65, 2.65, 2.5, 2.2])


def nac_r(y):
    base = nac_base(y)
    for a, b in RIBS:
        if a + 0.1 <= y <= b - 0.1:
            return max(base, 0.99 * min(1.0, base / 0.86 + 0.1))
    return base


def build_nacelle(m, s):
    ys = sorted(set([NAC_Y0, 9.12, 9.5, 16.0, 16.45, NAC_Y1]
                    + [v for a, b in RIBS for v in (a - 0.02, a + 0.1, b - 0.1, b + 0.02)]
                    + stations(10.0, 15.5, 1.8)))
    rings, mats = [], []
    for y in ys:
        r = nac_r(y)
        rings.append(ring(s * nac_x(y), y, r, nac_z(y) - r, nac_z(y) + r, n=10, p=2.0))
    for a, b in zip(ys, ys[1:]):
        mid = (a + b) / 2
        mats.append(POD_RIB if any(ra < mid < rb for ra, rb in RIBS) else POD)
    loft(m, rings, POD, mats=mats + [POD])


def build_struts(m, s):
    for y in (11.5, 13.5):
        cyl(m, (s * 4.0, y, 2.95), (s * 5.95, y, 2.75), 0.38, STRUT, n=6)
        cyl(m, (s * 5.3, y, 2.8), (s * 5.6, y, 2.8), 0.48, STRUT, n=6)   # collar where it meets the rib stack


def build_gun(m, s):
    """The tur-62 stub guns (col 7 / 17, rows 16-18): short, level along their length (D163)."""
    x = s * 5.0
    hull(m, cbox(x - 0.55, x + 0.55, 14.3, 16.3, 1.15, 2.75, 0.18), GUN)
    cyl(m, (x, 15.8, 1.95), (x, 17.45, 1.95), 0.4, GUN, n=8)
    cyl(m, (x, 17.3, 1.95), (x, 17.85, 1.95), 0.48, GUN, n=8)      # muzzle collar
    cyl(m, (x, 17.7, 1.95), (x, 17.88, 1.95), 0.26, MUZZLE, n=6)   # bore


def build_body():
    m = Mesh()
    build_keel(m)
    build_socket(m)
    # right half, mirrored for the left
    half = Mesh()
    build_shell(half)
    build_nacelle(half, 1)
    build_struts(half, 1)
    build_gun(half, 1)
    merge_mirrored(m, half)
    return m


def merge_mirrored(m, half):
    for s in (1, -1):
        bm2 = half.bm.copy()
        if s < 0:
            bmesh.ops.scale(bm2, vec=(-1, 1, 1), verts=bm2.verts)
            bmesh.ops.reverse_faces(bm2, faces=bm2.faces)
        tmp = bpy.data.meshes.new("tmp")
        bm2.to_mesh(tmp)
        bm2.free()
        m.bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)


def build_core(frame):
    m = Mesh()
    z0 = 2.75
    if frame == 131:
        dome(m, 0.0, SOCK_Y, 2.45, 2.95, z0, 1.35, CORE_C, n=20, k=4, p=2.1)
        dome(m, 0.0, SOCK_Y, 1.55, 2.1, z0, 1.55, MID_C, n=16, k=4, p=2.1)
        dome(m, 0.0, SOCK_Y - 0.1, 0.62, 1.55, z0, 1.72, HEART_C, n=12, k=4, p=2.1)
        dome(m, 0.0, SOCK_Y + 0.5, 0.5, 0.55, z0, 1.78, HOT_C, n=10, k=3, p=2.0)
    else:
        a, h, hot = (CORE_A, HEART_A, None) if frame == 125 else (CORE_B, HEART_B, HOT_B)
        dome(m, 0.0, SOCK_Y, 1.5, 2.0, z0, 1.2, a, n=16, k=4, p=2.1)
        dome(m, 0.0, SOCK_Y + 0.1, 0.6, 1.5, z0, 1.36, h, n=12, k=4, p=2.1)
        if hot is not None:
            dome(m, 0.0, SOCK_Y + 0.5, 0.48, 0.55, z0, 1.42, hot, n=10, k=3, p=2.0)
    return m


def to_object(m, name, mats, coll, sharp=32):
    bm = m.bm
    # sprite px -> Blender units: X = (x + 0.5) / 12, Y = (14 - y) / 12, Z = z / 12
    T = Matrix(((PX, 0, 0, (AXU - 12) * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=T, verts=bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY",
                          ngon_method="BEAUTY")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(sharp))
    return obj


def materials(sprite):
    out = []
    for i in range(len(MATS)):
        pal, met, rough, em = MATS[i]
        tag = f"{NAME}A_{i}"
        mt = common.palette_material(sprite, pal, tag, metallic=met, roughness=rough, emission_strength=em)
        if i in STEEL:
            bsdf = next(n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = STEEL_SPEC
        out.append(mt)
    return out

# --- bake (AO + edge lift, roughness/metal), after usp_talon.bake_maps / newshe-155 ----------------

def bake_maps(obj, out_dir, prefix, textured, size=512, samples=64):
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
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.02, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{prefix}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{prefix}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    b0 = next(n for n in me.materials[0].node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for img, c in ((col_img, (*TINT, 1.0)),
                   (rm_img, (1.0, b0.inputs["Roughness"].default_value, b0.inputs["Metallic"].default_value, 1.0))):
        img.pixels.foreach_set([v for _ in range(img.size[0] * img.size[1]) for v in c])
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
        ao_l.inputs["Distance"].default_value = 0.14
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
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.15)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(math_("MULTIPLY", v, TINT[k]), tint.inputs[k])
            nt.links.new(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.12)))
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
        bpy.ops.object.bake(type="EMIT", margin=16, margin_type="EXTEND", use_clear=False)
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
    # per-object copies of the materials, so each frame wires its own maps
    for i in textured:
        m = mats[i].copy()
        me.materials[i] = m
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


# --- measure -----------------------------------------------------------------------------------

def measure(frame_objs, sprite, sub=8):
    import sprite_mask as SM
    from mathutils.bvhtree import BVHTree
    res = {}
    W, H = 24, 28
    for frame, objs in frame_objs.items():
        fr = next(f for f in sprite["frames"] if f["index"] == frame)
        pix = fr["pixels"]
        bm = bmesh.new()
        offs = []
        for o in objs:
            tmp = bmesh.new()
            tmp.from_mesh(o.data)
            tmp.transform(o.matrix_world)
            me = bpy.data.meshes.new("m_tmp")
            tmp.to_mesh(me)
            tmp.free()
            offs.append((len(bm.faces), o))
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
        bm.faces.ensure_lookup_table()
        tree = BVHTree.FromBMesh(bm)
        fmat = [f.material_index for f in bm.faces]
        top = [[False] * (W * sub) for _ in range(H * sub)]
        regions = {}
        for r in range(H):
            for c in range(W):
                counts = {}
                for j in range(sub):
                    for i in range(sub):
                        u, v = c + (i + 0.5) / sub, r + (j + 0.5) / sub
                        hit = tree.ray_cast(Vector(((u - 12) * PX, (14 - v) * PX, 5.0)), Vector((0, 0, -1)), 20.0)
                        if hit[0] is not None:
                            top[r * sub + j][c * sub + i] = True
                            counts[fmat[hit[2]]] = counts.get(fmat[hit[2]], 0) + 1
                if sum(counts.values()) >= sub * sub / 2 and pix[r][c] >= 0:
                    mi = max(counts, key=counts.get)
                    regions.setdefault(mi, []).append(pix[r][c])
        bm.free()
        idx, colors = SM.load(NAME, frame)
        mk = SM.masks(idx, colors)
        meas = SM.measure(mk, top)
        reg = {}
        for mi, vals in regions.items():
            pal = MATS[mi][0]
            sv = sorted(vals)
            lo, hi = len(sv) // 6, len(sv) - len(sv) // 6
            trimmed = sv[lo:hi] or sv
            reg[f"{mi}:pal{pal}"] = {"n": len(vals), "median_trim": trimmed[len(trimmed) // 2], "pixels": sv}
        grid = ["".join("#" if sum(top[r * sub + j][c * sub + i] for j in range(sub) for i in range(sub)) >= sub * sub / 2
                        else "." for c in range(W)) for r in range(H)]
        res[frame] = {**meas, "regions": reg, "top": grid}
    return res


# --- renders ------------------------------------------------------------------------------------

def _camera(name, loc, look, ortho=None, lens=None, up_y=False):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens or 50
    cam = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = (0, 0, 0) if up_y else d.to_track_quat("-Z", "Y").to_euler()
    return cam


def _render(cam, path, w, h):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_all(frame_objs, all_objs, out):
    out.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError as err:
        sc.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "EEVEE" in e)
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.5, 0.52, 0.58, 1)
    bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    sc.collection.objects.link(sun)
    sun.rotation_euler = Vector((-0.35, 0.5, 1.0)).normalized().to_track_quat("Z", "Y").to_euler()
    gm = bpy.data.meshes.new("ground")
    gbm = bmesh.new()
    bmesh.ops.create_grid(gbm, x_segments=1, y_segments=1, size=3.0)
    bmesh.ops.translate(gbm, vec=(0, 0, -0.35), verts=gbm.verts)   # it hovers: ground well below
    gbm.to_mesh(gm)
    gbm.free()
    ground = bpy.data.objects.new("ground", gm)
    gm.materials.append(common.material("ground_mat", (0.13, 0.12, 0.1), roughness=0.9))
    sc.collection.objects.link(ground)
    C = Vector(((AXU - 12) * PX, 0.0, 0.25))
    views = {
        "top": ((C.x, 0, 10), (C.x, 0, 0), 2.0, None, True),
        "side": ((8, 0, C.z), (0, 0, C.z), 1.7, None, False),
        "front": ((C.x, -8, C.z), (C.x, 0, C.z), 1.7, None, False),
        "rear": ((C.x, 8, C.z), (C.x, 0, C.z), 1.7, None, False),
        "q_front": ((2.4, -2.9, 2.5), tuple(C), None, 60, False),
        "q_rear": ((-2.6, 2.6, 2.3), tuple(C), None, 60, False),
        "under": ((1.2, -1.8, -2.7), tuple(C), None, 55, False),
    }
    tilt = math.radians(32)
    dist = 9.0
    views["game"] = ((C.x, -dist * math.sin(tilt), dist * math.cos(tilt)), (C.x, 0, 0), None, 150, False)
    for frame, objs in frame_objs.items():
        for o in all_objs:
            o.hide_render = o not in objs
        for vn, (loc, look, ortho, lens, upy) in views.items():
            if frame != 125 and vn not in ("top", "game", "q_front"):
                continue
            ground.hide_render = vn != "game"
            cam = _camera(f"c_{vn}", loc, look, ortho=ortho, lens=lens, up_y=upy)
            _render(cam, out / f"{vn}-{frame}.png", 480, 480)
        ground.hide_render = False
        cam = _camera("c_small", views["game"][0], views["game"][1], lens=150)
        _render(cam, out / f"gamesmall-{frame}.png", 80, 80)
    print("rendered", out)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d  # noqa: E731
    sprite = common.load_sprite(WT, NAME)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    body = to_object(build_body(), NAME, mats, coll)
    cores = {f: to_object(build_core(f), f"{NAME}-core-{f}", mats, coll, sharp=80) for f in FRAMES}
    for o in [body, *cores.values()]:
        o.data.calc_loop_triangles()
        print(f"{o.name}: {len(o.data.loop_triangles)} triangles")
    # outline shell from the closed, unbaked body (D51, D90/D118: sealed before anything else)
    shell = common.outline_shell(body, coll, voxel=0.01, faces=900, smooth=6, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        bdir = Path(tempfile.mkdtemp(prefix="nsh125_bake_"))
        for o in coll.objects:
            o.hide_render = o is not body
        bake_maps(body, bdir, "pod125A_body", [i for i in MATS if i not in GLOW])
        for o in coll.objects:
            o.hide_render = False
        fmt = "WEBP"
    for f, o in cores.items():
        common.frame_part(o, [f])
    export = [body, shell, *cores.values()]
    if "--out" in argv:
        glb = Path(opt("--out"))
        common.export_glb(export, glb, image_format=fmt)
    else:
        common.export_sprite_model(WT, export, f"enemies/{NAME}", sprite["sprites"], image_format=fmt)
    frame_objs = {f: [body, cores[f]] for f in FRAMES}
    if "--measure" in argv:
        res = measure(frame_objs, sprite)
        Path(opt("--measure")).write_text(json.dumps(res, indent=1))
        for f, r in res.items():
            print("MEASURE", f, "iou_rule_grid", r["iou_rule_grid"], "iou_rule", r["iou_rule"],
                  {k: v["median_trim"] for k, v in r["regions"].items()})
    if "--render" in argv:
        render_all(frame_objs, [body, shell, *cores.values()], Path(opt("--render")))


if __name__ == "__main__":
    main()
