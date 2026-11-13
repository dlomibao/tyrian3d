"""DELIANI gun emplacement (newshu.shp, assembly of 7 pieces: newshu-1/3/5 over 39/41/43, 79 under the
middle; 72 x 84 px). A fixed, working gun emplacement (QA2 issue 7; D120/D122: built as what it is,
not as a wreck): piece 43 launches the shot from the muzzle every 50 ticks.

The sprite is authoritative for the plan, the parts' places and their colours. The plan edge sits on
the INNER edge of the sprite's ink border (D74, docs/agents/OUTLINE-BORDER.md). The blue tiles round
the turret are DELIANI's ground (D130): they are not part of the plan and nothing is built on them,
the machine stands on the HD ground. Everything but the turret casting is built in sprite px and
clipped to the plan by one boolean, so the sprite's see-through gaps stay open.

Reading from the tilted game camera, from the ground up:
- base: one gunmetal plinth under the whole plan (1.4 px, chamfered, pal 4), not an ink-black plate;
- gun house: ONE continuous armoured casemate under the whole dense body, west plant and middle
  together (marching-squares body from the plan, skirt + 1.1 px 45 degree glacis, roof at 4.8 px,
  pal 5), with the sprite's see-through gaps kept open. Every roof fitting is sunk into it (sq_roof
  keeps half the height above the roof; sq_west maps the west plant's 0-6 px onto 0-1 px proud), so
  the fittings read as panels and capped stacks cut into one mass: base, casemate, then the gun;
- the gun (axis 6.8 px): a long round grey barrel on the sprite's light barrel band (row 33.6) on two
  trunnion cradles from the breech (col 38) east through a low dark mantlet into the purple muzzle shell (a fat round shell with two seams and a sheen disc,
  lying in a grey cradle: the sprite's grey bands round the purple), ending in a blunt grey muzzle
  cone with a dark bore; a recuperator cylinder above the barrel;
- sensors north: the rangefinder mast (cap, red strip), the purple aerial rod on its root post and a
  stanchion under its tip, and the
  ammunition drum with its domed lid;
- west: a machinery housing with intact, capped red coolant canisters, tanks and the purple armour bar;
- south: an armoured feed duct with a purple conduit to the power turret (newshu-79): one round
  casting (ring, head, purple hatch with two red stripes, louvres, red tank on two straps).

Hard-surface (D65): chamfered sections, rounded machined canisters with lid seams, flanged pipes,
modelled bands and bolts. Underside: closed and flat (it stands on the ground). Palette materials
pal_<index> (the sprite's index per region). Outline shell per piece from a sealed copy taken before
the hidden-face cull (0.03 voxels, held 0.004 inside: D90/D118), so ink only draws on silhouettes.
AO / roughness bake per piece (no concept projection, D50).

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
    # The blue tiles round the turret are DELIANI's ground, which the game draws in HD (D130): the
    # plan is the sprite without them.
    idx = [[-1 if v in BLUE else v for v in row] for row in idx]
    m = SM.masks(idx, colors)
    F = np.array(m["inner"], bool) | np.array(m["free"], bool)
    # Stray single pixels (the sprite's lone dots at col 0) are not part of the machine.
    P = np.array(idx)
    keep = F.copy()
    for r in range(H):
        for c in range(W):
            if F[r, c] and not F[max(0, r - 1):r + 2, max(0, c - 1):c + 2].sum() > 1:
                keep[r, c] = False
    # The turret ring's south fringe (rows 74+: 1-2 px stubs of dark ring poking into the removed
    # ground tiles) is opened away, so the ring ends in one smooth edge instead of teeth.
    er = keep.copy()
    er[1:-1, 1:-1] = (keep[1:-1, 1:-1] & keep[:-2, 1:-1] & keep[2:, 1:-1] & keep[1:-1, :-2] & keep[1:-1, 2:])
    op = er.copy()
    op[1:] |= er[:-1]
    op[:-1] |= er[1:]
    op[:, 1:] |= er[:, :-1]
    op[:, :-1] |= er[:, 1:]
    keep[74:] &= op[74:]
    # ... and its SW notches (transparent px 26-27/29 on row 72, 26-27 on row 73) are filled.
    keep[72, 26:30] = True
    keep[73, 26:28] = True
    return P, {int(k): v for k, v in colors.items()}, keep


# Sprite px (row, col) of 1 px slits the casemate closes over: the slits that cut the west plant into
# separate clusters, as many per piece as the IoU budget allows (>= 0.955 per piece kept). Every
# other slit is only narrowed to a seam (grown_field).
FILL = [(38, 46), (38, 47), (39, 46), (39, 47), (40, 46), (40, 47), (19, 45), (19, 44), (27, 29), (35, 23), (35, 21), (34, 23), (33, 19), (33, 15), (40, 11), (33, 25),
        (31, 24), (42, 44), (38, 30), (38, 29), (31, 26), (30, 28), (43, 44), (42, 24), (41, 46), (36, 25),
        (32, 27), (44, 52), (42, 50), (38, 54), (35, 55), (45, 54)]


def closed_plan(F):
    Fc = F.copy()
    for r, c in FILL:
        Fc[r, c] = True
    return Fc


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
        self.sq = None  # height remap (px -> px) while building fittings sunk into the casemate
        self.wall = None  # side palette override: fittings sunk into a body take its wall colour

    def v(self, c, r, h):
        if self.sq is not None:
            h = self.sq(h)
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
        if self.wall is not None:
            pal = self.wall  # only the top keeps the sprite's colour: the walls are the body's
            bev = min(bev, 0.15)  # flush with the body's walls: no grooves between neighbours
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
        a, bq, c, d = c0 - 0.1, c1 + 1.1, r0 - 0.1, r1 + 1.1
        self.prism(rrect(a, c, bq, d, 0.42 * min(c1 - c0 + 1, r1 - r0 + 1) + 0.1), h, h + t, pal, 0.1, smooth=True)

    def rbox(self, c0, c1, r0, r1, h0, h1, pal, bev=0.3, top=None, el=None, lid=True):
        """A machined canister over inclusive px c0..c1 / r0..r1: rounded plan (radius 0.42 of the
        short side), smooth walls, chamfered top and, when lid, a recessed lid ring (the cap seam)."""
        a, bq, c, d = c0 + 0.05, c1 + 0.95, r0 + 0.05, r1 + 0.95
        rad = 0.42 * min(bq - a, d - c)
        f = self.prism(rrect(a, c, bq, d, rad), h0, h1, pal, bev, top, el=el, smooth=True)
        if lid and min(bq - a, d - c) >= 1.6:
            i = 0.35 + bev
            self.prism(rrect(a + i, c + i, bq - i, d - i, max(0.1, rad - i)), h1 - 0.1, h1 + 0.22,
                       pal if top is None else top, 0.08, smooth=True)
        return f

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


def exterior(ins):
    """Lattice points outside `ins` that connect to the lattice's border (not enclosed holes)."""
    out = ~ins
    ext = np.zeros_like(ins)
    ext[0, :], ext[-1, :], ext[:, 0], ext[:, -1] = out[0, :], out[-1, :], out[:, 0], out[:, -1]
    while True:
        g = ext.copy()
        g[1:] |= ext[:-1]
        g[:-1] |= ext[1:]
        g[:, 1:] |= ext[:, :-1]
        g[:, :-1] |= ext[:, 1:]
        g &= out
        if (g == ext).all():
            return ext
        ext = g


