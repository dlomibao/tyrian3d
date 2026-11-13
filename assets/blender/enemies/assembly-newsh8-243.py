"""Floating rock fortress (newsh8.shp, assembly of 21 pieces, 12 distinct), (final build of design A).

What it is: a flying mass of brown boulders (it spawns on the ground, top and sky layers and weaves
sideways across the terrain, D122's scout), a slab of rock about 14 x 6 units with a rounded crown
of stones on top, a steep front face whose stones run down into stalactites, a domed underside with
stalactites hanging from it, and two red machine pillars set into it, each in a bay cut into the
rock: a capped housing with a pulsing lamp window, a clamp band, a narrower lower column with a pipe,
a stack of cooling fins and a foot block, lying along the rock's top and running down its front.

Seams (the reason for the build order): in game the pieces are separate enemies, spawned in several
combinations (L P M M M P R in the full fortress; L P M P R elsewhere), so any vertical seam may
meet any column. Each column type (L 0-24, P 24-48, M 72-96, R 144-168 in grid px) is built from its
own sprite strip only, and the vertical seams all share one canonical cross-section: the core body's
section there is a function of the row only (the same plan extent, profile and rim at every seam),
and every stone or spike is clipped to its column and sunk under a steep wedge ceiling that reaches
just below the core at the seam line. So a column meets any other column without a step.

Geometry (D65 hard surface for the pillars, D175 rock for the stones):
- core: per column, sections every pixel across x, each section the rock's profile in y-z (a back
  wall, the crown rim, the top, the front face falling 39-45 degrees into the stalactite band, the
  domed underside), lofted and capped. Its plan edge is the sprite's inner mask (D74) traced with
  the bilinear field, so the outline is the sprite's.
- stones: the sprite's boulders (a watershed over the rock pixels' shading, per column strip), each a
  convex chipped polytope over its footprint (base ring sunk into the core, a shoulder ring, a top
  ring shifted toward the stone's lit pixels): crisp facets, V cracks where neighbours meet.
- stalactites: the elongated stones of the front band become tapered spikes whose tips run to the
  mask's bottom edge and a little below the core; a row of hanging cones under the body (hidden
  from above) so the side and front views read airborne.
- pillars: path lofts (chamfered rounded-rectangle sections, perpendicular to the rock's profile)
  with modelled cap ridge, window bezel, clamp band, pipe, fins and foot.

Colour: the stones and core take D175's facet ramp (lib_newshd_rock.facet_ramp, the sprite's own
shade distribution, ranked by the art's light and the sprite's brightness under each facet; only
faces visible from above or the game camera are ranked). Pillars: palette indices per region (the
sprite's medians: housing 115, its shaded left chamfer 113 and lit right 117, clamp band 118, lower
column 112, pipe 116, fins 114, foot 112 with a 113 top, vent 64). The lamp keeps the current model's frames:
rim 126 / core 127 on 165, (117, 120) on 277, (118, 124) on 279, (122, 126) on 281, and the
white-hot line down the core on 279 and 281 (frame parts); glows metallic 1, rough (D126/D173).
AO/roughness bake only (no concept projection), D90 outline shell from a sealed copy, split open
per piece so no ink line runs along the seams.

Output: the 12 distinct pieces to public/models/enemies/<piece>.glb (piece, shell slice and, for
newsh8-165, the lamp-line frame parts) with their spriteModels entries. `--out FILE` also writes a
review glb with all 21 pieces placed as in the layout, and build_info.json beside it.

    blender -b --factory-startup -P assembly-newsh8-243.py -- [--no-bake] [--out file.glb]
"""

import json
import math
import random
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "assets" / "blender" / "enemies"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import lib_newshd_rock as RK  # noqa: E402
import lib_b041 as LB  # noqa: E402
import sprite_mask as SM  # noqa: E402

NAME = "assembly-newsh8-243"
GW, GH = 168, 84            # grid px; grid (0, 0) is screen (-20, -31); Blender origin = grid (84, 42) = screen (64, 11)
CX0, CY0 = 64, 11
SEAMS = (24, 48, 72, 96, 120, 144)
# column types: (grid x of the built instance, seams it must meet: left?, right?)
COLUMNS = {"L": (0, False, True), "P": (24, True, True), "M": (72, True, True), "R": (144, True, False)}
# where each column type sits in the full fortress (grid x of its left edge)
PLACES = {"L": [0], "P": [24, 120], "M": [48, 72, 96], "R": [144]}
# pieces per column type, top to bottom
PIECES = {"L": ["newsh8-169", "newsh8-207", "newsh8-245"], "P": ["newsh8-165", "newsh8-203", "newsh8-241"],
          "M": ["newsh8-167", "newsh8-205", "newsh8-243"], "R": ["newsh8-161", "newsh8-199", "newsh8-237"]}
PIL = (29.0, 41.0, 4.5, 61.5)   # pillar bay in its column's own grid: cols [29, 41), rows [4.5, 61.5)
MID = 22                        # the rock's median palette index
RAMP = {"bias": 0.0}
GLOW = 126
LAMP_RIM = {277: 117, 279: 118, 281: 122}
LAMP_CORE = {277: 120, 279: 124, 281: 126}
LAMP_LINE = {279: (16.6, 20.4), 281: (15.8, 22.2)}
K_SEAM = 2.2   # the seam wedge's slope (rise per run)
D_S = 0.12     # the core's low ridge along every seam (units above the profile), so the seam crack stays shallow
W_S = 1.6      # its half width (px)
U = 1 / 12


