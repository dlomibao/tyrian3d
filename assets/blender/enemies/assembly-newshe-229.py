"""Red armoured pod with a dark glass cap and glowing lenses (newshe.shp 191/193/229/231, an assembly
of 4 pieces), silhouette and readability first, then detail.

WHAT IT IS: a fast free-flying pod (types 682-685: mv(0,3), armour 20, no gun; it slides down the
screen over the ground in 2.9 MISTAKES, flies on the top layer in 3.6 FLEET and sideways in 3.7
STARGATE). Not a ground structure. Several fly in a row, overlapping.

Read at the small tilted game camera as four masses: (1) a glossy red orb, a little oblate, with a
machined equator belt; (2) a big black glass cap set to its back left, raised on a dark bezel, that
wraps down over the rear; (3) two glowing white-hot lenses in thick collars on the cap (a big one
and a small one) and two dim red studs; (4) panel-line grooves on the red crescent (one latitude
line, five meridians) and notches round the belt. Rear (north, below the belt): two small thruster
bells, hidden from the top view. The underside is the closed round lower hull, no detail.

The sprite rules: the belt's plan is the sprite's inner mask (D74) traced in polar form round its
centroid and low-passed; the cap's plan is the sprite's dark region (palette 1/64, holes filled)
traced the same way; lenses and studs at the sprite's places and sizes. Colours are the sprite's
palette indices per region. The red ramp's shading (dark NE, lit W, hot SE rim) is lighting.

Coordinates while building: u = sprite column edge (0..48 east), v = sprite row edge (0..56 south),
z = height in sprite px (equator z = 0; top +13, bottom -10). Blender X = (u-24)/12, Y = (28-v)/12.
Cut into the four 24x28 pieces with common.split_assembly (layout = piece centre - (24, 28)).

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshe-229.py
or: blender --background --factory-startup --python assembly-newshe-229.py -- [--views DIR] [--no-bake]
[--glb OUT.glb (review GLB with the pieces placed in the pod, no game export)]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets/blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402  (read only: the sprite's inner mask, D74)
import usp_talon as T  # noqa: E402  (read only: pchip)

HERE = Path(__file__).resolve().parent
NAME = "assembly-newshe-229"
ROOT = common.repo_root(__file__)
PX = 1 / 12
PIECES = [("newshe-191", 0, 0), ("newshe-193", 24, 0), ("newshe-229", 0, 28), ("newshe-231", 24, 28)]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

# ---------------------------------------------------------------- shape constants --------------
H_TOP = 13.0      # dome height above the equator
H_BOT = 10.0      # round underside depth below it
P_TOP = 2.35      # superellipse exponent of the dome profile (2 = ellipse; a bit fuller)
P_BOT = 2.1
S_HULL = 0.972    # hull radius at the equator / belt radius (the belt stands 0.45 px proud)
BELT = (-1.7, 0.5)  # belt band z range (full radius)
BELT_CH = 0.22    # belt chamfer
GROW = 0.0        # plan offset (px) on the traced inner mask
HARM = 5          # Fourier terms kept of the traced outline: round, not lumpy
LAT_Z = 5.6       # latitude panel line on the dome
GROOVE = 0.38     # panel-line depth (px)
SEAMS = [(-18, 0.9, 10.5), (-62, 0.9, 10.5), (-108, 0.9, 10.5), (-150, 0.9, 9.0), (28, 0.9, 9.5)]
NOTCHES = list(range(0, 360, 24))
HATCH = (218.0, 240.0, 0.64, 0.84)  # access hatch on the SW flank: angle range (deg), rho/R range
BEZEL_W = 1.1     # bezel top width (px)
BEZEL_H = 0.9     # bezel height above the hull
GLASS_LIFT = 0.65  # glass edge height above the hull
GLASS_BULGE = 1.5  # extra bulge at the cap's middle

# key: (palette index, metallic, roughness, emission strength)
MATS = {
    "hull": (115, 0.4, 0.24, 0),
    "belt": (115, 0.5, 0.36, 0),
    "bezel": (1, 0.45, 0.35, 0),
    "glass": (1, 0.1, 0.06, 0),
    "socket": (115, 0.55, 0.3, 0),
    "socket2": (115, 0.55, 0.3, 0),
    "ring": (123, 0.0, 0.4, 1.1),
    "ring2": (121, 0.0, 0.4, 1.1),
    "core": (127, 0.0, 0.3, 4.0),
    "core2": (126, 0.0, 0.3, 4.0),
    "stud_a": (114, 0.2, 0.3, 0.5),
    "stud_b": (115, 0.2, 0.3, 0.5),
    "nozzle": (113, 0.55, 0.4, 0),
    "glow": (121, 0.0, 0.5, 2.0),
}
MKEYS = list(MATS)
NO_BAKE = {"glass", "ring", "ring2", "core", "core2", "glow", "stud_a", "stud_b"}


def P(u, v, z):
    return Vector(((u - 24) * PX, (28 - v) * PX, z * PX))


# ---------------------------------------------------------------- sprite tracing ---------------
def sprite():
    """One pod: the four pieces' frames in its 48 x 56 block (SM.load(NAME) composes the whole
    assemblyLayout, several overlapping pods, which is not one pod's grid)."""
    import json
    idx = [[-1] * 48 for _ in range(56)]
    colors = {}
    for name, c0, r0 in PIECES:
        d = json.loads((WT / "reference" / "models" / name / "sprite.json").read_text())
        colors.update({int(k): tuple(v) for k, v in d["colors"].items()})
        for r, row in enumerate(d["frames"][0]["pixels"]):
            for c, v in enumerate(int(x) for x in row.split()):
                if v >= 0:
                    idx[r0 + r][c0 + c] = v
    return idx, colors, SM.masks(idx, colors)


