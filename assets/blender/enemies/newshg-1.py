"""Molten rock for newshg-1: the tumbling molten rock (newshg.shp frames 1-17 and 39-47, 24x28 px).

WHAT IT IS: a falling lava meteor. It falls 5-6 px/tick from the sky layer in GYGES and is swept
sideways in MISTAKES: a free-flying ball of rock, closed all round, no base.

Each of the 14 tumble frames is its own closed rock (common.frame_part), lofted from that frame's
inner mask (inside its ink ring, D74): a round dome on top and a matching dome underneath, as tall
as it is wide (a ball). The sprite's own colours are laid on the top first, each region's edge a
smooth curve (relax). Then the ball is cleaved into irregular flat plates (plate_cuts: ~40-55
planes, each 0.03-0.05 under the body's furthest point its way, shallower facing sideways so the
top-down outline stays the sprite's), pressed straight down on the top so the sprite's colours stay
put; neighbouring plates meet in creases cut into shallow V grooves (grooves): rock, whose lit and
turned-away faces and dark crevices are its shading. The underside gets plates but no grooves.
Lava seams on the flanks are branching cracks (Cracks) that wander down from the hot rim: each band
edge (lava 123 / glow 120 / hot rock 118 / crust) is knifed into the surface as its own line
(cut_cracks), so the bands have clean edges, and the channel floor is let down (crack_channels).
The grey-pink cooled flakes stand a hair proud; the white-hot blister at the upper left (the same on
every frame, so it is the hottest side, not a bump) is near flush with the crust and glows.
Colours: one palette material per band of the sprite's own red ramp (crust 115, hot rock 118,
glow 120, lava 123, white-hot 127) and the flakes' own indices (71 salmon, 27 tan-grey); the crust
is dull (roughness 1, no emission). AO/roughness bake ("bake": "model", no concept projection,
D50/D65) of all frames into one atlas, the crust's texels darkened (darken_crust) so it reads dark
maroon under the game's light. Outline shell per frame from a sealed copy, after the bake (D90/D118).

Run: blender --background --python assets/blender/enemies/newshg-1.py [-- --no-bake] [--preview out.png]
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector, noise
from mathutils.bvhtree import BVHTree

WT = next(p for p in Path(__file__).resolve().parents if (p / "package.json").exists())
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402

NAME = "newshg-1"
D90_SHELL = {"voxel": 0.03, "inside": 0.004, "faces": 450, "smooth": 8}

H_TOP = 0.70      # dome height above the waist (units; 12 sprite px = 1 unit; the rock is ~17 px wide)
H_BOT = 0.68      # depth of the underside below the waist: with H_TOP a ball, as tall as it is wide
SUMMIT = (10.6, 11.6)   # sprite px (edges): where the top peaks, a little up-left of the centre
BLISTER = (9.0, 8.5)    # centre of the white-hot blister (cols 7-10, rows 7-9 on every frame)
BLISTER_R = 2.1         # px
BLISTER_H = 0.006       # units: nearly flush; it is the hottest side, not a bump
SEAM_DEPTH = 0.038      # units the lava channels sit below the crust
FLAKE_H = 0.016         # units the cooled flakes stand proud
SECTORS, RINGS_TOP, RINGS_BOT = 72, 15, 7
GROW = {41: 0.12}     # outline grow per frame (sprite px; default 0.18): 41's top/right ink is thin
SMOOTH = {41: 1}      # outline smoothing passes per frame (default 2): 41 keeps its one-pixel tips
# the crust: irregular flat plates (the body cleaved by planes), split by grooves along their
# creases; the lava seams on the flanks are branching cracks knifed into it
PLATES = 42                 # cleaving planes spread over the whole ball (then more on bare patches)
PLATE_DEPTH = (0.03, 0.05)  # units each plane sits under the body's furthest point its way
GROOVE_W = 0.014            # units: half-width of the groove along a plain crease
GROOVE_D = 0.014            # units: its floor below the plates
CRACK_W = 0.065             # units: half-width of a lava channel at its widest
SIDE_SEAM_DEPTH = 0.03      # units the lava channel floor sits below the plates
CRUST_DARK = 0.62           # the crust's share of the baked colour multiplier (darken_crust)
UNDER_Z = -0.45             # below this (sin of elevation) is underside: no grooves, no infill plates
SIDE_CUT = 0.45             # depth share of a plane facing straight out sideways
CRACK_BANDS = (0.36, 0.7, 1.0)     # band edges across a channel (fractions of its half-width)
SIDE_TOP = math.radians(30)   # the cracks start just under this elevation (the sprite rules above)

# material slots
CRUST, HOT, GLOW, LAVA, WHITE, FLAKE, FLAKE2 = range(7)
SALMON = set(range(67, 80))
GREYS = {4, 8, 13, 20, 23, 24, 25, 26, 27, 28, 29, 92, 94, 165, 168, 171, 173}


# --- one frame's sprite --------------------------------------------------------------------------

class FrameGrid:
    def __init__(self, index):
        idx, colors = SM.load(NAME, frame=index, ref=WT / "reference" / "models")
        self.idx = idx
        self.h, self.w = len(idx), len(idx[0])
        self.inner = SM.masks(idx, colors)["inner"]

    def x(self, u):
        return (u - self.w / 2) / 12

    def y(self, v):
        return (self.h / 2 - v) / 12

    def uv(self, x, y):
        return x * 12 + self.w / 2, self.h / 2 - y * 12

    def val(self, c, r):
        if 0 <= r < self.h and 0 <= c < self.w:
            return 1.0 if self.inner[r][c] else 0.0
        return 0.0

    def field(self, u, v):
        a, b = u - 0.5, v - 0.5
        c0, r0 = math.floor(a), math.floor(b)
        fa, fb = a - c0, b - r0
        return ((1 - fa) * (1 - fb) * self.val(c0, r0) + fa * (1 - fb) * self.val(c0 + 1, r0)
                + (1 - fa) * fb * self.val(c0, r0 + 1) + fa * fb * self.val(c0 + 1, r0 + 1))

    def outline(self, centre, steps=96, grow=0.0, smooth=2):
        """Radii of the inner mask's 0.5 contour on `steps` rays from `centre` (sprite px)."""
        cu, cv = centre
        radii = []
        for k in range(steps):
            a = 2 * math.pi * k / steps
            du, dv = math.cos(a), -math.sin(a)
            # the LAST exit along the ray: a pinhole of ink inside the rock (frame 41) is crossed
            t, last, edge = 0.0, 1.0, 0.0
            while t < 16:
                f = self.field(cu + du * t, cv + dv * t)
                if f < 0.5 <= last:
                    edge = t - 0.02 * (0.5 - f) / max(1e-6, last - f)
                last = f
                t += 0.02
            radii.append(edge + grow)
        for _ in range(smooth):
            radii = [(radii[k - 1] + 2 * radii[k] + radii[(k + 1) % steps]) / 4 for k in range(steps)]
        return cu, cv, radii

    # --- the sprite's colour as fields --------------------------------------------------------

    def pix(self, c, r):
        if 0 <= r < self.h and 0 <= c < self.w:
            return self.idx[r][c]
        return -1

    def _bilinear(self, u, v, value):
        a, b = u - 0.5, v - 0.5
        c0, r0 = math.floor(a), math.floor(b)
        fa, fb = a - c0, b - r0
        return ((1 - fa) * (1 - fb) * value(c0, r0) + fa * (1 - fb) * value(c0 + 1, r0)
                + (1 - fa) * fb * value(c0, r0 + 1) + fa * fb * value(c0 + 1, r0 + 1))

    def _ramp_px(self, c, r):
        i = self.pix(c, r)
        if 112 <= i <= 127:
            return float(i)
        return 113.0  # flakes, ink specks and the outside read as crust

    def _flake_px(self, c, r):
        i = self.pix(c, r)
        return 1.0 if (i in SALMON or i in GREYS) else 0.0

    def ramp(self, u, v):
        """The sprite's red ramp index as a smooth field (bilinear, lightly blurred)."""
        e = 0.3
        return (2 * self._bilinear(u, v, self._ramp_px) + self._bilinear(u + e, v, self._ramp_px)
                + self._bilinear(u - e, v, self._ramp_px) + self._bilinear(u, v + e, self._ramp_px)
                + self._bilinear(u, v - e, self._ramp_px)) / 6

    def level(self, u, v):
        """Ramp field with the blister kept round: the white-hot dome is the same on every frame."""
        return max(self.ramp(u, v), 113 + 14.5 * blister_w(u, v))

    def flake_field(self, u, v):
        e = 0.25
        return (2 * self._bilinear(u, v, self._flake_px) + self._bilinear(u + e, v, self._flake_px)
                + self._bilinear(u - e, v, self._flake_px) + self._bilinear(u, v + e, self._flake_px)
                + self._bilinear(u, v - e, self._flake_px)) / 6

    def flake_kind(self, u, v):
        best, bd = FLAKE, 9.0
        for r in range(int(v) - 1, int(v) + 2):
            for c in range(int(u) - 1, int(u) + 2):
                i = self.pix(c, r)
                if i in SALMON or i in GREYS:
                    d = math.hypot(c + 0.5 - u, r + 0.5 - v)
                    if d < bd:
                        best, bd = (FLAKE if i in SALMON else FLAKE2), d
        return best

    def cls(self, u, v):
        if self.flake_field(u, v) > 0.5 and self.level(u, v) < 121.5:
            return self.flake_kind(u, v)
        lv = self.level(u, v)
        for k, t in enumerate(THRESH):
            if lv < t:
                return k
        return WHITE


