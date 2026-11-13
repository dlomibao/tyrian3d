"""Twin cannon pair, design A (newshv.shp 14 + 16, left cannon; its mirror 167 + 169 is the right).

Seen in episode 4: UNDERDELI (4.7) flies a pair on the sky layer at the screen edges; in DREAD-NOT
(4.14) they are the dreadnought's side cannons. Two heavy gun mounts lie back to back along the
screen, muzzles out, joined in the middle by their trunnion couplings. Each half is 48 x 28 px of
two 2x2 pieces: newshv-14 (the barrel and its wing mount) and newshv-16 (the bulkhead, the turntable
half disc and the coupling).

Each cannon, from the sprite (inner mask, D74), muzzle to seam:
- the barrel, one lathe on row edge 10 (5 px radius): a darker muzzle cap with a chamfered lip and
  a deep bore, a bright clamp ring (col 5), the blue band (cols 10-11) with a bright ring behind it
  (col 12), a fine groove, and the long rear barrel into the bulkhead;
- an underslung recoil cylinder (rows 11-18) under the front of the barrel, held by the same clamp
  ring and band (the sprite's ring and band carry on down to row 17);
- a swept wing mount: a small upper gusset (rows 1-5) and a long lower one whose chamfered
  diagonal edge is the sprite's lit diagonal (rows 18-25), both thinning outward;
- a tall bulkhead across the barrel's root (cols 24-28, rows 1-25) with a seam groove (col 26);
- a blue-grey half disc turntable behind it (flat edge at col 29 with a blue rail, round edge to
  col 42) with a raised inner panel;
- the coupling on row edge 10.5: a bright flange, a dark shaft, a polished ball joint, a ring and
  a dark socket whose recessed face meets the other cannon's socket at the seam.
Bright sprite pixels (ring glints, the band's 136/141, the ball's 14/15) are sheen, not bumps; the
dark rows under the barrel are shading. Colours are each region's trimmed sprite median.
Underside: flat closed bottoms.

Library for assembly-newshv-14.py and assembly-newshv-169.py: main(own_pieces, name) builds the whole pair
and exports only its own two pieces (with outline shells). --measure DIR writes report/views to DIR.
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "tools")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import pchip  # noqa: E402

NAME = "assembly-newshv-14"
OWN = ["newshv-14", "newshv-16"]
BUILD_NAME = NAME
ALL = ["newshv-14", "newshv-16", "newshv-167", "newshv-169"]
LAYOUT = {"newshv-14": -36, "newshv-16": -12, "newshv-167": 12, "newshv-169": 36}  # piece centre x, px
OUT_DIR = HERE  # measure outputs (--measure DIR) go here only when asked
PX = 1 / 12


def X(u):
    """Pair column edge (0..96, seam at 48) to px x."""
    return u - 48.0


def Y(r):
    """Row edge (0..28) to px y (sprite up = +y)."""
    return 14.0 - r


# --- mesh helpers (px) --------------------------------------------------------------------------

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
        if dd > 2.5 * d:  # cap sharp mitres
            pt = (ox + (pt[0] - ox) * 2.5 * d / dd, oy + (pt[1] - oy) * 2.5 * d / dd)
        out.append(pt)
    return out


def fillet(poly, radii, seg=4):
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


def slab(M, o, z0, z1, mat, ch=0.0, chb=0.0, top=None, zs=None):
    """A prism over the CCW outline o from z0 to z1, its top edge given a rounded chamfer ch and its
    bottom edge a plain chamfer chb. zs(x, y) scales the height above z0 (a wing that thins out)."""
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
    if zs:
        rings = [[(x, y, z0 + (z - z0) * zs(x, y)) for x, y, z in r] for r in rings]
    vr = M.loft(rings, [mat] * (len(rings) - 1), cap0=True, cap1=False, smooth=False)
    M.face(vr[-1], mat if top is None else top)


def lathe(M, yc, zc, prof, mats, sides=28, smooth=True):
    """Revolve a profile [(u, radius)] about the line y = yc, z = zc along x. mats: one material per
    profile segment. A radius of 0 is an apex (closed end)."""
    rings = []
    for u, r in prof:
        if r <= 1e-6:
            rings.append([(X(u), yc, zc)])
        else:
            rings.append([(X(u), yc + r * math.cos(2 * math.pi * k / sides),
                           zc + r * math.sin(2 * math.pi * k / sides)) for k in range(sides)])
    M.loft(rings, mats, cap0=False, cap1=False, smooth=smooth)


def station_loft(M, stations, mats, smooth=False):
    """Loft along x: stations [(u, [(y, z)])] closed sections; ends capped."""
    rings = [[(X(u), y, z) for y, z in sec] for u, sec in stations]
    M.loft(rings, mats, cap0=True, cap1=True, smooth=smooth)


# --- materials ----------------------------------------------------------------------------------

(BARREL, CAP, RING, BAND, RING2, BORE, DARK, DISC, RAIL, BALL, SOCKET, UPPER) = range(12)


def merged_sprite():
    data = common.load_sprite(WT, "newshv-14")
    for n in ALL[1:]:
        data["colors"].update(common.load_sprite(WT, n)["colors"])
    data["name"] = NAME
    return data


def materials(sprite):
    def pal(i, tag, metallic, roughness, spec=0.5):
        m = common.palette_material(sprite, i, f"nshv14{tag}", metallic=metallic, roughness=roughness)
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Specular IOR Level"].default_value = spec
        return m

    return [
        pal(9, "", 0.6, 0.34, 0.7),          # BARREL (sprite median 9)
        pal(6, "", 0.55, 0.42),              # CAP muzzle cap, recoil cylinder, shaft (median 6)
        pal(10, "", 0.7, 0.24, 0.85),        # RING front clamp ring (median 10)
        pal(56, "", 0.55, 0.3, 0.7),         # BAND blue band (median 56)
        pal(11, "", 0.7, 0.26, 0.85),        # RING2 rear ring, coupling flange, socket ring (median 11)
        pal(2, "", 0.3, 0.7, 0.3),           # BORE muzzle bore, socket recess
        pal(4, "", 0.5, 0.48),               # DARK wing mount and bulkhead (median 4; upper gusset 3)
        pal(103, "", 0.35, 0.45),            # DISC turntable (median 103)
        pal(58, "", 0.5, 0.32, 0.7),         # RAIL blue edge rail of the disc (median 58)
        pal(9, "_ball", 0.75, 0.18, 1.0),    # BALL polished ball joint (median 9; 14/15 are sheen)
        pal(4, "_sock", 0.6, 0.36, 0.7),     # SOCKET coupling socket (median 4)
        pal(3, "", 0.5, 0.5),               # UPPER upper gusset (median 3)
    ]


# --- the left cannon (u 0..48); the right is its mirror about the seam --------------------------

ZA = 6.0        # barrel axis height (px)
RB = 10.0       # barrel axis row edge
RC = 10.5       # coupling axis row edge


def barrel(M):
    yc = Y(RB)
    prof = [(3.2, 0.0), (3.2, 2.2), (1.05, 2.2), (1.05, 3.2), (1.45, 4.0), (4.6, 4.0),   # bore, lip, cap
            (4.75, 4.6), (4.95, 5.4), (6.0, 5.4), (6.2, 5.0),                          # ring
            (9.85, 5.0), (10.0, 5.3), (11.9, 5.3),                                      # band
            (12.0, 5.3), (13.0, 5.3), (13.2, 5.0),                                    # ring 2
            (18.0, 5.0), (18.15, 4.75), (18.55, 4.75), (18.7, 5.0),                     # groove
            (22.3, 5.0), (22.45, 4.8), (22.75, 4.8), (22.9, 5.0),                       # groove
            (26.0, 5.0), (26.0, 0.0)]
    mats = [BORE, BORE, CAP, CAP, CAP,
            RING, RING, RING, RING,
            BARREL, BAND, BAND,
            RING2, RING2, RING2,
            BARREL, BARREL, BARREL, BARREL,
            BARREL, BARREL, BARREL, BARREL,
            BARREL, BARREL]
    lathe(M, yc, ZA, prof, mats, sides=32)
    # Underslung recoil cylinder, under the barrel's front, held by the ring and the band.
    ty, tz, tr = Y(14.6), 3.5, 3.35
    prof = [(5.0, 0.0), (5.0, 1.4), (5.3, 1.4), (5.3, 2.1), (4.95, 2.6), (4.95, tr + 0.4), (6.0, tr + 0.4),
            (6.2, tr), (9.85, tr), (10.0, tr + 0.35), (11.9, tr + 0.35), (12.05, tr), (16.0, tr),
            (16.0, 0.0)]
    mats = [BORE, BORE, CAP, CAP, RING, RING, RING, CAP, BAND, BAND, BAND, CAP, CAP]
    lathe(M, ty, tz, prof, mats, sides=24)


def wings(M):
    # Upper gusset (rows 1-5), thinning out toward its top edge.
    o = ur([(14.0, 9.0), (16.3, 5.2), (17.4, 4.6), (22.6, 1.4), (23.6, 0.95), (24.8, 0.95), (24.8, 9.0)])
    yb = Y(RB)
    slab(M, o, 2.0, 8.0, UPPER, ch=0.7, zs=lambda x, y: max(0.42, 1.0 - max(0.0, (y - yb - 4.5)) / 9.0))
    # Lower gusset (rows 13-26): the long swept wing, its diagonal edge chamfered.
    o = ur([(13.4, 12.0), (14.5, 17.9), (15.4, 18.9), (22.5, 25.1), (24.0, 26.0), (24.8, 26.0),
            (24.8, 12.0)])
    slab(M, o, 0.6, 7.0, DARK, ch=1.1, zs=lambda x, y: max(0.38, 1.0 - max(0.0, (yb - y - 4.0)) / 12.0))
    # Stiffener rib along the lower wing (parallel to its diagonal edge), a raised strip.
    o = ur([(17.0, 17.4), (17.9, 16.7), (24.8, 22.8), (24.8, 24.2)])
    slab(M, o, 2.0, 5.2, DARK, ch=0.5)


def bulkhead(M):
    """The tall plate across the barrel's root (cols 24-28, rows 1-25), seam groove at col 26."""
    rows = [1.0, 2.5, 4.5, 7.0, 10.0, 13.0, 16.0, 19.5, 23.0, 26.0]
    zt = [6.0, 9.0, 11.6, 13.2, 13.8, 13.2, 11.6, 9.4, 7.0, 4.8]
    f = pchip(rows, zt)
    top = [(Y(r), f(r)) for r in [1.0 + 25.0 * k / 24 for k in range(25)]]
    sec = [(Y(26.0), 0.0), (Y(1.0), 0.0)] + [(Y(1.0), 4.0)] + top[1:-1] + [(Y(26.0), 3.6)]
    sec = ccw(sec)
    st = [(24.0, inset(sec, 0.7)), (24.6, sec), (25.9, sec), (26.15, inset(sec, 0.45)),
          (26.75, inset(sec, 0.45)), (27.0, sec), (28.4, sec), (29.0, inset(sec, 0.7))]
    # keep the bottom on z = 0 (the inset lifts it)
    st = [(u, [(y, 0.0 if z < 0.8 else z) for y, z in s]) for u, s in st]
    station_loft(M, st, DARK)
    # Bolt heads along the top, either side of the seam groove.
    for r in (4.5, 8.0, 13.0, 18.0, 22.0):
        z = f(r)
        for u in (25.2, 27.8):
            lathe_bolt(M, X(u), Y(r), z - 0.25)


