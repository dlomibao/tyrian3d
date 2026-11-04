"""Grey and red crab-walker boss (newsh^.shp, an assembly of 8 pieces; episode 4): a hard-surface
model led by its silhouette and its read from the small tilted game camera, then detail
(D50-D53, D65 style; top view on the sprite's inner edge, D74). Damaged frames: D86 at runtime.

The sprite is authoritative: the 96 x 56 px assembly outline (pieces newsh-caret-83/85/87/89 over
121/123/125/127), the part layout, and each part's palette index (the median of its sprite pixels
on the lit left half, darkest shading and brightest sheen left out; region_medians.json of the
blueprint). The machine is mirror symmetric about the edge x = 48.5 (the right half is drawn
darker = shadow; built the same).

Reading of the sprite (x = assembly pixel-edge column, y = pixel-edge row, 0 = rear / screen top):
- Rear horns (x 29-38, y 5-18): raked armour tusks rising to a slanted visor tip; the sprite's
  bright columns down them are the ridge edge catching the light.
- Beside each horn a hydraulic actuator post with a domed head (x 36-40, y 12-17).
- Gun arms out to the side (x 15-31, y 11-18): a chamfered housing with a red access panel and a
  dark end clamp with a muzzle, braced by a tube into the horn (row 8).
- Red yoke beams (y 19-22) carrying the drum pods (x 7-24, y 20-31): domed outer bell with a hub,
  a bright flange rim, two red strap bands.
- Shoulder housings the pods plug into, a skirt under them.
- A red armour saddle across the middle (x 32-65, y 18-28) with a pink dorsal spine (head cap, two
  vertebrae and a tail, x 44-53, y 12-32).
- A light-grey chest across the front of the saddle (bright bar of row 32 = its front bevel).
- Red hip armour sweeping down to the claws; big ridged claws reaching forward at the lower corners
  (x 16-31, y 32-49), each on a dark hip drum.
- The jaw at the front: dark housing, red hinge bar, red fangs, struts and tines (x 33-64, y 35-48).

Built in sprite px (x col edge, y row edge, z up) and moved to Blender at the end:
X = (x - 48.5) / 12, Y = (27 - y) / 12, Z = z / 12 (the current script's assembly frame: screen
pixel (20, 37) is pixel (0, 0); origin screen (68.5, 64)). Then cut into the eight pieces with
common.split_assembly, each with its outline shell (D51; the shell is cut open at the seams, so no
ink line runs across the machine where two pieces meet). Each piece is exported to
public/models/enemies/<piece>.glb with its src/render/spriteModels/<piece>.json entry (one frame
each). Texture: AO / roughness bake only (usp_talon.bake_maps), no concept projection.

  blender --background --factory-startup --python assets/blender/enemies/assembly-newsh-caret-123.py
      -- [--no-bake] [--out review.glb] [--preview out.png]

--out writes a review copy of the whole machine (pieces at their places) instead of the game export.
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import pchip  # noqa: E402

NAME = "assembly-newsh-caret-123"
ROOT = common.repo_root(__file__)
PIECES = ["newsh-caret-83", "newsh-caret-85", "newsh-caret-87", "newsh-caret-89",
          "newsh-caret-121", "newsh-caret-123", "newsh-caret-125", "newsh-caret-127"]
SX0, SY0 = 68.5, 64.0
AX = 48.5
PX = 1 / 12


def MX(x):
    return 2 * AX - x


# --- regions: palette index (sprite lit-half median) and finish ---------------------------------
# (index, metallic, roughness). Greys are satin steel, reds painted armour, recesses dull.
# The pod rim is pal 8 although the sprite's lit median there is 10: the rim is a one-pixel bright
# column, i.e. sheen (tools/calibration/rubric.md, "Reading a sprite"); a bright 10 ring would read
# as a chrome band. Leave it at 8.
# The claws and the skirt under the pods are a duller, more matte steel than the rest (higher
# metallic darkens their diffuse, higher roughness kills the gloss), so under the game light they
# sit at the sprite's mid-dark grey (pal 5) instead of reading as a lighter material.
REGIONS = {
    "horn": (8, 0.5, 0.4), "post": (7, 0.55, 0.36), "rod": (5, 0.6, 0.32), "arm": (5, 0.5, 0.42),
    "endcap": (3, 0.5, 0.45), "armpanel": (67, 0.2, 0.5), "yoke": (67, 0.2, 0.5), "strap": (70, 0.2, 0.46),
    "pod": (5, 0.5, 0.4), "podrim": (8, 0.6, 0.3), "shoulder": (7, 0.5, 0.42), "skirt": (5, 0.92, 0.56),
    "plate": (73, 0.22, 0.44), "hip": (70, 0.22, 0.46), "spine": (74, 0.22, 0.42), "head": (72, 0.22, 0.42),
    "chest": (8, 0.5, 0.4), "crest": (5, 0.5, 0.42), "jaw": (4, 0.45, 0.48), "hinge": (67, 0.2, 0.5),
    "fang": (70, 0.22, 0.46), "strut": (5, 0.55, 0.38), "tine": (6, 0.55, 0.36), "claw": (5, 0.92, 0.56),
    "joint": (4, 0.5, 0.45), "recess": (2, 0.15, 0.8), "muzzle": (2, 0.2, 0.7),
}
RNAMES = list(REGIONS)
R = {k: i for i, k in enumerate(RNAMES)}
UNTEXTURED = ()
METAL = 0.6  # satin: keep the palette colour readable under the game's lights


# --- mesh builder (sprite px; closed solids, normals fixed at the end) ----------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, vs, region):
        if len({id(v) for v in vs}) < 3:
            return None
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = R[region] if isinstance(region, str) else region
        return face

    def rings(self, rings, region, cap0=True, cap1=True, seg_regions=None, tri=False):
        """Loft through rings of 3D points (same count; a 1-point ring is an apex)."""
        vr = [[self.v(p) for p in r] for r in rings]
        for k in range(len(vr) - 1):
            a, b = vr[k], vr[k + 1]
            reg = seg_regions[k] if seg_regions else region
            n = max(len(a), len(b))
            for i in range(n):
                j = (i + 1) % n
                if len(a) == 1:
                    self.f([a[0], b[i], b[j]], reg)
                elif len(b) == 1:
                    self.f([a[i], a[j], b[0]], reg)
                else:
                    self.f([a[i], a[j], b[j], b[i]], reg)
        caps = []
        if cap0 and len(vr[0]) > 2:
            caps.append(self.f(list(reversed(vr[0])), region))
        if cap1 and len(vr[-1]) > 2:
            caps.append(self.f(vr[-1], region))
        # ngon caps (concave or tilted plan outlines) triangulated here, so no exporter fan crosses them
        big = [c for c in caps if c is not None and len(c.verts) > 4]
        if big and tri:
            bmesh.ops.triangulate(self.bm, faces=big, quad_method="BEAUTY", ngon_method="BEAUTY")

    def hull(self, pts, region):
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
            self.f([vm[v] for v in fc.verts], region)
        tmp.free()


def inset2(poly, c):
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    s = 1 if area > 0 else -1
    nrm = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1
        nrm.append((-dy / ln * s, dx / ln * s))
    out = []
    for i in range(n):
        a, b = nrm[i - 1], nrm[i]
        d = 1 + a[0] * b[0] + a[1] * b[1]
        out.append((poly[i][0] + (a[0] + b[0]) * c / d, poly[i][1] + (a[1] + b[1]) * c / d))
    return out


def prism(M, region, poly, z0, z1, ch=0.0, zt=None, chb=0.0):
    """Vertical prism over a plan outline, top edge chamfered `ch` (and bottom `chb`); zt(x, y) tilts
    the top."""
    Z = zt or (lambda x, y: z1)
    rings = []
    if chb > 0:
        rings.append([(x, y, z0) for x, y in inset2(poly, chb)])
        rings.append([(x, y, z0 + chb) for x, y in poly])
    else:
        rings.append([(x, y, z0) for x, y in poly])
    if ch > 0:
        rings.append([(x, y, Z(x, y) - ch) for x, y in poly])
        rings.append([(x, y, Z(x, y)) for x, y in inset2(poly, ch)])
    else:
        rings.append([(x, y, Z(x, y)) for x, y in poly])
    M.rings(rings, region, tri=zt is not None)


def box(M, region, x0, x1, y0, y1, z0, z1, ch=0.0):
    prism(M, region, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, ch)


def ch_rect(u0, u1, z0, z1, cl, cr, cb=0.0):
    return [(u0 + cb, z0), (u1 - cb, z0), (u1, z0 + cb), (u1, z1 - cr), (u1 - cr, z1), (u0 + cl, z1),
            (u0, z1 - cl), (u0, z0 + cb)]


def loft_sec(M, region, axis, secs, steps=1, grooves=(), seg_region=None):
    """Loft along y (axis 'y': section points (x, z)) or x (axis 'x': (y, z)) through sections
    interpolated by pchip. grooves: [(t, width, depth)] cut panel joints round the section."""
    ts = [s[0] for s in secs]
    n = len(secs[0][1])
    fu = [pchip(ts, [s[1][k][0] for s in secs]) for k in range(n)]
    fz = [pchip(ts, [s[1][k][1] for s in secs]) for k in range(n)]
    stations = []
    for i in range(len(ts) - 1):
        for s in range(steps):
            stations.append((ts[i] + (ts[i + 1] - ts[i]) * s / steps, 0.0))
    stations.append((ts[-1], 0.0))
    for t, w, d in grooves:
        stations = [st for st in stations if not (t - w / 2 - 0.05 < st[0] < t + w / 2 + 0.05)]
        stations += [(t - w / 2, 0.0), (t - w / 2 + 0.02, d), (t + w / 2 - 0.02, d), (t + w / 2, 0.0)]
    stations.sort()
    rings = []
    for t, d in stations:
        pts = [(fu[k](t), fz[k](t)) for k in range(n)]
        if d:
            cu = sum(p[0] for p in pts) / n
            cz = sum(p[1] for p in pts) / n
            pts2 = []
            for u, z in pts:
                du, dz = u - cu, z - cz
                ln = math.hypot(du, dz) or 1
                pts2.append((u - du / ln * d, z - dz / ln * d))
            pts = pts2
        rings.append([(u, t, z) if axis == "y" else (t, u, z) for u, z in pts])
    M.rings(rings, region)


def lathe_x(M, region, st, cy, cz, ry, rz, n=20, seg=None):
    """Lathe along x: stations (x, f) (f = radius fraction) round the axis (cy, cz), radii ry, rz."""
    rings = []
    for x, f in st:
        if f <= 0:
            rings.append([(x, cy, cz)])
        else:
            rings.append([(x, cy + f * ry * math.cos(2 * math.pi * i / n), cz + f * rz * math.sin(2 * math.pi * i / n))
                          for i in range(n)])
    M.rings(rings, region, seg_regions=seg)


def sweep(M, region, pts, r, n=10):
    rings = []
    for k, p in enumerate(pts):
        a, b = Vector(pts[max(0, k - 1)]), Vector(pts[min(len(pts) - 1, k + 1)])
        t = (b - a).normalized()
        up = Vector((1, 0, 0)) if abs(t.z) > 0.9 else Vector((0, 0, 1))
        u = t.cross(up).normalized()
        v = u.cross(t).normalized()
        rr = r[k] if isinstance(r, (list, tuple)) else r
        if rr <= 0:
            rings.append([tuple(p)])
            continue
        rings.append([tuple(Vector(p) + rr * (math.cos(2 * math.pi * i / n) * u + math.sin(2 * math.pi * i / n) * v))
                      for i in range(n)])
    M.rings(rings, region)


def dome_y(M, region, cx, st, n=12, e=2.6):
    """Rounded-top loft along y: stations (y, half width, z bottom, z top), centred on cx."""
    rings = []
    for y, hw, zb, ztop in st:
        pts = []
        for i in range(n + 1):
            a = math.pi * i / n
            c, s = math.cos(a), math.sin(a)
            sx = math.copysign(abs(c) ** (2 / e), c)
            sz = abs(s) ** (2 / e)
            pts.append((cx + hw * sx, y, zb + (ztop - zb) * sz))
        rings.append(pts)
    M.rings(rings, region)


def post(M, region, cx, cy, rx, ry, z0, z1, n=16):
    dome = [1, 0.97, 0.86, 0.62, 0.0]
    hz = [0, 0.25, 0.55, 0.85, 1.0]
    cap = min(rx, ry) * 0.7
    rings = [[(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n), z0) for i in range(n)]]
    for f, h in zip(dome, hz):
        z = z1 - cap + cap * h
        if f <= 0:
            rings.append([(cx, cy, z)])
        else:
            rings.append([(cx + f * rx * math.cos(2 * math.pi * i / n), cy + f * ry * math.sin(2 * math.pi * i / n), z)
                          for i in range(n)])
    M.rings(rings, region)


def bolt(M, region, x, y, z, r=0.32, h=0.28, n=6, axis="z"):
    """A hex bolt head standing on a surface (axis = its normal: 'z', '-x', '+x', '+y')."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        for d, rr in ((-0.1, r), (h, r * 0.82)):
            u, w = rr * math.cos(a), rr * math.sin(a)
            if axis == "z":
                pts.append((x + u, y + w, z + d))
            elif axis in ("-x", "+x"):
                s = -1 if axis == "-x" else 1
                pts.append((x + s * d, y + u, z + w))
            else:
                s = 1 if axis == "+y" else -1
                pts.append((x + u, y + s * d, z + w))
    M.hull(pts, region)