THRESH = [116.5, 119.5, 121.5, 125.5]   # CRUST (<=116) | HOT (117-119) | GLOW | LAVA | WHITE


def radius_at(radii, ang):
    n = len(radii)
    t = (ang % (2 * math.pi)) / (2 * math.pi) * n
    k = int(t)
    f = t - k
    return radii[k % n] * (1 - f) + radii[(k + 1) % n] * f


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def blister_w(u, v):
    d = math.hypot(u - BLISTER[0], (v - BLISTER[1]) * 1.15)
    return math.exp(-(d / BLISTER_R) ** 2.6)


# --- the rock body -------------------------------------------------------------------------------

class Body:
    """The rock's surface as a function of sprite point (u, v) on its top half, so vertices can
    slide in (u, v) onto the sprite's colour boundaries and stay on the surface."""
    TOP_POW, BOT_POW = 0.92, 0.95

    def __init__(self, g, seed):
        self.g = g
        self.su, self.sv = SUMMIT
        _, _, self.radii = g.outline(SUMMIT, grow=GROW.get(seed, 0.18), smooth=SMOOTH.get(seed, 2))
        self.off = Vector((seed * 1.37, seed * 0.61, 3.3))

    def dome(self, u, v):
        s = min(1.0, self.s_of(u, v))
        sp = math.sin(math.acos(s ** (1 / self.TOP_POW)))
        z = H_TOP * sp ** self.TOP_POW
        return z + 0.025 * noise.noise(Vector((u / 4.0, v / 4.0, 0.0)) + self.off) * sp

    def ang(self, u, v):
        return math.atan2(-(v - self.sv), u - self.su)

    def s_of(self, u, v):
        R = radius_at(self.radii, self.ang(u, v))
        return math.hypot(u - self.su, v - self.sv) / max(R, 1e-6)

    def relief(self, u, v):
        g = self.g
        lv = g.level(u, v)
        bw = blister_w(u, v)
        seam = smoothstep(119.0, 120.3, lv) * (1 - smoothstep(0.3, 0.65, bw))
        fl = g.flake_field(u, v)
        return -SEAM_DEPTH * seam + FLAKE_H * smoothstep(0.35, 0.65, fl) + BLISTER_H * bw

    def waist(self, a, phi):
        return 0.03 * noise.noise(Vector((math.cos(a), math.sin(a), 0)) * 1.3 + self.off) * math.cos(phi) ** 2

    def top(self, u, v):
        a = self.ang(u, v)
        s = min(1.0, self.s_of(u, v))
        phi = math.acos(s ** (1 / self.TOP_POW))
        sp = math.sin(phi)
        z = self.dome(u, v)
        z += self.relief(u, v) * min(1.0, sp * 2.2)
        z += self.waist(a, phi)
        return Vector((self.g.x(u), self.g.y(v), z))

    def bottom(self, a, phi):
        r = radius_at(self.radii, a)
        s = math.cos(phi) ** self.BOT_POW
        u, v = self.su + s * r * math.cos(a), self.sv - s * r * math.sin(a)
        z = -H_BOT * (-math.sin(phi)) ** 0.95 + self.waist(a, phi)
        return Vector((self.g.x(u), self.g.y(v), z))