def centroid(mask):
    n = su = sv = 0
    for r, row in enumerate(mask):
        for c, b in enumerate(row):
            if b:
                n += 1
                su += c + 0.5
                sv += r + 0.5
    return su / n, sv / n


def polar_trace(mask, cu, cv, n=360, harmonics=7):
    """Radius of the mask's edge round (cu, cv) per angle (xy angle: east 0, north 90), low-passed
    to `harmonics` Fourier terms. Returns f(theta_rad) -> r (px)."""
    h, w = len(mask), len(mask[0])
    raw = []
    for i in range(n):
        a = 2 * math.pi * i / n
        du, dv = math.cos(a), -math.sin(a)
        t, last = 0.0, 0.0
        while t < 40:
            u, v = cu + du * t, cv + dv * t
            c, r = int(math.floor(u)), int(math.floor(v))
            if 0 <= r < h and 0 <= c < w and mask[r][c]:
                last = t
            elif t > 2:
                break
            t += 0.02
        raw.append(last)
    coef = []
    for k in range(harmonics + 1):
        a = sum(raw[i] * math.cos(2 * math.pi * k * i / n) for i in range(n)) * 2 / n
        b = sum(raw[i] * math.sin(2 * math.pi * k * i / n) for i in range(n)) * 2 / n
        coef.append((a / (2 if k == 0 else 1), b))

    def f(theta):
        x = theta * n / (2 * math.pi)
        return sum(a * math.cos(2 * math.pi * k * x / n) + b * math.sin(2 * math.pi * k * x / n)
                   for k, (a, b) in enumerate(coef))
    return f


def visor_mask(idx, border):
    """The dark glass region: palette 1/64 pixels off the outline ring, holes (lenses, studs)
    filled."""
    h, w = len(idx), len(idx[0])
    dark = [[idx[r][c] in (1, 64) and not border[r][c] for c in range(w)] for r in range(h)]
    # keep the biggest 4-connected island
    seen, best = set(), []
    for r in range(h):
        for c in range(w):
            if dark[r][c] and (r, c) not in seen:
                stack, isl = [(r, c)], []
                seen.add((r, c))
                while stack:
                    y, x = stack.pop()
                    isl.append((y, x))
                    for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= yy < h and 0 <= xx < w and dark[yy][xx] and (yy, xx) not in seen:
                            seen.add((yy, xx))
                            stack.append((yy, xx))
                if len(isl) > len(best):
                    best = isl
    keep = set(best)
    # fill holes: flood the outside from the picture's edge
    out = set()
    stack = [(r, c) for r in range(h) for c in (0, w - 1)] + [(r, c) for r in (0, h - 1) for c in range(w)]
    while stack:
        y, x = stack.pop()
        if (y, x) in out or (y, x) in keep:
            continue
        out.add((y, x))
        for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= yy < h and 0 <= xx < w:
                stack.append((yy, xx))
    return [[(r, c) not in out for c in range(w)] for r in range(h)]


