"""TYRIAN's brass drums (map 1-9, layer 2, Background3Over: tiles 189 pointing east, 199 pointing
west, one tile each; design A of the structure-rebuild wave 2, D141's hard-surface standard).

What it is (from the tiles): a brass machine housing lying on the island rock, its axis east-west
(pixel row 13.5). Seen from above its lid (rows 5-12) is a barrel vault: brass flanks, a tan hatch
plate in the middle (palette 160-167), a vertical strap beside it and end hoops; a riveted strap
runs across where the lid meets the front (rows 12-14); the front (rows 14-22), sloping toward the
camera, carries two louvred windows (rows 14-17), a riveted rail (rows 17-19) and a vertical slot
grille (rows 19-22). On the pointed end, past a dark neck, a nose on the same axis: a ringed cone
(east, tile 189) or a fluted ogive (west, tile 199). The west drum is the east one mirrored
(column c -> 21 - c, which the art follows pixel for pixel on the housing) with its own nose.

Built as hard surface: the housing is a loft along X of one chamfered section (vault + sloped face)
with 45-degree end chamfers; straps, hoops, hatch plate, rail and slats are thin lofts or chamfered
boxes laid on the vault or the face plane; the noses are lathes (sharp edges split by angle).
Colours: each region's palette index is the trimmed median of the art's pixels for it (darkest and
brightest fifth dropped, they are lighting). The island rock round it is the tile's own rock
(Structure.rock, plain, unbaked). AO/roughness bake only (bake_model), no concept projection, no
outline shell (tile models, D141). Everything stays under L2_OVER_MAX 0.38 (Background3Over).

Build (the models replace tiles 189 / 199 and carry the island rock; the tile contract is
unchanged from the old script):
    tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/tyrbld_drum.py
    blender --background --factory-startup --python assets/blender/tiles/tyrbld_drum.py -- [--no-bake] [--preview <dir>]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_sockets as ls  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402
from usp_talon import pchip  # noqa: E402

HERE = Path(__file__).resolve().parent
PX = lt.PX

# ---- Layout, in the EAST drum's pixel columns (the west drum mirrors them: c -> MIRROR - c) ------
MIRROR = 21.0
X0, X1 = 2.0, 13.0          # housing
AXIS = 13.5                 # pixel row of the nose's axis (the housing's middle row too)
BACK, FRONT = 5.0, 22.0     # housing's back and front feet (pixel rows)
SINK = -0.06                # every part's foot, under the rock's top (z = 0)
END_CH = 0.55               # px: the housing's end chamfer

# The vault (lid): pixel row -> height, through these stations (pchip).
VAULT = [(5.35, 0.232), (6.2, 0.300), (7.4, 0.338), (8.6, 0.350), (10.0, 0.342), (11.2, 0.322), (12.2, 0.298)]
BACK_WALL = 0.150           # height of the back wall before its chamfer
FACE_TOP = (13.9, 0.270)    # the sloped front face: a plane from here...
FACE_FOOT = (21.55, 0.070)  # ...to here, then a chamfer to the foot

NOSE_Z = 0.140              # nose axis height
NOSE_SQUASH = 0.60          # vertical radius / horizontal (stays under 0.38)

# Nose profiles (x in east-drum px, radius px), measured off the art's rows per column.
CONE = [(13.0, 0.0), (13.0, 3.1), (13.85, 3.1), (13.85, 4.0), (14.15, 4.45), (14.9, 4.5), (16.35, 4.05),
        (16.4, 4.22), (16.85, 4.22), (16.9, 3.85), (17.6, 3.3), (18.5, 2.45), (19.0, 1.95), (19.05, 1.65),
        (19.7, 1.05), (20.05, 0.45), (20.15, 0.0)]
OGIVE = [(13.0, 0.0), (13.0, 3.1), (13.8, 3.1), (13.8, 4.05), (14.2, 4.45), (14.9, 4.5), (16.0, 4.4),
         (17.0, 4.02), (18.0, 3.4), (19.0, 2.5), (19.7, 1.6), (20.15, 0.85), (20.4, 0.0)]


def vault_fn():
    xs, ys = zip(*VAULT)
    f = pchip(list(xs), list(ys))
    return lambda py: float(f(min(max(py, xs[0]), xs[-1])))


VZ = vault_fn()


def face_z(py):
    (a, za), (b, zb) = FACE_TOP, FACE_FOOT
    return za + (zb - za) * (py - a) / (b - a)


def lid_curve(a, b, n=None):
    """Points (py, z) along the vault from row a to row b."""
    n = n or max(3, int(abs(b - a) * 1.6) + 1)
    return [(a + (b - a) * i / (n - 1), VZ(a + (b - a) * i / (n - 1))) for i in range(n)]


def section():
    """The housing's closed cross-section [(py, z)], back foot -> vault -> front face -> foot.
    Returns the points and each edge's region ("back", "lid", "band", "face", "foot")."""
    pts, reg = [(BACK, SINK), (BACK, BACK_WALL)], ["back", "back"]
    for p in lid_curve(VAULT[0][0], VAULT[-1][0], 12):
        pts.append(p)
        reg.append("lid")
    pts += [(12.6, 0.283), FACE_TOP]
    reg += ["band", "band"]
    pts += [FACE_FOOT, (21.9, 0.030), (FRONT, 0.0), (FRONT, SINK)]
    reg += ["face", "face", "foot", "foot"]
    reg[-1] = "foot"  # the bottom edge (front foot -> back foot)
    return pts, reg