def rock_body(g, seed):
    body = Body(g, seed)
    su, sv = SUMMIT
    bm = bmesh.new()
    uvs = {}
    rings = []
    for k in range(1, RINGS_BOT):
        phi = -math.pi / 2 + (math.pi / 2) * k / RINGS_BOT
        rings.append([bm.verts.new(body.bottom(2 * math.pi * j / SECTORS, phi)) for j in range(SECTORS)])
    for k in range(0, RINGS_TOP):
        phi = (math.pi / 2) * k / RINGS_TOP
        s = math.cos(phi) ** Body.TOP_POW
        ring = []
        for j in range(SECTORS):
            a = 2 * math.pi * j / SECTORS
            r = radius_at(body.radii, a)
            u, v = su + s * r * math.cos(a), sv - s * r * math.sin(a)
            vert = bm.verts.new(body.top(u, v))
            if k > 0:
                uvs[vert] = (u, v)
            ring.append(vert)
        rings.append(ring)
    vb = bm.verts.new(body.bottom(0.0, -math.pi / 2))
    vt = bm.verts.new(body.top(su, sv))
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(SECTORS):
            k = (j + 1) % SECTORS
            bm.faces.new((r0[j], r0[k], r1[k], r1[j]))
    for j in range(SECTORS):
        k = (j + 1) % SECTORS
        bm.faces.new((vb, rings[0][k], rings[0][j]))
        bm.faces.new((rings[-1][j], rings[-1][k], vt))
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="SHORT_EDGE")
    relax(bm, g, body, uvs)
    # the sprite's own colours on the top (each face from the relaxed (u, v) under it); the
    # flanks and underside are crust for now
    bm.normal_update()
    rim = bm.faces.layers.int.new("rim")
    for f in bm.faces:
        c = f.calc_center_median()
        side = f.normal.z < -0.25 or c.z < 0.07
        f.material_index = CRUST if side else g.cls(*face_uv(f, uvs, g))
        f[rim] = 1 if side and c.z > -0.2 else 0
    c0 = Vector((g.x(su), g.y(sv), 0.0))
    lay, planes = plate_cuts(bm, c0, seed)
    # the plates press the top down (and the flank in), so some of the top of the flank now shows
    # from above: it takes the sprite's colour under it there too
    bm.normal_update()
    for f in bm.faces:
        if f[rim] and f.normal.z > 0.3:
            c = f.calc_center_median()
            f.material_index = g.cls(*g.uv(c.x, c.y))
    grooves(bm, lay, planes, c0)
    bm.normal_update()
    cracks = Cracks(g, body, c0, BVHTree.FromBMesh(bm), seed)
    cut_cracks(bm, cracks)
    crack_channels(bm, cracks)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_area() < 1e-10], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    merge_flat(bm, lay)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # flat plates with crisp edges; the grooves and channels smooth across
    bm.normal_update()
    # (smooth-shaded with sharp edges rather than flat faces: a plate is one plane, so its normals
    # agree anyway, and its vertices are shared in the export instead of three per triangle)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) == 2 and (lf[0][lay] != lf[1][lay] or lf[0].normal.angle(lf[1].normal, 0) > math.radians(12)):
            e.smooth = False
    bm.faces.layers.int.remove(bm.faces.layers.int["plate"])
    bm.faces.layers.int.remove(bm.faces.layers.int["rim"])
    return bm


