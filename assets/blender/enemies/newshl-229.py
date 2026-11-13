"""SQUADRON leader (newshl.shp 229): a 3D version of its sprite.

What it is (4.18 SQUADRON, section 45): the airborne leader of the SQUADRON formation, one spawn
weaving down the screen (ev19/20/27, x -7..+7, y +1 px/tick) with the newshl-115/-116 craft formed
up below it, armour 40, a turret. So a flying gunship, not a ground walker:

- a squat armoured hood (rows 4-16): a broad faired dome, flat-sided, its back chamfered at 45 deg
  (the sprite's staircase rows 4-9), four lengthwise panel seams (columns 6, 9, 15, 18) and a
  slatted intake grille on its centre panel (rows 8-12: slats on columns 10/12/14);
- a dorsal housing on its back (rows 2-4), the dark crease in front of it a real step;
- under the hood's front edge a glowing reactor vent (rows 13-15), a recess cut into the sloped
  front face, red-hot inside and hottest at its lower lip (119), with a bumper bar under it (row 16);
- a low belly deck behind (rows 17-22) carrying the turret's plasma chute: two ribbed rails with
  clamps (rows 18 and 20) either side of a glowing core rod that heats from 114 to 121 down its
  length into the muzzle cowl (rows 22-24), whose open throat glows yellow (124) and whose front face
  carries the muzzle;
- two forked landing prongs (columns 1-4, 20-23) hinged under the hood's flanks, each an outer limb
  to the bottom of the block and an inner limb that joins it at row 24, braced to the chute by a
  strut at rows 19-20.

The sprite's whites (13-15) are sheen and its dark right half lighting (rubric): one hood colour
(pal_10, the hood's median), the seams pal_4. Glow parts metallic 1 / rough (D126, D173). Hard
surface (D50-D53, D65): lofts with pchip stations, modelled seams and grille, chamfered blocks;
outline shell from a sealed copy, every outer island (D189). Underside: a closed belly, no detail.

Units: X = (u - 12) / 12, Y = (14 - v) / 12 for sprite edge coordinates (u right, v down), Z up;
built in sprite px (x = u - 12, y = v, z px) and scaled by usp_talon.finish.

Run: blender --background --python assets/blender/enemies/newshl-229.py [-- --review DIR]
(exports public/models/enemies/newshl-229.glb and its spriteModels entry; --review writes the review
renders to DIR and nothing else).
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve()


def find_repo():
    """The worktree: TYRIAN_REPO if set, else walk up from this script."""
    import os
    env = os.environ.get("TYRIAN_REPO")
    if env:
        return Path(env)
    for p in HERE.parents:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    raise SystemExit("set TYRIAN_REPO to the worktree (assets/blender/common.py not found above the script)")


ROOT = find_repo()
sys.path.insert(0, str(ROOT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshl-229"
MODEL = f"enemies/{NAME}"
W, H = 24, 28
REF = ROOT / "reference" / "models" / NAME
if not (REF / "sprite.json").exists():
    raise SystemExit(f"reference/models/{NAME} is missing in {ROOT} (npm run catalogue builds it)")
CX = 0.5  # the craft's centre line, u = 12.5


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


# --- materials -----------------------------------------------------------------------------------

MATS = {}  # key -> slot
MAT_LIST = []


def mat(sprite, key, index, metallic=0.75, roughness=0.38, glow=0.0, spec=0.5):
    if key in MATS:
        return MATS[key]
    m = common.palette_material(sprite, index, f"{NAME}-{key}", metallic=metallic, roughness=roughness,
                                emission_strength=glow)
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Specular IOR Level"].default_value = spec
    MATS[key] = len(MAT_LIST)
    MAT_LIST.append(m)
    return MATS[key]


def hot(sprite, index, glow):
    """A glowing palette colour: metallic 1 and rough, so the glow is not a reflection (D126, D173)."""
    return mat(sprite, f"hot{index}", index, metallic=1.0, roughness=0.9, glow=glow)


# --- geometry helpers (px space) -----------------------------------------------------------------

def superellipse_arc(xc, a, zb, h, p, n):
    """Top arc of a superellipse, right to left: (x, z)."""
    pts = []
    for i in range(n + 1):
        s = math.pi * i / n
        c, sn = math.cos(s), math.sin(s)
        x = xc + a * math.copysign(abs(c) ** (2 / p), c)
        z = zb + h * abs(sn) ** (2 / p)
        pts.append((x, z))
    return pts


def ring_loop(xc, a, z0, z1, p, n):
    """A closed superellipse ring between z0 and z1 (2n points)."""
    zc, h = (z0 + z1) / 2, (z1 - z0) / 2
    pts = []
    for i in range(2 * n):
        s = math.pi * i / n
        c, sn = math.cos(s), math.sin(s)
        pts.append((xc + a * math.copysign(abs(c) ** (2 / p), c), zc + h * math.copysign(abs(sn) ** (2 / p), sn)))
    return pts


def loft_xz(part, sections, mat_of, cap0=True, cap1=True):
    """Loft closed (x, z) loops at stations y: sections = [(y, [(x, z), ...]), ...] (equal counts).
    mat_of(y_mid, x_mid, z_mid) -> slot."""
    rings = []
    for y, loop in sections:
        rings.append([part.v((x, y, z)) for x, z in loop])
    n = len(rings[0])
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        y0, y1 = sections[i][0], sections[i + 1][0]
        cx = sum(x for x, _ in sections[i][1]) / n
        cz = sum(z for _, z in sections[i][1]) / n
        for k in range(n):
            j = (k + 1) % n
            q = (r0[k], r0[j], r1[j], r1[k])
            mx = sum(v.co.x for v in q) / 4
            mz = sum(v.co.z for v in q) / 4
            part.f(q, mat_of((y0 + y1) / 2, mx, mz), away=(cx, (y0 + y1) / 2, cz))
    for ring, cap, (y, loop), sgn in ((rings[0], cap0, sections[0], -1), (rings[-1], cap1, sections[-1], 1)):
        if cap:
            cx = sum(x for x, _ in loop) / n
            cz = sum(z for _, z in loop) / n
            c = part.v((cx, y, cz))
            for k in range(n):
                j = (k + 1) % n
                part.f((ring[k], ring[j], c), mat_of(y, cx, cz), out=(0, sgn, 0))


def tube(part, pts, slot, sides=8, flat=0.9, smooth_end=True):
    """A faired strut along pts [(x, y, z, r)], octagonal sections (r across, r*flat up), capped;
    the end ring is tiny so the tip closes to a point."""
    up = Vector((0, 0, 1))
    rings = []
    for i, (x, y, z, r) in enumerate(pts):
        p = Vector((x, y, z))
        a = Vector(pts[max(0, i - 1)][:3])
        b = Vector(pts[min(len(pts) - 1, i + 1)][:3])
        t = (b - a).normalized()
        n1 = t.cross(up)
        if n1.length < 1e-6:
            n1 = Vector((1, 0, 0))
        n1.normalize()
        n2 = n1.cross(t).normalized()
        if n2.z < 0:
            n2 = -n2
        ring = []
        for k in range(sides):
            th = 2 * math.pi * (k + 0.5) / sides
            ring.append(part.v(p + n1 * (r * math.cos(th)) + n2 * (r * flat * math.sin(th))))
        rings.append((ring, p))
    for i in range(len(rings) - 1):
        (r0, p0), (r1, p1) = rings[i], rings[i + 1]
        for k in range(sides):
            j = (k + 1) % sides
            q = (r0[k], r0[j], r1[j], r1[k])
            part.f(q, slot, away=tuple((p0 + p1) / 2))
    for (ring, p), sgn in ((rings[0], -1), (rings[-1], 1)):
        c = part.v(tuple(p))
        other = rings[1][1] if sgn < 0 else rings[-2][1]
        for k in range(sides):
            j = (k + 1) % sides
            part.f((ring[k], ring[j], c), slot, out=tuple(p - other))


def loop_tube(part, path, surf_z, r, slot, n=32, sides=6, lift=0.0):
    """A closed round bead along path(theta) -> (x, y), riding the surface z = surf_z(x, y)."""
    rings = []
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n
        x, y = path(th)
        pts.append(Vector((x, y, surf_z(x, y) + lift)))
    for i, p in enumerate(pts):
        t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        n1 = t.cross(Vector((0, 0, 1))).normalized()
        n2 = n1.cross(t).normalized()
        if n2.z < 0:
            n2 = -n2
        rings.append([part.v(p + n1 * (r * math.cos(2 * math.pi * k / sides)) + n2 * (r * 0.8 * math.sin(2 * math.pi * k / sides)))
                      for k in range(sides)])
    for i in range(n):
        r0, r1 = rings[i], rings[(i + 1) % n]
        c = (pts[i] + pts[(i + 1) % n]) / 2
        for k in range(sides):
            j = (k + 1) % sides
            part.f((r0[k], r0[j], r1[j], r1[k]), slot, away=tuple(c))


def block(part, x0, x1, y0, y1, z0, z1, ch, slot):
    T.hull(part, T.cbox(x0, x1, y0, y1, z0, z1, ch), slot)


def carve(part, xs, ys, region, depth, mat_at, top=0.15):
    """Cut the top faces inside region's bbox with x = const and y = const planes, then push the
    verts down by depth(x, y) (> 0 inside the recess) and give faces mat_at(x, y) (None: keep).
    region = (x0, x1, y0, y1)."""
    bm = part.bm
    x0, x1, y0, y1 = region

    def sel(f):
        if not f.is_valid:
            return False
        f.normal_update()
        c = f.calc_center_median()
        return f.normal.z > top and x0 - 0.6 < c.x < x1 + 0.6 and y0 - 0.6 < c.y < y1 + 0.6

    for axis, vals in ((Vector((1, 0, 0)), xs), (Vector((0, 1, 0)), ys)):
        for t in vals:
            faces = [f for f in bm.faces if sel(f)]
            if not faces:
                continue
            geom = list({e for f in faces for e in (*f.verts, *f.edges)}) + faces
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=axis * t, plane_no=axis, dist=1e-4)
    faces = [f for f in bm.faces if sel(f)]
    for f in faces:
        c = f.calc_center_median()
        m = mat_at(c.x, c.y)
        if m is not None:
            f.material_index = m
    verts = {v for f in faces for v in f.verts}
    for v in verts:
        d = depth(v.co.x, v.co.y)
        if d > 0:
            v.co.z -= d


# --- the model -----------------------------------------------------------------------------------

def hood_half(v):
    """Half width of the hood (px): the 45 deg back (a = v + 2, the sprite's staircase) rounding
    into the flat flanks (11.5), narrowing a little at the front lip."""
    back = v + 2.0
    side = T.pchip([9.0, 14.8, 15.8, 16.3], [11.5, 11.5, 11.1, 10.8])(min(max(v, 9.0), 16.3))
    k = 1.4  # corner fillet (px): polynomial smooth min
    hh = min(1.0, max(0.0, 0.5 + 0.5 * (side - back) / k))
    return side * (1 - hh) + back * hh - k * hh * (1 - hh)


HOOD_V = [4.0, 4.4, 4.8, 5.4, 6.0, 6.7, 7.4, 8.2, 9.0, 9.6, 10.3, 11.2, 12.0, 12.8, 13.4, 14.0, 14.6,
          15.2, 15.8, 16.3]
HOOD_T = T.pchip([4.0, 4.4, 4.8, 5.4, 6.0, 6.7, 7.4, 8.2, 9.0, 10.0, 11.0, 12.0, 12.8, 13.4, 14.0, 14.6, 15.2,
                  15.8, 16.3],
                 [2.6, 3.3, 3.9, 4.55, 5.05, 5.45, 5.75, 5.95, 6.05, 6.1, 6.1, 6.0, 5.75, 5.35, 4.9, 4.4, 3.8,
                  3.2, 2.7])
ZB = 0.9
GROOVES = [(6.5, 5.0, 15.4), (9.5, 4.6, 12.7), (15.5, 4.6, 12.7), (18.5, 5.0, 15.4)]  # (u, v0, v1)
MOUTH = ((12.5 - 12, 14.45), (3.4, 1.55))  # centre (x, v), semi-axes (px)
SLOT = ((12.5 - 12, 22.9), (2.3, 1.3))


def build_hood(sprite, P):
    steel = mat(sprite, "steel", 10)
    seam = mat(sprite, "seam", 4, metallic=0.6, roughness=0.55)
    crease = mat(sprite, "crease", 5, metallic=0.6, roughness=0.5)
    under = mat(sprite, "under", 3, metallic=0.5, roughness=0.6)
    secs = []
    for v in HOOD_V:
        a = hood_half(v)
        h = HOOD_T(v) - ZB
        arc = superellipse_arc(CX, a, ZB, h, 3.0, 40)
        loop = arc + [(CX - a * 0.9, ZB - 0.6), (CX + a * 0.9, ZB - 0.6)]
        secs.append((v, loop))

    centre = mat(sprite, "centre", 11)  # the centre panel between the seams on columns 9 and 15

    def m_of(y, x, z):
        if z < ZB - 0.05:
            return under
        if y < 4.6:
            return crease
        return centre if -2.5 < x < 3.5 else steel
    loft_xz(P, secs, m_of)
    P.orient()

    # Lengthwise panel seams: V grooves 0.25 px deep.
    xs = []
    for u, _, _ in GROOVES:
        xs += [u - 12 - 0.4, u - 12, u - 12 + 0.4]

    def g_depth(x, y):
        for u, v0, v1 in GROOVES:
            if abs(x - (u - 12)) < 0.05 and v0 <= y <= v1:
                ramp = min(1.0, (y - v0) / 0.5, (v1 - y) / 0.5)
                return 0.28 * max(0.0, ramp)
        return 0.0

    def g_mat(x, y):
        for u, v0, v1 in GROOVES:
            if abs(x - (u - 12)) < 0.4 and v0 + 0.2 <= y <= v1 - 0.2:
                return seam
        return None
    carve(P, xs, [5.0, 4.6, 12.7, 15.4], (-12, 12, 4.4, 15.6), g_depth, g_mat)

    # The intake grille on the centre panel: slats on columns 10, 12, 14, gaps on 11 and 13.
    slat = mat(sprite, "slat", 11, metallic=0.8, roughness=0.32)
    gap = mat(sprite, "gap", 3, metallic=0.5, roughness=0.6)
    gx = [u - 12 for u in (10.0, 11.0, 11.5, 12.0, 13.0, 13.5, 14.0, 15.0)]

    def gr_depth(x, y):
        if 8.0 <= y <= 12.7:
            for u in (11.5, 13.5):
                if abs(x - (u - 12)) < 0.05:
                    return 0.55
        return 0.0

    def gr_mat(x, y):
        if not (7.7 <= y <= 12.75 and -2.0 <= x <= 3.0):
            return None
        for u in (11.5, 13.5):
            if abs(x - (u - 12)) < 0.5 and y >= 8.0:
                return gap
        return slat
    carve(P, gx, [7.7, 8.0, 12.7], (-2.0, 3.0, 7.7, 12.8), gr_depth, gr_mat)

    # The reactor vent: an oval recess in the sloped front face, hottest at its lower lip.
    (mx, mv), (ax, av) = MOUTH
    wall = hot(sprite, 113, 0.7)
    deep = hot(sprite, 114, 1.1)
    mid = hot(sprite, 116, 1.2)
    rim_lo = hot(sprite, 115, 1.1)
    lip = hot(sprite, 119, 1.2)
    vxs = [mx + ax * (i / 10 - 1) for i in range(21)]
    vys = [mv + av * (i / 6 - 1) for i in range(13)]

    def r_of(x, y):
        return math.hypot((x - mx) / ax, (y - mv) / av)

    def m_depth(x, y):
        r = r_of(x, y)
        return 1.1 * (1 - r * r) ** 1.3 if r < 0.999 else 0.0

    def m_mat(x, y):
        r = r_of(x, y)
        if r > 1.0:
            return None
        if r > 0.8:
            return wall
        if y > mv + 0.45 * av:
            return lip if abs(x - mx) < 1.0 else rim_lo
        if y > mv - 0.35 * av:
            return mid if abs(x - mx) < 0.8 else deep
        return deep if abs(x - mx) < 1.2 else wall
    carve(P, vxs, vys, (mx - ax, mx + ax, mv - av, mv + av), m_depth, m_mat, top=0.05)
    # A machined bezel round the vent (the sprite's dark ring), riding the hood surface.
    bezel = mat(sprite, "bezel", 4, metallic=0.7, roughness=0.4)

    def hood_z(x, v):
        a = hood_half(v)
        k = min(1.0, abs(x - CX) / a)
        return ZB + (HOOD_T(v) - ZB) * max(0.0, 1 - k ** 3) ** (1 / 3)
    loop_tube(P, lambda th: (mx + ax * 1.02 * math.cos(th), mv + av * 1.04 * math.sin(th)), hood_z, 0.42, bezel,
              n=40, lift=0.05)


def build_block(sprite, P):
    housing = mat(sprite, "housing", 8)
    secs = []
    for v, a, zt in ((1.9, 5.0, 3.4), (2.2, 5.45, 3.95), (2.6, 5.5, 4.2), (4.3, 5.5, 4.3), (5.2, 5.5, 4.1)):
        secs.append((v, ring_loop(CX, a, 0.6, zt, 5.0, 14)))
    loft_xz(P, secs, lambda y, x, z: housing)
    # Two lift-thruster ports in its back face (the craft's own drive; hidden from the top view).
    ring = mat(sprite, "port", 4, metallic=0.6, roughness=0.5)
    for u in (9.6, 15.4):
        tube(P, [(u - 12, 2.1, 2.0, 1.35), (u - 12, 1.87, 2.0, 1.35)], ring, sides=12, flat=0.9)
        tube(P, [(u - 12, 2.0, 2.0, 0.85), (u - 12, 1.84, 2.0, 0.85)], hot(sprite, 116, 1.0), sides=12, flat=0.9)


def build_belly(sprite, P):
    deck = mat(sprite, "deck", 3, metallic=0.55, roughness=0.55)
    secs = []
    for v, a, z0, z1 in ((2.4, 4.8, 0.6, 2.0), (3.0, 5.4, 0.3, 2.4), (4.5, 6.2, 0.2, 2.4), (9.0, 10.4, 0.1, 2.0),
                         (15.5, 10.4, 0.1, 1.8), (16.8, 9.6, 0.1, 1.6), (21.3, 9.4, 0.2, 1.5),
                         (21.9, 8.9, 0.5, 1.15)):
        secs.append((v, ring_loop(CX, a, z0, z1, 4.0, 12)))
    loft_xz(P, secs, lambda y, x, z: deck)


def build_front(sprite, P):
    """Bumper bar, cross beam, hip housings."""
    bar = mat(sprite, "bar", 9, metallic=0.8, roughness=0.3)
    beam = mat(sprite, "beam", 6)
    hip = mat(sprite, "hip", 4, metallic=0.7, roughness=0.42)
    tube(P, [(4.6 - 12, 16.6, 1.75, 0.72), (4.8 - 12, 16.6, 1.75, 0.72), (20.2 - 12, 16.6, 1.75, 0.72),
             (20.4 - 12, 16.6, 1.75, 0.72)], bar, sides=10, flat=0.95)
    tube(P, [(4.8 - 12, 17.45, 1.6, 0.5), (20.2 - 12, 17.45, 1.6, 0.5)], beam, sides=8)
    for s in (-1, 1):
        u0, u1 = (1.9, 6.2) if s < 0 else (25 - 6.2, 25 - 1.9)
        tube(P, [(u0 - 12, 17.3, 1.65, 1.0), (u0 + 0.25 - 12, 17.3, 1.65, 1.0), (u1 - 0.25 - 12, 17.3, 1.65, 1.0),
                 (u1 - 12, 17.3, 1.65, 1.0)], hip, sides=10, flat=1.0)


def build_chute(sprite, P):
    rail = mat(sprite, "rail", 4, metallic=0.7, roughness=0.42)
    clamp = mat(sprite, "clamp", 6)
    for x0, x1 in ((9.1, 11.0), (14.0, 15.9)):
        block(P, x0 - 12, x1 - 12, 17.6, 22.4, 1.1, 2.4, 0.3, rail)
        for v0 in (18.1, 20.1):
            block(P, x0 - 12 - 0.25, x1 - 12 + 0.25, v0, v0 + 0.8, 1.1, 2.65, 0.22, clamp)
    floor = hot(sprite, 114, 1.0)
    block(P, 10.9 - 12, 14.1 - 12, 17.6, 22.3, 0.95, 1.45, 0.15, floor)
    # the core rod, three sprite px wide (columns 11-13), heating down its length
    for (v0, v1), idx, g in (((17.75, 18.6), 114, 1.1), ((18.6, 19.5), 116, 1.2), ((19.5, 20.5), 119, 1.2),
                             ((20.5, 21.5), 121, 1.2), ((21.5, 22.6), 124, 1.3)):
        tube(P, [(CX, v0, 1.6, 1.2), (CX, v1, 1.6, 1.2)], hot(sprite, idx, g), sides=12, flat=0.8)


def build_cowl(sprite, P):
    cowl = mat(sprite, "cowl", 6)
    secs = []
    for v, a, z0, z1 in ((21.4, 5.3, 0.4, 2.7), (22.3, 5.5, 0.3, 2.85), (23.3, 4.8, 0.3, 2.7), (24.2, 4.0, 0.4, 2.3),
                         (24.8, 3.0, 0.6, 1.8), (25.05, 2.0, 0.8, 1.4)):
        secs.append((v, ring_loop(CX, a, z0, z1, 3.0, 14)))
    loft_xz(P, secs, lambda y, x, z: cowl)
    P.orient()
    (sx, sv), (ax, av) = SLOT
    rimc = mat(sprite, "slotwall", 4, metallic=0.6, roughness=0.55)
    bore = mat(sprite, "bore", 2, metallic=0.5, roughness=0.6)
    c124, c120, c118, c112 = hot(sprite, 124, 1.1), hot(sprite, 120, 1.0), hot(sprite, 118, 1.0), hot(sprite, 112, 0.6)

    def r_of(x, y):
        return math.hypot((x - sx) / ax, (y - sv) / av)

    def s_depth(x, y):
        r = r_of(x, y)
        return 1.4 * math.sqrt(max(0.0, 1 - r * r)) if r < 0.999 else 0.0

    def s_mat(x, y):
        r = r_of(x, y)
        if r > 1.0:
            return None
        if r > 0.82:
            return rimc
        if y < sv - 0.15:
            return c124 if abs(x - sx) < 0.9 else (c120 if x > sx else c118)
        return c112 if abs(x - sx) < 0.6 else bore
    carve(P, [sx + ax * (i / 8 - 1) for i in range(17)],
          [sv + av * (i / 5 - 1) for i in range(11)], (sx - ax, sx + ax, sv - av, sv + av),
          s_depth, s_mat, top=0.05)
    sv_ = [21.4, 22.3, 23.3, 24.2, 24.8, 25.05]
    fa = T.pchip(sv_, [5.3, 5.5, 4.8, 4.0, 3.0, 2.0])
    f0 = T.pchip(sv_, [0.4, 0.3, 0.3, 0.4, 0.6, 0.8])
    f1 = T.pchip(sv_, [2.7, 2.85, 2.7, 2.3, 1.8, 1.4])

    def cowl_z(x, v):
        a, z0, z1 = fa(v), f0(v), f1(v)
        k = min(1.0, abs(x - CX) / a)
        return (z0 + z1) / 2 + (z1 - z0) / 2 * max(0.0, 1 - k ** 3) ** (1 / 3)
    loop_tube(P, lambda th: (sx + ax * 1.03 * math.cos(th), sv + av * 1.05 * math.sin(th)), cowl_z, 0.38, rimc,
              n=32, lift=0.05)
    # The muzzle on the cowl's front face: a dark ring round a glowing bore.
    ring = mat(sprite, "muzzle", 3, metallic=0.6, roughness=0.5)
    tube(P, [(CX, 24.85, 1.1, 1.15), (CX, 25.2, 1.1, 1.15)], ring, sides=12, flat=1.0)
    tube(P, [(CX, 25.0, 1.1, 0.7), (CX, 25.25, 1.1, 0.7)], hot(sprite, 118, 1.0), sides=12, flat=1.0)


def build_legs(sprite, P):
    outer = mat(sprite, "leg", 7, metallic=0.75, roughness=0.36)
    inner = mat(sprite, "leg_in", 6)
    strut = mat(sprite, "strut", 9, metallic=0.8, roughness=0.32)
    L_OUT = [(2.3, 16.6, 1.9, 1.0), (2.1, 18.5, 1.8, 1.05), (2.0, 21.0, 1.5, 1.0), (2.0, 23.5, 1.1, 0.95),
             (2.0, 25.6, 0.7, 0.8), (2.05, 27.3, 0.38, 0.55), (2.1, 27.85, 0.28, 0.22)]
    L_IN = [(4.8, 18.6, 1.75, 0.85), (4.65, 21.0, 1.45, 0.85), (4.15, 23.0, 1.1, 0.8), (3.0, 24.5, 0.85, 0.7)]
    L_STRUT = [(2.6, 19.6, 1.7, 0.62), (9.3, 19.8, 1.7, 0.62)]
    for s in (-1, 1):
        def m(pts):
            return [((u if s < 0 else 25 - u) - 12, v, z, r) for u, v, z, r in pts]
        tube(P, m(L_OUT), outer, sides=8, flat=0.85)
        tube(P, m(L_IN), inner, sides=8, flat=0.85)
        tube(P, m(L_STRUT), strut, sides=8, flat=0.9)


def build(sprite, coll):
    parts = []
    for name, fn, angle in (("hood", build_hood, 35), ("block", build_block, 35), ("belly", build_belly, 40),
                            ("front", build_front, 45), ("chute", build_chute, 40), ("cowl", build_cowl, 35),
                            ("legs", build_legs, 50)):
        P = T.Part(f"{NAME}_{name}", smooth_angle=angle)
        fn(sprite, P)
        bmesh.ops.triangulate(P.bm, faces=[f for f in P.bm.faces if len(f.verts) > 4])
        parts.append(T.finish(P, MAT_LIST, coll))
    # one object (the game wants one mesh per model; join keeps per-part sharp edges)
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    obj = parts[0]
    obj.name = obj.data.name = NAME
    # drop unused slots
    me = obj.data
    used = sorted({p.material_index for p in me.polygons})
    remap = {k: i for i, k in enumerate(used)}
    idx = [remap[p.material_index] for p in me.polygons]
    mats = [me.materials[k] for k in used]
    me.materials.clear()
    for m in mats:
        me.materials.append(m)
    for p, k in zip(me.polygons, idx):
        p.material_index = k
    return obj


def shell_of(obj, coll):
    """Outline shell (D51) from a sealed copy of the model, every outer island kept (D189)."""
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    bpy.context.view_layer.update()
    sh = common.outline_shell(closed, coll, islands="outer")
    sh.name = sh.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    assert len(sh.data.polygons) > 0, "empty outline shell"
    return sh


# --- review renders (only with --review) ---------------------------------------------------------

def review(obj, shell, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    PX = 1 / 12

    def cam(name, loc, look, ortho=None, lens=50):
        data = bpy.data.cameras.new(name)
        if ortho:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.lens = lens
        c = bpy.data.objects.new(name, data)
        scene.collection.objects.link(c)
        c.location = loc
        d = Vector(look) - Vector(loc)
        c.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return c

    def render(c, path, rx, ry):
        scene.camera = c
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    ext = max(W, H) * PX
    top = cam("top", (0, 0, 20), (0, 0, 0), ortho=ext)
    top.rotation_euler = (0, 0, 0)
    # 1. mask (workbench flat, model only, transparent film)
    shell.hide_render = True
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    render(top, out / "top_mask.png", W * 8, H * 8)
    render(top, out / "top_flat.png", W * 8, H * 8)
    # 2. lit views (EEVEE)
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            pass
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rv")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.45, 0.48, 0.55, 1)
    bg.inputs["Strength"].default_value = 1.0
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 3.5
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(40), math.radians(-25), math.radians(-30))
    shell.hide_render = True
    d = 5.2
    views = [
        ("top", top, 480, 560),
        ("side", cam("side", (-d, 0, 0.25), (0, 0, 0.25), ortho=2.7), 560, 320),
        ("front", cam("front", (0, -d, 0.25), (0, 0, 0.25), ortho=2.7), 560, 320),
        ("rear", cam("rear", (0, d, 0.25), (0, 0, 0.25), ortho=2.7), 560, 320),
        ("q34", cam("q34", (d * 0.6, -d * 0.6, d * 0.55), (0, 0, 0.1), lens=55), 480, 420),
        ("q34b", cam("q34b", (-d * 0.6, d * 0.55, d * 0.55), (0, 0, 0.1), lens=55), 480, 420),
        ("game", cam("game", (0, -d * math.sin(math.radians(32)), d * math.cos(math.radians(32))), (0, 0, 0),
                     lens=55), 480, 420),
        ("under", cam("under", (0.8, -2.5, -4.0), (0, 0, 0.1), lens=55), 480, 420),
    ]
    for name, c, rx, ry in views:
        render(c, out / f"{name}.png", rx, ry)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    (out / "stats.txt").write_text(f"triangles {tris}\nshell faces {len(shell.data.polygons)}\n"
                                   f"materials {[m.name for m in obj.data.materials]}\n")
    print("review renders in", out, "triangles", tris)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    for o in list(bpy.data.objects):  # the startup scene's cube, camera and light
        if o.users_collection and NAME not in [c.name for c in o.users_collection]:
            bpy.data.objects.remove(o)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    shell = shell_of(obj, coll)
    common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"])
    print(f"{sum(len(p.vertices) - 2 for p in obj.data.polygons)} triangles, shell "
          f"{len(shell.data.polygons)} faces")
    if "--review" in sys.argv:
        review(obj, shell, arg("--review"))


if __name__ == "__main__":
    main()