# ---------------------------------------------------------------- hull profile -----------------
def s_top(z):
    z = min(max(z, 0.0), H_TOP)
    return S_HULL * (1 - (z / H_TOP) ** P_TOP) ** (1 / P_TOP)


def s_bot(z):
    z = min(max(-z, 0.0), H_BOT)
    return S_HULL * (1 - (z / H_BOT) ** P_BOT) ** (1 / P_BOT)


def z_of_s_top(s):
    """Inverse of s_top on the dome."""
    s = min(max(s, 0.0), S_HULL)
    return H_TOP * (1 - (s / S_HULL) ** P_TOP) ** (1 / P_TOP)


class Pod:
    def __init__(self, idx, colors, m):
        self.idx, self.colors, self.m = idx, colors, m
        self.cu, self.cv = centroid(m["inner"])
        tr = polar_trace(m["inner"], self.cu, self.cv, harmonics=HARM)
        self.R = lambda th: tr(th) + GROW
        vm = visor_mask(idx, m["border"])
        self.vmask = vm
        self.vu, self.vv = centroid(vm)
        vt = polar_trace(vm, self.vu, self.vv, harmonics=7)
        self.Rv = vt

    def polar(self, u, v):
        du, dv = u - self.cu, v - self.cv
        return math.hypot(du, dv), math.atan2(-dv, du)

    def hull_z(self, u, v):
        rho, th = self.polar(u, v)
        return z_of_s_top(rho / self.R(th))

    def vfrac(self, u, v):
        du, dv = u - self.vu, v - self.vv
        th = math.atan2(-dv, du)
        return math.hypot(du, dv) / self.Rv(th), th

    def glass_z(self, u, v):
        f, _ = self.vfrac(u, v)
        f0 = self.glass_f0
        k = min(f / f0, 1.0)
        return self.hull_z(u, v) + GLASS_LIFT + GLASS_BULGE * (1 - k * k)


# ---------------------------------------------------------------- builder ----------------------
class Builder:
    def __init__(self):
        self.bm = bmesh.new()
        self.pid = self.bm.faces.layers.int.new("part")
        self.parts = []  # (name, matkey)

    def part(self, name, mk):
        self.parts.append((name, mk))
        return len(self.parts) - 1

    def face(self, vs, pid, smooth=True):
        f = self.bm.faces.new(vs)
        f[self.pid] = pid
        f.material_index = MKEYS.index(self.parts[pid][1])
        f.smooth = smooth
        return f

    def ring(self, pts):
        return [self.bm.verts.new(P(*p)) for p in pts]

    def bridge(self, a, b, pid, smooth=True, flip=False):
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            q = [a[i], a[j], b[j], b[i]]
            self.face(q[::-1] if flip else q, pid, smooth)

    def fan(self, ring, apex, pid, smooth=True, flip=False):
        c = self.bm.verts.new(P(*apex))
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            t = [ring[i], ring[j], c]
            self.face(t[::-1] if flip else t, pid, smooth)


def angles(pod):
    """xy angles of the body's columns: a uniform set plus three tight samples per seam / notch."""
    base = [2 * math.pi * i / 60 for i in range(60)]
    extra = []
    tags = {}
    for deg, z0, z1 in SEAMS:
        th = math.radians(deg) % (2 * math.pi)
        d = 0.5 / pod.R(th)
        extra += [th - d, th, th + d]
        tags[round(th, 6)] = ("seam", z0, z1)
    for deg in NOTCHES:
        th = math.radians(deg + 7) % (2 * math.pi)
        d = 0.45 / pod.R(th)
        extra += [th - d, th, th + d]
        tags[round(th, 6)] = ("notch",)
    allth = sorted(set(round(t % (2 * math.pi), 6) for t in base + extra))
    # drop base samples crowding the tight ones
    keep = []
    special = sorted(round(t % (2 * math.pi), 6) for t in extra)
    for t in allth:
        if t in special:
            keep.append(t)
            continue
        if min(abs((t - s + math.pi) % (2 * math.pi) - math.pi) for s in special) < 0.035:
            continue
        keep.append(t)
    return keep, tags