def hcbox(M, region, x0, x1, y0, y1, z0, z1, ch):
    M.hull(T.cbox(x0, x1, y0, y1, z0, z1, ch), region)


# --- the machine ------------------------------------------------------------------------------------

def horn_sec(t, x0, x1, z0, z1, ridge):
    # A raked tusk: flat outer flank, a sharp ridge (the sprite's bright line), inner shoulder.
    return (t, [(x0, z0), (x1, z0), (x1, z1 - 2.2), (x1 - 0.5, z1 - 1.5), (ridge, z1),
                (x0 + 0.9, z1 - 0.35), (x0, z1 - 1.1)])


def claw_sec(t, x0, x1, zb, zt, ridge):
    # heights kept in order as the section thins toward the point (no folded tip)
    h = zt - zb
    lo = zb + min(0.6, 0.2 * h)
    def side(d):
        return max(lo + 0.05 * h, zt - min(d, 0.6 * h))
    return (t, [(x0 + 0.3, zb), (x1 - 0.3, zb), (x1, lo), (x1, side(1.7)), (ridge + 1.2, zt - min(0.35, 0.2 * h)),
                (ridge, zt), (x0 + 0.8, zt - min(0.6, 0.3 * h)), (x0, side(1.4)), (x0, lo)])


def build_left(M):
    # --- rear horn (x 29-38, y 5-18), joints at rows 9.6 and 13.8 ---
    loft_sec(M, "horn", "y", [
        horn_sec(5.05, 31.3, 38.0, 9.2, 12.4, 34.8), horn_sec(6.0, 30.4, 37.6, 8.4, 12.2, 34.4),
        horn_sec(7.0, 29.4, 36.4, 7.4, 11.9, 33.8), horn_sec(9.0, 28.9, 36.0, 6.0, 11.3, 33.6),
        horn_sec(13.0, 28.8, 36.0, 3.6, 10.4, 33.6), horn_sec(18.6, 28.8, 36.2, 1.0, 9.4, 33.6)], 3,
        grooves=[(9.8, 0.35, 0.22), (13.9, 0.35, 0.22)])
    # the tip visor: a raised slanted cap
    prism(M, "horn", [(31.6, 5.2), (37.6, 5.2), (36.6, 6.9), (30.4, 6.9)], 11.4, 12.75, 0.3,
          zt=lambda x, y: 12.75 - (y - 5.2) * 0.25)
    # bolts down the horn's inner flank
    for y in (11.6, 16.2):
        bolt(M, "endcap", 35.0, y, 10.0 - (y - 11.6) * 0.17, r=0.36)
    # --- actuator post: cylinder, collar ring and a chrome rod band ---
    post(M, "post", 38.05, 15.0, 1.95, 3.0, 0, 9.6, n=18)
    lathe_z_ring(M, "arm", 38.05, 15.0, 2.2, 3.25, 6.0, 7.0)
    lathe_z_ring(M, "arm", 38.05, 15.0, 2.1, 3.15, 3.0, 3.6)
    # --- brace tube from the arm clamp into the horn (row 8) on a bracket web ---
    sweep(M, "rod", [(23.7, 8.55, 6.6), (29.6, 8.55, 7.2)], 0.62, 12)
    sweep(M, "arm", [(23.9, 8.55, 6.6), (24.7, 8.55, 6.65)], 0.8, 12)
    sweep(M, "arm", [(28.6, 8.55, 7.1), (29.4, 8.55, 7.18)], 0.78, 12)
    prism(M, "recess", [(24.0, 8.7), (29.0, 8.7), (29.0, 11.2), (23.6, 11.2)], 2.2, 6.4, 0.2)
    # --- gun arm: chamfered housing (x 18-30, y 11-18.6) ---
    loft_sec(M, "arm", "x", [
        (18.1, ch_rect(11.3, 18.4, 2.4, 6.9, 0.8, 0.5, 0.3)), (24.0, ch_rect(11.1, 18.5, 2.4, 7.3, 0.8, 0.5, 0.3)),
        (29.2, ch_rect(11.0, 18.6, 2.4, 7.6, 0.8, 0.5, 0.3))], 1, grooves=[(22.2, 0.3, 0.18)])
    # red access panel, two bolts
    prism(M, "armpanel", [(23.2, 13.0), (29.0, 13.0), (29.0, 16.0), (23.2, 16.0)], 6.8, 7.85, 0.25)
    for x in (24.0, 28.2):
        bolt(M, "endcap", x, 14.5, 7.8, r=0.34, h=0.25)
    # cooling slots on the housing's front face (toward the camera)
    for x in (19.6, 20.6, 21.6):
        box(M, "recess", x, x + 0.45, 18.45, 18.75, 3.4, 5.6)
    # dark end clamp with the muzzle
    prism(M, "endcap", [(17.2, 12.0), (21.8, 12.0), (21.8, 17.0), (15.1, 17.0), (15.1, 14.1), (16.2, 13.1)],
          1.8, 7.9, 0.55, chb=0.3)
    lathe_x(M, "endcap", [(15.05, 0.0), (15.05, 0.8), (15.05, 1.0), (15.6, 1.0)], 14.1, 4.9, 1.35, 1.35, n=16)
    lathe_x(M, "muzzle", [(14.95, 0.0), (14.95, 0.62), (15.15, 0.62)], 14.1, 4.9, 1.35, 1.35, n=16)
    prism(M, "endcap", [(18.2, 16.2), (23.4, 16.2), (23.4, 18.6), (19.0, 18.6)], 1.0, 4.6, 0.3)
    # --- red yoke beam (rows 19-22) ---
    loft_sec(M, "yoke", "x", [
        (14.1, ch_rect(20.8, 22.0, 5.6, 7.6, 0.4, 0.4)), (15.2, ch_rect(20.3, 22.1, 5.4, 8.8, 0.6, 0.5)),
        (17.9, ch_rect(19.7, 22.1, 5.4, 9.2, 0.7, 0.5)), (18.6, ch_rect(18.95, 22.1, 5.4, 9.2, 0.7, 0.5)),
        (29.6, ch_rect(18.95, 22.1, 5.4, 9.4, 0.7, 0.5))], 1, grooves=[(24.4, 0.3, 0.16)])
    for x in (20.6, 27.6):
        bolt(M, "endcap", x, 20.5, 9.25, r=0.3, h=0.22)
    # --- drum pod: domed bell, hub, drum with grooves, flange rim, two red straps ---
    cy, cz, ry, rz = 25.7, 4.7, 5.0, 4.3
    by, bry = 24.4, 4.5
    lathe_x(M, "pod", [(6.95, 0.4), (7.15, 0.7), (7.5, 0.89), (8.2, 0.98), (8.8, 1.0), (10.2, 1.0)], by, cz, bry, rz, n=24)
    # hub: a stepped boss with a dark bore
    lathe_x(M, "endcap", [(6.7, 0.0), (6.7, 0.24), (6.75, 0.3), (6.95, 0.34), (7.0, 0.42)], by, cz, bry, rz, n=16)
    lathe_x(M, "muzzle", [(6.6, 0.0), (6.6, 0.14), (6.75, 0.14)], by, cz, bry, rz, n=12)
    lathe_x(M, "pod", [(8.8, 0.9), (9.2, 1.0), (13.4, 1.0), (13.45, 0.95), (13.75, 0.95), (13.8, 1.0),
                       (19.0, 1.0), (19.05, 0.95), (19.35, 0.95), (19.4, 1.0), (21.0, 1.0), (23.8, 0.97)],
            cy, cz, ry, rz, n=24)
    lathe_x(M, "podrim", [(10.35, 1.0), (10.5, 1.035), (11.15, 1.035), (11.3, 1.0)], cy, cz, ry, rz, n=24)
    lathe_x(M, "strap", [(14.85, 0.98), (15.05, 1.035), (16.95, 1.035), (17.15, 0.98)], cy, cz, ry, rz, n=24)
    lathe_x(M, "strap", [(21.65, 0.97), (21.85, 1.03), (23.55, 1.03), (23.75, 0.97)], cy, cz, ry, rz, n=24)
    # bolts round the flange rim (upper half: what the camera sees)
    for a in (35, 70, 110, 145):
        t = math.radians(a)
        y, z = cy + 1.04 * ry * math.cos(t), cz + 1.04 * rz * math.sin(t)
        pts = []
        for k in range(6):
            q = 2 * math.pi * k / 6
            for d, rr in ((-0.1, 0.3), (0.22, 0.24)):
                nrm = Vector((0, math.cos(t) / ry, math.sin(t) / rz)).normalized()
                tan = Vector((0, -nrm.z, nrm.y))
                p = Vector((10.82, y, z)) + nrm * d + rr * (math.cos(q) * Vector((1, 0, 0)) + math.sin(q) * tan)
                pts.append(tuple(p))
        M.hull(pts, "endcap")
    # --- shoulder housing the pod plugs into (x 20-33, y 22-29), vent slots on top ---
    prism(M, "shoulder", [(21.0, 21.8), (33.2, 21.8), (33.2, 25.4), (29.4, 26.4), (28.4, 28.8), (21.0, 28.8),
                          (20.2, 27.4), (20.2, 22.8)], 0, 8.6, 0.9)
    for y in (23.1, 24.3, 25.5):
        box(M, "recess", 23.8, 28.6, y, y + 0.38, 8.25, 8.7)
    bolt(M, "endcap", 31.6, 23.0, 8.55, r=0.32, h=0.22)
    bolt(M, "endcap", 22.0, 27.6, 8.55, r=0.32, h=0.22)
    # skirt under the pod's inner end
    prism(M, "skirt", [(14.6, 28.2), (23.6, 28.2), (23.6, 33.6), (17.2, 33.4), (16.3, 32.9), (14.4, 31.9)], 0, 4.4, 0.6)
    # --- red hip armour sweeping to the claw root ---
    prism(M, "hip", [(29.2, 26.0), (39.6, 26.0), (39.6, 28.2), (36.2, 28.4), (36.0, 30.4), (31.6, 31.3), (31.0, 33.0),
                     (29.2, 34.4), (28.2, 35.2), (26.6, 34.8), (25.0, 33.4), (25.0, 30.1), (29.0, 29.9)],
          1.2, 7.6, 0.6, zt=lambda x, y: 7.6 - max(0, 34 - x) * 0.17 - max(0, y - 30) * 0.2)
    # a seam across it
    box(M, "recess", 30.0, 30.35, 26.4, 29.6, 6.9, 7.55)
    # --- claw: segmented armoured leg reaching forward to a point ---
    loft_sec(M, "claw", "y", [
        claw_sec(31.8, 17.6, 28.6, 1.6, 7.4, 23.0), claw_sec(34.0, 19.2, 30.2, 1.4, 7.1, 23.2),
        claw_sec(35.5, 18.3, 30.8, 1.3, 6.9, 23.4), claw_sec(36.5, 17.0, 31.4, 1.2, 6.7, 23.6),
        claw_sec(37.3, 16.2, 31.4, 1.2, 6.5, 23.8), claw_sec(39.9, 16.3, 30.9, 1.0, 5.8, 24.5),
        claw_sec(40.5, 18.0, 30.9, 1.0, 5.6, 24.7), claw_sec(41.2, 19.0, 30.4, 0.9, 5.3, 24.9),
        claw_sec(42.5, 19.1, 29.2, 0.8, 5.0, 25.0), claw_sec(45.2, 19.4, 29.2, 0.6, 3.9, 25.0),
        claw_sec(47.1, 21.6, 28.6, 0.4, 2.7, 25.3), claw_sec(48.5, 23.8, 27.1, 0.25, 1.5, 25.5),
        claw_sec(49.0, 25.0, 26.4, 0.2, 0.7, 25.6)], 2,
        grooves=[(36.0, 0.35, 0.25), (40.2, 0.35, 0.25), (44.0, 0.35, 0.22)])
    # a machined keel rib along the claw's ridge: the sprite's bright stripe down the claw is this
    # crisp edge catching the light
    path = [(23.0, 32.4, 7.3), (23.2, 34.0, 7.1), (23.8, 37.3, 6.5), (24.5, 39.9, 5.8), (25.0, 42.5, 5.0),
            (25.0, 45.2, 3.9), (25.2, 46.4, 3.15)]
    sec = [(-0.5, -0.35), (0.5, -0.35), (0.32, 0.32), (-0.32, 0.32)]
    rings = [[(x + u, y, z + w) for u, w in sec] for x, y, z in path]
    rings[-1] = [(x * 0.5 + path[-1][0] * 0.5, y, (z + path[-1][2]) * 0.5) for x, y, z in rings[-1]]
    M.rings(rings, "tine")
    for y, z in ((33.0, 7.0), (38.6, 6.2)):
        bolt(M, "joint", 20.4, y, z - 1.0, r=0.38, h=0.25)
    # hip drum on an axle
    lathe_x(M, "joint", [(26.8, 0.8), (27.1, 1.0), (29.9, 1.0), (29.95, 0.92), (30.25, 0.92), (30.3, 1.0),
                         (33.4, 1.0), (33.7, 0.8)], 34.1, 4.6, 2.35, 2.35, n=18)
    lathe_x(M, "muzzle", [(33.6, 0.5), (34.4, 0.5), (34.4, 0.0)], 34.1, 4.6, 2.35, 2.35, n=12)
    # --- front jaw ---
    prism(M, "jaw", [(34.1, 35.0), (42.4, 35.0), (42.4, 44.6), (43.2, 44.8), (43.2, 46.0), (37.0, 46.0), (36.9, 45.0),
                     (34.1, 44.9), (34.1, 40.1), (34.7, 39.9), (34.7, 38.1), (34.1, 37.9)], 0, 3.4, 0.4)
    loft_sec(M, "hinge", "x", [(35.9, ch_rect(35.8, 38.1, 3.8, 5.6, 0.4, 0.4)),
                               (41.3, ch_rect(35.8, 38.1, 3.8, 5.6, 0.4, 0.4))], 1)
    sweep(M, "tine", [(38.5, 36.9, 5.5), (38.5, 36.9, 6.0)], 0.45, 10)
    sweep(M, "tine", [(35.6, 36.95, 4.7), (41.6, 36.95, 4.7)], 0.55, 10)
    loft_sec(M, "fang", "y", [
        (38.4, ch_rect(37.9, 42.0, 1.6, 5.0, 0.6, 0.6, 0.3)), (42.0, ch_rect(38.0, 42.0, 1.2, 4.4, 0.6, 0.6, 0.3)),
        (45.5, ch_rect(37.9, 42.1, 0.8, 3.6, 0.55, 0.55, 0.25)), (47.4, ch_rect(38.3, 41.3, 0.5, 2.3, 0.4, 0.4, 0.15)),
        (48.15, ch_rect(39.3, 40.2, 0.4, 0.9, 0.15, 0.15, 0.05))], 2, grooves=[(41.0, 0.3, 0.18)])
    sweep(M, "strut", [(44.0, 34.8, 3.4), (44.0, 39.0, 3.0), (44.0, 43.8, 2.0)], [1.35, 1.25, 1.0], 12)
    sweep(M, "tine", [(44.0, 43.6, 2.05), (44.0, 44.2, 1.95), (44.0, 44.6, 1.8)], [0.85, 0.75, 0.0], 12)
    lathe_y_ring(M, "tine", 44.0, 2.9, 40.0, 40.6, 1.38)
    sweep(M, "tine", [(46.5, 37.0, 2.4), (46.5, 43.6, 1.6), (46.5, 44.0, 1.55)], [0.55, 0.5, 0.0], 10)
    # --- chest side block, its front face stepped down ---
    prism(M, "chest", [(36.2, 29.0), (41.6, 29.0), (41.6, 35.0), (36.8, 35.0), (36.2, 34.4)], 0, 7.4, 0.55,
          zt=lambda x, y: 7.4 if y < 32.4 else 7.4 - (y - 32.4) * 0.8)
    for y in (33.1, 33.9):
        box(M, "recess", 37.2, 40.6, y, y + 0.3, 5.0, 6.75 - (y - 33.1) * 0.6)
    # --- chassis (dark, only seen in the gaps) ---
    prism(M, "recess", [(14.6, 21.2), (18.4, 19.6), (18.6, 18.8), (23.0, 18.6), (23.1, 9.95), (28.5, 9.95), (36.8, 10.6),
                        (36.8, 11.9), (40.0, 12.0), (40.0, 18.8), (43.6, 19.0), (48.5, 19.0), (48.5, 45.0), (42.6, 45.0),
                        (42.4, 36.0), (34.0, 36.0), (33.6, 36.9), (31.0, 37.0), (28.2, 35.6), (17.0, 33.2), (14.6, 31.0)],
          0, 1.4, 0.2)


