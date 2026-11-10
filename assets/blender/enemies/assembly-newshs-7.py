"""Blue glossy pipe with an eye (newshs.shp; assembly-newshs-7: newshs-1, -7, -115, -3), final (design A, judged winner; cage colours from design B):
engineering first, cross-sections first, on the blueprint's geometry
(tyrian-scratch/e1-enemies/assembly-newshs-7/blueprint/blueprint.json). D50-D53, D65 style, top
view on the sprite's inner edge (D74).

The object: one 120 x 18 px round pipe lying across the screen, five 24 px sections bolted together
at four flanged joints (c 24, 48, 72, 96). Every section cut is the same flange, so the pieces tile
in any order (assemblies.json has a second pipe with the eye second from the left).

Cross-sections (sprite px; c = assembly column edge, r = row edge, z up; axis at row 15, z 7.5):
- Barrel: a lathe of the blueprint profile, 32 sides, r 8.7; flange collars r 9.0 c J-4.1..J+4.1
  with 0.3 chamfers and a 0.7 px V seam (r 8.5) at the piece cut; bolted half flanges (hex heads at
  c J -/+ 2.4, six round the visible arc, none on the crest). Bedded 1.2 px: the chord under it is
  flat (a closed underside, no detail).
- Ends (newshs-1 / newshs-3): pchip taper 7.05 -> 8.7 over 10 px (the sprite's inner mask rows 6-8
  and 21-23), a rolled rim, a recessed end plate with eight bolts and a centre hub.
- Cradle chocks: wedges under every joint on both flanks, inside the plan.
- The eye section (newshs-115, c 72-96): a gimbal housing r 9.0 between two collar grooves. Two
  trunnion bosses on the flanks (sprite rows 6 and 23, c 82-86: the lit knobs) carry the gimbal
  cage: an outer pair of straps (traced row by row from the sprite: 10.2 px from the eye's centre
  line at the crest: the sprite's bright 55-57 ridge, '(' and ')'), running into yoke lugs along the
  flank (row 6 c 77-80), and an inner pair (5.5 px at the crest) that run into the bosses. A red light bar (rows 14-15, the whole section)
  rides on top of the crest over the straps; two bezel rails (rows 13 and 16) flank it between the
  inner straps. North and south of the bar two sockets carry the eye's bulbs: their plan outlines
  are traced from the sprite's red pixels per state; bulbs rise straight up (vertical pistons), so
  the top view keeps the traced footprint.
- Eye states (three models, D17 palette frames inside each):
  newshs-115 (115, 117): flush iris shutters, pipe blue (51), the centre turns dark red (65) on 117;
  newshs-115-f2 (119, 121): bulbs half out, 66 -> 68 on 121; newshs-115-f3 (123): bulbs out, 69.
- Colours: each part the sprite's own palette index (blueprint palette_regions_sprite): barrel 51,
  collars 51 (50 on the eye piece's end bands), end taper 52, both strap pairs and bezels 56,
  trunnions 59 (pins 61), yoke/hub 53, bolts 54, bar 71 (glowing), socket rims 52. Satin metal; sheen stays sheen (the crest glints and the lit
  upper rim of the sprite are lighting, not geometry).

  tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshs-7.py

Exports public/models/enemies/{newshs-1,newshs-7,newshs-115,newshs-115-f2,newshs-115-f3,newshs-3}.glb
and their src/render/spriteModels entries (the contract of the script it replaces). The eye's
bulbs are frame parts: 119 and 121 have their own bulb outlines (traced from the sprite's red
pixels), so each frame matches the sprite.
"""

import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

WT = Path("/Users/dlomibao/projects/tyrian-worktrees/e1-enemies")
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import pchip  # noqa: E402

