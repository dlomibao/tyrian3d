"""Shared builder for TIME WAR's edge cannons (assembly-newshl-153.py left, assembly-newshl-197.py right) (newshl.shp 153 + 155/157/159, left; mirror 197 + 195/193/191, right).

TIME WAR (4.17) drops one 48 x 28 px cannon down each screen edge, gripping the blue wall columns
there (tyrian4.lvl level 17, event 7 at t 7950): the left one faces right, the right one is its
mirror. Each cannon is two 2x2 pieces: the mount (newshl-153 / -197, static) and the muzzle
(newshl-155 frames 155/157/159 / newshl-195 frames 195/193/191; the flash frames show while it fires).

The left cannon, from the sprite (inner mask, D74), screen edge to muzzle (u = assembly column edge,
r = row edge; the mount is u 0-24, the muzzle u 24-48):
- a C bracket that grips the wall: an upper arm (rows 2-7) and a deeper lower arm (rows 15-22), each
  a box rail with a rounded top edge and a south chamfer (the sprite's dark rows 6 and 19-21), ending
  at the wall in a foot pad split off by a groove (col 6), joined by a tall spine (cols 8-10);
- the gun housing east of the spine, a squared-off block (cols 10-23, rows 2-16) whose north-east
  corner is cut on the diagonal, its south side a steep chamfer (the dark band, rows 14-16) and its
  east side a chamfer down to the mantlet (cols 22-23); on its deck a raised hatch panel with a
  vent slot (the sprite's bright C-shaped frame round the dark slot, cols 11-16 rows 5-13) and a
  notched strap rib along the east edge (cols 19-21);
- a ridged brace under the housing that runs down to a point toward the screen bottom (rows 17-27);
- the mantlet, an armoured collar plate on the housing's front (cols 22-26, rows 6-20, top corner
  cut), and through it the muzzle stub: a barrel with a collar, a muzzle ring and a bore (rows 9-13),
  a gas tube under it, and a hanger down to a short recoil rod (rows 16-19);
- the muzzle flash (157, 159): thin glowing lens-shaped tongues of flame, red outside, orange inside and a
  white-hot core poking through the top, fitted to each frame's flame (thin glowing geometry, D130).
Bright sprite pixels (the barrel's row 10, the hatch frame's 13s) are sheen; the dark rows under the
arms and housing are the chamfers' lighting. Colours: each region's trimmed sprite median.
Underside: flat closed bottoms.

main(side) builds both cannons (the right is the left's mirror) and exports only the models of `side`
("left": newshl-153, -155; "right": newshl-197, -195). --measure DIR writes the IoU/colour report and
review renders to DIR (nothing is written outside the repo's exports on a normal build). The pieces'
frames are read from the game data with tools/sprite_data.py (the catalogue has no folder for them).
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


def find_repo():
    """The repo: the --repo argument, else the first parent of this script holding assets/blender/common.py."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--repo" in argv:
        return Path(argv[argv.index("--repo") + 1]).resolve()
    for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    raise SystemExit("cannot find the repo from this script's location; pass --repo")


WT = find_repo()
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "tools")]
import common  # noqa: E402
import sprite_data  # noqa: E402
from usp_talon import pchip  # noqa: E402

NAME = "assembly-newshl-153"  # collection name only
LEFT = {"mount": "newshl-153", "muzzle": "newshl-155", "flash": [157, 159], "rest": 155}
RIGHT = {"mount": "newshl-197", "muzzle": "newshl-195", "flash": [193, 191], "rest": 195}
PX = 1 / 12


def X(u):
    """Assembly column edge (0..48, piece seam at 24) to px x about the cannon's centre."""
    return u - 24.0


def Y(r):
    """Row edge (0..28) to px y (sprite up = +y)."""
    return 14.0 - r


# --- mesh helpers (px), after lib_cannon_pair14 ---------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def ring(self, pts):
        return [self.bm.verts.new(p) for p in pts]

    def face(self, vs, mat, smooth=False):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        f.smooth = smooth
        return f

    def loft(self, rings, mats, cap0=True, cap1=True, smooth=True):
        vr = [self.ring(r) for r in rings]
        if isinstance(mats, int):
            mats = [mats] * (len(vr) - 1)
        for k in range(len(vr) - 1):
            a, b = vr[k], vr[k + 1]
            if len(a) == 1 or len(b) == 1:
                ring, apex = (b, a[0]) if len(a) == 1 else (a, b[0])
                n = len(ring)
                for i in range(n):
                    self.face([ring[i], ring[(i + 1) % n], apex], mats[k], smooth)
                continue
            n = len(a)
            for i in range(n):
                j = (i + 1) % n
                self.face([a[i], a[j], b[j], b[i]], mats[k], smooth)
        if cap0 and len(vr[0]) > 2:
            self.face(vr[0], mats[0])
        if cap1 and len(vr[-1]) > 2:
            self.face(vr[-1], mats[-1])
        return vr


def area2(o):
    return sum(o[i][0] * o[i - 1][1] - o[i - 1][0] * o[i][1] for i in range(len(o))) * -0.5


def ccw(o):
    return o if area2(o) > 0 else list(reversed(o))