def grown_field(F, sigma=0.5, lift=0.1, limit=0.42, need=0.7):
    """Lattice field for the plan's bodies: the plan blurred (sigma px) and lifted, so its outline runs
    in straight diagonals and rounded corners instead of the sprite's pixel stairs and the see-through
    slits narrow to seams. Then held to the sprite grid pixel by pixel: no non-plan pixel more than
    `limit` covered, every plan pixel at least `need` (a pixel counts when half of it is covered), so
    the top view keeps every gap open and every plan pixel."""
    Fp = np.pad(F, PAD)
    f = np.clip(smooth_field(F, sigma) + lift, 0, 1)
    hgt, wid = f.shape
    sub = (np.arange(6) + 0.5) / 6

    def cover(R, C):
        cov = 0
        for v in sub:
            for u in sub:
                x = (C + u) * SUB - 0.5
                y = (R + v) * SUB - 0.5
                j, i = int(np.floor(x)), int(np.floor(y))
                fx, fy = x - j, y - i
                i, j = max(0, min(hgt - 2, i)), max(0, min(wid - 2, j))
                val = ((1 - fx) * (1 - fy) * f[i, j] + fx * (1 - fy) * f[i, j + 1]
                       + (1 - fx) * fy * f[i + 1, j] + fx * fy * f[i + 1, j + 1])
                cov += val >= 0.5
        return cov / 36

    for R in range(Fp.shape[0]):
        for C in range(Fp.shape[1]):
            sl = (slice(R * SUB, (R + 1) * SUB), slice(C * SUB, (C + 1) * SUB))
            if Fp[R, C]:
                k = 0.0
                orig = f[sl].copy()
                while cover(R, C) < need and k < 1:
                    k = round(k + 0.1, 2)  # a thin plan line the blur thinned: fill it back in
                    f[sl] = orig + (1.0 - orig) * k
                continue
            if f[sl].max() < 0.5:
                continue
            orig = f[sl].copy()
            k = 1.0
            # a slit grown into from both sides: pull this pixel's own lattice back step by step
            while cover(R, C) > limit and k > 0:
                k = round(k - 0.1, 2)
                f[sl] = orig * k
    return f


def heightfield(b, field, hz, ch, pal, top=None, z0=0.0, holes_sheer=False):
    """A closed slab over field >= 0.5: flat bottom at z0, walls, a ch px 45 degree chamfer and a flat
    top at hz (px). Marching squares at the lattice; coplanar faces dissolved afterwards."""
    bm = b.bm
    ins = field >= 0.5
    # holes_sheer: the chamfer runs round the outer edge only; enclosed slits get sheer walls (seams)
    dist_src = ~exterior(ins) if holes_sheer else ins
    dist = inside_distance(dist_src) / SUB if ch > 0 else np.full(ins.shape, 99.0)  # px
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
                f.smooth = bool(k < 4)  # the wall: shaded as one surface, not lattice facets
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