def X(c):
    return (c - 84) / 12


def Y(r):
    return (42 - r) / 12


def R_of(y):
    return 42 - 12 * y


# the rock's profile by row (units): crown rim, top, the front face falling into the stalactites
ZP = T.pchip([0, 4, 10, 22, 32, 40, 46, 52, 58, 63, 67, 72],
             [0.30, 0.36, 0.44, 0.47, 0.43, 0.33, 0.15, -0.15, -0.55, -0.95, -1.25, -1.45])
# the underside (units): a dome, deepest under the middle
ZU = T.pchip([0, 6, 20, 36, 50, 62, 72], [-0.40, -0.62, -1.05, -1.22, -1.22, -1.30, -1.50])


def zprof(r):
    return ZP(r)


def dzdr(r):
    return (ZP(r + 0.25) - ZP(r - 0.25)) / 0.5


# --- the sprite ----------------------------------------------------------------------------------

def load():
    idx, colors = SM.load(NAME)
    m = SM.masks(idx, colors)
    sprite = {"name": NAME, "colors": {}, "frames": [{"pixels": idx, "width": GW, "height": GH}]}
    for names in PIECES.values():
        for n in names:
            sprite["colors"].update(common.load_sprite(WT, n)["colors"])
    return idx, m["inner"], sprite


class G:
    """lib_newshd_rock.Grid's interface over the assembled grid."""

    def __init__(self, inner):
        self.w, self.h, self.inner = GW, GH, inner

    def uv(self, x, y):
        return x * 12 + 84, 42 - y * 12

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


# --- materials -------------------------------------------------------------------------------------

class Mats:
    def __init__(self, sprite):
        self.sprite, self.mats, self.slots = sprite, [], {}

    def slot(self, index, kind="rock", frames=None, part=None, glow=0.0):
        key = (index, kind, part)
        if key not in self.slots:
            if kind == "rock":
                kw = dict(metallic=0.0, roughness=0.85)
            elif kind == "glow":
                kw = dict(metallic=1.0, roughness=0.9, emission_strength=glow)
            else:  # satin red machine metal
                kw = dict(metallic=0.45, roughness=0.42)
            tag = NAME + "-A" + ("" if kind == "rock" else f"_{kind}") + (f"_{part}" if part else "")
            mat = common.palette_material(self.sprite, index, tag, frames=frames, **kw)
            if kind == "metal":
                bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                for nm in ("Specular IOR Level", "Specular"):
                    if nm in bsdf.inputs:
                        bsdf.inputs[nm].default_value = 0.55
                        break
            self.slots[key] = len(self.mats)
            self.mats.append(mat)
        return self.slots[key]


# --- bmesh helpers ---------------------------------------------------------------------------------

def append(dst, src, mat):
    vmap = {}
    for v in src.verts:
        vmap[v] = dst.verts.new(v.co)
    for f in src.faces:
        try:
            nf = dst.faces.new([vmap[v] for v in f.verts])
            nf.material_index = mat if mat is not None else f.material_index
            nf.smooth = False
        except ValueError:
            pass