NAME = "assembly-newshs-7"
ROOT = WT
PX = 1 / 12
AXR, AXZ = 15.0, 7.5  # pipe axis: row edge 15, z 7.5 px
RB, RC, RH = 8.7, 9.0, 9.0  # barrel, collar, eye housing radii
EYE = 84.0
JOINTS = (24.0, 48.0, 72.0, 96.0)
NSIDE = 32
CX0, CY0 = 176, 157  # screen centre of the assembly frame (assembly column c = screen x - 116)
LAYOUT = [("newshs-1", 128, 157), ("newshs-7", 152, 157), ("newshs-7", 176, 157), ("newshs-115", 200, 157),
          ("newshs-3", 224, 157)]
PIECES = ["newshs-1", "newshs-7", "newshs-115", "newshs-3"]
VARIANTS = [("newshs-115", [115, 117]), ("newshs-115-f2", [119, 121]), ("newshs-115-f3", [123])]

# --- materials: (palette index, metallic, roughness, emission strength) -------------------------
REGIONS = {
    "pipe": (51, 0.42, 0.30, 0.0), "collar": (51, 0.42, 0.34, 0.0), "endcap": (52, 0.42, 0.32, 0.0),
    "hub": (53, 0.5, 0.30, 0.0), "bolt": (54, 0.55, 0.30, 0.0), "chock": (50, 0.30, 0.50, 0.0),
    "hoop": (56, 0.50, 0.30, 0.0), "bezel": (56, 0.50, 0.28, 0.0), "hoopo": (56, 0.50, 0.30, 0.0),
    "eyecollar": (50, 0.42, 0.34, 0.0),
    "bezel_s": (53, 0.50, 0.28, 0.0), "trunnion": (59, 0.55, 0.28, 0.0),
    "pin": (61, 0.60, 0.25, 0.0), "yoke": (53, 0.50, 0.32, 0.0), "rim": (52, 0.40, 0.40, 0.0),
    "bar": (71, 0.10, 0.25, 1.6),
}
RNAMES = list(REGIONS)
R = {k: i for i, k in enumerate(RNAMES)}
UNTEXTURED = ("bar",)
# eye-state parts (their own objects, untextured): (index, metallic, roughness, emission, frames)
LENS_MATS = {
    "shutter": (51, 0.45, 0.32, 0.0, None),
    "iris": (51, 0.30, 0.35, 0.0, {117: 65}),
    "bulb1": (66, 0.15, 0.20, 1.2, {121: 68}),
    "bulb2": (69, 0.15, 0.18, 1.8, None),
}

# --- the barrel profile (c, radius), blueprint PROFILE with the eye section made a housing ---------
PROFILE = [
    (0.1, 0), (0.1, 1.5), (0.25, 1.9), (0.6, 2), (0.6, 5.4), (0.3, 5.8), (0, 6.3), (0, 6.75), (0.25, 7.05),
    (1.5, 7.27), (2.75, 7.47), (4.1, 7.8), (5.5, 8.1), (6.8, 8.33), (8, 8.5), (9, 8.62), (10, 8.7),
    (19.6, 8.7), (19.9, 9), (23.35, 9), (23.65, 8.72), (23.65, 8.5), (24, 8.5), (24.35, 8.5), (24.35, 8.72),
    (24.65, 9), (28.1, 9), (28.4, 8.7), (36.0, 8.7),
    (43.6, 8.7), (43.9, 9), (47.35, 9), (47.65, 8.72), (47.65, 8.5), (48, 8.5), (48.35, 8.5), (48.35, 8.72),
    (48.65, 9), (52.1, 9), (52.4, 8.7), (60.0, 8.7),
    (67.6, 8.7), (67.9, 9), (71.35, 9), (71.65, 8.72), (71.65, 8.5), (72, 8.5), (72.35, 8.5), (72.35, 8.72),
    (72.65, 9),
    # gimbal housing r 9.0 with a groove where each collar ends (instead of the barrel's 8.7 waist)
    (75.9, 9), (76.05, 8.8), (76.35, 8.8), (76.5, 9), (84.0, 9), (91.5, 9), (91.65, 8.8), (91.95, 8.8), (92.1, 9),
    (95.35, 9), (95.65, 8.72), (95.65, 8.5), (96, 8.5), (96.35, 8.5),
    (96.35, 8.72), (96.65, 9), (100.1, 9), (100.4, 8.7), (110, 8.7), (111, 8.62), (112, 8.5), (113.2, 8.33),
    (114.5, 8.1), (115.9, 7.8), (117.25, 7.47), (118.5, 7.27), (119.75, 7.05), (120, 6.75), (120, 6.3),
    (119.7, 5.8), (119.4, 5.4), (119.4, 2), (119.75, 1.9), (119.9, 1.5), (119.9, 0),
]