# Heights (px). The emplacement reads in four bands from the tilted game camera:
DK = 1.4    # base deck: one armoured plinth under the whole plan (pal 3)
RH = 4.8    # gun house roof (the casemate over the whole body; 45 degree glacis)
AX = 6.8    # gun axis: breech, barrel, mantlet, the purple muzzle shell and the grey muzzle cone
ROW = 35.2  # gun axis row (the sprite's grey barrel band rows 33-36 and the purple shell rows 32-38)


RB = 33.6  # barrel row: the sprite's light grey barrel band (rows 32-34), north of the shell's axis


HR = 8.6    # gun house roof: the turret body on its ring, 3.8 px over the casemate
GA = 8.9    # barrel axis: the barrel lies half sunk in the gun house roof (its top 1.8 px proud)


def sq_roof(h):
    """Roof fittings sink into the casemate: what stood above the roof keeps 0.3 of its height."""
    if abs(h - (RH - 0.2)) < 1e-6:
        return DK - 0.3  # feet reach down into the body (no gap where the glacis falls away)
    return h if h <= RH - 0.2 else RH - 0.2 + 0.3 * (h - (RH - 0.2))


def sq_west(h):
    """The west plant was built on the ground: its 0-6 px heights map onto the casemate's roof as
    panels 0.1-0.45 px proud (one roof plane with hatches and capped stack heads, not free boxes);
    the feet stay on the ground (rooted at the glacis, walls in the casemate's colour)."""
    return h if h < 1e-6 else RH + 0.08 + 0.06 * h


def casemate_zone(F):
    """The gun house's plan: the sprite's whole dense body (west plant, middle, the drum's footing),
    not the north fingers, the muzzle (east of col 56) or the feed duct south of row 47."""
    z = np.zeros_like(F)
    z[19:48, 7:56] = True
    z[13:19, 40:56] = True
    z[44:48, 44:57] = False  # the ragged south-east fringe stays on the low plinth: a straight casemate edge
    return z & F


def build_casemate(b, F):
    # ================= GUN HOUSE: one continuous armoured casemate =================
    # One body under the whole dense plan (west plant and middle together), a vertical skirt and a
    # 45 degree glacis up to the roof at RH; the sprite's see-through gaps stay open. Every roof fitting is sunk into it (sq_roof / sq_west).
    # Its plan field already keeps the sprite's see-through gaps (min with the plan's own sharp field),
    # so it needs no boolean clip.
    Fc = closed_plan(F)
    field = np.minimum(plate_field(casemate_zone(Fc), 0.7), grown_field(Fc))
    heightfield(b, field, RH, 0.0, 5, top=5)  # sheer walls: a lattice glacis terraced into stairs  # slits narrowed to seams, kept open
    b.parts.append(("casemate", 5, 7, 56, 19, 47))