def face_uv(f, uvs, g):
    pts = [uvs.get(v) for v in f.verts]
    if all(p is not None for p in pts):
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    c = f.calc_center_median()
    return g.uv(c.x, c.y)


def relax(bm, g, body, uvs, rounds=8):
    """Slide the top's vertices in (u, v) onto the sprite's colour boundaries (the iso-lines of
    the ramp field between two bands, or of the flake field), so each region's edge is a smooth
    curve rather than the loft's triangle saw-teeth. A vertex never travels more than 0.4 of its
    shortest edge from where the loft put it, and never folds a triangle."""
    def uvp(v):
        return uvs.get(v) or g.uv(v.co.x, v.co.y)

    def area(f, v=None, p=None):
        pts = [p if (w is v) else uvp(w) for w in f.verts]
        (ax, ay), (bx, by), (cx, cy) = pts[:3]
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)

    home = dict(uvs)
    reach = {}
    for v in uvs:
        reach[v] = 0.5 * min(math.dist(uvp(v), uvp(e.other_vert(v))) for e in v.link_edges)
    area0 = {f: area(f) for f in bm.faces if any(w in uvs for w in f.verts)}
    for _ in range(rounds):
        fcls = {f: g.cls(*face_uv(f, uvs, g)) for f in bm.faces}
        for v, (u0, v0) in list(uvs.items()):
            cs = {fcls[f] for f in v.link_faces}
            if len(cs) < 2:
                continue
            ramp_cs = sorted(c for c in cs if c <= WHITE)
            if any(c > WHITE for c in cs) and ramp_cs:
                field, target = g.flake_field, 0.5
            elif len(ramp_cs) >= 2:
                lv = g.level(u0, v0)
                ts = THRESH[ramp_cs[0]:ramp_cs[-1]]
                target = min(ts, key=lambda t: abs(t - lv))
                field = g.level
            else:
                continue
            e = 0.12
            f0 = field(u0, v0)
            gx = (field(u0 + e, v0) - field(u0 - e, v0)) / (2 * e)
            gy = (field(u0, v0 + e) - field(u0, v0 - e)) / (2 * e)
            g2 = gx * gx + gy * gy
            if g2 < 1e-6:
                continue
            k = (target - f0) / g2
            nu, nv = u0 + k * gx, v0 + k * gy
            hu, hv = home[v]
            d = math.hypot(nu - hu, nv - hv)
            if d > reach[v]:
                nu, nv = hu + (nu - hu) * reach[v] / d, hv + (nv - hv) * reach[v] / d
            if body.s_of(nu, nv) > 0.97:
                continue
            ok = True
            for f in v.link_faces:
                a0 = area0.get(f)
                if a0 is None:
                    continue
                a1 = area(f, v, (nu, nv))
                if a1 * a0 <= 0 or abs(a1) < 0.2 * abs(a0):
                    ok = False
                    break
            if ok:
                uvs[v] = (nu, nv)
                v.co = body.top(nu, nv)


def fib_dirs(n, rng, jitter):
    rot = rng.uniform(0, 2 * math.pi)
    out = []
    for k in range(n):
        z = 1 - 2 * (k + 0.5) / n
        r = math.sqrt(max(0.0, 1 - z * z))
        a = k * 2.399963 + rot
        s = Vector((r * math.cos(a), r * math.sin(a), z))
        s += Vector((rng.gauss(0, jitter), rng.gauss(0, jitter), rng.gauss(0, jitter)))
        out.append(s.normalized())
    return out


def merge_flat(bm, lay):
    """Merge each plate's coplanar triangles of one colour into one face (fewer triangles to draw;
    left as a polygon, the export triangulates it). Only a region that is a plain disc (one boundary loop, no holes, no
    pinched corners) is merged: its faces are replaced by one face on that loop, so no face ever
    touches itself."""
    bm.normal_update()
    done = set()
    regions = []
    for f0 in bm.faces:
        if f0 in done or f0[lay] <= 0:
            continue
        reg, stack = [f0], [f0]
        done.add(f0)
        while stack:
            f = stack.pop()
            for e in f.edges:
                for g2 in e.link_faces:
                    if (g2 not in done and g2[lay] == f0[lay] and g2.material_index == f0.material_index
                            and g2.normal.angle(f0.normal, 0) < math.radians(0.3)):
                        done.add(g2)
                        reg.append(g2)
                        stack.append(g2)
        if len(reg) > 3:
            regions.append(reg)
    for reg in regions:
        rs = set(reg)
        verts = {v for f in reg for v in f.verts}
        edges = {e for f in reg for e in f.edges}
        bound = [e for e in edges if sum(1 for g2 in e.link_faces if g2 in rs) == 1]
        nxt = {}
        ok = len(verts) - len(edges) + len(reg) == 1
        for f in reg:
            for lp in f.loops:
                if lp.edge in bound:
                    if lp.vert in nxt:
                        ok = False
                    nxt[lp.vert] = lp.link_loop_next.vert
        if not ok or len(nxt) != len(bound):
            continue
        start = next(iter(nxt))
        loop = [start]
        while True:
            v = nxt[loop[-1]]
            if v is start:
                break
            if v in loop or len(loop) > len(nxt):
                ok = False
                break
            loop.append(v)
        if not ok or len(loop) != len(nxt) or len(loop) < 3:
            continue
        example = reg[0]
        mat, plate = example.material_index, example[lay]
        smooth = example.smooth
        others = {k: example[l] for k, l in bm.faces.layers.int.items()}
        bmesh.ops.delete(bm, geom=reg, context="FACES")
        try:
            nf = bm.faces.new(loop)
        except ValueError:
            continue
        nf.material_index, nf.smooth = mat, smooth
        for k, val in others.items():
            nf[bm.faces.layers.int[k]] = val