def inset(o, d):
    """Every edge of the CCW polygon moved d inward (mitred, mitre capped)."""
    n = len(o)
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = o[i], o[(i + 1) % n]
        ln = math.hypot(x1 - x0, y1 - y0) or 1e-9
        lines.append(((x0 - (y1 - y0) / ln * d, y0 + (x1 - x0) / ln * d), (x1 - x0, y1 - y0)))
    out = []
    for i in range(n):
        (p, u), (q, v) = lines[i - 1], lines[i]
        den = u[0] * v[1] - u[1] * v[0]
        if abs(den) < 1e-9:
            out.append(q)
            continue
        t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
        pt = (p[0] + u[0] * t, p[1] + u[1] * t)
        ox, oy = o[i]
        dd = math.hypot(pt[0] - ox, pt[1] - oy)
        if dd > 2.5 * d:
            pt = (ox + (pt[0] - ox) * 2.5 * d / dd, oy + (pt[1] - oy) * 2.5 * d / dd)
        out.append(pt)
    return out


def fillet(poly, radii, seg=3):
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        if r <= 0:
            out.append(tuple(p1))
            continue
        a = p1 + (p0 - p1).normalized() * min(r, (p0 - p1).length * 0.49)
        b = p1 + (p2 - p1).normalized() * min(r, (p2 - p1).length * 0.49)
        for k in range(seg + 1):
            t = k / seg
            q = a * (1 - t) ** 2 + p1 * 2 * t * (1 - t) + b * t * t
            out.append((q.x, q.y))
    return out


def ur(pts):
    """[(u, r)] to a CCW [(x, y)] in px."""
    return ccw([(X(u), Y(r)) for u, r in pts])


def slab(M, o, z0, z1, mat, ch=0.0, chb=0.0, top=None):
    """A prism over the CCW outline o from z0 to z1, top edge given a rounded chamfer ch, bottom a plain chamfer chb."""
    rings = []
    if chb:
        rings.append([(x, y, z0) for x, y in inset(o, chb)])
        rings.append([(x, y, z0 + chb) for x, y in o])
    else:
        rings.append([(x, y, z0) for x, y in o])
    if ch:
        rings.append([(x, y, z1 - ch) for x, y in o])
        rings.append([(x, y, z1 - ch * 0.3) for x, y in inset(o, ch * 0.3)])
        rings.append([(x, y, z1) for x, y in inset(o, ch)])
    else:
        rings.append([(x, y, z1) for x, y in o])
    vr = M.loft(rings, [mat] * (len(rings) - 1), cap0=True, cap1=False, smooth=False)
    M.face(vr[-1], mat if top is None else top)


def lathe(M, yc, zc, prof, mats, sides=28, smooth=True):
    """Revolve a profile [(u, radius)] about the line y = yc, z = zc along x (radius 0 = apex)."""
    rings = []
    for u, r in prof:
        if r <= 1e-6:
            rings.append([(X(u), yc, zc)])
        else:
            rings.append([(X(u), yc + r * math.cos(2 * math.pi * k / sides),
                           zc + r * math.sin(2 * math.pi * k / sides)) for k in range(sides)])
    M.loft(rings, mats, cap0=False, cap1=False, smooth=smooth)


def u_loft(M, stations, mats, smooth=False):
    """Loft along x: stations [(u, [(r, z)])], each a closed section; ends capped."""
    rings = [[(X(u), Y(r), z) for r, z in sec] for u, sec in stations]
    M.loft(rings, mats, cap0=True, cap1=True, smooth=smooth)


def r_loft(M, stations, mats, smooth=False):
    """Loft along y: stations [(r, [(u, z)])], each a closed section; ends capped."""
    rings = [[(X(u), Y(r), z) for u, z in sec] for r, sec in stations]
    M.loft(rings, mats, cap0=True, cap1=True, smooth=smooth)


def shrink(sec, d):
    """A closed (a, z) section pulled toward its centroid by d (end chamfers)."""
    ca = sum(p[0] for p in sec) / len(sec)
    cz = sum(p[1] for p in sec) / len(sec)
    out = []
    for a, z in sec:
        da, dz = a - ca, z - cz
        ln = math.hypot(da, dz) or 1.0
        out.append((a - da / ln * d, z - dz / ln * d))
    return out


def bolt(M, u, r, z, mat, rad=0.42, h=0.35):
    sides = 8
    x, y = X(u), Y(r)
    rings = [[(x + rad * math.cos(2 * math.pi * k / sides + 0.39), y + rad * math.sin(2 * math.pi * k / sides + 0.39), zz)
              for k in range(sides)] for zz in (z - 0.2, z + h)]
    rings.append([(x + rad * 0.6 * math.cos(2 * math.pi * k / sides + 0.39),
                   y + rad * 0.6 * math.sin(2 * math.pi * k / sides + 0.39), z + h + 0.12) for k in range(sides)])
    M.loft(rings, mat, cap0=True, cap1=True, smooth=False)


def ellipsoid(M, c, rad, mat, seg=14, rings=8):
    """A closed ellipsoid at c = (x, y, z) px, radii rad = (a, b, h)."""
    pts = [[(c[0], c[1], c[2] - rad[2])]]
    for i in range(1, rings):
        t = -math.pi / 2 + math.pi * i / rings
        pts.append([(c[0] + rad[0] * math.cos(t) * math.cos(2 * math.pi * k / seg),
                     c[1] + rad[1] * math.cos(t) * math.sin(2 * math.pi * k / seg),
                     c[2] + rad[2] * math.sin(t)) for k in range(seg)])
    pts.append([(c[0], c[1], c[2] + rad[2])])
    M.loft(pts, mat, cap0=False, cap1=False, smooth=True)