# --- the gimbal straps, traced from the sprite (half width from the eye line c 84 vs row offset
# from the axis; symmetric; blueprint hoop_traces, smoothed) ----------------------------------------
# outer: the sprite's bright 55-57 ridge centres, row by row (c 4-5 at rows 6-8, c 1-2 at rows 12-17)
OUTER_DX = ([0.0, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5], [10.2, 10.1, 9.95, 9.5, 9.0, 8.5, 8.0, 7.3, 6.6])
INNER_DX = ([0.0, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5], [5.5, 5.5, 5.3, 4.65, 3.85, 3.1, 2.5, 2.1])
STRAP_Y = 8.5  # row offset of the yoke lugs / trunnion axis (rows 6.5 and 23.5)

# --- bulb footprints: the sprite's red pixels per row (row, half width about c 84), symmetrised ----
FOOT = {
    "s117": {"N": [(8, 1), (9, 2), (10, 2), (11, 1)], "S": [(17, 3), (18, 4), (19, 3), (20, 2)]},
    "s119": {"N": [(8, 1), (9, 2), (10, 3), (11, 3)],
             "S": [(17, 5), (18, 4), (19, 4), (20, 3), (21, 2)]},
    "s121": {"N": [(8, 1), (9, 2), (10, 3), (11, 3), (12, 2.5)],
             "S": [(17, 5), (18, 4), (19, 4), (20, 3), (21, 2)]},
    "s2": {"N": [(7, 1), (8, 2), (9, 3), (10, 3), (11, 3), (12, 2.5)],
           "S": [(17, 4.8), (18, 4.6), (19, 4.1), (20, 3.3), (21, 2.2)]},
}
KRING = 24


# --- mesh builder (sprite px; closed solids; normals recalculated at the end) ---------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, vs, mat):
        if len({id(v) for v in vs}) < 3:
            return None
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        return face

    def rings(self, rings, mat, cap0=True, cap1=True, closed=True, seg_mats=None):
        """Loft through rings of points (same count; a 1-point ring is an apex). closed: each ring is
        a loop."""
        vr = [[self.v(p) for p in r] for r in rings]
        for k in range(len(vr) - 1):
            a, b = vr[k], vr[k + 1]
            m = seg_mats[k] if seg_mats else mat
            n = max(len(a), len(b))
            last = n if closed else n - 1
            for i in range(last):
                j = (i + 1) % n
                if len(a) == 1:
                    self.f([a[0], b[i], b[j]], m)
                elif len(b) == 1:
                    self.f([a[i], a[j], b[0]], m)
                else:
                    self.f([a[i], a[j], b[j], b[i]], m)
        if cap0 and len(vr[0]) > 2:
            self.f(list(reversed(vr[0])), mat)
        if cap1 and len(vr[-1]) > 2:
            self.f(vr[-1], mat)

    def hull(self, pts, mat):
        tmp = bmesh.new()
        vs = [tmp.verts.new(p) for p in pts]
        res = bmesh.ops.convex_hull(tmp, input=vs, use_existing_faces=False)
        junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
        if junk:
            bmesh.ops.delete(tmp, geom=junk, context="VERTS")
        bmesh.ops.remove_doubles(tmp, verts=tmp.verts, dist=1e-6)
        bmesh.ops.dissolve_limit(tmp, angle_limit=math.radians(1.0), verts=tmp.verts[:], edges=tmp.edges[:])
        vm = {v: self.v(v.co.copy()) for v in tmp.verts}
        for fc in tmp.faces:
            self.f([vm[v] for v in fc.verts], mat)
        tmp.free()