def build_hull(B, pod):
    hull = B.part("hull", "hull")
    belt = B.part("belt", "belt")
    ths, tags = angles(pod)
    # z stations: (z, s, kind)
    st = []
    nb = 7
    for i in range(1, nb):
        phi = -math.pi / 2 + (math.pi / 2) * i / nb
        z = -H_BOT * abs(math.sin(phi)) ** (2 / P_BOT)
        if z < BELT[0] - 0.6:
            st.append((z, s_bot(z), "hull"))
    z0, z1 = BELT
    st += [(z0 - 0.35, s_bot(z0 - 0.35), "hull"),
           (z0 - 0.05, 1.0 - BELT_CH / 17, "belt"), (z0 + BELT_CH, 1.0, "belt"),
           (z0 + 0.5 * (z1 - z0), 1.0, "belt"),
           (z1 - BELT_CH, 1.0, "belt"), (z1 + 0.05, 1.0 - BELT_CH / 17, "belt"),
           (z1 + 0.35, s_top(z1 + 0.35), "hull")]
    nt = 10
    tops = []
    for i in range(1, nt):
        phi = (math.pi / 2) * i / nt
        z = H_TOP * math.sin(phi) ** (2 / P_TOP)
        if z > z1 + 0.9:
            tops.append(z)
    tops = [z for z in tops if abs(z - LAT_Z) > 0.7]
    tops += [LAT_Z - 0.35, LAT_Z, LAT_Z + 0.35]
    for z in sorted(tops):
        st.append((z, s_top(z), "lat" if z == LAT_Z else "hull"))
    st.sort()
    rings = []
    kinds = []
    for z, s, kind in st:
        pts = []
        for th in ths:
            r = s * pod.R(th)
            tag = tags.get(round(th, 6))
            if kind == "lat":
                r -= GROOVE
            if tag and tag[0] == "seam" and tag[1] <= z <= tag[2] and kind != "belt":
                r -= GROOVE
            if tag and tag[0] == "notch" and kind == "belt" and s >= 0.999:
                r -= GROOVE * 0.9
            pts.append((pod.cu + r * math.cos(th), pod.cv - r * math.sin(th), z))
        rings.append(B.ring(pts))
        kinds.append(kind)
    for i in range(len(rings) - 1):
        pid = belt if (kinds[i] == "belt" and kinds[i + 1] == "belt") else hull
        B.bridge(rings[i], rings[i + 1], pid)
    B.fan(rings[0], (pod.cu, pod.cv, -H_BOT), hull, flip=True)
    B.fan(rings[-1], (pod.cu, pod.cv, H_TOP), hull)


def conform_rings(B, pod, centre, rad_of, layers, zf, n=64):
    """Concentric rings round `centre` (u, v): layers = [(radius scale or px, dz, matkey)], each
    vertex at height zf(u, v) + dz. rad_of(theta, r) -> plan radius. Returns the rings."""
    rings = []
    for r, dz in layers:
        pts = []
        for i in range(n):
            th = 2 * math.pi * i / n
            rr = rad_of(th, r)
            u, v = centre[0] + rr * math.cos(th), centre[1] - rr * math.sin(th)
            pts.append((u, v, zf(u, v) + dz))
        rings.append(B.ring(pts))
    return rings