# --- materials ----------------------------------------------------------------------------------

(BODY, RIB, SLOT, BRACE, MANT, BARREL, RING, BORE, ROD, BOLT) = range(10)
FIRE_OUT, FIRE_MID, FIRE_HOT = range(3)


FRAMES = {"newshl-153": [153], "newshl-155": [155, 157, 159], "newshl-195": [195, 193, 191], "newshl-197": [197]}


def piece_sprite(name):
    """A piece's frames read straight from the game data (tools/sprite_data.py): the catalogue's world
    never draws these bot-only pieces, so reference/models has no folder for them."""
    return sprite_data.load(WT, name, "newshl.shp", FRAMES[name])


def merged_sprite():
    data = piece_sprite(LEFT["mount"])
    data["colors"].update(piece_sprite(LEFT["muzzle"])["colors"])
    data["name"] = NAME
    return data


def materials(sprite):
    def pal(i, tag, metallic, roughness, spec=0.5):
        m = common.palette_material(sprite, i, f"nshl153{tag}", metallic=metallic, roughness=roughness)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    return [
        pal(9, "", 0.6, 0.36, 0.7),          # BODY arms, spine, housing (median 9)
        pal(10, "", 0.65, 0.3, 0.8),         # RIB strap rib (median 10)
        pal(6, "_slot", 0.4, 0.55, 0.4),     # SLOT vent slot floor (median 6)
        pal(6, "", 0.55, 0.42, 0.6),         # BRACE ridged brace under the housing (median 5, lit slopes)
        pal(7, "", 0.6, 0.38, 0.7),          # MANT mantlet (median 5-7; its lower half is shading)
        pal(6, "_bar", 0.7, 0.26, 0.85),     # BARREL (median 6; row 10's 13s are sheen)
        pal(9, "_ring", 0.7, 0.24, 0.85),    # RING collar and muzzle ring (col 31's 9/10)
        pal(2, "", 0.3, 0.7, 0.3),           # BORE
        pal(4, "", 0.55, 0.4, 0.6),          # ROD gas tube, hanger, recoil rod (median 4)
        pal(11, "", 0.7, 0.3, 0.8),          # BOLT bolt heads
    ]


def fire_materials(sprite):
    def glow(i, s):
        return common.palette_material(sprite, i, "nshl153fire", metallic=1.0, roughness=0.85, emission_strength=s)
    # Glow at the palette colour (D126): past 1 / the colour's brightest linear channel a red runs to pink
    # and an orange to white in game, so all three stay at 1, as the other flames (lib_b050, newsh5-91).
    return [glow(119, 1.0), glow(122, 1.0), glow(126, 1.0)]


# --- the left cannon ----------------------------------------------------------------------------

ZT = 11.0       # housing deck
ZARM = 9.4      # arm tops
ZB = 0.8        # bottoms
BAX = (10.85, 6.6)   # barrel axis (row edge, z)


def arm_section(rn, rs, zt, rch, zs):
    """(r, z) section of an arm rail: rounded north top edge, flat top to rch, chamfer down to (rs, zs)."""
    return [(rn, ZB), (rn, zt - 0.8), (rn + 0.12, zt - 0.35), (rn + 0.4, zt - 0.08), (rn + 0.8, zt),
            (rch, zt), (rch + 0.35, zt - 0.12), (rs - 0.05, zs + 0.15), (rs, zs - 0.2), (rs, ZB)]


def arms(M):
    for rn, rs, rch, zs in ((2.0, 7.0, 5.4, 6.2), (15.0, 22.0, 18.3, 3.8)):
        full = arm_section(rn, rs, ZARM, rch, zs)
        pad = arm_section(rn, rs, ZARM + 0.35, rch, zs + 0.2)
        grv = shrink(full, 0.4)
        st = [(1.0, shrink(pad, 0.5)), (1.45, pad), (5.7, pad), (6.0, shrink(pad, 0.25)), (6.05, grv),
              (6.85, grv), (6.9, shrink(full, 0.2)), (7.2, full), (9.6 if rn > 10 else 8.6, full)]
        u_loft(M, st, BODY)
        for rr in ((rn + 1.4, rch - 0.6) if rn < 10 else (rn + 1.3, rch - 0.9)):
            bolt(M, 3.4, rr, ZARM + 0.35, BOLT)


def spine(M):
    """The bracket's spine joining the arms, cols 8-10, rows 2-18.5."""
    o = ur(fillet([(7.95, 2.0), (10.8, 2.0), (10.8, 18.6), (7.95, 18.6)], [0.3, 0.0, 0.0, 0.5], seg=2))
    slab(M, o, ZB, ZT, BODY, ch=0.7)