def plate_cuts(bm, c0, seed):
    """Cleave the round body into plates: ~46 planes in a jittered spread of directions, each set
    0.022-0.04 under the body's furthest point that way; the body beyond a plane is pressed flat
    onto it (the mesh is first cut along the plane, so the plate's edge is one clean line). The
    plates overlap into an irregular polyhedron of flat faces; each face records its plate."""
    rng = random.Random(seed * 7 + 3)
    lay = bm.faces.layers.int.new("plate")
    dirs = fib_dirs(PLATES, rng, 0.2)
    rng.shuffle(dirs)
    planes = {}
    total = sum(f.calc_area() for f in bm.faces)

    def next_plane(k):
        """The jittered spread first; then planes toward patches of round body still showing
        above and below the waist (each still set under the body's furthest point its way, so it
        never bites deeper elsewhere), while they reach one."""
        if k <= len(dirs):
            n = dirs[k - 1]
            return n, max((v.co - c0).dot(n) for v in bm.verts)
        body = [f for f in bm.faces if f[lay] == 0 and (f.calc_center_median() - c0).normalized().z > UNDER_Z]
        if sum(f.calc_area() for f in body) < 0.01 * total:
            return None
        for _ in range(12):
            f = max(body, key=lambda f: f.calc_area() * (1 + 3 * rng.random()))
            n = (f.calc_center_median() - c0).normalized()
            hi = max((v.co - c0).dot(n) for v in bm.verts)
            if (f.calc_center_median() - c0).dot(n) > hi - PLATE_DEPTH[0]:
                return n, hi
        return None

    for k in range(1, PLATES + 14):
        nxt = next_plane(k)
        if nxt is None:
            break
        n, hi = nxt
        # planes facing sideways cut shallower: they make the top-down outline
        depth = rng.uniform(*PLATE_DEPTH) * (SIDE_CUT + (1 - SIDE_CUT) * abs(n.z))
        d = hi - depth
        planes[k] = (n, c0 + n * d)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=c0 + n * d,
                               plane_no=n, dist=0.005)
        z_ok = n.z > 0.4
        for v in bm.verts:
            p = (v.co - c0).dot(n)
            if p > d - 0.005:   # (the cut took points this close as on the plane)
                r = v.co - c0
                if z_ok and r.z > 0.25 * r.length:
                    # pressed straight down on the top, so the sprite's colours stay where it has them
                    v.co.z -= (p - d) / n.z
                else:
                    v.co -= n * (p - d)
        for f in bm.faces:
            if all(abs((v.co - c0).dot(n) - d) < 1e-5 for v in f.verts):
                f[lay] = k
    return lay, planes


def creases(bm, lay):
    """Edges where two plates meet: {(plate, plate): [edges]}."""
    out = {}
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) != 2:
            continue
        a, b = lf[0][lay], lf[1][lay]
        if a == b or a <= 0 or b <= 0:
            continue
        if lf[0].normal.angle(lf[1].normal, 0) < math.radians(3):
            continue
        out.setdefault((min(a, b), max(a, b)), []).append(e)
    return out