def lathe_z_ring(M, region, cx, cy, rx, ry, z0, z1, n=18):
    """A collar ring round a vertical post: an elliptic band with chamfered edges."""
    rings = []
    for z, f in ((z0, 0.94), (z0 + 0.12, 1.0), (z1 - 0.12, 1.0), (z1, 0.94)):
        rings.append([(cx + f * rx * math.cos(2 * math.pi * i / n), cy + f * ry * math.sin(2 * math.pi * i / n), z)
                      for i in range(n)])
    M.rings(rings, region)


def lathe_y_ring(M, region, cx, cz, y0, y1, r, n=12):
    rings = []
    for y, f in ((y0, 0.92), (y0 + 0.1, 1.0), (y1 - 0.1, 1.0), (y1, 0.92)):
        rings.append([(cx + f * r * math.cos(2 * math.pi * i / n), y, cz + f * r * math.sin(2 * math.pi * i / n))
                      for i in range(n)])
    M.rings(rings, region)


def build_centre(M):
    # --- red armour saddle (x 32-65, y 18-28): chamfered plate with a raised centre deck ---
    sad = [(32.4, 19.4), (33.6, 18.2), (40.4, 18.2), (41.2, 19.0), (43.0, 19.0), (43.0, 18.0), (MX(43.0), 18.0),
           (MX(43.0), 19.0), (MX(41.2), 19.0), (MX(40.4), 18.2), (MX(33.6), 18.2), (MX(32.4), 19.4),
           (MX(32.4), 25.3), (MX(40.2), 25.3), (MX(40.4), 28.2), (MX(44.0), 28.4), (44.0, 28.4), (40.4, 28.2),
           (40.2, 25.3), (32.4, 25.3)]
    prism(M, "plate", sad, 0, 8.0, 0.8, zt=lambda x, y: 8.0 + 0.6 * max(0.0, 1 - abs(x - AX) / 10))
    for s in (1, -1):
        X = (lambda x: x) if s > 0 else MX
        x0, x1 = sorted((X(39.4), X(39.8)))
        box(M, "recess", x0, x1, 19.4, 24.9, 8.05, 8.55)
        x0, x1 = sorted((X(34.6), X(34.95)))
        box(M, "recess", x0, x1, 19.6, 24.6, 7.6, 7.75)
        for y in (20.0, 24.0):
            bolt(M, "endcap", X(36.8), y, 7.95, r=0.34, h=0.22)
    # --- pink dorsal spine: head cap, two vertebrae, a tail ---
    dome_y(M, "head", AX, [(12.75, 2.4, 3.0, 8.6), (13.0, 3.3, 2.4, 9.8), (14.0, 3.55, 2.0, 10.6), (15.6, 3.6, 2.0, 10.9),
                            (16.1, 4.15, 2.0, 10.7), (16.8, 4.15, 2.0, 10.4)], 14)
    dome_y(M, "spine", AX, [(16.4, 3.9, 2.0, 10.0), (17.4, 4.45, 2.0, 10.5), (19.4, 4.2, 2.0, 10.7), (21.0, 3.6, 4.0, 10.4),
                             (22.0, 2.6, 5.0, 9.8)], 14)
    dome_y(M, "spine", AX, [(21.6, 1.9, 6.0, 9.6), (24.0, 1.9, 6.0, 9.6)], 10)
    dome_y(M, "spine", AX, [(23.6, 2.6, 5.0, 9.6), (24.4, 3.4, 4.0, 10.2), (26.2, 3.5, 4.0, 10.3), (27.6, 3.0, 4.0, 9.8),
                             (28.4, 2.0, 5.0, 9.2)], 14)
    dome_y(M, "spine", AX, [(27.8, 1.75, 6.0, 9.2), (30.0, 1.75, 6.0, 8.9), (31.4, 1.6, 6.0, 8.5), (32.2, 0.9, 6.4, 8.0)], 10)
    # --- chest: grey crest and front block across the saddle's front ---
    prism(M, "crest", [(41.4, 29.0), (MX(41.4), 29.0), (MX(41.4), 32.4), (41.4, 32.4)], 0, 7.9, 0.35)
    sec = [(32.2, 0.0), (35.2, 0.0), (35.2, 5.2), (33.0, 7.6), (32.2, 7.9)]
    loft_sec(M, "chest", "x", [(41.4, sec), (MX(41.4), sec)], 1)
    # vent grille in the chest front (between the spine tail and the jaw)
    for x in (44.6, 46.0, 47.4, 48.8, 50.2, 51.6):
        box(M, "recess", x, x + 0.5, 35.1, 35.4, 2.0, 4.6)
    # --- centre ram tine ---
    sweep(M, "tine", [(AX, 34.8, 3.0), (AX, 40.0, 2.6), (AX, 45.4, 1.6), (AX, 46.0, 1.45)], [0.95, 1.0, 1.05, 0.0], 12)