def P(c, yp, z):
    """A point at column c, row offset yp from the axis, height z (sprite px)."""
    return (c, AXR + yp, z)


def polar(c, rad, phi):
    """Point on a circle round the axis: phi 0 = top, + toward the south (+row)."""
    return (c, AXR + rad * math.sin(phi), max(0.0, AXZ + rad * math.cos(phi)))


def surf_z(yp, rad=RH):
    yp = max(-rad + 1e-3, min(rad - 1e-3, yp))
    return AXZ + math.sqrt(rad * rad - yp * yp)


def surf_n(yp, rad=RH):
    yp = max(-rad + 1e-3, min(rad - 1e-3, yp))
    return Vector((0.0, yp / rad, math.sqrt(rad * rad - yp * yp) / rad))


# --- barrel ------------------------------------------------------------------------------------------

def seg_region(c0, r0, c1, r1):
    c, r = (c0 + c1) / 2, (r0 + r1) / 2
    if c < 0.7 or c > 119.3:
        if r < 1.95:
            return "hub"
        return "pipe" if r < 5.85 else "endcap"
    if c < 10 or c > 110:
        return "endcap"
    for J in JOINTS:
        if abs(c - J) <= 4.15:
            # the eye piece's end bands (its c 0-3 / 20-23) are 49-51 in the sprite: 50
            if (J == 72.0 and c > J) or (J == 96.0 and c < J):
                return "eyecollar"
            return "collar"
    return "pipe"


def build_barrel(M):
    rings, mats = [], []
    for c, r in PROFILE:
        if r < 1e-6:
            rings.append([(c, AXR, AXZ)])
        else:
            rings.append([polar(c, r, 2 * math.pi * k / NSIDE) for k in range(NSIDE)])
    for (c0, r0), (c1, r1) in zip(PROFILE, PROFILE[1:]):
        mats.append(R[seg_region(c0, r0, c1, r1)])
    M.rings(rings, 0, cap0=False, cap1=False, seg_mats=mats)


def hex_bolt(M, centre, normal, rad, h, mat, sink=0.12):
    n = Vector(normal).normalized()
    a = n.orthogonal().normalized()
    b = n.cross(a)
    c = Vector(centre)
    def ring(off, rr):
        return [tuple(c + n * off + (a * math.cos(math.pi / 3 * k + 0.3) + b * math.sin(math.pi / 3 * k + 0.3)) * rr)
                for k in range(6)]
    M.rings([ring(-sink, rad), ring(h - 0.07, rad), ring(h, rad - 0.09)], mat)


def build_bolts(M):
    for J in JOINTS:
        for dc in (-2.4, 2.4):
            for deg in (-112, -80, -50, 50, 80, 112):
                phi = math.radians(deg)
                n = (0.0, math.sin(phi), math.cos(phi))
                hex_bolt(M, polar(J + dc, RC, phi), n, 0.42, 0.26, R["bolt"])
    for cf, dirx in ((0.6, -1.0), (119.4, 1.0)):
        for k in range(8):
            phi = math.radians(22.5 + 45 * k)
            hex_bolt(M, (cf, AXR + 4.2 * math.sin(phi), AXZ + 4.2 * math.cos(phi)), (dirx, 0, 0), 0.45, 0.28,
                     R["bolt"])


def build_chocks(M):
    prof = [(4.4, 0.0), (8.85, 0.0), (8.85, 0.9), (8.55, 3.0), (7.6, 4.5), (4.4, 4.5)]
    for J in JOINTS:
        for s in (-1, 1):
            pts = []
            for yp, z in prof:
                outer = yp > 8.0
                for x in (J - 1.5, J + 1.5):
                    if outer:
                        xi = x + (0.3 if x < J else -0.3)
                        pts.append(P(xi, s * yp, z))
                        pts.append(P(x, s * (yp - 0.3), z))
                    else:
                        pts.append(P(x, s * yp, z))
            M.hull(pts, R["chock"])


# --- the gimbal eye section -------------------------------------------------------------------------