def build_visor(B, pod):
    bez = B.part("bezel", "bezel")
    gl = B.part("glass", "glass")
    c = (pod.vu, pod.vv)

    # clip the cap's plan inside the dome (frac of the body radius <= 0.93)
    def rad(th, f):
        rv = pod.Rv(th)
        # distance along the ray from the visor centre to frac 0.93 of the body
        lo, hi = 0.0, rv
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            u, v = c[0] + mid * math.cos(th), c[1] - mid * math.sin(th)
            rho, tb = pod.polar(u, v)
            if rho / pod.R(tb) <= 0.93:
                lo = mid
            else:
                hi = mid
        rv = min(rv, lo)
        if f >= 0:
            return rv * f
        return max(rv + f, 0.0)  # f < 0: px in from the edge
    pod.vrad = rad
    w = BEZEL_W
    layers = [(1.0, -0.5), (1.0, BEZEL_H - 0.2), (-0.25, BEZEL_H), (-w, BEZEL_H), (-w - 0.2, BEZEL_H - 0.2),
              (-w - 0.35, GLASS_LIFT)]
    pod.glass_f0 = 1.0  # set below once the glass edge fraction is known
    hz = pod.hull_z
    rings = conform_rings(B, pod, c, rad, layers, hz, n=60)
    for i in range(len(rings) - 1):
        B.bridge(rings[i], rings[i + 1], bez)
    # glass: f fractions of the glass edge radius
    def gedge(th, f):
        return rad(th, -w - 0.35) * f
    # glass_z uses vfrac (plan / Rv), so measure f0 as the glass edge's typical fraction
    pod.glass_f0 = 0.0
    fr = []
    for i in range(36):
        th = 2 * math.pi * i / 36
        fr.append(gedge(th, 1.0) / pod.Rv(th))
    pod.glass_f0 = sum(fr) / len(fr)
    gr = [rings[-1]]
    for f in (0.9, 0.75, 0.58, 0.4, 0.22):
        def gz(u, v, f=f):
            return pod.hull_z(u, v) + GLASS_LIFT + GLASS_BULGE * (1 - f * f)
        gr += conform_rings(B, pod, c, gedge, [(f, 0.0)], gz, n=60)
    for i in range(len(gr) - 1):
        B.bridge(gr[i], gr[i + 1], gl)
    cz = pod.hull_z(*c) + GLASS_LIFT + GLASS_BULGE
    B.fan(gr[-1], (c[0], c[1], cz), gl)

    def glass_z(u, v):
        f, th = pod.vfrac(u, v)
        e = gedge(th, 1.0) / pod.Rv(th)
        k = min(f / e, 1.0)
        return pod.hull_z(u, v) + GLASS_LIFT + GLASS_BULGE * (1 - k * k)
    pod.gz = glass_z


def build_lens(B, pod, name, c, r_out, r_ring, r_core, dome, sock="socket", collar=0.85, n=32,
               ring="ring", core="core"):
    """A lamp in a machined collar: collar (socket pal), a recessed lit cup (ring pal, glowing),
    a domed white-hot lens (core pal)."""
    ps = B.part(f"{name}_socket", sock)
    pr = B.part(f"{name}_ring", ring)
    pc = B.part(f"{name}_core", core)
    gz = pod.gz

    def rad(th, r):
        return r
    col = [(r_out, -0.5), (r_out, collar - 0.15), (r_out - 0.18, collar), (r_ring + 0.15, collar),
           (r_ring, collar - 0.15)]
    rings = conform_rings(B, pod, c, rad, col, gz, n=n)
    for i in range(len(rings) - 1):
        B.bridge(rings[i], rings[i + 1], ps)
    cup = conform_rings(B, pod, c, rad, [(r_core, 0.15)], gz, n=n)
    B.bridge(rings[-1], cup[0], pr)
    dr = [cup[0]]
    for k in (0.85, 0.6, 0.32):
        t = math.sqrt(1 - k * k)
        dr += conform_rings(B, pod, c, rad, [(r_core * k, 0.15 + dome * t)], gz, n=n)
    for i in range(len(dr) - 1):
        B.bridge(dr[i], dr[i + 1], pc)
    B.fan(dr[-1], (c[0], c[1], gz(*c) + 0.15 + dome), pc)


def build_stud(B, pod, name, c, r, h, mk, n=24):
    pid = B.part(name, mk)
    gz = pod.gz

    def rad(th, rr):
        return rr
    lay = [(r, -0.4), (r, 0.25)]
    for k in (0.9, 0.65, 0.35):
        lay.append((r * k, 0.25 + h * math.sqrt(1 - k * k)))
    rings = conform_rings(B, pod, c, rad, lay, gz, n=n)
    for i in range(len(rings) - 1):
        B.bridge(rings[i], rings[i + 1], pid)
    B.fan(rings[-1], (c[0], c[1], gz(*c) + 0.25 + h), pid)


