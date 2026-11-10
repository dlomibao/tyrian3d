"""Wrecked ground station (D65 standard; built from design B plus the judge's grafts from design A) (newshu.shp, assembly of 7 pieces: newshu-1/3/5 over 39/41/43, 79 under
the middle; 72 x 84 px), design B: silhouette and readability from the small tilted game camera
first, then hard-surface detail.

The sprite is authoritative for the plan, the parts' places and their colours. The plan edge sits on
the INNER edge of the sprite's ink border (D74, docs/agents/OUTLINE-BORDER.md): the whole plan is
one allowed region F = the assembly's inner mask plus its thin-part (free) pixels, smoothed at 1/3 px
so the sprite's diagonals and round housings come out round, not stepped. Everything is built in
sprite px and then clipped to F by one boolean, so the see-through gaps of the wreck (the sprite's
transparent pixels inside the body and the turret) stay open to the ground and nothing overhangs the
outline. The deck under it all is a heightfield of F: vertical walls with a 45 degree chamfered top
edge, burnt dark plate (pal 2); the blue landing pad (pal 98) is a second, thin one.

Reading from the game camera, in three height bands:
- skyline (8-12 px): the periscope mast with its lit cap and red access strip, the purple crystal
  emitter lying north on its post, the generator drum with a domed lid;
- plant (4-6.5 px): red coolant stacks with sheared (broken) tops, grey equipment blocks, the grey
  frame with its red panel and corner bolts, the lens projector (D housing, bolted rim, purple lens
  bulging east with a light centre), the red wedge and the purple armour bar;
- debris (1.5-3 px): brown struts, purple plates, pipe runs with flanges, crates.
A stalk with a purple conduit runs south to the turret on the pad: base ring with ten bolts, a heavy
chamfered head, purple hatch with two red stripes, louvres, a red tank on two straps, a red box.

Hard-surface: chamfered sections everywhere (plan corners cut, top edges chamfered), modelled panel
grooves and bolts on the larger tops, flanged pipes, faceted crystal, smooth-shaded round parts.
Underside: closed and flat (it stands on the ground). Palette materials pal_<index> (blueprint's
measured index per region). Outline shell per piece (common.outline_shell, D51); optional AO /
roughness bake per piece (--bake; usp_talon-style bake, no concept projection, D50).

Run: blender --background --python assets/blender/enemies/assembly-newshu-79.py -- [--no-bake] [--review DIR]
Exports public/models/enemies/newshu-<n>.glb for the 7 pieces (each with its outline shell
<piece>_outline) and their src/render/spriteModels entries, like every assembly script.
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]  # repo root (the scripts live in assets/blender/enemies)
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "assets" / "blender" / "enemies"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import lib_b127 as lib  # noqa: E402  (read-only: material_settings, inset_outline, sheet_origin)
import sprite_mask as SM  # noqa: E402

NAME = "assembly-newshu-79"
PIECES = [1, 3, 5, 39, 41, 43, 79]
W, H = 72, 84
U = 19.0  # old script's Blender units -> px of height (x1.58 of 12: reads as a machine)
BLUE = set(range(96, 103))
SUB = 3  # heightfield lattice points per sprite px


def X(c):
    return (c - W / 2) / 12


def Y(r):
    return (H / 2 - r) / 12


# --------------------------------------------------------------------------------------------------
# Sprite, masks, materials
# --------------------------------------------------------------------------------------------------

def sprite_grid():
    idx, colors = SM.load(NAME)
    m = SM.masks(idx, colors)
    F = np.array(m["inner"], bool) | np.array(m["free"], bool)
    # Stray single pixels (the sprite's lone dots at col 0) are not part of the machine.
    P = np.array(idx)
    keep = F.copy()
    for r in range(H):
        for c in range(W):
            if F[r, c] and not F[max(0, r - 1):r + 2, max(0, c - 1):c + 2].sum() > 1:
                keep[r, c] = False
    return P, {int(k): v for k, v in colors.items()}, keep


class Mats:
    def __init__(self, colors):
        self.sprite = {"name": NAME, "colors": {str(k): list(v) for k, v in colors.items()}}
        self.settings = lib.material_settings()
        self.list, self.slots = [], {}

    def __call__(self, index):
        if index not in self.slots:
            kw = dict(metallic=0.4, roughness=0.5)
            kw.update(self.settings.get(index, {}))
            self.slots[index] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, "nshu79b", **kw))
        return self.slots[index]


# --------------------------------------------------------------------------------------------------
# Builder in sprite px (c east, r south, h up)
# --------------------------------------------------------------------------------------------------

def area_xy(pts):
    return sum(X(a[0]) * Y(b[1]) - X(b[0]) * Y(a[1]) for a, b in zip(pts, pts[1:] + pts[:1]))


def chamfer_outline(pts, ch):
    """Cut every corner of a closed outline by ch px."""
    if ch <= 0:
        return pts
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        for q, s in ((p0, 1), (p2, 0)):
            dx, dy = q[0] - p1[0], q[1] - p1[1]
            ln = math.hypot(dx, dy) or 1
            t = min(ch, ln * 0.45) / ln
            pt = (p1[0] + dx * t, p1[1] + dy * t)
            if s:
                out.append(pt)
            else:
                out.append(pt)
    return out


def inset_convex(pts, d):
    """Inset a convex outline (c, r px) by d: each edge's line moved inward, consecutive lines
    intersected; an edge that would turn over collapses to a point (vertex count kept)."""
    n = len(pts)
    ar = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
    sgn = 1 if ar > 0 else -1  # in (c, r) with r down: ar > 0 is clockwise on screen
    alive = [True] * n
    for _ in range(n):
        lines = []
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            ex, ey = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(ex, ey) or 1e-9
            nx, ny = -ey / ln * sgn, ex / ln * sgn  # inward normal
            lines.append(((a[0] + nx * d, a[1] + ny * d), (ex / ln, ey / ln)))
        idx = [i for i in range(n) if alive[i]]

        def meet(i, j):
            (p, u), (q, v) = lines[i], lines[j]
            den = u[0] * v[1] - u[1] * v[0]
            if abs(den) < 1e-9:
                return (p[0], p[1])
            t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
            return (p[0] + u[0] * t, p[1] + u[1] * t)
        verts = {}
        for k, i in enumerate(idx):
            prev = idx[k - 1]
            verts[i] = meet(prev, i)  # start vertex of edge i
        flipped = False
        for k, i in enumerate(idx):
            nxt = idx[(k + 1) % len(idx)]
            a, b = verts[i], verts[nxt]
            u = lines[i][1]
            if (b[0] - a[0]) * u[0] + (b[1] - a[1]) * u[1] < -1e-9 and len(idx) > 3:
                alive[i] = False
                flipped = True
                break
        if not flipped:
            break
    out = []
    for i in range(n):
        j = i
        while not alive[j]:
            j = (j + 1) % n
        out.append(verts[j])
    return out


class B:
    def __init__(self, mats):
        self.m = mats
        self.bm = bmesh.new()
        self.parts = []  # (element, pal, c0, c1, r0, r1) for the colour table

    def v(self, c, r, h):
        return self.bm.verts.new((X(c), Y(r), h / 12))

    def face(self, vs, pal, smooth=False):
        f = self.bm.faces.new(vs)
        f.material_index = self.m(pal)
        f.smooth = smooth
        return f

    def note(self, el, pal, pts):
        cs = [p[0] for p in pts]
        rs = [p[1] for p in pts]
        self.parts.append((el, pal, min(cs), max(cs), min(rs), max(rs)))

    # -- prisms --------------------------------------------------------------------------------
    def prism(self, outline, h0, h1, pal, bev=0.0, top=None, slope=(0.0, 0.0), panel=False, bolts=None,
              el=None, smooth=False):
        pts = [tuple(map(float, p)) for p in outline]
        if area_xy(pts) < 0:
            pts.reverse()
        n = len(pts)
        cx = sum(p[0] for p in pts) / n
        cy = sum(p[1] for p in pts) / n
        ztop = lambda c, r: h1 + slope[0] * (c - cx) + slope[1] * (r - cy)  # noqa: E731
        wmin = min(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
        bev = min(bev, (h1 - h0) * 0.45, wmin * 0.3)
        tp = pal if top is None else top
        lo = [self.v(c, r, h0) for c, r in pts]
        self.face(list(reversed(lo)), pal)
        if bev > 0.02:
            ins = inset_convex(pts, bev)
            mid = [self.v(c, r, ztop(c, r) - bev) for c, r in pts]
            hi = [self.v(c, r, ztop(c, r)) for c, r in ins]
            for i in range(n):
                j = (i + 1) % n
                self.face((lo[i], lo[j], mid[j], mid[i]), pal, smooth)
                self.face((mid[i], mid[j], hi[j], hi[i]), pal, smooth)
            topf = self.face(hi, tp)
            inner = ins
        else:
            hi = [self.v(c, r, ztop(c, r)) for c, r in pts]
            for i in range(n):
                j = (i + 1) % n
                self.face((lo[i], lo[j], hi[j], hi[i]), pal, smooth)
            topf = self.face(hi, tp)
            inner = pts
        if el:
            self.note(el, tp, pts)
        if panel and slope == (0, 0) or panel and tuple(slope) == (0.0, 0.0):
            # A machined cover plate standing 0.14 px proud, 0.5 px inside the top's edge: the step
            # reads as the panel seam from the game camera.
            ip = inset_convex(inner, 0.5)
            self.prism(ip, h1 - 0.05, h1 + 0.14, tp, 0.07)
        if bolts:
            # Bolts just inside the top's corners (bolts = palette index).
            pts2 = inset_convex(inner, 0.55)
            corners = pts2 if len(pts2) <= 4 else pts2[::max(1, len(pts2) // 4)][:4]
            for c, r in corners:
                self.bolt(c, r, ztop(c, r), bolts)
        return topf

    def groove(self, f, inset, width, depth):
        """A modelled panel line: a groove `width` px wide, `inset` px inside the face's edge."""
        bm = self.bm
        try:
            f.normal_update()
            nrm = f.normal.copy()
            bmesh.ops.inset_region(bm, faces=[f], thickness=inset / 12, depth=0.0, use_even_offset=True)
            bmesh.ops.inset_region(bm, faces=[f], thickness=width * 0.5 / 12, depth=-depth / 12, use_even_offset=True)
            bmesh.ops.inset_region(bm, faces=[f], thickness=width * 0.5 / 12, depth=0.0, use_even_offset=True)
            bmesh.ops.translate(bm, vec=nrm * (depth / 12), verts=list(f.verts))
        except Exception as err:  # noqa: BLE001
            print("groove skipped", err)

    def box(self, c0, c1, r0, r1, h0, h1, pal, bev=0.0, top=None, ch=None, panel=None, bolts=None, slope=(0, 0),
            el=None):
        """Box over INCLUSIVE pixel columns c0..c1 / rows r0..r1 (fractions allowed), heights px."""
        a, b, c, d = c0, c1 + 1, r0, r1 + 1
        w, dd = b - a, d - c
        if ch is None:
            ch = 0.3 if min(w, dd) >= 1.9 else (0.15 if min(w, dd) >= 0.9 else 0.0)
        if panel is None:
            panel = w >= 3 and dd >= 3 and h1 - h0 >= 2.5
        out = chamfer_outline([(a, c), (b, c), (b, d), (a, d)], ch)
        return self.prism(out, h0, h1, pal, bev, top, slope, panel, bolts, el)

    def ub(self, c0, c1, r0, r1, z0, z1, pal, bev=0.0, top=None, **kw):
        """Box with heights in the old script's units (x U px)."""
        return self.box(c0, c1, r0, r1, z0 * U, z1 * U, pal, bev, top, **kw)

    def cyl(self, c, r, rad, h0, h1, pal, n=16, bev=0.0, top=None, sx=1.0, sy=1.0, el=None):
        out = [(c + rad * sx * math.cos(2 * math.pi * (i + 0.5) / n), r + rad * sy * math.sin(2 * math.pi * (i + 0.5) / n))
               for i in range(n)]
        return self.prism(out, h0, h1, pal, bev, top, el=el, smooth=True)

    def belt(self, c0, c1, r0, r1, h, pal, t=0.45):
        """A machined clamp band round a box over inclusive px c0..c1 / r0..r1 at height h px: stands
        0.15 px proud of the walls, chamfered (the panel seam of a coolant stack)."""
        self.box(c0 - 0.15, c1 + 0.15, r0 - 0.15, r1 + 0.15, h, h + t, pal, 0.1, ch=0.25, panel=False)

    def bolt(self, c, r, h, pal=9, rad=0.24):
        self.cyl(c, r, rad, h - 0.1, h + 0.22, pal, n=6, bev=0.06)

    # -- lofts ---------------------------------------------------------------------------------
    def loft(self, axis, at, secs, pal, sides=12, chamfer=True, el=None):
        """Sections (pos, half-width px, half-height px, centre height px) along rows ('y', at a column
        edge) or columns ('x', at a row edge); elliptic, capped, ends chamfered."""
        secs = [tuple(s) for s in secs]
        if chamfer and len(secs) >= 2:
            p0, p1 = secs[0][0], secs[-1][0]
            ln = abs(p1 - p0)
            d = min(0.25, ln * 0.12) * (1 if p1 > p0 else -1)
            out = []
            s0 = secs[0]
            if s0[1] > 0:
                out += [(s0[0], s0[1] * 0.78, s0[2] * 0.78, s0[3]), (s0[0] + d, s0[1], s0[2], s0[3])]
            else:
                out.append(s0)
            out += secs[1:-1]
            s1 = secs[-1]
            if s1[1] > 0:
                out += [(s1[0] - d, s1[1], s1[2], s1[3]), (s1[0], s1[1] * 0.78, s1[2] * 0.78, s1[3])]
            else:
                out.append(s1)
            secs = out
        rings = []
        for p, w, hh, z in secs:
            if w == 0 and hh == 0:
                rings.append([(at, p, z) if axis == "y" else (p, at, z)])
                continue
            ring = []
            for i in range(sides):
                a = 2 * math.pi * (i + 0.5) / sides
                u, vv = w * math.cos(a), z + hh * math.sin(a)
                ring.append((at + u, p, vv) if axis == "y" else (p, at + u, vv))
            rings.append(ring)
        R = [[self.v(*q) for q in ring] for ring in rings]
        for A, Bq in zip(R, R[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                if len(A) == 1:
                    self.face((A[0], Bq[j], Bq[i]), pal, True)
                elif len(Bq) == 1:
                    self.face((A[i], A[j], Bq[0]), pal, True)
                else:
                    self.face((A[i], A[j], Bq[j], Bq[i]), pal, True)
        for ring in (R[0], R[-1]):
            if len(ring) > 1:
                self.face(ring, pal)
        if el:
            pts = []
            for p, w, hh, z in secs:
                pts += [(at - w, p), (at + w, p)] if axis == "y" else [(p, at - w), (p, at + w)]
            self.note(el, pal, pts)

    def uloft(self, axis, at, secs, pal, sides=12, **kw):
        self.loft(axis, at, [(p, w, h * U, z * U) for p, w, h, z in secs], pal, sides, **kw)

    def pipe(self, axis, at, p0, p1, rad, z, pal, flange=None, sides=12, el=None, bands=()):
        """A pipe with chamfered ends; flange rings (palette `flange`, with chamfered edges) a little in
        from each end, plus collars at `bands` positions along it (design A's profile)."""
        e = min(0.25, (p1 - p0) * 0.1)
        self.loft(axis, at, [(p0, rad * 0.8, rad * 0.8, z), (p0 + e, rad, rad, z), (p1 - e, rad, rad, z),
                             (p1, rad * 0.8, rad * 0.8, z)], pal, sides, chamfer=False, el=el)
        if flange is not None:
            for p in [p0 + 0.35, p1 - 0.35] + list(bands):
                self.loft(axis, at, [(p - 0.28, rad * 1.18, rad * 1.18, z), (p - 0.2, rad * 1.3, rad * 1.3, z),
                                     (p + 0.2, rad * 1.3, rad * 1.3, z), (p + 0.28, rad * 1.18, rad * 1.18, z)],
                          flange, sides, chamfer=False)

    def dome(self, c, r, h, rx, ry, rz, pal, sides=16, rings=5):
        L = []
        for k in range(rings):
            f = math.pi / 2 * k / rings
            s, zz = math.cos(f), math.sin(f)
            L.append([self.v(c + rx * s * math.cos(2 * math.pi * (i + .5) / sides),
                             r + ry * s * math.sin(2 * math.pi * (i + .5) / sides), h + rz * zz) for i in range(sides)])
        apex = self.v(c, r, h + rz)
        self.face(list(reversed(L[0])), pal)
        for A, Bq in zip(L, L[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                self.face((A[i], A[j], Bq[j], Bq[i]), pal, True)
        for i in range(sides):
            self.face((L[-1][i], L[-1][(i + 1) % sides], apex), pal, True)

    def finish(self, name, coll, weld=True):
        bm = self.bm
        if weld:
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in self.m.list:
            me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        return o


# --------------------------------------------------------------------------------------------------
# Heightfields (deck, pad, cutter) from a pixel mask, smoothed
# --------------------------------------------------------------------------------------------------

PAD = 4  # px of padding round the grid


def smooth_field(mask, sigma_px=0.33, pad_value=0.0):
    """The mask supersampled SUB x and blurred: values at lattice points (sample centres)."""
    big = np.kron(np.pad(mask.astype(np.float32), PAD, constant_values=pad_value), np.ones((SUB, SUB), np.float32))
    s = sigma_px * SUB
    k = np.arange(-int(3 * s) - 1, int(3 * s) + 2)
    g = np.exp(-0.5 * (k / s) ** 2)
    g /= g.sum()
    big = np.apply_along_axis(lambda a: np.convolve(a, g, "same"), 0, big)
    big = np.apply_along_axis(lambda a: np.convolve(a, g, "same"), 1, big)
    return big


def lattice_cr(i, j):
    return (j + 0.5) / SUB - PAD, (i + 0.5) / SUB - PAD


def inside_distance(ins):
    """Chamfer (3-4) distance in lattice steps from each inside point to the nearest outside point."""
    hgt, wid = ins.shape
    big = 10 ** 6
    d = np.where(ins, big, 0).astype(np.int64)
    for i in range(hgt):
        for j in range(wid):
            if d[i, j]:
                m = d[i, j]
                if i > 0:
                    m = min(m, d[i - 1, j] + 3)
                    if j > 0:
                        m = min(m, d[i - 1, j - 1] + 4)
                    if j + 1 < wid:
                        m = min(m, d[i - 1, j + 1] + 4)
                if j > 0:
                    m = min(m, d[i, j - 1] + 3)
                d[i, j] = m
    for i in range(hgt - 1, -1, -1):
        for j in range(wid - 1, -1, -1):
            if d[i, j]:
                m = d[i, j]
                if i + 1 < hgt:
                    m = min(m, d[i + 1, j] + 3)
                    if j > 0:
                        m = min(m, d[i + 1, j - 1] + 4)
                    if j + 1 < wid:
                        m = min(m, d[i + 1, j + 1] + 4)
                if j + 1 < wid:
                    m = min(m, d[i, j + 1] + 3)
                d[i, j] = m
    return d / 3.0  # lattice steps


def dilate(mask):
    """4-neighbour dilation by one pixel."""
    d = mask.copy()
    d[1:] |= mask[:-1]
    d[:-1] |= mask[1:]
    d[:, 1:] |= mask[:, :-1]
    d[:, :-1] |= mask[:, 1:]
    return d


def plate_field(mask, sigma_px=0.75, grow=0):
    """Field for the dark plates (deck, pad): blurred wide enough that the sprite's pixel stairs,
    1 px notches and 1 px islands go (fix round 1), but never more than `grow` px past the mask, so
    the plan stays on the sprite. Contoured with a coarser tolerance this gives straight runs with
    cut corners instead of a staircase."""
    lim = mask
    for _ in range(grow):
        lim = dilate(lim)
    return np.minimum(smooth_field(mask, sigma_px), smooth_field(lim, 0.4))


def heightfield(b, field, hz, ch, pal, top=None, z0=0.0):
    """A closed slab over field >= 0.5: flat bottom at z0, walls, a ch px 45 degree chamfer and a flat
    top at hz (px). Marching squares at the lattice; coplanar faces dissolved afterwards."""
    bm = b.bm
    ins = field >= 0.5
    dist = inside_distance(ins) / SUB if ch > 0 else np.full(ins.shape, 99.0)  # px
    hgt, wid = field.shape
    tv, bv, ev = {}, {}, {}
    tp = pal if top is None else top
    first = len(bm.faces)

    def zt(i, j):
        d = dist[i, j]
        return z0 + (hz - ch + min(ch, d - 0.5 / SUB)) if ch > 0 else z0 + hz

    def top_v(i, j):
        if (i, j) not in tv:
            c, r = lattice_cr(i, j)
            tv[(i, j)] = b.v(c, r, zt(i, j))
        return tv[(i, j)]

    def bot_v(i, j):
        if (i, j) not in bv:
            c, r = lattice_cr(i, j)
            bv[(i, j)] = b.v(c, r, z0)
        return bv[(i, j)]

    def edge_v(a, bb):
        key = (min(a, bb), max(a, bb))
        if key not in ev:
            fa, fb = field[a], field[bb]
            t = (0.5 - fa) / (fb - fa)
            ca, ra = lattice_cr(*a)
            cb, rb = lattice_cr(*bb)
            ev[key] = b.v(ca + (cb - ca) * t, ra + (rb - ra) * t, z0)
        return ev[key]

    mi_side, mi_top = b.m(pal), b.m(tp)
    for i in range(hgt - 1):
        for j in range(wid - 1):
            cn = [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]
            flags = [ins[p] for p in cn]
            k = sum(flags)
            if k == 0:
                continue
            tpoly, bpoly = [], []
            for e in range(4):
                A, Bp = cn[e], cn[(e + 1) % 4]
                if flags[e]:
                    tpoly.append(top_v(*A))
                    bpoly.append(bot_v(*A))
                if flags[e] != flags[(e + 1) % 4]:
                    ev_ = edge_v(A, Bp)
                    tpoly.append(ev_)
                    bpoly.append(ev_)
            if len(tpoly) < 3:
                continue
            try:
                f = bm.faces.new(tpoly)
                f.material_index = mi_top if k == 4 and all(dist[p] - 0.5 / SUB >= ch - 1e-6 for p in cn) else mi_side
            except ValueError:
                pass
            if k == 4:
                try:
                    f = bm.faces.new(list(reversed(bpoly)))
                    f.material_index = mi_side
                except ValueError:
                    pass
            else:
                # bottom of a boundary cell: only the inside corners and the crossings, at z0
                try:
                    f = bm.faces.new(list(reversed(bpoly)))
                    f.material_index = mi_side
                except ValueError:
                    pass
    # walls: boundary cells' top polygons run from the crossing (z0) up to the inside points
    faces = bm.faces[:] if hasattr(bm.faces, "__getitem__") else list(bm.faces)
    bm.faces.ensure_lookup_table()
    new = [bm.faces[k] for k in range(first, len(bm.faces))]
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.6), use_dissolve_boundaries=False,
                             verts=list({v for f in new for v in f.verts}), edges=list({e for f in new for e in f.edges}),
                             delimit={"MATERIAL"})
    del faces


def contour_loops(field, tol=0.07):
    """Closed contour loops (lists of (c, r) px) of field = 0.5, marching squares at the lattice,
    simplified (Douglas-Peucker, tol px)."""
    hgt, wid = field.shape
    ins = field >= 0.5

    def pos(key):
        kind, i, j = key
        a = (i, j)
        bq = (i, j + 1) if kind == "h" else (i + 1, j)
        fa, fb = field[a], field[bq]
        t = (0.5 - fa) / (fb - fa)
        ca, ra = lattice_cr(*a)
        cb, rb = lattice_cr(*bq)
        return (ca + (cb - ca) * t, ra + (rb - ra) * t)

    adj = {}

    def seg(a, bq):
        adj.setdefault(a, []).append(bq)
        adj.setdefault(bq, []).append(a)

    for i in range(hgt - 1):
        for j in range(wid - 1):
            fl = (ins[i, j], ins[i, j + 1], ins[i + 1, j + 1], ins[i + 1, j])
            k = sum(fl)
            if k == 0 or k == 4:
                continue
            E = [("h", i, j), ("v", i, j + 1), ("h", i + 1, j), ("v", i, j)]  # top right bottom left
            cross = [e for e in range(4) if fl[e] != fl[(e + 1) % 4]]
            # corner e sits between edge (e-1) and edge e: TL=0 between left(3)/top(0), TR=1 top/right ...
            if len(cross) == 2:
                seg(E[cross[0]], E[cross[1]])
            else:
                centre = field[i:i + 2, j:j + 2].mean() >= 0.5
                if fl[0]:  # TL and BR inside
                    if centre:
                        seg(E[0], E[1]); seg(E[2], E[3])  # cut off TR and BL
                    else:
                        seg(E[3], E[0]); seg(E[1], E[2])  # cut round TL and BR
                else:  # TR and BL inside
                    if centre:
                        seg(E[3], E[0]); seg(E[1], E[2])
                    else:
                        seg(E[0], E[1]); seg(E[2], E[3])
    loops, seen = [], set()
    for start in adj:
        if start in seen:
            continue
        loop, prev, cur = [start], None, start
        seen.add(start)
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            loop.append(cur)
        if len(loop) >= 3:
            loops.append([pos(k) for k in loop])
    return [dp_closed(lp, tol) for lp in loops]


def dp_closed(pts, tol):
    n = len(pts)
    if n < 6:
        return pts
    far = max(range(n), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)

    def dp(seq):
        if len(seq) < 3:
            return seq
        (x0, y0), (x1, y1) = seq[0], seq[-1]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1e-9
        best, bi = -1, 0
        for i in range(1, len(seq) - 1):
            d = abs(dy * (seq[i][0] - x0) - dx * (seq[i][1] - y0)) / ln
            if d > best:
                best, bi = d, i
        if best <= tol:
            return [seq[0], seq[-1]]
        return dp(seq[:bi + 1])[:-1] + dp(seq[bi:])

    a = dp(pts[:far + 1])
    b = dp(pts[far:] + [pts[0]])
    return a[:-1] + b[:-1]


def field_at(field, c, r):
    """Bilinear field value at (c, r) px."""
    x = (c + PAD) * SUB - 0.5
    y = (r + PAD) * SUB - 0.5
    j, i = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - j, y - i
    hgt, wid = field.shape
    i, j = max(0, min(hgt - 2, i)), max(0, min(wid - 2, j))
    return ((1 - fx) * (1 - fy) * field[i, j] + fx * (1 - fy) * field[i, j + 1]
            + (1 - fx) * fy * field[i + 1, j] + fx * fy * field[i + 1, j + 1])


def slab(b, field, hz, ch, pal, top=None, z0=0.0, tol=0.07, min_area=0.35):
    """A closed slab over field >= 0.5 from contour loops: walls, a ch px 45 degree chamfer, a flat
    top (scanfill, holes kept) and a flat bottom."""
    bm = b.bm
    tp = pal if top is None else top
    lo_loops, hi_loops = [], []
    for lp in contour_loops(field, tol):
        if len(lp) < 3:
            continue
        ar = 0.5 * sum(a[0] * bq[1] - bq[0] * a[1] for a, bq in zip(lp, lp[1:] + lp[:1]))
        # Is the loop's own interior solid (an outer edge) or empty (a hole)?
        ins_test = lib.inset_outline(lp, 0.12)
        k = max(range(len(lp)), key=lambda i: 0)  # noqa: F841
        solid = field_at(field, *ins_test[len(lp) // 2]) >= 0.5
        if abs(ar) < min_area and solid:
            continue
        d = ch if solid else -ch
        if abs(ar) < 1.5:
            d *= 0.4
        hi_xy = lib.inset_outline(lp, d) if ch > 0 else lp
        # The chamfer's top edge must stay inside the plate: near a thin wall (a hole close to the
        # edge) a full inset crosses the next loop and the top fill loses the hole. Shrink it there.
        for k in (0.5, 0.25, 0.0):
            if ch <= 0 or all(field_at(field, c, r) >= 0.55 for c, r in hi_xy):
                break
            hi_xy = lib.inset_outline(lp, d * k) if k > 0 else lp
        lo = [b.v(c, r, z0) for c, r in lp]
        if ch > 0:
            mid = [b.v(c, r, z0 + hz - ch) for c, r in lp]
        hi = [b.v(c, r, z0 + hz) for c, r in hi_xy]
        n = len(lp)
        for i in range(n):
            j = (i + 1) % n
            if ch > 0:
                b.face((lo[i], lo[j], mid[j], mid[i]), pal)
                b.face((mid[i], mid[j], hi[j], hi[i]), pal)
            else:
                b.face((lo[i], lo[j], hi[j], hi[i]), pal)
        lo_loops.append(lp)
        hi_loops.append(hi_xy)
    fill_loops(b, hi_loops, z0 + hz, tp)
    fill_loops(b, lo_loops, z0, pal)


def fill_loops(b, loops, z, pal):
    """Fill closed (c, r) loops at height z px, holes by even-odd (a 2D curve's fill), into b."""
    cu = bpy.data.curves.new("fill", "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    for lp in loops:
        sp = cu.splines.new("POLY")
        sp.points.add(len(lp) - 1)
        for p, (c, r) in zip(sp.points, lp):
            p.co = (X(c), Y(r), 0.0, 1.0)
        sp.use_cyclic_u = True
    ob = bpy.data.objects.new("fill", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    vs = [b.bm.verts.new((v.co.x, v.co.y, z / 12)) for v in me.vertices]
    for poly in me.polygons:
        try:
            f = b.bm.faces.new([vs[i] for i in poly.vertices])
            f.material_index = b.m(pal)
        except ValueError:
            pass
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)


# --------------------------------------------------------------------------------------------------
# The machine (blueprint layout, hard-surface parts)
# --------------------------------------------------------------------------------------------------

def build_parts(b):
    K = U / 13
    # ---- skyline: sensor masts (rows 0-19) ----
    # Periscope mast: grey post, lit cap, red access strip, snapped antenna stub, machined bands.
    b.ub(30, 32, 5, 17, 0.0, 0.46, 8, 0.5, el="mast_periscope")
    for hb in (2.6, 5.6):
        b.box(29.85, 32.15, 5.4, 16.6, hb, hb + 0.45, 7, 0.12, ch=0.35, panel=False)
    b.uloft("y", 31.5, [(4.6, 1.5, 0.05, 0.43), (5.2, 1.6, 0.06, 0.44), (8.5, 1.6, 0.06, 0.44),
                        (9.2, 1.3, 0.04, 0.44)], 10, 12, el="periscope_cap")
    b.ub(31, 32, 11, 16, 0.38, 0.475, 72, 0.3, 70, el="periscope_strip")
    b.cyl(31.5, 6.6, 0.45, 5.9 * K, 8.4 * K, 9, 8, bev=0.12)
    b.cyl(31.5, 6.6, 0.62, 5.9 * K - 0.3, 5.9 * K + 0.4, 7, 8, bev=0.1)
    # Red conduit column below it with two clamps.
    b.ub(31, 32, 17, 26, 0.0, 0.3, 71, 0.4, 72, el="conduit_red")
    for r in (19.5, 23.5):
        b.box(30.8, 32.2, r, r + 0.4, 0, 4.2 * K, 70, 0.1, ch=0.1)
    b.ub(36, 37, 15, 19, 0.0, 0.34, 73, 0.4, 73, el="post_red_small")
    b.ub(34, 34, 17, 19, 0.0, 0.22, 8, 0.3, el="stub_grey")
    # Crystal emitter: grey post + rail, faceted purple crystal lying north to a point, two cradle bands.
    b.ub(40, 43, 10, 12, 0.0, 0.42, 5, 0.4, 6, el="mast_crystal_post")
    b.ub(43, 43, 5, 12, 0.0, 0.38, 6, 0.3, el="mast_crystal_rail")
    b.uloft("y", 41.5, [(10.0, 1.5, 0.07, 0.43), (7.0, 1.6, 0.08, 0.44), (4.0, 1.5, 0.07, 0.45),
                        (2.0, 1.0, 0.05, 0.45), (0.4, 0, 0, 0.45)], 91, 6, el="crystal")
    for r in (8.2, 5.2):
        b.box(39.8, 43.2, r, r + 0.4, 4.6 * K, 5.3 * K, 89, 0.1, ch=0.1, panel=False)
    b.ub(44, 45, 6, 12, 0.0, 0.4, 73, 0.5, 73, slope=(0, 0.04), el="pillar_red")
    b.ub(41, 45, 13, 16, 0.0, 0.40, 70, 0.5, 72, bolts=7, el="block_red")
    b.belt(41, 45, 13, 16, 3.6, 69)
    b.ub(41, 43, 17, 18, 0.0, 0.26, 10, 0.3, el="block_red_grey")
    b.ub(44, 45, 17, 18, 0.0, 0.3, 69, 0.3)
    # Generator drum: rounded-square housing, lid, domed cap, a ring of bolts.
    rr = rrect(47.2, 12.6, 53.9, 20.4, 1.6)
    b.prism(rr, 0, 4.0 * K, 4, 0.4, 5, el="drum_housing", smooth=True)
    b.prism(rrect(47.9, 13.4, 53.2, 19.6, 1.2), 4.0 * K, 4.4 * K, 6, 0.25, 6, el="drum_lid", smooth=True)
    b.prism(rrect(47.0, 12.4, 54.1, 20.6, 1.7), 1.6 * K, 2.2 * K, 5, 0.15, smooth=True)  # strap band
    b.dome(50.6, 16.5, 4.4 * K, 1.2, 1.2, 0.6 * K, 9, 12, 4)
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        b.bolt(50.55 + 2.05 * math.cos(a), 16.5 + 2.55 * math.sin(a), 4.4 * K, 7, 0.2)
    b.uloft("y", 42.5, [(19.0, 1.6, 0.13, 0.13), (25.0, 1.6, 0.13, 0.13)], 5, 12, el="column_grey")

    # ---- upper-left wreckage: coolant stacks with sheared tops, struts ----
    b.ub(20, 22, 19, 22, 0.0, 0.34, 9, 0.4, 8, slope=(0.0, 0.25), el="stack_left_A")
    b.ub(21, 22, 22, 26, 0.0, 0.3, 72, 0.4, 72, slope=(-0.3, 0.0), el="stack_left_B")
    b.belt(21, 22, 22, 26, 2.2, 70)
    b.ub(20, 20, 23, 26, 0.0, 0.26, 71, 0.3)
    b.ub(17, 20, 25, 30, 0.0, 0.28, 72, 0.5, 72, slope=(0.0, -0.2), el="stack_left_C")
    b.belt(17, 20, 25, 30, 1.6, 70)
    b.belt(17, 20, 25, 30, 3.2, 70, 0.3)
    b.ub(18, 19, 28, 29, 0.27, 0.29, 76, slope=(0.0, -0.2))
    b.ub(16, 16, 29, 30, 0.0, 0.2, 8, 0.3)
    b.ub(27, 27, 20, 26, 0.0, 0.18, 162, 0.3, el="strut_brown")
    b.ub(28, 30, 24, 26, 0.0, 0.22, 70, 0.3, 69, slope=(0.35, 0), el="stub_red_mid")
    b.ub(8, 9, 26, 32, 0.0, 0.34, 72, 0.5, 72, slope=(0, 0.18), el="stack_far_left")
    b.belt(8, 9, 26, 32, 2.0, 70)
    b.ub(22, 23, 28, 30, 0.0, 0.14, 162, 0.3, 19, el="debris")
    b.ub(24, 27, 30, 30, 0.0, 0.18, 72, 0.3, 72)
    b.ub(25, 27, 31, 32, 0.0, 0.12, 162, 0.3, 19)
    b.ub(20, 20, 31, 33, 0.0, 0.2, 70, 0.3, 70)
    b.ub(21, 22, 33, 36, 0.0, 0.1, 162, 0.3)
    b.ub(27, 29, 35, 36, 0.0, 0.2, 71, 0.3, 72)
    b.ub(28, 28, 31, 33, 0.0, 0.14, 162, 0.3)
    b.ub(10, 10, 29, 32, 0.0, 0.14, 19, 0.2)

    # ---- grey blocks under the periscope ----
    b.ub(32, 37, 20, 27, 0.0, 0.2, 5, 0.4, 5, panel=False, el="block_grey_A")
    b.box(34.0, 36.6, 20.6, 22.0, 0.2 * U - 0.2, 0.2 * U + 0.3, 6, 0.12, ch=0.2, panel=False)  # access hatch
    b.ub(32, 33, 23, 28, 0.0, 0.3, 11, 0.4, 11, el="block_grey_B")
    b.ub(33, 37, 23, 23, 0.0, 0.25, 11, 0.3)
    b.ub(35, 36, 24, 26, 0.0, 0.27, 7, 0.3, 10)
    b.ub(38, 41, 24, 25, 0.0, 0.22, 8, 0.3, 8, el="block_grey_C")
    b.ub(37, 41, 26, 26, 0.0, 0.24, 73, 0.3, 73, el="bar_red")
    b.ub(42, 43, 25, 30, 0.0, 0.32, 72, 0.4, 72, slope=(0, 0.12), el="stack_red_mid")
    b.belt(42, 43, 25, 30, 2.4, 70)
    b.ub(40, 41, 28, 31, 0.0, 0.26, 6, 0.3, 6, el="block_grey_D")

    # ---- right block: grey frame with red panel, pipe run ----
    b.ub(47, 54, 20, 28, 0.0, 0.3, 3, 0.5, 4, panel=False, el="frame_right")
    b.ub(50, 52, 22, 27, 0.0, 0.33, 72, 0.4, 70, el="frame_panel")
    for c, r in ((48, 21), (48, 27.6), (53.8, 21), (53.8, 27.6)):
        b.bolt(c, r, 0.3 * U)
    b.ub(54, 54, 20, 30, 0.0, 0.32, 8, 0.3, el="frame_rail")
    b.ub(44, 46, 20, 27, 0.0, 0.16, 3, 0.3, el="frame_skirt")
    for r in (21.0, 22.6, 24.2, 25.8):  # louvre slats across the skirt
        b.box(44.3, 45.7, r, r + 0.15, 0.16 * U, 0.16 * U + 0.35, 5, 0.08, ch=0.1, panel=False)
    b.pipe("x", 30.4, 44.6, 54.4, 1.4, 0.14 * U, 8, 6, el="pipe_A")
    b.pipe("x", 33.6, 40.4, 55.5, 1.5, 0.15 * U, 8, 6, el="pipe_B")
    b.pipe("x", 33.6, 49.8, 52.6, 1.7, 0.15 * U, 8, 6, bands=(51.2,), el="pipe_sleeve")
    b.pipe("y", 42.5, 34.6, 45.0, 1.4, 0.13 * U, 5, 8, el="riser")
    b.ub(43, 46, 35, 37, 0.0, 0.24, 5, 0.4, 7, el="junction_box")
    b.ub(44, 46, 38, 44, 0.0, 0.2, 69, 0.3, 70, bolts=7, el="tank_red_low")
    b.belt(44, 46, 38, 44, 1.5, 68, 0.35)
    b.ub(47, 48, 39, 42, 0.0, 0.16, 3, 0.3)
    b.ub(49, 53, 39, 43, 0.0, 0.18, 70, 0.3, 73, el="pump_red")
    b.ub(50, 53, 39, 40, 0.0, 0.24, 73, 0.4, 73, el="pump_lid")
    b.ub(52, 54, 36, 37, 0.0, 0.16, 7, 0.3)

    # ---- middle: armour box, red wedge, purple bar, drum ----
    b.ub(36, 39, 29, 32, 0.0, 0.34, 90, 0.5, 91, bolts=88, el="armour_box")
    b.ub(36, 39, 33, 33, 0.0, 0.2, 82, 0.3)
    b.prism([(35, 35), (39, 35), (39, 44), (38, 44), (35, 41)], 0.0, 0.3 * U, 69, 0.5, 69, el="wedge_red")
    b.ub(36.3, 38.6, 35, 35, 0.28, 0.315, 73)
    b.ub(25, 33, 39, 42, 0.0, 0.26, 90, 0.6, 90, el="bar_purple")
    b.uloft("x", 42.4, [(25.3, 0.7, 0.04, 0.24), (33.7, 0.7, 0.04, 0.24)], 93, 6)
    b.ub(25, 33, 43, 43, 0.0, 0.16, 86, 0.3, el="bar_purple_foot")
    for c in (26.2, 32.8):
        b.bolt(c, 40, 0.26 * U, 88)
    b.pipe("x", 36.6, 29.6, 34.2, 2.0, 0.14 * U, 6, 5, el="drum_mid")
    b.ub(29, 31, 31, 33, 0.0, 0.16, 68, 0.3, el="debris_mid")
    b.ub(29, 30, 32, 33, 0.0, 0.2, 73, 0.3, 73)
    b.pipe("x", 37.5, 22.2, 28.8, 0.9, 0.07 * U, 164, 162, el="pipe_salmon")
    b.ub(22, 28, 38, 38, 0.0, 0.08, 164, 0.2)
    b.ub(27, 28, 29, 30, 0.0, 0.18, 72, 0.3, 72)

    # ---- left: red stubs, grey block, purple plates ----
    b.ub(20, 23, 40, 43, 0.0, 0.30, 72, 0.4, 72, bolts=7, el="tank_red_left")
    b.belt(20, 23, 40, 43, 2.4, 70)
    b.uloft("x", 43.5, [(20.6, 0.6, 0.05, 0.2), (23.6, 0.6, 0.05, 0.2)], 76, 8)
    b.ub(18, 19, 40, 41, 0.0, 0.16, 71, 0.3)
    b.ub(19, 23, 44, 46, 0.0, 0.12, 19, 0.3, el="crate_brown")
    b.ub(26, 27, 45, 46, 0.0, 0.12, 19, 0.3, 19)
    b.ub(16, 20, 34, 37, 0.0, 0.26, 6, 0.4, 8, el="block_grey_left")
    b.ub(12, 15, 31, 32, 0.0, 0.28, 72, 0.4, 72, el="stub_red_left")
    b.ub(12, 15, 33, 34, 0.0, 0.1, 19, 0.3)
    b.ub(8, 10, 33, 39, 0.0, 0.26, 84, 0.5, 88, el="plate_purple_A")
    b.ub(11, 15, 39, 42, 0.0, 0.2, 88, 0.5, el="plate_purple_B")
    b.ub(12, 14, 36, 38, 0.0, 0.12, 82, 0.3, 82)

    # ---- lens projector (east end) ----
    rim = [(55.0, 29.0), (66.0, 29.0), (68.5, 30.5), (70.3, 33.0), (71.0, 35.5), (70.3, 38.5), (68.5, 40.3),
           (66.0, 41.4), (55.0, 41.4)]
    b.prism(rim, 0.0, 0.24 * U, 4, 0.6, 5, el="lens_housing")
    b.uloft("x", 35.6, [(56.0, 3.7, 0.09, 0.22), (58.0, 3.85, 0.1, 0.22), (60.0, 3.85, 0.1, 0.22),
                        (63.5, 3.6, 0.1, 0.22), (66.0, 2.8, 0.08, 0.22), (67.6, 1.4, 0.05, 0.22),
                        (68.2, 0, 0, 0.22)], 87, 16, el="lens_face")
    # Sheen ring round the lens rim (pal 90/91 only here).
    b.uloft("x", 35.6, [(55.6, 3.95, 0.07, 0.235), (56.4, 3.95, 0.07, 0.235)], 91, 16, chamfer=False)
    b.dome(62.0, 35.6, 0.31 * U - 0.3, 1.1, 1.0, 0.5 * K, 93, 10, 4)
    for c, r in ((56, 29.8), (60, 29.8), (64, 29.8), (56, 40.6), (60, 40.6), (64, 40.6)):
        b.bolt(c, r, 0.24 * U)
    b.uloft("x", 40.6, [(55.5, 1.3, 0.1, 0.14), (67.5, 1.3, 0.1, 0.14)], 4, 10, el="lens_bar")
    b.ub(50, 57, 45, 47, 0.0, 0.14, 3, 0.3, el="lens_block")

    # ---- stalk to the turret ----
    b.ub(29, 35, 45, 47, 0.0, 0.24, 5, 0.4, 3, el="stalk_collar")
    b.ub(33, 33, 48, 54, 0.0, 0.2, 5, 0.2, el="stalk_spine")
    b.ub(29, 34, 55, 56, 0.0, 0.24, 3, 0.4, 6, el="stalk_foot")
    b.ub(30, 31, 49, 53, 0.0, 0.16, 85, 0.3, 85, el="stalk_plate")
    b.uloft("y", 36.5, [(46.6, 0.7, 0.06, 0.16), (60.5, 0.7, 0.06, 0.16)], 86, 8, el="stalk_conduit")
    for r in (49.5, 53.5, 57.5):
        b.box(35.6, 37.4, r, r + 0.5, 0, 2.4 * K, 3, 0.1, ch=0.1)
    b.ub(38, 40, 49, 50, 0.0, 0.18, 19, 0.3, 19, el="stalk_box_brown")
    b.ub(38, 41, 51, 52, 0.0, 0.22, 72, 0.4, 72, el="stalk_box_red")

    # ---- turret on the pad (newshu-79) ----
    # Deck plates on the pad: 1.1 px slabs standing on the 1 px pad (0.09 u steel), chamfered edges,
    # a bolt at each corner; kept inside the plan so no clip notches them.
    for c0, c1, r0, r1 in ((24.3, 27.6, 56.3, 59.6), (43.3, 46.6, 56.3, 59.6), (24.3, 32.6, 79.4, 82.6),
                           (35.3, 40.6, 81.4, 82.6), (43.3, 46.6, 79.4, 82.6)):
        b.box(c0, c1, r0, r1, 0, 2.1, 101, 0.35, 101, ch=0.45, panel=False, el="pad_plate",
              bolts=99 if r1 - r0 > 2 else None)
    ring = [(25, 62), (27, 61), (42, 60.5), (46, 62), (47, 64), (47, 74), (46, 76.5), (44, 78.6), (34, 78.6),
            (30, 77.5), (27.5, 75.5), (25, 74)]
    b.prism(chamfer_outline(ring, 0.4), 0, 0.18 * U, 2, 0.5, 4, el="turret_ring")
    head = [(29, 63), (31, 61.6), (43, 61.6), (45.4, 63), (46, 66), (46, 71), (44.5, 73.5), (42, 74.4),
            (32, 74.4), (30, 73.4), (29, 71)]
    b.prism(chamfer_outline(head, 0.3), 0, 0.26 * U, 3, 0.9, 4, el="turret_head")
    b.ub(35, 41, 65, 68, 0.0, 0.34, 90, 0.4, 90, panel=False, el="turret_hatch")
    # Red bars standing clear of the hatch (graft from design A): the sprite's two red stripes.
    b.ub(36, 36, 65, 68, 0.33, 0.375, 72, 0.12, 72, panel=False, el="hatch_stripe")
    b.ub(39, 39, 64, 68, 0.33, 0.375, 72, 0.12, 72, panel=False, el="hatch_stripe")
    b.ub(35, 41, 69, 70, 0.0, 0.3, 84, 0.3, el="hatch_sill")
    for c in (35, 37, 39):
        b.ub(c, c, 72, 73, 0.1, 0.3, 70, 0.2, 70, el="louvre")
    b.box(33.6, 41.2, 71.6, 74.2, 1.0 * K, 2.6 * K, 3, 0.2, 3, panel=False)
    b.uloft("y", 26.5, [(61.6, 1.2, 0.1, 0.14), (62.2, 1.6, 0.14, 0.14), (71.4, 1.6, 0.14, 0.14),
                        (72.0, 1.2, 0.1, 0.14)], 69, 12, chamfer=False, el="tank_red")
    b.ub(25, 25, 62.4, 70.4, 0.18, 0.27, 72)
    for r in (63.6, 69.6):
        b.box(24.7, 28.3, r, r + 0.4, 0, 3.8 * K, 71, 0.1, ch=0.1, panel=False)
    b.ub(31, 34, 58, 62, 0.0, 0.3, 70, 0.5, 70, el="turret_box_red")
    b.ub(29, 29, 62, 66, 0.0, 0.27, 10, 0.3, 8, el="turret_sensor")
    for k in range(10):
        a = math.pi * (0.15 + 0.7 * k / 9)
        b.bolt(37.5 - 9.2 * math.cos(a), 69.6 + 8.0 * math.sin(a), 0.18 * U, 4)


def rrect(c0, r0, c1, r1, rad, seg=4):
    o = []
    for cx, cy, a0 in ((c1 - rad, r0 + rad, -90), (c1 - rad, r1 - rad, 0), (c0 + rad, r1 - rad, 90), (c0 + rad, r0 + rad, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            o.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    return o


# --------------------------------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------------------------------

def apply_mods(obj):
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def cull_hidden(obj, grid=3, ndirs=40):
    """Delete faces no ray from outside can reach (copied from assembly-newsh2-9.py)."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    eps = 1.5e-4
    dead = []
    for f in bm.faces:
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        if len(vs) == 4:
            for i in range(grid):
                for j in range(grid):
                    u, v = (i + 0.5) / grid, (j + 0.5) / grid
                    pts.append(vs[0].lerp(vs[1], u).lerp(vs[3].lerp(vs[2], u), v))
        else:
            for vco in vs[:12]:
                for t in (0.4, 0.9):
                    pts.append(c.lerp(vco, t))
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for p in pts:
            o = p + n * eps
            for d in cand:
                if tree.ray_cast(o, d, 50.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    return len(dead)


def build(coll):
    P, colors, F = sprite_grid()
    mats = Mats(colors)
    rows = np.arange(H)[:, None]
    cols = np.arange(W)[None, :]
    blue = np.isin(P, list(BLUE))
    padzone = (rows >= 56) & (cols >= 24) & (cols <= 47) & (blue | (rows >= 61))
    pad = F & padzone
    deck = F & ~padzone

    # Parts, clipped to F: only the islands whose plan box leaves F get a boolean.
    bp = B(mats)
    build_parts(bp)
    parts = bp.finish("parts", coll, weld=False)
    print("parts tris before clip", sum(len(f.vertices) - 2 for f in parts.data.polygons))
    fieldF = smooth_field(F)
    bc = B(mats)
    slab(bc, fieldF, 60.0, 0.0, 2, z0=-3.0, tol=0.05, min_area=0.0)
    cutter = bc.finish("cutter", coll)
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    parts.select_set(True)
    bpy.context.view_layer.objects.active = parts
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    islands = [o for o in bpy.context.selected_objects]
    clipped = 0
    for o in islands:
        xs = [v.co.x for v in o.data.vertices]
        ys = [v.co.y for v in o.data.vertices]
        c0, c1 = min(xs) * 12 + W / 2, max(xs) * 12 + W / 2
        r0, r1 = H / 2 - max(ys) * 12, H / 2 - min(ys) * 12
        ok = True
        cc = np.linspace(c0, c1, max(2, int((c1 - c0) * 5) + 2))
        rr = np.linspace(r0, r1, max(2, int((r1 - r0) * 5) + 2))
        for c in cc:
            for r in rr:
                if field_at(fieldF, c, r) < 0.5:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            continue
        mod = o.modifiers.new("clip", "BOOLEAN")
        mod.operation = "INTERSECT"
        mod.object = cutter
        mod.solver = "MANIFOLD"
        try:
            mod.material_mode = "TRANSFER"
        except Exception:  # noqa: BLE001
            pass
        mod.use_hole_tolerant = True
        nb = len(o.data.polygons)
        apply_mods(o)
        clipped += 1
        if len(o.data.polygons) < 4:
            print(f"EMPTY clip: c {c0:.1f}-{c1:.1f} r {r0:.1f}-{r1:.1f} faces {nb} -> {len(o.data.polygons)}")
    print(f"clipped {clipped} of {len(islands)} islands")
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    for o in islands:
        o.select_set(True)
    bpy.context.view_layer.objects.active = islands[0]
    bpy.ops.object.join()
    parts = islands[0]
    bpy.data.objects.remove(cutter, do_unlink=True)
    # Parts stand on the deck / pad: their ground faces (z = 0, facing down) are dropped so the
    # underside is the deck's own closed bottom (no z-fighting there).
    bm = bmesh.new()
    bm.from_mesh(parts.data)
    dead = [f for f in bm.faces if f.normal.z < -0.99 and max(abs(v.co.z) for v in f.verts) < 1e-4]
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bm.to_mesh(parts.data)
    bm.free()

    # Deck and pad.
    bd = B(mats)
    slab(bd, plate_field(deck), 1.9, 0.4, 2, tol=0.16, min_area=1.2)
    # The landing pad is a steel deck (about 1 px = 0.08 u thick, chamfered), not a sheet.
    slab(bd, plate_field(pad), 1.0, 0.3, 98, tol=0.16, min_area=1.2)
    deck_o = bd.finish("deck", coll)
    print("deck tris", sum(len(f.vertices) - 2 for f in deck_o.data.polygons))
    print("parts tris after clip", sum(len(f.vertices) - 2 for f in parts.data.polygons))
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    parts.select_set(True)
    deck_o.select_set(True)
    bpy.context.view_layer.objects.active = parts
    bpy.ops.object.join()
    obj = parts
    obj.name = obj.data.name = NAME
    return obj, bp.parts, P, colors, F


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    obj, parts, P, colors, F = build(coll)

    placed = [(f"newshu-{f}",) + lib.sheet_origin(f) for f in PIECES]
    layout = [(name, c + 12 - W // 2, r + 14 - H // 2) for name, c, r in placed]
    data79 = common.load_sprite(WT, "newshu-79")
    for e in data79["assemblyLayout"]:
        mine = next(item for item in layout if item[0] == e["model"])
        assert (e["cx"] - 56, e["cy"] - 10) == mine[1:], (e, mine)
    pieces = common.split_assembly(obj, layout)
    total = 0
    for name, cx, cy in layout:
        p = pieces[name]
        p.location = (cx / 12, -cy / 12, 0)
        n = cull_hidden(p)
        me = p.data
        me.set_sharp_from_angle(angle=math.radians(32))
        tris = sum(len(f.vertices) - 2 for f in me.polygons)
        total += tris
        print(f"{name}: culled {n}; {len(me.polygons)} faces, {tris} tris")
    print(f"total tris {total}")
    bpy.data.objects.remove(obj, do_unlink=True)

    bake = "--no-bake" not in argv
    if bake:
        for name, _, _ in layout:
            p = pieces[name]
            tag = name.replace("-", "_")
            for i, m in enumerate(list(p.data.materials)):
                c = m.copy()
                c.name = m.name.replace("_nshu79b", f"_{tag}")
                p.data.materials[i] = c
            bake_maps(p, tag)

    # Each piece is exported at its own origin with its outline shell, through the sprite-model
    # contract (public/models/enemies/<piece>.glb and its spriteModels entry, every sprite frame).
    shells = []
    for name, cx, cy in layout:
        p = pieces[name]
        loc = p.location.copy()
        p.location = (0, 0, 0)
        bpy.context.view_layer.update()
        sh = common.outline_shell(p, coll, faces=1200)
        sh.name = sh.data.name = f"{name}_outline"
        data = common.load_sprite(WT, name)
        common.export_sprite_model(WT, [p, sh], f"enemies/{name}", data["sprites"],
                                   image_format="WEBP" if bake else "AUTO")
        p.location = loc
        sh.location = loc
        shells.append(sh)

    if "--review" in argv:
        review([pieces[n] for n, _, _ in layout], shells, Path(argv[argv.index("--review") + 1]))
    if "--blend" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=argv[argv.index("--blend") + 1])
    if "--parts" in argv:
        import json
        Path(argv[argv.index("--parts") + 1]).write_text(json.dumps(parts))


# --------------------------------------------------------------------------------------------------
# Bake (copied from assembly-newsh2-9.py, usp_talon-style AO/edge + roughness-metal)
# --------------------------------------------------------------------------------------------------

def bake_maps(obj, tag, size=1024, samples=48):
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
    bpy.context.view_layer.update()
    for o in bpy.context.scene.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{tag}_rm", size // 2, size // 2, alpha=False)
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
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.5, math_("MULTIPLY", occl, 0.6)),
                                       math_("MULTIPLY", edge, 0.18)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(v, comb.inputs[k])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
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
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.pack()

    for m in mats:
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


# --------------------------------------------------------------------------------------------------
# Review renders (workbench): top mask/flat/lit at 8 image px per sprite px, elevations, 3/4, game
# --------------------------------------------------------------------------------------------------

def review(pieces, shells, out):
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    sh = scene.display.shading
    if scene.world is None:
        scene.world = bpy.data.worlds.new("rev")
    scene.world.color = (0.035, 0.04, 0.05)
    scene.render.resolution_percentage = 100
    for s in shells:
        s.hide_render = True
    k = 8

    def cam(name, loc, look, ortho=None, lens=50, rx=900, ry=600, up=(0, 0, 1)):
        d = bpy.data.cameras.new(name)
        if ortho:
            d.type = "ORTHO"
            d.ortho_scale = ortho
        else:
            d.lens = lens
        d.clip_end = 500
        o = bpy.data.objects.new(name, d)
        scene.collection.objects.link(o)
        o.location = loc
        direction = Vector(look) - Vector(loc)
        o.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        scene.camera = o
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        return o

    def shot(path, flat=False, transparent=False, cavity=True):
        sh.light = "FLAT" if flat else "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_cavity = cavity and not flat
        sh.cavity_type = "BOTH"
        sh.show_object_outline = False
        sh.show_specular_highlight = not flat
        scene.render.film_transparent = transparent
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    # Top views (exact sprite grid: W*k x H*k, ortho scale = H/12 along the longer side).
    c = cam("top", (0, 0, 20), (0, 0, 0), ortho=H / 12, rx=W * k, ry=H * k)
    c.rotation_euler = (0, 0, 0)
    shot(out / "top_mask.png", flat=True, transparent=True)
    shot(out / "top_flat.png", flat=True)
    shot(out / "top_lit.png")
    ext = 7.6
    views = {
        "front": ((0, -40, 2 / 12 * 3), (0, 0, 0.25)),
        "rear": ((0, 40, 0.5), (0, 0, 0.25)),
        "east": ((40, 0, 0.5), (0, 0, 0.25)),
        "west": ((-40, 0, 0.5), (0, 0, 0.25)),
    }
    for nm, (loc, look) in views.items():
        cam(nm, loc, look, ortho=ext, rx=900, ry=260)
        shot(out / f"{nm}.png")
    d = 16
    el = math.radians(32)
    az = math.radians(35)
    cam("q_high", (d * math.cos(el) * math.sin(az), -d * math.cos(el) * math.cos(az), d * math.sin(el)), (0, 0, 0.2),
        lens=60, rx=900, ry=700)
    shot(out / "q_high.png")
    az = math.radians(180 + 40)
    el = math.radians(30)
    cam("q_rear", (d * math.cos(el) * math.sin(az), -d * math.cos(el) * math.cos(az), d * math.sin(el)), (0, 0, 0.2),
        lens=60, rx=900, ry=700)
    shot(out / "q_rear.png")
    # Game camera: 32 degrees off vertical, from the south.
    t = math.radians(32)
    cam("game", (0, -d * math.sin(t), d * math.cos(t)), (0, 0, 0), lens=55, rx=700, ry=800)
    shot(out / "game.png")
    cam("under", (0, 0, -20), (0, 0, 0), ortho=H / 12 * 1.05, rx=W * 6, ry=H * 6)
    shot(out / "under.png")
    for s in shells:
        s.hide_render = False
    cam("game_ink", (0, -d * math.sin(t), d * math.cos(t)), (0, 0, 0), lens=55, rx=700, ry=800)
    shot(out / "game_shell.png")


if __name__ == "__main__":
    main()