class Cracks:
    """Lava seams on the flanks: a few branching cracks that wander down from the hot rim. Each
    starts where the sprite's rock is hottest near the rim (the front, toward the game camera,
    preferred), walks down over the ball in short steps that turn at random (so it zigzags like a
    crack, not one straight drip), forks once or twice, and narrows to nothing below the waist.
    A crack is a polyline of surface points with a half-width at each."""

    STEP = math.radians(6.5)

    def __init__(self, g, body, c0, bvh, seed):
        rng = random.Random(seed * 5 + 2)
        self.c0, self.bvh = c0, bvh
        score = []
        for k in range(72):
            a = 2 * math.pi * k / 72
            R = radius_at(body.radii, a)
            heat = max(g.level(body.su + f * R * math.cos(a), body.sv - f * R * math.sin(a)) for f in (0.62, 0.72, 0.82))
            score.append((heat + 2.0 * max(0.0, -math.sin(a)), a))
        score.sort(reverse=True)
        starts = [score[0][1]]
        for _, a in score:
            if all(abs(math.remainder(a - b, 2 * math.pi)) > math.radians(100) for b in starts):
                starts.append(a)
            if len(starts) == 3:
                break
        self.paths = []
        for n, a0 in enumerate(starts):
            e0 = SIDE_TOP - math.radians(rng.uniform(3, 8))
            d = Vector((math.cos(a0) * math.cos(e0), math.sin(a0) * math.cos(e0), math.sin(e0)))
            e_end = math.radians((-40, -30, -22)[n] + rng.uniform(-5, 5))
            self.walk(d, rng.uniform(-0.5, 0.5), (1.0, 0.85, 0.7)[n], e_end, rng, forks=2 if n == 0 else 1)

    def point(self, d):
        hit = self.bvh.ray_cast(self.c0 + d * 0.05, d, 3.0)
        return hit[0] if hit[0] is not None else self.c0 + d * 0.7

    def walk(self, d, turn, w0, e_end, rng, forks, steps=None):
        """From direction d, heading down (turned by `turn` radians), to elevation e_end."""
        el0 = math.asin(d.z)
        n = steps or max(3, int((el0 - e_end) / (self.STEP * 0.8)) + 1)
        dirs = [d.copy()]
        down = Vector((0, 0, -1))
        tdir = (down - d * d.dot(down)).normalized()
        tdir = Quaternion(d, turn) @ tdir
        for i in range(n):
            # a crack turns at random but keeps falling
            tdir = Quaternion(d, rng.gauss(0, math.radians(28))) @ tdir
            fall = (down - d * d.dot(down))
            if fall.length > 1e-6:
                tdir = (tdir + fall.normalized() * 0.45).normalized()
            d = (d + tdir * math.tan(self.STEP * rng.uniform(0.75, 1.25))).normalized()
            tdir = (tdir - d * d.dot(tdir)).normalized()
            dirs.append(d.copy())
        m = len(dirs)
        ws = [w0 * (0.55 + 0.45 * smoothstep(0, 1.2, i)) * (1 - i / (m - 1)) ** 0.7 for i in range(m)]
        self.paths.append(([self.point(x) for x in dirs], ws))
        if forks:
            for _ in range(forks):
                i = rng.randint(1, max(1, m // 2))
                if ws[i] < 0.25:
                    continue
                side = rng.choice((-1, 1))
                self.walk(dirs[i], side * math.radians(rng.uniform(40, 70)), ws[i] * 0.75,
                          e_end + math.radians(10), rng, 0, steps=rng.randint(3, 5))

    def segments(self):
        for pts, ws in self.paths:
            for i in range(len(pts) - 1):
                yield pts[i], pts[i + 1], ws[i], ws[i + 1]

    def q(self, p):
        """Distance from the nearest crack's centre line in its local half-widths (99 = none)."""
        best = 99.0
        for a, b, wa, wb in self.segments():
            ab = b - a
            ll = ab.length_squared
            t = max(0.0, min(1.0, (p - a).dot(ab) / ll)) if ll > 1e-12 else 0.0
            w = (wa + (wb - wa) * t) * CRACK_W
            if w < 1e-4:
                continue
            dd = (p - (a + ab * t)).length
            if dd < 1.6 * w:
                best = min(best, dd / w)
        return best

    def offset_lines(self):
        """Each crack's band edges (both sides), as surface-ish polylines."""
        for pts, ws in self.paths:
            m = len(pts)
            sides = []
            for i in range(m):
                t = pts[min(m - 1, i + 1)] - pts[max(0, i - 1)]
                nrm = (pts[i] - self.c0).normalized()
                sides.append(nrm.cross(t).normalized())
            for o in CRACK_BANDS:
                for sg in (-1, 1):
                    yield [pts[i] + sides[i] * (sg * o * ws[i] * CRACK_W) for i in range(m)]


def cut_cracks(bm, cracks):
    """Knife the cracks' band edges into the surface: each polyline segment is cut by the plane
    through it and the ball's centre, over the faces along that segment only, so neighbouring
    segments' cuts meet exactly at their shared point."""
    c0 = cracks.c0
    reach = 1.4 * CRACK_W
    for line in cracks.offset_lines():
        for a, b in zip(line, line[1:]):
            ab = b - a
            ll = ab.length_squared
            if ll < 1e-10:
                continue
            no = (a - c0).cross(b - c0)
            if no.length < 1e-9:
                continue
            no.normalize()
            faces = []
            for f in bm.faces:
                c = f.calc_center_median()
                t = (c - a).dot(ab) / ll
                if -0.15 < t < 1.15 and abs((c - c0).dot(no)) < reach and (c - a - ab * max(0.0, min(1.0, t))).length < 2 * reach + 0.05:
                    faces.append(f)
            if not faces:
                continue
            edges = {e for f in faces for e in f.edges}
            verts = {v for f in faces for v in f.verts}
            bmesh.ops.bisect_plane(bm, geom=list(verts) + list(edges) + faces, plane_co=c0, plane_no=no, dist=0.004)


def crack_channels(bm, cracks):
    """Let the channels' floors down (lips stay, the floor along the centre line deepest) and
    paint the bands by distance from the centre line in local half-widths: lava on the floor,
    glow, hot rock at the lips, where hotter than the colour a face carries (the sprite's on top)."""
    for f in bm.faces:
        q = cracks.q(f.calc_center_median())
        if q >= CRACK_BANDS[-1]:
            continue
        cls = LAVA if q < CRACK_BANDS[0] else GLOW if q < CRACK_BANDS[1] else HOT
        top = f.material_index
        if top == CRUST or top > WHITE or top < cls:
            f.material_index = cls
    moves = []
    for v in bm.verts:
        q = cracks.q(v.co)
        if q < 1.0:
            moves.append((v, (v.co - cracks.c0).normalized() * (SIDE_SEAM_DEPTH * (1 - q * q))))
    for v, m in moves:
        v.co -= m


class Seg:
    """A crease between plates a and b: the straight line where their planes meet, from p0 to p1."""

    def __init__(self, key, edges, planes):
        self.key = key
        pts = [v.co.copy() for e in edges for v in e.verts]
        u = planes[key[0]][0].cross(planes[key[1]][0])
        u = u.normalized() if u.length > 1e-6 else (edges[0].verts[1].co - edges[0].verts[0].co).normalized()
        o = pts[0]
        ts = [(p - o).dot(u) for p in pts]
        self.p0, self.p1 = o + u * min(ts), o + u * max(ts)
        self.ab = self.p1 - self.p0
        self.ll = self.ab.length_squared

    def foot(self, p):
        t = max(0.0, min(1.0, (p - self.p0).dot(self.ab) / self.ll)) if self.ll > 1e-12 else 0.0
        return t, self.p0 + self.ab * t


def nearest(p, segs):
    best = None
    for s in segs:
        t, f = s.foot(p)
        dd = (p - f).length_squared
        if best is None or dd < best[0]:
            best = (dd, s, t)
    return math.sqrt(best[0]), best[1], best[2]


def cut_side(bm, lay, plate, n_plate, a, b):
    """Cut plate's faces along the line a-b (in the plate's plane), only near that line."""
    d = b - a
    if d.length < 1e-6:
        return
    no = n_plate.cross(d.normalized())
    if no.length < 1e-6:
        return
    ll = d.length_squared

    def near(f):
        c = f.calc_center_median()
        t = (c - a).dot(d) / ll
        return -0.1 < t < 1.1 and (c - a - d * max(0.0, min(1.0, t))).length < 0.08

    faces = [f for f in bm.faces if f[lay] == plate and near(f)]
    if not faces:
        return
    edges = {e for f in faces for e in f.edges}
    verts = {v for f in faces for v in f.verts}
    bmesh.ops.bisect_plane(bm, geom=list(verts) + list(edges) + faces, plane_co=a, plane_no=no.normalized(), dist=0.004)


def grooves(bm, lay, planes, c0):
    """The creases between plates become narrow V grooves (dark in the AO bake): both lips cut as
    lines parallel to the crease, a groove's width off it, then the crease let down."""
    bm.normal_update()
    segs = []
    for key, edges in creases(bm, lay).items():
        s = Seg(key, edges, planes)
        # the underside needs no detail (a plain closed shape): its creases stay creases
        if s.ll > 1e-6 and max((s.p0 - c0).normalized().z, (s.p1 - c0).normalized().z) > UNDER_Z:
            segs.append(s)
    for s in segs:
        for plate in s.key:
            n = planes[plate][0]
            other = planes[s.key[1] if plate == s.key[0] else s.key[0]][0]
            t = (s.ab.normalized()).cross(n)
            if t.dot(other) > 0:   # away from the crease, into this plate
                t = -t
            cut_side(bm, lay, plate, n, s.p0 + t * GROOVE_W, s.p1 + t * GROOVE_W)
    moves = []
    for v in bm.verts:
        dist, s, t = nearest(v.co, segs)
        q = dist / GROOVE_W
        if q < 1.0:
            moves.append((v, (v.co - c0).normalized() * (GROOVE_D * (1 - q))))
    for v, m in moves:
        v.co -= m
    return segs


def darken_crust(obj, img, pad=3):
    """The crust is the sprite's darkest red (115, shading down to near black), but the game's sun,
    sky and room light lift a plain lit face of it to a cherry red. Its texels in the baked colour
    multiplier are scaled by CRUST_DARK (the palette index stays 115; the AO stays on top), so the
    open plates read dark maroon and the glowing seams stand out against them."""
    import numpy as np
    w, h = img.size
    m = np.zeros((h, w), dtype=np.float32)   # Blender's pixel rows: bottom first, as uv v
    me = obj.data
    me.calc_loop_triangles()
    uv = me.uv_layers["bake"].data
    for t in me.loop_triangles:
        if t.material_index != CRUST:
            continue
        (ax, ay), (bx, by), (cx, cy) = [(uv[li].uv[0] * w - 0.5, uv[li].uv[1] * h - 0.5) for li in t.loops]
        x0, x1 = max(0, int(min(ax, bx, cx))), min(w - 1, int(max(ax, bx, cx)) + 1)
        y0, y1 = max(0, int(min(ay, by, cy))), min(h - 1, int(max(ay, by, cy)) + 1)
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) < 1e-12:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / det
        l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / det
        inside = (l1 >= -0.02) & (l2 >= -0.02) & (1 - l1 - l2 >= -0.02)
        m[y0:y1 + 1, x0:x1 + 1][inside] = 1.0
    for _ in range(pad):   # into the bake's margin, so filtering never brings the light back
        m = np.maximum.reduce([m, np.roll(m, 1, 0), np.roll(m, -1, 0), np.roll(m, 1, 1), np.roll(m, -1, 1)])
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    f = 1 - (1 - CRUST_DARK) * m
    px[:, :, :3] *= f[:, :, None]
    img.pixels[:] = px.ravel()
    img.update()
    if img.filepath_raw:
        img.save()


def bake(rocks, size=1024, samples=48):
    """AO/roughness bake of the crust (D50/D65, "bake": "model"; no concept projection): the 14
    frame rocks are joined, spread apart so none shades another, into one object, so they share
    one UV atlas and one pair of maps (their palette materials are shared), baked with the Talon's
    recipe (usp_talon.bake_maps, untinted), then split back into the frame rocks. The glowing
    lava, glow and white-hot stay unbaked."""
    import tempfile
    import usp_talon as T
    for k, o in enumerate(rocks):
        me = o.data
        attr = me.attributes.new("rock_frame", "INT", "FACE")
        attr.data.foreach_set("value", [k] * len(me.polygons))
        me.transform(Matrix.Translation((6.0 * k, 0.0, 0.0)))
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in rocks:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rocks[0]
    bpy.ops.object.join()
    joined = rocks[0]
    tint, textured = T.TINT, T.TEXTURED
    T.TINT = (1.0, 1.0, 1.0)
    T.TEXTURED = (CRUST, HOT, FLAKE, FLAKE2)
    try:
        T.bake_maps(joined, Path(tempfile.mkdtemp(prefix="newshg1_bake_")), size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "newshg1")
    darken_crust(joined, bpy.data.images["newshg1_colour"])
    out = []
    mats = list(joined.data.materials)
    for k in range(len(rocks)):
        bm = bmesh.new()
        bm.from_mesh(joined.data)
        lay = bm.faces.layers.int["rock_frame"]
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lay] != k], context="FACES")
        bmesh.ops.translate(bm, verts=bm.verts[:], vec=(-6.0 * k, 0.0, 0.0))
        me = bpy.data.meshes.new(f"{NAME}-rock-{k}")
        bm.to_mesh(me)
        bm.free()
        me.attributes.remove(me.attributes["rock_frame"])
        for m in mats:
            me.materials.append(m)
        o = bpy.data.objects.new(me.name, me)
        joined.users_collection[0].objects.link(o)
        out.append(o)
    bpy.data.objects.remove(joined)
    return out