def build_thruster(B, pod, deg, z, name, n=20):
    """A small bell on the rear lower hull, pointing north (backwards), hidden under the belt."""
    pn = B.part(f"{name}_bell", "nozzle")
    pg = B.part(f"{name}_glow", "glow")
    th = math.radians(deg)
    rr = s_bot(z) * pod.R(th)
    u0, v0 = pod.cu + (rr - 1.4) * math.cos(th), pod.cv - (rr - 1.4) * math.sin(th)
    # axis: north (-v), length to stay inside the belt plan
    lim = pod.R(th) - 0.35

    def ring(dist, rad, zc):
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n
            pts.append((u0 + rad * math.cos(a), v0 - dist, zc + rad * math.sin(a)))
        return B.ring(pts)
    # find reach: the bell lip's plan distance from the centre stays < lim
    reach = 0.0
    while reach < 4:
        u, v = u0, v0 - (reach + 0.1)
        if math.hypot(u - pod.cu, v - pod.cv) + 0.2 > lim:
            break
        reach += 0.1
    rs = [ring(0.0, 1.0, z), ring(reach * 0.55, 1.05, z), ring(reach, 1.35, z), ring(reach, 1.05, z),
          ring(reach - 0.6, 0.8, z)]
    for i in range(len(rs) - 1):
        B.bridge(rs[i], rs[i + 1], pn, flip=True)
    B.fan(rs[-1], (u0, v0 - (reach - 0.6), z), pg, flip=True)


def build_hatch(B, pod):
    """A shallow raised, chamfered access plate on the SW flank, conformal to the dome (about
    GROOVE high, so the top view and the lit crescent keep their reading)."""
    pid = B.part("hatch", "hull")
    a0, a1, r0, r1 = HATCH
    a0, a1 = math.radians(a0), math.radians(a1)
    n = 8

    def loop(ins, lift):
        aa0, aa1 = a0 + ins * (a1 - a0) * 0.18, a1 - ins * (a1 - a0) * 0.18
        rr0, rr1 = r0 + ins * (r1 - r0) * 0.28, r1 - ins * (r1 - r0) * 0.28
        edge = [(aa0 + (aa1 - aa0) * i / n, rr0) for i in range(n + 1)]
        edge += [(aa1, rr0 + (rr1 - rr0) * i / 3) for i in range(1, 4)]
        edge += [(aa1 - (aa1 - aa0) * i / n, rr1) for i in range(1, n + 1)]
        edge += [(aa0, rr1 - (rr1 - rr0) * i / 3) for i in range(1, 3)]
        pts = []
        for a, rho in edge:
            r = rho * pod.R(a)
            u, v = pod.cu + r * math.cos(a), pod.cv - r * math.sin(a)
            pts.append((u, v, pod.hull_z(u, v) + lift))
        return B.ring(pts)

    rings = [loop(0.0, -0.3), loop(0.0, 0.25), loop(1.0, 0.4)]
    am, rm = (a0 + a1) / 2, (r0 + r1) / 2
    r = rm * pod.R(am)
    u, v = pod.cu + r * math.cos(am), pod.cv - r * math.sin(am)
    for i in range(len(rings) - 1):
        B.bridge(rings[i], rings[i + 1], pid, smooth=False)
    B.fan(rings[-1], (u, v, pod.hull_z(u, v) + 0.4), pid, smooth=False)


def build(sp, coll):
    idx, colors, m = sp
    pod = Pod(idx, colors, m)
    B = Builder()
    build_hull(B, pod)
    build_hatch(B, pod)
    build_visor(B, pod)
    build_lens(B, pod, "lens_big", (18.9, 22.6), 5.2, 4.2, 3.3, 1.1, sock="socket", collar=1.0)
    build_lens(B, pod, "lens_small", (26.4, 28.7), 3.0, 2.25, 1.45, 0.7, sock="socket2", collar=0.8, n=24,
               ring="ring2", core="core2")
    build_stud(B, pod, "stud_a", (25.0, 16.9), 1.8, 0.75, "stud_a")
    build_stud(B, pod, "stud_b", (28.9, 21.0), 2.1, 0.85, "stud_b")
    build_thruster(B, pod, 90 + 32, -3.6, "thr_l")
    build_thruster(B, pod, 90 - 32, -3.6, "thr_r")
    bm = B.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    sprite_d = {"name": NAME, "colors": {str(k): list(v) for k, v in colors.items()}}
    mats = [common.palette_material(sprite_d, MATS[k][0], f"nshe229b_{k}", metallic=MATS[k][1],
                                    roughness=MATS[k][2], emission_strength=MATS[k][3]) for k in MKEYS]
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    print(f"centre body {pod.cu:.2f},{pod.cv:.2f} visor {pod.vu:.2f},{pod.vv:.2f} glass_f0 {pod.glass_f0:.3f}")
    return obj, B.parts, pod