def lathe_bolt(M, x, y, z, r=0.45, h=0.45):
    sides = 8
    rings = [[(x + r * math.cos(2 * math.pi * k / sides), y + r * math.sin(2 * math.pi * k / sides), zz)
              for k in range(sides)] for zz in (z, z + h)]
    rings.append([(x, y, z + h + 0.12)])
    M.loft(rings, DARK, cap0=True, cap1=False, smooth=False)


def disc(M):
    """Half-disc turntable (flat edge at col 29, round to col 42) with a raised inner panel."""
    # right edge per row edge, traced from the inner mask (flat top at row 1, round toward the seam)
    rr = [1.0, 1.5, 2.5, 3.5, 4.5, 7.0, 10.0, 13.5, 17.0, 20.5, 22.0, 23.0, 24.0, 25.0, 25.6, 26.0]
    uu = [35.5, 37.0, 38.8, 39.4, 40.3, 41.7, 42.3, 42.4, 42.4, 42.2, 41.5, 40.5, 39.3, 37.6, 36.2, 34.5]
    f = pchip(rr, uu)
    pts = [(29.6, 1.0)] + [(f(r), r) for r in [1.0 + 25.0 * k / 50 for k in range(51)]] + [(29.6, 26.0)]
    o = ur(pts)
    slab(M, o, 0.0, 3.0, DISC, ch=0.9, chb=0.3)
    o2 = inset(o, 2.2)
    slab(M, o2, 2.5, 3.6, DISC, ch=0.5)
    # Blue rail along the flat edge (col 29).
    o = ur(fillet_rect(28.9, 0.95, 30.5, 26.05, 0.5))
    slab(M, o, 0.0, 4.4, RAIL, ch=0.5)