def chaikin(pts, n=2, closed=False):
    for _ in range(n):
        out = [pts[0]] if not closed else []
        m = len(pts)
        rng = range(m) if closed else range(m - 1)
        for i in rng:
            p, q = pts[i], pts[(i + 1) % m]
            out.append(tuple(0.75 * a + 0.25 * b for a, b in zip(p, q)))
            out.append(tuple(0.25 * a + 0.75 * b for a, b in zip(p, q)))
        if not closed:
            out.append(pts[-1])
        pts = out
    return pts


def resample(pts, step):
    out = [pts[0]]
    acc = 0.0
    for p, q in zip(pts, pts[1:]):
        d = math.dist(p, q)
        acc += d
        if acc >= step:
            out.append(q)
            acc = 0.0
    if out[-1] != pts[-1]:
        out[-1] = pts[-1]
    return out


def sweep_band(M, plan, w, t, mat, sink=0.14, ch=0.12, rad=RH):
    """A flat strap draped on the housing along plan points (c, yp): width w across the path, t
    proud of the surface, chamfered top edges, closed ends."""
    pts = [Vector((c, AXR + yp, surf_z(yp, rad))) for c, yp in plan]
    nrm = [surf_n(yp, rad) for c, yp in plan]
    prof = [(-w / 2, -sink), (w / 2, -sink), (w / 2, t - ch), (w / 2 - ch, t), (-w / 2 + ch, t), (-w / 2, t - ch)]
    rings = []
    for i, p in enumerate(pts):
        tan = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        n = nrm[i]
        b = tan.cross(n).normalized()
        n = b.cross(tan).normalized()
        rings.append([tuple(p + b * u + n * v) for u, v in prof])
    M.rings(rings, mat)


def strap_paths():
    fo = pchip(*OUTER_DX)
    fi = pchip(*INNER_DX)
    out = []
    ys = [-STRAP_Y + 0.5 * k for k in range(int(2 * STRAP_Y / 0.5) + 1)]
    # outer: yoke lug along the flank from the boss, over the top, back to the other boss
    o = [(1.3 + 0.5 * k, -STRAP_Y) for k in range(int((fo(STRAP_Y) - 1.3) / 0.5))]
    o += [(fo(abs(y)), y) for y in ys]
    o += [(x, -y) for x, y in reversed(o[:len(o) - len(ys)])]
    o = chaikin(o, 4)
    i = [(1.2, -STRAP_Y - 0.05), (1.7, -STRAP_Y)] + [(fi(abs(y)), y) for y in ys] + [(1.7, STRAP_Y), (1.2, STRAP_Y + 0.05)]
    i = chaikin(i, 2)
    for s in (-1, 1):
        out.append([(EYE + s * dx, y) for dx, y in resample(o, 0.35)])
        out.append([(EYE + s * dx, y) for dx, y in resample(i, 0.35)])
    return out


def loft_x(M, secf, xs, mat):
    """Loft along the pipe through sections secf(x) -> [(yp, z)] (closed loops)."""
    M.rings([[P(x, yp, z) for yp, z in secf(x)] for x in xs], mat)


def arc_sec(r0, r1, th0, th1, n=6, ch=0.06):
    """A strip section on the housing between angles th0..th1 (rad, + south), from radius r0 to r1
    with chamfered top corners."""
    sec = []
    for k in range(n + 1):
        th = th0 + (th1 - th0) * k / n
        sec.append((r0 * math.sin(th), AXZ + r0 * math.cos(th)))
    a0, a1 = th0 + ch / r1, th1 - ch / r1
    sec.append(((r1 - ch) * math.sin(th1), AXZ + (r1 - ch) * math.cos(th1)))
    for k in range(n + 1):
        th = a1 + (a0 - a1) * k / n
        sec.append((r1 * math.sin(th), AXZ + r1 * math.cos(th)))
    sec.append(((r1 - ch) * math.sin(th0), AXZ + (r1 - ch) * math.cos(th0)))
    return sec