def hull(points):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(bm, input=vs)
    bmesh.ops.delete(bm, geom=list(set(res["geom_interior"]) | set(res["geom_unused"])), context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def clip(bm, co, no):
    """Keep the side of the plane against `no`, capped."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
    edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    return len(bm.verts) > 3


def seam_clip(bm, c0, left, right, yc):
    """A column's stones and spikes: inside its x range and under the seam wedge."""
    r = R_of(yc)
    a = zprof(r)
    b = -12 * dzdr(r)           # dz/dy
    for on, xs, sgn in ((left, c0, 1), (right, c0 + 24, -1)):
        if not on:
            continue
        x0 = X(xs)
        if not clip(bm, (x0, 0, 0), (-sgn, 0, 0)):
            return False
        # wedge ceiling z = a + b (y - yc) - 0.035 + K |x - x0|; normal points up-and-away from it
        co = Vector((x0, yc, a + D_S - 0.03))
        no = Vector((-sgn * K_SEAM, -b, 1.0)).normalized()
        if not clip(bm, co, no):
            return False
    return True


# --- the core -------------------------------------------------------------------------------------

def core_extent(g, c0):
    """Plan extent of the core per x (grid px, the column's real place): (x, top row, bottom row)."""
    def top_at(x):
        for k in range(0, 84 * 20):
            r = k / 20
            if g.field(x, r) >= 0.5:
                return r
        return None

    def bot_raw(x):
        for k in range(84 * 20, 0, -1):
            r = k / 20
            if g.field(x, r) >= 0.5:
                return r
        return None

    xs = []
    lo, hi = c0, c0 + 24
    # outer ends: where the mask begins / ends
    while lo < hi and top_at(lo + 0.5) is None:
        lo += 1
    while hi > lo and top_at(hi - 0.5) is None:
        hi -= 1
    if not COLUMNS_SEAM(c0)[0]:
        # step in to the field's own edge
        e = lo
        for k in range(0, 21):
            if top_at(lo + k / 20) is not None:
                e = lo + k / 20
                break
        lo = e + 0.02
    if not COLUMNS_SEAM(c0)[1]:
        e = hi
        for k in range(0, 21):
            if top_at(hi - k / 20) is not None:
                e = hi - k / 20
                break
        hi = e - 0.02
    samples = sorted(set([lo, hi] + [x + 0.5 for x in range(int(math.ceil(lo)), int(hi)) if lo < x + 0.5 < hi]))
    if c0 in (24, 120):  # the pillar bay edges
        for d in (PIL[0] - 0.3, PIL[0] + 0.2, PIL[1] - 0.2, PIL[1] + 0.3):
            samples.append(c0 - 24 + d)
    for xs in (c0, c0 + 24):  # the seam ridge
        if xs in SEAMS:
            samples += [xs + d for d in (-1.6, -1.0, -0.5, 0.5, 1.0, 1.6)]
    samples = sorted(set(s for s in samples if lo <= s <= hi))
    bots = {}
    for x in samples:
        bots[x] = bot_raw(x)
    out = []
    for x in samples:
        t = top_at(x)
        # the core's bottom: the mask's bottom with the stalactite tips taken off (a window min)
        near = [bots[s] for s in samples if abs(s - x) <= 3.2 and bots[s] is not None]
        b = min(near) if near else bots[x]
        if t is None or b is None:
            continue
        b = min(b, 66.0)
        # seam blend to the canonical section
        for xs in (c0, c0 + 24):
            if xs in SEAMS:
                w = max(0.0, 1 - abs(x - xs) / 1.6)
                w = w * w * (3 - 2 * w)
                t = t + (TOP_C - t) * w
                b = b + (BOT_C - b) * w
        out.append((x, t, b))
    return out


TOP_C, BOT_C = 4.0, 66.0


def COLUMNS_SEAM(c0):
    return (c0 in SEAMS, c0 + 24 in SEAMS)


def section(x, t, b, bay, endroll, endlift=0.0):
    """The rock's closed section at grid x: top from the back rim (row t) to the front bottom (row b),
    then the underside back. Returns [(row, z)]; the same count for every x."""
    NT, NB = 34, 12
    pts = []
    for i in range(NT + 1):
        u = i / NT
        # denser at both rims
        u = 0.5 - 0.5 * math.cos(math.pi * u) if False else u
        r = t + (b - t) * u
        z = zprof(r) - bay
        d = r - t   # back rim roll (3 px radius)
        if d < 3.0:
            z -= 0.25 * (1 - math.sqrt(max(0.0, 1 - ((3.0 - d) / 3.0) ** 2)))
        z -= endroll
        pts.append((r, z))
    z0 = pts[0][1]
    for i in range(1, NB):
        u = i / NB
        r = b - (b - (t + 4.0)) * u
        pts.append((r, ZU(r) + endlift))
    # the back rounds under (an undercut, so the plan stays the mask's)
    pts += [(t + 4.0, min(ZU(t + 4.0) + endlift, z0 - 0.8)), (t + 2.0, z0 - 0.62), (t + 0.6, z0 - 0.3)]
    return pts


def build_core(bm, g, c0, mats):
    ext = core_extent(g, c0)
    pil = c0 in (24, 120)
    rings = []
    x_lo, x_hi = ext[0][0], ext[-1][0]
    left_end, right_end = not COLUMNS_SEAM(c0)[0], not COLUMNS_SEAM(c0)[1]
    for x, t, b in ext:
        bay = 0.0
        if pil:
            lx = x - (c0 - 24)
            if PIL[0] <= lx <= PIL[1]:
                bay = 0.12
        for xs in (c0, c0 + 24):
            if xs in SEAMS:
                w = max(0.0, 1 - abs(x - xs) / W_S)
                bay -= D_S * w * w * (3 - 2 * w)
        endroll = endlift = 0.0
        for on, xe in ((left_end, x_lo), (right_end, x_hi)):
            if on:
                d = abs(x - xe)
                if d < 3.0:
                    endroll += 0.30 * (1 - math.sqrt(max(0.0, 1 - ((3.0 - d) / 3.0) ** 2)))
                if d < 7.0:  # the underside rounds up into the end
                    endlift += 0.75 * (1 - math.sqrt(max(0.0, 1 - ((7.0 - d) / 7.0) ** 2)))
        sec = section(x, t, b, bay, endroll, endlift)
        rings.append([bm.verts.new((X(x), Y(r), z)) for r, z in sec])
    slot = mats.slot(MID)
    n = len(rings[0])
    for a, c in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((a[i], a[j], c[j], c[i]))
            f.material_index = slot
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        f = bm.faces.new(ring[::-1] if rev else ring)
        f.material_index = slot


# --- stones ----------------------------------------------------------------------------------------

def zsurf(c, r, c0):
    """The core's top at grid (c, r), for seating stones."""
    bay = 0.12 if (c0 in (24, 120) and PIL[0] <= c - (c0 - 24) <= PIL[1]) else 0.0
    return zprof(r) - bay


def segment(idx, inner, c0, pil):
    mask, vals = [], []
    for r in range(GH):
        mrow, vrow = [], []
        for c in range(c0, c0 + 24):
            v = idx[r][c]
            ok = inner[r][c] and 16 <= v <= 31
            if pil and PIL[0] - 0.5 <= c - c0 + 24 < PIL[1] + 0.5 and PIL[2] - 1 <= r < PIL[3]:
                ok = False
            mrow.append(ok)
            vrow.append(v - 16 if 16 <= v <= 31 else 0)
        mask.append(mrow)
        vals.append(vrow)
    lab, n = LB.watershed(vals, mask, radius=2, min_size=10)
    regs = LB.regions(lab, n)
    for reg in regs:
        reg["px"] = [(r, c + c0) for r, c in reg["px"]]
        reg["rows"] = {r: (a + c0, b + c0) for r, (a, b) in reg["rows"].items()}
    return regs


def footprint(px, shrink):
    """Convex footprint polygon (grid px) of a pixel set: hull of the pixel corners, pulled in."""
    pts = set()
    for r, c in px:
        for dr in (0, 1):
            for dc in (0, 1):
                pts.add((c + dc, r + dr))
    pts = sorted(pts)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    poly = lower[:-1] + upper[:-1]
    cx = sum(c for _, c in px) / len(px) + 0.5
    cy = sum(r for r, _ in px) / len(px) + 0.5
    out = []
    for x, y in poly:
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1
        k = max(0.0, d - shrink) / d
        out.append((cx + dx * k, cy + dy * k))
    # chamfer: resample so long edges get a mid vertex (rounder chips)
    res = []
    for i, p in enumerate(out):
        q = out[(i + 1) % len(out)]
        res.append(p)
        if math.hypot(q[0] - p[0], q[1] - p[1]) > 4:
            res.append(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2))
    return res, (cx, cy)