def fillet_rect(u0, r0, u1, r1, rad):
    return fillet([(u0, r0), (u1, r0), (u1, r1), (u0, r1)], rad, seg=2)


def coupling(M):
    yc = Y(10.4)
    prof = [(26.5, 0.0), (26.5, 3.4), (27.3, 4.1), (30.4, 4.1), (31.0, 3.3),           # flange
            (31.0, 2.9), (35.0, 2.9)]                                                # shaft
    mats = [RING2, RING2, RING2, RING2, CAP, CAP]
    bc, ba, bb = 37.0, 2.4, 4.7                                                      # ball joint
    for k in range(1, 12):
        t = -math.pi / 2 + math.pi * k / 12
        prof.append((bc + ba * math.sin(t), bb * math.cos(t)))
        mats.append(BALL)
    prof += [(39.4, 0.0)]
    mats.append(BALL)
    lathe(M, yc, ZA, prof, mats, sides=28)
    # ring and socket, a little lower on the screen (the sprite's socket is rows 6-16)
    yc = Y(10.9)
    prof = [(38.6, 0.0), (38.6, 3.8), (39.0, 4.7), (40.3, 4.7), (40.4, 4.4),             # ring
            (40.5, 5.0), (45.6, 5.0), (46.6, 4.3), (46.9, 3.5),                          # socket
            (46.9, 2.4), (45.4, 2.4), (45.4, 0.0)]                                        # recess
    mats = [RING2, RING2, RING2, RING2, SOCKET, SOCKET, SOCKET, SOCKET, BORE, BORE, BORE]
    lathe(M, yc, ZA, prof, mats, sides=28)
    for u in (42.4, 44.2):  # band grooves
        lathe(M, yc, ZA, [(u, 0.0), (u, 5.1), (u + 0.5, 5.1), (u + 0.5, 0.0)], SOCKET, sides=28)