def build_eye(M):
    # gimbal straps
    for k, plan in enumerate(strap_paths()):
        # outer hoops: a raised 56 ridge, '(' and ')' round the inner bezel ring
        sweep_band(M, plan, 1.4 if k % 2 == 0 else 1.05, 0.55 if k % 2 == 0 else 0.46,
                   R["hoopo"] if k % 2 == 0 else R["hoop"])
    # trunnion bosses (axis N-S, at the yoke lugs' height) and their pins
    zt = surf_z(STRAP_Y)
    for s in (-1, 1):
        def disc(yp, rr, nn=16):
            return [(EYE + rr * math.cos(2 * math.pi * k / nn), AXR + s * yp, zt + rr * math.sin(2 * math.pi * k / nn))
                    for k in range(nn)]
        M.rings([disc(7.2, 1.65), disc(8.8, 1.65), disc(9.05, 1.4)], R["trunnion"])
        M.rings([disc(8.9, 0.62, 10), disc(9.18, 0.62, 10), disc(9.3, 0.5, 10)], R["pin"])
        # yoke lug pads where the outer straps leave the flank (rows 6 / 23, c 77-80 and 88-91)
    # the red light bar over the crest, riding over the straps (rows 14-15, c 72.3-95.7)
    thb = math.asin(1.0 / RH)
    def bar(x):
        e = min(x - 72.3, 95.7 - x)
        if e < 0.1:
            return arc_sec(RH - 0.2, RH + 0.2, -thb + 0.05, thb - 0.05, 6, 0.08)
        if e < 1.0:
            return arc_sec(RH - 0.2, RH + 0.5, -thb + 0.02, thb - 0.02, 6, 0.1)
        return arc_sec(RH - 0.2, RH + 0.62, -thb, thb, 6, 0.12)
    loft_x(M, bar, [72.3, 72.6, 73.4, 94.6, 95.4, 95.7], R["bar"])
    # bezel rails rows 13 and 16 between the inner straps
    for s in (-1, 1):
        a0, a1 = math.asin(1.0 / RH), math.asin(2.0 / RH)
        th0, th1 = (a0, a1) if s > 0 else (-a1, -a0)
        def rail(x, th0=th0, th1=th1):
            e = min(x - 78.95, 89.05 - x)
            return arc_sec(RH - 0.2, RH + (0.45 if e > 0.15 else 0.3), th0, th1, 3, 0.1)
        loft_x(M, rail, [78.95, 79.1, 88.9, 89.05], R["bezel_s"] if s > 0 else R["bezel"])
    # socket rims round the bores (the state-2 footprints)
    for side in ("N", "S"):
        ring_rim(M, star(footprint(FOOT["s2"][side])), R["rim"])


def footprint(runs):
    """Plan outline (c, row) round a lens' red pixel runs [(row, half width about c 84)]."""
    left = []
    r0, w0 = runs[0]
    r1, w1 = runs[-1]
    left.append((EYE - 0.45 * w0, r0 + 0.02))
    for r, w in runs:
        left.append((EYE - w, r + 0.5))
    left.append((EYE - 0.45 * w1, r1 + 0.98))
    right = [(2 * EYE - x, y) for x, y in reversed(left)]
    return chaikin(left + right, 3, closed=True)


def star(poly, k=KRING, centre=None):
    """The outline resampled at k angles round its centroid (rings that line up across outlines)."""
    if centre is None:
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
    else:
        cx, cy = centre
    out = []
    for j in range(k):
        a = 2 * math.pi * j / k
        d = (math.cos(a), math.sin(a))
        best = None
        for p, q in zip(poly, poly[1:] + poly[:1]):
            ex, ey = q[0] - p[0], q[1] - p[1]
            den = d[0] * ey - d[1] * ex
            if abs(den) < 1e-9:
                continue
            t = ((p[0] - cx) * ey - (p[1] - cy) * ex) / den
            u = ((p[0] - cx) * d[1] - (p[1] - cy) * d[0]) / den
            if t > 0 and -1e-6 <= u <= 1 + 1e-6 and (best is None or t < best):
                best = t
        out.append((cx + d[0] * best, cy + d[1] * best))
    return out, (cx, cy)


def lift(c, row, h):
    return (c, row, surf_z(row - AXR) + h)