def housing(M):
    """The gun housing, lofted along u: north edge stepping down the diagonal, deck at ZT, steep south
    chamfer (rows 13.4-16.6), east end chamfered down to the mantlet."""
    def sec(rn, zt):
        zs = zt - 3.6
        return [(rn, ZB), (rn, zt - 0.7), (rn + 0.2, zt - 0.2), (rn + 0.65, zt), (13.3, zt),
                (13.75, zt - 0.3), (16.6, zs), (16.6, ZB)]
    rn = pchip([10.0, 13.6, 15.5, 17.5, 19.0, 23.6], [2.0, 2.05, 3.45, 4.5, 5.15, 5.4])
    st = []
    for u, zt in ((10.4, ZT), (12.0, ZT), (14.0, ZT), (15.0, ZT), (16.0, ZT), (17.0, ZT), (18.0, ZT),
                  (18.6, ZT), (19.2, ZT), (21.2, ZT), (21.7, ZT - 0.25), (22.6, ZT - 1.4), (23.6, ZT - 2.6)):
        st.append((u, sec(rn(u), zt)))
    u_loft(M, st, BODY)


def deck(M):
    """Hatch panel with a vent slot (the C-shaped frame), strap rib with a notch, bolts."""
    z = ZT - 0.1
    # The hatch: a C-shaped raised frame (top bar, left bar, bottom bar) round the vent slot.
    for poly, rad in (([(11.0, 4.9), (17.6, 4.9), (17.6, 8.0), (11.0, 8.0)], 0.25),
                      ([(11.0, 8.0), (11.95, 8.0), (11.95, 10.7), (11.0, 10.7)], 0.0),
                      ([(11.0, 10.7), (16.9, 10.7), (16.9, 13.7), (11.0, 13.7)], 0.25)):
        slab(M, ur(fillet(poly, rad, seg=2)), z, ZT + 0.75, BODY, ch=0.3)
    # Vent slot floor (recessed below the deck) with louvre bars.
    o = ur([(11.9, 8.0), (16.9, 8.0), (16.9, 10.7), (11.9, 10.7)])
    slab(M, o, ZT - 0.2, ZT + 0.12, SLOT)
    for k in range(4):
        u0 = 12.5 + k * 1.15
        slab(M, ur([(u0, 8.05), (u0 + 0.4, 8.05), (u0 + 0.4, 10.65), (u0, 10.65)]), ZT, ZT + 0.45, SLOT)
    # Strap rib along the east deck edge, notched at row 9.
    for r0, r1 in ((5.15, 8.9), (9.75, 13.8)):
        slab(M, ur(fillet([(19.0, r0), (21.6, r0), (21.6, r1), (19.0, r1)], 0.3, seg=2)), z, ZT + 0.9, RIB, ch=0.35)
    slab(M, ur([(19.3, 8.8), (21.3, 8.8), (21.3, 9.85), (19.3, 9.85)]), z, ZT + 0.35, RIB)
    for r in (6.3, 12.6):
        bolt(M, 20.3, r, ZT + 0.9, BOLT, rad=0.38, h=0.25)
    # Spine top bolts and a deck seam bolt row.
    for r in (4.0, 9.5, 15.5):
        bolt(M, 9.4, r, ZT, BOLT, rad=0.36, h=0.25)


def brace(M):
    """The ridged brace under the housing, running down to a point (rows 16.6-27.6)."""
    uw = pchip([22.5, 23.5, 24.5, 25.5, 26.5, 27.5, 27.9], [13.0, 15.0, 17.0, 18.8, 20.0, 21.0, 21.6])
    rid = pchip([14.0, 17.0, 20.0, 24.0, 27.9], [15.0, 15.4, 16.8, 19.6, 22.0])
    zr = pchip([14.0, 16.6, 20.0, 24.0, 27.9], [7.3, 7.2, 6.3, 4.8, 2.8])
    ue = 23.0

    def sec(r, uwest):
        u_r = min(rid(r), ue - 0.5)
        z_r = zr(r)
        z_w = max(ZB + 0.9, z_r - (u_r - uwest) * 0.32)
        z_e = max(ZB + 0.9, z_r - (ue - u_r) * 0.4)
        return [(uwest, ZB), (ue, ZB), (ue, z_e - 0.3), (ue - 0.25, z_e), (u_r, z_r),
                (uwest + 0.25, z_w), (uwest, z_w - 0.3)]
    st = []
    for r in (14.5, 16.0, 17.5, 19.0, 20.5, 21.9):
        st.append((r, sec(r, 9.65)))
    for r in (22.05, 22.5, 23.0, 23.5, 24.0, 24.5, 25.0, 25.5, 26.0, 26.5, 27.0, 27.5, 27.85):
        st.append((r, sec(r, uw(min(r, 27.9)) - (0.0 if r > 22.4 else 0.0))))
    r_loft(M, st, BRACE)


def mantlet(M):
    o = ur(fillet([(22.0, 5.5), (23.7, 5.85), (26.6, 8.15), (27.0, 8.6), (27.0, 19.85), (22.0, 19.85)],
                  [0.0, 0.4, 0.3, 0.2, 0.5, 0.0], seg=2))
    slab(M, o, ZB, 9.6, MANT, ch=0.8)
    # bolt flange round the barrel on the mantlet face, and face bolts
    yc, zc = Y(BAX[0]), BAX[1]
    lathe(M, yc, zc, [(26.6, 0.0), (26.6, 2.5), (27.2, 2.5), (27.4, 2.25), (27.4, 0.0)],
          [MANT, MANT, MANT, MANT], sides=24)
    for r in (16.0, 18.6):
        x = X(27.0)
        sides = 8
        rings = [[(x - 0.2, Y(r) + 0.4 * math.cos(2 * math.pi * k / sides), 5.6 + 0.4 * math.sin(2 * math.pi * k / sides))
                  for k in range(sides)],
                 [(x + 0.3, Y(r) + 0.4 * math.cos(2 * math.pi * k / sides), 5.6 + 0.4 * math.sin(2 * math.pi * k / sides))
                  for k in range(sides)]]
        M.loft(rings, BOLT, cap0=True, cap1=True, smooth=False)