def stone(px, idx, c0, rnd, spike=False):
    """A chipped boulder over its footprint: convex hull of a base ring sunk into the core, a
    shoulder ring and a top ring shifted toward the stone's lit pixels."""
    poly, (cx, cy) = footprint(px, 0.45)
    area = len(px)
    # the stone's lit side: brightness-weighted centroid
    wsum = sum(max(0, idx[r][c] - 18) ** 2 for r, c in px) or 1
    bx = sum((c + 0.5) * max(0, idx[r][c] - 18) ** 2 for r, c in px) / wsum
    by = sum((r + 0.5) * max(0, idx[r][c] - 18) ** 2 for r, c in px) / wsum
    ax, ay = cx + 0.45 * (bx - cx), cy + 0.45 * (by - cy)
    h = min(0.26, max(0.07, 0.30 * math.sqrt(area) / 12))
    pts = []
    for (x, y) in poly:
        pts.append((X(x), Y(y), zsurf(x, y, c0) - 0.07))
    rings = ((0.93, 0.50), (0.72, 0.84), (0.38, 1.0)) if not spike else ((0.9, 0.55), (0.55, 0.9))
    for k, (s, f) in enumerate(rings):
        for i, (x, y) in enumerate(poly):
            if spike and k == len(rings) - 1 and i % 2:
                continue
            px_, py_ = ax + (x - ax) * s, ay + (y - ay) * s
            j = 1 + rnd.uniform(-0.14, 0.14)
            pts.append((X(px_), Y(py_), zsurf(px_, py_, c0) + h * f * j))
    if not spike:
        pts.append((X(ax), Y(ay), zsurf(ax, ay, c0) + h * 1.04))
    return hull(pts), cy