def offset(curve, d_px):
    """A polyline (py, z) moved d_px (pixels; z counted in pixels) along its left normal (outward
    for a curve running back -> front over the top)."""
    P = np.array([(p, z / PX) for p, z in curve], float)
    out = []
    for i in range(len(P)):
        a, b = P[max(0, i - 1)], P[min(len(P) - 1, i + 1)]
        t = (b - a) / max(np.hypot(*(b - a)), 1e-9)
        n = np.array([-t[1], t[0]])  # left of the direction of travel: up for a curve running +py? (fixed below)
        if n[1] < 0:
            n = -n
        q = P[i] + n * d_px
        out.append((q[0], q[1] * PX))
    return out


def inset_section(pts, d_px):
    P = [(p, z / PX) for p, z in pts]
    q = ls.inset(P, d_px)
    return [(p, z * PX) for p, z in q]


def trimmed_index(ts, values, trim=0.2):
    """A region's palette index: the median of its pixels after dropping the darkest and brightest
    `trim` (lighting: the outline ring, shading and sheen)."""
    v = [int(x) for x in values if x >= 0]
    if not v:
        return None
    v.sort(key=lambda i: ts.lum[i])
    k = int(len(v) * trim)
    core = v[k:len(v) - k] or v
    return core[len(core) // 2]


class Drum:
    def __init__(self, name):
        self.name = name
        self.west = name == "drum-w"
        self.s = tb.Structure(name)
        self.bm = None

    # coordinates: east-drum px -> this drum's px -> units
    def X(self, px):
        return self.s.x(MIRROR - px if self.west else px)

    def Y(self, py):
        return self.s.y(py)

    def col(self, c):
        """East-drum pixel column c -> this drum's."""
        return int(MIRROR - 1 - c) if self.west else c

    # ---- measuring ----
    def region(self, cols, rows, keep=lambda v: v > 3):
        g = self.s.grid
        vals = [g[r, self.col(c)] for r in rows for c in cols if keep(g[r, self.col(c)])]
        return vals

    def measure(self, pool=None):
        """Per-region palette indices, pooled over both drums' art (one object, two lightings)."""
        ts = self.s.ts
        pool = pool or [self]
        R = lambda cols, rows, **k: trimmed_index(ts, [v for d in pool for v in d.region(cols, rows, **k)])  # noqa: E731
        brass = lambda v: 16 <= v <= 31  # noqa: E731
        tan = lambda v: 160 <= v <= 175  # noqa: E731
        idx = {
            "flank": R([2, 3, 4, 10, 11, 12], range(5, 12), keep=brass),
            "strap": R([5], range(5, 12), keep=brass),
            "hatch": R([6, 7, 8, 9], range(5, 12), keep=tan),
            "band": R(range(2, 13), range(12, 14), keep=brass),
            "face": R(list(range(2, 13)), list(range(14, 17)) + list(range(19, 22)), keep=brass),
            "rail": R(range(2, 13), range(17, 19), keep=brass),
            "nose": R(range(14, 21), range(8, 19), keep=brass),
            "slot": 2,
        }
        self.idx = idx
        print(f"{self.name}: measured palette indices {idx}")
        return idx

    def art_mask(self):
        """What the art paints for the drum's own parts (pattern px, 1x): the housing box (minus
        its dark corner pixels), the neck and the nose's brass pixels, holes filled."""
        g = self.s.grid
        m = np.zeros(g.shape, bool)
        c0, c1 = (self.col(12), self.col(2)) if self.west else (2, 12)
        m[5:22, c0:c1 + 1] = True
        for r in (5, 21):
            for c in (c0, c1):
                if g[r, c] <= 3:
                    m[r, c] = False
        neck = self.col(13)
        m[10:17, neck] = True
        ncols = [self.col(c) for c in range(14, 21)]
        for c in ncols:
            for r in range(8, 19):
                if 16 <= g[r, c] <= 31:
                    m[r, c] = True
        # fill holes (4-connected flood from the border)
        H, W = m.shape
        out = np.zeros_like(m)
        stack = [(y, x) for y in range(H) for x in (0, W - 1)] + [(y, x) for x in range(W) for y in (0, H - 1)]
        while stack:
            y, x = stack.pop()
            if 0 <= y < H and 0 <= x < W and not out[y, x] and not m[y, x]:
                out[y, x] = True
                stack += [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
        return ~out

    # ---- geometry ----
    def mat(self, key, **kw):
        defaults = {
            "flank": dict(metallic=0.65, roughness=0.38), "strap": dict(metallic=0.65, roughness=0.36),
            "hatch": dict(metallic=0.35, roughness=0.55), "band": dict(metallic=0.65, roughness=0.36),
            "face": dict(metallic=0.6, roughness=0.42), "rail": dict(metallic=0.65, roughness=0.36),
            "nose": dict(metallic=0.65, roughness=0.36), "slot": dict(metallic=0.2, roughness=0.8),
            "neck": dict(metallic=0.5, roughness=0.5), "rivet": dict(metallic=0.7, roughness=0.3),
            "louvre": dict(metallic=0.55, roughness=0.45),
        }
        if key == "neck":
            idx = 17
        elif key == "rivet":
            idx = min(31, self.idx["band"] + 3)
        elif key == "louvre":
            idx = max(16, self.idx["face"] - 2)
        else:
            idx = self.idx[key]
        return self.s.m(idx, **{**defaults[key], **kw})

    def v(self, bm, px, py, z):
        return bm.verts.new((self.X(px), self.Y(py), z))

    def loft_x(self, stations, mats, cap_mat):
        """Closed loft along X: stations [(px, [(py, z), ...])], equal point counts; mats per
        section edge (edge i: point i -> i+1, last closes)."""
        bm = bmesh.new()
        rings = [[self.v(bm, x, p, z) for p, z in sec] for x, sec in stations]
        n = len(rings[0])
        for a, b in zip(rings, rings[1:]):
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mats[i]
        bm.faces.new(rings[0]).material_index = cap_mat
        bm.faces.new(list(reversed(rings[-1]))).material_index = cap_mat
        self.add(bm)

    def band(self, xa, xb, curve, t_px, mat, bevel_px=0.18):
        """A strap of thickness t_px laid over the polyline `curve` [(py, z)] from px xa to xb,
        its edges bevelled."""
        inner = offset(curve, -0.12)
        outer = offset(curve, t_px)
        soft = offset(curve, t_px * 0.35)
        sec = outer + list(reversed(inner))
        sec_e = soft + list(reversed(inner))
        n = len(sec)
        b = min(bevel_px, (xb - xa) / 3)
        self.loft_x([(xa, sec_e), (xa + b, sec), (xb - b, sec), (xb, sec_e)], [mat] * n, mat)

    def face_box(self, xa, xb, ya, yb, h0, h1, mat, ch=0.2):
        """A chamfered box lying on the sloped front face: px xa..xb, rows ya..yb, heights h0..h1
        above the face."""
        bm = bmesh.new()
        ch = min(ch, (xb - xa) / 3, (yb - ya) / 3)
        hh = h1 - (h1 - h0) * 0.35 if ch > 0 else h1

        def ring(inset, h):
            pts = [(xa + inset, ya + inset), (xb - inset, ya + inset), (xb - inset, yb - inset), (xa + inset, yb - inset)]
            return [self.v(bm, x, y, face_z(y) + h) for x, y in pts]

        rings = [ring(0, h0 - 0.01), ring(0, hh)] + ([ring(ch, h1)] if ch > 0 else [])
        for a, b in zip(rings, rings[1:]):
            for i in range(4):
                j = (i + 1) % 4
                bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat
        bm.faces.new(rings[-1]).material_index = mat
        bm.faces.new(list(reversed(rings[0]))).material_index = mat
        self.add(bm)

    def rivet(self, px, py, z, mat, r_px=0.38, h=0.014):
        bm = bmesh.new()
        lt.block(bm, self.X(px), self.Y(py), r_px * PX, r_px * PX, 0.0, z - 0.008, h + 0.008, mat, sides=6, bevel=0.45)
        self.add(bm)

    def lathe(self, prof, mats, sides=24, flute=None):
        """Nose: surface of revolution along X (east-drum px) about row AXIS at NOSE_Z, squashed.
        `flute(i)` -> radius factor per angular step (ribs)."""
        bm = bmesh.new()
        rings = []
        for x, r in prof:
            ring = []
            for i in range(sides):
                a = 2 * math.pi * i / sides
                k = flute(i) if (flute and r > 2.0) else 1.0
                u, w = r * k * math.cos(a), r * k * math.sin(a)
                ring.append(bm.verts.new((self.X(x), self.Y(AXIS + u), NOSE_Z + w * PX * NOSE_SQUASH)))
            rings.append(ring)
        for k_, (a, b) in enumerate(zip(rings, rings[1:])):
            for i in range(sides):
                j = (i + 1) % sides
                bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mats[k_]
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
        self.add(bm)

    def add(self, bm, sharp_deg=32.0):
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for f in bm.faces:
            f.smooth = True
        lim = math.radians(sharp_deg)
        for e in bm.edges:
            if len(e.link_faces) == 2:
                e.smooth = e.calc_face_angle(0.0) < lim
            else:
                e.smooth = False
        self.s._merge(bm)

    # ---- the drum ----
    def build(self):
        s = self.s
        self.measure([self, Drum("drum-w" if not self.west else "drum-e")])
        M = {k: self.mat(k) for k in ("flank", "strap", "hatch", "band", "face", "rail", "nose", "slot", "neck", "rivet", "louvre")}

        # Housing: one section lofted along X, ends chamfered 45 degrees.
        sec, reg = section()
        rmat = {"back": M["flank"], "lid": M["flank"], "band": M["band"], "face": M["face"], "foot": M["neck"]}
        mats = [rmat[r] for r in reg]
        sec_e = inset_section(sec, END_CH)
        self.loft_x([(X0, sec_e), (X0 + END_CH, sec), (X1 - END_CH, sec), (X1, sec_e)], mats, M["flank"])

        back = [(BACK - 0.0, SINK + 0.02), (BACK, BACK_WALL), (VAULT[0][0], VAULT[0][1])]
        lid = lid_curve(VAULT[0][0], VAULT[-1][0], 12)
        over = back + lid[1:] + [(12.6, 0.283), FACE_TOP]
        # End hoops round the vault and down the face (both ends), the vertical straps beside the
        # hatch (the art's column 5 and the hatch's east edge), the hatch plate between them.
        wrap = over + [(16.0, face_z(16.0)), (19.0, face_z(19.0)), FACE_FOOT, (21.9, 0.03), (FRONT, 0.0), (FRONT, SINK + 0.02)]
        for xa, xb in ((X0 + 0.25, X0 + 1.05), (X1 - 1.05, X1 - 0.25)):
            self.band(xa, xb, wrap, 0.26, M["strap"])
        strap_curve = back + lid[1:] + [(12.6, 0.283)]
        for xa, xb in ((5.05, 5.95), (9.95, 10.75)):
            self.band(xa, xb, strap_curve, 0.22, M["strap"])
        self.band(6.05, 9.9, lid_curve(5.75, 11.85, 10), 0.13, M["hatch"], bevel_px=0.25)
        for px in (6.55, 9.4):
            for py in (6.4, 11.2):
                self.rivet(px, py, VZ(py) + 0.011, M["rivet"], r_px=0.32, h=0.01)

        # The cross strap where the lid meets the front, riveted.
        cross = lid_curve(11.75, 12.2, 3) + [(12.6, 0.283), FACE_TOP, (14.25, face_z(14.25))]
        self.band(X0 + 0.15, X1 - 0.15, cross, 0.28, M["band"], bevel_px=0.25)
        for px in (X0 + 1.6, (X0 + X1) / 2, X1 - 1.6):
            self.rivet(px, 13.0, 0.281 + 0.024, M["rivet"])

        # Front face. Two louvred windows (rows 14-17): a dark recess plate, a raised frame, slats.
        for xa, xb in ((3.85, 7.05), (8.95, 12.15)):
            ya, yb = 14.35, 16.95
            self.face_box(xa + 0.3, xb - 0.3, ya + 0.3, yb - 0.25, -0.01, 0.003, M["slot"], ch=0)
            fw = 0.32
            for bx in ((xa, xa + fw, ya, yb), (xb - fw, xb, ya, yb), (xa + fw, xb - fw, ya, ya + fw), (xa + fw, xb - fw, yb - fw, yb)):
                self.face_box(*bx, 0.0, 0.024, M["face"], ch=0.1)
            for k in range(3):
                y = ya + fw + 0.35 + k * 0.62
                self.face_box(xa + fw, xb - fw, y, y + 0.28, 0.0, 0.014, M["louvre"], ch=0.08)
        # The rail across the middle (rows 17-19), riveted.
        self.face_box(X0 + 0.2, X1 - 0.2, 17.05, 18.95, 0.0, 0.028, M["rail"], ch=0.25)
        for px in (X0 + 1.4, (X0 + X1) / 2, X1 - 1.4):
            self.rivet(px, 18.0, face_z(18.0) + 0.028, M["rivet"])
        # The slot grille (rows 19-22): a dark backing and brass slats between the art's slots
        # (columns 4, 6, 9, 11).
        self.face_box(3.7, 12.3, 19.2, 21.45, -0.01, 0.004, M["slot"], ch=0)
        for xa, xb in ((3.55, 4.0), (5.0, 6.0), (7.0, 9.0), (10.0, 11.0), (12.0, 12.45)):
            self.face_box(xa, xb, 19.15, 21.5, 0.0, 0.022, M["face"], ch=0.12)
        self.face_box(3.55, 12.45, 21.35, 21.6, 0.0, 0.022, M["face"], ch=0.08)

        # Nose: neck, flange, then the ringed cone (east) or the fluted ogive (west).
        if self.west:
            prof = OGIVE
            mats = [M["neck"], M["neck"], M["neck"]] + [M["nose"]] * (len(prof) - 4)
            self.lathe(prof, mats, sides=36, flute=lambda i: 0.92 if i % 3 == 2 else 1.0)
        else:
            prof = CONE
            mats = [M["neck"], M["neck"], M["neck"]] + [M["nose"]] * (len(prof) - 4)
            for i, (x, r) in enumerate(prof[:-1]):
                if 16.35 <= x < 16.9 or 19.0 <= x < 19.6:
                    mats[i] = M["band"]
            self.lathe(prof, mats, sides=24)

        # The island's rock round it (plain, the tile's own rock model), level and dark under it.
        mask = self.art_mask()
        s.rock(exclude=lb.dilate(mask, 1))
        return mask


def build(name, bake=True, preview=None):
    lb.clear_scene()
    d = Drum(name)
    mask = d.build()
    s = d.s
    objects = s.objects()
    return s.finish(objects, mask, bake=bake, preview=preview)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
for _name in ("drum-e", "drum-w"):
    build(_name, bake="--no-bake" not in argv, preview=lt.preview_arg())