def gun(M):
    yc, zc = Y(BAX[0]), BAX[1]
    prof = [(26.4, 0.0), (26.4, 1.85), (27.3, 1.85), (27.42, 2.05), (28.2, 2.05), (28.35, 1.85),
            (30.45, 1.85), (30.6, 2.05), (31.85, 2.05), (32.0, 1.8), (32.0, 1.1), (30.9, 1.1), (30.9, 0.0)]
    mats = [BARREL, BARREL, RING, RING, RING, BARREL, RING, RING, RING, RING, BORE, BORE]
    lathe(M, yc, zc, prof, mats, sides=28)
    # gas tube under the barrel
    lathe(M, Y(13.15), 5.0, [(26.4, 0.0), (26.4, 0.85), (31.2, 0.85), (31.45, 0.6), (31.5, 0.0)],
          [ROD, ROD, ROD, ROD], sides=16)
    # hanger: clamp on the gas tube, a post, clamp on the recoil rod
    o = ur(fillet([(28.0, 13.5), (31.0, 13.5), (31.0, 14.9), (30.3, 15.2), (30.3, 15.8), (31.0, 16.1),
                   (31.0, 17.6), (28.0, 17.6), (28.0, 16.1), (28.7, 15.8), (28.7, 15.2), (28.0, 14.9)],
                  [0.3, 0.3, 0.2, 0.0, 0.0, 0.2, 0.3, 0.3, 0.2, 0.0, 0.0, 0.2], seg=2))
    slab(M, o, 2.6, 5.3, ROD, ch=0.35, chb=0.2)
    # recoil rod
    lathe(M, Y(18.0), 3.6, [(25.6, 0.0), (25.6, 1.0), (30.5, 1.0), (30.85, 0.75), (30.95, 0.0)],
          [ROD, ROD, ROD, ROD], sides=16)


def build_static(sprite, name, coll):
    M = Mesh()
    arms(M)
    spine(M)
    housing(M)
    deck(M)
    brace(M)
    mantlet(M)
    gun(M)
    return to_object(M, name, materials(sprite), coll)


FLAMES = {  # (u, r, a, b) plan ellipses fitted to each flash frame's flame (fitflame.py, grid IoU)
    157: [(35.64, 15.39, 2.74, 2.75), (39.47, 13.43, 3.6, 2.11), (33.23, 11.92, 5.41, 3.9), (32.07, 17.37, 3.73, 1.65),
          (32.81, 13.01, 1.4, 2.62), (28.5, 13.94, 1.3, 4.69), (30.88, 17.09, 2.03, 3.1)],
    159: [(34.4, 17.85, 5.99, 2.77), (34.08, 20.72, 4.24, 1.2), (40.09, 15.94, 2.82, 3.01), (42.21, 17.17, 5.06, 2.46),
          (29.18, 14.91, 1.98, 3.73), (37.91, 10.89, 3.69, 3.92), (35.79, 10.81, 5.58, 5.74), (38.56, 13.51, 1.2, 7.08),
          (39.24, 13.73, 7.1, 6.53)],
}


LAYERS = {  # hotter layers (u, r, a, b): pixels >= 121 (orange) and >= 125 (white-hot), fitlayers.py
    157: {FIRE_MID: [(34.61, 16.57, 2.09, 1.79), (33.01, 12.51, 0.7, 3.9), (38.42, 13.12, 2.26, 1.48),
                     (34.57, 11.24, 3.83, 1.73), (31.26, 15.16, 1.54, 3.87)],
          FIRE_HOT: [(32.46, 17.1, 3.22, 0.94), (33.61, 10.77, 2.51, 1.24), (31.82, 15.83, 2.34, 0.7)]},
    159: {FIRE_MID: [(41.39, 13.6, 5.15, 0.97), (32.75, 15.84, 2.41, 2.89), (35.91, 14.02, 4.64, 4.26),
                     (40.35, 16.87, 4.7, 1.81), (36.26, 10.15, 3.27, 3.57), (42.09, 14.04, 2.45, 3.7),
                     (33.82, 14.56, 3.92, 5.62)],
          FIRE_HOT: [(36.96, 11.55, 2.82, 1.25), (33.54, 11.06, 1.3, 1.72), (37.69, 13.25, 0.8, 1.29),
                     (32.53, 17.14, 3.24, 1.24)]},
}


def blob(M, c, rad, mat, eps=1.0, seg=14, rings=8):
    """A superellipsoid blob at c, radii rad; eps < 1 flattens its top and squares its rim."""
    def pw(v):
        return math.copysign(abs(v) ** eps, v)
    pts = [[(c[0], c[1], c[2] - rad[2])]]
    for i in range(1, rings):
        t = -math.pi / 2 + math.pi * i / rings
        pts.append([(c[0] + rad[0] * pw(math.cos(t)) * math.cos(2 * math.pi * k / seg),
                     c[1] + rad[1] * pw(math.cos(t)) * math.sin(2 * math.pi * k / seg),
                     c[2] + rad[2] * pw(math.sin(t))) for k in range(seg)])
    pts.append([(c[0], c[1], c[2] + rad[2])])
    M.loft(pts, mat, cap0=False, cap1=False, smooth=True)