def build(mats, coll):
    M = Mesh()
    build_left(M)
    geom = M.bm.verts[:] + M.bm.edges[:] + M.bm.faces[:]
    dup = bmesh.ops.duplicate(M.bm, geom=geom)
    dv = [g for g in dup["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in dv:
        v.co.x = MX(v.co.x)
    build_centre(M)
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = Matrix(((PX, 0, 0, -AX * PX), (0, -PX, 0, 27 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    return obj


def merged_sprite():
    """newsh-caret-123's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newsh-caret-123")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def materials(sprite):
    return [common.palette_material(sprite, i, f"nshc123_{k}", metallic=m * METAL, roughness=r)
            for k, (i, m, r) in REGIONS.items()]


def split_open(obj, layout, coll):
    """common.split_assembly's cut without capping the cuts (for the outline shells): a capped shell
    draws an ink line across the machine at every piece seam (as assembly-newsh2-119.py)."""
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


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = merged_sprite()
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    obj = build(mats, coll)
    if "--no-cull" not in argv:
        T.cull_hidden(obj)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        textured, tint = T.TEXTURED, T.TINT
        T.TEXTURED = tuple(i for i, k in enumerate(RNAMES) if k not in UNTEXTURED)
        T.TINT = (1.0, 1.0, 1.0)
        try:
            T.bake_maps(obj, Path(tempfile.mkdtemp(prefix="nshc123_bake_")), size=1024, samples=64)
        finally:
            T.TEXTURED, T.TINT = textured, tint
        for img in bpy.data.images:
            if img.name in ("talon_colour", "talon_rm"):
                img.name = img.name.replace("talon", "nshc123")
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.02, faces=5000, smooth=8)
    layout = [(e["model"], e["cx"] - SX0, e["cy"] - SY0) for e in sprite["assemblyLayout"] if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout, coll)
    shells = split_open(shell, layout, coll)
    for o in (obj, shell):
        o.hide_render = True
    total = 0
    for name, _cx, _cy in layout:
        p = pieces[name]
        p.data.shade_smooth()
        p.data.set_sharp_from_angle(angle=math.radians(38))
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        t = sum(len(q.vertices) - 2 for q in p.data.polygons)
        total += t
        print(f"piece {name}: {t} triangles, outline {len(shells[name].data.polygons)} faces")
    print(f"total {total} triangles")
    if "--out" in argv:  # a review copy of the whole machine, not the game export
        export = []
        for name, cx, cy in layout:
            for o in (pieces[name], shells[name]):
                o.location = (cx / 12, -cy / 12, 0)
                export.append(o)
        out = common.export_glb(export, argv[argv.index("--out") + 1], image_format=fmt)
        print(f"review copy {out}")
        for name, _cx, _cy in layout:
            for o in (pieces[name], shells[name]):
                o.location = (0, 0, 0)
    else:
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"],
                                       image_format=fmt)
    if "--preview" in argv:
        out = Path(argv[argv.index("--preview") + 1])
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)
        obj.hide_render = False
        common.render_preview([obj], str(out), None, size=(96, 56), view_px=480)


if __name__ == "__main__":
    main()