def spike_from(px, idx, c0, rnd, tip_row):
    """A stalactite of the front band: a tapered blade along its pixels, its tip run out to the
    mask's bottom edge and below the core's front."""
    rows = sorted(set(r for r, _ in px))
    r0, r1 = rows[0], rows[-1]
    by_row = {}
    for r, c in px:
        by_row.setdefault(r, []).append(c)
    pts = []
    tip_c = sum(by_row[r1]) / len(by_row[r1]) + 0.5
    tip_r = max(r1 + 1.0, tip_row)
    width0 = max(by_row[r0]) - min(by_row[r0]) + 1
    h = min(0.22, max(0.08, 0.05 * width0 + 0.04))
    n = len(rows)
    for k, r in enumerate(rows[:: max(1, n // 6)] + [r1]):
        lo, hi = min(by_row[r]) + 0.4, max(by_row[r]) + 0.6
        if hi - lo < 0.6:
            m = (lo + hi) / 2
            lo, hi = m - 0.3, m + 0.3
        rr = r + 0.5
        f = 1 - 0.55 * (rr - r0) / max(1.0, tip_r - r0)
        zb = zsurf((lo + hi) / 2, rr, c0)
        for x in (lo, hi):
            pts.append((X(x), Y(rr), zb - 0.08))
        m = (lo + hi) / 2 + rnd.uniform(-0.25, 0.25)
        pts.append((X(m - (hi - lo) * 0.22), Y(rr), zb + h * f))
        pts.append((X(m + (hi - lo) * 0.22), Y(rr), zb + h * f * 0.85))
    # the top end rounds into the stone above
    top = by_row[r0]
    pts.append((X((min(top) + max(top)) / 2 + 0.5), Y(r0 + 0.1), zsurf(tip_c, r0, c0) + h * 0.6))
    # the tip: a point below and in front of the core's lip
    pts.append((X(tip_c), Y(tip_r - 0.15), zprof(tip_r) - 0.32))
    return hull(pts), (r0 + r1) / 2


def hanging(c, r_root, r_tip, w, rnd):
    """A stalactite under the body (hidden from above): a 6-sided chipped cone."""
    pts = []
    zr = ZU(r_root) + 0.12
    for k in range(6):
        a = 2 * math.pi * k / 6 + rnd.uniform(-0.3, 0.3)
        rr = w / 2 * (1 + rnd.uniform(-0.2, 0.2))
        pts.append((X(c) + U * rr * math.cos(a), Y(r_root) + U * rr * math.sin(a) * 0.8, zr))
        pts.append((X(c) + U * rr * 0.55 * math.cos(a + 0.4), Y(r_root + (r_tip - r_root) * 0.35) + U * rr * 0.5 * math.sin(a),
                    zr - 0.35 * (1 + rnd.uniform(-0.2, 0.2))))
    pts.append((X(c + rnd.uniform(-0.4, 0.4)), Y(r_tip), ZU(r_root) - 0.75 - 0.25 * w / 6))
    return hull(pts)


def build_rock(bm, idx, inner, c0, mats, rnd):
    left, right = COLUMNS_SEAM(c0)
    pil = c0 in (24, 120)
    regs = segment(idx, inner, c0, pil)
    slot = mats.slot(MID)
    # the mask's bottom per column (tips) for the spikes
    bottom = {}
    for c in range(c0, c0 + 24):
        rs = [r for r in range(GH) if inner[r][c]]
        bottom[c] = (max(rs) + 1) if rs else None
    n_st = n_sp = 0
    for reg in regs:
        px = reg["px"]
        rows = [r for r, _ in px]
        r0, r1 = min(rows), max(rows)
        cols = [c for _, c in px]
        tall = (r1 - r0 + 1) >= 1.6 * (max(cols) - min(cols) + 1)
        if r1 >= 60 and (r0 + r1) / 2 >= 50 and tall:
            cs = [c for r, c in px if r == r1]
            tips = [bottom[c] for c in cs if bottom.get(c)]
            tip_row = max(tips) if tips else r1 + 1
            sb, yc_r = spike_from(px, idx, c0, rnd, tip_row)
            n_sp += 1
        else:
            sb, yc_r = stone(px, idx, c0, rnd)
            n_st += 1
        if seam_clip(sb, c0, left, right, Y(yc_r)):
            append(bm, sb, slot)
        sb.free()
    # hanging stalactites under the body: three per column, tips kept inside the mask in plan
    for k, (dc, rr, rt, w) in enumerate(((5.5, 30, 34, 5.0), (12.5, 46, 50, 6.0), (18.5, 22, 26, 4.5))):
        c = c0 + dc
        if pil and PIL[0] - 1 <= dc <= PIL[1] + 1:
            c = c0 + (PIL[0] - 3 if k == 0 else PIL[1] + 3)
        if not (inner[int(rt)][int(c)] and inner[int(rr)][int(c)]):
            continue
        hb = hanging(c, rr, rt, w, rnd)
        if seam_clip(hb, c0, left, right, Y((rr + rt) / 2)):
            append(bm, hb, slot)
        hb.free()
    # big weathered lumps round the back and under it (the rear and side views), clear of the seams
    for dc, dr, rx, ry, rz in ((6.0, 6.0, 3.2, 2.6, 0.30), (12.0, 9.0, 3.6, 3.0, 0.34), (18.0, 6.5, 3.0, 2.6, 0.30)):
        c = c0 + dc
        rs = [r for r in range(GH) if inner[r][int(c)]]
        if not rs:
            continue
        r = min(rs) + dr
        pts = []
        for k in range(14):
            a = 2 * math.pi * k / 14
            for e in (-0.5, 0.15, 0.7):
                q = 1 + rnd.uniform(-0.18, 0.12)
                pts.append((X(c + rx * math.cos(a) * math.cos(e) * q), Y(r + ry * math.sin(a) * math.cos(e) * q),
                            ZU(r) + 0.2 + rz * math.sin(e) * q))
        lb = hull(pts)
        append(bm, lb, slot)
        lb.free()
    print(f"column {c0}: {n_st} stones, {n_sp} stalactites")


# --- the pillar -------------------------------------------------------------------------------------

def path_frame(r):
    """Station frame on the rock's profile at row r: origin on the profile, x right, n the
    profile's normal (up and toward the screen bottom on the front face), t along the path."""
    t = Vector((0, -U, dzdr(r))).normalized()
    xa = Vector((1, 0, 0))
    n = t.cross(xa)
    return Vector((0, Y(r), zprof(r))), xa, n


def rrect(ul, ur, vb, vt, ch):
    """A chamfered rectangle in (u, v) px: 8 points, counter-clockwise from the bottom left."""
    return [(ul + ch, vb), (ur - ch, vb), (ur, vb + ch), (ur, vt - ch), (ur - ch, vt), (ul + ch, vt),
            (ul, vt - ch), (ul, vb + ch)]


def ploft(bm, c0, stations, mat, cap=True, top_mats=None):
    """Loft stations (row, ul, ur, vb, vt, ch) in px (u: grid column, v: px above the profile),
    sections perpendicular to the profile. top_mats: per-side material override (0..7 sides of
    rrect; side 4 is the top)."""
    rings = []
    for r, ul, ur, vb, vt, ch in stations:
        o, xa, n = path_frame(r)
        ring = []
        for u, v in rrect(ul, ur, vb, vt, ch):
            p = Vector((X(c0 + u), 0, 0)) + Vector((0, o.y, o.z)) + n * (v * U)
            ring.append(bm.verts.new(p))
        rings.append(ring)
    m = 8
    for a, b in zip(rings, rings[1:]):
        for i in range(m):
            f = bm.faces.new((a[i], a[(i + 1) % m], b[(i + 1) % m], b[i]))
            f.material_index = top_mats[i] if top_mats and i in top_mats else mat
    if cap:
        f0 = bm.faces.new(rings[0])
        f1 = bm.faces.new(rings[-1][::-1])
        f0.material_index = f1.material_index = mat
    return rings


def cyl(bm, c0, col, r0, r1, rad, lift, mat, sides=8):
    """A pipe along the profile from row r0 to r1 at grid column col (px), radius rad px, its axis
    `lift` px above the profile."""
    rings = []
    for r in T.frange(r0, r1, 1.0):
        o, xa, n = path_frame(r)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            p = Vector((X(c0 + col), o.y, o.z)) + xa * (math.cos(a) * rad * U) + n * ((lift + math.sin(a) * rad) * U)
            ring.append(bm.verts.new(p))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(sides):
            f = bm.faces.new((a[i], a[(i + 1) % sides], b[(i + 1) % sides], b[i]))
            f.material_index = mat
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        f = bm.faces.new(ring[::-1] if rev else ring)
        f.material_index = mat


def build_pillar(bm, c0, mats):
    """c0: the grid column of the P column's left edge; u below is the column's own grid (24-48)."""
    o = c0 - 24
    met = lambda i: mats.slot(i, "metal")  # noqa: E731
    H, H_L, H_D = met(115), met(113), met(117)
    sides_house = {0: H_L, 6: H_L, 7: H_L, 2: H_D, 3: H_D, 1: H, 4: H, 5: H}
    # cap (rows 4.6-9): a domed lid with a rolled rim at row 7 (the sprite's lit line is that rim)
    ploft(bm, o, [(4.6, 31.0, 40.0, -2.5, 1.3, 0.8), (5.2, 30.2, 40.7, -2.5, 2.2, 0.9),
                  (6.3, 29.8, 41.0, -2.5, 2.7, 1.0), (7.2, 29.6, 41.2, -2.5, 2.9, 1.0),
                  (8.0, 29.8, 41.0, -2.5, 2.6, 1.0), (8.6, 30.2, 40.6, -2.5, 2.2, 0.9)], met(116),
          top_mats={4: met(118), 5: met(117), 3: met(118)})
    # upper housing (rows 8.6-32.6), chamfered, the left chamfer in shade, the right lit
    ploft(bm, o, [(8.5, 30.0, 40.6, -2.5, 2.3, 1.1), (32.6, 30.0, 40.6, -2.5, 2.3, 1.1)], H, top_mats=sides_house)
    # clamp band (rows 28.8-31.8)
    ploft(bm, o, [(28.8, 29.7, 40.9, -2.0, 2.45, 0.9), (29.3, 29.6, 41.0, -2.0, 2.75, 1.0),
                  (31.3, 29.6, 41.0, -2.0, 2.75, 1.0), (31.8, 29.7, 40.9, -2.0, 2.45, 0.9)], met(118))
    # lamp window (rows 14-25, cols 33-39): bezel, glowing lens, hot core (frames)
    ploft(bm, o, [(13.6, 32.6, 39.4, 1.6, 2.65, 0.6), (25.4, 32.6, 39.4, 1.6, 2.65, 0.6)], met(114))
    rim = mats.slot(GLOW, "glow", frames=LAMP_RIM, part="lamp", glow=1.2)
    ploft(bm, o, [(14.2, 33.2, 38.8, 1.6, 2.72, 0.5), (24.8, 33.2, 38.8, 1.6, 2.72, 0.5)], rim)
    core = mats.slot(127, "glow", frames=LAMP_CORE, part="core", glow=2.0)
    ploft(bm, o, [(15.0, 34.0, 37.0, 2.0, 2.80, 0.4), (22.6, 34.0, 37.0, 2.0, 2.80, 0.4)], core)
    # vent slot under the lamp (row 25-26, cols 35-38)
    ploft(bm, o, [(25.3, 35.0, 38.0, 1.6, 2.36, 0.2), (26.2, 35.0, 38.0, 1.6, 2.36, 0.2)], met(64))
    # lower column (rows 32.6-44.3): narrower and lower, the pipe down its left, a slot between
    ploft(bm, o, [(32.4, 35.8, 39.8, -2.5, 1.3, 0.7), (44.4, 35.8, 39.8, -2.5, 1.3, 0.7)], met(112),
          top_mats={4: met(113), 3: met(114)})
    ploft(bm, o, [(32.4, 31.6, 33.4, -2.5, 0.7, 0.5), (44.4, 31.6, 33.4, -2.5, 0.7, 0.5)], met(112))
    cyl(bm, o, 34.4, 32.0, 44.6, 0.85, 0.7, met(116))
    # spine under the fins and foot
    ploft(bm, o, [(44.0, 32.6, 38.6, -2.5, 0.6, 0.5), (56.0, 32.6, 38.6, -2.5, 0.6, 0.5)], met(112))
    # cooling fins (rows 45, 47, 49, 51; dark gaps between)
    for r, ul, ur in ((45.0, 30.6, 39.8), (47.0, 30.8, 39.8), (49.0, 31.0, 39.8), (51.0, 31.4, 39.6)):
        ploft(bm, o, [(r + 0.05, ul + 0.4, ur - 0.4, -2.0, 1.8, 0.5), (r + 0.3, ul, ur, -2.0, 2.2, 0.6),
                      (r + 0.75, ul, ur, -2.0, 2.2, 0.6), (r + 1.0, ul + 0.4, ur - 0.4, -2.0, 1.8, 0.5)],
              met(114), top_mats={4: met(115)})
    # foot block (rows 53-61): stepped out at row 57
    ploft(bm, o, [(52.8, 32.4, 39.4, -2.5, 1.0, 0.6), (53.2, 32.0, 39.8, -2.5, 1.6, 0.7),
                  (56.6, 32.0, 39.8, -2.5, 1.6, 0.7), (57.0, 30.4, 40.6, -2.5, 1.9, 0.8),
                  (60.2, 30.4, 40.6, -2.5, 1.9, 0.8), (61.0, 31.0, 40.0, -2.5, 1.0, 0.6)], met(112),
          top_mats={4: met(113), 5: met(113), 3: met(114)})


def lamp_lines(mats, coll, piece_off):
    hot = mats.slot(127, "glow", part="line", glow=3.0)
    parts = []
    for frame, (r0, r1) in LAMP_LINE.items():
        bm = bmesh.new()
        ploft(bm, 0, [(r0, 34.9, 36.1, 2.0, 2.86, 0.25), (r1, 34.9, 36.1, 2.0, 2.86, 0.25)], hot)
        bmesh.ops.translate(bm, vec=(-piece_off[0], -piece_off[1], 0), verts=bm.verts)
        obj = common.mesh_object(f"newsh8-165-lamp-{frame}", bm, mats.mats, coll, smooth=False)
        parts.append(common.frame_part(obj, [frame]))
    return parts


# --- visibility for the ramp ------------------------------------------------------------------------

def visible_faces(obj):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    bvh = BVHTree.FromBMesh(bm)
    dirs = [Vector((0, 0, 1)), Vector((0, -math.sin(math.radians(32)), math.cos(math.radians(32)))),
            Vector((0, -0.8, 0.6)).normalized(), Vector((0, 0, -1)), Vector((0, 1, 0.3)).normalized(),
            Vector((1, 0, 0.2)).normalized(), Vector((-1, 0, 0.2)).normalized(), Vector((0, -1, 0))]
    out = []
    for f in bm.faces:
        c = f.calc_center_median()
        for d in dirs:
            if f.normal.dot(d) <= 0.02:
                continue
            hit = bvh.ray_cast(c + f.normal * 0.004 + d * 0.002, d, 30)
            if hit[0] is None:
                out.append(f.index)
                break
    bm.free()
    return out


# --- shell -----------------------------------------------------------------------------------------

def sink_shell(shell, model, margin, reach):
    """newshv-10.py's sink_shell (D185), copied: every shell vertex dropped to `margin` under the
    lowest model top within `reach` of it, seen from straight above, so the smoothed voxel shell never
    bridges the cracks between the stones (its back faces would draw ink across the top); x and y are
    untouched, so the silhouette ink is the same. Should be shared (common.py)."""
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    moved = 0
    for v in shell.data.vertices:
        w = v.co
        hit = tree.ray_cast(Vector((w.x, w.y, 5.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        zt = hit[0].z
        for k in range(12):
            a = 2 * math.pi * k / 12
            for rad in (0.35 * reach, 0.7 * reach, reach):
                h = tree.ray_cast(Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)), Vector((0, 0, -1)))
                if h[0] is not None:
                    zt = min(zt, h[0].z)
        zt -= margin
        if w.z > zt:
            v.co = Vector((w.x, w.y, zt))
            moved += 1
    shell.data.update()
    print(shell.name, "sunk", moved, "of", len(shell.data.vertices))


# --- split ------------------------------------------------------------------------------------------

def split_open(obj, layout, coll):
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
        for m in obj.data.materials:
            me.materials.append(m)
        s = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(s)
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        out[name] = s
    return out


# --- main -------------------------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    idx, inner, sprite = load()
    g = G(inner)
    coll = common.reset_collection(NAME)
    mats = Mats(sprite)
    mats.slot(MID)  # slot 0: the rock mid
    rnd = random.Random(243)
    # the ramp's sprite: the rock only (the pillars' reds and their bay are not rock shades)
    rpx = [row[:] for row in idx]
    for o in (0, 96):
        for r in range(3, 63):
            for c in range(o + 29, o + 41):
                rpx[r][c] = -1
    rsprite = dict(sprite, frames=[{"pixels": rpx, "width": GW, "height": GH}])
    cols = {}
    for key, (c0, _, _) in COLUMNS.items():
        bm = bmesh.new()
        build_core(bm, g, c0, mats)
        build_rock(bm, idx, inner, c0, mats, rnd)
        if key == "P":
            build_pillar(bm, c0, mats)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        obj = common.mesh_object(f"col_{key}", bm, mats.mats, coll, smooth=False)
        # D175 facet ramp on the visible rock faces
        vis = set(visible_faces(obj))
        rock_faces = [p.index for p in obj.data.polygons if p.material_index == 0 and p.index in vis
                      and p.normal.z > -0.3 and abs(p.normal.x) < 0.75]
        RK.facet_ramp(rsprite, g, obj, {"mid": MID, "ramp": RAMP, "metallic": 0.0, "roughness": 0.85},
                      faces=rock_faces)
        cols[key] = obj
    # every material on every column object (facet_ramp appends per object): unify by name
    allm = []
    for o in cols.values():
        for m in o.data.materials:
            if m not in allm:
                allm.append(m)
    for o in cols.values():
        remap = [allm.index(m) for m in o.data.materials]
        polys = [(p.index, remap[p.material_index]) for p in o.data.polygons]
        o.data.materials.clear()
        for m in allm:
            o.data.materials.append(m)
        for i, mi in polys:
            o.data.polygons[i].material_index = mi
    # place every column instance and join into the whole fortress
    inst = []
    for key, places in PLACES.items():
        for c in places:
            o = cols[key].copy()
            o.data = cols[key].data.copy()
            o.location = (X(c) - X(COLUMNS[key][0]), 0, 0)
            coll.objects.link(o)
            inst.append(o)
    for o in cols.values():
        bpy.data.objects.remove(o)
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in inst:
        o.select_set(True)
    bpy.context.view_layer.objects.active = inst[0]
    bpy.ops.object.transform_apply(location=True)
    bpy.ops.object.join()
    whole = bpy.context.view_layer.objects.active
    whole.name = NAME
    me = whole.data
    print(f"whole: {len(me.polygons)} triangles")
    closed = whole.copy()
    closed.data = whole.data.copy()
    fmt = "AUTO"
    if "--no-bake" not in argv:
        tint, textured = T.TINT, T.TEXTURED
        T.TINT, T.TEXTURED = (1.0, 1.0, 1.0), tuple(range(len(me.materials)))
        try:
            T.bake_maps(whole, tempfile.mkdtemp(prefix="n8_243A_bake_"), size=1024, samples=48)
        finally:
            T.TINT, T.TEXTURED = tint, textured
        for img in bpy.data.images:
            if img.name.startswith("talon_"):
                img.name = img.name.replace("talon_", f"{NAME}_")
        fmt = "WEBP"
    coll.objects.link(closed)
    shell = common.outline_shell(closed, coll, voxel=0.025, faces=22000, smooth=8, inside=0.004)
    shell.name = shell.data.name = f"{NAME}_outline"
    sink_shell(shell, closed, 0.5 * U, 1.3 * U)
    bpy.data.objects.remove(closed)
    bpy.context.view_layer.update()
    first = common.load_sprite(WT, "newsh8-243")
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in first["assemblyLayout"]]
    export_at = {}
    for key, places in PLACES.items():
        c = COLUMNS[key][0]
        for k, n in enumerate(PIECES[key]):
            export_at[n] = (c + 12 - 20 - CX0, [-17, 11, 39][k] - CY0)
    exp_layout = [(n, cx, cy) for n, (cx, cy) in export_at.items()]
    pieces = common.split_assembly(whole, exp_layout)
    shells = split_open(shell, exp_layout, coll)
    for q in pieces.values():
        q.data.set_sharp_from_angle(angle=math.radians(14))
        RK.set_facet_normals(q)
    cx, cy = export_at["newsh8-165"]
    lamp = lamp_lines(mats, coll, (cx / 12, -cy / 12))
    tris = {n: len(q.data.polygons) for n, q in pieces.items()}
    print("piece triangles", tris, "distinct total", sum(tris.values()))
    # the game's per-piece models: the piece, its shell slice (and newsh8-165's lamp-line frame parts)
    for name in export_at:
        objs_n = [pieces[name], shells[name]] + (lamp if name == "newsh8-165" else [])
        common.export_sprite_model(WT, objs_n, f"enemies/{name}", common.load_sprite(WT, name)["sprites"],
                                   image_format=fmt)
    if out is None:
        return
    # the review glb (--out): every layout entry, a copy of its piece (and shell, lamp lines) placed
    objs = []
    for i, (name, lx, ly) in enumerate(layout):
        for src in [pieces[name], shells[name]] + (lamp if name == "newsh8-165" else []):
            o = src.copy()
            o.data = src.data
            o.name = f"{src.name}@{i}"
            o.location = (lx / 12, -ly / 12, 0)
            coll.objects.link(o)
            objs.append(o)
    bpy.context.view_layer.update()
    common.export_glb(objs, out, image_format=fmt)
    (out.parent / "build_info.json").write_text(json.dumps({"triangles": tris, "distinct_total": sum(tris.values()),
                                                       "whole": len(me.polygons)}))
    print("wrote", out)


if __name__ == "__main__":
    main()