def build(sprite, coll, do_bake=True):
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(115, metallic=0.0, roughness=1.0, emission_strength=0.0),    # crust: dull dark stone
        pal(118, metallic=0.0, roughness=0.85, emission_strength=0.5),   # hot red rock
        pal(120, metallic=0.0, roughness=0.6, emission_strength=1.0),    # glowing seam edge
        pal(123, metallic=0.0, roughness=0.5, emission_strength=1.0),    # orange-yellow lava
        pal(127, metallic=0.0, roughness=0.4, emission_strength=1.1),    # white-hot
        pal(71, metallic=0.0, roughness=0.95),                            # cooled salmon flake
        pal(27, metallic=0.0, roughness=0.95),                            # cooled tan-grey flake
    ]
    rocks, frames = [], []
    for f in sprite["frames"]:
        index = f["index"]
        g = FrameGrid(index)
        bm = rock_body(g, seed=index)
        bad = [e for e in bm.edges if not e.is_manifold]
        if bad:
            print(f"frame {index}: non-manifold edges {len(bad)}")
        obj = common.mesh_object(f"{NAME}-rock-{index}", bm, mats, coll, smooth=None)
        print(f"frame {index}: {sum(len(p.vertices) - 2 for p in obj.data.polygons)} triangles")
        rocks.append(obj)
        frames.append(index)
    if do_bake:
        rocks = bake(rocks)
    objs = []
    tris_total = 0
    for obj, index in zip(rocks, frames):
        obj.name = obj.data.name = f"{NAME}-rock-{index}"
        tris_total += sum(len(p.vertices) - 2 for p in obj.data.polygons)
        closed = obj.copy()
        closed.data = obj.data.copy()
        coll.objects.link(closed)
        shell = common.outline_shell(closed, coll, **D90_SHELL)
        shell.name = shell.data.name = f"{NAME}-rock-{index}_outline"
        bpy.data.objects.remove(closed)
        print(f"frame {index}: shell {len(shell.data.polygons)}")
        common.frame_part(obj, [index])
        common.frame_part(shell, [index])
        objs += [obj, shell]
    print(f"{NAME} total triangles (rocks) {tris_total}")
    return objs


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_bake = "--no-bake" not in argv
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    objs = build(sprite, coll, do_bake=do_bake)
    common.export_sprite_model(WT, objs, f"enemies/{NAME}", sprite["sprites"], image_format="WEBP" if do_bake else "AUTO")
    if "--preview" in argv:
        f0 = sprite["frames"][0]
        common.render_preview(objs, argv[argv.index("--preview") + 1], WT / "reference" / "models" / NAME / f0["image"], size=f0["size"], frame=f0["index"])