# ---------------------------------------------------------------- outline shell split ----------
def split_shell(shell, layout, coll):
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(shell.data)
        bmesh.ops.transform(bm, matrix=shell.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            cut = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                         plane_no=no, clear_outer=True)
            edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            # left open (no cap): a capped cut would outline the seam between pieces
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + "_outline")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(shell.data.materials[0])
        me.shade_smooth()
        o = bpy.data.objects.new(name + "_outline", me)
        coll.objects.link(o)
        o["tyrian_outline"] = True
        out[name] = o
    return out


# ---------------------------------------------------------------- views -----------------------
def setup_ids(obj, parts):
    me = obj.data
    pid = me.attributes["part"].data
    attr = me.color_attributes.new("ids", "FLOAT_COLOR", "CORNER")

    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    for poly in me.polygons:
        k = pid[poly.index].value
        pal = MATS[parts[k][1]][0]
        col = (lin(4 * (k + 1)), lin(pal), 0.0, 1.0)
        for li in poly.loop_indices:
            attr.data[li].color = col
    me.color_attributes.active_color = attr


def camera(scene, name, rot_deg, loc, ortho=4.4):
    data = bpy.data.cameras.new(name)
    data.type = "ORTHO"
    data.ortho_scale = ortho
    data.clip_end = 200
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.rotation_euler = [math.radians(a) for a in rot_deg]
    cam.location = loc
    return cam


def look_cam(scene, name, rot_deg, dist=20, target=(0, 0, 0.25), ortho=4.4):
    from mathutils import Euler
    e = Euler([math.radians(a) for a in rot_deg])
    d = Vector((0, 0, -1))
    d.rotate(e)
    return camera(scene, name, rot_deg, Vector(target) - d * dist, ortho)


def gpu(scene):
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        scene.cycles.device = "GPU"
    except Exception as err:
        print("no gpu", err)