def ring_rim(M, st, mat, wdt=0.35, h=0.18):
    pts, (cx, cy) = st
    inner = pts
    outer = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1
        outer.append((x + dx / d * wdt, y + dy / d * wdt))
    rings = [[lift(x, y, -0.12) for x, y in inner], [lift(x, y, h) for x, y in inner],
             [lift(x, y, h) for x, y in outer], [lift(x, y, -0.12) for x, y in outer]]
    rings.append(rings[0])
    M.rings(rings, mat, cap0=False, cap1=False)


def dome(M, st, hs, hc, mat, levels=(0.97, 0.9, 0.78, 0.62, 0.42, 0.2), sink=0.15):
    """A bulb on the housing: vertical skirt hs over the footprint, then a cap hc high."""
    pts, (cx, cy) = st
    rings = [[lift(x, y, -sink) for x, y in pts], [lift(x, y, hs) for x, y in pts]]
    for rho in levels:
        hh = hs + hc * math.sqrt(max(0.0, 1 - rho * rho))
        rings.append([lift(cx + rho * (x - cx), cy + rho * (y - cy), hh) for x, y in pts])
    rings.append([lift(cx, cy, hs + hc)])
    M.rings(rings, mat, cap0=True, cap1=False)


def build_lens(state):
    """The eye's state parts: 0 iris shutters, 1 half-out bulbs (119), 2 further out (121), 3 out (123)."""
    M = Mesh()
    names = list(LENS_MATS)
    for side in ("N", "S"):
        bore = star(footprint(FOOT["s2"][side]))
        if state == 0:
            core = star(footprint(FOOT["s117"][side]), centre=bore[1])
            # flush shutter annulus (pipe blue) and the iris centre (51 -> 65 on 117)
            rings = [[lift(x, y, -0.1) for x, y in bore[0]], [lift(x, y, 0.07) for x, y in bore[0]],
                     [lift(x, y, 0.07) for x, y in core[0]], [lift(x, y, -0.1) for x, y in core[0]]]
            rings.append(rings[0])
            M.rings(rings, names.index("shutter"), cap0=False, cap1=False)
            dome(M, core, 0.04, 0.05, names.index("iris"), levels=(0.6,), sink=0.1)
        elif state == 1:  # frame 119: bulbs half out
            dome(M, star(footprint(FOOT["s119"][side])), 0.3, 0.7, names.index("bulb1"))
        elif state == 2:  # frame 121: a little further
            dome(M, star(footprint(FOOT["s121"][side])), 0.35, 0.85, names.index("bulb1"))
        else:
            dome(M, bore, 0.8, 1.6, names.index("bulb2"))
    return M


# --- assembly ------------------------------------------------------------------------------------