def build(sprite, coll):
    mats = materials(sprite)
    halves = []
    for side in (-1, 1):
        M = Mesh()
        barrel(M)
        wings(M)
        bulkhead(M)
        disc(M)
        coupling(M)
        if side > 0:
            for v in M.bm.verts:
                v.co.x = -v.co.x
            bmesh.ops.reverse_faces(M.bm, faces=M.bm.faces)
        halves.append(M)
    bm = bmesh.new()
    for M in halves:
        me = bpy.data.meshes.new("tmp")
        M.bm.to_mesh(me)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        M.bm.free()
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.scale(bm, vec=(PX, PX, PX), verts=bm.verts)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(35.0))
    return obj


def split_open(obj, layout, coll):
    """Cut the outline shell into the pieces without filling the cuts (no ink along the seams)."""
    out = {}
    for name, cx, cy in layout:
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
        o = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(o)
        out[name] = o
    return out


# --- measuring (left half, 48 x 28) -------------------------------------------------------------

def raycast_grid(obj, k, w=48, h=28):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    mats = [m.name for m in obj.data.materials]
    top = []
    for yy in range(h * k):
        s = (yy + 0.5) / k
        row = []
        for xx in range(w * k):
            e = (xx + 0.5) / k
            hit, *_ = ev.ray_cast(Vector((X(e) * PX, Y(s) * PX, 5.0)), Vector((0, 0, -1)))
            row.append(bool(hit))
        top.append(row)
    pal = [[None] * w for _ in range(h)]
    hgt = [[0.0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            hit, loc, nrm, fi = ev.ray_cast(Vector((X(c + 0.5) * PX, Y(r + 0.5) * PX, 5.0)), Vector((0, 0, -1)))
            if hit:
                pal[r][c] = int(mats[obj.data.polygons[fi].material_index].split("_")[1])
                hgt[r][c] = loc.z
    return top, pal, hgt


def measure(obj):
    import collections
    import sprite_mask as SM
    k = 6
    top, pal, hgt = raycast_grid(obj, k)
    idx, cols = SM.load(NAME)
    MS = SM.masks(idx, cols)
    out = {"whole": SM.measure(MS, top)}
    for i, n in enumerate(OWN):
        pidx, pcol = SM.load(n)
        sub = [row[i * 24 * k:(i + 1) * 24 * k] for row in top]
        out[n] = SM.measure(SM.masks(pidx, pcol), sub)
    # the right half, mirrored, against its own sprite (it should equal the left)
    g = [[sum(top[r * k + j][c * k + i] for j in range(k) for i in range(k)) / (k * k) >= 0.5
          for c in range(48)] for r in range(28)]
    diff = []
    for r in range(28):
        line = ""
        for c in range(48):
            s, m, fr = MS["inner"][r][c], g[r][c], MS["free"][r][c]
            line += ("#" if s and m else "-" if s else "+" if m and not fr else "f" if fr and m else
                     "o" if MS["outer"][r][c] else ".")
        diff.append(line)
    out["diff"] = diff
    reg = json.loads((OUT_DIR / "regions.json").read_text())
    col = {}
    for n, boxes in reg["regions"].items():
        cnt = collections.Counter(pal[r][c] for c0, c1, r0, r1 in boxes for r in range(r0, r1 + 1)
                                  for c in range(c0, c1 + 1) if pal[r][c] is not None)
        col[n] = {"sprite": reg["median"][n], "model": cnt.most_common(2)}
    out["colour"] = col
    out["max_height"] = max(max(r) for r in hgt)
    return out, pal, hgt


# --- review renders -----------------------------------------------------------------------------

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


def render_views(out):
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

    c = Vector((0, 0, 0.4))
    cam.location = (0, 0, 10)
    cam.rotation_euler = (0, 0, 0)
    shoot("top", 960, 300, ortho=8.4)
    look((0, -12, 0.5), (0, 0, 0.5))
    shoot("side", 960, 240, ortho=8.4)          # from the screen bottom
    look((0, 12, 0.5), (0, 0, 0.5))
    shoot("side_far", 960, 240, ortho=8.4)
    look((-12, 0, 0.55), (0, 0, 0.55))
    shoot("front", 480, 300, ortho=3.2)          # down the left muzzle
    look((-1.0, -6.0, 4.5), (-2.0, 0, 0.4))
    shoot("q_front", 760, 480, lens=45)
    look((2.5, 6.0, 4.0), (-2.0, 0, 0.4))
    shoot("q_rear", 760, 480, lens=45)
    a = math.radians(15)
    look((0, -26 * math.sin(a), 26 * math.cos(a)), c)
    shoot("game", 960, 400, lens=95)
    look((-6.5, -4.5, 1.2), (-2, 0, 0.4))
    shoot("low", 760, 420, lens=45)
    look((0.0, -3.2, 2.2), (0, 0, 0.45))
    shoot("seam", 760, 420, lens=45)
    cam.location = (0, 0, -10)
    cam.rotation_euler = (math.pi, 0, 0)
    shoot("under", 960, 300, ortho=8.4)


# --- main ---------------------------------------------------------------------------------------

def main(own=None, name=None):
    global OWN, NAME, OUT_DIR
    OWN = own or OWN
    NAME = name or NAME
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sprite = merged_sprite()
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    report = {"whole_tris": sum(len(p.vertices) - 2 for p in obj.data.polygons)}
    if "--measure" in argv:
        OUT_DIR = Path(argv[argv.index("--measure") + 1])
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        m, pal, hgt = measure(obj)
        report.update(m)
        (OUT_DIR / "pal.json").write_text(json.dumps({"pal": pal, "hgt": hgt}))
    # Outline shell from the closed whole pair (every part is a closed solid), all outer islands.
    shell = common.outline_shell(obj, coll, voxel=0.02, faces=8000, smooth=6, inside=0.004, islands="outer")
    shell.hide_render = True
    bake = "--bake" in argv
    if bake:
        T.TINT = (1.0, 1.0, 1.0)
        T.TEXTURED = tuple(range(len(obj.data.materials)))
        T.bake_maps(obj, tempfile.mkdtemp(prefix="nshv14A_bake_"), size=1024, samples=64)
    layout = [(n, LAYOUT[n], 0) for n in ALL]
    pieces = common.split_assembly(obj, layout, coll)
    shells = split_open(shell, layout, coll)
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    fmt = "WEBP" if bake else "AUTO"
    info, shown = {}, []
    for name, cx, cy in layout:
        p, sh = pieces[name], shells[name]
        p.data.set_sharp_from_angle(angle=math.radians(35.0))
        sh.data.shade_smooth()
        sh["tyrian_outline"] = True
        sh.data.materials.clear()
        sh.data.materials.append(outline_mat)
        objs = [p] + ([sh] if len(sh.data.polygons) else [])
        info[name] = {"tris": sum(len(q.vertices) - 2 for q in p.data.polygons),
                      "shell_faces": len(sh.data.polygons)}
        if name in OWN:
            common.export_sprite_model(WT, objs, f"enemies/{name}", common.load_sprite(WT, name)["sprites"],
                                       image_format=fmt)
    report["pieces"] = info
    report["own_tris"] = sum(info[n]["tris"] for n in OWN)
    if "--measure" in argv:
        for o in list(coll.objects):
            o.hide_render = o is not obj
        render_views(OUT_DIR / "views")
    if "--measure" in argv:
        (OUT_DIR / "report.json").write_text(json.dumps(report, indent=1))
    print("REPORT", json.dumps({k: v for k, v in report.items() if k != "diff"})[:3000])
    if "diff" in report:
        print("\n".join(report["diff"]))