def build_flame(sprite, frame, name, coll):
    """The flash: a red shell of thin lens-shaped tongues fitted to the frame's flame, then orange and
    white-hot ones fitted to the sprite's hotter pixels, each standing just through the layer under
    it, so the top view shows the sprite's colour layout and the side view a flat burst of flame."""
    M = Mesh()
    zc = BAX[1]
    shell = []
    for u, r, a, b in FLAMES[frame]:
        # thin flat tongues of flame (lens sections), not puffy balls: low height, pointed rims
        h = 0.3 * min(a, b) + 0.7
        shell.append((u, r, a, b, h))
        blob(M, (X(u), Y(r), zc), (a, b, h), FIRE_OUT, eps=1.35)

    def top(blobs, u, r):
        z = 0.0
        for bu, br, a, b, h in blobs:
            q = ((u - bu) / a) ** 2 + ((r - br) / b) ** 2
            if q < 1:
                z = max(z, h * math.sqrt(1 - q))
        return z
    under = list(shell)
    for mat in (FIRE_MID, FIRE_HOT):
        made = []
        for u, r, a, b in LAYERS[frame][mat]:
            # tall enough to show ~85% of its plan through what lies under it
            need = max(top(under, u + du * a * 0.7, r + dr * b * 0.7)
                       for du, dr in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (0.7, 0.7), (-0.7, -0.7), (0.7, -0.7), (-0.7, 0.7)))
            h = max(need / 0.78 + 0.2, top(under, u, r) + 0.35)
            made.append((u, r, a, b, h))
            # bulging up only: its bottom stays inside the shell, so the side view is red below
            lo = 0.25 * min(a, b) + 0.3
            blob(M, (X(u), Y(r), zc + (h - lo) / 2), (a, b, (h + lo) / 2), mat, eps=1.1, seg=12, rings=8)
        under += made
    obj = to_object(M, name, fire_materials(sprite), coll, sharp=False)
    return common.frame_part(obj, [frame])