def to_object(M, name, mats, coll, smooth_deg=38):
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = Matrix(((PX, 0, 0, -60 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_deg))
    return obj


def merged_sprite():
    data = common.load_sprite(ROOT, "newshs-115")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def build_base(sprite, coll):
    mats = [common.palette_material(sprite, i, f"nshs7_{k}", metallic=m, roughness=r, emission_strength=e)
            for k, (i, m, r, e) in REGIONS.items()]
    M = Mesh()
    build_barrel(M)
    build_bolts(M)
    build_chocks(M)
    build_eye(M)
    return to_object(M, NAME, mats, coll)


def build_state(sprite, state, coll):
    mats = [common.palette_material(sprite, i, f"nshs7_{k}", metallic=m, roughness=r, emission_strength=e,
                                    frames=fr)
            for k, (i, m, r, e, fr) in LENS_MATS.items()]
    return to_object(build_lens(state), f"{NAME}-eye{state}", mats, coll, smooth_deg=50)


def split_open(obj, layout, coll):
    """split_assembly's cut without capping (for outline shells: no ink line across the seams)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for mt in obj.data.materials:
            me.materials.append(mt)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        out[name] = sh
    return out


def joined_copy(objs, name, coll):
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def weighted(o):
    wn = o.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(o)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


STATE_VARIANT = {0: 0, 1: 1, 2: 1, 3: 2}  # lens state -> VARIANTS entry
STATE_FRAMES = {1: [119], 2: [121]}  # state parts shown on one frame only (D17)


def main(argv=None):
    """Build and export the six models. Returns the parts the review driver renders."""
    argv = argv if argv is not None else (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    sprite = merged_sprite()
    coll = common.reset_collection(NAME)
    base = build_base(sprite, coll)
    T.cull_hidden(base)
    weighted(base)
    states = [build_state(sprite, s, coll) for s in range(4)]
    print(f"{NAME}: base {tris(base)} triangles; eye states {[tris(s) for s in states]}")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        textured, tint = T.TEXTURED, T.TINT
        T.TEXTURED = tuple(i for i, k in enumerate(RNAMES) if k not in UNTEXTURED)
        T.TINT = (1.0, 1.0, 1.0)
        try:
            T.bake_maps(base, Path(tempfile.mkdtemp(prefix="nshs7_bake_")), size=1024, samples=48)
        finally:
            T.TEXTURED, T.TINT = textured, tint
        for img in bpy.data.images:
            if img.name in ("talon_colour", "talon_rm"):
                img.name = img.name.replace("talon", "nshs7")
        fmt = "WEBP"
    layout = [(n, cx - CX0, cy - CY0) for n, cx, cy in LAYOUT]
    uniq = []
    for e in layout:
        if e[0] not in [u[0] for u in uniq]:
            uniq.append(e)
    eye_xy = next((cx, cy) for n, cx, cy in layout if n == "newshs-115")
    pieces = common.split_assembly(base, uniq, coll)
    # outline shells (D51): the plain pieces from the base, each eye variant from base + its parts
    shell = common.outline_shell(base, coll, voxel=0.02, faces=6000, smooth=8)
    shells = split_open(shell, uniq, coll)
    lens_obj = {}
    for s in range(4):
        vname = VARIANTS[STATE_VARIANT[s]][0]
        lens_obj[s] = common.split_assembly(states[s], [(f"{vname}-eye{s}", *eye_xy)], coll)[f"{vname}-eye{s}"]
        if s in STATE_FRAMES:
            common.frame_part(lens_obj[s], STATE_FRAMES[s])
    eye_models = {}  # variant -> (lens objects, outline shell)
    for v, (vname, frames) in enumerate(VARIANTS):
        sts = [s for s in range(4) if STATE_VARIANT[s] == v]
        if v == 0:
            esh = shells["newshs-115"]
        else:
            j = joined_copy([base] + [states[s] for s in sts], f"{vname}-joined", coll)
            jsh = common.outline_shell(j, coll, voxel=0.02, faces=6000, smooth=8)
            esh = split_open(jsh, [(vname, *eye_xy)], coll)[vname]
            for o in (j, jsh):
                o.hide_render = True
        eye_models[vname] = ([lens_obj[s] for s in sts], esh)
    for o in [base, shell] + states:
        o.hide_render = True
    for name, p in pieces.items():
        p.data.shade_smooth()
        p.data.set_sharp_from_angle(angle=math.radians(38))
        weighted(p)
        print(f"piece {name}: {tris(p)} triangles, outline {len(shells[name].data.polygons)} faces")
    for vname, (lenses, esh) in eye_models.items():
        print(f"model {vname}: {tris(pieces['newshs-115']) + sum(tris(l) for l in lenses)} triangles")

    # export: the same models, paths and sprites entries as before this rebuild
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        if name != "newshs-115":
            common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"],
                                       image_format=fmt)
    eye = common.load_sprite(ROOT, "newshs-115")
    for vname, frames in VARIANTS:
        lenses, esh = eye_models[vname]
        sprites = [dict(s, frames=frames) for s in eye["sprites"]]
        common.export_sprite_model(ROOT, [pieces["newshs-115"], *lenses, esh], f"enemies/{vname}", sprites,
                                   image_format=fmt)
    return base, states, pieces, eye_models, lens_obj, uniq


if __name__ == "__main__":
    main()