def render_views(obj, parts, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    setup_ids(obj, parts)
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    sh = scene.display.shading
    sh.light = "FLAT"
    try:
        sh.color_type = "VERTEX"
    except TypeError:
        sh.color_type = "ATTRIBUTE"
    sh.show_cavity = False
    sh.show_object_outline = False
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 480, 560
    scene.render.resolution_percentage = 100
    top = camera(scene, "top", (0, 0, 0), (0, 0, 10), ortho=56 / 12)
    scene.camera = top
    scene.render.filepath = str(out_dir / "top_ids.png")
    bpy.ops.render.render(write_still=True)
    if "--top-only" in argv:
        return
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = 40
    scene.cycles.use_denoising = True
    gpu(scene)
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.32, 0.36, 0.42, 1)
    bg.inputs[1].default_value = 0.8
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    sun.data.angle = math.radians(8)
    sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(-30))
    scene.collection.objects.link(sun)
    views = {
        "top": ((0, 0, 0), 480, 560, 56 / 12),
        "game": ((15, 0, 0), 600, 560, 3.6),
        "steep": ((32, 0, 0), 600, 560, 3.6),
        "side": ((90, 0, 90), 600, 460, 3.6),
        "front": ((90, 0, 0), 600, 460, 3.6),
        "rear": ((90, 0, 180), 600, 460, 3.6),
        "q_se": ((55, 0, 40), 600, 520, 3.6),
        "q_nw": ((55, 0, 220), 600, 520, 3.6),
        "q_low": ((78, 0, -35), 600, 460, 3.6),
        "under": ((180, 0, 0), 480, 560, 56 / 12),
    }
    for name, (rot, w, h, osc) in views.items():
        cam = look_cam(scene, "cam_" + name, rot, ortho=osc)
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = w, h
        scene.render.filepath = str(out_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    # game size: 4 screen px per sprite px (1080p frame HUD ~5.4)
    cam = look_cam(scene, "cam_small", (15, 0, 0), ortho=3.6)
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = 172, 160
    scene.render.filepath = str(out_dir / "game_small.png")
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- AO / roughness bake ---------
def bake_maps(obj, out_dir, size=1024, samples=64):
    """As the ships (D50/D65): Smart UV, bake a grey colour multiplier (occlusion at two scales and
    a lift on bevelled edges) and a roughness/metalness map; Base Color = map x palette colour.
    No concept projection."""
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    gpu(scene)
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
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new("nshe229b_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("nshe229b_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
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
        L = nt.links.new
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def mth(op, a, b=None):
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
        edge = mth("MINIMUM", mth("MULTIPLY", mth("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = mth("MULTIPLY", mth("POWER", ao_s.outputs["AO"], 0.8),
                   mth("ADD", 0.65, mth("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        comb = node("ShaderNodeCombineColor")
        if mode == "colour":
            v = mth("MINIMUM", mth("ADD", mth("ADD", 0.48, mth("MULTIPLY", occl, 0.62)), mth("MULTIPLY", edge, 0.2)), 1.0)
            for k in range(3):
                L(v, comb.inputs[k])
        else:
            r = mth("ADD", rough, mth("SUBTRACT", mth("MULTIPLY", mth("SUBTRACT", 1.0, occl), 0.3),
                                      mth("MULTIPLY", edge, 0.16)))
            r = mth("MAXIMUM", mth("MINIMUM", r, 1.0), 0.05)
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
        tmps = {m.name: bake_shader(m, mode) for m in mats}
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
    for key, m in zip(MKEYS, mats):
        if key in NO_BAKE:
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


def smooth_by_angle(obj, deg=38):
    """Smooth shading, hard where faces meet at more than `deg` (belt chamfers, collars)."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    for e in bm.edges:
        if len(e.link_faces) == 2:
            a, b = e.link_faces
            if a.normal.angle(b.normal, 0.0) > math.radians(deg) or a.material_index != b.material_index:
                e.smooth = False
    bm.to_mesh(me)
    bm.free()


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sp = sprite()
    coll = common.reset_collection(NAME)
    obj, parts, pod = build(sp, coll)
    smooth_by_angle(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}_B: {len(obj.data.polygons)} faces, {tris} tris, top z {max(v.co.z for v in obj.data.vertices) * 12:.2f} px")
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    import json
    if views:
        views.mkdir(parents=True, exist_ok=True)
        json.dump({"parts": [{"id": i, "name": n, "mat": mk, "pal": MATS[mk][0]} for i, (n, mk) in enumerate(parts)],
                   "tris": tris}, open(views / "parts.json", "w"), indent=1)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="nshe229b_bake_"))
        fmt = "WEBP"
    # Outline shell (D51/D90/D118): from a sealed copy of the whole pod, before the cut.
    shell = common.outline_shell(obj, coll, faces=1600)
    shell.hide_render = True
    print("SHELL faces", len(shell.data.polygons), [round(v,3) for v in shell.dimensions])
    layout = [(name, c0 + 12 - 24, r0 + 14 - 28) for name, c0, r0 in PIECES]
    pieces = common.split_assembly(obj, layout)
    shells = split_shell(shell, layout, coll)
    review = "--glb" in argv
    objs = []
    for name, cx, cy in layout:
        p, s = pieces[name], shells[name]
        p.hide_render = s.hide_render = True  # the views render the whole pod, not the pieces
        print(f"piece {name}: {sum(len(q.vertices) - 2 for q in p.data.polygons)} tris, shell {len(s.data.polygons)}")
        if review:
            p.location = s.location = (cx * PX, -cy * PX, 0.0)
            objs += [p, s]
        else:
            # the game contract: one model per piece at its own origin, its sprites registered
            data = common.load_sprite(ROOT, name)
            common.export_sprite_model(ROOT, [p, s], f"enemies/{name}", data["sprites"], image_format=fmt)
    if review:
        glb = Path(argv[argv.index("--glb") + 1])
        common.export_glb(objs, glb, image_format=fmt)
        print("exported", glb)
    if views:
        render_views(obj, parts, views)


if __name__ == "__main__":
    main()