def to_object(M, name, mats, coll, sharp=True):
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.scale(bm, vec=(PX, PX, PX), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    if sharp:
        me.set_sharp_from_angle(angle=math.radians(35.0))
        weighted_normals(obj)
    else:
        me.shade_smooth()
    return obj


def weighted_normals(obj):
    """Face-area weighted normals (sharp edges kept), so big flat faces stay flat next to their
    rounded chamfers instead of shading in triangles. The glTF export applies it."""
    wn = obj.modifiers.new("weighted_normal", "WEIGHTED_NORMAL")
    wn.mode = "FACE_AREA"
    wn.keep_sharp = True
    wn.weight = 100


def mirror_obj(src, name, coll):
    me = src.data.copy()
    me.name = name
    bm = bmesh.new()
    bm.from_mesh(me)
    for v in bm.verts:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    for k in src.keys():
        obj[k] = src[k]
    coll.objects.link(obj)
    if src.modifiers.get("weighted_normal"):
        me.set_sharp_from_angle(angle=math.radians(35.0))
        weighted_normals(obj)
    return obj


def split_open(obj, layout, coll):
    """Cut the outline shell into the pieces without filling the cuts (no ink along the seams)."""
    out = {}
    for name, cx in layout:
        x0 = cx / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, 0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(o)
        out[name] = o
    return out


# --- measuring ------------------------------------------------------------------------------------

def composed(side, mframe):
    """The cannon's sprite (48 x 28 palette indices) with the muzzle on frame mframe, and the colours."""
    pieces = [(side["mount"], None), (side["muzzle"], mframe)] if side is LEFT else [(side["muzzle"], mframe), (side["mount"], None)]
    idx = [[-1] * 48 for _ in range(28)]
    cols = {}
    for k, (n, f) in enumerate(pieces):
        sp = piece_sprite(n)
        i = next(fr["pixels"] for fr in sp["frames"] if f is None or fr["index"] == f)
        cols.update({int(ci): tuple(rgb) for ci, rgb in sp["colors"].items()})
        for y in range(28):
            for x in range(24):
                if i[y][x] >= 0:
                    idx[y][24 * k + x] = i[y][x]
    return idx, cols


def raycast_top(objs, k, mirror=False):
    """Top-view coverage of objs (assembly coordinates, cannon centred at x 0), 48k x 28k."""
    dg = bpy.context.evaluated_depsgraph_get()
    evs = [o.evaluated_get(dg) for o in objs]
    top = []
    for yy in range(28 * k):
        s = (yy + 0.5) / k
        row = []
        for xx in range(48 * k):
            e = (xx + 0.5) / k
            x = X(e) * PX
            p = Vector((x, Y(s) * PX, 5.0))
            hit = False
            for o, ev in zip(objs, evs):
                lp = o.matrix_world.inverted() @ p
                ld = (o.matrix_world.inverted().to_3x3() @ Vector((0, 0, -1))).normalized()
                if ev.ray_cast(lp, ld)[0]:
                    hit = True
                    break
            row.append(hit)
        top.append(row)
    return top


def palette_grid(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mats = [m.name for m in obj.data.materials]
    inv = obj.matrix_world.inverted()
    pal = [[None] * 48 for _ in range(28)]
    for r in range(28):
        for c in range(48):
            p = inv @ Vector((X(c + 0.5) * PX, Y(r + 0.5) * PX, 5.0))
            hit, loc, nrm, fi = ev.ray_cast(p, Vector((0, 0, -1)))
            if hit:
                pal[r][c] = int(mats[obj.data.polygons[fi].material_index].split("_")[1])
    return pal


REGIONS = {  # left cannon, rest frame: [col0, col1, row0, row1] boxes, inclusive
    "arm_upper": [[1, 7, 2, 5]], "arm_lower": [[1, 7, 15, 18]], "spine": [[8, 10, 7, 13]],
    "deck": [[12, 18, 2, 7], [12, 18, 12, 13]], "slot": [[12, 15, 8, 10]], "rib": [[19, 21, 5, 13]],
    "east_slope": [[22, 23, 6, 13]], "south_band": [[11, 23, 14, 16]], "wedge": [[12, 22, 17, 25]],
    "mantlet": [[24, 25, 8, 19]], "barrel": [[27, 30, 9, 13]], "lug": [[27, 30, 16, 18]]}


def measure(static_l, flames_l, static_r, flames_r, out_dir):
    import collections
    import sprite_mask as SM
    k = 6
    rep = {}
    worst = 1.0
    diffs = {}
    for side, static, flames in ((LEFT, static_l, flames_l), (RIGHT, static_r, flames_r)):
        for fr in [side["rest"]] + side["flash"]:
            objs = [static] + ([flames[fr]] if fr in flames else [])
            top = raycast_top(objs, k)
            idx, cols = composed(side, fr)
            frames = [composed(side, f)[0] for f in [side["rest"]] + side["flash"]]
            MS = SM.masks(idx, cols, SM.pulse_partners(idx, frames))
            m = SM.measure(MS, top)
            # per piece (24 x 28 each)
            pieces = {}
            for i in range(2):
                sub = [row[i * 24 * k:(i + 1) * 24 * k] for row in top]
                sm = {key: [row[i * 24:(i + 1) * 24] for row in MS[key]] for key in MS}
                pieces[i] = SM.measure(sm, sub)["iou_rule_grid"]
            key = f"{side['mount']}+{fr}"
            rep[key] = {"iou_rule_grid": m["iou_rule_grid"], "iou_rule": m["iou_rule"], "pieces": pieces,
                        "edge_vs_inner_px": m["edge_vs_inner_px"]}
            worst = min(worst, m["iou_rule_grid"])
            g = [[sum(top[r * k + j][c * k + i] for j in range(k) for i in range(k)) / (k * k) >= 0.5
                  for c in range(48)] for r in range(28)]
            diffs[key] = ["".join("#" if MS["inner"][r][c] and g[r][c] else "-" if MS["inner"][r][c] and not MS["free"][r][c]
                                  else "f" if MS["free"][r][c] else "+" if g[r][c] else "o" if MS["outer"][r][c] else "."
                                  for c in range(48)) for r in range(28)]
            if side is LEFT and fr == side["rest"]:
                write_mask_png(out_dir / "top_mask_left_rest.png", top)
    rep["worst_iou_rule_grid"] = worst
    # colour per region (left cannon, rest frame)
    idx, cols = composed(LEFT, LEFT["rest"])
    med = {}
    for n, boxes in REGIONS.items():
        v = sorted((SM.luma(cols[idx[r][c]]), idx[r][c]) for c0, c1, r0, r1 in boxes
                   for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if idx[r][c] >= 0)
        t = len(v) // 5
        vv = v[t:len(v) - t] or v
        med[n] = vv[len(vv) // 2][1]
    reg = {"regions": REGIONS, "median": med}
    pal = palette_grid(static_l)
    col = {}
    for n, boxes in reg["regions"].items():
        cnt = collections.Counter(pal[r][c] for c0, c1, r0, r1 in boxes for r in range(r0, r1 + 1)
                                  for c in range(c0, c1 + 1) if pal[r][c] is not None)
        col[n] = {"sprite": reg["median"][n], "model": cnt.most_common(2)}
    rep["colour"] = col
    return rep, diffs


def write_mask_png(path, top):
    import struct
    import zlib
    h, w = len(top), len(top[0])
    raw = b"".join(b"\x00" + bytes(255 if v else 0 for v in row) for row in top)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


# --- review renders -------------------------------------------------------------------------------

def setup_render():
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.30, 0.33, 0.36, 1)
    bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = Vector((6, 8.4, -20)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(sun)
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 0.8
    fill.rotation_euler = Vector((-0.4, -0.6, -0.4)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(fill)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    return scene, cam


def render_views(out, coll, show_sets):
    """show_sets: {tag: [objects to show]}; renders each view per tag."""
    out.mkdir(parents=True, exist_ok=True)
    scene, cam = setup_render()

    def look(loc, target):
        cam.location = Vector(loc)
        cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()

    def shoot(name, w, h, ortho=None, lens=50):
        scene.render.resolution_x, scene.render.resolution_y = w, h
        if ortho:
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = ortho
        else:
            cam.data.type = "PERSP"
            cam.data.lens = lens
        cam.data.clip_end = 100
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)

    def show(objs):
        for o in coll.objects:
            o.hide_render = o not in objs

    c = Vector((0, 0, 0.45))
    for tag, objs in show_sets.items():
        show(objs)
        cam.location = (0, 0, 10)
        cam.rotation_euler = (0, 0, 0)
        shoot(f"top_{tag}", 960, 560, ortho=4.0 * 1.0)
        if tag not in ("rest", "f159"):
            continue
        a = math.radians(15)
        look((0, -26 * math.sin(a), 26 * math.cos(a)), c)
        shoot(f"game_{tag}", 960, 560, lens=180)
        look((2.6, -3.6, 3.2), (0.3, 0, 0.45))
        shoot(f"q_front_{tag}", 760, 480, lens=45)
        if tag != "rest":
            continue
        look((0, -12, 0.5), (0, 0, 0.5))
        shoot("side", 960, 360, ortho=4.4)
        look((12, 0, 0.55), (0, 0, 0.55))
        shoot("front", 560, 360, ortho=2.8)
        look((-12, 0, 0.55), (0, 0, 0.55))
        shoot("rear", 560, 360, ortho=2.8)
        look((-3.0, 3.6, 3.0), (0, 0, 0.45))
        shoot("q_rear", 760, 480, lens=45)
        look((-2.4, -3.8, 1.6), (0, 0, 0.45))
        shoot("q_low", 760, 480, lens=45)
        cam.location = (0, 0, -10)
        cam.rotation_euler = (math.pi, 0, 0)
        shoot("under", 960, 560, ortho=4.0)


# --- main -----------------------------------------------------------------------------------------

def main(side_name="left"):
    global NAME
    own_side = LEFT if side_name == "left" else RIGHT
    NAME = "assembly-newshl-153" if side_name == "left" else "assembly-newshl-197"
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sprite = merged_sprite()
    coll = common.reset_collection(NAME)
    static_l = build_static(sprite, f"{NAME}_left", coll)
    flames_l = {f: build_flame(sprite, f, f"{LEFT['muzzle']}-flash-{f}", coll) for f in LEFT["flash"]}
    static_r = mirror_obj(static_l, f"{NAME}_right", coll)
    flames_r = {}
    for fl, fr in zip(LEFT["flash"], RIGHT["flash"]):
        o = mirror_obj(flames_l[fl], f"{RIGHT['muzzle']}-flash-{fr}", coll)
        common.frame_part(o, [fr])
        o.data.shade_smooth()
        flames_r[fr] = o
    report = {"tris_static_left": sum(len(p.vertices) - 2 for p in static_l.data.polygons),
              "tris_flash": {f: sum(len(p.vertices) - 2 for p in o.data.polygons) for f, o in flames_l.items()}}
    mdir = Path(argv[argv.index("--measure") + 1]) if "--measure" in argv else None
    if mdir:
        mdir.mkdir(parents=True, exist_ok=True)
        rep, diffs = measure(static_l, flames_l, static_r, flames_r, mdir)
        report.update(rep)
        (mdir / "diffs.json").write_text(json.dumps(diffs, indent=0))
    # Outline shells from each closed static cannon (every part a closed solid), all outer islands.
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    exported, info = [], {}
    for side, static, flames in ((LEFT, static_l, flames_l), (RIGHT, static_r, flames_r)):
        shell = common.outline_shell(static, coll, voxel=0.02, faces=6000, smooth=6, inside=0.004, islands="outer")
        shell.hide_render = True
        if side is LEFT:
            layout = [(side["mount"], -12), (side["muzzle"], 12)]
        else:
            layout = [(side["muzzle"], -12), (side["mount"], 12)]
        pieces = common.split_assembly(static, [(n, cx, 0) for n, cx in layout], coll)
        shells = split_open(shell, layout, coll)
        # every exported node stays at the origin: split_assembly already centred each piece and
        # placeModel only sets the root's position (a node offset would shift the piece in game)
        for name, cx in layout:
            p, sh = pieces[name], shells[name]
            p.data.set_sharp_from_angle(angle=math.radians(35.0))
            weighted_normals(p)
            sh.data.shade_smooth()
            sh["tyrian_outline"] = True
            sh.data.materials.clear()
            sh.data.materials.append(outline_mat)
            objs = [p] + ([sh] if len(sh.data.polygons) else [])
            if name == side["muzzle"]:
                for f, fo in flames.items():
                    fl = fo.copy()
                    fl.data = fo.data.copy()
                    fl.name = f"{name}-flash-{f}"
                    coll.objects.link(fl)
                    # the flame is built in assembly coordinates: move it into the piece's own
                    fl.data.transform(Matrix.Translation((-cx * PX, 0, 0)))
                    fl.location = (0, 0, 0)
                    objs.append(fl)
            info[name] = {"tris": sum(len(q.vertices) - 2 for q in p.data.polygons),
                          "shell_faces": len(sh.data.polygons)}
            exported += objs
            if side is own_side:
                common.export_sprite_model(WT, objs, f"enemies/{name}", piece_sprite(name)["sprites"])
    report["pieces"] = info
    if mdir:
        # review renders of the left cannon (assembly coordinates): rest and both flash frames
        for o in exported:
            o.hide_render = True
        sets = {"rest": [static_l], "f157": [static_l, flames_l[157]], "f159": [static_l, flames_l[159]]}
        render_views(mdir / "views", coll, sets)
        (mdir / "report.json").write_text(json.dumps(report, indent=1))
    print("REPORT", json.dumps(report)[:4000])


if __name__ == "__main__":
    main()