def build_parts(b, bt):
    # ---- roof fittings in the sprite's colours, sunk into the casemate's roof (walls: its colour) ----
    b.sq = sq_roof
    b.wall = 5
    b.box(32, 37, 20, 27, RH - 0.2, RH + 1.3, 5, 0.3, 5, panel=False, el="block_grey_A")  # hatch block
    b.box(34.0, 36.6, 20.6, 22.0, RH + 1.2, RH + 1.6, 6, 0.12, ch=0.2, panel=False)     # its access lid
    b.box(32, 33, 23, 28, RH - 0.2, RH + 1.8, 11, 0.3, 11, el="block_grey_B")
    b.box(33, 37, 23, 23, RH - 0.2, RH + 1.5, 11, 0.2)
    b.box(35, 36, 24, 26, RH - 0.2, RH + 1.9, 7, 0.3, 10)
    b.box(38, 41, 24, 25, RH - 0.2, RH + 0.9, 8, 0.25, 8, el="block_grey_C")
    b.box(37, 41, 26, 26, RH - 0.2, RH + 1.0, 73, 0.2, 73, el="bar_red")
    # Red conduit along the roof from the rangefinder mast (rows 17-26, cols 31-32).
    b.box(31, 32, 17, 26, 0.0, RH + 1.0, 71, 0.35, 72, el="conduit_red")
    # Red coolant tank against the gun house's north-west wall, capped (cols 42-43, rows 25-30), and
    # a grey valve block.
    b.rbox(42, 43, 25, 30, RH - 0.2, RH + 2.2, 72, 0.4, 72, el="stack_red_mid")
    b.box(40, 41, 28, 30, RH - 0.2, RH + 1.2, 6, 0.3, 6, el="block_grey_D")
    # Grey frame (fire-control box) with a red panel, north of the gun house.
    b.box(47, 54, 20, 27, RH - 0.2, RH + 1.6, 3, 0.4, 4, panel=False, el="frame_right")
    b.box(50, 52, 22, 27, RH + 1.4, RH + 1.9, 72, 0.15, 70, panel=False, el="frame_panel")
    b.box(54, 54, 20, 27, RH - 0.2, RH + 1.2, 8, 0.3, el="frame_rail")
    b.box(44, 46, 20, 27, RH - 0.2, RH + 0.7, 3, 0.3, el="frame_skirt")
    # South roof: red ammo tank against the gun house's south wall, pump, sill.
    b.rbox(44, 45.7, 38, 44, RH - 0.2, RH + 1.4, 69, 0.4, 70, el="tank_red_low")
    b.box(47, 48, 39, 42, RH - 0.2, RH + 0.6, 3, 0.2)
    b.rbox(50, 53, 39, 41, RH - 0.2, RH + 1.2, 72, 0.4, 73, el="pump_red")  # red pump (sprite 50-53 x 39-41)
    b.box(50.4, 52.6, 39.2, 39.8, RH + 1.0, RH + 1.6, 73, 0.15, 73, el="pump_lid")
    b.box(52, 53, 41.6, 43, RH - 0.2, RH + 0.6, 19, 0.2, 19)  # brown valve chest under it
    b.box(49, 49, 39, 42, RH - 0.2, RH + 0.5, 6, 0.15, 6)    # grey flange west of the pump
    b.box(43.0, 43.0, 39.6, 44.6, RH - 0.2, RH + 0.8, 6, 0.2, 6, el="riser")  # grey riser rail
    # Red armour wedge on the gun house's south-west, the breech's skirt.
    b.prism([(35, 35.8), (39, 35.8), (39, 44), (38, 44), (35, 41)], RH - 0.2, RH + 1.2, 69, 0.4, 69, el="wedge_red")
    b.pipe("x", 36.6, 30.0, 34.4, 1.6, RH + 0.4, 5, 4, el="drum_mid")
    b.sq = None
    b.wall = None

    # ================= THE GUN HOUSE (turret) on its ring =================
    # One faceted armoured body over the sprite's dark block round the barrel (cols 40-55, rows 28-38),
    # standing on a darker ring collar on the casemate roof; the barrel lies half sunk in its roof
    # (the sprite's light band, rows 32-34), held by a trunnion yoke at the breech; the breech housing
    # (the sprite's purple block) rises behind it and the barrel leaves the house through a round
    # mantlet into the purple muzzle shell.
    house = [(40.0, 31.0), (44.0, 28.0), (52.6, 28.0), (55.4, 30.0), (55.4, 37.0), (53.6, 39.0), (40.0, 39.0)]
    ring_ = [(39.6, 30.8), (43.8, 27.6), (52.8, 27.6), (55.8, 29.8), (55.8, 37.2), (53.8, 39.4), (39.6, 39.4)]
    b.prism(ring_, RH - 0.3, RH + 0.75, 3, 0.25, 3, el="turret_collar")
    b.prism(house, RH + 0.5, HR, 4, 1.25, 4, el="gun_house")  # sloped armour faces all round
    b.prism(inset_convex(house, 1.6), HR - 0.05, HR + 0.12, 4, 0.06)  # roof plate (seam ring)
    # roof hatches and panels in the sprite's colours (flush plates)
    b.box(47.2, 52.6, 35.2, 36.6, HR, HR + 0.22, 3, 0.1, 3, panel=False, el="house_hatch")
    for c, r in ((47.8, 35.8), (53.0, 35.8), (47.8, 37.0), (53.0, 37.0)):
        b.bolt(c, r, HR + 0.22, 6, 0.2)
    b.box(44.2, 46.6, 35.4, 36.6, HR, HR + 0.25, 5, 0.1, 5, panel=False, el="house_panel")
    b.box(43.0, 43.8, 35.4, 36.6, HR, HR + 0.2, 7, 0.08, 7, panel=False, el="house_stripe")
    b.box(44.4, 52.4, 29.3, 29.7, HR, HR + 0.18, 3, 0.06, 3, panel=False)  # north vision slit
    # Breech housing: the purple armour block behind the gun, taller than the house.
    b.box(36, 39, 29, 33, RH - 0.2, GA + 1.6, 4, 0.6, 91, bolts=88, el="armour_box")
    b.box(36.5, 39.5, 29.6, 31.9, GA + 1.5, GA + 1.8, 91, 0.1, 91, panel=False)
    b.box(36.2, 39.6, 33.1, 33.9, GA + 1.0, GA + 1.6, 82, 0.15, 82, panel=False)  # its dark back plate
    # Trunnion yoke: two cheek plates either side of the barrel at the breech, pins through them.
    for r0, r1 in ((31.1, 31.9), (35.3, 36.1)):
        b.box(40.4, 42.6, r0, r1 - 1, HR - 0.1, GA + 1.0, 5, 0.2, 6, ch=0.25, panel=False, el="trunnion")

    # ================= THE GUN: barrel, recuperator, mantlet, muzzle shell, cone =================
    # Barrel: a long round grey tube from the breech (col 38.5) through the mantlet into the shell.
    b.loft("x", RB, [(38.4, 1.25, 1.25, GA), (38.8, 1.5, 1.5, GA), (49.0, 1.45, 1.45, GA),
                     (56.0, 1.3, 1.3, GA - 0.2), (57.0, 1.3, 1.3, GA - 0.2)], 7, 16, el="barrel")
    for p in (43.4, 47.6):  # barrel bands
        b.loft("x", RB, [(p - 0.3, 1.62, 1.62, GA), (p - 0.2, 1.74, 1.74, GA), (p + 0.2, 1.74, 1.74, GA),
                          (p + 0.3, 1.62, 1.62, GA)], 6, 16, chamfer=False)
    # Recuperator: the thinner grey cylinder on the roof beside the barrel's north side (rows 29-31).
    b.pipe("x", 30.4, 45.6, 53.2, 0.95, HR + 0.6, 8, 6, el="recuperator")
    # Mantlet: a round armoured collar at the house's front that the barrel leaves through.
    b.loft("x", RB, [(52.2, 2.0, 2.0, GA), (52.8, 2.45, 2.45, GA), (55.2, 2.45, 2.45, GA),
                     (55.8, 2.0, 2.0, GA)], 4, 20, chamfer=False, el="mantlet")
    for p in (53.2, 54.8):
        b.loft("x", RB, [(p - 0.12, 2.55, 2.55, GA), (p + 0.12, 2.55, 2.55, GA)], 5, 20, chamfer=False)
    # Muzzle shell: a fat round purple shell (the sprite's purple, rows 32-38) lying in a grey cradle
    # (the grey bands above and below it, rows 29-31 / 39-41), ending in a blunt grey muzzle cone
    # (cols 67-70) with a dark bore facing east.
    rim = [(55.0, 29.4), (66.0, 29.4), (68.5, 30.8), (70.0, 33.0), (70.3, 35.5), (70.0, 38.3), (68.5, 40.0),
           (66.0, 41.0), (55.0, 41.0)]
    b.prism(rim, 0.0, AX - 1.2, 4, 0.9, 5, el="muzzle_cradle")
    for c in (56.4, 60.4, 64.4):
        b.bolt(c, 30.2, AX - 1.2)
        b.bolt(c, 40.2, AX - 1.2)
    b.loft("x", ROW, [(55.4, 3.0, 3.0, AX + 0.6), (56.4, 3.75, 3.75, AX + 0.6), (65.6, 3.8, 3.8, AX + 0.6),
                      (66.9, 3.5, 3.5, AX + 0.6), (67.6, 2.8, 2.8, AX + 0.6)], 87, 24, el="muzzle_shell")
    for p in (58.2, 63.0):  # armour seams round the shell
        b.loft("x", ROW, [(p - 0.18, 3.86, 3.86, AX + 0.6), (p + 0.18, 3.86, 3.86, AX + 0.6)], 86, 24, chamfer=False)
    b.cyl(61.6, ROW, 1.1, AX + 4.25, AX + 4.55, 89, 12, bev=0.1, top=93)  # sight disc (sheen spot)
    b.loft("x", ROW, [(66.6, 3.7, 3.4, AX + 0.6), (67.4, 4.1, 3.7, AX + 0.6), (69.4, 3.5, 3.1, AX + 0.6),
                      (70.2, 2.6, 2.3, AX + 0.6)], 7, 20, el="muzzle_cone")
    b.loft("x", ROW, [(69.95, 1.4, 1.3, AX + 0.6), (70.25, 1.4, 1.3, AX + 0.6)], 82, 12, chamfer=False)  # bore
    b.box(50, 57, 45, 47, 0.0, DK + 1.0, 3, 0.3, el="lens_block")

    # ================= SENSORS north of the house =================
    # Rangefinder mast: grey post, lit cap, red access strip, bands.
    b.box(30, 32, 5, 17, 0.0, 9.7, 8, 0.5, el="mast_periscope")
    for hb in (3.0, 6.6):
        b.box(29.85, 32.15, 5.4, 16.6, hb, hb + 0.45, 7, 0.12, ch=0.35, panel=False)
    b.loft("y", 31.5, [(4.6, 1.5, 0.95, 9.2), (5.2, 1.6, 1.1, 9.35), (8.5, 1.6, 1.1, 9.35), (9.2, 1.3, 0.8, 9.35)],
           8, 12, el="periscope_cap")
    b.box(31, 32, 11, 16, 8.2, 10.0, 72, 0.3, 70, el="periscope_strip")
    # Aerial: purple emitter rod lying north on its post, cradle bands.
    b.rbox(40, 43, 10, 12, 0.0, 9.0, 6, 0.4, 5, el="mast_crystal_post")
    b.box(43, 43, 5, 12, 0.0, 8.2, 6, 0.3, el="mast_crystal_rail")
    # The rod lies on two posts: its root in the post block (rows 10-12) and a grey stanchion under
    # its north end (rows 3-5), so it does not hang in the air in elevation.
    b.loft("y", 41.5, [(10.0, 1.5, 1.3, 8.9), (7.0, 1.6, 1.5, 9.0), (4.0, 1.5, 1.3, 8.9), (2.0, 1.0, 0.95, 8.6),
                       (0.4, 0, 0, 8.4)], 91, 6, el="crystal")
    for r in (8.2, 5.2):
        b.box(39.8, 43.2, r, r + 0.4, 7.2, 8.3, 89, 0.1, ch=0.1, panel=False)
    b.box(40.8, 42.2, 3.0, 5.0, 0.0, 8.0, 6, 0.2, 6, ch=0.3, panel=False)       # stanchion
    b.box(40.2, 42.8, 3.2, 4.8, 0.0, 0.9, 5, 0.2, 5, ch=0.3, panel=False)       # its foot
    b.rbox(44, 45, 6, 12, 0.0, 8.6, 73, 0.5, 73, el="pillar_red")
    b.rbox(41, 45, 13, 16, 0.0, 7.6, 70, 0.5, 72, el="block_red")
    b.belt(41, 45, 13, 16, 5.4, 69)
    b.rbox(36, 37, 15, 19, 0.0, 6.8, 73, 0.4, 73, el="post_red_small")
    b.box(34, 34, 17, 19, 0.0, 5.6, 8, 0.3, el="stub_grey")
    # Ammunition drum: rounded housing, lid, domed cap, bolt ring.
    b.prism(rrect(47.2, 12.6, 53.9, 20.4, 1.6), 0, 6.8, 4, 0.4, 5, el="drum_housing", smooth=True)
    b.prism(rrect(47.9, 13.4, 53.2, 19.6, 1.2), 6.8, 7.4, 6, 0.25, 6, el="drum_lid", smooth=True)
    b.prism(rrect(47.0, 12.4, 54.1, 20.6, 1.7), 5.3, 6.0, 5, 0.15, smooth=True)
    b.dome(50.6, 16.5, 7.4, 1.2, 1.2, 0.9, 9, 12, 4)
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        b.bolt(50.55 + 2.05 * math.cos(a), 16.5 + 2.55 * math.sin(a), 7.4, 7, 0.2)

    # ================= WEST: power plant on the deck (coolant stacks, intact capped tops) =================
    # One armoured machinery housing under the west wing: the stacks and tanks rise out of it.
    # (the casemate is their housing: build_casemate; heights remapped onto its roof)
    # Every west fitting is a panel or capped stack head in the casemate's roof plane (sq_west), its
    # walls in the casemate's colour: one perforated body (the sprite's see-through gaps are vents).
    b.sq = sq_west
    b.wall = 5

    def stack(c0, c1, r0, r1, h, pal, top, el=None, bands=(), cap=76):
        b.rbox(c0, c1, r0, r1, 0.0, h, pal, 0.4, top, el=el)
    b.rbox(20, 22, 19, 22, 0.0, 6.0, 9, 0.4, 8, el="stack_left_A")
    stack(21, 22, 22, 26, 5.4, 72, 72, "stack_left_B", (2.6,))
    b.box(20, 20, 23, 26, 0.0, 4.6, 71, 0.3)
    stack(17, 20, 25, 30, 5.0, 72, 72, "stack_left_C", (1.8, 3.4))
    b.box(16, 16, 29, 30, 0.0, 3.6, 8, 0.3)
    b.box(27, 27, 20, 26, 0.0, 3.2, 162, 0.3, el="strut_brown")
    b.rbox(28, 30, 24, 26, 0.0, 4.0, 70, 0.3, 69, el="stub_red_mid")
    stack(8, 9, 26, 32, 5.6, 72, 72, "stack_far_left", (2.0, 4.0))
    b.box(22, 23, 28, 30, 0.0, 2.6, 162, 0.3, 162, el="debris")
    b.box(24, 27, 30, 30, 0.0, 3.2, 72, 0.3, 72)
    b.box(25, 27, 31, 32, 0.0, 2.2, 162, 0.3, 19)
    b.box(20, 20, 31, 33, 0.0, 3.6, 70, 0.3, 70)
    b.box(21, 22, 33, 36, 0.0, 2.0, 162, 0.3)
    b.box(27, 29, 35, 36, 0.0, 3.6, 71, 0.3, 72)
    b.box(28, 28, 31, 33, 0.0, 2.6, 162, 0.3)
    b.box(10, 10, 29, 32, 0.0, 2.6, 19, 0.2)
    b.box(29, 31, 31, 33, 0.0, 3.0, 162, 0.3, el="debris_mid")
    b.box(29, 30, 32, 33, 0.0, 3.6, 73, 0.3, 73)
    b.pipe("x", 37.5, 22.2, 29.6, 0.9, 1.6, 164, 162, el="pipe_salmon")
    b.box(22, 28, 38, 38, 0.0, 1.6, 164, 0.2)
    b.box(27, 28, 29, 30, 0.0, 3.4, 72, 0.3, 72)
    # Purple armour bar leaning on the house's west skirt, bolted.
    b.box(25, 33, 39, 42, 0.0, 4.6, 90, 0.6, 90, el="bar_purple")
    b.loft("x", 42.4, [(25.3, 0.7, 0.75, 4.5), (33.7, 0.7, 0.75, 4.5)], 93, 6)
    b.box(25, 33, 43, 43, 0.0, 3.0, 86, 0.3, el="bar_purple_foot")
    for c in (26.2, 32.8):
        b.bolt(c, 40, 4.6, 88)
    b.rbox(20, 23, 40, 43, 0.0, 5.6, 72, 0.4, 72, el="tank_red_left")
    b.loft("x", 43.5, [(20.6, 0.6, 0.95, 3.8), (23.6, 0.6, 0.95, 3.8)], 76, 8)
    b.box(18, 19, 40, 41, 0.0, 3.0, 71, 0.3)
    b.box(19, 23, 44, 46, 0.0, 2.3, 19, 0.3, el="crate_brown")
    b.box(26, 27, 45, 46, 0.0, 2.3, 19, 0.3, 19)
    b.rbox(16, 20, 34, 37, 0.0, 4.6, 6, 0.4, 8, el="block_grey_left")
    b.rbox(12, 15, 31, 32, 0.0, 5.0, 72, 0.4, 72, el="stub_red_left")
    b.box(12, 15, 33, 34, 0.0, 1.9, 19, 0.3)
    b.rbox(8, 10, 33, 39, 0.0, 4.4, 84, 0.5, 86, el="plate_purple_A")
    b.box(11, 15, 39, 42, 0.0, 3.6, 88, 0.5, el="plate_purple_B")
    b.box(12, 14, 36, 38, 0.0, 2.2, 82, 0.3, 82)
    b.sq = None
    b.wall = None

    # ================= FEED DUCT south to the power turret =================
    # One armoured trunk, as tall as the turret's ring, from the casemate's south skirt straight into
    # the power turret's casting (its neck reaches the ring at row 62): the turret is part of the
    # same emplacement, not a box on a strut.
    duct = [(29.6, 45.0), (41.4, 45.0), (42.0, 47.0), (41.4, 55.6), (29.6, 55.6), (29.0, 47.0)]
    b.prism(duct, 0.0, 4.2, 3, 0.8, 3, el="feed_duct")
    b.prism([(30.0, 54.6), (38.0, 54.6), (38.0, 63.0), (30.0, 63.0)], 0.0, 4.2, 3, 0.6, 3, el="duct_neck")
    b.sq = lambda h: h + 1.4 if h > 1e-6 else h  # its fittings ride on the raised duct
    b.wall = 4
    b.box(29, 35, 45, 47, 2.4, 3.8, 5, 0.4, 3, el="stalk_collar")
    b.box(33, 33, 48, 54, 2.4, 3.6, 5, 0.2, el="stalk_spine")
    b.box(29, 34, 55, 56, 0.0, 3.6, 3, 0.4, 6, el="stalk_foot")
    b.box(30, 31, 49, 53, 2.4, 3.2, 85, 0.3, 85, el="stalk_plate")
    b.wall = None
    b.sq = None
    b.loft("y", 36.5, [(46.6, 0.7, 0.7, 4.4), (61.0, 0.7, 0.7, 4.4)], 86, 8, el="stalk_conduit")
    for r in (49.5, 53.5, 57.5):  # conduit clamps
        b.box(35.6, 37.4, r, r + 0.5, 3.8, 5.2, 3, 0.1, ch=0.1)
    b.sq = lambda h: h + 1.4 if h > 1e-6 else h
    b.wall = 4
    b.box(38, 40, 49, 50, 2.4, 3.6, 19, 0.3, 19, el="stalk_box_brown")
    b.rbox(38, 41, 51, 52, 2.4, 4.2, 72, 0.4, 72, el="stalk_box_red")
    b.box(37, 37, 55, 57, 2.4, 3.2, 162, 0.2, 164)
    b.sq = None
    b.wall = None

    # ================= POWER TURRET (newshu-79) on its ring =================
    # Ring and head are one casting with a smooth plan drawn just inside the sprite's dark ring (its
    # pixel knobs are not followed); built unclipped (bt) and standing on the HD ground (D130).
    ring = [(26.0, 62.0), (42.8, 62.0), (43.9, 63.0), (45.0, 64.0), (46.0, 65.0), (46.0, 67.9), (46.9, 68.1),
            (46.9, 70.9), (46.0, 71.1), (46.0, 74.9), (45.0, 75.1), (45.0, 77.9), (34.0, 78.0), (33.4, 77.0),
            (30.9, 76.9), (29.0, 75.9), (29.0, 74.0), (30.0, 72.9), (30.8, 72.0), (25.1, 71.95), (25.1, 63.0)]
    bt.prism(chamfer_outline(ring, 0.3), 0, 3.4, 4, 0.35, 4, el="turret_ring", smooth=False)
    head = [(29, 63), (31, 61.6), (43, 61.6), (45.4, 63), (46, 66), (46, 71), (44.5, 73.5), (42, 74.4),
            (32, 74.4), (30, 73.4), (29, 71)]
    bt.prism(chamfer_outline(head, 0.3), 0, 4.9, 3, 0.9, 4, el="turret_head")
    b.box(35, 41, 65, 68, 0.0, 6.4, 90, 0.4, 90, panel=False, el="turret_hatch")
    b.box(36, 36, 65, 68, 6.3, 7.1, 72, 0.12, 72, panel=False, el="hatch_stripe")
    b.box(39, 39, 64, 68, 6.3, 7.1, 72, 0.12, 72, panel=False, el="hatch_stripe")
    b.box(35, 41, 69, 70, 0.0, 5.7, 84, 0.3, el="hatch_sill")
    for c in (35, 37, 39):
        b.box(c, c, 72, 73, 1.9, 5.7, 70, 0.2, 70, el="louvre")
    b.box(33.6, 41.2, 71.6, 74.2, 1.5, 3.8, 3, 0.2, 3, panel=False)
    b.loft("y", 26.5, [(61.6, 1.2, 1.9, 2.7), (62.2, 1.6, 2.66, 2.7), (71.4, 1.6, 2.66, 2.7),
                       (72.0, 1.2, 1.9, 2.7)], 69, 12, chamfer=False, el="tank_red")
    b.box(25, 25, 62.4, 70.4, 3.4, 5.1, 72)
    for r in (63.6, 69.6):
        b.box(24.7, 28.3, r, r + 0.4, 0, 5.6, 71, 0.1, ch=0.1, panel=False)
    b.rbox(31, 34, 58, 62, 0.0, 5.7, 70, 0.5, 70, el="turret_box_red")
    b.box(29, 29, 62, 66, 0.0, 5.1, 10, 0.3, 8, el="turret_sensor")
    for k in range(10):
        a = math.pi * (0.15 + 0.7 * k / 9)
        b.bolt(37.5 - 9.2 * math.cos(a), 69.6 + 8.0 * math.sin(a), 3.4, 4)


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
    # Parts, clipped to F: only the islands whose plan box leaves F get a boolean.
    bp = B(mats)
    bt = B(mats)
    bh_ = B(mats)
    build_casemate(bh_, F)
    house = bh_.finish("house", coll, weld=True)
    print("house faces", len(house.data.polygons), "zmax px", max((v.co.z for v in house.data.vertices), default=0) * 12)
    build_parts(bp, bt)
    parts = bp.finish("parts", coll, weld=False)
    turret = bt.finish("turret", coll, weld=False)
    # The turret casting keeps the sprite's see-through gaps (hatch slit, the hole by the box): it is
    # cut by a plate with those holes (enclosed non-plan px of the turret block), nothing else.
    zone = np.zeros_like(F)
    zone[59:81, 22:50] = True
    outside = np.zeros_like(F)
    stack = [(59, 22)]
    while stack:
        r, c = stack.pop()
        if not (59 <= r < 81 and 22 <= c < 50) or outside[r, c] or F[r, c]:
            continue
        outside[r, c] = True
        stack += [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]
    for r in range(59, 81):  # flood from every zone edge
        for c in (22, 49):
            stack.append((r, c))
    for c in range(22, 50):
        for r in (59, 80):
            stack.append((r, c))
    while stack:
        r, c = stack.pop()
        if not (59 <= r < 81 and 22 <= c < 50) or outside[r, c] or F[r, c]:
            continue
        outside[r, c] = True
        stack += [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]
    holes = zone & ~F & ~outside
    print("turret holes px", int(holes.sum()), [tuple(map(int, x)) for x in np.argwhere(holes)])
    bh = B(mats)
    slab(bh, smooth_field(zone & ~holes), 60.0, 0.0, 2, z0=-3.0, tol=0.05, min_area=0.0)
    hcut = bh.finish("hcut", coll)
    mod = turret.modifiers.new("holes", "BOOLEAN")
    mod.operation = "INTERSECT"
    mod.object = hcut
    mod.solver = "MANIFOLD"
    try:
        mod.material_mode = "TRANSFER"
    except Exception:  # noqa: BLE001
        pass
    apply_mods(turret)
    bpy.data.objects.remove(hcut, do_unlink=True)
    print("parts tris before clip", sum(len(f.vertices) - 2 for f in parts.data.polygons))
    fieldF = grown_field(closed_plan(F))  # fittings clipped to the same narrowed slits as the casemate
    # The power turret's ring (rows 58+) is one round casting: its plan is the sprite blurred wider,
    # so the ring and its plinth end in a smooth curve, not the dark border's pixel knobs.
    i0 = int((58 + PAD) * SUB)
    soft = smooth_field(F, 1.0)
    fieldF[i0:] = np.minimum(fieldF[i0:], soft[i0:] + 0.12)  # trims knobs, keeps the sprite's gaps
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
        print(f"clip: c {c0:.1f}-{c1:.1f} r {r0:.1f}-{r1:.1f} z {max(v.co.z for v in o.data.vertices) * 12 if o.data.vertices else 0:.1f}"
              f" faces {nb} -> {len(o.data.polygons)}")
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
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    parts.select_set(True)
    turret.select_set(True)
    house.select_set(True)
    bpy.context.view_layer.objects.active = parts
    bpy.ops.object.join()
    bpy.data.objects.remove(cutter, do_unlink=True)
    # Parts stand on the deck / pad: their ground faces (z = 0, facing down) are dropped so the
    # underside is the deck's own closed bottom (no z-fighting there).
    bm = bmesh.new()
    bm.from_mesh(parts.data)
    dead = [f for f in bm.faces if f.normal.z < -0.99 and max(abs(v.co.z) for v in f.verts) < 1e-4]
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bm.to_mesh(parts.data)
    bm.free()

    # Base deck: one armoured plinth under the whole plan (gunmetal, not ink black). No pad: the
    # turret stands on the HD ground (D130).
    bd = B(mats)
    deckF = fieldF.copy()  # the plan's smooth outline (grown_field): no pixel stairs round the plinth
    deckF[int((61.7 + PAD) * SUB):] = 0.0  # the turret's ring is its own base
    deckF[i0:] = np.minimum(deckF[i0:], soft[i0:] + 0.12)
    slab(bd, deckF, DK, 0.45, 4, tol=0.16, min_area=1.2)
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
    return obj, bh_.parts + bp.parts + bt.parts, P, colors, F


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
    sealed = {}
    for name, cx, cy in layout:
        p = pieces[name]
        p.location = (cx / 12, -cy / 12, 0)
        # The outline shell's source: a copy taken BEFORE the cull, kept out of the scene (D90/D118:
        # a shell wrapped round the culled, open parts followed the seams in and drew ink slabs).
        sealed[name] = bpy.data.objects.new(f"{name}_sealed", p.data.copy())
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
        src = sealed[name]
        coll.objects.link(src)
        src.matrix_world = p.matrix_world.copy()
        bpy.context.view_layer.update()
        sh = common.outline_shell(src, coll, voxel=0.03, faces=2500, inside=0.004, islands="outer")
        bpy.data.objects.remove(src, do_unlink=True)
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
    d = 11
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
